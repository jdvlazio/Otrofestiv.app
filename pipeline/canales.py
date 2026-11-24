#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""canales.py: ¿sabemos por dónde comunica cada festival por montar? (24 nov 2026)

POR QUÉ. FECILI 11 estaba en el radar con una sola cuenta (Instagram, muda) y con
fechas de Festhome (4–7 dic). Publicó su programación en Facebook y empezó el 24
nov. La ventana de 7 días no servía: se contaba desde una fecha equivocada.

QUÉ EXIGE. Cada festival de `preonboarding` en ig-vigia-cuentas.json, desde 30 días
antes, tiene ficha en `canales` (mismo archivo):
  redes       {instagram, facebook, web…: URL}; null = se buscó y no tiene
  activo      cuál usa para comunicar (una llave de redes)
  ultimo_post fecha del último post suyo de esta edición
  fechas      {inicio, fin, fuente, publicado}: del propio festival; una ficha de
              convocatoria (Festhome, FilmFreeway) no confirma
  revisado    cuándo se miró
Con el tiempo se aprieta: a 30 días, una revisión; a 15, otra y con fechas
confirmadas; a 7, cada 2 días. A 7 días sin canal activo: DESECHAR (decide Juan).

    python3 pipeline/canales.py [--hoy AAAA-MM-DD]   # código 1 si algo falta
"""
import json
import os
import sys
from datetime import date, timedelta

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ig-vigia-cuentas.json')
NO_CONFIRMA = ('festhome', 'filmfreeway')
MUDO_D = 30
# (días que faltan, días máximos desde la última revisión)
ESCALONES = ((7, 2), (15, 8), (30, 15))


def faltas(cuentas, hoy, publicados=()):
    """[(id, días que faltan, [problemas])] de los festivales por montar a ≤30 días."""
    canales, out, vistos = cuentas.get('canales', {}), [], set()
    for p in sorted(cuentas.get('preonboarding', []), key=lambda x: x['inicio']):
        if p['id'] in vistos or p['id'] in publicados:
            continue
        vistos.add(p['id'])
        c = canales.get(p['id']) or {}
        ini = date.fromisoformat((c.get('fechas') or {}).get('inicio') or p['inicio'])
        n = (ini - hoy).days
        if n < 0 or n > 30:
            continue
        mal, redes = [], c.get('redes') or {}
        for r in ('instagram', 'facebook', 'web'):
            if r not in redes:
                mal.append(f'falta buscar su {r}')
        activo = bool(redes.get(c.get('activo')))
        if not activo:
            mal.append('sin canal activo')
        u = c.get('ultimo_post')
        mudo = not u or (hoy - date.fromisoformat(u)).days > MUDO_D
        if activo and mudo:
            mal.append(f'su canal no publica desde {u or "nunca"}')
        fu = (c.get('fechas') or {})
        if n <= 15 and (not fu.get('fuente') or any(x in fu['fuente'].lower() for x in NO_CONFIRMA)):
            mal.append('fechas sin confirmar por el propio festival')
        tope = next(t for d, t in ESCALONES if n <= d)
        rev = c.get('revisado')
        if not rev or hoy - date.fromisoformat(rev) > timedelta(days=tope):
            mal.append(f'revisado {rev or "nunca"} (máximo {tope} días)')
        if n <= 7 and (not activo or mudo):
            mal.append('DESECHAR: a 7 días sin canal activo (decide Juan)')
        if mal:
            out.append((p['id'], n, mal))
    return out


def fuera_de_fechas(cuentas, fid, festival):
    """Funciones del JSON de un festival fuera de las fechas oficiales de su ficha
    (afiche o anuncio). Regla de Juan, 8 oct 2026; la violó Vélez el 24 nov con una
    función previa del 30 nov y afiche 1–6 dic. Van fuera aunque el festival las anuncie."""
    fe = (cuentas.get('canales', {}).get(fid.replace('-', '')) or {}).get('fechas')
    if not fe:
        return []
    dias = {d for f in festival.get('films', []) for d in [f.get('day')] + [s.get('day') for s in f.get('screenings') or []]}
    dias |= {(festival.get('festivalStartStr') or '')[:10], (festival.get('festivalEndStr') or '')[:10]}
    return sorted(d for d in dias if d and not fe['inicio'] <= d <= fe['fin'])


def main():
    hoy = date.fromisoformat(sys.argv[sys.argv.index('--hoy') + 1]) if '--hoy' in sys.argv else date.today()
    import ig_vigia   # los que ya están en config los vigila ig_vigia.py
    pub = ig_vigia.festivales_config(open(ig_vigia.CONFIG, encoding='utf-8').read())
    f = faltas(json.load(open(RUTA, encoding='utf-8')), hoy, pub)
    for fid, n, mal in f:
        print(f'✗ {fid} (en {n} días): ' + ' · '.join(mal))
    if not f:
        print('✓ canales: todo festival por montar tiene canal activo y fechas confirmadas')
    return 1 if f else 0


if __name__ == '__main__':
    sys.exit(main())
