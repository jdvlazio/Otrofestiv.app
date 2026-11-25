#!/usr/bin/env python3
"""bogoshorts-2026-programas.py — los cortos que BOGOSHORTS ya publicó, por programa.

PRE-ONBOARDING (23 oct 2026). La lista completa de cortos por programa NO está
publicada: el menú «Secciones y cortos 2026» de festival.bogoshorts.com apunta a
http://localhost/categoria. Lo que sí existe:

  · tres boletines de prensa (info.bogoshorts.com/sccs/prensa/2026/24bsff/), con
    la lista «Título - DIR. Director. País, año» al final:
      005 Especial METRÓPOLIS        → ES-METRO
      007 Fuera de Competencia       → SO-FCO
      009 Festivales (3 alianzas)    → ES-NEXOS, HUMOR, FES-LADRA
  · los pies de IG de @bogoshorts (Apify, sin sesión), «🎥 Título — Dir. X 🇨🇴»:
      PAC-DOC, PAC-FIC, PAC-EXP, ES-PER, F3-ALIENS, FES-LADRA

HUMOR no está en la leyenda de la grilla: es la celda «HUMOR (65') + StandUp»
de la Sala Gaitán; el boletín 009 la llama «HUMOR EN CORTO – NOCHE DE HUMOR».
FES-LADRA sale en las dos fuentes: el boletín manda en dirección/país/año, el
pie de IG CONTRASTA (mismos 5 títulos, o frena).

El script FRENA si un programa no da el número de obras que su fuente declara.
Escribe festivals/staging/bogoshorts-2026-programas.json
"""
import html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

F = f'{REPO}/fuentes/bogoshorts-2026'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-programas.json'
BOL = 'https://info.bogoshorts.com/sccs/prensa/2026/24bsff/'

# boletín → [(rótulo de la lista en el boletín, código de la grilla, obras declaradas)]
BOLETINES = {
    '005_especial_metropolis': [('Conozca a continuación las obras', 'ES-METRO', 4)],
    '007_fuera_de_competencia': [('Selección Oficial - Fuera de Competencia:', 'SO-FCO', 4)],
    '009_festivales': [('ESPECIAL NEXOS', 'ES-NEXOS', 5),
                       ('HUMOR EN CORTO – NOCHE DE HUMOR', 'HUMOR', 6),
                       ('PANORAMA DE CINE COLOMBIANO EN PARÍS – PACCPA', 'FES-LADRA', 5)],
}
# shortcode de IG → (código, obras declaradas en el pie)
IG = {'Dewkg_ukX-2': ('PAC-DOC', 4), 'Det96D6EXZh': ('PAC-FIC', 4), 'De0HT9sDnpy': ('PAC-EXP', 6),
      'DecGoIkDrVs': ('ES-PER', 7), 'DehCoz4kZkM': ('F3-ALIENS', 5), 'DeSwrgsDmSX': ('FES-LADRA', 5)}
# La LISTA del boletín trae erratas que su propio cuerpo corrige («Elisabeth
# Caravell» → «Caravella», «Víctor Orozc» → «Orozco», «Col, Ale», «Colombi»,
# «Yugo» sin país). Se capturan TAL CUAL: corregirlas aquí sería una tabla de
# excepciones en el script ([excepcion-en-crudo]); van como afirmación cuando
# se arme la función (docs/FUNCION.md).
BANDERA = {'🇨🇴': 'Colombia', '🇫🇷': 'Francia', '🇬🇧': 'Reino Unido', '🇮🇷': 'Irán', '🇵🇹': 'Portugal',
           '🇳🇿': 'Nueva Zelanda', '🇩🇪': 'Alemania'}


def texto(path):
    t = io.open(path, encoding='utf-8', errors='replace').read()
    t = re.sub(r'(?s)<(script|style).*?</\1>', '', t)
    t = re.sub(r'<br\s*/?>|</p>|</li>|</tr>|</h\d>|</div>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return [re.sub(r'\s+', ' ', l).strip() for l in t.split('\n') if l.strip()]


LINEA = re.compile(r'^(?P<t>.+?) - DIR\.\s*(?P<d>[^.]+(?:\.[A-Z][^.]*)*)\.\s*(?P<p>.*?),?\s*(?P<a>(19|20)\d\d)\s*$')


def de_boletin(nombre, rotulo, n):
    ls = texto(f'{F}/{nombre}.html')
    i = next(k for k, l in enumerate(ls) if l.startswith(rotulo) or rotulo in l)
    obras = []
    for l in ls[i + 1:]:
        m = re.match(r'^(?P<t>.+?) - DIR\.\s*(?P<resto>.+)$', l)
        if not m:
            if obras:
                break
            continue
        resto = m['resto']
        ma = re.search(r',?\s*((?:19|20)\d\d)\s*$', resto)
        anio = int(ma.group(1)) if ma else None
        resto = resto[:ma.start()] if ma else resto
        # «Director. País, País» — el último punto separa (los nombres no llevan punto)
        d, _, p = resto.rpartition('. ')
        if not d:                       # «Carlos Gómez Salamanca, 2021»: sin país
            d, p = resto.strip(' .,'), ''
        obras.append({'titulo': m['t'].strip(), 'director': d.strip(), 'pais': p.strip(' .,'),
                      'anio': anio, '_src': {'url': BOL + nombre + '.html'}})
    if len(obras) != n:
        sys.exit(f'✗ {nombre} «{rotulo}» dio {len(obras)} obras y declara {n}')
    return obras


def de_ig(post, n):
    obras = []
    for l in post['caption'].split('\n'):
        m = re.match(r'^\s*(?:🎥|🎬)\s*(?P<t>.+?)\s*(?:—|\|)\s*Dir\.\s*(?P<d>.+?)\s*$', l)
        if not m:
            continue
        d = m['d']
        flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', d)
        d = re.sub(r'[\U0001F1E6-\U0001F1FF]', '', d)
        d = re.sub(r'\(@[^)]*\)', '', d).strip()
        obras.append({'titulo': m['t'].strip(), 'director': d,
                      'pais': ', '.join(BANDERA.get(f, f) for f in flags),
                      '_src': {'url': post['url'], 'date': post['timestamp'][:10]}})
    if len(obras) != n:
        sys.exit(f'✗ IG {post["shortCode"]} dio {len(obras)} obras y declara {n}')
    return obras


def main():
    progs = {}
    for nombre, listas in BOLETINES.items():
        for rotulo, cod, n in listas:
            progs[cod] = de_boletin(nombre, rotulo, n)
    posts = {p['shortCode']: p for p in json.load(open(f'{F}/ig-apify-2026-10-23.json', encoding='utf-8'))
             if p.get('ownerUsername') == 'bogoshorts'}
    for sc, (cod, n) in IG.items():
        obras = de_ig(posts[sc], n)
        if cod in progs:   # contraste: los mismos títulos, o frena
            a = sorted(o['titulo'].lower() for o in progs[cod])
            b = sorted(o['titulo'].lower() for o in obras)
            if a != b:
                sys.exit(f'✗ {cod}: el boletín y el IG {sc} no listan las mismas obras\n  {a}\n  {b}')
            continue
        progs[cod] = obras
    json.dump({'_provenance': provenance('boletines de prensa 005/007/009 + pies de IG @bogoshorts (Apify, 23 oct 2026)',
                                         metodo='lista «Título - DIR.» del boletín; «🎥 Título — Dir.» del pie'),
               'programas': progs}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(progs)} programas, {sum(map(len, progs.values()))} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
