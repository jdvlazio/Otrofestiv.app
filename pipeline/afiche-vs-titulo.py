# -*- coding: utf-8 -*-
"""afiche-vs-titulo.py <fest-id> [--aplicar] — el afiche dice un título; la ficha, otro.

Una obra se muestra con nuestro póster de TMDB, que a veces es el arte de
distribución en ESPAÑOL. Si el festival la titula en otro idioma, el afiche
dice «Hoja seca» en letras grandes y la ficha «Dry Leaf»: el usuario busca lo
que ve y no la encuentra (Cinemancia, auditoría A-8, 3 sep 2026).

El título de la ficha es CORRECTO por doctrina —así lo publica el festival— y
no se toca. Lo que falta es `title_es` (pipeline/contrato.json), que el
buscador mira además de `title` y `title_en` desde #833.

Cómo detecta, por obra con posterSource=tmdb + tmdb_id + póster en image.tmdb.org:
  1. pide a TMDB los pósters en español de esa obra (include_image_language=es)
     y comprueba que NUESTRO archivo de póster está entre ellos — el afiche
     que mostramos es, de verdad, el español;
  2. pide el título es-ES; si difiere del de la ficha y del title_en
     (comparando sin tildes ni puntuación, lib.norm), hay desajuste.
Sin las dos condiciones no hay nada que llenar: un afiche en inglés con título
en inglés está bien como está.

Con --aplicar escribe `title_es` (con su porqué) en el sidecar de TMDB del
festival, festivals/staging/<id>-tmdb.json, casando por tmdb_id. De ahí lo
lleva el ensamblador —_enriquece() en el genérico; el propio en TIFF— y el
festival se re-corre por su camino: python3 pipeline/correr.py <id>. NUNCA se
escribe sobre festivals/*.json: PROTOCOLO §5, «solo se publica lo que corrió
el runner».

Corre después del paso de TMDB y antes de publicar. Se repite en cada
festival con pósters de TMDB.
"""
import json, os, sys, time, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY en el entorno')


def tmdb(path, **params):
    params['api_key'] = K
    for _ in range(3):
        try:
            r = requests.get(f'https://api.themoviedb.org/3{path}', params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {}
        except Exception:
            pass
        time.sleep(1)
    return None            # red: distinto de «no hay», y se cuenta aparte


def _mismo_para_buscar(a, b):
    """¿Buscar por las palabras de `a` ya encuentra a `b`? Entonces no falta nada.

    Dos falsos positivos reales de la primera pasada (Cinemancia, 3 sep 2026):
      · «Vampir Cuadecuc» vs «Cuadecuc, vampir» — mismas palabras, otro orden.
      · «Refracción» vs «Refraction» — el festival YA titula en español; lo que
        TMDB devuelve como es-ES es el inglés. Escribir title_es ahí sería falso
        además de inútil: el contrato lo reserva para cuando el festival titula
        en OTRO idioma y el afiche dice el español.
    La prueba no es «¿son iguales?» sino «¿sirve el mismo teclazo?»: basta con
    que cada palabra de una tenga en la otra alguna que empiece igual."""
    pa = [w for w in norm(a).split() if len(w) >= 4]
    pb = [w for w in norm(b).split() if len(w) >= 4]
    if not pa or not pb:
        return False
    return all(any(x[:6] == y[:6] for y in pb) for x in pa)


def obras(fest):
    for f in fest['films']:
        for o in ([f] if not f.get('film_list') else f['film_list']):
            yield o


def detectar(fid):
    fest = json.load(open(f'{REPO}/festivals/{fid}.json', encoding='utf-8'))
    vistos, hallazgos, red = {}, [], 0
    for o in obras(fest):
        tid, p = o.get('tmdb_id'), str(o.get('poster') or '')
        if o.get('posterSource') != 'tmdb' or not tid or 'image.tmdb.org' not in p:
            continue
        archivo = '/' + p.rsplit('/', 1)[-1]
        if (tid, archivo) in vistos:
            continue
        vistos[(tid, archivo)] = True
        imgs = tmdb(f'/movie/{tid}/images', include_image_language='es')
        ficha = tmdb(f'/movie/{tid}', language='es-ES')
        if imgs is None or ficha is None:
            red += 1; continue
        es_posters = {x.get('file_path') for x in (imgs.get('posters') or [])}
        if archivo not in es_posters:
            continue
        t_es = (ficha.get('title') or '').strip()
        if not t_es or norm(t_es) == norm(o.get('title') or '') or norm(t_es) == norm(o.get('title_en') or ''):
            continue
        if _mismo_para_buscar(t_es, o.get('title') or ''):
            continue
        hallazgos.append({'tmdb_id': tid, 'title': o.get('title'), 'title_es': t_es, 'poster': archivo})
        time.sleep(0.15)
    return hallazgos, len(vistos), red


def aplicar(fid, hallazgos):
    p = f'{REPO}/festivals/staging/{fid}-tmdb.json'
    d = json.load(open(p, encoding='utf-8'))
    por_id = {}
    for x in d['obras']:
        i = x.get('tmdb_id') or x.get('tmdbId')
        if i:
            por_id.setdefault(int(i), x)
    escritas, sin_entrada = 0, []
    hoy = datetime.date.today().isoformat()
    for h in hallazgos:
        x = por_id.get(int(h['tmdb_id']))
        if not x:
            sin_entrada.append(h); continue
        x['title_es'] = h['title_es']
        x['_title_es_src'] = (f'afiche-vs-titulo.py {hoy}: el póster {h["poster"]} es arte en español '
                              f'en TMDB y su título es-ES difiere del que publica el festival')
        escritas += 1
    d.setdefault('_provenance', provenance('TMDB'))
    d['_provenance']['title_es'] = f'{escritas} escritos por pipeline/afiche-vs-titulo.py el {hoy}'
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return escritas, sin_entrada


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    fid = sys.argv[1]
    h, n, red = detectar(fid)
    print(f'{fid}: {n} pósters únicos de TMDB revisados · {len(h)} con el afiche en español y otro título'
          + (f' · {red} sin respuesta de red' if red else ''))
    for x in h:
        print(f"   «{x['title']}» → «{x['title_es']}»  (tmdb {x['tmdb_id']})")
    if '--aplicar' in sys.argv and h:
        e, sin = aplicar(fid, h)
        print(f'→ {e} title_es escritos en festivals/staging/{fid}-tmdb.json')
        for x in sin:
            print(f"   ⚠ sin entrada en el sidecar para tmdb {x['tmdb_id']} «{x['title']}» — no se escribió")
        print(f'→ ahora: re-correr el festival por su camino (correr.py {fid})')
