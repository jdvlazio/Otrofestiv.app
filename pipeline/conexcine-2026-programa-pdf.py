#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-programa-pdf.py — la parrilla del 3° CONEXCINE, del PDF oficial.

LA FUENTE. «Programacion Oficial - CONEXCINE 2026.pdf», 4 páginas, hecho en
Illustrator el 8 sep 2026 y colgado en Drive desde fedecajas.com/conexcine.
La página 2 es la parrilla; la 3, el catálogo de cortos por programa.

NO ES UNA RETÍCULA, ES UN COLLAGE. Los cuatro días son TARJETAS repartidas por
la hoja, no columnas: el jueves ocupa dos bloques de x distinta (x≈306 y x≈498)
y el sábado tres (x≈290, 540 y 704). Agrupar por columna de x parte los días;
agrupar por «la etiqueta más cercana» los mezcla. Así que las cuatro regiones
van DECLARADAS, y cada una dice qué etiqueta y qué número tiene que encontrar
dentro: si el festival rehace el diseño, el paso falla en vez de inventar.

EL TEXTO DEL PDF MIENTE EN PARTE. Los títulos compuestos con la tipografía
decorativa salen con el ToUnicode roto: «PROGRAMA 3: BŀŝėƝŀĶŭ÷ŤɑŜŵ÷ɑƣŀŝ÷ë÷Ķ».
No se adivinan: los mismos títulos están escritos LIMPIOS en la página 3, en la
descripción de cada programa, y de ahí se toman. La tabla MOJIBAKE deja escrito
qué se leyó y contra qué se corrigió.

Salida: festivals/staging/conexcine-2026-parrilla.json
"""
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, hora24

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/conexcine-2026/programacion-2026.pdf'
OUT = f'{REPO}/festivals/staging/conexcine-2026-parrilla.json'
URL = ('https://drive.google.com/file/d/1x0l0MwffrReBexjv_d312trbZvZ5JP5p/view'
       ' (enlazado desde https://www.fedecajas.com/conexcine/)')

# LAS CUATRO TARJETAS. (x0, y0, x1, y1) en puntos de la página 2, con la
# etiqueta y el número que deben aparecer dentro. Medidas sobre el PDF del
# 8 sep 2026; `--check` las vuelve a comprobar en cada corrida.
DIAS = [
    {'dia': '2026-09-23', 'label': 'MIÉRCOLES', 'num': '23', 'caja': (30, 290, 290, 630)},
    {'dia': '2026-09-24', 'label': 'JUEVES', 'num': '24', 'caja': (290, 35, 680, 440)},
    {'dia': '2026-09-25', 'label': 'VIERNES', 'num': '25', 'caja': (680, 75, 950, 440)},
    {'dia': '2026-09-26', 'label': 'SÁBADO', 'num': '26', 'caja': (285, 440, 950, 630)},
]

# EL TEXTO QUE EL PDF DA ROTO, y de dónde sale el bueno. La página 3 escribe
# los mismos títulos con la tipografía normal, en el párrafo que describe cada
# programa. No es una conjetura: es la misma frase, dos veces, en el mismo PDF.
MOJIBAKE = {
    'PROGRAMA 3: BŀŝėƝŀĶŭ÷ŤɑŜŵ÷ɑƣŀŝ÷ë÷Ķ':
        ('PROGRAMA 3: Horizontes que florecen',
         'p3: «3. HORiZONTES QUE FLORECEN, donde el campo se convierte…»'),
}

RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s*[-–]\s*'
                     r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?$', re.I)
# La franja transversal no es una función: son dos exposiciones abiertas todo
# el festival. Se reconocen por su propia línea de horario, que no es un rango
# de reloj sino «desde el miércoles … hasta el sábado …».
RE_TRANSVERSAL = re.compile(r'desde el mi[ée]rcoles.*hasta el s[áa]bado', re.I)


def lineas(pagina):
    """Las líneas de una página con su esquina superior izquierda, en puntos."""
    x = subprocess.run(['pdftotext', '-f', str(pagina), '-l', str(pagina),
                        '-bbox-layout', PDF, '-'],
                       capture_output=True, text=True).stdout
    out = []
    for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" '
                         r'xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', x, re.S):
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(5)))).strip()
        if t:
            out.append({'x': float(m.group(1)), 'y': float(m.group(2)), 'txt': t})
    return out


def limpia(t):
    if t in MOJIBAKE:
        return MOJIBAKE[t][0]
    return t




def main():
    ls = lineas(2)
    sueltas = list(ls)
    bloques, avisos, transversales = [], [], []

    for d in DIAS:
        x0, y0, x1, y1 = d['caja']
        dentro = [l for l in ls if x0 <= l['x'] < x1 and y0 <= l['y'] < y1]
        # LA TARJETA SE IDENTIFICA SOLA. Si su etiqueta o su número no están
        # dentro de la caja, el diseño cambió y esta medida ya no vale.
        txts = [l['txt'] for l in dentro]
        if d['label'] not in txts or d['num'] not in txts:
            avisos.append(f'{d["dia"]}: la caja no contiene «{d["label"]}» y/o «{d["num"]}» '
                          f'— el PDF cambió de diseño, revisar DIAS')
            continue
        # el nombre del día («DÍA 1: HISTORIAS QUE NOS ENCUENTRAN»), que el
        # festival usa como título de la jornada
        nom = [l['txt'] for l in sorted(dentro, key=lambda l: l['y'])
               if l['txt'].startswith('DÍA ')]
        jornada = ''
        if nom:
            i = txts.index(nom[0])
            seg = sorted(dentro, key=lambda l: (l['x'] // 100, l['y']))
            k = [j for j, l in enumerate(seg) if l['txt'] == nom[0]][0]
            jornada = nom[0]
            for l in seg[k + 1:]:
                if RE_HORA.match(l['txt']) or l['txt'].startswith('DÍA '):
                    break
                if l['txt'].isupper() or l['txt'][0].isupper():
                    jornada += ' ' + l['txt']
                if len(jornada) > 90:
                    break

        # los bloques: cada uno empieza en una línea de hora y se queda con lo
        # que le sigue EN SU MISMA COLUMNA hasta la hora siguiente.
        #
        # CADA LÍNEA EN UNA SOLA COLUMNA. Redondear la x y después recoger «lo
        # que esté a menos de 20 pt» hace que una línea entre en dos columnas
        # vecinas y el bloque salga DUPLICADO: 19 bloques donde hay 13. Las
        # columnas se agrupan una vez, por cercanía, y cada línea va a la suya.
        columnas = []
        for l in sorted(dentro, key=lambda l: l['x']):
            if columnas and l['x'] - columnas[-1][-1]['x'] < 30:
                columnas[-1].append(l)
            else:
                columnas.append([l])
        for grupo in columnas:
            en_col = sorted(grupo, key=lambda l: l['y'])
            col = round(min(l['x'] for l in grupo))
            actual = None
            for l in en_col:
                m = RE_HORA.match(l['txt'])
                if m:
                    actual = {'dia': d['dia'], 'jornada': jornada,
                              'hora': hora24(f'{m.group(1)}:{m.group(2)} {m.group(3)}.m.'),
                              'fin': hora24(f'{m.group(4)}:{m.group(5)} {m.group(6)}.m.'),
                              'lineas': [], '_x': col, '_y': l['y'], 'pagina': 2}
                    bloques.append(actual)
                    if l in sueltas:
                        sueltas.remove(l)
                    continue
                if RE_TRANSVERSAL.search(l['txt']):
                    transversales.append(l['txt'])
                    actual = None
                if actual is not None:
                    actual['lineas'].append(limpia(l['txt']))
                    if l in sueltas:
                        sueltas.remove(l)

    for b in bloques:
        b['duracion_min'] = ((int(b['fin'][:2]) * 60 + int(b['fin'][3:]))
                             - (int(b['hora'][:2]) * 60 + int(b['hora'][3:])))

    bloques.sort(key=lambda b: (b['dia'], b['hora'], b['_x']))
    # lo que quedó fuera de toda tarjeta y de todo bloque: se nombra, no se tira
    resto = [l['txt'] for l in sueltas]

    json.dump({'_provenance': provenance(
        'Programación Oficial CONEXCINE 2026 (PDF de 4 páginas), página 2',
        que_aporta='los bloques con día, hora de inicio y de fin, el nombre de la '
                   'jornada y las líneas que el festival imprime en cada uno',
        url=URL,
        metodo='pdftotext -bbox-layout: los cuatro días son tarjetas en un '
               'collage, con sus regiones declaradas y auto-verificadas por la '
               'etiqueta y el número que deben caer dentro. Cada bloque arranca '
               'en su línea de hora y toma lo que le sigue en la misma columna'),
        'bloques': bloques, 'transversales': transversales,
        'mojibake_corregido': {k: {'leido': k, 'publicado': v[0], 'fuente': v[1]}
                               for k, v in MOJIBAKE.items()},
        'sin_clasificar': resto, 'avisos': avisos},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{len(bloques)} bloques en {len({b["dia"] for b in bloques})} días '
          f'→ {OUT.split("/")[-1]}')
    for b in bloques:
        print(f'  {b["dia"][-2:]} {b["hora"]}–{b["fin"]} {b["duracion_min"]:>4}m  '
              f'{" / ".join(b["lineas"])[:72]}')
    if transversales:
        print(f'\ntransversales (no son función): {len(transversales)}')
    if resto:
        print(f'\nlíneas sin bloque ({len(resto)}) — cabecera, rótulos y adorno:')
        for r in resto:
            print('   ·', r[:70])
    if avisos:
        print('\n✗ ' + '\n✗ '.join(avisos))
        sys.exit(1)


if __name__ == '__main__':
    main()
