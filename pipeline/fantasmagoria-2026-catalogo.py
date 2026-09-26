#!/usr/bin/env python3
"""fantasmagoria-2026-catalogo.py — las siete selecciones de Fantasmagoría 8 → catálogo.

PRE-ONBOARDING (26 sep 2026, radar #963). El 8° Festival Internacional de Cine
Fantástico y de Terror de Medellín (15–25 oct) publicó su selección y todavía no
la parrilla: no hay día, hora ni sede de ninguna función. Igual que FILCMAR, no
hay crudo sino catálogo, y se puede enriquecer porque cada obra trae director,
país, año y duración.

LA FUENTE es la página `/edicion-2026/` de festivalfantasmagoriamedellin.com, con
TEXTO: un bloque por sección y una línea por obra,
    «Título. Dir: Nombre / Género / País, Año, Duración´ / (Estreno …)».
Se guarda en fuentes/fantasmagoria-2026/ (fuera del repo) y este script la lee
de ahí; `--bajar` la vuelve a traer.

LA SEGUNDA LECTURA son las tres noticias de cortos del 24 sep (Oficial,
Latinoamericanos, Animados), que el festival publicó aparte: todo corto de esas
secciones tiene que aparecer en su noticia. Si una obra está en una lectura y no
en la otra, el paso falla.

LAS SECCIONES, con la palabra del festival. El nombre sale de la cabecera de
cada bloque, salvo la de Asedio, que no tiene cabecera propia en su bloque y
se toma del resumen de la misma página. La colombiana se llama DOS veces
distinto en la misma página —«Selección de Cortometrajes Colombianos» en su
bloque, «Selección Colombia es Fantástica» en el resumen y en los jurados—; se
guarda la del bloque y la otra queda escrita, para que Juan elija al montar.

LO QUE LA LÍNEA NO SIGUE, escrito en tabla y no adivinado:
  · «Schichinin No Samurai (Seven Samurai) Dir:» — sin punto antes de «Dir:».
  · «Rio Bravo … / Western, Estados Unidos, 1959» — el género pegado al país.
  · «Trading Cards» — la ficha técnica repetida dos veces en la misma línea.
  · la duración con tres apóstrofes distintos (´ ’ ').
El género se guarda verbatim, con su errata: «Thiller» en Green Room.
"""
import html
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'fantasmagoria-2026'
BASE = 'https://festivalfantasmagoriamedellin.com'
FUENTES = f'{REPO}/fuentes/{FID}'
PAGINA = ('edicion-2026.html', f'{BASE}/edicion-2026/')
NOTICIAS = {   # sección del catálogo → su noticia del 24 sep
    'Selección Oficial Cortometrajes':
        ('noticia-cortos-oficial.html', f'{BASE}/noticias/seleccion-oficial-cortometrajes/'),
    'Selección Latinoamericana de Cortometrajes':
        ('noticia-cortos-latinos.html', f'{BASE}/noticias/seleccion-cortometrajes-latinoamericanos/'),
    'Selección de Cortometrajes Animados':
        ('noticia-cortos-animados.html', f'{BASE}/noticias/seleccion-de-cortometrajes-animados-2026/'),
}
DESTINO = f'{REPO}/festivals/staging/{FID}-catalogo.json'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/140 Safari/537.36'

# Las cabeceras de bloque, en el orden de la página. La de Asedio no existe en
# su bloque: el bloque empieza por su texto curatorial.
SECCIONES = [
    'Selección Oficial Largometrajes de Ficción',
    'Selección Oficial Largometrajes Documentales',
    'Selección Asedio: Las murallas del miedo',
    'Selección Oficial Cortometrajes',
    'Selección de Cortometrajes Animados',
    'Selección Latinoamericana de Cortometrajes',
    'Selección de Cortometrajes Colombianos',
]
ANCLA_ASEDIO = 'En la octava edición del festival se explora el cine sobre los asedios'
OTRO_NOMBRE = {'Selección de Cortometrajes Colombianos': 'Selección Colombia es Fantástica'}
# lo que se espera por sección: si la página cambia, el paso falla en vez de
# publicar un catálogo corto sin avisar
ESPERADAS = {
    'Selección Oficial Largometrajes de Ficción': 8,
    'Selección Oficial Largometrajes Documentales': 4,
    'Selección Asedio: Las murallas del miedo': 5,
    'Selección Oficial Cortometrajes': 8,
    'Selección de Cortometrajes Animados': 9,
    'Selección Latinoamericana de Cortometrajes': 6,
    'Selección de Cortometrajes Colombianos': 7,
}
# LA MISMA OBRA, OTRO NOMBRE EN SU NOTICIA. La segunda lectura cazó cuatro, y
# cada una está mirada: ninguna es una obra que falte.
#   · las dos animadas, con su título en INGLÉS en la noticia —y así se guardan,
#     que es una llave más para buscarlas en TMDB—;
#   · «Night Whisper», en singular en la noticia y en plural en la página;
#   · el apóstrofo, que es otro carácter (´ contra ’) — eso lo absorbe la
#     comparación, no esta tabla.
EN_LA_NOTICIA = {
    'Bestias de la Muerte': ('Beasts of Death', 'en'),
    'La Habitación del Macho Cabrío': ('The Devil Room', 'en'),
    'Remembrance of Night Whispers': ('Remembrance of Night Whisper', 'grafia'),
}
APOSTROFOS = str.maketrans({'´': "'", '’': "'", '‘': "'"})

# el género pegado al país, en la única línea donde pasa
GENERO_EN_EL_PAIS = {'Rio Bravo': ('Western', 'Estados Unidos')}


def bajar(nombre, url):
    os.makedirs(FUENTES, exist_ok=True)
    p = f'{FUENTES}/{nombre}'
    if '--bajar' in sys.argv or not os.path.exists(p):
        r = subprocess.run(['curl', '-sSfL', '--max-time', '40', '-A', UA, '-o', p, url])
        if r.returncode:
            sys.exit(f'✗ no se pudo bajar {url}')
    return io.open(p, encoding='utf-8', errors='ignore').read()


def texto(h):
    h = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h, flags=re.S)
    h = re.sub(r'<br\s*/?>|</(p|div|li|h\d)>', '\n', h)
    t = html.unescape(re.sub(r'<[^>]+>', '', h))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t)


RE_OBRA = re.compile(r'^(?P<t>.+?)\.?\s*Dir:\s*(?P<d>[^/]+?)\s*/(?P<resto>.+)$')
RE_FICHA = re.compile(r'(?P<pais>[^/]+?),\s*(?P<anio>\d{4}),\s*(?P<dur>\d+)\s*[´’\']')


def obra(linea, seccion):
    m = RE_OBRA.match(linea.strip())
    if not m:
        return None
    t, d, resto = m.group('t').strip(), m.group('d').strip(), m.group('resto')
    f = RE_FICHA.search(resto)          # la PRIMERA ficha: «Trading Cards» la repite
    if not f:
        sys.exit(f'✗ «{t}»: la línea no trae «País, Año, Duración» — mirarla: {linea!r}')
    antes = resto[:f.start()]
    generos = [g.strip() for g in antes.split('/') if g.strip()]
    pais = f.group('pais').strip(' /')
    if t in GENERO_EN_EL_PAIS:
        g, p = GENERO_EN_EL_PAIS[t]
        assert pais == f'{g}, {p}', (t, pais)
        generos, pais = [g], p
    estreno = re.search(r'\(([^)]*(?:Estreno|Aniversario)[^)]*)\)', resto[f.end():])
    o = {'titulo': t, 'director': d, 'pais': pais, 'anio': int(f.group('anio')),
         'duracion_min': int(f.group('dur')), 'genero': ', '.join(generos),
         'seccion': seccion}
    # «Huo zhe yan (The Furious)»: el título original y, entre paréntesis, el
    # inglés. Se publica como lo escribe el festival; el original va aparte
    # para que el enricher lo busque también.
    mp = re.match(r'^(?P<o>.+?)\s*\((?P<en>[^)]+)\)$', t)
    if mp:
        o['titulo_original'] = mp.group('o').strip()
        o['titulo_en'] = mp.group('en').strip()
    if estreno:
        o['estreno'] = estreno.group(1).strip()
    return o


def main():
    txt = texto(bajar(*PAGINA))
    i = txt.find('RESUMEN DE LAS SELECCIONES')
    assert i >= 0, 'la página ya no tiene el resumen de selecciones — mirarla'
    cuerpo = txt[i:]
    # dónde empieza el BLOQUE de cada sección (no su mención en el resumen)
    inicio = {}
    for s in SECCIONES:
        if s == 'Selección Asedio: Las murallas del miedo':
            k = cuerpo.find(ANCLA_ASEDIO)
        else:
            occ = [m.start() for m in re.finditer(re.escape(s), cuerpo)]
            k = occ[-1] if occ else -1
        assert k >= 0, f'no encuentro el bloque de «{s}»'
        inicio[s] = k
    fin = cuerpo.find('JURADOS SELECCIÓN')
    orden = sorted(inicio, key=inicio.get)
    obras, cuenta = [], {}
    for n, s in enumerate(orden):
        a = inicio[s]
        b = inicio[orden[n + 1]] if n + 1 < len(orden) else fin
        for linea in cuerpo[a:b].split('\n'):
            o = obra(linea, s)
            if o:
                if s in OTRO_NOMBRE:
                    o['_seccion_tambien'] = OTRO_NOMBRE[s]
                obras.append(o)
                cuenta[s] = cuenta.get(s, 0) + 1
    for s, n in ESPERADAS.items():
        if cuenta.get(s, 0) != n:
            sys.exit(f'✗ «{s}»: {cuenta.get(s, 0)} obras, se esperaban {n}')

    # la segunda lectura: cada corto está en la noticia de su sección
    faltan = []
    for s, (nombre, url) in NOTICIAS.items():
        nt = texto(bajar(nombre, url)).lower().translate(APOSTROFOS)
        for o in obras:
            if o['seccion'] != s:
                continue
            otro, clase = EN_LA_NOTICIA.get(o['titulo'], (o['titulo'], ''))
            if otro.lower().translate(APOSTROFOS) not in nt:
                faltan.append(f'{o["titulo"]} ({s})')
            elif clase == 'en':
                o['titulo_en'] = otro
    _sobran = sorted(set(EN_LA_NOTICIA) - {o['titulo'] for o in obras})
    if _sobran:
        sys.exit('✗ EN_LA_NOTICIA nombra obras que no están en el catálogo: ' + ' · '.join(_sobran))
    if faltan:
        sys.exit('✗ cortos del catálogo que no están en su noticia: ' + ' · '.join(faltan))

    json.dump({'_provenance': provenance(
        f'{PAGINA[1]} (las siete selecciones, con texto) + las tres noticias de '
        'cortos del 24 sep como segunda lectura'),
        'obras': obras}, open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras en {len(cuenta)} secciones · los cortos, '
          f'cruzados con sus tres noticias → {os.path.relpath(DESTINO, REPO)}')
    for s in orden:
        print(f'   {cuenta[s]:2}  {s}')


if __name__ == '__main__':
    main()
