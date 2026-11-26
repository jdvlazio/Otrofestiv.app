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

OBRA SIN NINGÚN TEXTO (Onboarding, 26 nov 2026: las 20 de Festicine Antioquia salían con las
ocho clases en «no aplica: la obra no publica sinopsis» y el registro quedaba COMPLETO sin haber
buscado nada). Ahí no hay texto que comprobar: se busca la obra, por título y dirección. Cada
archivo guardado que la nombra y cada página suya queda como línea POR LEER; TMDB se consulta
por número o, sin número, por título con la dirección confirmada en los créditos. Quien lee
anota con --anotar: «sin resultado», o el texto hallado, que la máquina comprueba en ese mismo
lugar. Un registro con todas las clases en «no aplica» ya no cuenta como búsqueda.

La búsqueda web es la única que no corre sola (los buscadores bloquean a los programas):
el código escribe las consultas EXACTAS; quien las corre anota un resultado por consulta
con --anotar. Nadie elige dónde buscar.

    python3 pipeline/buscar_sinopsis.py <work_id> [...]          # corre todas las clases salvo la web
    python3 pipeline/buscar_sinopsis.py --pendiente <work_id>    # consultas web y líneas por leer que faltan (JSON)
    python3 pipeline/buscar_sinopsis.py --anotar <res.json>      # [{work_id, consulta | donde, resultado, url?, texto?, idioma?, nota}]
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
    if not txs:         # sin texto que citar, la obra se busca donde suele tener ficha
        q += [f'"{t}" {ap} cortometraje'.strip(), f'"{t}" {ap} filmfreeway'.strip(), f'"{t}" {ap} vimeo OR youtube'.strip()]
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


def _nombra(ficha):
    """→ f(texto plano) → dónde nombra a la obra (posición) o -1. Para una obra SIN texto: el
    título manda; un título de una palabra corriente («Hush», «Criatura») solo con el apellido."""
    from sello_fuente import plano, apellido, _titulo_ancla
    fuertes = {_titulo_ancla(x) for x in ficha.get('titulos') or []} - {''}
    debiles = {plano(x) for x in ficha.get('titulos') or []} - fuertes - {''}
    aps = {apellido(d) for d in ficha.get('directores') or []} - {''}

    def f(p):
        for x in fuertes:
            if x in p:
                return p.index(x)
        if aps and any(a in p for a in aps):
            for x in debiles:
                m = re.search(r'\b' + re.escape(x) + r'\b', p)
                if m:
                    return m.start()
        return -1
    return f


def _archivos(carpetas, ficha, nombra=None):
    """Archivos de fuentes/ donde aparece lo que ata un texto a la obra: un título o el apellido
    de quien la dirige (una ficha de cinecorto trae el título solo en la URL). Con `nombra`
    (obra sin texto) da (archivo, lo que sigue al título): eso se lee, no se comprueba."""
    from sello_fuente import leer_local, plano, FUENTES, anclas
    tit = [a for a in anclas(ficha) if len(a) >= 4]
    for c in carpetas:
        for p in sorted(glob.glob(os.path.join(FUENTES, c, '**', '*'), recursive=True)):
            if not p.lower().endswith(LEIBLES) or not os.path.isfile(p) or os.path.getsize(p) > 30_000_000:
                continue
            r = 'fuentes/' + os.path.relpath(p, FUENTES)
            pl = plano(leer_local(r))
            if nombra:
                i = nombra(pl)
                if i >= 0:
                    yield r, pl[i:i + 400]
            elif any(t in pl for t in tit):
                yield r


def _tmdb_buscar(titulo):
    """TMDB por título → [{id, titulo, directores}] (hasta 5), con la dirección de los créditos."""
    import urllib.parse
    import urllib.request
    k = os.environ.get('TMDB_API_KEY') or ''
    h = {'Authorization': 'Bearer ' + k} if len(k) > 40 else {}

    def pide(ruta, q=''):
        u = 'https://api.themoviedb.org/3' + ruta + '?' + q + ('' if h else ('&' if q else '') + 'api_key=' + k)
        with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
            return json.load(r)
    out = []
    for x in (pide('/search/movie', 'query=' + urllib.parse.quote(titulo)).get('results') or [])[:5]:
        cr = pide(f'/movie/{x["id"]}/credits').get('crew') or []
        out.append({'id': x['id'], 'titulo': x.get('original_title') or x.get('title') or '',
                    'directores': [c.get('name') or '' for c in cr if c.get('job') == 'Director']})
    return out


def _suyas(ficha, red):
    """Sin número de TMDB en la obra: las fichas con su título Y su dirección → (cuántas había, las suyas)."""
    from sello_fuente import plano, apellido
    aps = {apellido(d) for d in ficha.get('directores') or []} - {''}
    t0 = (ficha.get('titulos') or [''])[0]
    cands = red['buscar'](t0) if t0 else []
    return len(cands), [x for x in cands if aps and any(a in plano(' '.join(x['directores'])) for a in aps)][:2]


def ficha_de(w, festivales, pub=None):
    """La ficha de la obra; si el almacén no trae título o dirección, lo que publican los festivales
    (una obra sin sinopsis no sale en sello_obra.publicadas)."""
    import sello_obra as so
    import catalogo
    f = so.ficha(w, pub)
    if f['titulos'] and f['directores']:
        return f
    for _, d in sorted(festivales.items()):
        for x in (d or {}).get('films') or []:
            if not isinstance(x, dict):
                continue
            x = dict(x, film_list=[y for y in x['film_list'] if isinstance(y, dict)]) if isinstance(x.get('film_list'), list) else x
            for o in catalogo.obras_de(x):
                if o.get('work_id') == w and o.get('type') != 'event':
                    if o.get('title') and o['title'] not in f['titulos']:
                        f['titulos'].append(o['title'])
                    if o.get('director') and not f['directores']:
                        f['directores'] = [o['director']]
    return f


def _descubrir(w, reg, fs, ficha, festivales, clases, red):
    """Obra SIN texto: se busca la obra. Lo que no puede decidir el código queda POR LEER."""
    from sello_fuente import SinLeer, plano, apellido
    C, nombra = reg['clases'], _nombra(ficha)
    viejo = {(c, q.get('donde') or q.get('consulta')): q for c, x in (registro(w).get('clases') or {}).items()
             for q in x.get('consultas') or [] if q.get('resultado')}

    def linea(c, donde, **mas):
        return viejo.get((c, donde)) or {'donde': donde, **mas}
    for c, carpetas, vacio in (('fuentes', fs, 'ningún archivo nombra la obra'), ('instagram', ['ig-vigia'], 'ningún post guardado nombra la obra')):
        if c in clases:
            lin = [linea(c, p, contexto=ctx) for p, ctx in _archivos(carpetas, ficha, nombra)]
            C[c] = {'consultas': lin or [{'donde': 'fuentes/' + ', fuentes/'.join(carpetas), 'resultado': 'sin resultado', 'nota': vacio}]}
    tm, hallada = ficha.get('tmdb'), None
    if 'tmdb' in clases:
        try:
            if tm:
                ts = {i: x for i, x in red['textos'](tm) if x and x.strip()}
                u = f'https://www.themoviedb.org/movie/{tm}'
                C['tmdb'] = {'consultas': [{'donde': u, 'resultado': 'literal', 'texto': ts.get('es') or ts.get('en') or next(iter(ts.values())),
                                            'idioma': 'es' if ts.get('es') else 'en' if ts.get('en') else next(iter(ts)), 'textos': ts,
                                            'nota': f'TMDB {tm}, la ficha de la obra'} if ts else
                                           {'donde': u, 'resultado': 'sin resultado', 'nota': f'TMDB {tm}: la ficha no tiene sinopsis'}]}
            else:
                aps = {apellido(d) for d in ficha.get('directores') or []} - {''}
                t0 = (ficha.get('titulos') or [''])[0]
                cands = red['buscar'](t0) if t0 else []
                suyas = [x for x in cands if aps and any(a in plano(' '.join(x['directores'])) for a in aps)]
                lin = []
                for x in suyas[:2]:
                    ts = {i: y for i, y in red['textos'](x['id']) if y and y.strip()}
                    u = f'https://www.themoviedb.org/movie/{x["id"]}'
                    hallada = hallada or x['id']
                    lin.append({'donde': u, 'resultado': 'ilegible', 'texto': ts.get('es') or ts.get('en') or next(iter(ts.values())),
                                'idioma': 'es' if ts.get('es') else 'en' if ts.get('en') else next(iter(ts)), 'textos': ts,
                                'nota': f'TMDB {x["id"]} («{x["titulo"]}», {", ".join(x["directores"])}): hallada por título y dirección; la obra no tiene ese número, lo confirma una persona'} if ts else
                               {'donde': u, 'resultado': 'sin resultado', 'nota': f'TMDB {x["id"]} es de la obra por título y dirección, y no tiene sinopsis'})
                C['tmdb'] = {'consultas': lin or [{'donde': f'TMDB, búsqueda «{t0}»', 'resultado': 'sin resultado',
                                                   'nota': f'{len(cands)} ficha(s) con ese título; ninguna con la dirección de la obra' if aps else 'la obra no tiene dirección con qué confirmar una ficha'}]}
        except Exception as z:
            C['tmdb'] = {'consultas': [{'donde': 'TMDB', 'resultado': 'no responde', 'nota': str(z)[:120]}]}
    i = tm or hallada
    det = {}
    if i and {'imdb', 'productora'} & set(clases):
        try:
            det = red['tmdb'](i, '') or {}
            det['ids'] = red['tmdb'](i, '/external_ids') or {}
        except Exception as z:
            det = {'error': str(z)[:120]}
    paginas = {'letterboxd': f'https://letterboxd.com/tmdb/{i}/' if i else None,
               'imdb': f'https://www.imdb.com/title/{det["ids"]["imdb_id"]}/' if (det.get('ids') or {}).get('imdb_id') else None,
               'productora': det.get('homepage') or None}
    motivos = {'letterboxd': 'la obra no tiene ficha TMDB (se buscó por título y dirección)', 'imdb': 'TMDB no da número de IMDb' if i else 'la obra no tiene ficha TMDB (se buscó por título y dirección)',
               'productora': 'TMDB no da página oficial' if i else 'la obra no tiene ficha TMDB (se buscó por título y dirección)'}
    for c in ('letterboxd', 'imdb', 'productora'):
        if c not in clases:
            continue
        u = paginas[c]
        if not u:
            C[c] = {'no aplica': motivos[c]}
            continue
        if (c, u) in viejo:
            C[c] = {'consultas': [viejo[(c, u)]]}
            continue
        try:
            leido = red['web'](u)
        except SinLeer as z:
            C[c] = {'consultas': [{'donde': u, 'resultado': 'no responde', 'nota': str(z)[:120]}]}
            continue
        C[c] = {'consultas': [{'donde': u} if leido else {'donde': u, 'resultado': 'bloqueado', 'nota': 'la página no se dejó leer'}]}
    if 'filmaffinity' in clases:
        t0 = (ficha.get('titulos') or [''])[0]
        u = 'https://www.filmaffinity.com/co/search.php?stext=' + __import__('urllib.parse').parse.quote(t0)
        try:
            leido = red['web'](u)
            pelis = list(dict.fromkeys(re.findall(r'filmaffinity\.com/\w+/film\d+\.html', leido)))[:3]
            if not leido:
                C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'bloqueado', 'nota': 'la búsqueda no se dejó leer'}]}
            elif not pelis:
                C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'sin resultado', 'nota': 'sin fichas en la búsqueda'}]}
            else:
                C['filmaffinity'] = {'consultas': [linea('filmaffinity', 'https://www.' + p) for p in pelis]}
        except SinLeer as z:
            C['filmaffinity'] = {'consultas': [{'donde': u, 'resultado': 'no responde', 'nota': str(z)[:120]}]}
    if 'web' in clases:
        C['web'] = {'consultas': [viejo.get(('web', q)) or {'consulta': q} for q in consultas_web(ficha, [], dominios(festivales[k] for k in fs))]}


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
    red = {'web': leer_web, 'tmdb': _tmdb, 'buscar': _tmdb_buscar,
           'textos': lambda i: __import__('sello_fuente').leer_tmdb(i, os.environ.get('TMDB_API_KEY') or ''), **(red or {})}
    if festivales is None:
        from obra_unica import _festivales
        festivales = _festivales()
    fs = sorted(k for k, d in festivales.items() if f'"{w}"' in json.dumps(d))
    pub = so.publicadas({k: festivales[k] for k in fs}).get(w)
    if not fs:
        raise SystemExit(f'✗ {w}: ningún festival publica esa obra')
    ficha = ficha_de(w, {k: festivales[k] for k in fs}, pub)
    txs = textos(w, pub, so.originales().get(w))
    reg = {'work_id': w, 'fecha': datetime.date.today().isoformat(), 'festivales': fs, 'clases': {}}
    if not txs:
        reg['modo'] = 'sin texto'
        _descubrir(w, reg, fs, ficha, festivales, clases, red)
        reg['hallazgo'] = hallazgo(reg)
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
    if 'tmdb' in clases:
        if tm:
            C['tmdb'] = {'consultas': [_comprobar(txs, f'https://www.themoviedb.org/movie/{tm}', ficha, comprobar)]}
        else:           # sin número en la obra TAMBIÉN se busca: por título, con la dirección de los créditos
            try:
                n, suyas = _suyas(ficha, red)
                lin = []
                for x in suyas:
                    r = _comprobar(txs, f'https://www.themoviedb.org/movie/{x["id"]}', ficha, comprobar)
                    if r['resultado'] == 'ilegible':
                        r['nota'] = (r['nota'] + f' · el texto está en TMDB {x["id"]}, hallada por título y dirección: lo confirma una persona')[:300]
                    lin.append(r)
                    tm = tm or x['id']          # sus otras páginas (Letterboxd, IMDb) salen de esa ficha
                C['tmdb'] = {'consultas': lin or [{'donde': f'TMDB, búsqueda «{(ficha.get("titulos") or [""])[0]}»', 'resultado': 'sin resultado',
                                                   'nota': f'{n} ficha(s) con ese título; ninguna con la dirección de la obra'}]}
            except Exception as z:
                C['tmdb'] = {'consultas': [{'donde': 'TMDB', 'resultado': 'no responde', 'nota': str(z)[:120]}]}
    det = {}
    if tm:
        try:
            det = red['tmdb'](tm, '') or {}
            det['ids'] = red['tmdb'](tm, '/external_ids') or {}
        except Exception as z:
            det = {'error': str(z)[:120]}
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
    mas = lambda q: {k: q[k] for k in ('texto', 'idioma') if q.get(k)}
    for c, q in qs:
        if q.get('resultado') == 'literal':
            return {'clase': c, 'donde': q.get('url') or q.get('donde'), **mas(q)}
    for c, q in qs:
        if q.get('resultado') == 'ilegible' and ('el texto está' in (q.get('nota') or '') or q.get('texto')):
            return {'clase': c, 'donde': q.get('url') or q.get('donde'), 'a_mano': True, **mas(q)}
    return None


def incompleto(reg):
    """→ qué falta para que el registro diga «busqué en todo». [] = completo."""
    falta = []
    cl = reg.get('clases') or {}
    if cl and all('no aplica' in (cl.get(c) or {}) for c in CLASES):
        falta.append('ninguna clase se consultó: «no aplica» en todas no es una búsqueda')
    for c in CLASES:
        x = (reg.get('clases') or {}).get(c)
        if not x:
            falta.append(f'{c}: no se consultó')
        elif 'no aplica' in x:
            if not str(x['no aplica']).strip():
                falta.append(f'{c}: «no aplica» sin motivo')
            elif c in ('fuentes', 'instagram', 'tmdb', 'web'):
                falta.append(f'{c}: no admite «no aplica» (siempre se puede buscar por título)')
        elif not x.get('consultas'):
            falta.append(f'{c}: sin consultas')
        else:
            falta += [f'{c}: «{q.get("consulta") or q.get("donde")}» sin resultado anotado'
                      for q in x['consultas'] if q.get('resultado') not in RESULTADOS]
    return falta


def anotar(lote, comprobar=None, festivales=None):
    """Resultado de cada consulta web o de cada línea por leer. Un texto lo comprueba la máquina
    en el lugar que se dijo: nadie declara «literal» de palabra."""
    import sello_obra as so
    comprobar = comprobar or __import__('sello_fuente').comprobar
    todos = festivales if festivales is not None else __import__('obra_unica')._festivales()
    for e in lote:
        w, reg = e['work_id'], registro(e['work_id'])
        lineas = [(c, q) for c, x in (reg.get('clases') or {}).items() for q in x.get('consultas') or []]
        if not lineas:
            raise SystemExit(f'✗ {w}: primero buscar (sin consultas emitidas)')
        clave = e.get('consulta') or e.get('donde')
        c, q = next(((c, q) for c, q in lineas if clave and clave in (q.get('consulta'), q.get('donde'))), (None, None))
        if q is None:
            raise SystemExit(f'✗ {w}: «{clave}» no es una consulta emitida; se anotan las del código, tal cual')
        fuente = e.get('url') or (q.get('donde') if c != 'web' else None)
        if e.get('resultado') not in ('sin resultado', 'bloqueado', 'no responde') and not fuente:
            raise SystemExit(f'✗ {w}: un resultado que no es «sin resultado» lleva url')
        fest = {k: v for k, v in todos.items() if k in reg['festivales']}
        pub = so.publicadas(fest).get(w)
        txs, ficha = textos(w, pub, so.originales().get(w)), ficha_de(w, fest, pub)
        if not txs and not e.get('texto') and e.get('resultado') not in ('sin resultado', 'bloqueado', 'no responde'):
            raise SystemExit(f'✗ {w}: la obra no tiene texto: se anota «sin resultado» o el texto hallado (texto + dónde)')
        q.update({k: e[k] for k in ('resultado', 'url', 'nota') if e.get(k)})
        if not txs and e.get('texto'):          # obra sin texto: el hallado se comprueba ahí mismo
            r = _comprobar([('hallado', e['texto'])], fuente, ficha, comprobar) or {}
            q.update({'resultado': r.get('resultado', 'no está'), 'nota': ((e.get('nota') or '') + ' · máquina: ' + (r.get('nota') or ''))[:300],
                      'texto': e['texto'].strip(), 'idioma': e.get('idioma') or 'es'})
        elif e.get('url'):
            r = _comprobar(txs, e['url'], ficha, comprobar) or {}
            q.update({'resultado': r.get('resultado', 'no está'), 'nota': (e.get('nota') or '') + ' · máquina: ' + (r.get('nota') or '')})
            if e.get('texto'):
                q['texto_otro'] = e['texto'][:2000]     # otra sinopsis de la obra: sirve para reescribir, no para sellar
        reg['hallazgo'] = hallazgo(reg)
        _escribir(os.path.join(REGISTROS, w + '.json'), reg)
    return len(lote)


def pendiente(ws):
    """Lo que falta responder: consultas web y líneas por leer (con lo que sigue al título)."""
    return [{'work_id': w, **({'consulta': q['consulta']} if q.get('consulta') else {'clase': c, 'donde': q.get('donde'), **({'contexto': q['contexto']} if q.get('contexto') else {})})}
            for w in ws for c in CLASES for q in (registro(w).get('clases', {}).get(c) or {}).get('consultas') or [] if q.get('resultado') not in RESULTADOS]


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
    r5 = {'clases': {c: {'no aplica': 'la obra no publica sinopsis'} for c in CLASES}}
    if not incompleto(r5):
        mal.append('acepta «no aplica» en todas las clases: un registro completo sin haber buscado')
    r6 = json.loads(json.dumps(reg)); r6['clases']['tmdb'] = {'no aplica': 'la obra no tiene ficha TMDB'}
    if not incompleto(r6):
        mal.append('acepta TMDB «no aplica»: sin número también se busca por título')
    r7 = json.loads(json.dumps(reg)); r7['clases']['fuentes'] = {'consultas': [{'donde': 'fuentes/x/a.html', 'contexto': 'hush …'}]}
    if not incompleto(r7):
        mal.append('acepta una línea por leer sin resultado')
    n = _nombra({'titulos': ['Hush'], 'directores': ['Santiago Franco']})
    if n('programa hush de santiago franco') < 0 or n('hush puppies en oferta') >= 0 or n('hushed de franco') >= 0:
        mal.append('título de una palabra: debe pedir el apellido y la palabra entera')
    if _nombra({'titulos': ['Tejiendo un árbol'], 'directores': []})('selección tejiendo un árbol 12 min') < 0:
        mal.append('no reconoce un título de varias palabras sin dirección')
    r8 = json.loads(json.dumps(reg)); r8['clases']['tmdb'] = {'consultas': [{'donde': 'u', 'resultado': 'ilegible', 'texto': 'Una mujer vuelve.', 'nota': 'hallada por título'}]}
    if not ((hallazgo(r8) or {}).get('a_mano') and (hallazgo(r8) or {}).get('texto')):
        mal.append('un texto hallado sin número de TMDB no sale como hallazgo a confirmar')
    if not any('filmfreeway' in x for x in consultas_web({'titulos': ['La tinaja'], 'directores': ['Ana Pérez']}, [], [])):
        mal.append('una obra sin texto no recibe las consultas de descubrimiento')
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
        print(json.dumps(pendiente(a[1:]), ensure_ascii=False, indent=1))
    elif a[:1] == ['--medir']:
        ok, n = medir(int(a[1]))
        sys.exit(0 if ok * 10 >= n * 9 else 1)
    elif a[:1] == ['--sin-fuente']:
        print(declarar_sin_fuente(_leer(a[1], [])), 'declaradas sin fuente')
    elif a[:1] == ['--autoprueba']:
        m = autoprueba(); print('\n'.join(m) or 'OK'); sys.exit(bool(m))
    else:
        if not a or [w for w in a if not re.fullmatch(r'w_[0-9A-Z]+', w)]:      # «--help» dejó un registro llamado --help.json
            sys.exit(__doc__)
        for w in a:
            r = buscar(w)
            print(w, (r.get('hallazgo') or {}).get('donde') or 'sin hallazgo', '· falta: ' + '; '.join(incompleto(r)[:3]) if incompleto(r) else '· completo', sep=' ')
