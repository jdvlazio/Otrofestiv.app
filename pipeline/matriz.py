"""matriz.py — la matriz del catálogo, para mirarla (14 oct 2026).

El catálogo vive en 2.145 JSON, uno por obra: sirve a la máquina y nadie lo
puede recorrer. Esto arma la vista de Juan: una fila por obra con lo que
publicó cada festival, campo por campo, para ver las obras repetidas del
circuito, los huecos (uno lo tiene, otro no) y los datos que no coinciden.
La página es pipeline/matriz.html, que lee el matriz.json de al lado; se
publica como Artifact (no va a otrofestiv.app). Es un DERIVADO: no se
versiona, se regenera después de cada publicación (PROTOCOLO §3).

Uso: python3 pipeline/matriz.py [salida.json]   (por omisión, /tmp/matriz.json)"""
import glob
import json
import os
import sys

CAMPOS = ('director', 'year', 'country', 'duration', 'genre', 'title_en',
          'synopsis', 'synopsis_en', 'poster', 'lbSlug')

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
salida = sys.argv[1] if len(sys.argv) > 1 else '/tmp/matriz.json'
obras = {}
for p in glob.glob(f'{raiz}/catalogo/obras/*.json'):
    o = json.load(open(p, encoding='utf-8'))
    obras[o['id']] = o

# nombre corto de cada festival, del propio JSON
fest = {}
pres = {}
for p in sorted(glob.glob(f'{raiz}/festivals/*.json')):
    fid = os.path.basename(p)[:-5]
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(d, dict) or 'films' not in d:
        continue
    fest[fid] = {'n': d.get('displayName') or d.get('name') or fid,
                 'a': d.get('year'), 'c': d.get('city') or ''}
    for f in d['films']:
        if f.get('type') == 'event':
            continue
        for o in (f.get('film_list') or [f]):
            w = o.get('work_id')
            if not w or o.get('type') == 'event':
                continue
            k = (w, fid)
            r = pres.setdefault(k, {'t': o.get('title'), 'n': 0, 'v': {}})
            r['n'] += 1
            for c in CAMPOS:
                v = o.get(c)
                if c == 'poster':
                    v = ('fotograma' if o.get('posterSource') == 'editorial' else 'afiche') if v else None
                elif c in ('synopsis', 'synopsis_en'):
                    v = (v or '').strip()[:60] or None
                if v and c not in r['v']:
                    r['v'][c] = str(v)

filas = []
for w, o in obras.items():
    ps = [(fid, r) for (ww, fid), r in pres.items() if ww == w]
    if not ps:
        continue
    # por campo: cuántos festivales lo tienen y si los valores difieren
    est = {}
    for c in CAMPOS:
        vals = [r['v'].get(c) for _, r in ps]
        con = [v for v in vals if v]
        # el país, sin orden ni mayúsculas: «Colombia, Venezuela» = «Venezuela, Colombia»
        if c == 'country':
            con = [', '.join(sorted(x.strip().lower() for x in v.split(','))) for v in con]
        if c == 'poster':
            con = [v for v in con if v == 'afiche']
        distintos = len({v for v in con}) > 1 and c not in ('synopsis', 'synopsis_en', 'poster')
        est[c] = [len(con), len(ps) - len(con), 1 if distintos else 0]
    filas.append({
        'id': w,
        't': o.get('titulo_original'),
        'al': [a['titulo'] for a in o.get('aliases') or []][:4],
        'd': ', '.join(o.get('directores') or []),
        'a': o.get('anio'),
        'p': o.get('paises') or [],
        'g': o.get('generos') or [],
        'tm': (o.get('xref') or {}).get('tmdb'),
        'lb': (o.get('xref') or {}).get('letterboxd'),
        # el tipo de afiche (oficial / del festival / fotograma) llegó al catálogo
        # el 14 oct; sin él, que haya archivo ya dice que tiene
        'af': (o.get('afiche') or {}).get('veredicto') or ('afiche' if (o.get('afiche') or {}).get('archivo') else None),
        'e': est,
        'pr': [{'f': fid, 't': r['t'], 'n': r['n'], 'v': r['v']} for fid, r in
               sorted(ps, key=lambda x: (fest[x[0]]['a'] or 0, x[0]))],
    })

filas.sort(key=lambda x: (-len(x['pr']), x['t'] or ''))
json.dump({'campos': CAMPOS, 'festivales': fest, 'obras': filas},
          open(salida, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
rep = sum(1 for x in filas if len(x['pr']) > 1)
print(f'{len(filas)} obras · {rep} en 2+ festivales · {len(fest)} festivales · '
      f'{os.path.getsize(salida) // 1024} KB')
