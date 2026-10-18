#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preonboarding.py — ¿el catálogo de un festival está COMPLETO? (18 oct 2026)

POR QUÉ. Juan lo pidió dos veces (28 sep y 10 oct): en cuanto un festival publica
su selección, el pre-onboarding es COMPLETO —catálogo + enriquecido + afiches +
sinopsis—, para que con la parrilla solo falte montar días y horas. En FICICA se
hizo el catálogo con TMDB y nunca se bajaron los afiches; dos días antes de abrir
salió en cascada. La regla estaba en una memoria; acá es un chequeo que falla.

QUÉ MIDE. Por cada festivals/staging/<fid>-catalogo.json de un festival que
TODAVÍA NO SALIÓ (lo publicado lo vigila [afiche-cobertura]): las obras sin afiche
ni su porqué (`sin_afiche` de <fid>-correcciones.json), en el enriquecido que
declara su plan o el del catálogo. Sin enriquecido = todas.

LA DEUDA. pipeline/preonboarding-deuda.json congela lo de hoy por festival y solo
puede bajar; un festival que no está ahí tiene tolerancia CERO.

    python3 pipeline/preonboarding.py            # informe
    python3 pipeline/preonboarding.py --bajar    # baja la deuda medida
"""
import glob, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEUDA = os.path.join(REPO, 'pipeline', 'preonboarding-deuda.json')


def plano(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


def _publicadas(fid, raiz):
    """{título: tiene afiche} de lo publicado, o None si el festival no salió."""
    pub = os.path.join(raiz, 'festivals', f'{fid}.json')
    if not os.path.exists(pub):
        return None
    d = json.load(open(pub, encoding='utf-8'))
    out = {}
    for f in d.get('films') or []:
        for o in [f] + (f.get('film_list') or []):
            k = plano(o.get('title'))
            out[k] = out.get(k, False) or bool(o.get('poster'))
    return out


def _con_afiche(fid, raiz):
    plan = os.path.join(raiz, 'pipeline', f'{fid}.plan.json')
    rutas = []
    if os.path.exists(plan):
        e = (json.load(open(plan, encoding='utf-8')).get('festival') or {}).get('enriquecido')
        if e:
            rutas.append(os.path.join(raiz, e))
    rutas.append(os.path.join(raiz, 'festivals', 'staging', f'{fid}-catalogo-enriquecido.json'))
    for r in rutas:
        if os.path.exists(r):
            L = json.load(open(r, encoding='utf-8')).get('obras') or []
            return {plano(x.get('titulo') or x.get('title')) for x in L if x.get('poster') or x.get('poster_path')}
    return None                      # sin enriquecido


def medir(raiz=REPO):
    """{fid: [títulos sin afiche ni porqué]}"""
    out = {}
    for p in sorted(glob.glob(os.path.join(raiz, 'festivals', 'staging', '*-catalogo.json'))):
        fid = os.path.basename(p)[:-len('-catalogo.json')]
        obras = json.load(open(p, encoding='utf-8')).get('obras') or []
        if not os.path.exists(os.path.join(raiz, 'pipeline', f'{fid}.plan.json')):
            continue                 # no es un festival (p. ej. mamut-2026-programa, sidecar)
        if _publicadas(fid, raiz) is not None:
            # YA SALIÓ: lo publicado lo vigila [afiche-cobertura] (acepta el rastro
            # de que se buscó y no se halló). Este guardián es para el PRE-onboarding
            continue
        con = _con_afiche(fid, raiz) or set()
        # el afiche RECORTADO que el catálogo declara (FICIDI: de la lámina) cuenta
        # solo si el archivo está EN EL REPO: en fuentes/ (gitignored) se pierde —
        # 64 de FICIDI apuntaban ahí y ya no existían (18 oct 2026)
        con |= {plano(o.get('titulo')) for o in obras
                if (o.get('afiche') or o.get('poster')) and str(o.get('afiche') or o.get('poster')).startswith(('assets/', '/assets/'))
                and os.path.exists(os.path.join(raiz, str(o.get('afiche') or o.get('poster')).lstrip('/')))}
        cp = os.path.join(raiz, 'festivals', 'staging', f'{fid}-correcciones.json')
        exp = {plano(t) for t in (json.load(open(cp, encoding='utf-8')).get('sin_afiche') or {})} if os.path.exists(cp) else set()
        out[fid] = [o.get('titulo') for o in obras
                    if (con is None or plano(o.get('titulo')) not in con) and plano(o.get('titulo')) not in exp]
    return out


def comparar(medido, deuda):
    """→ (sobre, bajo): festivales por encima de su deuda / que pueden bajarla."""
    sobre = {f: len(v) for f, v in medido.items() if len(v) > deuda.get(f, 0)}
    bajo = {f: len(v) for f, v in medido.items() if len(v) < deuda.get(f, 0)}
    return sobre, bajo


if __name__ == '__main__':
    m = medir()
    d = json.load(open(DEUDA, encoding='utf-8'))['deuda'] if os.path.exists(DEUDA) else {}
    if '--bajar' in sys.argv:
        nueva = {f: min(len(v), d.get(f, len(v))) for f, v in m.items() if v}
        json.dump({'_nota': 'obras de catálogo sin afiche ni porqué, por festival; solo baja (preonboarding.py)',
                   'deuda': nueva}, open(DEUDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'✓ deuda: {sum(nueva.values())} obras en {len(nueva)} festivales')
    else:
        for f, v in m.items():
            print(f'{f:24} {len(v):3} sin afiche ni porqué (deuda {d.get(f, 0)})' + (f' — p. ej. {v[:3]}' if v else ''))
