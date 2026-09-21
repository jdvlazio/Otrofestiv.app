#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-actividades-pdf.py — la ficha de cada actividad (pp. 51–60).

LO QUE FALTABA Y NADIE VIO. `-obras-pdf.py` lee las fichas de OBRA, que llegan
hasta la página 50, y se detiene ahí. Las diez páginas siguientes son las fichas
de la RUTA ACADÉMICA —una por actividad, con quién la da y un párrafo de qué
es— y no las leía nadie. Resultado: las 24 actividades del festival se
publicaban con título, hora y sede y ni una línea de contenido. Alguien abría
«Dirigir el tiempo» y no sabía si era una charla, un taller o una proyección.

CÓMO SE LEEN. Por TAMAÑO DE FUENTE, que en estas páginas es la estructura:

    32,5 pt → la franja («RUTA ACADÉMICA - CineCamino»)
    ~32  pt → el nombre de la actividad
    ~17  pt → su subtítulo, cuando lo tiene
     9   pt → el crédito y el cuerpo

Y dentro de los 9 pt, el ORDEN DE LECTURA es (y, x), no el del flujo de texto:
la página de Estación Igüaque parte su primera frase en ocho cajas a la misma
altura y `pdftotext` las devuelve como «¿Tienes un proyecto en desarrollo y
quieres recibir / retroalimentación…», con el verbo fuera de sitio. Ordenando
por coordenada la frase se rearma sola.

Los párrafos se separan por el SALTO: dentro de un párrafo las líneas van a 9,7
pt; entre párrafos, a 19,5. El último párrafo es la sinopsis; lo de antes es
crédito —salvo donde se declare, porque en Estación Igüaque el primer párrafo
no es un crédito sino la pregunta con la que abre la ficha—.

CADA PÁGINA VA DECLARADA con el título que publicamos, porque el de la ficha no
siempre es el mismo («UNIVERSOS EXPANDIDOS CON EL PODCAST» se programa como la
charla «Gente que hace cine»). Una página sin entrada, o una entrada cuya
página no aparece, hacen fallar el paso.

Lee   fuentes/villadelcine-2026/programacion-2026.pdf  (p. 15 y pp. 51–60)
Esc.  festivals/staging/villadelcine-2026-actividades-pdf.json
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/villadelcine-2026/programacion-2026.pdf'
OUT = f'{REPO}/festivals/staging/villadelcine-2026-actividades-pdf.json'

SALTO_PARRAFO = 15.0     # pt entre párrafos; dentro de uno son ~9,7
CUERPO = 20.0            # alto de caja: el texto de 9 pt mide 12,4; los
                         # titulares, 44. Es el alto de la CAJA, no el cuerpo
                         # de la fuente — poner 11 aquí dejaba la ficha vacía.

# página → [(título que publicamos, ancla del párrafo de sinopsis)]
#
# El TÍTULO es el de `NOMBRE_ACTIVIDAD` en el crudo: el de la ficha y el de la
# retícula no siempre coinciden («UNIVERSOS EXPANDIDOS CON EL PODCAST» se
# programa como la charla «Gente que hace cine») y manda el que ya publicamos.
#
# La ANCLA son las primeras palabras del párrafo de la sinopsis. Con ella el
# paso se verifica solo: si el festival reexporta el PDF y la maqueta cambia,
# falla en la cara en vez de publicar el párrafo de al lado. `None` significa
# «toda la página es sinopsis, no hay crédito».
#
# Y permite DOS FICHAS EN UNA PÁGINA, que es como está maquetada la 15:
# la Fundación Patrimonio Fílmico arriba y Mabel Velosa abajo. Sin ancla, el
# lector de fichas de obra las mezclaba y las dos salían con el mismo párrafo
# revuelto — se ve en `-obras-pdf.json`.
PAGINAS = {
    15: [('Reconocimiento a Mabel Teresa Velosa', 'Hay personas que no solo')],
    52: [('Estación Igüaque', None)],
    53: [('Club de Pitch — Encuentro Work in Progress', 'Un espacio de encuentro')],
    54: [('Claquetazo — Laboratorio de creación', 'Experiencia formativa')],
    55: [('Taller Eureka — Del collage al póster', 'Un taller para acercarse')],
    56: [('Gente que hace cine', 'Una conversación para descubrir')],
    57: [('Maquillaje: transformaciones del tiempo', 'Un encuentro para descubrir')],
    58: [('Dirigir el tiempo', 'Una conversación cercana')],
    59: [('Trazos — Charla con realizadores', 'Un encuentro con las y los')],
    60: [('Proceso de restauración de La paga y Aquileo Venganza', 'Una charla sobre restauración')],
}

# La página 51 no es una ficha: es el índice de la Ruta Académica, y trae una
# NOTA que no está en ninguna otra parte del PDF. Se guarda como dato del
# festival, no de una actividad.
NOTA_RUTA = 51

RE_DUR = re.compile(r'Duraci[óo]n\s+(\d{1,3})\s*min', re.I)


def lineas(pagina):
    """[(y, x, tamaño, texto)] de una página, con pdftotext -bbox-layout."""
    xml = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(pagina),
                          '-l', str(pagina), PDF, '-'],
                         capture_output=True, text=True).stdout
    out = []
    for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" '
                         r'yMax="([\d.]+)">(.*?)</line>', xml, re.S):
        x0, y0, _, y1, inner = m.groups()
        t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', inner)).strip()
        if t:
            out.append((float(y0), float(x0), float(y1) - float(y0), t))
    return out


def parrafos(ls):
    """Las líneas de cuerpo, agrupadas en párrafos por el salto vertical."""
    ls = sorted(ls, key=lambda r: (round(r[0], 1), r[1]))
    filas, actual, y_ant = [], [], None
    for y, x, _, t in ls:
        if y_ant is not None and abs(y - y_ant) > 1.5:
            filas.append((y_ant, ' '.join(actual)))
            actual = []
        actual.append(t)
        y_ant = y
    if actual:
        filas.append((y_ant, ' '.join(actual)))

    ps, cur, prev = [], [], None
    for y, t in filas:
        if prev is not None and (y - prev) >= SALTO_PARRAFO:
            ps.append(' '.join(cur))
            cur = []
        cur.append(t)
        prev = y
    if cur:
        ps.append(' '.join(cur))
    return ps


def ficha(pagina, titulo, ancla):
    ls = lineas(pagina)
    if not ls:
        sys.exit(f'✗ p{pagina}: sin texto. ¿Cambió el PDF?')
    grandes = [t for _, _, h, t in sorted(ls, key=lambda r: r[0]) if h >= CUERPO]
    cuerpo = [(y, x, h, t) for y, x, h, t in ls if h < CUERPO]
    ps = parrafos(cuerpo)
    if not ps:
        sys.exit(f'✗ p{pagina} «{titulo}»: la ficha no trae cuerpo de 9 pt.')
    if ancla is None:
        credito, sinopsis = '', ' '.join(ps)
    else:
        i = next((k for k, x in enumerate(ps) if x.startswith(ancla)), None)
        if i is None:
            sys.exit(f'✗ p{pagina} «{titulo}»: no aparece el párrafo que empieza '
                     f'por «{ancla}». Párrafos leídos: '
                     + ' | '.join(x[:40] for x in ps))
        ps, resto = ps[:i + 1], ps[i + 1:]
        if resto and pagina not in (15,):
            sys.exit(f'✗ p{pagina} «{titulo}»: sobra texto después de la '
                     f'sinopsis — «{resto[0][:60]}». Mirar la página.')
        # EL CRÉDITO VA VERBATIM, sin limpiar. En estas páginas comparte cuerpo
        # con el subtítulo de la pieza («Dir. Luna Martínez Rodríguez» + «DEL
        # COLLAGE AL PÓSTER»), y separarlos a ojo cuesta más de lo que vale:
        # `credito` NO se publica —no existe en el contrato—, se guarda para
        # poder rastrear de dónde salió cada ficha. Intentar depurarlo por
        # mayúsculas se comía además las siglas, que sí son parte del crédito:
        # el ENACC de la tallerista y el FPFC del restaurador.
        credito, sinopsis = ' · '.join(ps[:-1]), ps[-1]
    d = {'titulo': titulo, '_titulo_pdf': ' / '.join(g for g in grandes
                                                    if 'RUTA ACAD' not in g.upper()),
         'sinopsis': sinopsis, 'pagina': pagina,
         '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                         f'p{pagina}', 'date': '2026-09-21'}}
    if credito:
        d['credito'] = credito
        m = RE_DUR.search(credito)
        if m:
            d['duracion_ficha_min'] = int(m.group(1))
    if len(sinopsis) < 80:
        sys.exit(f'✗ p{pagina} «{titulo}»: la sinopsis mide {len(sinopsis)} '
                 f'caracteres — «{sinopsis}». Mirar la página.')
    return d


def main():
    if not os.path.exists(PDF):
        sys.exit(f'✗ falta el PDF en {PDF} — está en fuentes/, que va gitignored')
    fichas = [ficha(p, t, a) for p, es in sorted(PAGINAS.items())
              for t, a in es]

    nota = ' '.join(parrafos([(y, x, h, t) for y, x, h, t in lineas(NOTA_RUTA)
                              if h < CUERPO])).strip()
    if 'certificaci' not in norm(nota):
        sys.exit(f'✗ p{NOTA_RUTA}: no se encuentra la nota de la Ruta Académica. '
                 f'Leído: «{nota[:120]}»')

    json.dump({'_provenance': provenance(
        'PROGRAMACIÓN «Caminos del tiempo» 2026 (PDF), páginas 51–60: la ficha '
        'de cada actividad de la Ruta Académica',
        que_aporta=f'el crédito y la descripción de {len(fichas)} actividades, '
                   f'que el festival publica y nosotros no leíamos',
        url='https://villadelcine.com/wp-content/uploads/2026/09/'
            'Programacion-caminos-del-tiempo-2026_compressed.pdf',
        metodo='por tamaño de fuente (32 pt el nombre, 9 pt el cuerpo) y en '
               'orden de lectura (y, x): la primera frase de Estación Igüaque '
               'viene partida en ocho cajas y el flujo de texto la desordena'),
        'actividades': fichas,
        'nota_ruta_academica': nota},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{len(fichas)} fichas de actividad → {OUT.split("/")[-1]}')
    for f in fichas:
        print(f'  p{f["pagina"]} {f["titulo"][:44]:46} {len(f["sinopsis"]):3} car.'
              f'{"  dur " + str(f["duracion_ficha_min"]) if f.get("duracion_ficha_min") else ""}')
    print(f'\nnota de la Ruta Académica (p{NOTA_RUTA}): {nota[:150]}')


if __name__ == '__main__':
    main()
