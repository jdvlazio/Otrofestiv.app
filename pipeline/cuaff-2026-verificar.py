#!/usr/bin/env python3
"""cuaff-2026-verificar.py — 2.ª lectura del build de CUAFF 2026, por otro camino.

No pasa por el crudo ni por su tabla: lee las FUENTES crudas y busca en ellas
los TOKENS de cada función del build.
  · el pie del post de IG (fuentes/ig/<sc>/post.json): el día escrito
    («20 de noviembre»), la hora en 12 h («7:00 p. m.»), la sala;
  · la ficha de la Cinemateca (fuentes/cuaff-2026/cinemateca-<n>.html): el
    título (o su alias declarado), la duración y, en los programas, cada obra
    con su duración («26 min»).
Un token que no aparece en su fuente es una discrepancia: sale con código 1.
"""
import html, io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/cuaff-2026-build.json'
# títulos que el festival y la sala escriben distinto (declarado en cuaff-2026-crudo.py)
ALIAS_SALA = {'El Lejano Sur': 'El Ajeno sur', 'Still Free': 'Latam tour',
              'Morbo x Noches Aires': 'Morboxnoches Aires', 'Código cypher vol1': 'Codigo cypher vol1',
              'Sanber: vivencias de un bajo mundo': 'Sanber vivencias bajo un mundo',
              'Hip Hop, Comunidad y Graffiti': 'Hip Hop/comunidad y graffiti',
              'Uniendo plazas: Los padres del under': 'Uniendo plazas : Los padres del under'}
DIAS = {'2026-11-20': '20 de noviembre', '2026-11-21': '21 de noviembre', '2026-11-22': '22 de noviembre'}


def plano(s):
    s = unicodedata.normalize('NFD', html.unescape(s).lower())
    return re.sub(r'\s+', ' ', ''.join(c for c in s if not unicodedata.combining(c)))


def hora12(h):
    hh, mm = map(int, h.split(':'))
    return f'{(hh - 1) % 12 + 1}:{mm:02d} {"a" if hh < 12 else "p"}. m.'


def main():
    films = json.load(io.open(BUILD, encoding='utf-8'))['films']
    malas = 0
    for f in films:
        src = f['_src']
        pies = ' '.join(plano(json.load(io.open(f'{REPO}/fuentes/ig/{sc}/post.json', encoding='utf-8'))['pie'])
                        for sc in src['posts'])
        toks = [(DIAS[f['day']], pies, 'IG'), (plano(hora12(f['time'])), pies, 'IG')]
        if f.get('sala'):   # el taller de stop motion (Df8Q_qpjFpO) no publica sala
            toks.append((plano(f['sala']), pies, 'IG'))
        if src.get('ficha_sala'):
            n = src['ficha_sala'].rsplit('/', 1)[1]
            ficha = plano(io.open(f'{REPO}/fuentes/cuaff-2026/cinemateca-{n}.html', encoding='utf-8').read())
            t = ALIAS_SALA.get(f['title'], f['title'])
            toks.append((plano(t), ficha, f'sala {n}'))
            for o in f.get('film_list') or []:
                toks.append((plano(ALIAS_SALA.get(o['title'], o['title'])), ficha, f'sala {n}'))
                toks.append((o['duration'].replace(' min', ' min'), ficha, f'sala {n}'))
        for tok, txt, de in toks:
            if tok not in txt:
                malas += 1
                print(f'  ✗ {f["title"]}: «{tok}» no está en {de}')
    print(f'{"✓" if not malas else "✗"} {len(films)} funciones · {malas} discrepancia(s)')
    sys.exit(1 if malas else 0)


if __name__ == '__main__':
    main()
