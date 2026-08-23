# -*- coding: utf-8 -*-
"""Staging → `festivals/staging/qaff-2026-build.json`. NO escribe en festivals/.

HISTORIA DEL ARCHIVO, porque explica su forma: nació como publicador propio
(`qaff-2026-publicar.py`, staging → festivals/ directo) y el 23 ago 2026 se
degradó a paso de BUILD. El motivo no fue el guardián: fue que ese mismo día
re-correrlo BORRÓ las 55 banderas que se habían arreglado a mano sobre el
publicado. Un publicador por festival es un sitio sin gate anti-pérdida donde
las correcciones no sobreviven. Ahora `festivals/qaff-2026.json` lo escribe
SOLO pipeline/publicar.py, que compara cobertura contra producción y aborta
antes de perder un dato — más limpio, normaliza (NFC/year) y contrato.

Aquí queda únicamente lo QAFF-específico, que es curaduría de datos:

  · SOLO QUIBDÓ (Juan, 23 ago): fuera las 14 funciones de Bogotá. Cuesta 7
    títulos que no se proyectan en Quibdó —Iniciación en la Octava Dimensión,
    LAUNDRY (Uhlanjululo), Of Mud and Blood, The Travelers, Wrong Generation
    y los dos Diálogo Improbable, que se llevan su sección—. El dato sigue en
    la fuente (qaff-2026-programacion-raw.json): omisión decidida, no perdida.
  · TÍTULOS (Juan, 23 ago): el original manda en `title`, el inglés a
    `title_en` — como los otros nueve festivales. La frontera entre «mismo
    título mal escrito» y «traducción de verdad» es comparar sin tildes,
    mayúsculas NI puntuación (sin lo último, «Amazonas: Cocinas…» se copiaba
    a title_en como si fuera inglés).
  · flags DERIVADO del país (lib.banderas), porque el ensamblador de QAFF no
    lo hace y el arreglo de las 55 vivía fuera del pipeline.
  · `short` de sede sin la ciudad pegada (regla de ensamblar.py:251).
  · poda de `_src`: quedan boom_event_id y tmdb_id; los stills de wixstatic
    son material de trabajo y se quedan en el staging.

El resto —limpio de claves privadas, NFC, year→int, contrato, gate
anti-pérdida— es del publicador genérico y NO se repite aquí.

    python3 pipeline/qaff-2026-build.py && python3 pipeline/publicar.py qaff-2026
"""
import json, os, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f'{REPO}/festivals/staging/qaff-2026.json'
OUT = f'{REPO}/festivals/staging/qaff-2026-build.json'

SRC_UTIL = ('boom_event_id', 'tmdb_id')

# El inglés venía pegado al original entre corchetes.
EN_LIMPIO = {'POSESAS [Possessed]': 'Possessed'}

# Dos obras que la regla general no podía ver porque nunca tuvieron title_orig
# (nadie leyó su afiche). Aparecieron cruzando el lbSlug verificado contra el
# título; confirmadas en TMDB y Letterboxd.
A_MANO = {
    'Mi viche todo el dia': ('Mi viche todo el día', 'My Daily Viche'),
    'Soñé su nombre':       ('Soñé su nombre',       'I Dreamed His Name'),
}


def _clave(s):
    """Título reducido a letras y dígitos: sin tildes, mayúsculas ni puntuación."""
    t = ''.join(c for c in unicodedata.normalize('NFKD', s or '')
                if not unicodedata.combining(c)).lower()
    return ''.join(c for c in t if c.isalnum())


def main():
    d = json.load(open(SRC, encoding='utf-8'))

    films = [dict(f) for f in d['films']]
    # NFC ANTES de las tablas por clave: «Soñé su nombre» llegaba en NFD
    # (n+tilde combinante), se ve idéntico y no casa con nada.
    for f in films:
        for k, v in list(f.items()):
            if isinstance(v, str):
                f[k] = unicodedata.normalize('NFC', v)

    # ── solo Quibdó ─────────────────────────────────────────────────────────
    bog = {k for k, v in d['venues'].items() if v.get('city') != 'Quibdó'}
    films = [f for f in films if f['venue'] not in bog]
    venues = {k: dict(v) for k, v in d['venues'].items() if k not in bog}
    usadas = {f.get('section') for f in films}
    sections = {k: v for k, v in d['sections'].items() if k in usadas}

    # ── títulos ─────────────────────────────────────────────────────────────
    for f in films:
        if f['title'] in A_MANO:
            f['title'], f['title_en'] = A_MANO[f['title']]
        orig = f.pop('title_orig', None)
        if not orig or orig == f['title']:
            continue
        if _clave(orig) == _clave(f['title']):
            f['title'] = orig                      # solo ortografía: no hay inglés
        else:
            f['title_en'] = EN_LIMPIO.get(f['title'], f['title'])
            f['title'] = orig

    # ── derivados y podas ───────────────────────────────────────────────────
    for f in films:
        if not f.get('flags'):
            b = lib.banderas(f.get('country') or '')
            if b:
                f['flags'] = b
        s = f.get('_src')
        if isinstance(s, dict):
            f['_src'] = {k: s[k] for k in SRC_UTIL if s.get(k)} \
                        or {'origen': 'calendario Boom del festival'}
    for k, v in venues.items():
        if v.get('short') == k and ' - ' in k:
            v['short'] = k.rsplit(' - ', 1)[0]

    out = {k: v for k, v in d.items() if k not in ('films', 'venues', 'sections')}
    out.update({'sections': sections, 'venues': venues, 'films': films})
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              separators=(',', ':'))
    print(f'✓ build: {len(films)} funciones · {len(venues)} sede(s) · '
          f'{len(sections)} secciones · title_en: '
          f'{sum(1 for f in films if f.get("title_en"))}')
    print('  ahora: python3 pipeline/publicar.py qaff-2026')


if __name__ == '__main__':
    main()
