# -*- coding: utf-8 -*-
"""Catálogo Y programación de TIFF 2026, de su propio endpoint.

LA FUENTE
`https://www.tiff.net/festivalfilmlist` devuelve ~870 KB de JSON con TODO lo
que necesitamos en una sola petición: 244 obras con sinopsis, póster, director,
sección, países e idiomas, y sus 887 funciones con hora, sede, sala, audiencia,
accesibilidad, formato y enlace de boletería. Es el endpoint que la propia
parrilla de tiff.net consume para pintarse.

Antes de usarla se comprobó que TIFF no publica `robots.txt` (404): no hay
restricción declarada, a diferencia de tiffr y Letterboxd, que sí prohíben
explícitamente la recolección automatizada y por eso NO son fuente aquí.

POR QUÉ ESTE SCRIPT NO DESCARGA
tiff.net está detrás de un muro anti-bot que responde 202 con cuerpo vacío a
cualquier cliente que no sea un navegador de verdad — `curl` no pasa ni con
cabeceras completas. La captura se hace desde el navegador, en la pestaña ya
abierta en tiff.net:

    await (await fetch('/festivalfilmlist', {credentials:'include'})).json()

y se vuelca a `--crudo`. Este script toma ese volcado, lo proyecta a nuestros
campos y le pone procedencia. Se documenta así a propósito: un script que
fingiera descargar y fallara con 202 sería peor que uno honesto sobre su
dependencia manual.

LA GRANULARIDAD, QUE ES LO QUE HAY QUE ENTENDER
TIFF cuenta 244 «obras» y nosotros contamos 259 desde Letterboxd. Ninguno se
equivoca: TIFF lista la UNIDAD QUE SE VENDE («Short Cuts 2026 Programme 01»,
«Wavelengths 2: This Suffocating Now») y Letterboxd lista los cortos que van
DENTRO. Es exactamente nuestro modelo de cortos como items de una función, y
por eso las dos fuentes se complementan en vez de competir.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
FUENTE = 'https://www.tiff.net/festivalfilmlist'


def proyectar(d):
    obras = []
    for f in d['items']:
        obras.append({
            'id': f.get('id'), 'slug': f.get('slug'), 'titulo': f.get('title'),
            'url': f.get('url'),
            'sinopsis': (f.get('description') or '').strip(),
            'poster': f.get('posterUrl') or None,
            'directores': f.get('directors') or [],
            'secciones': f.get('webProgrammes') or [],
            'paises': f.get('countries'), 'idiomas': f.get('languages'),
            'generos': f.get('genre') or [],
            'canadiense': bool(f.get('isCanadian')),
            'invitados': len(f.get('guests') or []),
            'funciones': [{
                'id': s.get('id'), 'ini': s.get('startTime'), 'fin': s.get('endTime'),
                # `audienceType` separa lo asistible de lo que no lo es. Sin este
                # campo publicaríamos 247 pases de prensa y mercado como si el
                # público pudiera entrar.
                'audiencia': s.get('audienceType'),
                'cancelada': bool(s.get('cancelled')),
                'sede': (s.get('venue') or {}).get('name'),
                'sala': (s.get('venue') or {}).get('shortName'),
                'salaLarga': (s.get('venue') or {}).get('room'),
                'costo': s.get('cost') or [],
                'accesibilidad': s.get('accessibility') or [],
                'formato': s.get('printFormat'), 'boleta': s.get('url'),
            } for s in (f.get('scheduleItems') or [])],
        })
    return obras


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--crudo', required=True,
                    help='volcado JSON de /festivalfilmlist capturado desde el navegador')
    a = ap.parse_args()
    d = json.load(open(a.crudo, encoding='utf-8'))
    if 'items' not in d:
        sys.exit('El volcado no tiene «items»: no es la respuesta de /festivalfilmlist.')

    obras = proyectar(d)
    funcs = [f for o in obras for f in o['funciones']]
    pub = [f for f in funcs if f['audiencia'] == 'General Public']

    salida = f'{ST}/tiff-2026-oficial.json'
    json.dump({'_provenance': provenance(
                   FUENTE, metodo='fetch desde el navegador; tiff.net responde 202 a curl',
                   nota='TIFF no publica robots.txt (404): sin restriccion declarada'),
               '_obras': len(obras), '_funciones': len(funcs),
               '_funciones_publicas': len(pub), 'obras': obras},
              open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'── {salida}')
    print(f'   obras {len(obras)} · funciones {len(funcs)} '
          f'(públicas {len(pub)}, resto prensa/mercado/privadas)')
    print(f'   sinopsis {sum(1 for o in obras if o["sinopsis"])}/{len(obras)} · '
          f'póster {sum(1 for o in obras if o["poster"])}/{len(obras)}')
    print(f'   sedes {len({f["sede"] for f in funcs})} · salas {len({f["sala"] for f in funcs})}')


if __name__ == '__main__':
    main()
