#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-posters.py — el afiche de cada obra, en disco y nombrado.

POR QUÉ UN PASO PROPIO Y NO `enriquecer.py --posters`. El genérico baja los
pósters recorriendo el CRUDO, y el crudo de este festival tiene una función de
37 obras: bajaría uno. Acá las 37 obras viven en el catálogo, que existe desde
antes que la parrilla, así que los afiches se pueden tener listos hoy y no la
noche del miércoles.

TRES ORÍGENES, EN EL ORDEN QUE MANDA docs/POSTERS.md §2, y no dan lo mismo:

  1. EL AFICHE DE LA OBRA, de TMDB (w780). Vertical, es el que la ficha quiere.
  2. EL AFICHE EN LETTERBOXD (`og:image`), para la obra que tiene ficha allí y
     no tiene `poster_path` en TMDB. En este festival NO APORTÓ NINGUNO, y eso
     también se registra: las tres obras con `lbSlug` y sin afiche en TMDB
     —«Un aparato para detectar fantasmas», «Malas posturas» y «La Mona»—
     devolvieron la misma tarjeta cuadrada con el logo de Letterboxd. El paso
     se queda porque la próxima obra sí puede tenerlo; lo que lo hace seguro
     es `es_afiche()`, no la confianza en la fuente.
  3. EL STILL QUE PUBLICA EL FESTIVAL en la página de la obra (`og:image`).
     NO es un afiche: es un fotograma apaisado, y va como `posterSource:
     editorial` para que la vista lo encuadre a 16:9 en vez de estirarlo a 2:3
     (docs/POSTERS.md §2, fila 4). Mejor un fotograma honesto que un hueco, y
     mucho mejor que un apaisado estirado fingiendo ser un afiche.

CADA CANDIDATO SE MIRA EN DISCO, no se acepta por venir de donde viene. Ver
`es_afiche()`: lo que Letterboxd sirve cuando no tiene la obra es una tarjeta
de 500×500 con su propio logotipo, y el encuadre la estiraba a 780×1170 sin
rechistar. Se cazó midiendo los archivos ya bajados, no leyendo la URL.

EL STILL SE REDUCE Y SE COMPRIME. Tal como los sirve el sitio pesan hasta 871
KB —el festival sube el original de 2560×1440— y el service worker los cachea
para siempre. Van a 896 px de ancho con calidad 72: los 66 editoriales que ya
hay en producción miden entre 640 y 896 y pesan 63 KB de mediana. Reducir sin
comprimir no bastaba: a 896 px y calidad original uno seguía pesando 716 KB.
No se recorta: la proporción es la que publicó el festival.

SE BAJAN, NO SE ENLAZAN. Publicar la URL de image.tmdb.org deja el archivo sin
dueño y se salta `encuadrar-posters.py`, que solo trabaja con archivos locales:
son los 16 pósters sueltos que costó Villa del Cine. Y este sidecar, que va
versionado, NOMBRA cada archivo — que es lo que hace que `[asset-huerfano]` no
los tome por basura mientras el festival todavía no se publica.

Lee   festivals/staging/jardin-2026-catalogo.json
      festivals/staging/jardin-2026-catalogo-enriquecido.json
Esc.  festivals/staging/jardin-2026-posters.json
      assets/jardin-2026/<slug>.jpg
"""
import collections
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, norm, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/jardin-2026'
CAT = f'{ST}/jardin-2026-catalogo.json'
ENR = f'{ST}/jardin-2026-catalogo-enriquecido.json'
PARR = f'{ST}/jardin-2026-parrilla.json'


def solo_en_la_parrilla(cat):
    """Las obras que SE PROYECTAN y no están en el catálogo de la web.

    LA ESPINA ERA EL CATÁLOGO Y LA PROGRAMACIÓN ES MÁS ANCHA. El festival
    ficha en su web 37 obras, pero la parrilla proyecta algunas que nunca
    fichó: «Cien años de soledad: Eran más de tres mil», «Una sola golondrina
    no hace llover», «La casa del trueno»… Recorriendo solo el catálogo, esas
    obras no recibían NI UN INTENTO —ni TMDB, ni Letterboxd, ni nada—, y no se
    veía porque la cuenta del paso era sobre el catálogo: 37 de 37 parecía
    completo. Es el mismo error de espina que costó los afiches de Villa del
    Cine, y lo destapó Juan preguntando por qué faltaban (22 sep).

    Entran con lo que la parrilla imprime, que trae director, año y duración.
    """
    if not os.path.exists(PARR):
        return []
    tengo = {norm(o['titulo']) for o in cat}
    vistas, out = set(), []
    for f in json.load(open(PARR, encoding='utf-8'))['funciones']:
        for x in ([f] + (f.get('obras') or [])):
            t = re.sub(r'^Cine foro:\s*', '', x.get('titulo') or '')
            # los bloques («Muestra…», «Panel:…») no son obras y no llevan
            # afiche de película: se reconocen porque la parrilla no les
            # imprime ficha (ni director ni año).
            if not t or not x.get('director') or not x.get('anio'):
                continue
            k = norm(t)
            if k in tengo or k in vistas:
                continue
            vistas.add(k)
            out.append({'titulo': t, 'director': x.get('director'),
                        'anio': x.get('anio'), 'duracion_min': x.get('duracion_min'),
                        '_solo_parrilla': 'se proyecta y el festival no le publicó ficha'})
    return out
OUT = f'{ST}/jardin-2026-posters.json'

MINIMO = 5000       # menos que esto es un JPEG truncado, no una imagen
def sin_barras(ruta):
    """Quita las BARRAS DE CINEMASCOPE incrustadas en el fotograma.

    Varios stills de la web vienen con el 2.39:1 metido dentro de un 16:9, con
    franjas negras arriba y abajo. No son imagen: son el formato de la copia.
    `[poster-mirado]` las caza —«banda plana en un borde»— y tiene razón: en la
    tarjeta se ven como un recorte mal hecho.

    Se recorta solo lo que es PLANO Y OSCURO de verdad, con tope del 20% por
    lado, y se exige que la banda esté en LOS DOS bordes o que ocupe más del 4%:
    una sola fila oscura es arte, no barra.
    """
    from PIL import Image
    im = Image.open(ruta).convert('RGB')
    w, h = im.size
    px = im.load()

    def oscura(y):
        m = [px[x, y] for x in range(0, w, max(1, w // 40))]
        return max(max(c) for c in m) < 26

    top = next((y for y in range(int(h * 0.20)) if not oscura(y)), 0)
    bot = next((y for y in range(int(h * 0.20)) if not oscura(h - 1 - y)), 0)
    if max(top, bot) * 100 // h < 4:
        return
    im.crop((0, top, w, h - bot)).save(ruta, 'JPEG', quality=92)


ANCHO_STILL = 896   # el ancho más común de los 66 editoriales ya en producción
CALIDAD_STILL = 72  # con 100 (el defecto de sips) un still de 896 px pesa 700 KB

# OBRAS SIN NINGUNA IMAGEN, y por qué. Una obra sin entrada acá hace fallar el
# paso: el hueco se declara o se arregla, no se deja pasar.
SIN_IMAGEN_OK = {
    # LAS QUE SE PROYECTAN Y EL FESTIVAL NUNCA FICHÓ. Entran por la parrilla
    # —antes ni se intentaban, porque la espina de este paso era el catálogo—,
    # y para las cuatro se buscó en la web del festival (no tienen página: lo
    # dice su post-sitemap) y en TMDB con `ficha_tmdb`, que exige que año o
    # duración cuadren. Ninguna verifica. Queda escrito para que no se vuelvan
    # a buscar a ciegas.
    'Cien años de soledad: Eran más de tres mil':
        'es un EPISODIO de la serie de Netflix (S02E06, dir. Laura Mora), no '
        'una película: TMDB la tiene como serie y el candado de `ficha_tmdb` '
        'compara películas por año y duración, así que no verifica. El '
        'festival no le publicó ficha. Sin afiche hasta decidir si se usa el '
        'arte de la serie, que es una decisión de Juan.',
    'Cien años de soledad (SO2E6): Eran más de tres mil':
        'la misma obra con el rótulo del episodio en el título: la parrilla la '
        'imprime de las dos formas, el sábado y el viernes. Mismo motivo.',
    'Una sola golondrina no hace llover':
        'documental de Caribe Afirmativo (2021, 86 min). Sin página en '
        'festicinejardin.com —no está en su sitemap— y sin ficha verificable '
        'en TMDB. No hay imagen que bajar en ninguna fuente conocida.',
    'La casa del trueno':
        'sin página en la web del festival y sin ficha en TMDB. Cuatro '
        'directores acreditados (Dahian Cifuentes, Raúl Cifuentes, Tatiana '
        'Rojas, Marta Saiz), Colombia 2025, 33 min — solo lo dice la parrilla.',
    'Tres Mujeres guerreras':
        'EXISTE Y NO ESTÁ EN TMDB — candidata a alta. Lo destapó Juan (22 sep): '
        'IMDb la tiene como «Tres Mujeres Guerreras: 3 Kriegerinnen» (2014), '
        'tt4402368, porque es coproducción Colombia–Alemania y su otro título '
        'es alemán. Yo la había buscado solo por el título español. Comprobado '
        'después: TMDB no la tiene ni por «3 Kriegerinnen», ni por «Drei '
        'Kriegerinnen», ni por el español, ni por imdb_id. Camino de la casa '
        'para esto: darla de alta en TMDB (scripts/verificar-antes-de-alta.py '
        'y docs/PIPELINE Fase 3b), no inventarle un afiche.',
    'Gustavo, el observador invisible':
        'estreno de Antena 4 Jardín (25 min). Sin página en la web y sin TMDB: '
        'es una producción local que estrena en este festival.',
    'Deus ex necro machina': 'el festival no le publicó ficha: su slug '
                             '`deus-ex-necro-machina` REDIRIGE a la página de '
                             '«Primer amor», que es otra obra. Entra al '
                             'catálogo solo desde Instagram y no hay imagen '
                             'que bajar. Preguntado al festival.',
    'Elementales': 'su página en la web está etiquetada «Caleidoscopio 2025», '
                   'no 2026, así que no se toma como ficha de esta edición. '
                   'Entra solo desde Instagram. Preguntado al festival.',
    'Ubuntu: La métrica de los afectos': 'tiene ficha en la web pero sin '
                                         'imagen (`og:image` es el logo del '
                                         'festival, que el raspador descarta) '
                                         'y TMDB no la verifica.',
}


def baja(url, dest):
    """El archivo, con reintentos. Devuelve True si quedó una imagen real."""
    if os.path.exists(dest) and os.path.getsize(dest) > MINIMO:
        return True
    for intento in range(4):
        subprocess.run(['curl', '-sL', '--max-time', '60', '-A', UA,
                        '-o', dest, url], capture_output=True)
        if os.path.exists(dest) and os.path.getsize(dest) > MINIMO:
            return True
        time.sleep(2 * (intento + 1))
    if os.path.exists(dest):
        os.remove(dest)          # un truncado en assets/ es peor que nada
    return False


def dimensiones(p):
    def g(k):
        return int(subprocess.run(['sips', '-g', k, p], capture_output=True)
                   .stdout.decode().split(':')[-1])
    return g('pixelWidth'), g('pixelHeight')


def es_afiche(p):
    """¿Lo que se bajó es un AFICHE, o es otra cosa con forma de afiche?

    Se mira la imagen, no la URL. Letterboxd ya no sirve el placeholder
    `empty-poster` que documentaba POSTERS.md: cuando no tiene afiche devuelve
    en su `og:image` una tarjeta CUADRADA de 500×500 con su propio logo y
    «Your life in film». Pasa cualquier filtro por nombre de archivo, y el
    encuadre la estiraba a 780×1170 tan contenta — tres obras se habrían
    publicado con el logotipo de Letterboxd por afiche. Un afiche es vertical:
    si la proporción no está cerca de 2:3, no lo es."""
    w, h = dimensiones(p)
    return bool(h) and 0.55 <= w / h <= 0.80


def lb_poster(lb_slug):
    """El `og:image` de la ficha en Letterboxd. Lo que sea se comprueba luego."""
    r = subprocess.run(['curl', '-sL', '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/film/{lb_slug}/'],
                       capture_output=True)
    m = re.search(r'<meta property="og:image" content="([^"]+)"',
                  r.stdout.decode('utf-8', 'replace'))
    return m.group(1) if m else ''


def main():
    cat = json.load(open(CAT, encoding='utf-8'))['obras']
    extra = solo_en_la_parrilla(cat)
    if extra:
        print(f'   + {len(extra)} obra(s) que se proyectan sin ficha en la web: '
              + ', '.join(o['titulo'][:26] for o in extra))
        cat = cat + extra
    enr = json.load(open(ENR, encoding='utf-8'))['verificadas']
    E = {norm(k): v for k, v in enr.items()}
    os.makedirs(ASSETS, exist_ok=True)

    films, sin, fallos, descartes = [], [], [], []
    for i, o in enumerate(sorted(cat, key=lambda x: x['titulo']), 1):
        t = o['titulo']
        e = E.get(norm(t), {})
        dest = f'{ASSETS}/{slug(t)}.jpg'
        origen = fuente = ''
        # EL ÁRBOL DE docs/POSTERS.md §2, y cada candidato SE COMPRUEBA en disco
        # antes de aceptarlo: un afiche que no es vertical no es un afiche.
        candidatos = []
        if e.get('poster_path'):
            candidatos.append(
                (f'https://image.tmdb.org/t/p/w780{e["poster_path"]}', 'tmdb'))
        if e.get('lbSlug'):
            candidatos.append((lb_poster(e['lbSlug']), 'letterboxd'))
        for u, f_ in candidatos:
            if u and baja(u, dest):
                if es_afiche(dest):
                    origen, fuente = u, f_
                    break
                w, h = dimensiones(dest)
                descartes.append(f'«{t}»: {f_} devolvió {w}×{h} (r={w / h:.2f}), '
                                 f'no es un afiche vertical — se descarta')
                os.remove(dest)
        if not origen and o.get('imagen'):
            origen = o['imagen']
            fuente = 'editorial'
        if not origen:
            sin.append(t)
            if t not in SIN_IMAGEN_OK:
                fallos.append(f'«{t}» sin imagen y sin entrada en SIN_IMAGEN_OK')
            print(f'[{i:2}/{len(cat)}] —   {t[:44]:46} sin imagen', flush=True)
            continue
        if not baja(origen, dest):
            fallos.append(f'«{t}»: no se pudo bajar {origen[:70]}')
            print(f'[{i:2}/{len(cat)}] ✗   {t[:44]:46} falló la descarga', flush=True)
            continue
        if fuente == 'editorial':
            sin_barras(dest)
            # Reducir NO es comprimir: `sips -Z` conserva la calidad original y
            # un fotograma de 896 px seguía pesando 716 KB. Los dos pasos.
            subprocess.run(['sips', '-Z', str(ANCHO_STILL), '-s', 'format', 'jpeg',
                            '-s', 'formatOptions', str(CALIDAD_STILL),
                            dest, '--out', dest], capture_output=True)
        films.append({'title': t, 'poster': f'/assets/jardin-2026/{slug(t)}.jpg',
                      'posterSource': fuente, '_origen': origen})
        print(f'[{i:2}/{len(cat)}] OK  {t[:44]:46} {fuente}', flush=True)

    json.dump({'_provenance': provenance(
        'TMDB (image.tmdb.org, w780), Letterboxd (og:image) y el `og:image` de '
        'la ficha en festicinejardin.com — en ese orden, el de docs/POSTERS.md §2',
        que_aporta=f'{len(films)} imágenes de las {len(cat)} obras del catálogo, '
                   f'bajadas a assets/jardin-2026/',
        metodo='los dos primeros son afiches de verdad y van a 2:3; el still del '
               'festival es apaisado, se reduce a 896 px de ancho y va como '
               '`editorial`, que la vista encuadra a 16:9 en vez de estirarlo. No '
               'se publica la URL remota: el archivo se sirve desde el repo y este '
               'sidecar lo nombra'),
        'films': films, 'sin_imagen': sorted(sin), '_descartados': descartes,
        '_sin_imagen_por_que': SIN_IMAGEN_OK},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    c = collections.Counter(f['posterSource'] for f in films)
    print(f'\n{len(films)} de {len(cat)} obras con imagen — '
          f'{c["tmdb"]} afiches de TMDB · {c["letterboxd"]} de Letterboxd · '
          f'{c["editorial"]} stills del festival · {len(sin)} sin ninguna')
    for x in descartes:
        print('   ⚠', x)
    for t in sin:
        print(f'   · «{t}» — {SIN_IMAGEN_OK.get(t, "SIN DECLARAR")}')
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for x in fallos:
            print('   ✗', x)
        sys.exit(1)


if __name__ == '__main__':
    main()
