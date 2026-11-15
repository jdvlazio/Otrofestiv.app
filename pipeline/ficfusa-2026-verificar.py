#!/usr/bin/env python3
"""ficfusa-2026-verificar.py — el build contra la transcripción, en los dos sentidos.

Lee el build (festivals/staging/ficfusa-2026-build.json) por su propio camino, sin
pasar por el crudo, y lo cruza con ficfusa-2026-programacion-oficial.json:
  · cada entrada de la fuente con sede tiene UNA función en el build con su día,
    hora y sede (y sus obras, si las trae);
  · cada función del build sale de una entrada de la fuente;
  · cada sede del build tiene pin en el sidecar geo.
Sale con error si algo no cuadra.
"""
import io
import json
import os
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn' and c.isalnum())


def main():
    prog = json.load(io.open(f'{ST}/ficfusa-2026-programacion-oficial.json', encoding='utf-8'))['funciones']
    build = json.load(io.open(f'{ST}/ficfusa-2026-build.json', encoding='utf-8'))
    films = build['films'] if isinstance(build, dict) else build
    geo = json.load(io.open(f'{ST}/ficfusa-2026-venues-geo.json', encoding='utf-8'))
    sedes = json.load(io.open(f'{REPO}/pipeline/ficfusa-2026.plan.json', encoding='utf-8'))['festival']['sedes']
    fallos = []
    usadas = set()
    # Encima de la transcripción, las afirmaciones (IG más nuevo): existe:{…}
    # agrega una función; venue/time/day mueven la de su ancla.
    afs = json.load(io.open(f'{ST}/ficfusa-2026-afirmaciones.json', encoding='utf-8'))['afirmaciones']
    for e in prog:
        if e['sede'] != 'Por definir':
            e['venue'] = sedes[e['sede']][0]
    for a in afs:
        k = (a['ancla']['dia'], a['ancla']['hora'], plano(a['ancla']['sede']))
        if a['casilla'] == 'existe' and isinstance(a['valor'], dict):
            v = a['valor']
            prog.append({'fecha': v['day'], 'hora': v['time'], 'sede': v['venue'], 'venue': v['venue'], 'titulo': v['title']})
        elif a['casilla'] in ('venue', 'time', 'day'):
            campo = {'venue': 'venue', 'time': 'hora', 'day': 'fecha'}[a['casilla']]
            for e in prog:
                if e['sede'] != 'Por definir' and (e['fecha'], e['hora'], plano(e['venue'])) == k:
                    e[campo] = a['valor']
    for e in prog:
        if e['sede'] == 'Por definir':
            continue
        cands = [i for i, f in enumerate(films)
                 if f.get('day') == e['fecha'] and f.get('time') == e['hora'] and plano(e['venue']) == plano(f.get('venue'))]
        if len(cands) != 1:
            fallos.append(f"{e['fecha']} {e['hora']} {e['sede']} «{e['titulo']}»: {len(cands)} funciones en el build")
            continue
        i = cands[0]
        usadas.add(i)
        f = films[i]
        lista = f.get('film_list') or []
        en_build = {plano(x.get('title') if isinstance(x, dict) else x) for x in lista} | {plano(f.get('title'))}
        for o in e.get('obras') or []:
            if plano(o) not in en_build:
                fallos.append(f"{e['fecha']} {e['hora']}: falta «{o}» en el build")
    for i, f in enumerate(films):
        if i not in usadas:
            fallos.append(f"función del build sin entrada en la fuente: {f.get('day')} {f.get('time')} «{f.get('title')}»")
        if f.get('venue') not in geo:
            fallos.append(f"sede sin pin: {f.get('venue')}")
    if fallos:
        sys.exit('✗ el build no cuadra con la fuente:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {len(films)} funciones = {len(usadas)} entradas de la fuente, cada sede con pin')


if __name__ == '__main__':
    main()
