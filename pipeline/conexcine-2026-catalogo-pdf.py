#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-catalogo-pdf.py — qué cortos van en cada programa.

LA PÁGINA 3 del PDF oficial es el catálogo, y no viene como lista: viene como
PROSA. Cada programa se describe en un párrafo que termina «…, con los cortos:
El Chucur (Nariño), Hilo al cielo (Córdoba) … y Los años del conejo
(Antioquia).» El paréntesis es el DEPARTAMENTO, no el país: todas son
colombianas, y eso lo dice el propio festival («historias de realizadores de
distintos territorios del país»).

TRES TRAMPAS DE ESTE PDF, todas medidas:

  1. `pdftotext -raw` pega las palabras de los títulos compuestos con la
     tipografía decorativa: «Bullerengue:ritmoquesiguesonando». Con `-layout`
     los espacios sobreviven, así que se lee en layout y se re-une por líneas.
  2. El ToUnicode está roto en esa misma tipografía: «÷ƣ÷ĥŀŤ (Tolima)» es
     «Avatares». No se adivina — va en MOJIBAKE, con la fuente que lo dice.
  3. Cortar la lista en el primer punto parte «Bogotá D.C.» en «Bogotá D». La
     lista termina en el punto que sigue a un paréntesis cerrado, no en
     cualquiera.

LA COMPETENCIA VIRTUAL NO ES UNA FUNCIÓN. Son ocho cortos en el YouTube de
FEDECAJAS, «disponibles del 11 al 25 de septiembre» para el Premio del Público:
no tienen día, ni hora, ni sede. Se extraen igual —son parte del festival— y se
marcan `virtual`, para que quien decida si van a la app lo haga con el dato
delante y no por olvido.

Salida: festivals/staging/conexcine-2026-catalogo.json
"""
import json
import os
import html
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/conexcine-2026/programacion-2026.pdf'
OUT = f'{REPO}/festivals/staging/conexcine-2026-catalogo.json'
URL = ('https://drive.google.com/file/d/1x0l0MwffrReBexjv_d312trbZvZ5JP5p/view'
       ' (enlazado desde https://www.fedecajas.com/conexcine/)')

# El título que el PDF entrega ilegible, y de dónde sale el bueno.
MOJIBAKE = {
    # «Reflejos», NO «Avatares». El registro de radar #719 había transcrito
    # «Avatares» y yo lo copié sin más; el OCR de la página rasterizada leyó
    # «Reflejos (Tolima)» y el recorte de la imagen lo confirma a simple vista.
    # Es la razón de ser de la tercera lectura: ni poppler ni MuPDF pueden
    # desmentir un mapa de caracteres roto, porque los dos leen el mismo mapa.
    '÷ƣ÷ĥŀŤ': ('Reflejos',
               'Vision OCR sobre la página 3 rasterizada a 200 dpi, confirmado '
               'mirando el recorte: «cortos: Reflejos (Tolima), Por quien '
               'derraman las lágrimas (Valle del Cauca)…». El radar #719 decía '
               '«Avatares» y estaba equivocado'),
}

# Los programas, con la frase EXACTA con la que el PDF los titula. Van
# declarados porque el número y el nombre son la clave con que la parrilla los
# llama («PROGRAMA 3: Horizontes que florecen»): si el PDF cambiara uno, este
# paso tiene que fallar, no emparejar a medias.
PROGRAMAS = [
    ('Competencia Adultos', 1, 'AVENTURAS MÁGiCAS Y AMiSTADES iNOLViDABLES',
     'Aventuras mágicas y amistades inolvidables'),
    ('Competencia Adultos', 2, 'ENTRE EL MAR Y LA LUNA', 'Entre el mar y la luna'),
    ('Competencia Adultos', 3, 'HORiZONTES QUE FLORECEN', 'Horizontes que florecen'),
    ('Competencia Adultos', 4, 'TRANSiTANDO DEL NORTE AL SUR',
     'Transitando del norte al sur'),
    ('Competencia Juvenil', 1, 'VOCES, MiRADAS Y PAiSAJES PROPiOS',
     'Voces, miradas y paisajes propios'),
    ('Competencia Juvenil', 2, 'CAMiNO DE HiSTORiAS ViVAS', 'Camino de historias vivas'),
]
SUELTAS = [
    ('Competencia En(Foco) Santanderes', 'COMPETENCIA EN (FOCO) SANTANDERES'),
    ('Competencia Virtual', 'COMPETENCiA ViRTUAL'),
]

# LOS TRES LARGOS, que la página 3 imprime en su propio recuadro con día, hora
# y duración — el único sitio del PDF donde aparece un metraje.
RE_LARGO = re.compile(r'(\d{2,3})\s*min\.', re.I)


def columnas(pagina):
    """El texto de la página, UNA CADENA POR COLUMNA.

    La página 3 va a dos columnas y `-layout` las entrelaza: buscando «con los
    cortos:» hacia adelante desde una cabecera se recogía la lista del programa
    de al lado, y los conteos salían 7/8/8/4 donde el festival pone 6/6/6/5.

    Las columnas no se adivinan por el hueco entre palabras —el texto está
    JUSTIFICADO y sus huecos internos son tan grandes como el que separa una
    columna de la otra: con umbral de hueco, «1. AVENTURAS MÁGiCAS Y AMiSTADES»
    se pegaba con «2. ENTRE EL MAR Y LA LUNA»—. Se toman de los renglones de
    CUERPO, que son los largos y empiezan siempre en el borde izquierdo de su
    columna; los fragmentos sueltos caen después en la banda que los contiene.
    """
    x = subprocess.run(['pdftotext', '-f', str(pagina), '-l', str(pagina),
                        '-bbox-layout', PDF, '-'], capture_output=True, text=True).stdout
    L = []
    for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" '
                         r'xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', x, re.S):
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(5)))).strip()
        if t:
            L.append({'x': float(m.group(1)), 'y': float(m.group(2)), 't': t})
    bordes = []
    for l in sorted((l for l in L if len(l['t']) > 45), key=lambda l: l['x']):
        if not bordes or l['x'] - bordes[-1] > 60:
            bordes.append(l['x'])
    out = []
    for i, b in enumerate(bordes):
        a, z = b - 15, (bordes[i + 1] - 15) if i + 1 < len(bordes) else 1e9
        filas = []
        for l in sorted((l for l in L if a <= l['x'] < z),
                        key=lambda l: (round(l['y'] / 3), l['x'])):
            if filas and abs(l['y'] - filas[-1]['y']) < 3:
                filas[-1]['t'] += ' ' + l['t']
            else:
                filas.append(dict(l))
        out.append(' '.join(f['t'] for f in filas))
    return out


def limpia(t):
    # El PDF cuela caracteres de control delante de los títulos rotos («\x8a»
    # antes del mojibake): con ellos, la clave de MOJIBAKE nunca casa y la
    # corrección no se aplica sin decir nada. Se quitan antes de buscar.
    t = ''.join(c for c in t if c.isprintable()).strip(' .,;')
    return MOJIBAKE.get(t, (t,))[0]


def corta_lista(t, desde):
    """La lista de cortos que sigue a «con los cortos:», hasta el punto que va
    detrás de un paréntesis cerrado. Cortar en el primer punto parte «Bogotá
    D.C.» y deja un departamento llamado «Bogotá D»."""
    m = re.search(r'con los cortos:(.*?)\)\s*\.', t[desde:], re.S)
    return (m.group(1) + ')') if m else ''


# Los 32 departamentos y Bogotá. El paréntesis de la lista es SIEMPRE uno de
# ellos; sirve de ancla para cortar los títulos y de red para no tomar por obra
# un paréntesis cualquiera de la prosa.
DEPTOS = {
    'amazonas', 'antioquia', 'arauca', 'atlántico', 'bolívar', 'boyacá', 'caldas',
    'caquetá', 'casanare', 'cauca', 'cesar', 'chocó', 'córdoba', 'cundinamarca',
    'guainía', 'guaviare', 'huila', 'la guajira', 'magdalena', 'meta', 'nariño',
    'norte de santander', 'putumayo', 'quindío', 'risaralda', 'san andrés',
    'santander', 'sucre', 'tolima', 'valle del cauca', 'vaupés', 'vichada',
    'bogotá d.c.',
}


def parte(lista):
    """«A (X), B (Y) y C (Z)» → [(A,X), (B,Y), (C,Z)].

    NO se corta por comas: «¡Corroncho, y qué! (Atlántico)» lleva una dentro y
    partiendo por comas el corto se publicaba como «qué!». El ancla es el
    PARÉNTESIS con el departamento —lista cerrada—, y el título es todo lo que
    va entre el paréntesis anterior y el siguiente.
    """
    obras, pos = [], 0
    for m in re.finditer(r'\(([^)]+)\)', lista):
        depto = m.group(1).strip()
        tit = lista[pos:m.start()]
        pos = m.end()
        if depto.lower() not in DEPTOS:
            continue
        tit = re.sub(r'^[\s,;.]*(?:y|e)\s+', '', tit.strip())
        tit = limpia(tit)
        if tit:
            obras.append({'titulo': tit, 'departamento': depto})
    return obras


def busca(cols, cabecera):
    """La columna y la posición donde está una cabecera. Devuelve (None, -1)
    si no aparece en ninguna: eso es un fallo, no un cero."""
    for c in cols:
        i = c.find(cabecera)
        if i >= 0:
            return c, i
    return None, -1


def main():
    cols = columnas(3)
    obras, avisos = [], []

    for seccion, num, cabecera, nombre in PROGRAMAS:
        col, i = busca(cols, cabecera)
        if i < 0:
            avisos.append(f'no está la cabecera «{cabecera}» en la página 3')
            continue
        lista = corta_lista(col, i)
        if not lista:
            avisos.append(f'«{cabecera}»: no se halló su «con los cortos:»')
            continue
        for o in parte(lista):
            obras.append({**o, 'seccion': seccion, 'programa': f'PROGRAMA {num}: {nombre}',
                          'pais': 'Colombia', 'pagina': 3,
                          '_src': {'url': URL, 'date': '2026-09-19'}})

    for seccion, cabecera in SUELTAS:
        col, i = busca(cols, cabecera)
        if i < 0:
            avisos.append(f'no está la cabecera «{cabecera}» en la página 3')
            continue
        lista = corta_lista(col, i)
        if not lista:
            avisos.append(f'«{cabecera}»: no se halló su «con los cortos:»')
            continue
        for o in parte(lista):
            obras.append({**o, 'seccion': seccion, 'programa': '',
                          'pais': 'Colombia', 'pagina': 3,
                          **({'virtual': True} if 'Virtual' in seccion else {}),
                          '_src': {'url': URL, 'date': '2026-09-19'}})

    # los tres largos: título, duración, día y hora, en su recuadro
    largos = []
    for tit, dur, dia, hora in (('El Juego de la Vida', 95, '2026-09-24', '16:00'),
                                ('Adiós al Amigo', 118, '2026-09-25', '17:30'),
                                ('MU-KI-RA', 81, '2026-09-26', '10:00')):
        if not any(f'{dur} min.' in c for c in cols):
            avisos.append(f'«{tit}»: la página 3 ya no imprime «{dur} min.»')
        largos.append({'titulo': tit, 'duracion_min': dur, 'dia': dia, 'hora': hora,
                       'seccion': 'Proyecciones Especiales', 'pais': 'Colombia',
                       'pagina': 3, '_src': {'url': URL, 'date': '2026-09-19'}})

    json.dump({'_provenance': provenance(
        'Programación Oficial CONEXCINE 2026 (PDF), página 3 — el catálogo',
        que_aporta='qué cortos componen cada programa, con su departamento de '
                   'origen, y la duración de los tres largometrajes',
        url=URL,
        metodo='la página describe cada programa en prosa y cierra con «con los '
               'cortos: …»; la lista se corta en el punto que sigue a un '
               'paréntesis para no partir «Bogotá D.C.», y se lee en -layout '
               'porque -raw pega las palabras de la tipografía decorativa'),
        'obras': obras, 'largos': largos,
        'mojibake_corregido': {k: {'publicado': v[0], 'fuente': v[1]}
                               for k, v in MOJIBAKE.items()},
        'avisos': avisos},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    import collections
    c = collections.Counter((o['seccion'], o['programa']) for o in obras)
    print(f'{len(obras)} cortos · {len(largos)} largos → {OUT.split("/")[-1]}')
    for (s, p), n in c.items():
        print(f'  {n:2}  {s:34} {p}')
    if avisos:
        print('\n✗ ' + '\n✗ '.join(avisos))
        sys.exit(1)


if __name__ == '__main__':
    main()
