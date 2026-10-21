#!/usr/bin/env python3
"""anibia-2026-verificar.py — lo que se va a publicar, contra las fuentes, por OTRO camino.

El crudo transcribe el PDF a mano y toma las obras del catálogo. Este paso mira
el BUILD —lo que llega a la app— y NO reusa esa transcripción:

  1. LAS LÁMINAS, leídas a ojo por un lector independiente (lectura B, en
     -ojos.json `items`, con su propia regla de hora «3:00 p.m.» y su propia
     tabla de sedes): cada ítem es UNA función del build en su día, hora y sede,
     y el build no publica nada que no esté en una lámina. Las afirmaciones
     `time` mueven su función (Fontanar, 31 oct). Fuera, solo lo «Evento para
     aliados».
  2. LA AGENDA de la Cinemateca (agenda-11/80/112.html): toda función de un
     programa de Anibia en la agenda está en el build en ese día y esa hora, con
     la SALA de la agenda; las del Centro, salvo la inaugural, con su link de
     TuBoleta (el de la ficha, o el corregido declarado en el crudo).
  3. LAS FICHAS de la Cinemateca: la lista de obras de cada programa del build,
     en su orden, es la de la ficha, leída del HTML crudo con otra regla (el
     texto que precede a cada «(Dir»), no con el parser del catálogo.
  4. Toda sede con su pin puesto a mano.
Las lecturas A y C (scratchpad del cruce, 21 oct) coincidieron con estas: no
se versionan, quedaron en el informe.
"""
import collections, html, importlib.util, io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'anibia-2026'
SRC = f'{REPO}/fuentes/anibia-2026'
ST = f'{REPO}/festivals/staging'
CINE = 'Cinemateca de Bogotá - Bogotá'
# la tabla de sedes de la LECTURA B (sus palabras) → sede del build
SEDE_B = {
    'Cinemateca de Bogotá / Centro': CINE,
    'Cinemateca de Bogotá / Fontanar del Río': 'Cinemateca Fontanar del Río - Bogotá',
    'CEFE Chapinero': 'CEFE Chapinero - Bogotá',
    'Cinemateca Sala Alterna UNAL': 'Universidad Nacional, Edificio 303 (NEA) - Bogotá',
    'Universidad Nacional de Colombia': 'Universidad Nacional, Edificio 303 (NEA) - Bogotá',
    'Hall entrada admin. Facultad de Artes, Edf. Gerardo Arango S.J': 'Pontificia Universidad Javeriana - Bogotá',
    'Edificio Gerardo Arango S. J': 'Pontificia Universidad Javeriana - Bogotá',
}


def sede_b(x):
    if x['sede'] == 'Universidad Jorge Tadeo Lozano':
        return ('Universidad Jorge Tadeo Lozano, Módulo 4 - Bogotá' if 'Módulo 4' in (x['sala'] or '')
                else 'Universidad Jorge Tadeo Lozano, Ed. Biblioteca - Bogotá')
    if x['sede'] == 'Pontificia Universidad Javeriana' and 'Ático' in (x['sala'] or ''):
        return 'Pontificia Universidad Javeriana - Bogotá'
    return SEDE_B[x['sede']]


def hora_b(h):
    m = re.match(r'(\d+):(\d+)\s*([ap])', h.replace(' ', ''))
    hh = int(m[1]) % 12 + (12 if m[3] == 'p' else 0)
    return f'{hh:02d}:{m[2]}'


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).strip()


def titulos_de_la_ficha(n):
    """Otra regla: el último trozo de texto antes de cada «(Dir», en el HTML crudo."""
    s = io.open(f'{SRC}/fichas/{n}.html', encoding='utf-8').read()
    s = s[s.find('2D'):s.find('Más Películas')]
    out = []
    for trozo in s.split('(Dir')[:-1]:
        t = [html.unescape(x).strip() for x in re.split(r'<[^>]+>', trozo)]
        t = [x for x in t if x.strip(' \xa0')]
        out.append(t[-1].strip(' \xa0'))
    return out


def main():
    sp = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/{FID}-crudo.py')
    cr = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(cr)
    build = json.load(io.open(f'{ST}/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{ST}/{FID}-venues-geo.json', encoding='utf-8'))
    af = json.load(io.open(f'{ST}/{FID}-afirmaciones.json', encoding='utf-8'))['afirmaciones']
    items = json.load(io.open(f'{ST}/{FID}-ojos.json', encoding='utf-8'))['items']
    films = build['films']
    fallos = []

    # 1 · las láminas (lectura B) ↔ el build
    lam = collections.Counter()
    for x in items:
        if not x.get('sede'):
            continue          # el taller ASIFA: sin sede en la lámina (va en `_fuera` del crudo)
        lam[(x['dia'], hora_b(x['hora']), sede_b(x))] += 1
    for a in af:
        if a['casilla'] == 'time':
            k = (a['ancla']['dia'], a['ancla']['hora'], a['ancla']['sede'])
            lam[k] -= 1
            lam[(k[0], a['valor'], k[2])] += 1
    if any(n < 0 for n in lam.values()):
        fallos.append(f'una afirmación apunta a un ancla que las láminas no tienen: {[k for k, n in lam.items() if n < 0]}')
    lam = +lam
    pub = collections.Counter((f['day'], f['time'], f['venue']) for f in films)
    fallos += [f'en la lámina y NO en el build: {k} ×{n - pub[k]}' for k, n in lam.items() if pub[k] < n]
    fallos += [f'en el build y en NINGUNA lámina: {k} ×{n - lam[k]}' for k, n in pub.items() if lam[k] < n]

    # 2 · la agenda de la Cinemateca ↔ el build
    ag = cr.agenda()
    nodos = {x[8]: x for x in cr.FUNCIONES if x[8]}
    idx = {(f['day'], f['time'], f['venue']): f for f in films}
    n_ag = 0
    for (n, d, h), sala in sorted(ag.items()):
        if n not in nodos:
            continue
        n_ag += 1
        sede = nodos[n][4]
        f = idx.get((d, h, f'{sede} - Bogotá'))
        if not f:
            fallos.append(f'en la agenda y NO en el build: ficha {n} {d} {h}')
            continue
        if sede == cr.CIN and f.get('sala') != sala:
            fallos.append(f'{d} {h} {f["title"]}: sala {f.get("sala")!r}, la agenda dice {sala!r}')
        if sede == cr.CIN and n != 3590:
            if f.get('ticket_url') != cr.tuboleta(n) or f.get('is_free') is not False:
                fallos.append(f'{d} {h} {f["title"]}: TuBoleta {f.get("ticket_url")!r} / is_free {f.get("is_free")!r}')
        elif f.get('is_free') is not True:
            fallos.append(f'{d} {h} {f["title"]}: debería ser entrada libre')
    # el Reel / WIP Day: «Evento para aliados» → por invitación
    for f in films:
        if f['title'].startswith('Reel') and not f.get('by_invitation'):
            fallos.append(f'{f["title"]}: «Evento para aliados» debería salir por invitación')

    # 3 · las fichas ↔ las obras de cada programa del build
    prog = {}
    for d, h, tit, sec, sede, sala, acc, edad, n, x in cr.FUNCIONES:
        if x.get('programa'):
            prog.setdefault(x['programa'], set()).add((d, h, f'{sede} - Bogotá'))
    ficha_de = {'Surgentes - Animage': 3591, 'Surgentes - Con extremos': 3592, 'Surgentes - Miyu': 3596,
                'Conexión - Foco Pez Dorado': 3593, 'Costa a costa': 3616,
                'Costa a costa - Lo mejor de Annecy 2026': 3692,
                'Con acento nacional - Procesos de formación - Programa 1': 3594,
                'Con acento nacional - Procesos de formación - Programa 2': 3617,
                'Con acento nacional - Profesional - Programa 1': 3595,
                'Con acento nacional - Profesional - Programa 2': 3618}
    n_obras = 0
    for p, anclas in prog.items():
        esperado = [plano(t) for t in titulos_de_la_ficha(ficha_de[p])]
        for k in anclas:
            k = next((a for a in idx if a[0] == k[0] and a[2] == k[2] and (a[1] == k[1] or
                      any(z['casilla'] == 'time' and z['ancla']['dia'] == k[0] and z['ancla']['hora'] == k[1] and z['valor'] == a[1] for z in af))), None)
            f = idx.get(k)
            if not f:
                continue
            got = [plano(o.get('title')) for o in f.get('film_list') or []]
            if got != esperado:
                fallos.append(f'{k} {p}: obras {got} ≠ ficha {esperado}')
            n_obras += len(got)

    # 4 · pines
    for v, x in build['venues'].items():
        g = geo.get(v.replace(' - Bogotá', '')) or {}
        if x.get('lat') is None:
            fallos.append(f'sede {v!r} sin pin')
        elif g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano')
    if fallos:
        sys.exit('✗ el build no coincide con las fuentes:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {sum(lam.values())} ítems de las láminas = las {len(films)} funciones del build (con la hora afirmada de Fontanar) · '
          f'{n_ag} funciones de la agenda con su sala y su acceso · {n_obras} obras en el orden de su ficha · '
          f'{len(build["venues"])} sedes con pin a mano')


if __name__ == '__main__':
    main()
