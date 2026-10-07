#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-actividades-contraste.py — las fichas de actividad, tres veces.

POR QUÉ EXISTE (Juan, 21 sep 2026). Las fichas de actividad se extrajeron UNA
sola vez, con poppler, y dentro de esa única lectura ya se cometieron dos
errores: el umbral de altura de caja dejaba la ficha vacía, y una limpieza del
crédito se comió las siglas —el ENACC de la tallerista, el FPFC del
restaurador—. Los dos se vieron por casualidad. La casa lee cada fuente con
herramientas distintas y las enfrenta; a estas páginas no se les hizo.

LAS TRES LECTURAS, y cada una puede fallar donde la otra no:

  A · POPPLER `-bbox-layout` — la que produjo el sidecar que publicamos.
  B · PyMuPDF — otra librería sobre la misma capa de texto. Discrepa de poppler
      en cómo agrupa líneas y en el orden de lectura, que es justo donde este
      PDF muerde: la ficha de Estación Igüaque parte su primera frase en ocho
      cajas a la misma altura.
  C · VISION sobre los PÍXELES — no toca la capa de texto. Es la única que
      puede decir que lo que publicamos no está pintado en la página, o que la
      página muestra algo que las otras dos no traen.

A y B tienen que coincidir CARÁCTER A CARÁCTER: son el mismo dato leído dos
veces. Con C se compara por parecido, porque el OCR confunde mayúsculas
acentuadas y corta la última línea al pie; lo que baje del umbral se imprime
para mirarlo, no se descarta.

Y LA COBERTURA INVERSA, que es la pregunta que nadie hace: de todo lo que el
OCR VE en esas páginas, ¿qué no está en lo que extrajimos? Ahí es donde
aparecería un párrafo entero que los dos motores de texto se saltaron.

    /tmp/vdcenv/bin/python pipeline/villadelcine-2026-actividades-contraste.py
"""
import difflib
import importlib.util
from collections import Counter
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/villadelcine-2026/programacion-2026.pdf'
SIDECAR = f'{REPO}/festivals/staging/villadelcine-2026-actividades-pdf.json'
PARECIDO = 0.80

# FICHAS EN LAS QUE EL BLOQUE CONTIGUO NO SIRVE, y por qué. En ellas se compara
# el MULTICONJUNTO DE PALABRAS en vez del bloque común más largo: si las dos
# lecturas dicen exactamente las mismas palabras, el texto es el mismo aunque
# el OCR las agrupe en otro orden.
ORDEN_LIBRE = {
    52: 'la primera frase está compuesta en OCHO cajas a la misma altura '
        '(«¿Tienes» «un» «proyecto» «en» «desarrollo» «y» «quieres» «recibir») '
        'y Vision las devuelve agrupadas a su manera: «¿Tienes un / desarrollo '
        'y / quieres recibir / proyecto». Nosotros las ordenamos por coordenada '
        'izquierda-derecha, que es la que da una frase en español. Las palabras '
        'son las mismas; el bloque contiguo se rompe por el reagrupamiento.',
}


def _mod(nombre):
    """Importa un script del pipeline cuyo nombre lleva guiones."""
    ruta = f'{REPO}/pipeline/{nombre}.py'
    spec = importlib.util.spec_from_file_location(nombre.replace('-', '_'), ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


EXTRACTOR = _mod('villadelcine-2026-actividades-pdf')
OCRC = _mod('villadelcine-2026-ocr-contraste')

# Lo que el OCR ve en estas páginas y no es la ficha: la marca del festival, la
# franja y los rótulos de sección. Se declara para que la cobertura inversa
# señale contenido de verdad y no el membrete.
CHROME = re.compile(
    r'^(12|festival|villa|del cine|villa del cine|caminos|del|tiempo|del tiempo|'
    r'caminos del tiempo|ruta academica|ruta academica cinecamino|cinecamino|'
    r'eventos especiales|nota|por sus 40 anos|charla|talleres|claquetazo|'
    r'estacion iguaque|masterclass|charlas|festival villa del cine)$')


# PALABRAS QUE EL OCR NO VE Y SÍ ESTÁN PINTADAS. Cada una comprobada MIRANDO
# LOS PÍXELES, ampliados, no deducida. Una entrada acá es una limitación del
# OCR declarada, no un permiso para publicar lo que no está en el papel.
OCR_CIEGO = {
    (52, 'en'): 'la caja de dos letras de «un proyecto EN desarrollo». Vision se '
                'la salta —es la más pequeña de las ocho de esa línea— y las dos '
                'lecturas de la capa de texto sí la traen. Comprobado en el '
                'recorte ampliado de la línea: dice «¿Tienes un proyecto en '
                'desarrollo y quieres recibir», en ese orden.',
}


# LO QUE EL OCR VE EN ESTAS PÁGINAS Y NO ES UNA FICHA PUBLICADA, mirado en la
# página (PDF del 6 oct). (página, comienzo normalizado) → por qué.
VISTO_FUERA = {
    (14, 'unkt'): 'la transcripción fonética «/unkɨ/ · muisca» bajo UNQUY: adorno del nombre',
    (15, 'exposicion fotografica'): 'la EXPOSICIÓN «Memorias de Aquileo Venganza», «durante todo '
        'el festival»: no tiene casilla en la retícula, ni sede ni hora. No se publica; '
        'queda en las preguntas al festival',
    (15, 'un recorrido fotografico'): 'ídem, su párrafo',
    (15, 'historia y restauracion'): 'ídem', (15, 'villa de leyva desde sus'): 'ídem',
    (15, 'una nueva version 4k'): 'ídem',
    (55, 'estudiantes'): 'el crédito de EL FÓSIL MÁGICO, que es OBRA y lo lee -obras-pdf.py',
    (58, '16 vier'): 'el día de la ficha («16, VIERNES»), en la columna de fechas',
}


def lee_mupdf(pagina):
    """LECTURA B. Misma idea que el extractor —cuerpo por altura de caja,
    orden por (y, x), párrafos por el salto— con otra librería."""
    import fitz
    d = fitz.open(PDF)
    ls, vistas = [], set()
    for b in d[pagina - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            # los tramos van PEGADOS: cada uno trae sus propios espacios, y
            # unirlos con ' ' metía uno de más en cada cambio de cursiva
            t = re.sub(r'\s+', ' ', ''.join(s['text'] for s in l['spans'])).strip()
            # EL PDF DEL 6 OCT DIBUJA EL CUERPO DOS VECES, con la misma caja y
            # el mismo texto (relleno + trazo). Poppler lo funde; MuPDF lo
            # devuelve dos veces y la frase salía repetida a mitad de camino.
            clave = (tuple(round(v, 1) for v in l['bbox']), t)
            if t and clave not in vistas:
                vistas.add(clave)
                x0, y0, _, y1 = l['bbox']
                ls.append((y0, x0, y1 - y0, t))
    d.close()
    return ls


def main():
    if not os.path.exists(SIDECAR):
        sys.exit(f'✗ falta {SIDECAR}: correr antes el extractor')
    # PDF del 6 oct: hasta dos fichas por página
    fichas = json.load(open(SIDECAR, encoding='utf-8'))['actividades']
    pub = {}
    for f in fichas:
        pub.setdefault(f['pagina'], []).append(f)
    pags = sorted(pub)

    rutas = [OCRC.render(p) for p in pags]
    visto = OCRC.ocr(rutas)
    ocr_por_pag = {p: visto[r] for p, r in zip(pags, rutas)}

    fallos, avisos, iguales = [], [], 0
    print(f'{len(pags)} fichas · tres lecturas: poppler, MuPDF y Vision sobre '
          f'los píxeles\n')
    for p, a in [(p, a) for p in pags for a in pub[p]]:
        # ── B · MuPDF, mismo algoritmo, otra librería ────────────────────────
        ls = lee_mupdf(p)
        cuerpo = [(y, x, h, t) for y, x, h, t in ls if h < EXTRACTOR.CUERPO]
        ps = EXTRACTOR.parrafos(cuerpo)
        e = next(e for e in EXTRACTOR.PAGINAS[p] if e[0] == a['titulo'])
        ancla, extra = e[1], (e[2] if len(e) > 2 else 0)
        if ancla is None:
            sin_b = ' '.join(ps)
        else:
            i = next((k for k, x in enumerate(ps) if ancla in x), None)
            sin_b = (' '.join([ancla + ps[i].split(ancla, 1)[1]] + ps[i + 1:i + 1 + extra])
                     if i is not None else '')
        if not sin_b:
            fallos.append(f'p{p} «{a["titulo"]}»: MuPDF no encuentra la sinopsis')
        elif ' '.join(sin_b.split()) != ' '.join(a['sinopsis'].split()):
            fallos.append(f'p{p} «{a["titulo"]}»: poppler y MuPDF NO coinciden\n'
                          f'      poppler: {a["sinopsis"][:90]}\n'
                          f'      mupdf  : {sin_b[:90]}')
        else:
            iguales += 1

        # ── C · Vision sobre los píxeles ────────────────────────────────────
        lineas_ocr = ocr_por_pag[p]
        plano = norm(' '.join(lineas_ocr))
        na = norm(a['sinopsis'])
        # La sinopsis tiene que estar CONTENIDA en lo que se ve: se busca su
        # bloque común más largo, que con el OCR limpio es casi toda ella.
        #
        # `autojunk=False` NO ES UN DETALLE. Con el valor por omisión, difflib
        # marca como «basura» todo carácter que aparezca en más del 1% de una
        # secuencia larga —o sea el espacio y media abecedario— y el bloque
        # común más largo se desploma a 1 carácter. Este mismo paso reprobó
        # cinco de diez fichas con «el OCR solo confirma el 0%» mientras el OCR
        # las leía enteras y correctas. El defecto era del verificador.
        if p in ORDEN_LIBRE:
            faltan = sorted(w for w in (Counter(na.split()) - Counter(plano.split()))
                            if (p, w) not in OCR_CIEGO)
            cobertura = 1.0 if not faltan else 0.0
            como = 'palabras'
            if faltan:
                avisos.append(f'p{p} «{a["titulo"]}»: el OCR no ve estas '
                              f'palabras de la sinopsis: {faltan[:8]}')
        else:
            m = difflib.SequenceMatcher(None, na, plano, autojunk=False) \
                .find_longest_match(0, len(na), 0, len(plano))
            cobertura = m.size / max(len(na), 1)
            como = 'bloque'
            if cobertura < PARECIDO:
                avisos.append(f'p{p} «{a["titulo"]}»: el OCR solo confirma el '
                              f'{cobertura:.0%} de la sinopsis — mirar la página')
        estado = '✓' if cobertura >= PARECIDO else '⚠'
        print(f'  {estado} p{p:2} {a["titulo"][:42]:44} A=B ✓  '
              f'píxeles {cobertura:.0%} ({como})')

        # ── cobertura inversa: ¿se ve algo que no leímos? ───────────────────
        if a is not pub[p][-1]:
            continue                      # la inversa, una vez por página
        nuestro = norm(' '.join(' '.join([x['titulo'], x.get('_titulo_pdf', ''),
                                          x.get('credito', ''), x['sinopsis']])
                                for x in pub[p]))
        for l in lineas_ocr:
            nl = norm(l)
            if not nl or len(nl) < 8 or CHROME.match(nl):
                continue
            if nl in nuestro:
                continue
            if OCRC.LOGOS.match(nl):
                continue          # marcas de aliados impresas como imagen
            if any(p == p0 and nl.startswith(k0) for (p0, k0) in VISTO_FUERA):
                continue
            mejor = difflib.SequenceMatcher(None, nl, nuestro, autojunk=False) \
                .find_longest_match(0, len(nl), 0, len(nuestro))
            if mejor.size / len(nl) < 0.75:
                avisos.append(f'p{p}: el OCR ve «{l[:70]}» y no está en lo que '
                              f'extrajimos')

    print(f'\npoppler == MuPDF en {iguales}/{len(fichas)} fichas')
    for x in avisos:
        print('   ⚠', x)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for x in fallos:
            print('   ✗', x)
        sys.exit(1)
    # UN AVISO NO ES UN ✓. La primera versión imprimía «las tres lecturas dicen
    # lo mismo» aunque acabara de reportar cinco fichas al 0% de cobertura en
    # píxeles: el ✓ miraba solo `fallos`. Un verificador que se felicita
    # mientras avisa de algo no sirve para lo que existe.
    if avisos:
        print(f'\n⚠ las dos lecturas de la capa de texto coinciden, pero quedan '
              f'{len(avisos)} aviso(s) sin explicar. Mirarlos antes de dar el '
              f'contraste por bueno.')
        sys.exit(1)
    print('\n✓ las tres lecturas dicen lo mismo: la capa de texto, leída con dos '
          'librerías, y lo que de verdad está pintado en la página')


if __name__ == '__main__':
    main()
