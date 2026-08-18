# -*- coding: utf-8 -*-
"""Un still propio para cada corto, sacado del PDF oficial del festival.

POR QUÉ. Los 67 cortos de CineAutopsia son cine experimental de circuito: casi
ninguno tiene ficha en TMDB ni en Letterboxd, así que sin esto la mayoría se
queda sin imagen. El PDF del festival trae un still por obra —es su propia
selección de imagen, mejor que cualquier cosa que pudiéramos elegir nosotros—.

CÓMO. Cada página de día es UNA imagen aplanada con el texto arriba y los stills
apilados debajo, sin márgenes entre ellos. Se cortan con `cortar_tira.py`, que
usa dos cosas: el número de obras lo dice el texto de la misma página (así no
hay que adivinar cuántos son) y el borde se detecta por distancia entre
histogramas, que no se deja engañar por el contraste interno de un still.

EL RECORTE ES 16:9 y quita de los LADOS, porque los stills del PDF son
panorámicos (3:1 o más). Se elige la ventana con más detalle en vez del centro:
en «La methode des moments» el centrado partía la cara de la mujer por el
perfil. Regla de Juan: recortar está bien salvo cuando hay personas.

    python3 pipeline/cineautopsia-2026-stills.py            # ver qué haría
    python3 pipeline/cineautopsia-2026-stills.py --aplicar  # extrae y pega
"""
import json, os, re, subprocess, sys, collections, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from cortar_tira import cortar
from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/cineautopsia-2026/programacion-oficial-2026.pdf'
DEST = f'{REPO}/assets/cineautopsia'
CRUDO = f'{REPO}/festivals/staging/cineautopsia-2026-crudo.json'
OCR = f'{REPO}/festivals/staging/cineautopsia-2026-ocr.json'
MARCA = re.compile(r'\(Dir|min\.|muestra|oportunidad|Conversatorio|p\.m|Boleteria|Gratuit', re.I)
ANCHO_MIN = 500          # por debajo de esto el corte es sospechoso, no un still


# El slug lo hace lib: tener uno propio era exactamente lo que [lib-unica]
# existe para impedir, y me cazó al primer intento.


def ventana_16_9(band):
    """La ventana 16:9 con MÁS DETALLE. Los bordes se concentran donde está el
    sujeto, y el fondo liso no puntúa: por eso conserva las caras."""
    g = band.convert('L').filter(ImageFilter.FIND_EDGES)
    w, h = g.size
    px = g.load()
    col = [sum(px[x, y] for y in range(0, h, 4)) for x in range(w)]
    anc = min(round(h * 16 / 9), w)
    acc = [0] * (w + 1)
    for i, v in enumerate(col):
        acc[i + 1] = acc[i] + v
    mejor, x0 = -1, 0
    for x in range(0, max(1, w - anc + 1), 4):
        s = acc[x + anc] - acc[x]
        if s > mejor:
            mejor, x0 = s, x
    return band.crop((x0, 0, x0 + anc, h))


def poster_de_pagina(full, y0):
    """Recorte 16:9 a ancho completo para el PROGRAMA, cuando la sede no publicó
    póster. Se elige la altura cuyo corte cruce MENOS detalle: en la página del
    Encuentro, que es un mosaico de retratos pegados sin márgenes, cualquier
    corte a ojo parte una cara por la mitad."""
    w, h = full.size
    alto = round(w * 9 / 16)
    if h - y0 < alto:
        return None
    g = full.convert('L').filter(ImageFilter.FIND_EDGES)
    px = g.load()
    energia = lambda y: sum(px[x, y] for x in range(0, w, 4))
    mejor = None
    for y in range(y0, h - alto, 6):
        c = energia(y) + energia(y + alto)
        if mejor is None or c < mejor[0]:
            mejor = (c, y)
    return full.crop((0, mejor[1], w, mejor[1] + alto))


def main():
    aplicar = '--aplicar' in sys.argv
    ocr = json.load(open(OCR, encoding='utf-8'))['paginas']
    crudo = json.load(open(CRUDO, encoding='utf-8'))['programas']
    por_pag = collections.defaultdict(list)
    for f in crudo:
        por_pag[f['_pagina']].append(f)
    os.makedirs(DEST, exist_ok=True)
    # qué obras ya tienen imagen de una fuente que MANDA sobre el still
    pub = json.load(open(f'{REPO}/festivals/cineautopsia-2026.json', encoding='utf-8'))
    ya_tienen = {lib.norm(x.get('title', '')): x.get('posterSource')
                 for f in pub['films'] for x in (f.get('film_list') or [])
                 if x.get('posterSource') in ('tmdb', 'letterboxd', 'oficial')}
    hechos, flojos, progs = {}, [], {}
    for pag in sorted(por_pag):
        obras = [o for f in por_pag[pag] for o in f['obras']]
        sin_poster = [f for f in por_pag[pag] if not f.get('poster')]
        if not obras and not sin_poster:
            continue
        n = int(re.search(r'(\d+)', pag).group(1))
        tmp = f'/tmp/ca-pdfimg-{n}'
        subprocess.run(['pdfimages', '-f', str(n), '-l', str(n), '-png', PDF, tmp],
                       capture_output=True)
        img = f'{tmp}-000.png'
        if not os.path.exists(img):
            print(f'  ⚠ {pag}: no se pudo extraer la imagen'); continue
        ys = [l['y'] + l['h'] for l in ocr[pag] if MARCA.search(l['t'])]
        full = Image.open(img).convert('RGB')
        y0 = int(max(ys) * full.size[1])
        bandas = []
        if obras:
            _, bandas = cortar(img, len(obras) + 1, y0)
            bandas = bandas[1:]                  # la primera es la sobra del texto
        # el programa sin póster de la sede se queda con un trozo de su página
        for f in por_pag[pag]:
            if not f.get('poster'):
                pc = poster_de_pagina(full, y0)
                if pc:
                    nom = f'programa-{lib.slug(f['titulo'])[:60]}.jpg'
                    if aplicar:
                        pc.save(f'{DEST}/{nom}', quality=88)
                    progs[lib.norm(f['titulo'])] = f'/assets/cineautopsia/{nom}'
                    print(f'  {pag}  PROGRAMA {f["titulo"][:34]:36} {pc.size[0]}×{pc.size[1]}')
        for (a, b), o in zip(bandas, obras):
            # NO se recorta lo que ya tiene póster de TMDB o Letterboxd: ese
            # archivo no lo leería nadie. Generé 30 así —2,2 MB— antes de que
            # Juan preguntara «¿para qué necesitas Allegory, si ya tiene póster?».
            if ya_tienen.get(lib.norm(o['titulo'])):
                continue
            crop = ventana_16_9(full.crop((0, a, full.size[0], b)))
            w, h = crop.size
            if w < ANCHO_MIN:
                flojos.append((pag, o['titulo'], f'{w}×{h}'))
                continue
            nom = f'{lib.slug(o['titulo'])[:60]}.jpg'
            if aplicar:
                crop.save(f'{DEST}/{nom}', quality=88)
            hechos[lib.norm(o['titulo'])] = (f'/assets/cineautopsia/{nom}', w, h)
            print(f'  {pag}  {o["titulo"][:38]:40} {w}×{h}')
    print(f'\n  stills listos: {len(hechos)}')
    if flojos:
        print('  ⚠ cortes demasiado estrechos, NO se usan (revisar a mano):')
        for p, t, d in flojos:
            print(f'     {p}  {t[:40]:42} {d}')
    if not aplicar:
        print('\n  (simulación — con --aplicar se escriben los .jpg y el JSON)')
        return
    # pegar en el JSON: solo donde la obra no tiene ya un póster mejor
    P = f'{REPO}/festivals/cineautopsia-2026.json'
    d = json.load(open(P, encoding='utf-8'))
    n_puestos = n_respetados = 0
    n_prog = 0
    for f in d['films']:
        pp = progs.get(lib.norm(f.get('title', '')))
        if pp and not f.get('poster'):
            f['poster'], f['posterSource'] = pp, 'editorial'
            n_prog += 1
        for it in (f.get('film_list') or []):
            h = hechos.get(lib.norm(it.get('title', '')))
            if not h:
                continue
            if it.get('poster'):
                n_respetados += 1        # TMDB o Letterboxd mandan (docs/POSTERS.md §2)
                continue
            it['poster'], it['posterSource'] = h[0], 'editorial'
            n_puestos += 1
    json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'\n✓ obras con póster nuevo: {n_puestos} · ya tenían uno mejor: {n_respetados}'
          f' · programas: {n_prog}')


if __name__ == '__main__':
    main()
