#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""buscar_sinopsis.py — dónde está la sinopsis de una obra: siempre los mismos lugares, y queda escrito.

POR QUÉ (Juan, 26 nov 2026: «hay que poner guardianes a esos que buscaron poco; el método
de búsqueda debe ser pipeline y medido con rigor, no depender de lo que les da la gana»):
cuatro agentes buscaron la fuente de 29 obras; dos confesaron 5 búsquedas y ninguna en
Filmaffinity, IMDb ni las webs de los festivales. «Sin fuente» valía lo que el agente quisiera.

REGLA: la búsqueda la hace el código, en CLASES, en este orden. Cada lugar consultado deja
una línea en catalogo/busquedas/<obra>.json: dónde, qué pasó (literal · no está · ilegible ·
no vale · no responde · bloqueado · sin resultado) y una nota. Cada texto se comprueba con
sello_fuente.comprobar, la misma máquina que sella. Una obra se declara SIN FUENTE
(catalogo/sin-fuente.json) solo con el registro COMPLETO: todas las clases hechas o «no aplica»
con motivo, y toda consulta web respondida. validate [busqueda-completa] lo exige.

La búsqueda web es la única que no corre sola (los buscadores bloquean a los programas):
el código escribe las consultas EXACTAS; quien las corre anota un resultado por consulta
con --anotar. Nadie elige dónde buscar.

    python3 pipeline/buscar_sinopsis.py <work_id> [...]          # corre todas las clases salvo la web
    python3 pipeline/buscar_sinopsis.py --pendiente <work_id>    # consultas web por responder (JSON)
    python3 pipeline/buscar_sinopsis.py --anotar <res.json>      # [{work_id, consulta, resultado, url?, texto?, nota}]
    python3 pipeline/buscar_sinopsis.py --medir <n>              # contra obras ya selladas: ¿encuentra su fuente?
    python3 pipeline/buscar_sinopsis.py --sin-fuente <lista.json> # [{work_id, motivo}]: solo con registro completo
"""
import datetime
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
REGISTROS = os.path.join(REPO, 'catalogo', 'busquedas')
SIN_FUENTE = os.path.join(REPO, 'catalogo', 'sin-fuente.json')
CLASES = ('fuentes', 'instagram', 'tmdb', 'letterboxd', 'imdb', 'productora', 'filmaffinity', 'web')
RESULTADOS = ('literal', 'no está', 'ilegible', 'no vale', 'no responde', 'bloqueado', 'sin resultado')
LEIBLES = ('.html', '.htm', '.txt', '.json', '.csv', '.md', '.pdf', '.xml')


def _leer(p, d=None):
    if not os.path.exists(p):
        return {} if d is None else d
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _escribir(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write('\n')


def registro(w):
    return _leer(os.path.join(REGISTROS, w + '.json'))


def textos(w, pub, orig):
    """Lo que se busca: el original guardado y lo publicado (es, en)."""
    t = [('original', (orig or {}).get('texto'))] + [(k, x) for k in ('es', 'en') for x in sorted((pub or {}).get(k) or [])]
    return [(k, x) for k, x in t if x and x.strip()]


def dominios(festivales):
    """Las webs del festival: de dónde dice su procedencia que salió el programa."""
    out = set()
    for d in festivales:
        p = json.dumps({k: d.get(k) for k in ('_provenance', 'radar', '_acceso')}, ensure_ascii=False)
        out |= {m.lower().removeprefix('www.') for m in re.findall(r'\b((?:[a-z0-9-]+\.)+(?:com|co|org|net|cl|ar|mx|pe|ec|es|fr|br|info|tv|art|film|com\.co|org\.co))\b', p, re.I)}
    return sorted(out - {'instagram.com', 'facebook.com', 'themoviedb.org', 'letterboxd.com', 'youtube.com', 'vimeo.com'})


def consultas_web(ficha, txs, doms):
    """Las consultas EXACTAS de la clase web. Las escribe el código, no quien busca."""
    t = (ficha.get('titulos') or [''])[0]
    ap = ' '.join(re.split(r'\s+', d.strip())[-1] for d in (ficha.get('directores') or [])[:2])
    q = [f'"{t}" {ap}'.strip(), f'"{t}" sinopsis', f'"{t}" synopsis {ap}'.strip()]
    for _, x in txs[:1]:
        q.append('"' + ' '.join(re.findall(r'\w+', x)[:9]) + '"')
    q += [f'site:{d} "{t}"' for d in doms]
    return list(dict.fromkeys(q))


def _comprobar(txs, fuente, ficha, comprobar):
    """Cada texto contra una fuente → la mejor línea (literal gana)."""
    from sello_fuente import SinLeer
    mejor = None
    for k, x in txs:
        try:
            e, d = comprobar({'texto': x, 'idioma': '', 'fuente': fuente}, obra=ficha)
        except SinLeer as z:
            return {'donde': fuente, 'resultado': 'no responde', 'nota': str(z)[:120]}
        lin = {'donde': fuente, 'resultado': e, 'nota': f'{k}: {d}'[:200]}
        if e == 'literal':
            return lin
        if mejor is None or (e == 'ilegible' and mejor['resultado'] != 'ilegible'):
            mejor = lin
    return mejor


def _archivos(carpetas, ficha):
    """Archivos de fuentes/ donde aparece lo que ata un texto a la obra: un título o el apellido
    de quien la dirige (una ficha de cinecorto trae el título solo en la URL)."""
    from sello_fuente import leer_local, plano, FUENTES, anclas
    tit = [a for a in anclas(ficha) if len(a) >= 4]
    for c in carpetas:
        for p in sorted(glob.glob(os.path.join(FUENTES, c, '**', '*'), recursive=True)):
            if not p.lower().endswith(LEIBLES) or not os.path.isfile(p) or os.path.getsize(p) > 30_000_000:
                continue
            r = 'fuentes/' + os.path.relpath(p, FUENTES)
            if any(t in plano(leer_local(r)) for t in tit):
                yield r


def _tmdb(i, ruta):
    import urllib.request
    k = os.environ.get('TMDB_API_KEY') or ''
    u = f'https://api.themoviedb.org/3/movie/{i}{ruta}' + ('' if len(k) > 40 else f'?api_key={k}')
    h = {'Authorization': 'Bearer ' + k} if len(k) > 40 else {}
    with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
        return json.load(r)


def buscar(w, festivales=None, comprobar=None, clases=CLASES, red=None):
    """Corre las clases (menos la web, que solo deja sus consultas) y escribe el registro."""
    import sello_obra as so
    from sello_fuente import leer_web, SinLeer
    comprobar = comprobar or __import__('sello_fuente').comprobar
    red = red or {'web': leer_web, 'tmdb': _tmdb}
    if festivales is None:
        from obra_unica import _festivales
        festivales = _festivales()
    fs = sorted(k for k, d in festivales.items() if f'"{w}"' in json.dumps(d))
    pub = so.publicadas({k: festivales[k] for k in fs}).get(w)
    ficha = so.ficha(w, pub)
    txs = textos(w, pub, so.originales().get(w))
    reg = {'work_id': w, 'fecha': datetime.date.today().isoformat(), 'festivales': fs, 'clases': {}}
    if not txs:
        reg['clases'] = {c: {'no aplica': 'la obra no publica sinopsis'} for c in CLASES}
        _escribir(os.path.join(REGISTROS, w + '.json'), reg)
        return reg
    C = reg['clases']
    tm = ficha.get('tmdb')
    if 'fuentes' in clases:
        lin = [_comprobar(txs, p, ficha, comprobar) for p in _archivos(fs, ficha)]
        C['fuentes'] = {'consultas': lin or [{'donde': 'fuentes/' + ', fuentes/'.join(fs), 'resultado': 'sin resultado', 'nota': 'ningún archivo nombra la obra'}]}
    if 'instagram' in clases:
        lin = [_comprobar(txs, p, ficha, comprobar) for p in _archivos(['ig-vigia'], ficha)]
        C['instagram'] = {'consultas': lin or [{'donde': 'fuentes/ig-vigia', 'resultado': 'sin resultado', 'nota': 'ningún post guardado nombra la obra'}]}
    det = {}
    if tm:
        try:
            det = red['tmdb'](tm, '') or {}
            det['ids'] = red['tmdb'](tm, '/external_ids') or {}
        except Exception as z:
            det = {'error': str(z)[:120]}
    sin_tm = {'no aplica': 'la obra no tiene ficha TMDB'}
    if 'tmdb' in clases:
        C['tmdb'] = {'consultas': [_comprobar(txs, f'https://www.themoviedb.org/movie/{tm}', ficha, comprobar)]} if tm else sin_tm
    paginas = {'letterboxd': f'https://letterboxd.com/tmdb/{tm}/' if tm else None,
               'imdb': f'https://www.imdb.com/title/{det["ids"]["imdb_id"]}/' if (det.get('ids') or {}).get('imdb_id') else None,
               'productora': det.get('homepage') or None}
    motivos = {'letterboxd': 'la obra no tiene ficha TMDB', 'imdb': 'TMDB no da número de IMDb',
               'productora': 'TMDB no da página oficial'}
    for c in ('letterboxd', 'imdb', 'productora'):
        if c not in clases:
            continue
        u = paginas[c]
        if not u:
            C[c] = {'no aplica': motivos[c] if tm or c == 'letterboxd' else 'la obra no tiene ficha TMDB'}
            continue
        try:
            leido = red['web'](u)
        except SinLeer as z:
            C[c] = {'consultas': [{'donde': u, 'resultado': 'no responde', 'nota': str(z)[:120]}]}
            continue
        C[c] = {'consultas': [_comprobar(txs, u, ficha, comprobar) if leido else {'donde': u, 'resultado': 'bloqueado', 'nota': 'la página no se dejó leer'}]}
    if 'filmaffinity' in clases:
        t = (ficha.get('titulos') or [''])[0]
        u = 'https://www.filmaffinity.com/co/search.php?stext=' + __import__('urllib.parse').parse.quote(t)
        try:
            leido = red['web'](u)
            pelis = list(dict.fromkeys(re.findall(r'filmaffinity\.com/\w+/film\d+\.html', leido)))[:3]
            if not leido:
                C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'bloqueado', 'nota': 'la búsqueda no se dejó leer'}]}
            elif not pelis:
                C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'sin resultado', 'nota': 'sin fichas en la búsqueda'}]}
            else:
                C['filmaffinity'] = {'consultas': [_comprobar(txs, 'https://www.' + p, ficha, comprobar) for p in pelis]}
        except SinLeer as z:
            C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'no responde', 'nota': str(z)[:120]}]}
    if 'web' in clases:
        viejo = {q['consulta']: q for q in (registro(w).get('clases', {}).get('web', {}).get('consultas') or []) if q.get('resultado')}
        C['web'] = {'consultas': [viejo.get(q) or {'consulta': q} for q in consultas_web(ficha, txs, dominios(festivales[k] for k in fs))]}
    reg['hallazgo'] = hallazgo(reg)
    _escribir(os.path.join(REGISTROS, w + '.json'), reg)
    return reg


def hallazgo(reg):
    """Literal gana; si no, un texto que está pero sin título ni dirección cerca (lo confirma una persona)."""
    qs = [(c, q) for c in CLASES for q in (reg.get('clases', {}).get(c) or {}).get('consultas') or []]
    for c, q in qs:
        if q.get('resultado') == 'literal':
            return {'clase': c, 'donde': q.get('donde') or q.get('url')}
    for c, q in qs:
        if q.get('resultado') == 'ilegible' and 'el texto está' in (q.get('nota') or ''):
            return {'clase': c, 'donde': q.get('donde') or q.get('url'), 'a_mano': True}
    return None


def incompleto(reg):
    """→ qué falta para que el registro diga «busqué en todo». [] = completo."""
    falta = []
    for c in CLASES:
        x = (reg.get('clases') or {}).get(c)
        if not x:
            falta.append(f'{c}: no se consultó')
        elif 'no aplica' in x:
            if not str(x['no aplica']).strip():
                falta.append(f'{c}: «no aplica» sin motivo')
        elif not x.get('consultas'):
            falta.append(f'{c}: sin consultas')
        else:
            falta += [f'{c}: «{q.get("consulta") or q.get("donde")}» sin resultado anotado'
                      for q in x['consultas'] if q.get('resultado') not in RESULTADOS]
    return falta


def anotar(lote, comprobar=None):
    """Resultado de cada consulta web. Si trae URL y texto, la máquina lo comprueba."""
    import sello_obra as so
    comprobar = comprobar or __import__('sello_fuente').comprobar
    for e in lote:
        w, reg = e['work_id'], registro(e['work_id'])
        qs = (reg.get('clases', {}).get('web') or {}).get('consultas')
        if not qs:
            raise SystemExit(f'✗ {w}: primero buscar (sin consultas web emitidas)')
        q = next((q for q in qs if q.get('consulta') == e.get('consulta')), None)
        if q is None:
            raise SystemExit(f'✗ {w}: «{e.get("consulta")}» no es una consulta emitida; se anotan las del código, tal cual')
        if e.get('resultado') not in ('sin resultado', 'bloqueado', 'no responde') and not e.get('url'):
            raise SystemExit(f'✗ {w}: un resultado que no es «sin resultado» lleva url')
        q.update({k: e[k] for k in ('resultado', 'url', 'nota') if e.get(k)})
        if e.get('url'):
            pub = so.publicadas({k: v for k, v in __import__('obra_unica')._festivales().items() if k in reg['festivales']}).get(w)
            txs = textos(w, pub, so.originales().get(w))
            r = _comprobar(txs, e['url'], so.ficha(w, pub), comprobar) or {}
            q.update({'resultado': r.get('resultado', 'no está'), 'nota': (e.get('nota') or '') + ' · máquina: ' + (r.get('nota') or '')})
            if e.get('texto'):
                q['texto_otro'] = e['texto'][:2000]     # otra sinopsis de la obra: sirve para reescribir, no para sellar
        reg['hallazgo'] = hallazgo(reg)
        _escribir(os.path.join(REGISTROS, w + '.json'), reg)
    return len(lote)


def declarar_sin_fuente(lote):
    sf = _leer(SIN_FUENTE)
    for e in lote:
        w, reg = e['work_id'], registro(e['work_id'])
        if not str(e.get('motivo') or '').strip():
            raise SystemExit(f'✗ {w}: lleva motivo')
        if incompleto(reg) or not reg:
            raise SystemExit(f'✗ {w}: búsqueda incompleta: ' + '; '.join(incompleto(reg)[:5] or ['sin registro']))
        if reg.get('hallazgo'):
            raise SystemExit(f'✗ {w}: la búsqueda SÍ halló fuente ({reg["hallazgo"]})')
        sf[w] = e['motivo']
    _escribir(SIN_FUENTE, sf)
    return len(lote)


def problemas():
    """Para validate: toda obra declarada sin fuente tiene su búsqueda completa y sin hallazgo."""
    out = []
    for w in sorted(_leer(SIN_FUENTE)):
        reg = registro(w)
        if not reg:
            out.append(f'{w}: declarada sin fuente y sin registro de búsqueda')
        elif incompleto(reg):
            out.append(f'{w}: ' + '; '.join(incompleto(reg)[:3]))
        elif hallazgo(reg):
            out.append(f'{w}: declarada sin fuente, pero la búsqueda halló {hallazgo(reg)["donde"]}')
    return out


def medir(n, semilla=7):
    """Obras con sello comprobado por máquina: ¿la búsqueda (sin la web) halla su fuente?"""
    import random
    import sello_obra as so
    from collections import Counter
    sel = so.sellos()
    ws = sorted(w for w, s in sel.items() if str(s.get('comprobado') or '').startswith('máquina:'))
    random.Random(semilla).shuffle(ws)
    por, ok, mano = Counter(), 0, 0
    for w in ws[:n]:
        r = buscar(w, clases=[c for c in CLASES if c != 'web'])
        h = r.get('hallazgo')
        ok += bool(h)
        por[h['clase'] if h else '—'] += 1
        mano += bool(h and h.get('a_mano'))
        print(w, (h['clase'] + (' (a mano)' if h.get('a_mano') else '')) if h else 'NO HALLÓ', sel[w].get('comprobado', '')[:80], sep=' · ', flush=True)
    print(f'halló {ok} de {min(n, len(ws))} ({100 * ok // max(1, min(n, len(ws)))} %; {mano} a confirmar a mano) · por clase: {dict(por)}')
    return ok, min(n, len(ws))


def autoprueba():
    mal = []
    reg = {'clases': {c: {'consultas': [{'donde': 'x', 'resultado': 'no está'}]} for c in CLASES}}
    if incompleto(reg):
        mal.append('un registro completo sale incompleto')
    r2 = json.loads(json.dumps(reg)); del r2['clases']['imdb']
    if not incompleto(r2):
        mal.append('acepta un registro sin una clase')
    r3 = json.loads(json.dumps(reg)); r3['clases']['web'] = {'consultas': [{'consulta': '"x"'}]}
    if not incompleto(r3):
        mal.append('acepta una consulta web sin resultado')
    r4 = json.loads(json.dumps(reg)); r4['clases']['imdb'] = {'no aplica': ' '}
    if not incompleto(r4):
        mal.append('acepta «no aplica» sin motivo')
    q = consultas_web({'titulos': ['La tinaja'], 'directores': ['Ana María Pérez']}, [('es', 'Una mujer vuelve a su pueblo y encuentra un hotel abandonado.')], ['cinecorto.co'])
    if '"La tinaja" Pérez' not in q or 'site:cinecorto.co "La tinaja"' not in q or not any(x.startswith('"Una mujer vuelve') for x in q):
        mal.append(f'consultas web: {q}')
    if dominios([{'_provenance': {'fuente': 'festicinepopayan.com, página de programación'}}]) != ['festicinepopayan.com']:
        mal.append('no saca el dominio de la procedencia')
    return mal


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--anotar']:
        print(anotar(_leer(a[1], [])), 'consultas anotadas')
    elif a[:1] == ['--pendiente']:
        print(json.dumps([{'work_id': w, 'consulta': q['consulta']} for w in a[1:]
                          for q in (registro(w).get('clases', {}).get('web') or {}).get('consultas') or [] if not q.get('resultado')], ensure_ascii=False, indent=1))
    elif a[:1] == ['--medir']:
        ok, n = medir(int(a[1]))
        sys.exit(0 if ok * 10 >= n * 9 else 1)
    elif a[:1] == ['--sin-fuente']:
        print(declarar_sin_fuente(_leer(a[1], [])), 'declaradas sin fuente')
    elif a[:1] == ['--autoprueba']:
        m = autoprueba(); print('\n'.join(m) or 'OK'); sys.exit(bool(m))
    else:
        for w in a:
            r = buscar(w)
            print(w, (r.get('hallazgo') or {}).get('donde') or 'sin hallazgo', '· falta: ' + '; '.join(incompleto(r)[:3]) if incompleto(r) else '· completo', sep=' ')
