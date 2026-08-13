# -*- coding: utf-8 -*-
"""Programación de TIFF 2026 desde el CDN de Contentful que alimenta tiff.net.

POR QUÉ ESTA FUENTE Y NO RASPAR LA WEB
tiff.net no es HTML servido: es una app que pinta la parrilla leyendo el CDN de
Contentful. Sus propias funciones de página (`TiffApp.getCalendarToolJSON`,
`getFestivalDataJSON`) hacen exactamente esta consulta, con este espacio y este
token. Leer de aquí es leer la misma fuente pública que ve cualquier visitante,
estructurada, y pesando UNA petición donde raspar costaría once páginas.

SOBRE EL TOKEN
Es un *delivery token* de Contentful: de solo lectura, sobre contenido ya
publicado, y viaja en el JavaScript de cada visita — está diseñado para ser
público. Aun así NO se commitea: se pasa por `--token`, y se obtiene abriendo
tiff.net y leyendo `appSettings.accessToken`. El repo no guarda credenciales de
terceros, ni siquiera públicas.

QUÉ NO ES ESTA FUENTE
No sustituye la verificación. Contentful nos da lo que TIFF publica; que un
`tmdb_id` case con la obra correcta sigue siendo trabajo del cruce con
Letterboxd y TMDB.
"""
import argparse, json, os, subprocess, sys, time, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ESPACIO = '22n7d68fswlw'
CDN = f'https://cdn.contentful.com/spaces/{ESPACIO}/entries/'


def consultar(token, **params):
    """Una página de resultados. Sin reintento ciego: un error se ve de una."""
    q = urllib.parse.urlencode({'access_token': token, **params})
    r = subprocess.run(['curl', '-s', '--max-time', '40', f'{CDN}?{q}'],
                       capture_output=True)
    try:
        d = json.loads(r.stdout.decode())
    except Exception:
        sys.exit(f'Contentful devolvió algo que no es JSON: {r.stdout[:200]!r}')
    if 'items' not in d:
        sys.exit(f'Contentful respondió con error: {json.dumps(d)[:300]}')
    return d


def paginar(token, etiqueta, **params):
    """Recorre `skip` hasta agotar `total`. El límite duro del CDN es 1000."""
    items, incl_a, incl_e, skip, total = [], [], [], 0, None
    while total is None or skip < total:
        d = consultar(token, limit=200, skip=skip, **params)
        total = d['total']
        items += d['items']
        inc = d.get('includes') or {}
        incl_a += inc.get('Asset', [])
        incl_e += inc.get('Entry', [])
        skip += 200
        print(f'   {etiqueta}: {min(skip, total)}/{total}', flush=True)
        if not d['items']:
            break
        time.sleep(0.3)
    return items, incl_a, incl_e


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--token', required=True,
                    help='delivery token público; se lee de appSettings.accessToken en tiff.net')
    ap.add_argument('--explorar', action='store_true',
                    help='solo describe el modelo de contenido y sale, sin escribir nada')
    a = ap.parse_args()

    if a.explorar:
        # Paso 0: no se asume ningún nombre de campo. Primero se mira qué hay.
        d = consultar(a.token, limit=1000, **{'sys.type': 'Entry'})
        tipos = {}
        for it in d['items']:
            t = it['sys']['contentType']['sys']['id']
            tipos.setdefault(t, {'n': 0, 'campos': set()})
            tipos[t]['n'] += 1
            tipos[t]['campos'] |= set(it['fields'].keys())
        print(f'muestra de {len(d["items"])} entradas · total en el espacio: {d["total"]}\n')
        for t, v in sorted(tipos.items(), key=lambda k: -k[1]['n']):
            print(f'  {t:22} {v["n"]:5}  {", ".join(sorted(v["campos"]))[:150]}')
        return

    os.makedirs(ST, exist_ok=True)
    fests = consultar(a.token, content_type='festival', limit=100)['items']
    print(f'── {len(fests)} festivales en el espacio')
    salida = f'{ST}/tiff-2026-contentful-festivales.json'
    json.dump({'_espacio': ESPACIO, '_fuente': 'cdn.contentful.com (el mismo que usa tiff.net)',
               'festivales': [f['fields'] | {'_id': f['sys']['id']} for f in fests]},
              open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {salida}')


if __name__ == '__main__':
    main()
