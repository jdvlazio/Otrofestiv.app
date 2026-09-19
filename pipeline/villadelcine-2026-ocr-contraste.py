#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-ocr-contraste.py — la tercera lectura: lo que SE VE en la página.

POR QUÉ UNA TERCERA (19 sep 2026). Las dos primeras leen la CAPA DE TEXTO del
PDF: poppler y MuPDF discrepan en cómo agrupan líneas, pero preguntan al mismo
sitio. Las dos comparten, por tanto, el mismo punto ciego: si la capa de texto
dice algo que la página no muestra, las dos lo creen; y si la página muestra
algo que la capa no trae, ninguna se entera.

No es hipotético. Este PDF ya tiene un caso: «#Hija» está en la capa de texto
de la página del jueves y NO está pintado en ninguna parte — sobra de una
versión anterior en Canva. Lo tratamos como fantasma porque lo miramos a ojo,
no porque nada lo comprobara.

QUÉ HACE. Rasteriza las páginas y las lee con Vision (el OCR del sistema, el
mismo de Live Text): píxeles a texto, sin tocar la capa. Y compara en las dos
direcciones, que son dos preguntas distintas:

  · ¿PUBLICAMOS ALGO QUE NO SE VE? Cada línea que extrajimos tiene que
    aparecer en el OCR de su página. Lo que no aparezca es un fantasma: o lo
    declaramos, o lo estamos publicando y no existe en el papel.
  · ¿SE VE ALGO QUE NO LEÍMOS? Cada línea del OCR tiene que estar en lo
    extraído o en el adorno. Lo que no, es contenido del festival que los dos
    motores de texto se saltaron.

EL OCR SE EQUIVOCA, y por eso el cruce es POR PARECIDO y no exacto: confunde
mayúsculas acentuadas, parte títulos largos en dos líneas y se inventa alguna
tilde. Un umbral de parecido del 82% sobre el texto normalizado deja pasar esos
ruidos y sigue cazando lo que falta de verdad. Lo que quede por debajo se
imprime para mirarlo, no se descarta en silencio.

    python3 pipeline/villadelcine-2026-ocr-contraste.py
    python3 pipeline/villadelcine-2026-ocr-contraste.py --todo   # las 67 páginas
"""
import difflib, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/villadelcine-2026/programacion-2026.pdf'
PAR = f'{REPO}/festivals/staging/villadelcine-2026-parrilla.json'
PAG = f'{REPO}/fuentes/villadelcine-2026/pag'
SWIFT = f'{REPO}/pipeline/ficma-2026-ocr.swift'
DPI = 200                      # más que los 150 de la segmentación: el OCR agradece
PARECIDO = 0.82

# Lo que el OCR ve y no es contenido: la marca, los rótulos de los ejes y las
# horas de la columna izquierda. Mismo criterio que la cobertura.
# OJO: se compara contra el texto YA NORMALIZADO (sin tildes ni puntuación),
# así que «04:45 p.m» llega como «04 45 p m». Escribir el patrón con los dos
# puntos no casa nunca, y las 130 horas de la columna izquierda salían como
# contenido sin leer.
ADORNO = re.compile(
    r'^(12|festival|villa|del cine|caminos|del|tiempo|del tiempo|septiembre|lugar|hora|'
    r'manana|tarde|noche|tarde noche|lunes|martes|miercoles|jueves|viernes|sabado|'
    r'domingo|[0-9o]{1,2} \d{2}( [ap0o])?( m)?|\d{1,2}|\d{1,2} [a-z]+)$')

# FANTASMAS DECLARADOS: están en la capa de texto y no en la página. Cada uno
# con la razón por la que sabemos que no es contenido.
# Páginas que no son programación y por eso no extraemos: portada, créditos,
# patrocinadores, mapa y contraportada. El OCR las lee enteras —y en ellas ve,
# además, el texto DENTRO de los logotipos, que la capa de texto no trae—.
PAGS_SIN_PROGRAMA = {1, 61, 62, 63, 64, 65, 66, 67}
# TEXTO DE LOGOTIPO en páginas que sí son de contenido. Son marcas de aliados
# impresas como imagen al pie de la ficha: el OCR las ve y ningún motor de
# texto las trae. Se listan una por una; lo que no esté acá se mira.
LOGOS = re.compile(
    r'^(xiv premios|fundacion|fundacio n|patrimonio|filmico|colombiano|darte|dasc|'
    r'da sc|cultera|arte|euroka|escuela|nacional|m de cine|de cine)$')

FANTASMAS = {
    'hija': 'el «#Hija» de la página del jueves mañana: sobra de una versión '
            'anterior en Canva, no está pintado y cae dentro del recuadro del '
            'CLUB DE PITCH. Confirmado por este mismo paso: el OCR no lo ve.',
    'libre': 'el punto final de la ficha de CIANOTIPIA (p21). SÍ está impreso: el '
             'OCR corta la última línea al pie de la página y devuelve «…al ai». '
             'Es límite del OCR, no texto que falte en el papel.',
}


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def render(pag):
    p = f'{PAG}/ocr-{pag:02d}.jpg'
    if not os.path.exists(p):
        os.makedirs(PAG, exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(DPI), '-jpeg', '-f', str(pag), '-l', str(pag),
                        PDF, f'{PAG}/ocr'], check=True)
        # pdftoppm numera con su propio ancho; se renombra al nuestro
        for c in os.listdir(PAG):
            if c.startswith('ocr-') and c.endswith('.jpg') and not os.path.exists(p):
                n = re.sub(r'\D', '', c)
                if n and int(n) == pag:
                    os.rename(f'{PAG}/{c}', p)
    return p


def ocr(rutas):
    r = subprocess.run(['swift', SWIFT] + rutas, capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit(f'el OCR falló ({r.returncode}): {(r.stderr or "")[:200]}')
    j = json.loads(r.stdout)
    return {ruta: [l['t'] for l in j.get(os.path.basename(ruta), [])] for ruta in rutas}


def parece(a, bs):
    """El mejor parecido de `a` contra una lista, entre 0 y 1."""
    na = norm(a)
    if not na:
        return 1.0, ''
    mejor, cual = 0.0, ''
    for b in bs:
        nb = norm(b)
        if not nb:
            continue
        if na in nb or nb in na:
            return 1.0, b
        r = difflib.SequenceMatcher(None, na, nb).ratio()
        if r > mejor:
            mejor, cual = r, b
    return mejor, cual


def main():
    d = json.load(open(PAR, encoding='utf-8'))
    pags = list(range(1, 68)) if '--todo' in sys.argv else list(range(2, 12))

    # lo nuestro, por página
    # DOS LISTAS, PORQUE SON DOS PREGUNTAS. `lineas` es lo que de verdad
    # extrajimos como texto y tiene que verse en la página. `indice` añade los
    # trozos del nombre de sede —que se compone de varias líneas apiladas— y
    # solo sirve para la pregunta contraria: si el OCR ve «1er piso», eso está
    # cubierto. Exigirle a «del Hotel Mesón de» que se vea como línea era
    # inventarse 84 fantasmas propios.
    nuestro, indice = {}, {}
    for b in d['bloques']:
        ps = b['sede'].split()
        trozos = [' '.join(ps[i:i + n]) for n in range(1, len(ps) + 1)
                  for i in range(len(ps) - n + 1)]
        # un bloque que el PDF parte entre dos páginas está dibujado en LAS
        # DOS, así que su texto se indexa en las dos: si no, la mitad de abajo
        # —la clausura del sábado, RESURGENCIAS— parecía texto sin leer.
        pgs = [b['pagina']] + ([b['pagina'] + 1] if b.get('_partido') else [])
        for pg in pgs:
            indice.setdefault(pg, []).extend(b['lineas'] + trozos)
        # para la pregunta «¿se ve?», un bloque partido se busca en LAS DOS
        # páginas a la vez: cada una lo corta por otro sitio, y «Prima
        # Internacional» es una línea en la primera y media en la segunda.
        nuestro.setdefault(tuple(pgs), []).extend(b['lineas'])
    for f in d['fichas']:
        ls = f['texto'].split('\n') + [f['cabecera']]
        ps = f['cabecera'].split()
        nuestro.setdefault((f['pagina'],), []).extend(ls)
        indice.setdefault(f['pagina'], []).extend(
            ls + [' '.join(ps[i:i + n]) for n in range(1, len(ps) + 1)
                  for i in range(len(ps) - n + 1)])
    for a in d['academica']:
        nuestro.setdefault((a['pagina'],), []).extend(a['texto'].split('\n'))
        indice.setdefault(a['pagina'], []).extend(a['texto'].split('\n'))

    # LA CABECERA DE UNA COLUMNA VACÍA TAMBIÉN ES TABLA. Toda página de la
    # retícula dibuja las seis sedes, use o no todas: el miércoles solo
    # programa en Casa San Pedro y las otras cinco cabeceras siguen impresas.
    # Son el eje de la tabla, igual que la columna de horas, y no contenido
    # que nos hayamos saltado.
    sedes = set()
    for b in d['bloques']:
        ps = b['sede'].split()
        sedes |= {norm(' '.join(ps[i:i + n])) for n in range(1, len(ps) + 1)
                  for i in range(len(ps) - n + 1)}

    rutas = [render(p) for p in pags]
    visto = ocr(rutas)

    por_pag = {p: visto.get(r, []) for p, r in zip(pags, rutas)}
    invisibles, no_leidas, flojas = [], [], []

    # 1 · ¿publicamos algo que no se ve?
    for pgs, textos in nuestro.items():
        ve = [t for p in pgs for t in por_pag.get(p, [])]
        if not ve:
            continue
        etiqueta = 'p' + '+'.join(str(p) for p in pgs)
        for t in dict.fromkeys(textos):
            if not norm(t) or ADORNO.match(norm(t)):
                continue
            r, cual = parece(t, ve)
            if r < PARECIDO:
                if norm(t) in FANTASMAS:
                    continue
                invisibles.append(f'{etiqueta}: extrajimos «{t[:46]}» y el OCR no lo ve '
                                  f'(lo más parecido: «{cual[:32]}», {r:.0%})')
            elif r < 0.95:
                flojas.append(f'{etiqueta}: «{t[:36]}» ≈ «{cual[:36]}» ({r:.0%})')

    # 2 · ¿se ve algo que no leímos?
    for pag, ruta in zip(pags, rutas):
        ve = visto.get(ruta, [])
        for t in ve:
            nt = norm(t)
            if not nt or ADORNO.match(nt) or len(nt) < 4 or nt in sedes \
                    or pag in PAGS_SIN_PROGRAMA or LOGOS.match(nt):
                continue
            r, _ = parece(t, indice.get(pag, []))
            if r < PARECIDO:
                no_leidas.append(f'p{pag}: se ve «{t[:50]}» y no está en lo extraído')

    print(f'villadelcine-2026 · OCR de {len(pags)} páginas a {DPI} dpi')
    print(f'   {len(invisibles)} extraída(s) que el OCR no ve · '
          f'{len(no_leidas)} vista(s) que no extrajimos · '
          f'{len(flojas)} pareja(s) flojas')
    for x in flojas[:8]:
        print('   · parecido bajo:', x)
    if len(flojas) > 8:
        print(f'   · … y {len(flojas) - 8} parejas flojas más')
    for x in invisibles:
        print('   ✗', x)
    for x in no_leidas:
        print('   ✗', x)
    if invisibles or no_leidas:
        sys.exit(1)
    print('\n✓ lo que publicamos se ve en la página, y lo que se ve está leído')


if __name__ == '__main__':
    main()
