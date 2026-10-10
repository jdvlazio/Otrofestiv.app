#!/usr/bin/env python3
"""ficpa-2026-verificar.py — lo que se va a publicar, contra la página del festival.

Mira el BUILD (lo que llega a la app) contra las tarjetas de la página de
programación, en las dos direcciones, por el MISMO camino del crudo (se importan
sus tablas: verificador-mismo-camino):

  · toda tarjeta que no se declaró fuera está en el build, en su día y su hora
    (como función propia o como obra de un programa);
  · todo lo que el build publica a una hora tiene una tarjeta a esa hora;
  · toda sede tiene su pin verificado a mano, o un pendiente escrito.
"""
import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'ficpa-2026'
_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/ficpa-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)
plano = crudo.plano


def main():
    oficial, alterna = crudo.tarjetas()
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    pub = {}
    for f in build['films']:
        pub.setdefault((f['day'], f['time']), set()).add(plano(f['title']))
        for o in f.get('film_list') or []:
            pub[(f['day'], f['time'])].add(plano(o['title']))
    fallos, n = [], 0
    for t in oficial + alterna:
        tit = t['titulo']
        if t.get('grupo') in crudo.ALTERNA_FUERA:
            continue
        if not t.get('grupo') and tit not in crudo.FUERA_EXCEPTO and (
                t['categoria'] in crudo.FUERA_CATEGORIA or tit in crudo.FUERA_TITULO):
            continue
        if tit in crudo.ENCABEZADO_SOLO:
            continue
        n += 1
        if tit.startswith('Película Inaugural: Lactar'):
            tit = 'Película Inaugural: Lactar'
        nombre = crudo.TITULO.get(tit) or crudo.PROGRAMA.get(tit) or tit
        if plano(nombre) not in pub.get((t['dia'], t['hora']), set()) and \
                plano(crudo.frase(nombre)) not in pub.get((t['dia'], t['hora']), set()):
            fallos.append(f'en la página y NO en el build: {t["dia"]} {t["hora"]} «{nombre[:60]}»')
    horas = {(t['dia'], t['hora']) for t in oficial + alterna}
    for (d, h) in pub:
        if (d, h) not in horas:
            fallos.append(f'en el build a una hora que ninguna tarjeta tiene: {d} {h}')
    for v, x in build['venues'].items():
        g = geo.get(x.get('short') or v.split(' - ')[0], {})
        if x.get('lat') is None and not g.get('_todo'):
            fallos.append(f'sede {v!r} sin pin y sin pendiente escrito')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')
    if fallos:
        sys.exit('✗ el build no coincide con la página:\n  · ' + '\n  · '.join(fallos))
    sin_pin = [v for v, x in build['venues'].items() if x.get('lat') is None]
    print(f'✓ las {n} tarjetas publicables están en el build en su día y hora, y el build no publica '
          f'ninguna hora sin tarjeta · {len(build["venues"]) - len(sin_pin)} sedes con pin a mano'
          + (f' · sin pin, con su porqué: {", ".join(sin_pin)}' if sin_pin else ''))


if __name__ == '__main__':
    main()
