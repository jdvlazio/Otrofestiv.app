#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-parrilla.py — la parrilla que el festival publicó COMO IMÁGENES.

El 11° Festival de Cine de Jardín no publica parrilla en su web: el enlace de
«programación» de la home sigue apuntando al PDF de 2025. La publicó el 21 sep
2026 en un carrusel de Instagram de 14 láminas, y ahí está entera.

LA MAQUETA, que es lo que permite leerla sin adivinar:

  · CABECERA con el día: «Viernes 25 de septiembre - Día 2», arriba del todo.
    El lector genérico (ig-programa.py) no la miraba y fechó las 14 láminas el
    mismo día: sacaba las horas bien y el día mal, que es peor que no sacar
    nada. La cabecera es un dato del propio festival, no una deducción.
  · TRES COLUMNAS por posición horizontal: la hora a la izquierda, la sede en
    el medio, la ficha a la derecha.
  · UNA HORA VALE PARA VARIAS SEDES. A las 10:00 del viernes hay función en el
    Teatro Municipal, en la Casa de la cultura y en la Placa deportiva; la hora
    se imprime UNA vez y las tres filas cuelgan de ella. Leer «una fila = una
    hora» perdería dos de cada tres.

Láminas: 00 portada · 01 índice de secciones · 02–11 la parrilla por día ·
12 TALLERES (otra maqueta, con «Lugar:» y «Hora:» rotulados) · 13 cierre.

Esc.  festivals/staging/jardin-2026-parrilla.json
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
from lib import provenance

POST = 'DdkY5ejlraV'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
SWIFT = f'{REPO}/pipeline/ficma-2026-ocr.swift'
OUT = f'{REPO}/festivals/staging/jardin-2026-parrilla.json'

# Las tres columnas, medidas sobre las láminas (x normalizado 0–1).
COL_HORA, COL_FICHA = 0.20, 0.44
# CON QUÉ PALABRA EMPIEZA UNA SEDE. La columna del medio parte los nombres
# largos en dos líneas («Teatro Municipal» / «de Jardín», «Placa deportiva» /
# «Barrio Simón Bolívar») y no hay separación vertical que distinga esa
# continuación del comienzo de la sede siguiente: probé por distancia y fundió
# «Casa de la cultura» con «Coliseo municipal» en una sola. Así que la fila
# nueva la marca el VOCABULARIO, que es lo que el festival imprime de verdad.
CABEZA_SEDE = re.compile(r'^(Teatro|Casa|Placa|Coliseo|Escuela|Fonda|I\.?E\b|'
                         r'Instituci[óo]n|Biblioteca|Parque|Auditorio)', re.I)
DIAS = {'jueves': 24, 'viernes': 25, 'sábado': 26, 'sabado': 26, 'domingo': 27}
RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)
# «Colombia, 2026, 84 min, documental» — país(es), año, duración, género.
RE_FICHA = re.compile(r'^(.+?),\s*((?:1[89]|20)\d{2}),\s*(\d{1,3})\s*min,\s*(.+)$')


def ocr(rutas):
    """{basename: [líneas con caja]} — Vision, con posición."""
    r = subprocess.run(['swift', SWIFT] + rutas, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ OCR falló: {r.stderr[:300]}')
    return json.loads(r.stdout)


def h24(m):
    h, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ap == 'p' and h != 12:
        h += 12
    if ap == 'a' and h == 12:
        h = 0
    return f'{h:02d}:{mm:02d}'


def dia_de(lineas):
    """El día que anuncia la cabecera de la lámina, o '' si no la lleva."""
    cab = ' '.join(c['t'] for c in lineas if c['y'] < 0.075)
    m = re.search(r'(jueves|viernes|s[áa]bado|domingo)\s+(\d{1,2})', cab, re.I)
    if not m:
        return ''
    d = int(m.group(2))
    # el nombre del día y el número tienen que decir lo MISMO: si no, no se
    # inventa ninguno de los dos.
    if DIAS.get(m.group(1).lower()) != d:
        return ''
    return f'2026-09-{d:02d}'


def filas(lineas, dia):
    """Las funciones de una lámina de parrilla.

    NO se recorre un solo flujo ordenado por altura: las tres columnas se
    entrelazan y la ficha de una fila puede quedar por encima de la sede de la
    siguiente. Se arma al revés —primero las FILAS, que las define la columna
    de la sede, y después cada línea de ficha cae en su banda—. Leyéndolo como
    un flujo, «Teatro Municipal» / «de Jardín» salían como dos funciones y la
    lámina del viernes daba 12 donde los ojos cuentan 9.
    """
    util = [c for c in lineas if c['y'] >= 0.075 and c['t'].strip()]
    horas = sorted(((c['y'], h24(m)) for c in util if c['x'] < COL_HORA
                    for m in [RE_HORA.match(c['t'].strip())] if m))
    sedes = sorted((c for c in util if COL_HORA <= c['x'] < COL_FICHA),
                   key=lambda c: c['y'])
    # una sede partida en dos líneas («Teatro Municipal» / «de Jardín») es UNA
    filas_ = []
    for c in sedes:
        if filas_ and not CABEZA_SEDE.match(c['t'].strip()) \
                and c['y'] - filas_[-1]['_y2'] < 0.05:
            filas_[-1]['sede'] += ' ' + c['t'].strip()
            filas_[-1]['_y2'] = c['y']
        else:
            filas_.append({'dia': dia, 'sede': c['t'].strip(),
                           '_y': c['y'], '_y2': c['y'], 'ficha': []})
    for f in filas_:
        previas = [h for y, h in horas if y <= f['_y'] + 0.012]
        f['hora'] = previas[-1] if previas else ''
    # cada línea de ficha, a la fila cuya banda empieza más cerca por encima
    for c in sorted((c for c in util if c['x'] >= COL_FICHA), key=lambda c: c['y']):
        cand = [f for f in filas_ if f['_y'] <= c['y'] + 0.012]
        if cand:
            cand[-1]['ficha'].append(c['t'].strip())
    for f in filas_:
        f.pop('_y2', None)
    return [f for f in filas_ if f['hora']]


def una_columna(lineas, dia):
    """La lámina del jueves, que NO tiene tres columnas.

    El día inaugural se maqueta en una sola columna alineada a la izquierda, con
    dos bloques rotulados —LECCIÓN INAUGURAL y ACTO INAUGURAL—, cada uno con su
    hora, su sede y su ficha debajo. Leído con la regla de las tres columnas
    daba CERO funciones: no hay nada a la derecha de 0,44.
    """
    ls = [c for c in sorted(lineas, key=lambda c: c['y'])
          if c['y'] >= 0.075 and c['t'].strip()]
    out, act = [], None
    for c in ls:
        t = c['t'].strip()
        if re.match(r'^[A-ZÁÉÍÓÚÑ ]{6,}$', t) and 'PONENTES' not in t.upper():
            act = {'dia': dia, 'hora': '', 'sede': '', 'rotulo': t, 'ficha': []}
            out.append(act)
            continue
        if act is None:
            continue
        m = RE_HORA.match(t)
        if m and not act['hora']:
            act['hora'] = h24(m)
        elif not act['sede'] and re.search(r'teatro|casa|placa|coliseo|escuela|i\.e', t, re.I):
            act['sede'] = t
        else:
            act['ficha'].append(t)
    return [f for f in out if f['hora'] and f['sede']]


def ficha(f):
    """Título, dirección y metadatos de la columna derecha."""
    ls = [x for x in f['ficha'] if x.strip()]
    d = {}
    # la FRANJA, cuando la lámina la rotula encima del título
    # SOLO «Franja …». Antes entraban también «Muestra …» y «Competencia …»,
    # y la «Muestra Red de Audiovisuales de Medellín» del viernes perdía su
    # título entero: el rótulo se lo comía y la función salía sin nombre.
    if len(ls) > 1 and re.match(r'^Franja\b', ls[0], re.I):
        d['franja'] = ls.pop(0)
    if not ls:
        return d
    d['titulo'] = ls[0].strip()
    resto = ls[1:]
    for x in resto:
        if x.startswith('Dir.'):
            d['director'] = x[4:].strip(' .')
        m = RE_FICHA.match(x)
        if m:
            d['pais'] = m.group(1).strip()
            d['anio'] = int(m.group(2))
            d['duracion_min'] = int(m.group(3))
            d['genero'] = m.group(4).strip()
    notas = [x for x in resto if not x.startswith('Dir.') and not RE_FICHA.match(x)]
    if notas:
        d['_extra'] = ' '.join(notas)
    return d


def main():
    rutas = sorted(f'{LAMINAS}/{n}' for n in os.listdir(LAMINAS) if n.endswith('.jpg'))
    crudo = ocr(rutas)
    funciones, sin_dia = [], []
    for ruta in rutas:
        k = os.path.basename(ruta)
        ls = crudo.get(k) or crudo.get(ruta) or []
        dia = dia_de(ls)
        if not dia:
            sin_dia.append(k)
            continue
        hay_cols = any(c['x'] >= COL_FICHA and c['y'] > 0.075 for c in ls)
        for f in (filas(ls, dia) if hay_cols else una_columna(ls, dia)):
            f.pop('_y', None)
            f.update(ficha(f))
            f.pop('ficha', None)
            f['_lamina'] = k
            funciones.append(f)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    json.dump({'_provenance': provenance(
        'Instagram @festicinejardin — el carrusel de programación',
        que_aporta='la parrilla entera: día, hora, sede y ficha. La web del '
                   'festival no publica programación de 2026',
        url=f'https://www.instagram.com/p/{POST}/',
        metodo='OCR con cajas sobre las 14 láminas; el día sale de la cabecera '
               'de cada una y la hora vale para todas las sedes que cuelgan'),
        'funciones': funciones,
        '_laminas_sin_dia': sin_dia},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(funciones)} funciones · {len(rutas)} láminas '
          f'({len(sin_dia)} sin día: {", ".join(sin_dia)}) → {os.path.basename(OUT)}')
    import collections
    for d, n in sorted(collections.Counter(f['dia'] for f in funciones).items()):
        print(f'   {d}: {n}')


if __name__ == '__main__':
    main()
