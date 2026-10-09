#!/usr/bin/env python3
"""fantasmagoria-2026-verificar.py — el build contra las dos fuentes oficiales del festival.

  · cada largometraje de la página «Largometrajes 2026» tiene en el build las
    MISMAS funciones (día y hora) que esa página, en los dos sentidos;
  · el día de la semana impreso casa con la fecha;
  · el acceso («Entrada libre» / «con boleta») de cada función coincide;
  · el año y la duración publicados son los de la ficha del largo;
  · toda sede tiene pin verificado a mano, salvo la de una transmisión en línea.

Las dos fuentes del festival se contradicen en algunas funciones. Cada
contradicción conocida está en CONTRADICCIONES con lo que se publicó y por
qué; una que no esté ahí detiene el paso.
"""
import datetime
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'fantasmagoria-2026'
DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

# (título, día, hora) → qué se hizo. Mirado en las dos páginas el 29 sep.
CONTRADICCIONES = {
    ('Al Final del Espectro', '2026-10-19', '17:00'): 'la página de largos dice lunes 19; la parrilla, martes 20 (Colombo). Se publica la parrilla; CONFIRMADO por el festival (DM, 8 oct): sáb 17 18:30 Parque de los Deseos y mar 20 17:00 Colombo',
    ('Al Final del Espectro', '2026-10-20', '17:00'): 'ver la del lunes 19',
    ('Schichinin No Samurai (Seven Samurai)', '2026-10-16', '18:30'): 'la parrilla dice «Entrada Libre»; la página de largos, «Entrada con boleta». Se publica la parrilla; CONFIRMADO por el festival (DM, 8 oct): entrada libre, 19:00',
    ('Hoodsteps', '2026-10-22', '18:40'): 'no es contradicción: el corto que acompaña a You Are The Film («+ Hoodsteps»); la página de largos lo lista aparte',
    ('Hoodsteps', '2026-10-23', '16:00'): 'ídem',
    # LA BASE DE SU CARTELERA (v2, 6 oct) contra la página de largos (28 sep): la
    # base es la más reciente y la que el equipo edita, y manda (7 oct). Preguntado.
    ('Critters', '2026-10-18', '19:00'): 'la página de largos dice dom 18, 7:00 p. m.; la base v2, sáb 17 a las 19:00 (el 18 queda la de X-Files). Se publica la base',
    ('Critters', '2026-10-17', '19:00'): 'ver la del domingo 18',
    ('Pura Sangre', '2026-10-20', '18:30'): 'la página de largos dice 6:30 p. m.; la base v2, 18:00. Se publica la base',
    ('Pura Sangre', '2026-10-20', '18:00'): 'ver la de las 18:30',
    # la base v5 (7 oct) la pasa a las 19:00 en la Sala 1; la página de largos sigue en 18:30
    ('Schichinin No Samurai (Seven Samurai)', '2026-10-16', '19:00'): 'la página de largos dice 6:30 p. m. (Sala 2); la base v5, 19:00 en la Sala 1. Se publica la base',
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def acc(t):
    t = (t or '').lower()
    return 'confirmar' if 'confirmar' in t else 'libre' if 'libre' in t else 'boleta' if 'boleta' in t else '?'


def main():
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    largos = json.load(io.open(f'{REPO}/festivals/staging/{FID}-largos.json', encoding='utf-8'))['peliculas']
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    pub = {}
    for f in build['films']:
        for o in [f] + (f.get('film_list') or []):
            pub.setdefault(plano(o['title']), []).append(f)
    avisos = []
    for t, p in largos.items():
        k = plano(t)
        fs = pub.get(k) or next((v for kk, v in pub.items() if kk.startswith(k + ' ') or k.startswith(kk + ' ')), [])
        en_build = {(f['day'], f['time']): f for f in fs}
        en_web = {(x['dia'], x['hora']): x for x in p['funciones']}
        for x in p['funciones']:
            wd = DIAS[datetime.date.fromisoformat(x['dia']).weekday()]
            if x['dia_impreso'].lower() != wd:
                avisos.append((t, x['dia'], x['hora'], f'la página de largos imprime «{x["dia_impreso"]}» y el {x["dia"][-2:]} es {wd}'))
        for kd in en_web.keys() - en_build.keys():
            avisos.append((t, *kd, 'en la página de largos y NO en la parrilla (build)'))
        for kd in en_build.keys() - en_web.keys():
            avisos.append((t, *kd, 'en la parrilla (build) y NO en la página de largos'))
        for f in {id(x): x for x in fs}.values():
            dur = int(re.match(r'\d+', f.get('duration') or '0').group())
            if p.get('anio') and f.get('year') != p['anio']:
                avisos.append((t, f['day'], f['time'], f'año: la ficha dice {p["anio"]}, publicamos {f.get("year")}'))
            if p.get('duracion_min') and dur != p['duracion_min']:
                avisos.append((t, f['day'], f['time'], f'duración: la ficha dice {p["duracion_min"]}, publicamos {dur}'))
        for kd in en_web.keys() & en_build.keys():
            f = en_build[kd]
            a_web = acc(en_web[kd]['sede_y_acceso'])
            a_pub = 'libre' if f.get('is_free') else 'confirmar' if not f.get('ticket_url') and 'desconocido' in json.dumps(f) else 'boleta'
            if a_web in ('libre', 'boleta') and a_web != a_pub:
                avisos.append((t, *kd, f'acceso: la página de largos dice {a_web}, publicamos {a_pub}'))
    nuevos = [a for a in avisos if (a[0], a[1], a[2]) not in CONTRADICCIONES]
    fallos = [f'{t} · {d} {h}: {m}' for t, d, h, m in nuevos]
    for v, x in build['venues'].items():
        g = geo.get(v.rsplit(' - ', 1)[0], {})
        # toda sede lleva pin (Juan, 30 sep); la única sin él es la de una
        # transmisión, y entonces TODAS sus funciones son en línea
        _fs = [f for f in build['films'] if f.get('venue') == v]
        if x.get('lat') is None and not (_fs and all(f.get('online') for f in _fs)):
            fallos.append(f'sede {v!r} sin pin')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano')
    if fallos:
        sys.exit('✗ el build y las fuentes del festival no cuadran:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {len(largos)} largometrajes con sus funciones iguales en las dos fuentes · '
          f'{len(avisos)} contradicciones conocidas, cada una con su decisión · '
          f'{sum(1 for x in build["venues"].values() if x.get("lat") is not None)} sedes con pin manual · '
          f'{sum(1 for f in build["films"] if f.get("online"))} funciones en línea')


if __name__ == '__main__':
    main()
