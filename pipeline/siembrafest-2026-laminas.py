# -*- coding: utf-8 -*-
"""Las láminas de la Selección Oficial que el festival publicó en Instagram.

SiembraFest presentó su selección en ocho carruseles, uno por sección, y dentro
de cada uno hay una lámina por obra: un fotograma con el título, el director,
el sello de la sección y el laurel de Selección Oficial. Es la única imagen
oficial que existe de la mayoría de estas obras — casi todas son cortos
colombianos sin ficha en TMDB ni en Letterboxd.

Manda el original: donde el catálogo ya trae un póster de TMDB, ese se queda.
La lámina solo entra donde íbamos a quedarnos sin nada.

De 4:5 a 2:3 sobran 16.7% de ancho. Recortarlo todo deja el título a dos puntos
del borde; estirarlo todo deforma la tipografía un 20%. Se hacen las dos cosas a
medias —6% por lado, 5.6% de estirón— y no se nota ninguna. El 6% está medido,
no supuesto: en las 92 láminas ningún título ni sello baja del 10.2%.

    python3 pipeline/siembrafest-2026-laminas.py            # informe
    python3 pipeline/siembrafest-2026-laminas.py --escribir  # + assets y sidecar
"""
import json, os, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance, slug                              # noqa: E402
from ig_carrusel import laminas as _carrusel                        # noqa: E402

CAT = f'{REPO}/festivals/staging/siembrafest-2026.json'
SALIDA = f'{REPO}/festivals/staging/siembrafest-2026-laminas.json'
ASSETS = f'{REPO}/assets/siembrafest'
WEB = '/assets/siembrafest'

ANCHO, LADO, CALIDAD = 500, 0.06, 82

# Los NUEVE carruseles «Presentamos <sección>» de @siembrafest, uno por sección.
# El de Mujeres que sostienen la vida abre la serie (17 ago) y ya no se alcanza
# desde el perfil —sin sesión solo se ven ~12 publicaciones—: su shortcode salió
# de nuestro propio sidecar siembrafest-2026-programas-ig.json, capturado el 23
# ago. Lo que ya está en el repo se busca en el repo antes que en la web.
POSTS = {
    'mujeres-que-sostienen-la-vida': 'DcJ9J4toPgL',
    'sabores-en-escena':   'DcelBcQoD1S',
    'asi-es-cundinamarca': 'Dcb_hTGICGX',
    'ojo-pelao':           'DcZZ0sJoOBN',
    'muertos-de-risa':     'DcW0_hhoDAP',
    'buenos-malos-y-feos': 'DcURPb9ILjZ',
    'cinema-patatus':      'DcRqj2VINfq',
    'estampas':            'DcPHklooI9G',
    'amores-desamores':    'DcMlUyBILIO',
}

# Qué obra hay en cada lámina. LEÍDO de la imagen, una por una: el título va
# pintado, no viene en ningún campo. La lámina 1 es la portada de la sección y
# la última son los créditos de los socios; ninguna de las dos es una obra, y
# por eso cada carrusel trae exactamente (obras de la sección + 2) láminas.
OBRAS = {
 'mujeres-que-sostienen-la-vida': {
  2: 'La gallina saraviada', 3: 'En su sombra fértil', 4: 'La grandiosa',
  5: 'Paramunas: El alma de la montaña', 6: 'La tinaja', 7: 'Cayenas libertarias',
  8: 'Pasta negra', 9: 'Victorias y Glorias – Relatos de campeonas'},
 'sabores-en-escena': {
  2: "Phakhakhe Pi'txi – Minga de pensamiento", 3: 'La Asociación',
  4: 'Somos historias: Casaramano, sagrado y vida'},
 'asi-es-cundinamarca': {
  2: 'Elipsis', 3: 'Trigos', 4: 'Herminda', 5: 'Teresa', 6: 'La muerte de Elías',
  7: 'Gachalá, entre el miedo y la memoria', 8: 'Xie. Defensa de la vida'},
 'ojo-pelao': {
  2: 'En el mar', 3: 'Emechiche, el renacer de los Cabeciblanco',
  4: 'Chicha la chicharra', 5: 'Daniel', 6: 'Zizuma, nuestra casa de agua y nubes',
  7: 'Cantos al juego de “Bolar”', 8: 'La gran hazaña', 9: 'Extinta',
  10: 'La pecera', 11: 'Un pájaro más'},
 'muertos-de-risa': {
  2: 'El día de mi suerte', 3: 'HDLT',
  4: 'Miguel Ángel, Federico, y el carro que pasó encima de las gafas',
  5: 'Muertos que no son muertos'},
 'buenos-malos-y-feos': {
  2: 'Catatumbo: Casa del trueno, memoria y dignidad', 3: '6 de diciembre',
  4: 'Relatos del camino', 5: 'La Europa', 6: 'Dios y suerte',
  7: 'La despedida del río', 8: 'Las piedras del río', 9: 'Y el río lloró',
  10: 'Preguntas frecuentes', 11: 'Pudor ante el asalto de los ojos furtivos',
  12: 'La Mona', 13: 'Términa', 14: 'Desde la ventana', 15: 'El huaquero',
  16: 'Entre 2 aguas', 17: 'Floresmiro', 18: 'Irredentos'},
 'cinema-patatus': {
  2: 'La Oscurana', 3: 'Animero: Son de la muerte', 4: 'Nativos de la tierra negra',
  5: 'Que el cielo nos perdone', 6: 'El silbido del cañaduzal', 7: 'Noche de vuelo',
  8: 'Villa Feliz', 9: 'Bajo el mismo techo', 10: 'Linfernum', 11: 'Payasadas'},
 'estampas': {
  2: 'Herencia: los cantos de la tierra', 3: 'Mingoya: Tierra de ornitólogos',
  4: 'Refugiar el gesto', 5: 'Guatapé (No) ha muerto', 6: 'Donde nace el nombre',
  7: 'Camino al Chicamocha', 8: 'Sinfonía incompleta de oficios del Fonce'},
 'amores-desamores': {
  2: 'Take It Off', 3: 'Carola', 4: 'Desarraigo', 5: 'Gladiolos', 6: 'Idilio',
  7: 'Elementales', 8: 'Orígenes', 9: 'Desde acá veo la tormenta',
  10: 'Unlearning Motherhood', 11: 'Amor', 12: 'La Independencia',
  13: 'Tres gatos parias', 14: 'Valentino y la calavera', 15: 'La calle del amor',
  16: 'Corazón galvánico', 17: 'El mejor chocolate del mundo',
  18: 'Make up: El arte de amar', 19: 'Soñé su nombre'},
}

# La lámina escribe el título de otra forma que el catálogo. El festival ya
# tiene las dos versiones en circulación (se le preguntó el 24 ago, sin
# respuesta); manda el catálogo, que es su web.
#   «Flores Miro» → Floresmiro, «HDLT - Hijo de la Tierra» → HDLT,
#   «cabeciblancos» → Cabeciblanco  (aplicados ya en OBRAS)
# Excepto uno, que Juan cerró: es «al juego», no «al fuego» —Bolar es un juego—
# y la obra ya está completa en Tercer Tiempo.
TITULO_CORREGIDO = {'Cantos al fuego de “Bolar”': 'Cantos al juego de “Bolar”'}


def _bajar(url, destino):
    subprocess.run(['curl', '-sSf', '--retry', '2', '--max-time', '60',
                    '-o', destino, url], check=True)


def a_poster(origen, destino):
    """4:5 → 2:3 sin perder ni una letra: recorte corto y estirón corto."""
    from PIL import Image
    im = Image.open(origen).convert('RGB')
    c = int(im.width * LADO)
    im = im.crop((c, 0, im.width - c, im.height))
    im.resize((ANCHO, ANCHO * 3 // 2), Image.LANCZOS).save(
        destino, 'JPEG', quality=CALIDAD, optimize=True)


def main(escribir):
    cat = {norm(f['title']): f for f in json.load(open(CAT, encoding='utf-8'))['films']}
    # el bruto pesa ~100 MB y no es una fuente: se cachea FUERA del repo
    tmp = os.path.join(tempfile.gettempdir(), 'siembrafest-2026-laminas')
    if escribir:
        os.makedirs(ASSETS, exist_ok=True)
        os.makedirs(tmp, exist_ok=True)

    obras, sin_cruce, ya_tenia = [], [], []
    for sec, sc in POSTS.items():
        d = _carrusel(sc)
        esperadas = max(OBRAS[sec]) + 1                 # + la lámina de créditos
        if len(d['laminas']) != esperadas:
            raise SystemExit(
                f'{sec}: el carrusel tiene {len(d["laminas"])} láminas y el mapa '
                f'describe {esperadas}. El festival lo reeditó: hay que volver a '
                f'LEER las láminas antes de seguir.')
        for i, titulo in sorted(OBRAS[sec].items()):
            titulo = TITULO_CORREGIDO.get(titulo, titulo)
            f = cat.get(norm(titulo))
            if f is None:
                sin_cruce.append((sec, i, titulo))
                continue
            if f.get('poster'):
                ya_tenia.append(titulo)
                continue
            ruta = f'{WEB}/{slug(titulo)}.jpg'
            obras.append({'titulo': f['title'], 'poster': ruta,
                          'posterSource': 'custom',
                          '_lamina': f'instagram.com/p/{sc} #{i}'})
            if escribir:
                bruto = f'{tmp}/{sec}-{i:02d}.jpg'
                if not os.path.exists(bruto):
                    _bajar(d['laminas'][i - 1]['url'], bruto)
                a_poster(bruto, f'{ASSETS}/{slug(titulo)}.jpg')

    print(f'  láminas de obra en los {len(POSTS)} carruseles: {sum(len(v) for v in OBRAS.values())}')
    print(f'  ya tenían póster original (se respeta):  {len(ya_tenia)}')
    print(f'  póster NUEVO desde la lámina oficial:    {len(obras)}')
    if sin_cruce:
        print(f'  SIN CRUZAR con el catálogo ({len(sin_cruce)}):')
        for s, i, t in sin_cruce:
            print(f'    · {s} #{i}: {t}')

    if not escribir:
        print('\n  (informe; --escribir para generar assets y sidecar)')
        return
    json.dump({'_provenance': provenance(
                 'carruseles «Presentamos <sección>» de instagram.com/siembrafest '
                 '(9 posts, uno por sección; embed público)',
                 metodo='una lámina por obra, con el título PINTADO en la imagen: el '
                        'mapa lámina→obra se leyó imagen por imagen, no por el orden '
                        'del carrusel. 4:5 → 2:3 con recorte del 6% por lado (medido: '
                        'ningún título baja del 10.2%) más el 5.6% de estirón restante',
                 regla='solo donde el catálogo NO tiene póster; el original de TMDB manda'),
               'obras': obras}, open(SALIDA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n  {len(obras)} obras → {SALIDA}')
    print(f'  {len(obras)} pósters → {ASSETS}/')


if __name__ == '__main__':
    main('--escribir' in sys.argv)
