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

EL CANDADO vive en `lib.ficha_tmdb`, que es de donde lo toma también Villa del
Cine: director ✓ SIEMPRE, y año/duración cuando las dos partes los publican.
Cada ficha guarda en `_verificado` con qué se comprobó.

Lee   festivals/staging/ficma-2026-crudo-septiembre.json (qué obras hay: la
      parrilla oficial; antes del 18 sep era la lista armada post a post)
      festivals/staging/ficma-2026-catalogo-agosto.json (qué ya tenía ficha)
Esc.  festivals/staging/ficma-2026-fichas-tmdb.json
      assets/ficma/<slug>.jpg                          (póster w780)

Requiere TMDB_API_KEY en el entorno.
"""
import json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, ficha_tmdb, norm, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/ficma'   # FICMA guarda sus pósters acá desde agosto
OUT = f'{ST}/ficma-2026-fichas-tmdb.json'

# Campos que esta pasada puede aportar. `synopsis` va al final a propósito: la
# que publica el propio festival sobre su edición vale más y se aplica después,
# pero una obra que no tiene sinopsis en NINGUNA parte se queda muda en la app
# teniendo TMDB la suya. [cosecha-tmdb] lo vigila: el dato estaba en la fuente y
# no cosecharlo es la misma pérdida que no haber mirado.
CAMPOS = ('tmdb_id', 'genre', 'title_en', 'synopsis', 'synopsis_en', 'lbSlug',
          'poster', 'posterSource')


def lb_slug(tmdb_id):
    """El slug lo da Letterboxd por su propio mapeo; nunca se infiere."""
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'],
                       capture_output=True)
    s = r.stdout.decode().strip()
    return s.rsplit('/film/', 1)[-1].strip('/') if '/film/' in s else ''


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
    rep = json.load(open(f'{ST}/ficma-2026-crudo-septiembre.json', encoding='utf-8'))
    cat = json.load(open(f'{ST}/ficma-2026-catalogo-agosto.json',
                         encoding='utf-8'))['obras']
    tenia = {norm(t): o for t, o in cat.items()}

    obras = {}
    for f in rep['funciones']:
        # las cinco actividades de maqueta centrada no son obra: no tienen
        # dirección ni año, y buscarlas en TMDB solo puede traer un homónimo
        if f.get('maqueta') == 'centrada':
            continue
        obras.setdefault(f['titulo'], f)

    fichas, sin = {}, []
    for titulo, obra in sorted(obras.items()):
        vieja = tenia.get(norm(titulo), {})
        faltan = [c for c in CAMPOS if not vieja.get(c)]
        if not faltan:
            continue
        r = ficha_tmdb(obra, key)
        time.sleep(0.2)
        if not r:
            sin.append(titulo)
            print(f'—   {titulo[:46]:48} sin ficha verificable en TMDB', flush=True)
            continue
        det, det_en, como = r
        e = {'tmdb_id': det['id'], '_verificado': como}
        if 'genre' in faltan and det.get('genres'):
            e['genre'] = det['genres'][0]['name']
        if 'synopsis' in faltan and det.get('overview'):
            e['synopsis'], e['synopsis_lang'] = det['overview'], 'es'
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

    # Si NADIE casó, no es que el festival haya programado 43 obras inéditas:
    # es que la consulta está rota. Antes de escribir el sidecar —que es lo que
    # pisa las fichas buenas— se para.
    if obras and not fichas:
        sys.exit(f'ninguna de las {len(obras)} obras casó en TMDB: eso no es un '
                 f'resultado, es una consulta rota. No se escribe el sidecar.')

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
