#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-fichas-tmdb.py — lo que TMDB sepa de estos 53 cortos.

EL PROBLEMA. El festival publica «🎬 Título – Dir. Nombre» y nada más: ni año,
ni duración, ni país, ni sinopsis. Con eso no se puede armar una ficha, y el
plan de este festival lo decía como un pendiente («es lo primero que hay que
pedirle al festival»). Pero medio dato no es ningún dato: el título y el
director alcanzan para BUSCAR, y lo que TMDB devuelva —si el director casa—
trae justo lo que falta.

EL CANDADO ES EL DE `lib.ficha_tmdb`, el mismo que usa FICMA: director ✓
siempre, y título idéntico cuando no hay año ni duración con qué contrastar —el
caso de todos estos—. En un festival de CORTOS eso importa más que en ninguno:
hay obras que se llaman «Solo», «Human», «Lens», «Grief», «Far» o «Shorts», y
un match por título sin director sería una ficha ajena con cara de propia.

QUÉ ESPERAR, dicho de antemano: la mayoría de estos cortos NO está en TMDB.
Circulan por festivales y muchos ni se han estrenado. Este paso no inventa
cobertura; deja escrito quién sí está, y la lista de los que no —que es la
misma lista que hay que pedirle al festival, o dar de alta más adelante—.

Lee   festivals/staging/villadelcine-2026-seleccion-oficial.json
Esc.  festivals/staging/villadelcine-2026-fichas-tmdb.json
      assets/villadelcine-2026/<slug>.jpg        (póster w780)

Requiere TMDB_API_KEY en el entorno.
"""
import json, os, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, banderas, ficha_tmdb, norm, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/villadelcine-2026'
FUENTE = f'{ST}/villadelcine-2026-seleccion-oficial.json'
OUT = f'{ST}/villadelcine-2026-fichas-tmdb.json'

# LA MISMA OBRA CON OTRO NOMBRE EN TMDB. No es corrección del título —el del
# festival se conserva— sino el nombre con el que hay que BUSCARLA. Las dos
# salieron de la sonda por filmografía del director (`verificar-antes-de-alta`),
# que ve lo que la búsqueda por título no: una es la misma palabra escrita de
# otro modo por quien creó la ficha, la otra es el título original en francés.
ALIAS = {
    'Vía Crucis': 'Via Crusis',          # dir. Juan Lucas Neira, TMDB 1697484
    'Behind the Door': 'Derrière la porte',  # dir. Leonardo Valenti, TMDB 1696442
}

# VISTO Y NO TOMADO. Los directores de «Grief» (Nicolas Patiño Hortua y Andrés
# Santiago Cely Orjuela) firman en TMDB «Desarraigo» (1510204), corto colombiano
# de 2026, 15 min. Puede ser la misma obra con otro título o la anterior de los
# mismos autores: «desarraigo» y «grief» no son la misma palabra. No se toma sin
# preguntar — una ficha ajena pegada a una obra es peor que una obra sin ficha.
EN_DUDA = {'Grief': 'los mismos directores firman «Desarraigo» (TMDB 1510204, '
                    'Colombia 2026, 15 min). ¿Es la misma obra?'}


def lb_slug(tmdb_id):
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'],
                       capture_output=True)
    s = r.stdout.decode().strip()
    return s.rsplit('/film/', 1)[-1].strip('/') if '/film/' in s else ''


def baja_poster(poster_path, titulo):
    os.makedirs(ASSETS, exist_ok=True)
    dest = f'{ASSETS}/{slug(titulo)}.jpg'
    if not os.path.exists(dest) or os.path.getsize(dest) < 5000:
        for intento in range(4):
            try:
                req = urllib.request.Request(
                    f'https://image.tmdb.org/t/p/w780{poster_path}',
                    headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    datos = r.read()
                if len(datos) < 5000:
                    raise OSError(f'{len(datos)} bytes: truncado')
                open(dest, 'wb').write(datos)
                break
            except Exception as e:
                if intento == 3:
                    print(f'    ⚠ sin póster para «{titulo}»: {e}', flush=True)
                    return ''
                time.sleep(2 * (intento + 1))
    return f'/assets/villadelcine-2026/{os.path.basename(dest)}'


def main():
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')
    obras = json.load(open(FUENTE, encoding='utf-8'))['obras']

    fichas, sin = {}, []
    for i, o in enumerate(obras, 1):
        r = ficha_tmdb(o, key)
        if not r and o['titulo'] in ALIAS:
            r = ficha_tmdb({**o, 'titulo': ALIAS[o['titulo']]}, key)
        time.sleep(0.2)
        if not r:
            sin.append({'titulo': o['titulo'], 'director': o['director'],
                        'categoria': o['categoria']})
            print(f'[{i:2}/{len(obras)}] —   {o["titulo"][:44]:46} '
                  f'{o["director"][:24]}', flush=True)
            continue
        det, det_en, como = r
        e = {'tmdb_id': det['id'], '_verificado': como}
        anio = int((det.get('release_date') or '0')[:4] or 0)
        if anio:
            e['anio'] = anio
        if det.get('runtime'):
            e['duracion_min'] = det['runtime']
        if det.get('genres'):
            e['genero'] = det['genres'][0]['name']
        if det.get('overview'):
            e['sinopsis'] = det['overview']
        if det_en.get('overview'):
            e['sinopsis_en'] = det_en['overview']
        en = det_en.get('title') or ''
        if en and norm(en) != norm(o['titulo']):
            e['title_en'] = en
        paises = [p.get('name', '') for p in (det.get('production_countries') or [])]
        if paises:
            e['pais'] = paises[0]
            e['flags'] = banderas(paises[0])
        if det.get('poster_path'):
            ruta = baja_poster(det['poster_path'], o['titulo'])
            if ruta:
                e['poster'], e['posterSource'] = ruta, 'tmdb'
        sl = lb_slug(det['id'])
        if sl:
            e['lbSlug'] = sl
        fichas[o['titulo']] = e
        print(f'[{i:2}/{len(obras)}] OK  {o["titulo"][:44]:46} tmdb {det["id"]}'
              f'{"  póster✓" if e.get("poster") else ""}'
              f'{"  lb✓" if e.get("lbSlug") else ""}', flush=True)

    json.dump({'_provenance': provenance(
        'TMDB (api.themoviedb.org) + Letterboxd por el redirect /tmdb/<id>',
        que_aporta='año, duración, país, género, sinopsis, póster y lbSlug de los '
                   'cortos de la Selección Oficial que TMDB tiene',
        candado='lib.ficha_tmdb — director ✓ SIEMPRE; en un festival de cortos el '
                'título solo no distingue nada («Solo», «Human», «Far»)',
        alcance=f'{len(fichas)} de {len(obras)} cortos con ficha; los demás no están '
                f'en TMDB y su dato hay que pedírselo al festival'),
        'fichas': fichas, 'sin_ficha': sin, 'en_duda': EN_DUDA},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(fichas)} con ficha · {len(sin)} sin ficha en TMDB')


if __name__ == '__main__':
    main()
