#!/usr/bin/env python3
"""anibia-2026-catalogo.py — las obras de ANIBIA Festival de Animación 2026
(Bogotá, 20 oct–1 nov 2026). PRE-ONBOARDING.

LAS FUENTES (bajadas a fuentes/anibia-2026/, 21 oct 2026):
  · fichas/<n>.html — la ficha de cada programa en la Cinemateca de Bogotá
    (/node/peliculas/<n>). Es TEXTO: cada obra va como
        Título
         (Dir. X, año) País. m:ss min.
        Sinopsis
    y se lee de ahí, no a ojo. Las de Anibia se reconocen por el rótulo
    «Anibia Festival de Animación» / «Festival Anibia» (agenda/11, 80 y 112).
  · programacion.pdf — la programación oficial (Linktree), 13 págs. con texto:
    da la SECCIÓN de cada programa (Surgentes, Con acento nacional, Conexión,
    Costa a costa, Todxs a bordo) y las obras que no tienen ficha de sala.

La ficha 3579 (Fontanar del Río, «Animage BRASIL») repite las cinco obras de
la 3591 sin sinopsis y con otros redondeos: es OTRA FUNCIÓN del mismo programa,
no otras obras. Se usa como verificación cruzada (mismos títulos).

El script FRENA si un programa no da el número de obras que se contó a mano.

Escribe festivals/staging/anibia-2026-catalogo.json
"""
import html, io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

SRC = f'{REPO}/fuentes/anibia-2026'
OUT = f'{REPO}/festivals/staging/anibia-2026-catalogo.json'
FICHA = 'https://cinematecadebogota.gov.co/node/peliculas/{}?sede={}'
PDF = 'https://drive.google.com/uc?export=download&id=1oWVSdLh8OtO65UAX8pybuF2hhdnflkOK'
FECHA = '2026-10-21'

# nodo → (sede de la ficha, sección VERBATIM del PDF, programa VERBATIM del PDF, obras contadas)
PROGRAMAS = {
    3591: (11, 'Surgentes', 'Surgentes - Animage', 5),
    3592: (11, 'Surgentes', 'Surgentes - Con extremos', 8),
    3596: (11, 'Surgentes', 'Surgentes - Miyu', 6),
    3593: (11, 'Conexión', 'Conexión - Foco Pez Dorado', 4),
    3594: (11, 'Con acento nacional', 'Con acento nacional - Procesos de formación - Programa 1', 15),
    3617: (11, 'Con acento nacional', 'Con acento nacional - Procesos de formación - Programa 2', 18),
    3595: (11, 'Con acento nacional', 'Con acento nacional - Profesional - Programa 1', 7),
    3618: (11, 'Con acento nacional', 'Con acento nacional - Profesional - Programa 2', 6),
    3616: (11, 'Costa a costa', 'Costa a costa', 6),
    3692: (11, 'Costa a costa', 'Costa a costa - Lo mejor de Annecy 2026', 9),
}
# AFICHES que no vienen de TMDB (los de TMDB los pone el enriquecido). Cada ficha
# de la Cinemateca trae UN afiche oficial, de una sola de sus obras; se miraron
# todos (el título va impreso) y solo cuentan para la obra que muestran. Los
# demás de esas fichas ya tienen el de TMDB, que manda. El de «Lo mejor de
# Annecy» (3692) es un FOTOGRAMA sin título: no es afiche.
AFICHES = {
    'Aguacero': ('assets/anibia-2026/aguacero.jpg', 'afiche de la ficha 3594 de la Cinemateca, encuadrado 780×1170'),
    'La Pecera': ('assets/filcmar-2026/la-pecera.jpg', 'el afiche oficial con que la publicamos en FILCMAR 2026 (= el de la ficha 3617)'),
}
# EL PAÍS va en español y separado por comas (lo que segmenta la app para las
# banderas); la ficha lo escribe en tres idiomas y con «/», «-» o «and». El
# texto de la ficha queda en `_pais_ficha`.
NOMBRE_PAIS = {'The Netherlands': 'Países Bajos', 'Germany': 'Alemania', 'Columbia': 'Colombia',
               'USA': 'Estados Unidos', 'Suède': 'Suecia', 'Ukraine': 'Ucrania', 'Finland': 'Finlandia'}


def pais_es(p):
    partes = [x.strip() for x in re.split(r'\s*(?:/|,| - |-| and )\s*', p) if x.strip()]
    return ', '.join(NOMBRE_PAIS.get(x, x) for x in partes)


DIR = re.compile(r'^(?P<pre>.*?)\(\s*Dir\.?\s*(?P<dir>.+?)(?:,\s*(?P<anio>\d{4}|sin estrenar))?\)\s*'
                 r'(?P<pais>.*?)\.?\s+(?P<dur>[\d:,]+)\s*min\.?\s*$')


def texto(n):
    s = open(f'{SRC}/fichas/{n}.html', encoding='utf-8').read()
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', s))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    t = t[t.find('Salas asociadas'):t.find('Más Películas')]
    lineas = [l.strip() for l in t.split('\n') if l.strip()]
    i = lineas.index('2D')                       # «Formato: 2D» cierra la cabecera
    fin = lineas.index('Idioma', i)
    return lineas, lineas[i + 1:fin]


def minutos(d):
    if ':' in d:
        m, s = d.split(':')
        return int(m) + (1 if int(s) >= 30 else 0)
    return max(1, round(float(d.replace(',', '.'))))


def obras_de(n):
    _, cuerpo = texto(n)
    obras = []
    for k, l in enumerate(cuerpo):
        m = DIR.match(l)
        if not m:
            continue
        titulo = m['pre'].strip() or cuerpo[k - 1].strip()
        d = re.sub(r'\s+', ' ', m['dir']).strip()
        d = re.sub(r'\s*\(Kaboom Distribution$', '', d)   # 3618: «(Kaboom Distribution, 2025)» va pegado
        o = {'titulo': titulo, 'director': d,
             'pais': m['pais'].strip().rstrip('.').strip(),
             'duracion_txt': f"{m['dur']} min", 'duracion_min': minutos(m['dur'])}
        if m['anio'] and m['anio'].isdigit():
            o['anio'] = int(m['anio'])
        elif m['anio']:
            o['_anio_txt'] = m['anio']
        obras.append(o)
    # sinopsis: lo que va entre una obra y el título de la siguiente
    idx = [k for k, l in enumerate(cuerpo) if DIR.match(l)]
    for j, k in enumerate(idx):
        hasta = (idx[j + 1] - (0 if DIR.match(cuerpo[idx[j + 1]])['pre'].strip() else 1)) if j + 1 < len(idx) else len(cuerpo)
        sin = ' '.join(cuerpo[k + 1:hasta]).strip()
        if sin:
            obras[j]['sinopsis'] = sin
    return obras


def main():
    if not os.path.isdir(f'{SRC}/fichas'):
        sys.exit('✗ faltan las fichas: bajar /node/peliculas/<n> a fuentes/anibia-2026/fichas/')
    obras = []
    for n, (sede, seccion, programa, contadas) in PROGRAMAS.items():
        L = obras_de(n)
        if len(L) != contadas:
            sys.exit(f'✗ ficha {n} dio {len(L)} obras y se contaron {contadas}')
        for o in L:
            if pais_es(o['pais']) != o['pais']:
                o['_pais_ficha'], o['pais'] = o['pais'], pais_es(o['pais'])
            o.update({'tipo': 'corto', 'seccion': seccion, 'programa': programa,
                      '_src': {'url': FICHA.format(n, sede), 'date': FECHA}})
            obras.append(o)

    # Cruce con la ficha de Fontanar (3579): mismas cinco obras de Animage
    lin, _ = texto(3579)
    tit_f = [plano(re.split(r'\(\s*Dir', l)[0]) for l in lin if '(Dir' in l]
    tit_a = [plano(o['titulo']) for o in obras if o['programa'] == 'Surgentes - Animage']
    if tit_f != tit_a:
        sys.exit(f'✗ Animage: Fontanar {tit_f} ≠ Centro {tit_a}')
    for o in obras:
        if o['titulo'] == 'Viaje bajo la lluvia':
            o['_duda'] = ('año: la ficha del Centro (3591) dice 2024 y la de Fontanar (3579) 2014; '
                          'el corto de Wesley Rodrigues («Viagem na Chuva») es de 2014')

    # Los largos sueltos
    lin, cuerpo = texto(3590)
    obras.append({'titulo': 'El hijo de puta (O filho da puta)', 'titulo_original': 'O filho da puta',
                  'director': 'Tânia Anaya, Otto Guerra, Sávio Leite, Erica Rocha',
                  'anio': 2026, 'pais': 'Brasil', 'duracion_min': 72, 'tipo': 'largo',
                  'seccion': 'Surgentes', 'programa': 'Surgentes - Película inaugural',
                  'sinopsis': ' '.join(cuerpo), '_src': {'url': FICHA.format(3590, 11), 'date': FECHA}})
    lin, cuerpo = texto(3513)
    assert 'Estefanía Piñeres' in lin, 'MU-KI-RA: cambió la ficha'
    obras.append({'titulo': 'Mukira', '_titulo_variantes': ['MUKIRA (programación PDF)', 'MU-KI-RA (Cinemateca, CEFE)'],
                  'director': 'Estefanía Piñeres', 'anio': 2026, 'pais': 'Colombia, España',
                  'duracion_min': 82, 'tipo': 'largo', 'seccion': 'Todxs a bordo',
                  'programa': 'Todxs a bordo - Estreno nacional',
                  'sinopsis': ' '.join(x for x in cuerpo if x not in ('Festival Anibia',)),
                  '_src': {'url': FICHA.format(3513, 112), 'date': FECHA}})
    # «Conexión de largo aliento» (Javeriana, 30 oct): conversaciones sobre el
    # INICIO de la producción de dos largos. No son proyecciones; la obra no existe aún.
    for t, estudio in (('Mi papá el camión', 'Pez Dorado'), ('Desechable', 'Nocroma')):
        obras.append({'titulo': t, 'estudio': estudio, 'tipo': 'proyecto',
                      'seccion': 'Conexión de largo aliento', 'programa': 'Conexión de largo aliento',
                      '_nota': 'conversación sobre un largometraje en producción (PDF pág. 12); no se proyecta',
                      '_src': {'url': PDF, 'date': FECHA}})

    for o in obras:
        if o['titulo'] in AFICHES:
            o['afiche'], o['_afiche_fuente'] = AFICHES[o['titulo']]
            assert os.path.exists(f"{REPO}/{o['afiche']}"), o['afiche']
    json.dump({'_provenance': provenance('Cinemateca de Bogotá (fichas de programa) + programación PDF de Anibia',
                                         metodo='HTML de las fichas, «Título / (Dir. X, año) País. m:ss min. / sinopsis»'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras en {len(PROGRAMAS) + 4} programas → {os.path.relpath(OUT, REPO)}')


def plano(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


if __name__ == '__main__':
    main()
