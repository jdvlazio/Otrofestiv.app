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

Bogotá (25–29 nov) no publicó nada todavía.
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/aleste-2026-crudo.json'
IG = 'https://www.instagram.com/p/'
MAMM_URL = 'https://www.elmamm.org/producto/'
MAMM, COLOMBO = 'MAMM', 'Centro Colombo Americano'
ESPECIAL, FOKUS, MUSEO = 'Al Este Especial', 'Fokus: Las grietas en el muro', 'Al Este en el MAMM'
MAMM_ACC = 'Con boleta: $14.000 general; $10.000 mayores de 60, menores de 12 y estudiantes'
COL_ACC = 'Con boleta'

# (día, hora, título, sede, sección, fuente, extra)
F = [
    ('18', '19:00', 'Noche inaugural', COLOMBO, ESPECIAL, (IG + 'DfkttriN6pD/', None),
     dict(event_kind='apertura', obras=['Latidos: el grafiti como arte, el grafiti como forma de vida',
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

cat = {o['titulo']: o for o in json.load(io.open(f'{REPO}/festivals/staging/aleste-2026-catalogo.json', encoding='utf-8'))['obras']}
funciones = []
for dia, hora, tit, sede, sec, (url, lam), extra in F:
    r = {'titulo': tit, 'dia': '2026-11-' + dia, 'hora': hora, 'sede': sede, 'seccion': sec,
         'acceso': MAMM_ACC if sede == MAMM else COL_ACC,
         '_src': {'url': url, 'date': '2026-11-12', 'tipo': 'festival-ig' if 'instagram' in url else 'festival-web'}}
    if lam:
        r['_src']['lamina'] = lam
    if sede == MAMM:
        r['ticket_url'] = url
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

io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
    '_provenance': provenance('MAMM (fichas del ciclo) + láminas de @aleste.colombia (3, 5 y 10 nov 2026)',
                              metodo='transcripción a ojo; láminas cruzadas con ig-lecturas.py',
                              que_aporta='día, hora, sede, acceso'),
    '_fuera': {'Bogotá 25–29 nov': 'sin programación publicada al 12 nov'},
    'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')
