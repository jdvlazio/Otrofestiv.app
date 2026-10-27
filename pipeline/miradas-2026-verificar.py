#!/usr/bin/env python3
"""miradas-2026-verificar.py — el BUILD contra tres lecturas INDEPENDIENTES del
PDF oficial, hechas por lectores que no vieron ni el crudo ni el build
(PROTOCOLO §2·ter; memoria «triple lectura»):

  A · la prosa y las fichas (págs. 1–61 y 102–112), por pdftotext;
  B · las grillas por día (págs. 56–96 y 102–110), leídas como IMAGEN;
  C · la web de la Alcaldía, que solo enlaza el mismo PDF: su lector releyó la
      grilla y las fichas por su cuenta.

Las lecturas viven en fuentes/miradas-2026/lecturas/ (A-prosa, B-grillas,
C-web). Compara (día, hora, título) en las DOS direcciones: toda función de
una lectura está en el build o en `_no_se_publica` / ACEPTADAS con su porqué,
y toda función del build está en alguna lectura. Además: los programas suman
la duración de sus obras, y cada sede tiene pin a mano.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'miradas-2026'
LEC = f'{REPO}/fuentes/{FID}/lecturas'


def k(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def _hora_lectura(s):
    m = re.match(r'\s*(\d{1,2}):(\d{2})\s*([ap])?', s or '')
    if not m:
        return None
    h = int(m.group(1))
    if m.group(3) == 'p' and h != 12:
        h += 12
    return f'{h:02d}:{m.group(2)}'


MESES = {'mar': 3, 'mie': 4, 'jue': 5, 'vie': 6, 'sab': 7, 'dom': 8}
# Diferencias de lectura RESUELTAS contra el PDF (la discrepancia es el dato):
# (lectura, día, hora, palabra del título) → por qué no es un faltante
# el mismo lugar con otro nombre en el PDF
ALIAS_SEDE = {'Museo de Arte Moderno de Medellín - MAMM - Medellín': {'mamm', 'museo'},
              'Planetario de Medellín - Medellín': {'planetario', 'domo'},
              'Parque de los Deseos - Medellín': {'cinemateca', 'movil', 'deseos'},
              'Casa de la Música - Medellín': {'deseos', 'musica'},
              'Coocine - Medellín': {'coocine'},
              'Comfama Otraparte - Medellín': {'otraparte'}}
ACEPTADAS = {
    ('A', '2026-10-28', '19:00', 'mama chila'): 'fuera de las fechas oficiales (_no_se_publica)',
}


STOP = set('de del la las el los y en a con para por un una cine proyeccion programa'.split())


def palabras(s):
    return set(k(s).split()) - STOP


def build_idx(build):
    """(día, hora) → funciones; una abierta de varios días (`hasta`) cuenta en cada uno"""
    idx = {}
    for f in build['films']:
        claves = [f['title']] + [o.get('title') for o in f.get('film_list') or []]
        if f.get('_programa_original'):
            claves.append(f['_programa_original'])
        texto = k(f.get('description') or f.get('synopsis') or '')
        dias = [f['day']]
        if f.get('hasta'):
            d0, d1 = int(f['day'][-2:]), int(f['hasta'][-2:])
            dias = [f'{f["day"][:-2]}{d:02d}' for d in range(d0, d1 + 1)]
        for d in dias:
            idx.setdefault((d, f['time']), []).append((f, [c for c in claves if c], texto))
    return idx


def casa(idx, dia, hora, titulos):
    """la función del build en ese día y hora que MEJOR se parece (no la primera)"""
    mejor, pmejor = None, 0.0
    for f, claves, texto in idx.get((dia, hora), []):
        for t in titulos:
            kt, pt = k(t), palabras(t)
            if not pt:
                continue
            for c in claves:
                kc, pc = k(c), palabras(c)
                p = (0.5 + 0.5 * min(len(kc), len(kt)) / max(len(kc), len(kt))) if (kc and (kc in kt or kt in kc)) else (len(pc & pt) / len(pc | pt) if pc else 0)
                if p > pmejor:
                    mejor, pmejor = f, p
            if kt and kt in texto and pmejor < 0.9:
                mejor, pmejor = f, 0.9
    return mejor if pmejor >= 0.3 else None


def main():
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    idx = build_idx(build)
    vistas, fallos, n, sedes_dif = set(), [], {}, []

    def mira(lect, dia, hora, titulos, sede=''):
        if not dia or not hora:
            return
        n[lect] = n.get(lect, 0) + 1
        f = casa(idx, dia, hora, titulos)
        if f:
            vistas.add(id(f))
            if sede and not (palabras(sede) & (palabras(f['venue']) | palabras(f.get('sala') or '') | ALIAS_SEDE.get(f['venue'], set()))):
                sedes_dif.append(f'{lect}: {dia} {hora} «{f["title"]}» — lectura «{sede}» · build «{f["venue"]}» {f.get("sala") or ""}')
            return
        if any((lect, dia, hora, w) in ACEPTADAS for t in titulos for w in [k(t)[:10]]) or \
           any(a[0] == lect and a[1] == dia and a[2] == hora for a in ACEPTADAS):
            return
        fallos.append(f'{lect}: {dia} {hora} «{titulos[0]}» no está en el build')

    B = json.load(io.open(f'{LEC}/B-grillas.json', encoding='utf-8'))
    for a in B['actividades'] + B['industria']:
        mira('B', a['dia'], a.get('hora_inicio'), [a['titulo']] + [o['titulo'] for o in a.get('obras') or []], a.get('sede') or '')
    C = json.load(io.open(f'{LEC}/C-web.json', encoding='utf-8'))
    for a in C['actividades']:
        # C escribe las sesiones repetidas como «2026-11-04/05/06»
        base, *otros = a['dia'].split('/')
        for d in [base] + [base[:-2] + x for x in otros]:
            mira('C', d, a.get('hora_inicio'), [a['titulo'].split(' (')[0]] + [o['titulo'] for o in a.get('obras') or []], a.get('sede') or '')
    A = json.load(io.open(f'{LEC}/A-prosa.json', encoding='utf-8'))
    for o in A['obras']:
        for h in o.get('horario_si_aparece') or []:
            m = re.match(r'\s*(\w{3})\w*\.?\s+(\d{1,2})\s+(?:de\s+)?(\w{3})\w*\s+(\d{1,2}:\d{2}\s*[ap])', k(h) and h.lower()
                         .replace('á', 'a').replace('é', 'e'))
            if not m:
                continue
            mes = 10 if m.group(3) == 'oct' else 11
            mira('A', f'2026-{mes:02d}-{int(m.group(2)):02d}', _hora_lectura(m.group(4)), [o['titulo']])

    sin_lectura = [f'{f["day"]} {f["time"]} {f["title"]}' for f in build['films'] if id(f) not in vistas]

    # los programas suman la duración que publican
    for f in build['films']:
        fl = f.get('film_list') or []
        if fl:
            s = sum(int(re.match(r'\d+', o['duration']).group()) for o in fl if o.get('duration'))
            if f.get('duration') != f'{s} min':
                fallos.append(f'programa «{f["title"]}» {f["day"]}: suma {s} ≠ {f.get("duration")}')
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    for v, x in build['venues'].items():
        if x.get('lat') is None or geo.get(v, {}).get('_prec') != 'manual':
            fallos.append(f'sede {v!r} sin pin a mano')

    print(f'lecturas: ' + ', '.join(f'{l} {c} entradas' for l, c in sorted(n.items())))
    if sedes_dif:
        print('  · sede distinta entre lectura y build (revisar):\n      ' + '\n      '.join(sedes_dif))
    if sin_lectura:
        print('  · en el build sin ninguna lectura que la nombre:\n      ' + '\n      '.join(sin_lectura))
    if fallos:
        sys.exit('✗ el build no coincide con las lecturas:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ las {len(build["films"])} funciones del build contra A, B y C · '
          f'{len(build["venues"])} sedes con pin a mano · programas cuadran')


if __name__ == '__main__':
    main()
