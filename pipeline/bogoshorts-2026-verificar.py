#!/usr/bin/env python3
"""bogoshorts-2026-verificar.py — el crudo contra lecturas INDEPENDIENTES de la grilla.

Triple lectura (docs: PROTOCOLO §2·ter):
  A  el crudo: pdftotext -bbox + bandas de espacio (bogoshorts-2026-crudo.py)
  B  festivals/staging/bogoshorts-2026-lectura-b.json — a ojo sobre la imagen
     de la grilla a 300 ppp, por celdas (otro lector, sin ver el código ni el texto)
  C  festivals/staging/bogoshorts-2026-lectura-c.json — a ojo, por columnas de día
y un CONTRASTE: los días/horas/sedes que los pies de IG publicaron por programa.

Compara TOKENS —día, hora 24h, espacio (palabra distintiva), código—, no registros
parseados. La discrepancia es el dato: se lista, no se vota. Sale con error si A
tiene algo que ni B ni C vieron, o si B y C coinciden en algo que A no tiene.
"""
import io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ESP = [('fontanar', 'FONTANAR'), ('sala capital', 'CAPITAL'), ('sala 2', 'SALA2'), ('sala 3', 'SALA3'),
       ('imagen', 'IMAGEN'), ('lounge', 'LOUNGE'), ('plazoleta', 'LOUNGE'), ('parque', 'PARQUE'),
       ('sótano', 'SOTANO'), ('alianza', 'ALIANZA'), ('ático', 'ATICO'), ('cefe', 'CEFE'),
       ('delia', 'DELIA'), ('media torta', 'TORTA'), ('gaitán antigua', 'GAITAN'), ('sala gaitán', 'GAITAN'),
       ('jorge', 'JEG'), ('fiestas', 'FIESTAS'), ('monkeydo', 'FIESTAS'), ('retina', 'RETINA'), ('city', 'CITYU')]


def esp(s):
    s = s.lower()
    return next((v for k, v in ESP if k in s), s)


def cod(t):
    t = re.sub(r'\s*\d{1,2}:\d\d - \d{1,2}:\d\d [ap]\.m\.', '', t)   # «IMAGINATÓN 2:00 - 8:00 p.m.»
    t = t.replace('ES -PER', 'ES-PER')
    m = re.match(r"^([A-Z0-9]+(?:[-/][A-Z0-9]+)*)", t)
    return m[1] if m and re.search(r'[A-Z]-|/', m[1]) else re.sub(r'[^a-záéíóúñ0-9]', '', t.lower())[:14]


def toks_crudo():
    d = json.load(io.open(f'{ST}/bogoshorts-2026-crudo.json', encoding='utf-8'))
    out = set()
    for f in d['funciones']:
        if 'catalogo2026' in f['_src']['url']:
            continue                                  # no es celda de la grilla (Entrega clave IMAGINATÓN, del catálogo)
        import datetime as _dt
        dia, fin = f['dia'], f.get('hasta') or f['dia']
        while dia < fin:        # la VR va en un tramo (`hasta`): se abre día por día para comparar
            dia = (_dt.date.fromisoformat(dia) + _dt.timedelta(1)).isoformat()
            out.add((dia, f['hora'], esp(f['sede'] + ' ' + f['sala']), cod(f['texto_grilla'])))
        out.add((f['dia'], f['hora'], esp(f['sede'] + ' ' + f['sala']), cod(f['texto_grilla'])))
    return out, d


def toks_lectura(n):
    d = json.load(io.open(f'{ST}/bogoshorts-2026-lectura-{n}.json', encoding='utf-8'))
    out = set()
    for c in d['celdas']:
        e = esp(c['espacio'])
        if e == 'FIESTAS' and c['texto'] == 'Noche Sagitario':
            pass                                      # la única fiesta con lugar (IG 23 nov)
        elif e in ('CITYU', 'SOTANO', 'RETINA', 'FIESTAS') or c['texto'].startswith('Franja Encuentros'):
            continue                                  # los descartes declarados del crudo
        h = c.get('hora') or ''
        # VR del mar 8: la grilla da 11:00 (nota de festivos) y así se compara; se publica 14:00 por el catálogo del
        # 18 nov (pág. 12) y las fichas web — bogoshorts-2026-afirmaciones.json
        out.add((c['dia'], h, e, cod(c['texto'])))
    return out


def main():
    a, crudo = toks_crudo()
    b, c = toks_lectura('b'), toks_lectura('c')
    solo_a = sorted(a - b - c)
    bc_no_a = sorted((b & c) - a)
    print(f'A {len(a)} · B {len(b)} · C {len(c)} · A∩B∩C {len(a & b & c)}')
    for nom, x in (('solo B', sorted(b - a - c)), ('solo C', sorted(c - a - b)),
                   ('A y B, no C', sorted((a & b) - c)), ('A y C, no B', sorted((a & c) - b))):
        for t in x:
            print(f'  · {nom}: {t}')
    # contraste con IG: cada (día, hora, espacio) que un pie publicó para un código
    IG = {'PAC-DOC': [('2026-12-06', '18:00', 'ATICO'), ('2026-12-08', '17:00', 'CAPITAL')],
          'PAC-FIC': [('2026-12-02', '19:30', 'CAPITAL'), ('2026-12-05', '18:00', 'ATICO')],
          'PAC-EXP': [('2026-12-04', '18:00', 'ATICO'), ('2026-12-06', '17:00', 'CAPITAL')],
          'ES-PER': [('2026-12-03', '17:30', 'CEFE'), ('2026-12-05', '18:30', 'SALA2')],
          'F3-ALIENS': [('2026-12-05', '17:00', 'TORTA')],
          'FES-LADRA': [('2026-12-04', '13:30', 'SALA2'), ('2026-12-07', '13:30', 'ALIANZA')]}
    vistos = {(f['dia'], f['hora'], esp(f['sede'] + ' ' + f['sala']), f.get('codigo')) for f in crudo['funciones']}
    for k, fs in IG.items():
        for x in fs:
            if x + (k,) not in vistos:
                print(f'  ⚠ IG publicó {k} {x} y la grilla del 23 oct no lo trae ahí (la grilla es más nueva)')
    # los números tienen que cuadrar (PROTOCOLO §«Los números tienen que cuadrar»):
    # la suma de los cortos del catálogo contra los minutos de la grilla. Se LISTA,
    # no frena: la grilla redondea y algunos programas suman presentación o charla.
    vistos_cod = {}
    for f in crudo['funciones']:
        if f.get('codigo') not in (None, 'CVR', 'BFM-IV') and f.get('obras'):
            vistos_cod.setdefault(f['codigo'], (sum(o.get('duracion_min') or 0 for o in f['obras']), f.get('duracion_min')))
    raros = [(k, s_, g) for k, (s_, g) in sorted(vistos_cod.items()) if not g or abs(s_ - g) > max(3, 0.05 * g)]
    print(f'duración: {len(vistos_cod) - len(raros)}/{len(vistos_cod)} programas cuadran (±3 min) con la grilla')
    for k, s_, g in raros:
        print(f'  ⚠ {k}: los cortos suman {s_} min, la grilla dice {g}')
    if solo_a or bc_no_a:
        sys.exit('✗ ' + '\n✗ '.join([f'solo A (nadie más lo vio): {t}' for t in solo_a] +
                                     [f'B y C lo ven, A no: {t}' for t in bc_no_a]))
    print('✓ todo lo del crudo lo vio al menos otra lectura, y nada que B y C vean le falta')


if __name__ == '__main__':
    main()
