#!/usr/bin/env python3
"""ficcali-2026-catalogo.py — la Selección Oficial del 18° FICCALI, ficha por ficha.

LA FUENTE es la web del festival (ficcali.com). La página «Selección de
películas 2026» (WP 12862) arma sus listas con JavaScript; lo que sí está en el
HTML son sus ONCE subpáginas, una por sección, con el enlace a la ficha de cada
obra. Cada ficha (tipo `pelicula`) trae:

    Selección oficial
    Género: Drama · Duración: 121 min · País: Bélgica · Año: 2026 · Idioma: Español
    <título>
    <rótulo de la sección (a veces «Competencia» y debajo la competencia)>
    <sinopsis, uno o dos párrafos>
    Funciones                      ← vacío: la ficha NO dice cuándo se proyecta
    Dirigido por / <director> / <biografía> / créditos …

La API REST expone el tipo `pelicula`, pero sus campos ACF vienen vacíos: el
dato está en el HTML. La fecha de publicación de una ficha no dice la edición
(se reusan fichas de años anteriores): lo que la hace 2026 es estar enlazada
desde una subpágina de la Selección 2026.

    python3 pipeline/ficcali-2026-catalogo.py          # usa la caché
    python3 pipeline/ficcali-2026-catalogo.py --bajar  # vuelve a bajar todo
"""
import html
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

DIR = f'{REPO}/fuentes/ficcali-2026'
SECCIONES = f'{DIR}/seleccion-secciones.json'
DESTINO = f'{REPO}/festivals/staging/ficcali-2026-catalogo.json'
# FICHAS PROGRAMADAS FUERA DE LAS SUBPÁGINAS: la sección no tiene subpágina
# (¡Que viva la música!), pero la obra está en la programación 2026 —el
# lanzamiento del sáb 3 en La Tertulia— y su ficha existe
EXTRA = {'https://ficcali.com/pelicula/para-vivir-el-implacable-tiempo-de-pablo-milanes/': '¡Que viva la música!'}
UA = 'Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15'
CAMPO = re.compile(r'^(Género|Duración|País|Año|Idioma):\s*(.*)$')
# LOS RÓTULOS DE SECCIÓN que la ficha pone entre el título y la sinopsis: los
# nombres de categoría del sitio (categorias.json) más «Competencia». Lo que no
# es uno de ellos es sinopsis — también una línea corta: la sinopsis suele
# empezar con el título en cursiva, partido en su propio renglón.
_CAT = f'{DIR}/categorias.json'
ROTULOS = {'competencia'} | ({v[0].strip().lower() for v in json.load(io.open(_CAT, encoding='utf-8')).values()}
                            if os.path.exists(_CAT) else set())


def bajar_secciones():
    r = subprocess.run(['curl', '-s', 'https://ficcali.com/wp-json/wp/v2/pages?parent=12862&per_page=100'],
                       capture_output=True, text=True).stdout
    pags = json.loads(r, strict=False)
    out = {}
    for p in pags:
        c = p['content']['rendered']
        out[p['slug']] = {'titulo': html.unescape(p['title']['rendered']), 'id': p['id'],
                          'modificada': p['modified_gmt'],
                          'peliculas': list(dict.fromkeys(re.findall(
                              r'href="(https://ficcali.com/pelicula/[^"#?]+?)/?"', c)))}
    json.dump({'subpaginas': out}, io.open(SECCIONES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def cuerpo(p):
    """Las líneas de la ficha, después del menú del sitio."""
    c = io.open(p, encoding='utf-8').read()
    c = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', c, flags=re.S)
    L = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', c)).split('\n') if x.strip()]
    i = max(i for i, x in enumerate(L) if x == 'Ediciones Anteriores')
    return L[i + 1:]


def ficha(L):
    d, i = {}, L.index('Selección oficial') + 1 if 'Selección oficial' in L else 0
    while i < len(L) and CAMPO.match(L[i]):
        k, v = CAMPO.match(L[i]).groups()
        d[k] = v.strip()
        i += 1
    titulo = L[i]
    fin = L.index('Funciones') if 'Funciones' in L else len(L)
    resto = L[i + 1:fin]
    # el rótulo de la sección: «Competencia» suelto y debajo la competencia, o
    # directamente la sección; la sinopsis es lo que sigue (líneas largas)
    rot = []
    while resto and resto[0].strip().lower() in ROTULOS:
        rot.append(resto.pop(0))
    # las cursivas parten la frase en renglones: se pegan con espacio, y sin
    # espacio delante de la puntuación que las sigue
    sinopsis = re.sub(r'\s+([,.;:)])', r'\1', re.sub(r'\s+', ' ', ' '.join(resto))).strip()
    j = L.index('Dirigido por') + 1 if 'Dirigido por' in L else None
    director = L[j] if j is not None and j < len(L) else None
    # SIN NOMBRE: hay fichas donde debajo de «Dirigido por» va directo la
    # biografía (Aguapanela). No se adivina: queda vacío y lo resuelve la cascada
    if director and (len(director) > 60 or director.endswith('.') or director in (
            'Producción', 'Guión', 'Dirección de fotografía')):
        director = None
    # dos fichas con el campo cruzado: Muiyukuna trae «2026» como país y Tuktu,
    # «País: Colombia» dentro del valor
    pais = re.sub(r'^País:\s*', '', d.get('País') or '').strip()
    if re.fullmatch(r'(19|20)\d{2}', pais):
        pais = ''
    d['País'] = pais
    dur = re.match(r'(\d+)', d.get('Duración', ''))
    anio = re.search(r'(19|20)\d{2}', d.get('Año', ''))
    return {'titulo': titulo, 'director': director,
            'pais': d.get('País') or None, 'anio': int(anio.group()) if anio else None,
            'duracion_min': int(dur.group(1)) if dur else None,
            'genero': d.get('Género') or None, 'idioma': d.get('Idioma') or None,
            'rotulo': ' · '.join(rot) or None, 'sinopsis': sinopsis or None}


def main():
    if '--bajar' in sys.argv or not os.path.exists(SECCIONES):
        bajar_secciones()
    S = json.load(io.open(SECCIONES, encoding='utf-8'))['subpaginas']
    os.makedirs(f'{DIR}/fichas', exist_ok=True)
    obras, fallos = {}, []
    pares = [(u, s['titulo']) for _, s in sorted(S.items()) for u in s['peliculas']] + list(EXTRA.items())
    for u, sec in pares:
        if True:
            slug = u.rstrip('/').split('/')[-1]
            p = f'{DIR}/fichas/{slug}.html'
            if '--bajar' in sys.argv or not os.path.exists(p) or os.path.getsize(p) < 5000:
                subprocess.run(['curl', '-sL', '--max-time', '30', '-A', UA, u, '-o', p])
                time.sleep(0.3)
            try:
                f = ficha(cuerpo(p))
            except (ValueError, IndexError) as e:
                fallos.append(f'{u}: {e}')
                continue
            o = obras.setdefault(slug, {**f, 'url': u, 'secciones': []})
            if sec not in o['secciones']:
                o['secciones'].append(sec)
    if fallos:
        sys.exit('✗ fichas que no se leen:\n  · ' + '\n  · '.join(fallos))
    sin = [o['titulo'] for o in obras.values() if not o.get('sinopsis')]
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('ficcali.com, Selección de películas 2026 (11 subpáginas de la página 12862)',
                                  url='https://ficcali.com/seleccion-de-peliculas-2026/',
                                  metodo='subpágina por sección → ficha `pelicula` de cada obra (HTML)'),
        'obras': sorted(obras.values(), key=lambda o: o['titulo'])}, ensure_ascii=False, indent=1))
    print(f'✓ {len(obras)} obras en {len(S)} secciones · {len(sin)} sin sinopsis → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
