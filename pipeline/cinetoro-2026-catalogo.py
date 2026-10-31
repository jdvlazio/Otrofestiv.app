#!/usr/bin/env python3
"""cinetoro-2026-catalogo.py — las obras de CINETORO Experimental Film Festival
2026 (Toro, Valle; 10–15 nov 2026). PRE-ONBOARDING (radar #1268).

LA FUENTE (bajada a fuentes/cinetoro-2026/, 26 oct 2026): las 4 páginas de la
selección oficial en cinetoro.org/edicion-2026/. Cada obra es un bloque de líneas
    Título / Dirección / Lugar (ciudad o país) / Año / Duración / Sinopsis…
cerrado por su imagen (un FOTOGRAMA cuadrado 1024×1024, no un afiche: se miraron).
Dynamo no trae duración; La garganta del diablo, ni duración ni país (la imagen
dice «Colombia» en el nombre del archivo). Por eso el bloque se lee de atrás
para adelante desde la imagen, no por posiciones fijas.

La sección es el nombre de la competencia tal cual el festival (Título); el
nombre poético de cada una («Vector imaginado»…) va en `programa`.

El script FRENA si una página no da el número de obras contado a mano
(26 oct: 11 + 14 + 9 + 5 = 39; el radar decía 13 y 8, contó mal).

Escribe festivals/staging/cinetoro-2026-catalogo.json
"""
import html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f'{REPO}/fuentes/cinetoro-2026'
OUT = f'{REPO}/festivals/staging/cinetoro-2026-catalogo.json'
FECHA = '2026-10-26'

# página → (sección VERBATIM, programa VERBATIM, obras contadas, tipo)
PAGINAS = {
    'vector-imaginado-competencia-oficial-nacional': ('Competencia Oficial Nacional', 'Vector imaginado', 11, 'corto'),
    'geometria-de-la-diferencia-competencia-oficial-internacional': ('Competencia Oficial Internacional', 'Geometría de la diferencia', 14, 'corto'),
    'curvas-interlineadas-competencia-oficial-emergente': ('Competencia Oficial Emergente', 'Curvas Interlineadas', 9, 'corto'),
    'puntos-de-fuga-competencia-oficial-de-mediometrajes': ('Competencia Oficial de Mediometrajes', 'Puntos de fuga', 5, 'mediometraje'),
}
# La Nacional escribe la CIUDAD (Bogotá, Tunja…), no el país: todas son de Colombia
# (la convocatoria exige directores nacidos en Colombia).
CIUDADES_CO = {'Bogotá', 'Tunja', 'Medellín', 'Pasto'}
# Erratas de la web, corregidas contra el nombre de archivo de su propia imagen
# (lo subió el festival) y la sinopsis. Lo dudoso NO se corrige: va en _duda.
# Las correcciones de título y dirección viven como DATO, con su porqué, en
# festivals/staging/cinetoro-2026-correcciones.json → «catalogo_titulo» y
# «catalogo_director» (erratas contra el nombre de archivo de su imagen; caja).
_CORR = json.load(io.open(f'{REPO}/festivals/staging/cinetoro-2026-correcciones.json', encoding='utf-8'))
TIT = {k: v['a'] for k, v in _CORR.get('catalogo_titulo', {}).items()}
DIR = {k: v['a'] for k, v in _CORR.get('catalogo_director', {}).items()}
# Afiches y duraciones halladas fuera de la web (otros festivales), con su fuente
AFI = _CORR.get('catalogo_afiche', {})
DURX = {k: v['a'] for k, v in _CORR.get('catalogo_duracion', {}).items()}
PAIS_FALTANTE = {'La garganta del diablo': 'Colombia'}       # imagen «…-Mateo-Ramirez-Colombia-2026»
# Las dudas de la primera lectura se resolvieron con fuentes: ver «dudas_resueltas»
# y «catalogo_duracion» en cinetoro-2026-correcciones.json (26 oct).
DUDAS = {}
DUR = re.compile(r'^(\d+)\s*min\.?(?:\s*(?:y\s*)?(\d+)\s*sec\.?)?$', re.I)
ANIO = re.compile(r'^(19|20)\d\d$')


def lineas(path):
    s = io.open(path, encoding='utf-8').read()
    b = re.search(r'<body.*', s, re.S).group()
    b = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', b, flags=re.S)
    b = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r'\n[IMG \1]\n', b)
    b = re.sub(r'<[^>]+>', '\n', b)
    return [l.strip() for l in html.unescape(b).split('\n') if l.strip()]


def obras(slug, seccion, programa, tipo):
    ls = lineas(f'{SRC}/{slug}.html')
    i0 = ls.index('Close') + 2          # salta la descripción de la competencia
    bloque, out = [], []
    for l in ls[i0:]:
        if l == 'CINETORO':
            break
        if not l.startswith('[IMG '):
            bloque.append(l)
            continue
        img = l[5:-1]
        # el año es la primera línea de 4 dígitos; antes, título/dirección/lugar
        ia = next(k for k, x in enumerate(bloque) if ANIO.match(x))
        cab, resto = bloque[:ia], bloque[ia + 1:]
        titulo, director = cab[0], cab[1]
        lugar = ' '.join(cab[2:]).strip()
        dur_txt, dur = None, None
        if resto and DUR.match(resto[0]):
            dur_txt = resto.pop(0)
            m = DUR.match(dur_txt)
            dur = int(m.group(1)) + (1 if m.group(2) and int(m.group(2)) >= 30 else 0)
        titulo = TIT.get(titulo, titulo)
        director = DIR.get(director, director)
        pais = 'Colombia' if lugar in CIUDADES_CO else re.sub(r'\s*/\s*', ', ', lugar) or PAIS_FALTANTE.get(titulo)
        o = {'titulo': titulo, 'director': director, 'pais': pais, 'anio': int(bloque[ia]),
             'duracion_txt': dur_txt, 'duracion_min': dur,
             'sinopsis': '\n'.join(resto), 'tipo': tipo, 'seccion': seccion, 'programa': programa,
             'imagen_web': img, '_src': {'url': f'https://cinetoro.org/edicion-2026/{slug}/', 'date': FECHA}}
        if dur is None and titulo in DURX:
            o['duracion_min'] = DURX[titulo]
        if titulo in AFI:
            o['afiche'], o['_afiche_fuente'] = AFI[titulo]['a'], AFI[titulo]['_fuente']
            assert os.path.exists(f"{REPO}/{o['afiche']}"), o['afiche']
        if lugar in CIUDADES_CO:
            o['ciudad'] = lugar
        if titulo in DUDAS:
            o['_duda'] = DUDAS[titulo]
        out.append(o)
        bloque = []
    return out


def main():
    todas = []
    for slug, (sec, prog, n, tipo) in PAGINAS.items():
        ob = obras(slug, sec, prog, tipo)
        if len(ob) != n:
            sys.exit(f'✗ {slug}: {len(ob)} obras, se contaron {n} a mano')
        todas += ob
        print(f'  {sec}: {len(ob)}')
    d = {'_provenance': {'fuente': 'cinetoro.org/edicion-2026 — las 4 páginas de la selección oficial',
                         'capturado': FECHA,
                         'metodo': 'HTML: Título / Dirección / Lugar / Año / Duración / Sinopsis, cerrado por su imagen'},
         'obras': todas}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(todas)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
