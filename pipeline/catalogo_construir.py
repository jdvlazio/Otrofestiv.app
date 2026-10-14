#!/usr/bin/env python3
"""catalogo_construir.py — fase 1 del catálogo único (docs/CATALOGO-OBRAS.md).

MODO SIMULACIÓN por defecto: lee los 32 festivales publicados, agrupa sus obras
y escribe INFORMES en una carpeta de trabajo (--salida), nunca en catalogo/.
Nada se publica ni se fusiona solo.

El reconocimiento tiene TRES salidas (EIDR / DAMA-DMBOK):
  · COINCIDE   — mismo tmdb_id o slug de Letterboxd; o misma huella de título + mismo apellido de
                 director + año ±1 (o año ausente en uno de los dos lados).
  · CANDIDATO  — va a Juan: misma huella y una fuente sin director; o mismo
                 director y año con título parecido (≥ 0,85, traducciones/akas);
                 o misma huella y director pero años a más de 1 de distancia.
  · NO COINCIDE — todo lo demás (homónimos, remakes).
Un candidato NUNCA se une solo: queda en candidatos.json hasta que Juan decida.

    python3 pipeline/catalogo_construir.py --salida <carpeta>
    TMDB_API_KEY=… python3 pipeline/catalogo_construir.py --escribir

--escribir (fase 3) materializa catalogo/obras/, procedencia/ y decisiones.json.
Re-correrlo es idempotente: cada grupo conserva el id de la obra que ya lo
contenía (catalogo.obra_de), y las decisiones ya guardadas mandan.
"""
import difflib
import glob
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogo  # noqa: E402
from catalogo import huella, apellido  # noqa: E402
from lib import sinacento, banderas, tmdb_ficha  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UMBRAL = 0.85


def registros():
    """Cada obra publicada, con su festival. Las de dentro de los programas de
    cortos también; las actividades no."""
    out = []
    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        try:
            d = json.load(io.open(p, encoding='utf-8'))
        except Exception:
            continue
        for f in d.get('films', []):
            if f.get('type') == 'event':
                continue
            for o in (f.get('film_list') if f.get('film_list') else [f]):
                if o.get('type') == 'event' or not o.get('title'):
                    continue
                dur = re.match(r'\d+', str(o.get('duration') or ''))
                anio = o.get('year')
                out.append({'fest': fid, 'titulo': o['title'], 'director': (o.get('director') or '').strip(),
                            'anio': int(anio) if str(anio or '').isdigit() else None,
                            'duracion': int(dur.group()) if dur else None,
                            'pais': o.get('country'), 'tmdb': o.get('tmdb_id'),
                            'lb': o.get('lbSlug') if re.fullmatch(r'[a-z0-9-]+', str(o.get('lbSlug') or '')) else None,   # «⚠️ LB PENDIENTE» no es un slug
                            'poster': o.get('poster'), 'sinopsis': o.get('synopsis'),
                            'sinopsis_en': o.get('synopsis_en'), 'title_en': o.get('title_en'),
                            'genero': (o.get('genre') or '').strip() or None,
                            'anteriores': list(o.get('titulos_anteriores') or [])})
    return out


class Uniones:
    def __init__(self, n):
        self.p = list(range(n))

    def raiz(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def une(self, a, b):
        self.p[self.raiz(a)] = self.raiz(b)


def _anio_ok(a, b):
    return a is None or b is None or abs(a - b) <= 1


def construir(R):
    U = Uniones(len(R))
    for r in R:
        r['_h'], r['_ap'] = huella(r['titulo']), apellido(r['director'])
    # 1. mismo tmdb_id
    por_tmdb = defaultdict(list)
    for i, r in enumerate(R):
        if r['tmdb']:
            por_tmdb[r['tmdb']].append(i)
    for ids in por_tmdb.values():
        for j in ids[1:]:
            U.une(ids[0], j)
    # 1b. mismo slug de Letterboxd: también es un xref (salvo dos tmdb distintos)
    por_lb = defaultdict(list)
    for i, r in enumerate(R):
        if r['lb']:
            por_lb[r['lb']].append(i)
    for ids in por_lb.values():
        for j in ids[1:]:
            if not (R[ids[0]]['tmdb'] and R[j]['tmdb'] and R[ids[0]]['tmdb'] != R[j]['tmdb']):
                U.une(ids[0], j)
    # 2. misma huella + mismo apellido + año compatible
    por_h = defaultdict(list)
    for i, r in enumerate(R):
        if r['_h']:
            por_h[r['_h']].append(i)
    candidatos = []
    for h, ids in por_h.items():
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = R[ids[x]], R[ids[y]]
                if a['tmdb'] and b['tmdb'] and a['tmdb'] != b['tmdb']:
                    continue                      # dos fichas distintas: no es la misma
                if a['fest'] == b['fest']:
                    U.une(ids[x], ids[y])         # un festival no repite título para dos obras
                    continue
                if a['_ap'] and b['_ap']:
                    if a['_ap'] != b['_ap']:
                        continue                  # homónimos
                    if _anio_ok(a['anio'], b['anio']):
                        U.une(ids[x], ids[y])
                    else:
                        candidatos.append((ids[x], ids[y], f'mismo título y director, años {a["anio"]} y {b["anio"]}'))
                elif (a['duracion'] and b['duracion'] and abs(a['duracion'] - b['duracion']) <= 3) or \
                        (a['anio'] and b['anio'] and abs(a['anio'] - b['anio']) <= 1):
                    U.une(ids[x], ids[y])         # sin director en un lado, pero duración o año lo corroboran (regla de lib.ya_publicada)
                else:
                    candidatos.append((ids[x], ids[y], 'mismo título; una fuente sin director'))
    # 3. mismo director + año, título parecido (traducción / aka): solo candidato
    por_bloque = defaultdict(list)
    for i, r in enumerate(R):
        if r['_ap'] and r['anio']:
            por_bloque[(r['_ap'], r['anio'])].append(i)
    for ids in por_bloque.values():
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = R[ids[x]], R[ids[y]]
                if U.raiz(ids[x]) == U.raiz(ids[y]) or a['_h'] == b['_h']:
                    continue
                s = difflib.SequenceMatcher(None, a['_h'], b['_h']).ratio()
                if s >= UMBRAL:
                    candidatos.append((ids[x], ids[y], f'mismo director y año, títulos parecidos ({s:.2f})'))
    # 4. las decisiones de identidad ya tomadas (catalogo/revision-fase2.json):
    #    «sí» une; «no» queda registrado y el par no se vuelve a preguntar
    rev_p = os.path.join(REPO, 'catalogo', 'revision-fase2.json')
    no_es = set()
    if os.path.exists(rev_p):
        idx = defaultdict(list)
        for i, r in enumerate(R):
            idx[(r['fest'], r['titulo'])].append(i)
        for d in json.load(io.open(rev_p, encoding='utf-8')).get('identidad', []):
            ia, ib = idx.get(tuple(d['a'])), idx.get(tuple(d['b']))
            if not ia or not ib:
                sys.exit(f'✗ decisión de identidad sobre una obra que no está publicada: {d["a"]} / {d["b"]}')
            if d['misma']:
                U.une(ia[0], ib[0])
            else:
                no_es.add(tuple(sorted((U.raiz(ia[0]), U.raiz(ib[0])))))
    # los candidatos que ya quedaron unidos, o que ya se decidió que no son la
    # misma obra, no se preguntan
    vistos, cand = set(), []
    for x, y, por in candidatos:
        k = tuple(sorted((U.raiz(x), U.raiz(y))))
        if k[0] == k[1] or k in vistos or k in no_es:
            continue
        vistos.add(k)
        cand.append((x, y, por))
    grupos = defaultdict(list)
    for i in range(len(R)):
        grupos[U.raiz(i)].append(i)
    return list(grupos.values()), cand


def _dir(s):
    return re.sub(r'[^a-z ]', '', sinacento(s or '').lower()).strip()


def contradicciones(R, grupo):
    """Lo que la misma obra dice distinto en cada festival."""
    out = {}
    for campo, norma in (('director', _dir), ('anio', lambda v: v), ('pais', lambda v: v)):
        vals = {R[i]['fest']: R[i][campo] for i in grupo if R[i][campo] not in (None, '')}
        if len({norma(v) for v in vals.values()}) > 1:
            out[campo] = vals
    durs = {R[i]['fest']: R[i]['duracion'] for i in grupo if R[i]['duracion']}
    if durs and max(durs.values()) - min(durs.values()) > 3:
        out['duracion (va a versiones)'] = durs
    tm = {R[i]['fest']: R[i]['tmdb'] for i in grupo if R[i]['tmdb']}
    if len(set(tm.values())) > 1:
        out['tmdb'] = tm
    return out


# ── fase 3: materializar ────────────────────────────────────────────────────
def _iso(pais):
    """«Colombia, Francia» → ['CO', 'FR'] (por la bandera: dos letras regionales)."""
    return [''.join(chr(ord(c) - 0x1F1E6 + 65) for c in f) for f in banderas(pais or '')]


def _directores(s):
    return [d.strip() for d in re.split(r',| y | & |/', s or '') if d.strip()]


def _tildes(s):
    return sum(1 for c in s if ord(c) > 127)


def _tmdb(tid, key, cache):
    if tid not in cache:
        # por id: una ficha vacía por la red escribía año, país y director de
        # festival como si TMDB no los tuviera (lib.tmdb_ficha, 14 oct 2026)
        m = tmdb_ficha(tid, key, append_to_response='credits') if key else {}
        cache[tid] = {'anio': int(m['release_date'][:4]) if (m.get('release_date') or '')[:4].isdigit() else None,
                      'paises': [c['iso_3166_1'] for c in m.get('production_countries') or []],
                      'directores': [c['name'] for c in (m.get('credits') or {}).get('crew', []) if c.get('job') == 'Director']}
    return cache[tid]


def materializar(R, grupos, key, cache):
    """Un grupo → una obra, con la supervivencia de §4.2 y procedencia por campo."""
    obs_viejas = catalogo.obras()
    rev = json.load(io.open(os.path.join(REPO, 'catalogo', 'revision-fase2.json'), encoding='utf-8'))
    hoy = rev['fecha']
    nuevas, proc, usados = {}, {}, set()
    fus = catalogo.fusiones()
    for g in grupos:
        regs = [R[i] for i in g]
        # con sus títulos anteriores: un renombre conserva el id (FICPA, 13 oct)
        viejos = sorted({w for w in (catalogo.obra_de(obs_viejas, r['fest'], t, r['tmdb'])
                                     for r in regs for t in [r['titulo']] + r['anteriores']) if w})
        wid = viejos[0] if viejos else None
        for w in viejos[1:]:            # dos obras de ayer son hoy la misma: un id nunca se borra, se redirige
            fus.append({'absorbido': w, 'superviviente': wid, 'fecha': hoy, 'motivo': 'el constructor las reconoce como la misma obra'})
        if not wid or wid in usados:
            wid = catalogo.nuevo_id()
            while wid in usados or wid in obs_viejas:
                wid = catalogo.nuevo_id()
        usados.add(wid)
        pr = {}
        titulos = defaultdict(list)
        for r in regs:
            titulos[r['titulo']].append(r['fest'])
        titulo = max(titulos, key=lambda t: (len(titulos[t]), _tildes(t), -len(t)))
        pr['titulo_original'] = {'fuente': 'festival:' + ','.join(sorted(titulos[titulo])), 'regla': 'el título que más festivales imprimen'}
        tm = sorted({r['tmdb'] for r in regs if r['tmdb']})
        t = _tmdb(tm[0], key, cache) if len(tm) == 1 else None
        dirs = max((_directores(r['director']) for r in regs), key=lambda d: (len(d) > 0, _tildes(' '.join(d)), len(' '.join(d))))
        pr['directores'] = {'fuente': 'festival', 'regla': 'la grafía más completa que acreditan los festivales'}
        if t and t['directores'] and [_dir(x) for x in t['directores']] != [_dir(x) for x in dirs]:
            if sorted(_dir(x) for x in t['directores']) != sorted(_dir(x) for x in dirs):
                dirs = t['directores']
                pr['directores'] = {'fuente': f'tmdb:{tm[0]}', 'regla': 'tmdb-manda'}
        anios = sorted({r['anio'] for r in regs if r['anio']})
        anio = anios[0] if anios else None
        pr['anio'] = {'fuente': 'festival', 'regla': 'anio-mas-temprano' if len(anios) > 1 else 'único'}
        if t and t['anio']:
            anio = t['anio']
            pr['anio'] = {'fuente': f'tmdb:{tm[0]}', 'regla': 'tmdb-manda'}
        paises = []
        for r in regs:
            paises += [c for c in _iso(r['pais']) if c not in paises]
        pr['paises'] = {'fuente': 'festival', 'regla': 'pais-union'}
        if t and t['paises']:
            paises = t['paises']
            pr['paises'] = {'fuente': f'tmdb:{tm[0]}', 'regla': 'tmdb-manda'}
        o = {'id': wid, 'titulo_original': titulo, 'anio': anio, 'paises': paises, 'directores': dirs}
        al = [{'titulo': x, 'tipo': 'festival'} for x in sorted(set(titulos) | {a for r in regs for a in r['anteriores']}) if x != titulo]
        al += [{'titulo': x, 'idioma': 'en', 'tipo': 'traduccion'} for x in sorted({r['title_en'] for r in regs if r.get('title_en')}) if x != titulo]
        if al:
            o['aliases'] = al
        sin = {k: v for k, v in (('es', next((r['sinopsis'] for r in regs if r['sinopsis']), None)),
                                 ('en', next((r['sinopsis_en'] for r in regs if r['sinopsis_en']), None))) if v}
        if sin:
            o['sinopsis'] = sin
        # EL GÉNERO, tal como lo publicó cada festival (14 oct 2026). No estaba en
        # la obra: el «Drama» de La paga en Cinemancia 2025 no llegaba a FILCMAR
        # ni a MUBI, que salían sin género porque TMDB no lo tiene. Se guardan
        # TODOS los distintos, del más publicado al menos: los festivales no
        # coinciden («Drama» / «Ficción», «Animation», hasta un país), y elegir
        # uno acá sería decidir por ellos. Quien lo hereda decide (enriquecer.py)
        _gen = {}
        for r in regs:
            if r.get('genero'):
                _gen[r['genero']] = _gen.get(r['genero'], 0) + 1
        if _gen:
            o['generos'] = sorted(_gen, key=lambda g: -_gen[g])
            pr['generos'] = {'fuente': 'festival', 'regla': 'todos los publicados, del más al menos frecuente'}
        af = next((r['poster'] for r in regs if r['poster']), None)
        if af:
            o['afiche'] = {'archivo': af}
        lb = next((r['lb'] for r in regs if r['lb']), None)
        o['xref'] = {k: v for k, v in (('tmdb', tm[0] if len(tm) == 1 else None), ('letterboxd', lb)) if v}
        durs = sorted({r['duracion'] for r in regs if r['duracion']})
        if durs:
            o['versiones'] = [{'etiqueta': f'{d} min', 'duracion_min': d} for d in durs]
        o['presentaciones'] = sorted({r['fest'] for r in regs})
        nuevas[wid], proc[wid] = o, pr
    # las decisiones de la revisión, por título → por work_id
    decs = [d for d in catalogo.decisiones()]
    ya = {(d['work_id'], d['campo']) for d in decs}
    for d in rev['datos']:
        wids = [w for w, o in nuevas.items() if huella(d['obra']) in {huella(o['titulo_original'])} | {huella(a['titulo']) for a in o.get('aliases', [])}]
        if len(wids) > 1:            # las decisiones salieron de la hoja de contradicciones: obras en varios festivales
            wids = [w for w in wids if len(nuevas[w]['presentaciones']) > 1]
        if len(wids) != 1:
            sys.exit(f'✗ la decisión sobre «{d["obra"]}» no apunta a UNA obra ({len(wids)})')
        if (wids[0], d['campo']) not in ya:
            decs.append({'work_id': wids[0], 'campo': d['campo'], 'valor': d['valor'], 'motivo': d['motivo'],
                         'fecha': hoy, 'quien': rev['quien']})
    for d in rev['identidad']:
        if not d['misma']:
            a = catalogo.obra_de(nuevas, *d['a']); b = catalogo.obra_de(nuevas, *d['b'])
            if (a, 'no-es') not in ya:
                decs.append({'work_id': a, 'campo': 'no-es', 'valor': b, 'motivo': d['motivo'], 'fecha': hoy, 'quien': rev['quien']})
    # prioridad máxima: la decisión humana
    reemplazadas = {d.get('reemplaza') for d in decs}
    for i, d in enumerate(decs):
        if i in reemplazadas or d['campo'] in ('no-es', 'no-alta-tmdb') or d['work_id'] not in nuevas:
            continue
        o = nuevas[d['work_id']]
        partes = d['campo'].split('.')
        for k in partes[:-1]:
            o = o.setdefault(k, {})
        o[partes[-1]] = d['valor']
        proc[d['work_id']][d['campo']] = {'fuente': 'humano', 'regla': 'decisión', 'motivo': d['motivo'], 'fecha': d['fecha']}
    return nuevas, proc, decs, fus


def escribir(R, grupos):
    key = os.environ.get('TMDB_API_KEY')
    if not key:
        sys.exit('falta TMDB_API_KEY (source ~/.zshrc)')
    cp = os.path.expanduser('~/.cache/otrofestiv/catalogo-tmdb.json')   # fuera del repo
    cache = {int(k): v for k, v in json.load(io.open(cp, encoding='utf-8')).items()} if os.path.exists(cp) else {}
    try:
        obs, proc, decs, fus = materializar(R, grupos, key, cache)
    finally:
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        json.dump(cache, io.open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
    for sub in ('obras', 'procedencia'):
        d = os.path.join(REPO, 'catalogo', sub)
        for p in glob.glob(f'{d}/w_*.json'):
            if os.path.basename(p)[:-5] not in obs:
                os.remove(p)             # una obra que ya no existe se redirige por fusión, no queda colgando
    for wid, o in obs.items():
        json.dump(o, io.open(f'{REPO}/catalogo/obras/{wid}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(proc[wid], io.open(f'{REPO}/catalogo/procedencia/{wid}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(fus, io.open(f'{REPO}/catalogo/fusiones.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(decs, io.open(f'{REPO}/catalogo/decisiones.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # la presentación apunta a su obra (fase 3b): solo se agrega `work_id`
    ix, sin_resolver = catalogo.indice(obs), []
    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        crudo = io.open(p, encoding='utf-8').read()
        d = json.loads(crudo)
        sin_resolver += [(fid, t) for t in catalogo.enlazar(d, fid, obs, ix)]
        # el mismo formato que ya tiene el archivo: el diff es solo `work_id`
        compacto = json.dumps(json.loads(crudo), ensure_ascii=False, separators=(',', ':')) == crudo.rstrip('\n')
        nuevo = json.dumps(d, ensure_ascii=False, **({'separators': (',', ':')} if compacto else {'indent': 1}))
        nuevo += '\n' if crudo.endswith('\n') else ''
        if nuevo != crudo:
            io.open(p, 'w', encoding='utf-8').write(nuevo)
    print(f'✓ {len(obs)} obras, {len(decs)} decisiones; {len(sin_resolver)} presentaciones sin obra única')
    for x in sin_resolver[:20]:
        print('  ·', x)


def main():
    if '--escribir' in sys.argv:
        R = registros()
        grupos, cand = construir(R)
        if cand:
            sys.exit(f'✗ {len(cand)} candidatos sin resolver: primero la revisión (--salida)')
        return escribir(R, grupos)
    if '--salida' not in sys.argv:
        sys.exit('uso: catalogo_construir.py --salida <carpeta>  (simulación: nunca escribe catalogo/)')
    sal = sys.argv[sys.argv.index('--salida') + 1]
    if os.path.abspath(sal).startswith(os.path.join(REPO, 'catalogo')):
        sys.exit('✗ la simulación no escribe en catalogo/')
    os.makedirs(sal, exist_ok=True)
    R = registros()
    grupos, cand = construir(R)
    multi = [g for g in grupos if len({R[i]['fest'] for i in g}) > 1]
    contra = [(g, contradicciones(R, g)) for g in multi]
    contra = [(g, c) for g, c in contra if c]
    fmt = lambda i: {k: R[i][k] for k in ('fest', 'titulo', 'director', 'anio', 'duracion', 'tmdb')}
    json.dump([{'a': fmt(x), 'b': fmt(y), 'por_que': por} for x, y, por in cand],
              io.open(f'{sal}/candidatos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump([{'obra': R[g[0]]['titulo'], 'festivales': sorted({R[i]['fest'] for i in g}), 'difiere': c}
               for g, c in sorted(contra, key=lambda gc: -len(gc[0]))],
              io.open(f'{sal}/contradicciones.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    resumen = {'registros': len(R), 'obras': len(grupos), 'en_varios_festivales': len(multi),
               'con_contradicciones': len(contra), 'candidatos': len(cand),
               'sin_tmdb': sum(1 for g in grupos if not any(R[i]['tmdb'] for i in g)),
               'por_motivo': {m: sum(1 for *_, p in cand if p.startswith(m)) for m in
                              ('mismo título y director', 'mismo título; una fuente', 'mismo director y año')}}
    json.dump(resumen, io.open(f'{sal}/resumen.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
