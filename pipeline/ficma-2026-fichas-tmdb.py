#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-fichas-tmdb.py — la ficha de las obras que agosto no tenía.

POR QUÉ NO SIRVE `enriquecer.py`. El genérico lee un crudo del formato
intermedio, y FICMA reprogramado no tiene crudo: su parrilla se arma post a
post (`ficma-2026-reprogramado.py`) y el catálogo se hereda congelado de la
edición de agosto. Las obras que el festival AÑADIÓ al reprogramar —las que no
estaban en agosto— entran sin póster, sin género y sin botón de Letterboxd.
Esto las busca en TMDB y rellena SOLO lo que falta; nunca pisa la ficha vieja,
donde viven correcciones hechas a mano.

EL CANDADO, Y POR QUÉ ES DISTINTO. `lib.ficha_verifica` exige director ✓ MÁS
año (±1) o duración (±3 min). Para un documental colombiano de 2026 recién
estrenado, TMDB suele tener la ficha con el título y el director y **sin fecha
de estreno ni duración**: el candado no puede abrirse y la obra se queda sin
nada, aunque la ficha sea evidentemente la suya. Acá se acepta un segundo
camino, más estrecho y declarado en el sidecar obra por obra:

    título IDÉNTICO (normalizado) + director ✓  →  válido solo si TMDB no
    publica ni año ni duración con qué contrastar.

Si TMDB SÍ los publica, manda el candado de siempre. La lección Tribeca sigue
en pie: lo que no verifica, no entra — pero «no verifica» no puede significar
«la fuente está incompleta».

Lee   festivals/staging/ficma-2026-reprogramado.json   (qué obras hay)
      festivals/staging/ficma-2026-catalogo-agosto.json (qué ya tenía ficha)
Esc.  festivals/staging/ficma-2026-fichas-tmdb.json
      assets/ficma/<slug>.jpg                          (póster w780)

Requiere TMDB_API_KEY en el entorno.
"""
import json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, director_coincide, ficha_verifica, norm, provenance, slug, tmdb_get

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/ficma'   # FICMA guarda sus pósters acá desde agosto
OUT = f'{ST}/ficma-2026-fichas-tmdb.json'

# Campos que esta pasada puede aportar. `synopsis` NO está: la sinopsis que
# publica el propio festival sobre su edición vale más que la de TMDB, y ya
# viene del post o de la web.
CAMPOS = ('tmdb_id', 'genre', 'title_en', 'synopsis_en', 'lbSlug', 'poster',
          'posterSource')


def lb_slug(tmdb_id):
    """El slug lo da Letterboxd por su propio mapeo; nunca se infiere."""
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'],
                       capture_output=True)
    s = r.stdout.decode().strip()
    return s.rsplit('/film/', 1)[-1].strip('/') if '/film/' in s else ''


def busca(obra, key):
    """La ficha de TMDB de esta obra, o None. El director se verifica SIEMPRE.

    Cuando las dos partes publican año o duración, decide el candado de
    siempre (`lib.ficha_verifica`). Cuando no hay con qué contrastar —el caso
    de la obra recién estrenada—, decide el título idéntico. Lo que quede se
    escribe en `_verificado`, que es donde se audita."""
    titulo, director = obra['titulo'], obra.get('director', '')
    for lang in ('es-ES', 'en-US'):
        res = tmdb_get('/search/movie', key, query=titulo, language=lang,
                       include_adult='false')
        for c in (res.get('results') or [])[:6]:
            det = tmdb_get(f"/movie/{c['id']}", key, language='es-ES',
                           append_to_response='credits')
            det_en = tmdb_get(f"/movie/{c['id']}", key, language='en-US',
                              append_to_response='credits')
            # los créditos en-US vienen romanizados: sin ellos hay directores
            # que nunca casan
            det.setdefault('credits', {}).setdefault('crew', []).extend(
                det_en.get('credits', {}).get('crew', []))
            dirs = [p['name'] for p in det['credits']['crew']
                    if p.get('job') == 'Director']
            if not director_coincide(director, dirs):
                continue
            if not (norm(det.get('title') or '') == norm(titulo)
                    or norm(det.get('original_title') or '') == norm(titulo)):
                continue
            anio = int((det.get('release_date') or '0')[:4] or 0)
            dur = det.get('runtime') or 0
            nuestro = {'director': director, 'anio': obra.get('anio'),
                       'duracion_min': obra.get('duracion_min')}
            contrastable = (anio or dur) and (nuestro['anio'] or nuestro['duracion_min'])
            if contrastable:
                if not ficha_verifica(nuestro, det):
                    continue
                como = f'director ✓ + año/duración (TMDB: {anio or "?"}, {dur or "?"} min)'
            else:
                como = ('director ✓ + título idéntico; no hay año ni duración '
                        'en ambos lados con qué contrastar')
            return det, det_en, como
    return None


def baja_poster(poster_path, titulo):
    """w780 a assets/ficma/<slug>.jpg. Devuelve la ruta pública o ''."""
    os.makedirs(ASSETS, exist_ok=True)
    dest = f'{ASSETS}/{slug(titulo)}.jpg'
    if not os.path.exists(dest) or os.path.getsize(dest) < 5000:
        # el CDN de TMDB corta la conexión de vez en cuando; se reintenta en vez
        # de dejar el archivo a medias (y a medias es peor que ausente: un .jpg
        # truncado pasa por existente y la app pinta un hueco)
        for intento in range(4):
            try:
                req = urllib.request.Request(
                    f'https://image.tmdb.org/t/p/w780{poster_path}',
                    headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    datos = r.read()
                if len(datos) < 5000:
                    raise OSError(f'póster de {len(datos)} bytes: truncado')
                open(dest, 'wb').write(datos)
                break
            except Exception as e:
                if intento == 3:
                    print(f'    ⚠ sin póster para «{titulo}»: {e}', flush=True)
                    return ''
                time.sleep(2 * (intento + 1))
    return f'/assets/ficma/{os.path.basename(dest)}'


def main():
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')
    rep = json.load(open(f'{ST}/ficma-2026-reprogramado.json', encoding='utf-8'))
    cat = json.load(open(f'{ST}/ficma-2026-catalogo-agosto.json',
                         encoding='utf-8'))['obras']
    tenia = {norm(t): o for t, o in cat.items()}

    obras = {}
    for f in rep['funciones']:
        if f.get('tipo') in ('taller', 'charla'):
            continue
        obras.setdefault(f['titulo'], f)

    fichas, sin = {}, []
    for titulo, obra in sorted(obras.items()):
        vieja = tenia.get(norm(titulo), {})
        faltan = [c for c in CAMPOS if not vieja.get(c)]
        if not faltan:
            continue
        r = busca(obra, key)
        time.sleep(0.2)
        if not r:
            sin.append(titulo)
            print(f'—   {titulo[:46]:48} sin ficha verificable en TMDB', flush=True)
            continue
        det, det_en, como = r
        e = {'tmdb_id': det['id'], '_verificado': como}
        if 'genre' in faltan and det.get('genres'):
            e['genre'] = det['genres'][0]['name']
        if 'synopsis_en' in faltan and det_en.get('overview'):
            e['synopsis_en'] = det_en['overview']
        en = det_en.get('title') or ''
        if 'title_en' in faltan and en and norm(en) != norm(titulo):
            e['title_en'] = en
        if 'poster' in faltan and det.get('poster_path'):
            ruta = baja_poster(det['poster_path'], titulo)
            if ruta:
                e['poster'], e['posterSource'] = ruta, 'tmdb'
        if 'lbSlug' in faltan:
            sl = lb_slug(det['id'])
            if sl:
                e['lbSlug'] = sl
        fichas[titulo] = e
        print(f'OK  {titulo[:46]:48} tmdb {det["id"]}'
              f'{"  póster✓" if e.get("poster") else ""}'
              f'{"  lb✓" if e.get("lbSlug") else ""}', flush=True)

    json.dump({'_provenance': provenance(
        'TMDB (api.themoviedb.org) + Letterboxd por el redirect /tmdb/<id>',
        que_aporta='póster, género, título en inglés, sinopsis EN y lbSlug de las '
                   'obras que la edición de agosto no tenía',
        candado='director ✓ SIEMPRE, más título idéntico. Cada ficha dice en '
                '`_verificado` con qué se comprobó.'),
        'fichas': fichas, 'sin_ficha': sin},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(fichas)} fichas · {len(sin)} sin ficha verificable')
    for s in sin:
        print('   ·', s)


if __name__ == '__main__':
    main()
