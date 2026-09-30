#!/usr/bin/env python3
"""fantasmagoria-2026-largos.py — la página «Largometrajes 2026» de la web → ficha y funciones por película.

La SEGUNDA fuente oficial del festival (wp-json página 6440, 28 sep): por cada
largometraje, la dirección, la sinopsis, el sello de estreno («(Estreno
colombiano)») y sus «Proyecciones» con día, hora, sede y acceso. Aporta al
crudo la SINOPSIS y el ESTRENO, y al verificador una lectura de las funciones
independiente de la parrilla (la noticia de programación): donde las dos no
coinciden, el verificador lo dice.
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FUENTE = f'{REPO}/fuentes/fantasmagoria-2026/largometrajes.json'
URL = 'https://festivalfantasmagoriamedellin.com/largometrajes-2026/'
DESTINO = f'{REPO}/festivals/staging/fantasmagoria-2026-largos.json'
FECHA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+(\d{1,2})\s+de\s+octubre[\s.–-]*(\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)?', re.I)
HORA = re.compile(r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)
# «Colombia, 2016, 64’»: el año y la duración al final del crédito
ANIO_DUR = re.compile(r'(\d{4})\s*,\s*(\d{1,3})\s*[´’\']?\s*$')


def main():
    d = json.load(io.open(FUENTE, encoding='utf-8'))
    t = html.unescape(re.sub(r'<[^>]+>', '\n', d['content']['rendered'])).replace('\xa0', ' ')
    L = [x.strip() for x in t.split('\n') if x.strip() and not x.strip().startswith('[')]
    pelis, i = {}, 0
    while i < len(L):
        # una película: su título y, en la línea siguiente, «Dir:»
        if i + 1 < len(L) and L[i + 1].startswith('Dir:') and not L[i].startswith('Dir:'):
            titulo = L[i]
            cred = L[i + 1][4:].strip() or (L[i + 2] if i + 2 < len(L) else '')
            j = i + (3 if not L[i + 1][4:].strip() else 2)
            p = {'credito': cred.strip(' /'), 'funciones': []}
            ad = ANIO_DUR.search(p['credito'])
            if ad:
                p['anio'], p['duracion_min'] = int(ad.group(1)), int(ad.group(2))
            while j < len(L) and not (j + 1 < len(L) and L[j + 1].startswith('Dir:')):
                x = L[j]
                if re.match(r'^\(Estreno [^)]+\)$', x):
                    p['estreno'] = x.strip('()')
                elif len(x) > 60 and 'sinopsis' not in p and not x.startswith(('Proyecci', 'Esta proyecci', 'Película')) and not FECHA.match(x):
                    p['sinopsis'] = x
                else:
                    m = FECHA.match(x)
                    if m:
                        hh = m.group(3) or (L[j + 1] if j + 1 < len(L) else '')
                        mh = HORA.search(hh)
                        if not m.group(3):
                            j += 1
                        v = L[j + 1] if j + 1 < len(L) else ''
                        if mh:
                            h = int(mh.group(1)) % 12 + (12 if mh.group(3).lower() == 'p' else 0)
                            p['funciones'].append({'dia': f'2026-10-{int(m.group(2)):02d}', 'hora': f'{h:02d}:{mh.group(2)}',
                                                   'dia_impreso': m.group(1), 'sede_y_acceso': v})
                        j += 1
                j += 1
            pelis[titulo] = p
            i = j
            continue
        i += 1
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('festivalfantasmagoriamedellin.com, página Largometrajes 2026 (wp-json 6440)', url=URL,
                                  que_aporta='sinopsis, sello de estreno, año y duración de cada largo; sus funciones, para el verificador'),
        '_modificada': d['modified'], 'peliculas': pelis}, ensure_ascii=False, indent=1))
    print(f'✓ {len(pelis)} largometrajes · {sum(1 for p in pelis.values() if p.get("sinopsis"))} con sinopsis · '
          f'{sum(len(p["funciones"]) for p in pelis.values())} funciones → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
