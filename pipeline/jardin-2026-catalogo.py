#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-catalogo.py — el catálogo del 11° Festival de Cine de Jardín.

QUÉ HAY Y QUÉ NO. El festival publicó sus obras entre el 14 y el 15 sep 2026:
una página propia por obra, con ficha completa —país, idioma, género, duración,
dirección, producción, guion, año, sinopsis y hasta premios—. Lo que NO publicó
es la PARRILLA: ni un día, ni una hora, ni una sede. Por eso esto es un catálogo
y no un crudo: el formato intermedio exige los tres y no se inventan.

EL ÍNDICE ES EL SITEMAP, no el menú (PROTOCOLO §0·bis, lección de
#NarrarElFuturo). `post-sitemap.xml` fecha cada página al minuto, así que se
sabe exactamente qué entró en esta edición: las 22 de CALEIDOSCOPIO el 14 y el
15, y las 15 de la Muestra Central el 15 por la tarde.

DOS FORMAS DE FICHA, y hay que aceptar las dos:
  · los LARGOS ponen la etiqueta y el valor en renglones distintos
    («País:» / «México»);
  · los CORTOS los mezclan en una línea («Duración: 17 min») y además usan
    «Estreno:» donde los otros usan «Año:».

⚠ TRAMPA REGISTRADA POR EL RADAR (#811): el banner de «programación» de la home
enlaza `PROGRAMACION-FCJ-2025_-1.pdf` — es de la edición PASADA. Y los sitemaps
del plugin de agenda (`wcs-*`) están congelados en 2018: no sirven de señal.

Lee   https://festicinejardin.com/post-sitemap.xml  (+ una página por obra)
Esc.  festivals/staging/jardin-2026-catalogo.json
"""
import io, json, os, re, subprocess, sys, time
import html as _html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/jardin-2026'
SITEMAP = 'https://festicinejardin.com/post-sitemap.xml'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'

# Páginas de sept 2026 que NO son obra, con su motivo.
NO_OBRA = {
    'caleidoscopio-2026': 'índice de la sección, no una obra',
}
# LA MISMA OBRA ESCRITA DE DOS FORMAS. El catálogo de Instagram se leyó a ojo de
# una lámina y quedó «Jiru luiai» con ele; la web, que la escribe el festival a
# máquina, dice «Jiru iuiai» con i latina. Sin esta línea entra dos veces, que
# es peor que entrar mal: un corto duplicado en el catálogo se cuenta dos veces
# en todo lo que venga después.
MISMA_OBRA = {'jiru luiai algo malo': 'jiru iuiai algo malo'}
CAMPOS = [('pais', 'País'), ('idioma', 'Idioma'), ('genero', 'Género'),
          ('duracion', 'Duración'), ('director', 'Dirección'),
          ('produccion', 'Producción'), ('guion', 'Gui[oó]n'),
          ('anio', 'A[ñn]o de estreno|A[ñn]o|Estreno'), ('clasificacion', 'Clasificación de edad')]


def bajar(url, nombre, siempre=False):
    """La página, de la caché o de la red.

    EL ÍNDICE NUNCA SE CACHEA. Las fichas de obra sí —su contenido no cambia y
    son 37 peticiones—, pero `post-sitemap.xml` es la lista de QUÉ EXISTE, y
    cacheada convierte al raspador en ciego: el festival publicó las fichas de
    «Deus ex necro machina» y «Elementales» el 21 sep y el paso siguió leyendo
    el índice del 20 a las 20:01, así que para nosotros no existían. Se vio al
    preguntar por qué faltaban afiches (Juan, 22 sep).

    Una caché sin caducidad sobre un índice no acelera: esconde.
    """
    p = f'{CACHE}/{nombre}'
    if siempre or not os.path.exists(p) or os.path.getsize(p) < 3000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
        time.sleep(0.2)
    return io.open(p, encoding='utf-8', errors='replace').read()


def texto(h):
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.S | re.I)
    t = _html.unescape(re.sub(r'<[^>]+>', '\n', t))
    return [x.strip() for x in t.split('\n') if x.strip()]


def campo(L, etiqueta):
    """El valor de «Etiqueta:», venga en la misma línea o en la siguiente."""
    for i, x in enumerate(L):
        m = re.match(rf'^(?:{etiqueta})\s*:\s*(.*)$', x, re.I)
        if not m:
            continue
        v = m.group(1).strip()
        if not v and i + 1 < len(L):
            v = L[i + 1].strip()
        v = v.strip(' .,')
        if v and not re.match(r'^(Sinopsis|Mensaje|Correo)', v, re.I):
            return v
    return None


def minutos(d):
    """«8:28» son 8 min 28 s, no 8 h: el sitio escribe la duración de las dos
    formas y sin esto once cortos se caían por no llevar la palabra «min»."""
    if not d:
        return None
    m = re.search(r'(\d+):(\d{2})', d)
    if m:
        return int(m.group(1)) + (1 if int(m.group(2)) >= 30 else 0)
    m = re.search(r'(\d+)\s*min', d, re.I)
    if m:
        return int(m.group(1))
    # y a veces es un número pelado: «Duración:» / «14». Viene etiquetado como
    # duración, así que no hay riesgo de confundirlo con un año.
    return int(d.strip()) if re.fullmatch(r'\d{1,3}', d.strip()) else None


def parse(url, h):
    L = texto(h)
    # EL MENÚ ES IDÉNTICO EN TODAS LAS PÁGINAS, y contiene «Caleidoscopio 2026»:
    # buscar la sección en la página entera la ponía en las 25 obras, largos
    # incluidos. El contenido empieza tras «Seleccionar página» — antes va el
    # menú, que en este sitio son veinticinco renglones de ediciones pasadas.
    _c = next((i for i, x in enumerate(L) if 'Seleccionar página' in x), 0)
    L = L[_c:]
    slug = url.rstrip('/').rsplit('/', 1)[-1]
    # el título es el <title> sin el nombre del sitio: la maqueta lo repite
    # después del menú, y el menú tiene 25 renglones idénticos en cada página
    m = re.search(r'<title>([^<]*)</title>', h)
    titulo = re.sub(r'\s*[-–]\s*Festival de Cine de Jardin.*$', '', _html.unescape(m.group(1))).strip() if m else slug
    d = {'titulo': titulo, '_slug': slug, '_src': url}
    for clave, etq in CAMPOS:
        v = campo(L, etq)
        if v:
            d[clave] = v
    if d.get('anio'):
        a = re.search(r'(19|20)\d\d', d['anio'])
        d['anio'] = int(a.group(0)) if a else None
    d['duracion_min'] = minutos(d.get('duracion'))
    # SECCIÓN: la línea de categorías que la maqueta pinta bajo el título
    # («— — — Documental , — — Caleidoscopio 2026» / «— Muestras 11FCJ»).
    # en el CONTENIDO entero: los cortos ponen la categoría justo bajo el
    # título y los largos la ponen después de la ficha técnica. El menú, que
    # dice «Caleidoscopio 2026» en todas las páginas, ya quedó fuera arriba.
    cats = ' '.join(L)
    if 'Caleidoscopio 2026' in cats:
        d['seccion'] = 'CALEIDOSCOPIO'
        mc = re.search(r'(Documental|Ficci[oó]n|Experimental)', cats)
        if mc:
            d['categoria'] = mc.group(1).replace('Ficcion', 'Ficción')
    elif 'Muestras 11FCJ' in cats:
        d['seccion'] = 'Muestra Central'
    for i, x in enumerate(L):
        if re.match(r'^Sinopsis\s*:', x, re.I):
            s = re.sub(r'^Sinopsis\s*:\s*', '', x).strip() or (L[i + 1] if i + 1 < len(L) else '')
            if len(s) > 40:
                d['sinopsis'] = s.strip()
            break
    m = re.search(r'<meta property="og:image" content="([^"]+)"', h)
    if m and 'logo' not in m.group(1).lower():
        d['imagen'] = m.group(1)
    return d


def main():
    x = bajar(SITEMAP, 'post-sitemap.xml', siempre=True)
    urls = [(u, f) for u, f in re.findall(r'<url>\s*<loc>([^<]+)</loc>\s*<lastmod>([^<]*)</lastmod>', x)
            if f.startswith('2026-09')]
    obras, fuera = [], []
    for u, f in sorted(urls, key=lambda r: r[1]):
        slug = u.rstrip('/').rsplit('/', 1)[-1]
        if slug in NO_OBRA:
            fuera.append((slug, NO_OBRA[slug]))
            continue
        d = parse(u, bajar(u, f'{slug}.html'))
        # una obra tiene dirección Y duración; lo que no, es otra cosa
        if not (d.get('director') and d.get('duracion_min')):
            fuera.append((slug, 'sin dirección o sin duración: no es ficha de obra'))
            continue
        # PÁGINAS DE OTRA EDICIÓN: el sitio retocó en septiembre fichas de
        # ediciones pasadas («Elementales» es Caleidoscopio 2025), así que la
        # fecha del sitemap NO basta para decir que algo es de esta edición.
        if not d.get('seccion'):
            fuera.append((slug, 'ficha de otra edición: su categoría no es de 2026'))
            continue
        d['_publicado'] = f[:10]
        obras.append(d)

    # COBERTURA INVERSA contra la selección que el festival anunció en
    # Instagram el 2 y el 4 sep: verificar lo transcrito no verifica lo que
    # falta. Dos cortos de esa lista NO tienen ficha en la web —«Elementales»,
    # cuya página sigue etiquetada «Caleidoscopio 2025», y «Deus ex necro
    # machina», cuyo slug el sitio REUTILIZÓ para la página de «Primer amor»
    # (redirige allí, y son obras distintas: Mateo M. Correa vs Iván Luna
    # Dulcey)—. Entran igual, con lo que IG da y diciendo de dónde salen: una
    # obra anunciada no deja de existir porque su página no esté.
    ig_p = f'{ST}/jardin-2026-caleidoscopio.json'
    sueltas = []
    if os.path.exists(ig_p):
        tengo = {norm(o['titulo']) for o in obras}
        for o in json.load(io.open(ig_p, encoding='utf-8'))['obras']:
            _k = norm(o['titulo'])
            if MISMA_OBRA.get(_k, _k) in tengo:
                continue
            obras.append({**o, '_solo_ig': 'anunciada en Instagram; sin ficha en la web el 16 sep'})
            sueltas.append(o['titulo'])

    import collections
    sec = collections.Counter(o.get('seccion') or '—' for o in obras)
    io.open(f'{ST}/jardin-2026-catalogo.json', 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'festicinejardin.com — una página por obra, halladas por post-sitemap.xml',
            metodo='ficha de la web, que trae país, idioma, género, duración, dirección, producción, guion, año y sinopsis. El sitemap fecha cada página al minuto: así se sabe qué entró en esta edición.',
            alcance='Las obras publicadas. NO hay parrilla: ni día, ni hora, ni sede. El festival es del 24 al 27 de septiembre.',
            trampa='el banner de «programación» de la home enlaza el PDF de 2025; los sitemaps del plugin de agenda están congelados en 2018'),
        '_festival': {'nombre': 'Festival de Cine de Jardín', 'edicion': 11,
                      'ciudad': 'Jardín, Antioquia', 'fechas': '24–27 de septiembre de 2026',
                      'tema': 'Ecos de Voces Silenciadas',
                      'web': 'https://festicinejardin.com/',
                      'ig': 'https://www.instagram.com/festicinejardin/',
                      'radar': 811},
        '_secciones': dict(sec), '_obras': len(obras),
        '_solo_en_instagram': sueltas,
        '_grafia': ['«Jiru iuiai \u201cAlgo malo\u201d»: la web la escribe con i latina y el catálogo '
                    'leído de la lámina de Instagram tenía «luiai» con ele. Manda la web, que la escribe '
                    'el festival a máquina; la lámina se leyó a ojo.'],
        'obras': obras}, ensure_ascii=False, indent=1) + '\n')
    print(f'── jardin-2026-catalogo.json · {len(obras)} obras · {dict(sec)}')
    for o in obras:
        print(f"  {(o.get('seccion') or '—')[:16]:<17} {o['titulo'][:34]:<36} "
              f"{str(o.get('anio') or '—'):<6} {str(o.get('duracion_min') or '—'):>4} min · "
              f"{(o.get('pais') or '—')[:18]:<20} {'sinopsis' if o.get('sinopsis') else 'SIN sinopsis'}")
    if fuera:
        print('  fuera:')
        for s, m in fuera:
            print(f'    {s}: {m}')


if __name__ == '__main__':
    main()
