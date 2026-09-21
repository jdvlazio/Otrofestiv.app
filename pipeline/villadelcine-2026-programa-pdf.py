#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-programa-pdf.py — la parrilla y las fichas del PDF oficial.

QUÉ ES. El 18 de septiembre —a cinco días de abrir— el festival cambió el botón
PROGRAMACIÓN de su home: dejó de apuntar a un PDF de 2023 y apunta al de 2026.
67 páginas hechas en Canva, CON CAPA DE TEXTO (no hace falta OCR):

  · p2–p11   la RETÍCULA de los cuatro días: filas de hora, columnas de sede.
  · p12–p50  una FICHA por obra, agrupadas por el mismo nombre de programa que
             usa la retícula («NARRATIVAS DIVERGENTES / PORTALES»).
  · p51–p60  la Ruta Académica: talleres, charlas y laboratorios.
  · p61–p67  patrocinadores, créditos y mapa.

POR QUÉ CON POSICIONES Y NO CON `pdftotext -layout`. La retícula es una tabla
dibujada: lo que dice qué sede y qué hora es una celda es su POSICIÓN, no el
orden del texto. Con `-bbox-layout` cada línea trae su caja, y entonces la
columna sale de la x y la hora de la y. En plano, «Museo Casa Antonio Nariño
Salón principal» aparece dos veces seguidas y no hay forma de saber cuál es 1er
piso y cuál 2do.

NI LA HORA DE INICIO SALE DEL TEXTO. Esto costó una vuelta entera: el texto de
cada celda va CENTRADO en vertical, así que su primera línea no marca dónde
empieza el bloque. Leyéndolo así, la programación infantil del jueves —que va de
9:00 a 12:45— salía a las 10:30, que es donde cae su rótulo. Cuatro de cinco
bloques quedaban mal y ninguno se veía mal.

Lo que sí marca la celda es su RECTÁNGULO DE COLOR. No está en la capa de texto,
pero sí en la página dibujada: se renderiza a 150 dpi y se segmentan las manchas
de color (los fondos pastel sobre blanco). De cada mancha salen las dos horas
—arriba el inicio, abajo el fin— contra los rótulos de la columna de la
izquierda, y de paso la DURACIÓN, que así es la que el festival dibujó y no una
suma nuestra.

Y APARECE TEXTO QUE NADIE VE. La página del jueves trae un «#Hija» en la capa de
texto que no está pintado en ninguna parte: sobra de una versión anterior en
Canva. Como el contenido se toma de lo que cae DENTRO de un rectángulo, ese
fantasma se queda fuera solo.

LAS FILAS NO SON DE 15 MINUTOS. Los rótulos saltan: 04:45, 05:00, 05:30, 05:45…
El paso lee los rótulos, no cuenta filas.

Lee   fuentes/villadelcine-2026/programacion-2026.pdf  (del botón de la home)
Esc.  festivals/staging/villadelcine-2026-parrilla.json
"""
import html as _html
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PDF = f'{REPO}/fuentes/villadelcine-2026/programacion-2026.pdf'
URL = ('https://villadelcine.com/wp-content/uploads/2026/09/'
       'Programacion-caminos-del-tiempo-2026_compressed.pdf')
OUT = f'{ST}/villadelcine-2026-parrilla.json'

PAGS_RETICULA = (2, 11)
PAGS_FICHAS = (12, 50)
PAGS_ACADEMICA = (51, 60)
ANCHO_PT = 609.75          # el ancho de página del PDF, para pasar píxeles a puntos
DPI = 150

RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])\.?m\.?$|^(\d{1,2}):(\d{2})\s*m$')
RE_HORA_ROTA = re.compile(r'^(\d{1,2}):(\d{2})\s*.?\.?m\.?$')
# El número del día viaja pegado a lo que toque: «23 MIÉRCOLES» en una página
# y «24 MAÑANA» en la siguiente. Se ancla al número, no a la palabra.
RE_DIA = re.compile(r'^(\d{1,2})\s+(MIÉRCOLES|JUEVES|VIERNES|SÁBADO|DOMINGO|LUNES|MARTES'
                    r'|MAÑANA|TARDE|NOCHE|TARDE/NOCHE)$')
# Lo que nunca es contenido de una celda: la marca del festival y los rótulos
# de la propia tabla.
MARCA = re.compile(r'^(12|FESTIVAL|VILLA|DEL CINE|Septiembre|Lugar|Hora|caminos|del|tiempo|'
                   r'MAÑANA|TARDE|NOCHE|TARDE/NOCHE|LUNES|MARTES|MIÉRCOLES|JUEVES|VIERNES|'
                   r'SÁBADO|DOMINGO)$', re.I)


def lineas(p0, p1):
    """[(página, x0, y0, x1, y1, texto)] de un rango de páginas."""
    xml = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(p0), '-l', str(p1),
                          PDF, '-'], capture_output=True, text=True, check=True).stdout
    out, pag = [], p0 - 1
    for m in re.finditer(r'<page |<line xMin="([\d.]+)" yMin="([\d.]+)" '
                         r'xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', xml, re.S):
        if m.group(0).startswith('<page'):
            pag += 1
            continue
        x0, y0, x1, y1, inner = m.groups()
        # `pdftotext -bbox-layout` devuelve XML: el apóstrofo y el ampersand
        # viajan como entidades. Sin deshacerlas quedaban títulos como
        # «I DON&apos;T KNOW WHAT TO DO» y «Q&amp;A», que no cruzan con
        # ninguna otra fuente y ensucian lo que se publica.
        t = _html.unescape(' '.join(re.findall(r'>([^<]*)</word>', inner))).strip()
        t = re.sub(r'\s+', ' ', t)
        if t:
            out.append((pag, float(x0), float(y0), float(x1), float(y1), t))
    return out


def hora_reticula(t, ap_previo=''):
    """«05:30 p.m» → «17:30». NO es `lib.hora24`, y por eso el otro nombre:
    esta hereda el a.m./p.m. de la fila anterior con `ap_previo`, que es lo que
    salva el «10:00 0.m» mal escrito de la última fila del sábado noche. Sin
    ella el último bloque del festival terminaba quince minutos antes de lo
    dibujado."""
    m = RE_HORA.match(t.strip())
    if not m:
        m2 = RE_HORA_ROTA.match(t.strip())
        if not (m2 and ap_previo):
            return ''
        return f'{int(m2.group(1)) % 12 + (12 if ap_previo == "p" else 0):02d}:{m2.group(2)}'
    if m.group(4):                      # «12:00 m» = mediodía
        return f'{int(m.group(4)) % 12 + 12:02d}:{m.group(5)}'
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3)
    return f'{h % 12 + (12 if ap == "p" else 0):02d}:{mm}'


def sedes_de(ls, y_primera_hora):
    """[{x0, x1, nombre}] de las columnas, leyendo la banda de cabecera.

    LA BANDA NO ESTÁ EN UNA ALTURA FIJA: cada página de la retícula la dibuja
    donde le cabe (en la del jueves mañana empieza en y≈100 y en la del viernes
    tarde en y≈87). Fijar una franja recortaba la primera línea del nombre y
    dejaba sedes llamadas «1er piso». Se ancla a lo que sí es estable: la
    cabecera es todo lo que está ARRIBA de la primera fila de hora y a la
    derecha de la columna de horas.

    Un nombre ocupa hasta tres líneas apiladas («Museo Casa Antonio / Nariño
    Salón principal / 1er piso»), y lo que las junta es que se solapan en x.
    """
    cab = [l for l in ls if l[2] < y_primera_hora - 2 and l[1] > 88
           and not MARCA.match(l[5]) and not RE_DIA.match(l[5]) and not hora_reticula(l[5])]
    cols = []
    for _, x0, y0, x1, _, t in sorted(cab, key=lambda l: (l[1], l[2])):
        for c in cols:
            if min(x1, c['x1']) - max(x0, c['x0']) > 0.4 * min(x1 - x0, c['x1'] - c['x0']):
                c['partes'].append((y0, t))
                c['x0'], c['x1'] = min(c['x0'], x0), max(c['x1'], x1)
                break
        else:
            cols.append({'x0': x0, 'x1': x1, 'partes': [(y0, t)]})
    return [{'x0': c['x0'], 'x1': c['x1'],
             'nombre': ' '.join(t for _, t in sorted(c['partes']))} for c in cols]


def render(pag):
    """La página como imagen, cacheada en fuentes/ (no se versiona: es derivable)."""
    d = f'{REPO}/fuentes/villadelcine-2026/pag'
    p = f'{d}/p-{pag:02d}.jpg'
    if not os.path.exists(p):
        os.makedirs(d, exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(DPI), '-jpeg', '-f', str(pag), '-l', str(pag),
                        PDF, f'{d}/p'], check=True)
    return p


def manchas(pag, y_min_pt):
    """Los rectángulos de color de una página, en puntos PDF.

    Una celda es un fondo pastel sobre blanco. Se descarta el blanco (fondo) y
    lo muy oscuro (texto y líneas); lo que queda son las celdas y la banda de
    cielo de la cabecera, que se va por altura.
    """
    from PIL import Image
    im = Image.open(render(pag)).convert('RGB')
    W, H = im.size
    esc = ANCHO_PT / W
    px = im.load()

    def color(x, y):
        # LO QUE DISTINGUE UNA CELDA DE UNA LÍNEA ES EL TONO, NO EL BRILLO. Con
        # un umbral de brillo, el punteado gris de la retícula contaba como
        # relleno y unía celdas vecinas: la del miércoles se tragó «ARENAS»
        # entera y devolvía un bloque de 135 minutos que no existe. Los fondos
        # pastel tienen tono (canales separados); el punteado y el blanco, no.
        r, g, b = px[x, y]
        return max(r, g, b) - min(r, g, b) > 12 and not (r > 244 and g > 244 and b > 244)

    def parecido(a, b):
        """Dos píxeles del MISMO relleno. Dos celdas pegadas de colores
        distintos —el CLAQUETAZO amarillo y el Reconocimiento vinotinto del
        sábado— se tocan sin una línea de por medio: sin comparar el color
        salían como un solo bloque de media hora que no existe."""
        return sum(abs(x - y) for x, y in zip(a, b)) < 90

    y0_px = int(y_min_pt / esc)
    visto = bytearray(W * H)
    cajas = []
    for y in range(y0_px, H):
        fila = y * W
        for x in range(W):
            if visto[fila + x] or not color(x, y):
                continue
            semilla = px[x, y]
            pila = [(x, y)]
            visto[fila + x] = 1
            bx0 = bx1 = x
            by0 = by1 = y
            while pila:
                cx, cy = pila.pop()
                if cx < bx0: bx0 = cx
                if cx > bx1: bx1 = cx
                if cy < by0: by0 = cy
                if cy > by1: by1 = cy
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < W and y0_px <= ny < H and not visto[ny * W + nx] \
                            and color(nx, ny) and parecido(semilla, px[nx, ny]):
                        visto[ny * W + nx] = 1
                        pila.append((nx, ny))
            if (bx1 - bx0) * esc > 24 and (by1 - by0) * esc > 8:
                cajas.append(tuple(round(v * esc, 1) for v in (bx0, by0, bx1, by1)))
    return _unir_solapadas(cajas)


def _unir_solapadas(cajas):
    """Una celda con degradado o con una franja de otro tono se parte en varias
    manchas. Lo que se toca es lo mismo: se unen las cajas que se solapan.

    Es la contraparte de comparar el color al inundar: sin unir después, el
    corto de apertura del miércoles salía dos veces —una con duración cero—.
    """
    cajas = sorted(cajas)
    cambio = True
    while cambio:
        cambio = False
        for i in range(len(cajas)):
            for j in range(i + 1, len(cajas)):
                a, b = cajas[i], cajas[j]
                # SE SOLAPAN DE VERDAD, no se tocan. Con una tolerancia de dos
                # puntos volvían a unirse celdas vecinas que comparten borde —el
                # FÓSIL MÁGICO, el CLAQUETAZO y el Reconocimiento del sábado se
                # fundían en un bloque de 45 minutos—. Un trozo desprendido por
                # el degradado, en cambio, cae DENTRO de su celda.
                # CASI CONTENIDA, no apenas solapada. Un trozo desprendido por
                # el degradado cae DENTRO de su celda; dos celdas vecinas solo
                # se rozan. Con un umbral del 25% volvían a fundirse el
                # CLAQUETAZO y el Reconocimiento del sábado, que son dos: lo
                # cazó el contraste contra los vectores de MuPDF, donde son dos
                # rectángulos distintos.
                ancho = min(a[2], b[2]) - max(a[0], b[0])
                alto = min(a[3], b[3]) - max(a[1], b[1])
                menor = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if ancho > 0 and alto > 0 and ancho * alto > 0.80 * menor:
                    cajas[i] = (min(a[0], b[0]), min(a[1], b[1]),
                                max(a[2], b[2]), max(a[3], b[3]))
                    del cajas[j]
                    cambio = True
                    break
            if cambio:
                break
    return cajas


def _reparto(ls, cajas):
    """A qué celda pertenece cada línea de texto. UNA SOLA.

    Con una tolerancia hacia abajo —necesaria porque el texto se desborda de su
    recuadro— una línea cabía en dos celdas a la vez, y el rótulo del
    «Reconocimiento a Mabel Teresa Velosa» se colaba además en el CLAQUETAZO de
    encima. Se resuelve eligiendo: la celda que CONTIENE el centro de la línea
    y, si ninguna lo contiene, la más cercana por debajo, a no más de 7 pt.
    """
    de = {}
    for i, (_, lx0, ly0, lx1, ly1, t) in enumerate(ls):
        cx, cy = (lx0 + lx1) / 2, (ly0 + ly1) / 2
        dentro = [c for c in cajas if c[0] - 3 <= cx <= c[2] + 3 and c[1] <= cy <= c[3]]
        if not dentro:
            dentro = [c for c in cajas if c[0] - 3 <= cx <= c[2] + 3
                      and c[1] - 5 <= cy <= c[3] + 7]
            if len(dentro) > 1:
                dentro = [min(dentro, key=lambda c: min(abs(cy - c[1]), abs(cy - c[3])))]
        if dentro:
            de[i] = dentro[0]
    return de


def bloques(ls, cols, horas, cajas):
    """Una celda por mancha: sus dos horas salen del rectángulo y su contenido,
    de las líneas de texto que caen dentro."""
    # EL BORDE DE UNA CELDA CAE EN LA LÍNEA PUNTEADA, NO EN EL RÓTULO. Medido
    # en la retícula: la línea de cada fila va 6,4 pt POR ENCIMA del centro del
    # texto de su hora. Comparando contra el texto, la hora de FIN se corría una
    # fila hacia atrás en todos los bloques —la programación infantil terminaba
    # 12:45 en vez de 13:00, el club de pitch 10:00 en vez de 10:15— y como el
    # inicio sí caía bien, el error no se veía por ninguna parte.
    LINEA = 6.4
    lineas_fila = [((y0 + y1) / 2 - LINEA, h) for y0, y1, h in horas]

    def rotulo(y):
        return min(lineas_fila, key=lambda c: abs(c[0] - y))[1]

    reparto = _reparto(ls, cajas)
    regs = []
    for x0, y0, x1, y1 in cajas:
        cx = (x0 + x1) / 2
        sede = next((c['nombre'] for c in cols if c['x0'] - 14 <= cx <= c['x1'] + 14), '')
        if not sede:
            continue
        # EL TEXTO SE DESBORDA DE SU CELDA. En «Nuevas Miradas: RESURGENCIAS»
        # del viernes noche, las dos últimas líneas caen por debajo del borde
        # del recuadro. Exigiendo que la línea entera quepa, se perdían —y una
        # línea perdida es un dato que no publicamos—. Basta con que el CENTRO
        # de la línea caiga dentro, con un margen de media fila.
        dentro = [ls[i][5] for i, c in reparto.items() if c == (x0, y0, x1, y1)
                  and not MARCA.match(ls[i][5]) and not hora_reticula(ls[i][5])
                  and not RE_DIA.match(ls[i][5])]
        if not dentro:
            # UNA CELDA PUEDE NO TENER TEXTO Y AUN ASÍ SER PROGRAMACIÓN. Al pie
            # del viernes tarde hay un trozo rosa mudo: es el arranque de
            # «Territorios: PODEROSAS», cuyo rótulo el festival dibujó en la
            # página siguiente. Descartarlo movía la función quince minutos
            # más tarde de lo anunciado. Se conserva como colgajo y `parrilla()`
            # lo pega al bloque que lo continúa.
            regs.append({'sede': sede, 'hora': rotulo(y0), 'hasta': rotulo(y1),
                         'duracion_min': 0, 'lineas': [], '_colgajo': True,
                         'caja': [x0, y0, x1, y1]})
            continue
        ini, fin = rotulo(y0), rotulo(y1)
        if fin == ini:
            # una franja de una sola fila —el reconocimiento a Mabel Teresa
            # Velosa— cae entera dentro de un rótulo: dura hasta el siguiente.
            siguientes = [h for _, h in centros if h > ini]
            fin = min(siguientes) if siguientes else ini
        regs.append({'sede': sede, 'hora': ini, 'hasta': fin,
                     'duracion_min': _mins(fin) - _mins(ini),
                     'lineas': dentro, 'caja': [x0, y0, x1, y1]})
    return regs


def _mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def parrilla():
    ls = lineas(*PAGS_RETICULA)
    porpag = {}
    for l in ls:
        porpag.setdefault(l[0], []).append(l)
    dias, fuera = [], []
    for pag in sorted(porpag):
        pl = porpag[pag]
        dia = ''
        for _, _, _, _, _, t in pl:
            m = RE_DIA.match(t)
            if m:
                dia = f'2026-09-{int(m.group(1)):02d}'
        if not dia:
            fuera.append(pag)
            continue
        # se leen en orden: un rótulo roto hereda el a.m./p.m. del anterior
        horas, ap = [], ''
        for l in sorted(pl, key=lambda l: l[2]):
            h = hora_reticula(l[5], ap)
            if h:
                horas.append((l[2], l[4], h))
                ap = 'a' if h < '12:00' else 'p'
        horas.sort()
        if not horas:
            fuera.append(pag)
            continue
        cols = sedes_de(pl, horas[0][0])
        for b in bloques(pl, cols, horas, manchas(pag, horas[0][0] - 6)):
            b['dia'], b['pagina'] = dia, pag
            dias.append(b)
    return _unir_paginas(_pegar_colgajos(dias)), fuera


def _pegar_colgajos(bs):
    """Los trozos mudos del pie de una página se pegan al bloque que los
    continúa arriba de la siguiente, en la misma sede y el mismo día."""
    colgajos = [b for b in bs if b.get('_colgajo')]
    resto = [b for b in bs if not b.get('_colgajo')]
    for c in colgajos:
        cont = [b for b in resto if b['dia'] == c['dia'] and b['sede'] == c['sede']
                and b['pagina'] == c['pagina'] + 1
                and _mins(b['hora']) - _mins(c['hasta']) <= 15]
        if cont:
            b = min(cont, key=lambda b: b['hora'])
            b['_empieza_antes'] = (f"la página {c['pagina']} dibuja su arranque a las "
                                   f"{c['hora']}, sin rótulo")
            b['hora'] = min(b['hora'], c['hora'])
            b['duracion_min'] = _mins(b['hasta']) - _mins(b['hora'])
    return resto


def _unir_paginas(bs):
    """Un bloque que cruza el corte tarde/noche se dibuja en las DOS páginas.

    La ceremonia de clausura del sábado va de 6:15 a 8:00 y el PDF la parte: la
    página de la tarde la muestra hasta las 6:45 y la de la noche la retoma a
    las 7:00. Son la misma cosa —mismo día, misma sede, mismo texto— y se
    publican como una: si no, la app ofrece dos ceremonias y ninguna con su
    duración real.
    """
    por_clave = {}
    for b in sorted(bs, key=lambda b: (b['dia'], b['sede'], b['hora'])):
        k = (b['dia'], b['sede'], ' '.join(b['lineas']).lower())
        a = por_clave.get(k)
        # solo se unen si son CONTIGUOS y de páginas distintas: el mismo taller
        # repetido en dos franjas del mismo día son dos sesiones, no una.
        if a and b['pagina'] != a['pagina'] and _mins(b['hora']) - _mins(a['hasta']) <= 15:
            a['hasta'] = max(a['hasta'], b['hasta'])
            a['duracion_min'] = _mins(a['hasta']) - _mins(a['hora'])
            a['lineas'] = list(dict.fromkeys(a['lineas'] + b['lineas']))
            a['_partido'] = f"dibujado en las páginas {a['pagina']} y {b['pagina']}"
        else:
            por_clave[k] = b
            if a:
                por_clave[k + (b['hora'],)] = b
                por_clave[k] = a
    return sorted([v for v in por_clave.values()], key=lambda b: (b['dia'], b['hora'], b['sede']))


RE_DUR = re.compile(r'\b(\d):(\d{2}):(\d{2})\b')
RE_MIN = re.compile(r'\b(\d{1,3})\s*minutos\b', re.I)


def fichas():
    """Una ficha por obra, agrupada por el programa que la contiene.

    La cabecera de cada página trae la sección y el programa partidos por el
    logotipo («NARRATIVAS DIVERGENTES | caminos | PORTALES | del tiempo»): se
    reconstruyen quitando las palabras del logo y respetando el orden en x.
    """
    ls = lineas(*PAGS_FICHAS)
    porpag = {}
    for l in ls:
        porpag.setdefault(l[0], []).append(l)
    out = []
    for pag in sorted(porpag):
        pl = sorted(porpag[pag], key=lambda l: (l[2], l[1]))
        cab = [l for l in pl if l[2] < 40 and not re.fullmatch(
            r'caminos|del|tiempo|del tiempo', l[5].strip(), re.I)]
        titulo_cab = ' '.join(t for *_, t in sorted(cab, key=lambda l: (round(l[2] / 8), l[1])))
        cuerpo = [l for l in pl if l[2] >= 40]
        texto = '\n'.join(t for *_, t in cuerpo)
        out.append({'pagina': pag, 'cabecera': titulo_cab.strip(), 'texto': texto})
    return out


def academica():
    ls = lineas(*PAGS_ACADEMICA)
    porpag = {}
    for l in ls:
        porpag.setdefault(l[0], []).append(l)
    return [{'pagina': p,
             'texto': '\n'.join(t for *_, t in sorted(porpag[p], key=lambda l: (l[2], l[1])))}
            for p in sorted(porpag)]


def main():
    if not os.path.exists(PDF):
        sys.exit(f'falta {PDF} — bajalo del botón PROGRAMACIÓN de villadelcine.com')
    pa, fuera = parrilla()
    fi, ac = fichas(), academica()
    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'PROGRAMACIÓN «Caminos del tiempo» 2026 (PDF de 67 páginas) — botón '
        'PROGRAMACIÓN de villadelcine.com, subido el 18 sep 2026',
        que_aporta='la parrilla de los 4 días (día, hora de inicio y sede de cada '
                   'bloque), la ficha de cada obra agrupada por programa, y la Ruta '
                   'Académica',
        url=URL,
        metodo='el PDF trae capa de texto; se lee con pdftotext -bbox-layout porque '
               'en la retícula la columna es la SEDE y la fila la HORA: sin las cajas '
               'no se distingue el 1er piso del 2do en la misma sede. La hora de FIN '
               'no se deduce del alto del texto (va centrado en la celda): la duración '
               'sale de la ficha de cada obra'),
        'bloques': pa, 'fichas': fi, 'academica': ac},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(pa)} bloques de parrilla · {len(fi)} páginas de ficha · '
          f'{len(ac)} de ruta académica → {os.path.basename(OUT)}')
    if fuera:
        print(f'⚠ páginas de retícula sin día reconocido: {fuera}')
    for b in sorted(pa, key=lambda b: (b['dia'], b['hora'], b['sede'])):
        print(f"  {b['dia'][-2:]} {b['hora']}–{b['hasta']} {str(b['duracion_min']).rjust(3)}m "
              f"{b['sede'][:32]:33} {' / '.join(b['lineas'])[:52]}")


if __name__ == '__main__':
    main()
