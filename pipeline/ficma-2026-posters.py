#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-posters.py — el afiche que publica el FESTIVAL, re-hosteado.

PARA QUÉ. Dos obras del reprogramado no tienen imagen en TMDB: «Ayuno y
cenizas», cuya ficha existe pero sin póster, y «Apuntes sobre anomalías y
fantasmas», que no tiene ficha. Las dos SÍ tienen afiche publicado por el
festival — uno en su web, el otro dentro de su post—. Una obra sin imagen en la
grilla es un hueco que se ve; el afiche estaba a un clic.

DE DÓNDE SALE CADA UNO, declarado obra por obra en FUENTES. Dos formas:

  · `web` — una URL fija de laficma.com. Se pide el ORIGINAL, no el recorte que
    WordPress sirve en la página (`-717x1024`): la app re-escala hacia abajo,
    nunca hacia arriba.
  · `ig`  — (shortcode, número de lámina). La URL del CDN de Instagram va
    FIRMADA y caduca en horas, así que guardarla no sirve de nada: se resuelve
    en cada corrida con `ig_carrusel.py`, que la saca del embed público. Esto
    es lo que hace el paso re-corrible.

SE MIDE LO QUE SE BAJA. Un .jpg que en realidad es una página de error pasa por
archivo existente y la app pinta un hueco (cicatriz de #NarrarElFuturo: dos
pósters rotos, uno HTML disfrazado y otro un 404 de WordPress). Acá cada archivo
se abre con `sips` y tiene que devolver un ancho: si no, no se escribe la ficha.

Lee   FUENTES (abajo) · laficma.com · el embed de Instagram
Esc.  festivals/staging/ficma-2026-posters.json
      assets/ficma/<slug>.jpg
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/ficma'
OUT = f'{ST}/ficma-2026-posters.json'

# EL AFICHE ESTÁ EN SU PROPIA PÁGINA. Cinco obras no tienen imagen en TMDB ni
# en la web, pero la lámina del programa las lleva impresas: el PDF es la
# fuente y el recorte, la forma de sacarlas. La caja es la de la plantilla —fija
# para las fichas de película, otra para la maqueta centrada de las muestras— y
# cada recorte se midió mirándolo, no a ojo de regla.
RECORTE = {'ficha': (0.105, 0.265, 0.585, 0.835),
           'centrada': (0.285, 0.275, 0.715, 0.700)}
PAG = f'{REPO}/fuentes/ficma-2026/programa-septiembre/pag'

FUENTES = {
    'Ayuno y cenizas': (
        'web', 'https://laficma.com/wp-content/uploads/2026/09/Ayuno.jpg',
        'el afiche de la obra en /estrenosficma17/ (1000×1429). TMDB tiene la '
        'ficha —1756580— pero sin imagen.'),
    'Apuntes sobre anomalías y fantasmas': (
        'ig', ('DdUsahVGspB', 1),
        'la lámina 1 del post es el afiche de la obra, con bloque de créditos y '
        'laureles (1080×1440). No tiene ficha en TMDB.'),
    'La Quimera de Oro': ('pdf', ('p-43.jpg', 'ficha'),
        'recortado de su página del programa: no está en TMDB'),
    'Cuando el dolor se nombra: Diálogo abierto y violencia de género': (
        'pdf', ('p-63.jpg', 'ficha'),
        'recortado de su página del programa: corto local, no está en TMDB'),
    'Entrelazados': ('pdf', ('p-70.jpg', 'ficha'),
        'recortado de su página del programa: estreno local, no está en TMDB'),
    # LAS DOS MUESTRAS DE CORTOS NO LLEVAN AFICHE Y NO SE LES INVENTA UNO. Su
    # lámina es de maqueta centrada y lo que hay ahí es el logo del ciclo sobre
    # papel en blanco: recortarlo daba una tarjeta con media palabra y un sello.
    # Son PROGRAMAS, no obras —el festival no publica qué cortos van dentro—, y
    # la app ya sabe pintar una tarjeta sin imagen. Un recorte malo se ve peor
    # que un hueco, y además haría creer que el afiche es ese.
}
SIN_AFICHE = {
    'Cortos Colombia de película': 'su lámina solo trae el logo del ciclo',
    'Muestra de Cortometrajes: Realizadores locales y Eje Cafetero':
        'su lámina solo trae una ilustración del programa, no un afiche',
}


def mide(p):
    """(ancho, alto) según sips, o None si el archivo no es una imagen."""
    r = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', p],
                       capture_output=True, text=True)
    d = dict(l.strip().split(': ') for l in r.stdout.splitlines() if ': ' in l)
    try:
        return int(d['pixelWidth']), int(d['pixelHeight'])
    except (KeyError, ValueError):
        return None


def url_de_lamina(shortcode, i):
    """La URL de una lámina, resuelta hoy: las de Instagram caducan."""
    r = subprocess.run([sys.executable, f'{REPO}/pipeline/ig_carrusel.py', shortcode],
                       capture_output=True, text=True)
    d = json.loads(r.stdout.strip().split('\n')[0])
    for l in d['laminas']:
        if l['i'] == i and not l.get('video'):
            return l['url']
    return ''


def recorta(pagina, maqueta, titulo):
    """La caja del afiche dentro de la lámina → assets/ficma/<slug>.jpg."""
    from PIL import Image
    src = f'{PAG}/{pagina}'
    if not os.path.exists(src):
        return ''
    im = Image.open(src)
    W, H = im.size
    x0, y0, x1, y1 = RECORTE[maqueta]
    dest = f'{ASSETS}/{slug(titulo)}.jpg'
    # write-once: el archivo publicado ya pasó por optimize-posters (500 px);
    # re-recortarlo en cada corrida lo devolvía a 350 KB y ensuciaba el diff.
    if not os.path.exists(dest):
        im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))).save(dest, quality=88)
    return f'/assets/ficma/{os.path.basename(dest)}'


def main():
    os.makedirs(ASSETS, exist_ok=True)
    fichas, fallos = {}, []
    for titulo, (clase, ref, por_que) in FUENTES.items():
        if clase == 'pdf':
            ruta = recorta(ref[0], ref[1], titulo)
            if not ruta:
                fallos.append(f'{titulo} — falta la página {ref[0]} del PDF '
                              f'(corré ficma-2026-programa-pdf.py)')
                continue
            m = mide(f'{REPO}{ruta}')
            fichas[titulo] = {'poster': ruta, 'posterSource': 'custom',
                              '_medida': f'{m[0]}×{m[1]}' if m else '?',
                              '_de': por_que, '_url': f'{ref[0]} del PDF de programación'}
            print(f'OK  {titulo[:44]:46} {m[0]}×{m[1]} (recorte)')
            continue
        url = ref if clase == 'web' else url_de_lamina(*ref)
        if not url:
            fallos.append(f'{titulo} — no se pudo resolver la lámina')
            continue
        dest = f'{ASSETS}/{slug(titulo)}.jpg'
        subprocess.run(['curl', '-sS', '--retry', '3', '--max-time', '60',
                        '-A', UA, '-o', dest, url], check=False)
        m = mide(dest)
        if not m:
            os.path.exists(dest) and os.remove(dest)
            fallos.append(f'{titulo} — lo descargado no es una imagen')
            continue
        fichas[titulo] = {'poster': f'/assets/ficma/{os.path.basename(dest)}',
                          'posterSource': 'custom',
                          '_medida': f'{m[0]}×{m[1]}',
                          '_de': por_que,
                          '_url': url if clase == 'web' else
                                  f'instagram {ref[0]} · lámina {ref[1]}'}
        print(f'OK  {titulo[:44]:46} {m[0]}×{m[1]}')
    for f in fallos:
        print('—  ', f)

    json.dump({'_provenance': provenance(
        'el afiche que publica el propio festival: laficma.com y su Instagram',
        que_aporta='póster de las obras que TMDB no tiene o tiene sin imagen',
        ojo='las URL de Instagram caducan; la lámina se resuelve en cada corrida '
            'desde el shortcode, no se guarda'),
        'fichas': fichas, 'fallos': fallos, 'sin_afiche_a_proposito': SIN_AFICHE},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(fichas)} pósters · {len(fallos)} fallos')
    if fallos:
        sys.exit(1)


if __name__ == '__main__':
    main()
