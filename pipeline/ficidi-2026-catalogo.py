#!/usr/bin/env python3
"""ficidi-2026-catalogo.py — la Selección Oficial del IV Festival Internacional de Cine
Diverso (Barranquilla, 4–7 nov 2026), desde sus láminas de Instagram.

LA FUENTE: cinco carruseles de @festivaldecinediverso (6–7 oct 2026, leídos por
el embed público, sin sesión). La primera lámina de cada uno es la portada de la
categoría; las demás son GRILLAS de afiches con TÍTULO / «Dir. …» / PAÍS
pintados debajo de cada uno.

DOS LECTURAS INDEPENDIENTES, que tienen que coincidir:
  · a ojo: fuentes/ficidi-2026/ojos-seleccion.json — título, dirección, país y
    la caja aproximada del afiche, leídos sobre cada lámina con una cuadrícula;
  · la OCR del sistema CON CAJAS (pipeline/ficma-2026-ocr.swift): toda palabra
    de 4+ letras del título, de la dirección y del país tiene que estar en SU
    lámina, y cada «Dir.» que la OCR lee en una lámina tiene que estar transcrito.

LA DETECCIÓN AUTOMÁTICA DEL AFICHE se probó y no sirve aquí (7 oct): las grillas
nacionales tienen afiches casi negros sobre fondo negro y se funden. Por eso la
caja es la de la lectura a ojo, y el script solo la AJUSTA: cada borde se corre,
a lo sumo 24 px, a la línea donde el salto entre adentro y afuera es mayor. Una
imagen apaisada (null en la transcripción) no es un afiche: la obra va sin.

Escribe festivals/staging/ficidi-2026-catalogo.json y los afiches en
fuentes/ficidi-2026/afiches/.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

from PIL import Image, ImageFilter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

IG = f'{REPO}/fuentes/ig'
DIR = f'{REPO}/fuentes/ficidi-2026'
OJOS = f'{DIR}/ojos-seleccion.json'
DESTINO = f'{REPO}/festivals/staging/ficidi-2026-catalogo.json'
CATEGORIA = {
    'DeKb-mdlH_S': 'Cortometraje de Ficción Internacional LGBTIQ+',
    'DeKeU-OD8Ck': 'Cortometraje de Ficción Internacional LGBTIQ+',
    'DeK-5-VkXUw': 'Cortometraje de No Ficción Internacional LGBTIQ+',
    'DeM47Tqkf0o': 'Cortometraje de Ficción Nacional LGBTIQ+',
    'DeNsAq0kchD': 'Cortometraje de No Ficción Nacional LGBTIQ+',
}
AJUSTE = 24      # px que puede correrse un borde de la caja a ojo


# la OCR lee a veces letras CIRÍLICAS de forma idéntica a las latinas
# («Хіаохі» por «Xiaoxi», en Ius del tiempo): se comparan como latinas
_HOMOGLIFOS = str.maketrans('АВЕКМНОРСТХаеіорсухј', 'ABEKMHOPCTXaeiopcyxj')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').translate(_HOMOGLIFOS).lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def ocr_cajas(rutas):
    cache = f'{DIR}/ocr-cajas.json'
    hecho = json.load(open(cache)) if os.path.exists(cache) else {}
    faltan = [r for r in rutas if os.path.relpath(r, REPO) not in hecho]
    # la herramienta devuelve los resultados POR NOMBRE DE ARCHIVO, y todos los
    # carruseles tienen un 02.jpg: se llama una vez por carpeta, o se pisan
    for carpeta in sorted({os.path.dirname(p) for p in faltan}):
        lote = [p for p in faltan if os.path.dirname(p) == carpeta]
        r = subprocess.run(['swift', f'{REPO}/pipeline/ficma-2026-ocr.swift'] + lote,
                           capture_output=True, text=True)
        out = json.loads(r.stdout)
        for p in lote:
            hecho[os.path.relpath(p, REPO)] = out[os.path.basename(p)]
    if faltan:
        os.makedirs(DIR, exist_ok=True)
        json.dump(hecho, open(cache, 'w'), ensure_ascii=False)
    return {r: hecho[os.path.relpath(r, REPO)] for r in rutas}


def ajustar(im, caja):
    """Corre cada borde de la caja (a lo sumo AJUSTE px) a la línea con el mayor
    salto de luminancia entre su lado de adentro y su lado de afuera."""
    g = im.convert('L').filter(ImageFilter.GaussianBlur(2))
    px = g.load()
    W, H = g.size
    x0, y0, x1, y1 = caja

    def salto_fila(y, xa, xb, adentro):     # adentro = +1 (debajo) o -1 (encima)
        return sum(abs(px[x, min(H - 1, max(0, y + 3 * adentro))] - px[x, min(H - 1, max(0, y - 3 * adentro))])
                   for x in range(xa, xb, 6))

    def salto_col(x, ya, yb, adentro):
        return sum(abs(px[min(W - 1, max(0, x + 3 * adentro)), y] - px[min(W - 1, max(0, x - 3 * adentro)), y])
                   for y in range(ya, yb, 6))
    cx = (x0 + 30, x1 - 30)
    cy = (y0 + 30, y1 - 30)
    y0 = max(range(y0 - AJUSTE, y0 + AJUSTE + 1), key=lambda y: salto_fila(y, *cx, +1))
    y1 = max(range(y1 - AJUSTE, y1 + AJUSTE + 1), key=lambda y: salto_fila(y, *cx, -1))
    x0 = max(range(x0 - AJUSTE, x0 + AJUSTE + 1), key=lambda x: salto_col(x, *cy, +1))
    x1 = max(range(x1 - AJUSTE, x1 + AJUSTE + 1), key=lambda x: salto_col(x, *cy, -1))
    m = 6   # por dentro del borde
    return (x0 + m, y0 + m, x1 - m, y1 - m)


# EL TÍTULO PUBLICADO (propuesta, a confirmar con Juan): las láminas lo pintan en
# mayúscula sostenida, y eso no se publica. Minúscula salvo nombres propios, con
# los acentos que trae el AFICHE cuando el pie los omite (Ansío, Gaitán, mí), y
# los títulos en inglés con mayúscula de título. Llave = el pie de la lámina.
TITULO = {
    'EXILIO': 'Exilio', 'VERDULERA': 'Verdulera', 'LA MUJER SENTADA': 'La mujer sentada',
    'EL BAÑADOR': 'El bañador', 'LOS PÁJAROS': 'Los pájaros', 'MUÑECAS DE PORCELANA': 'Muñecas de porcelana',
    'A MI EDAD': 'A mi edad', 'BLUE BERRI': 'Blue Berri', 'TÍA MORGANA': 'Tía Morgana', 'COURAÇA': 'Couraça',
    'AR-DOR': 'Ar-dor', 'VERANO': 'Verano', 'PENDIENTE DE ESTRELLA': 'Pendiente de estrella', 'CAST ME': 'Cast Me',
    'AQUÍ DONDE SOY': 'Aquí donde soy', 'VERDADES': 'Verdades', 'IUS DEL TIEMPO': 'Ius del tiempo',
    'CIELO DE ENERO': 'Cielo de enero', 'JUGO EN POLVO': 'Jugo en polvo',
    '¿ME VAS A ESTAR ESPERANDO?': '¿Me vas a estar esperando?', 'INÉS': 'Inés',
    'DE AQUELLOS POLVOS': 'De aquellos polvos', 'HÁ SINAIS': 'Há sinais', 'ONADES': 'Onades', '621 KM': '621 km',
    'YOUNG WILD THINGS': 'Young Wild Things', 'SOLO NATALIE': 'Solo Natalie',
    'TODOS LOS NOMBRES EMPIEZAN CON M': 'Todos los nombres empiezan con M', 'PERROS': 'Perros',
    'REINA DE POLVO Y LUZ': 'Reina de polvo y luz',
    'TRAVESTIS, BOMBAS Y UN CORTEJO FÚNEBRE': 'Travestis, bombas y un cortejo fúnebre',
    'LO QUE FUIMOS': 'Lo que fuimos', '90 SEGUNDOS': '90 segundos', 'DAFNE Y POL': 'Dafne y Pol',
    'LA OTRA MITAD DEL DOLOR': 'La otra mitad del dolor', 'TUESDAY SESSION': 'Tuesday Session',
    'TRAVAS SOBREVIVIENTES': 'Travas sobrevivientes', 'A SIN DE FELLA STORY': 'A Sin de Fella Story',
    'LA MASCULINIDAD ES UNA PREGUNTA': 'La masculinidad es una pregunta',
    'MIL MORTES DE UM SOBREVIVENTE': 'Mil mortes de um sobrevivente', 'ALWASIYYA': 'Alwasiyya', 'KIBOKO': 'Kiboko',
    'O DIÁRIO IMAGINADO': 'O diário imaginado', 'JAMÁS VOLVEREMOS': 'Jamás volveremos',
    'LAS COSAS QUE NO TE DIJE': 'Las cosas que no te dije',
    'PEPA GAITAN PRESENTE, AHORA Y SIEMPRE.': 'Pepa Gaitán presente, ahora y siempre',
    'CORPO E IDENTIDADE': 'Corpo e identidade', 'ANSIO DESPERTAR': 'Ansío despertar',
    '¿QUIÉN SE LLEVA LAS ESTRELLAS?': '¿Quién se lleva las estrellas?',
    'TODO LO QUE PASARÁ MAÑANA': 'Todo lo que pasará mañana', 'AMOR EN POSITIVO': 'Amor en positivo',
    'REFRACCIÓN': 'Refracción', 'AGUIJÓN ROJO': 'Aguijón rojo', 'FIELMENTE': 'Fielmente', 'NO': 'No',
    'DANZAN LAS LUCIÉRNAGAS': 'Danzan las luciérnagas', 'TRANSITAR LO MARICA NEGRO': 'Transitar lo marica negro',
    'YO SOY YO': 'Yo soy yo', 'MARICONES': 'Maricones',
    '¿A MI QUIÉN ME CUIDA? EXPERIENCIAS NEGRAS DIVERSAS EN EL PARO NACIONAL DEL 2021':
        '¿A mí quién me cuida? Experiencias negras diversas en el paro nacional del 2021',
    'ESPACIOS HÚMEDOS': 'Espacios húmedos', 'MÁS ALLÁ DE LA CORONA': 'Más allá de la corona',
    'MIRADAS TRANS-PARENTES': 'Miradas trans-parentes',
    '1AÑO Y UN MEZ EN COLOMBIAMARICX': '1 año y un mez en Colombiamaricx',
    'MADE TO SHINE': 'Made to Shine', 'FRAGMENTOS': 'Fragmentos',
}


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['laminas']
    rutas = sorted({f'{IG}/{sc}/{f}' for sc, f, *_ in ojos})
    O = ocr_cajas(rutas)
    fallos = []
    # cobertura en los dos sentidos: todo «Dir.» que lee la OCR está transcrito
    for r in rutas:
        sc, f = r.split('/')[-2], r.split('/')[-1]
        n_ocr = sum(1 for l in O[r] if re.match(r'^\s*Dir[\.\s:]', l['t']))
        n_ojo = sum(1 for o in ojos if o[0] == sc and o[1] == f)
        if n_ocr != n_ojo:
            fallos.append(f'{sc}/{f}: la OCR lee {n_ocr} «Dir.» y hay {n_ojo} transcritas')
    os.makedirs(f'{DIR}/afiches', exist_ok=True)
    obras = []
    for k, (sc, f, titulo, director, pais, caja) in enumerate(ojos):
        r = f'{IG}/{sc}/{f}'
        w = set(plano(' '.join(l['t'] for l in O[r])).split())
        for x in plano(f'{titulo} {director} {pais}').split():
            if len(x) >= 4 and x not in w:
                fallos.append(f'{sc}/{f}: la OCR no encuentra «{x}» de «{titulo}» / «{director}» / «{pais}»')
        if titulo not in TITULO:
            fallos.append(f'{sc}/{f}: «{titulo}» no tiene su título publicado en TITULO')
        o = {'titulo': TITULO.get(titulo, titulo), 'titulo_lamina': titulo, 'director': director, 'pais': pais, 'categoria': CATEGORIA[sc],
             '_src': {'url': f'https://www.instagram.com/p/{sc}/', 'post': sc, 'lamina': f, 'date': '2026-10-07'}}
        if caja:
            im = Image.open(r).convert('RGB')
            c = ajustar(im, caja)
            ww, hh = c[2] - c[0], c[3] - c[1]
            if not 1.1 < hh / ww < 1.9:
                fallos.append(f'{sc}/{f}: el afiche de «{titulo}» quedó {ww}×{hh}, fuera de proporción')
            nombre = f'{sc}-{f[:-4]}-{k:02d}.jpg'
            im.crop(c).save(f'{DIR}/afiches/{nombre}', quality=92)
            o['afiche'] = f'fuentes/ficidi-2026/afiches/{nombre}'
            o['_src']['caja'] = list(c)
        else:
            o['_sin_afiche'] = 'la lámina trae una imagen apaisada, no un afiche'
        obras.append(o)
    if fallos:
        sys.exit('✗ la transcripción y las láminas no coinciden:\n  · ' + '\n  · '.join(fallos))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('IG @festivaldecinediverso, 5 carruseles de la Selección Oficial (6–7 oct 2026)',
                                  url='https://www.instagram.com/festivaldecinediverso/',
                                  metodo='lectura a ojo de las 12 grillas, confirmada por la OCR del sistema; '
                                         'afiche recortado de la caja a ojo, ajustada a su borde'),
        'obras': obras}, ensure_ascii=False, indent=1))
    print(f'✓ {len(obras)} obras ({sum(1 for o in obras if o.get("afiche"))} con afiche) → '
          f'{os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
