#!/usr/bin/env python3
"""aleste-2026-crudo.py — la programación de Al Este 2026 en Medellín → crudo.

LAS FUENTES (12 nov 2026):
  · MAMM: ficha de cada película (fuentes/aleste-2026/mamm-*.html), con día y
    hora («21 noviembre, sábado - 4:30 p.m.»), boleta $14.000 general / $10.000
    reducida y compra en línea en la misma ficha.
  · IG @aleste.colombia: p/DfSV6Z3lpE1 (3 nov) y p/DfYe-5Slr8E (5 nov), una
    lámina por función en el Centro Colombo Americano; p/DfkttriN6pD (10 nov),
    la noche inaugural (corto «Latidos» + «La última ronda en Venecia»).
    p/DfVsaFKhkYM dice «Lunes 18 de Noviembre»: el 18 es miércoles; manda la
    fecha, que repiten las otras láminas.

ACCESO: MAMM, el precio de su página. Colombo: «Asegura tus entradas en el link
del perfil» y «el aforo para la noche de apertura es limitado», sin precio →
con boleta, sin monto.

Bogotá: IG p/DfsHqtAlpmC (13 nov), Cinemateca de Bogotá, «Con boleta» (el pie: «antes de que se agoten las boletas»), sin precio.

16 nov 2026 — BOGOTÁ SALE DE LA WEB OFICIAL (aleste-2026-programa.json, 40
fichas de alestfestival.com/programa2026): 26 funciones (33 líneas, 2 bloques), con sala. Antes eran
las 5 de la lámina del 13 nov, que la web confirma. Medellín sigue con sus
fuentes (MAMM + láminas, más nuevas o la más temprana donde chocan) y toma de
la web la sala y la sección.
  · varias obras a la misma hora y sala = UN bloque (Hecho en Colombia):
    una función con sus obras, titulada con el bloque de la web;
  · «Seguida de conversatorio con…» / «Presentación con el director» → Q&A
    del equipo; «Seguida de cineforo» → conversación (has_qa, sin tipo);
  · «Seguida de la premiación» → la clausura.
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/aleste-2026-crudo.json'
IG = 'https://www.instagram.com/p/'
MAMM_URL = 'https://www.elmamm.org/producto/'
MAMM, COLOMBO, CINEMATECA = 'MAMM', 'Centro Colombo Americano', 'Cinemateca de Bogotá'
CINE_SEC = 'Al Este en la Cinemateca'
ESPECIAL, FOKUS, MUSEO = 'Al Este Especial', 'Fokus: Las grietas en el muro', 'Al Este en el MAMM'
MAMM_ACC = 'Con boleta: $14.000 general; $10.000 mayores de 60, menores de 12 y estudiantes'
COL_ACC = 'Con boleta'

# (día, hora, título, sede, sección, fuente, extra)
F = [
    ('18', '19:00', 'Noche inaugural', COLOMBO, ESPECIAL, (IG + 'DfkttriN6pD/', None),
     # 16 nov (vigía): el link del perfil es un formulario de inscripción sin precio
     # (linktr.ee/alestefestivalcolombia) → libre con inscripción (regla 13 oct)
     dict(event_kind='apertura', acceso='Entrada libre con inscripción previa',
          registration_url='https://forms.gle/d6aSy5hBEQr3R2m98', obras=['Latido. El grafiti como arte, el grafiti como forma de vida.',
                                        'La última ronda en Venecia'])),
    ('19', '18:30', 'The Souffleur', MAMM, MUSEO, (MAMM_URL + 'the-souffleur/', None), {}),
    ('19', '19:00', 'Cenizas y diamantes', COLOMBO, FOKUS, (IG + 'DfYe-5Slr8E/', '02.jpg'), {}),
    ('20', '16:30', 'Regreso de África', COLOMBO, FOKUS, (IG + 'DfYe-5Slr8E/', '03.jpg'), {}),
    ('20', '18:30', 'Padre', MAMM, MUSEO, (MAMM_URL + 'padre/', None), {}),
    ('20', '19:00', 'Los inocentes encantadores', COLOMBO, FOKUS, (IG + 'DfYe-5Slr8E/', '05.jpg'), {}),
    ('20', '19:00', 'Gioia mia', COLOMBO, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '03.jpg'), {}),
    ('21', '14:00', 'Pucallpa la Europea', COLOMBO, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '04.jpg'), {}),
    ('21', '14:30', 'La tierra prometida', COLOMBO, FOKUS, (IG + 'DfYe-5Slr8E/', '04.jpg'), {}),
    ('21', '16:30', '1982', MAMM, MUSEO, (MAMM_URL + '1982/', None), {}),
    ('22', '14:00', 'Gioia mia', COLOMBO, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '03.jpg'), {}),
    ('22', '16:00', 'Londres', MAMM, MUSEO, (MAMM_URL + 'londres/', None), {}),
]

PROGRAMA = f'{REPO}/festivals/staging/aleste-2026-programa.json'
WEB = 'https://www.alestfestival.com/programa2026'
web = json.load(io.open(PROGRAMA, encoding='utf-8'))['obras']
web_med = {(f['dia'], f['hora'], o['titulo']): f['sala'] for o in web for f in o['funciones'] if f['ciudad'] == 'Medellín'}


def seccion_web(sec):
    import re
    return re.sub(r'\s*[-–]\s*Bloque \d+$', '', sec)


SEC = {o['titulo']: seccion_web(o['seccion']) for o in web}

cat = {o['titulo']: o for o in json.load(io.open(f'{REPO}/festivals/staging/aleste-2026-catalogo.json', encoding='utf-8'))['obras']}
funciones = []
for dia, hora, tit, sede, sec, (url, lam), extra in F:
    sec = SEC.get(tit, sec)
    if extra.get('event_kind') == 'apertura':
        sec = 'Al Este Especial'
    r = {'titulo': tit, 'dia': '2026-11-' + dia, 'hora': hora, 'sede': sede, 'seccion': sec,
         'acceso': MAMM_ACC if sede == MAMM else COL_ACC,
         '_src': {'url': url, 'date': '2026-11-12', 'tipo': 'festival-ig' if 'instagram' in url else 'festival-web'}}
    if lam:
        r['_src']['lamina'] = lam
    if sede == MAMM:
        r['ticket_url'] = url
    sala = web_med.get((r['dia'], hora, tit))
    if sala and sala != 'Sala de cine':
        r['sala'] = sala
    obras = extra.pop('obras', None)
    r.update(extra)
    if obras:
        r.update(tipo='evento', obras=[cat[t] for t in obras])
        r['duracion_min'] = 120   # corto sin duración publicada + 98 min de la película (TMDB)
    else:
        o = cat[tit]
        for k in ('director', 'pais', 'anio', 'duracion_min'):
            if o.get(k):
                r[k] = o[k]
    funciones.append(r)

# ── Bogotá: la web ─────────────────────────────────────────────────────────
# MOVIDA (19 nov): «Desde acá veo la tormenta» va en el Bloque 2 (dom 29, 14:00),
# no en el 1 como dice la web: post Df7JJA8x1GK de @elforro_6 con @aleste.colombia
# de coautor + catálogo oficial PDF del 18 nov. Lo más reciente del festival manda.
MOVIDAS = {'Desde acá veo la tormenta': ('2026-11-29', '14:00', 'Competencia Hecho en Colombia – Bloque 2')}
for o in web:
    if o['titulo'] in MOVIDAS:
        dia_, hora_, sec_ = MOVIDAS[o['titulo']]
        o['seccion'] = sec_
        for f in o['funciones']:
            if f['ciudad'] == 'Bogotá':
                f['dia'], f['hora'] = dia_, hora_
grupos = {}
for o in web:
    for f in o['funciones']:
        if f['ciudad'] == 'Bogotá':
            grupos.setdefault((f['dia'], f['hora'], f['sede'], f['sala']), []).append((o, f))
for (dia, hora, sede, sala), lst in sorted(grupos.items()):
    o0, f0 = lst[0]
    notas = {f['nota'] for _, f in lst}
    if len(notas) > 1:
        sys.exit(f'✗ {dia} {hora} {sala}: notas distintas en un mismo bloque: {notas}')
    r = {'dia': dia, 'hora': hora, 'sede': sede, 'acceso': COL_ACC,
         '_src': {'url': f'{WEB}/{o0["pagina"]}', 'date': '2026-11-16', 'tipo': 'festival-web'}}
    if sala:
        r['sala'] = sala
    if len(lst) > 1:
        bloque = o0['seccion'].replace('Competencia ', '')
        r.update(titulo=bloque.replace(' - ', ' – '), seccion=seccion_web(o0['seccion']), tipo='evento',
                 obras=[cat[o['titulo']] for o, _ in lst],
                 duracion_min=sum(o['duracion_min'] for o, _ in lst))
        r['_src']['url'] = WEB
    else:
        c = cat[o0['titulo']]
        r.update(titulo=o0['titulo'], seccion=seccion_web(o0['seccion']))
        for k in ('director', 'pais', 'anio', 'duracion_min'):
            if c.get(k):
                r[k] = c[k]
    nota = (f0['nota'] or '').lower()
    if 'conversatorio' in nota or 'presentación con' in nota:
        r.update(has_qa=True, qa_type='team')
    elif 'cineforo' in nota:
        r['has_qa'] = True
    # Inauguración y Clausura de Bogotá son la proyección de UNA película: se
    # quedan como película (con su sinopsis); la sección ya dice qué noche es.
    # Un event_kind la volvería evento y se perdería la ficha.
    funciones.append(r)
n_bog = sum(1 for f in funciones if f['sede'].startswith('Cinemateca'))
if n_bog != 26:
    sys.exit(f'✗ Bogotá: {n_bog} funciones, se contaron 26 en la web (33 líneas; los 2 bloques juntan 9)')

io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
    '_provenance': provenance('MAMM (fichas del ciclo) + láminas de @aleste.colombia (3, 5 y 10 nov 2026) + web oficial programa2026 (16 nov, Bogotá)',
                              metodo='transcripción a ojo; láminas cruzadas con ig-lecturas.py',
                              que_aporta='día, hora, sede, acceso'),
    'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')
