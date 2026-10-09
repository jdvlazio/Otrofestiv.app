#!/usr/bin/env python3
"""ficcali-2026-verificar.py — el build de FICCALI contra el festival, por OTRO camino.

El crudo lee las tarjetas del contenido de la página (WP 14870) partiendo el
HTML por el loop de Elementor. Este paso NO reusa ese parser: lee

  · la API REST `programacion-ficcali` (título, fecha por su etiqueta
    `dd-mm-aaaa`, sede por su categoría) — no pasa por el HTML;
  · la página PÚBLICA renderizada (fuentes/ficcali-2026/programacion-ficcali-2026.html)
    con html.parser, solo para la HORA de cada tarjeta, buscada por su id.

y exige, en los dos sentidos:
  · cada tarjeta del 16 al 25 con hora es UNA función del build, con su día,
    su hora y su sede (salvo las declaradas fuera en el crudo);
  · cada función del build sale de una tarjeta;
  · toda sede del build tiene pin verificado a mano (o es en línea).
"""
import html
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'ficcali-2026'
DIR = f'{REPO}/fuentes/ficcali-2026'
DESDE, HASTA = '2026-10-16', '2026-10-25'


class Tarjetas(HTMLParser):
    """Texto de cada e-loop-item, por id, contando la profundidad de los div."""
    def __init__(self):
        super().__init__()
        self.pila, self.txt = [], {}

    def handle_starttag(self, tag, attrs):
        if tag != 'div':
            return
        cls = dict(attrs).get('class') or ''
        m = re.search(r'\be-loop-item-(\d+)\b', cls)
        self.pila.append(m.group(1) if m else None)

    def handle_endtag(self, tag):
        if tag == 'div' and self.pila:
            self.pila.pop()

    def handle_data(self, data):
        ids = [x for x in self.pila if x]
        if ids and data.strip():
            self.txt.setdefault(ids[-1], []).append(data.strip())


HORA = re.compile(r'^(\d{1,2}):(\d{2})')
MARCA = re.compile(r'([ap])m|(?<![a-z])m(?![a-z])')


def hora(lineas):
    """La hora de arranque: el primer «h:mm» de una línea que empieza con él, y
    la PRIMERA marca a.m./p.m./m. que aparezca después en esa línea (en un rango
    «3:00 a 7:00 p.m.» el inicio no la lleva). Otra regla que la del crudo, a
    propósito: si las dos coinciden, la hora está bien leída."""
    for x in lineas:
        t = x.lower().replace('.', '').replace(' ', '')
        m = HORA.match(t)
        if not m:
            continue
        mk = MARCA.search(t[m.end():])
        if not mk:
            continue
        ap = mk.group(1) or 'p'                    # «12:00 m» = mediodía
        h = int(m.group(1)) % 12 + (12 if ap == 'p' else 0)
        # un inicio que con la marca del final quedaría después de él es de mañana
        fin = re.search(r'[a–-](\d{1,2}):(\d{2})', t[m.end():])
        if fin and ap == 'p':
            hf = int(fin.group(1)) % 12 + 12
            if h > hf:
                h -= 12
        return f'{h:02d}:{m.group(2)}'
    return None


def main():
    rest = json.load(io.open(f'{DIR}/programacion-ficcali.json', encoding='utf-8'))
    pag = Tarjetas()
    pag.feed(io.open(f'{DIR}/programacion-ficcali-2026.html', encoding='utf-8').read())
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    crudo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-crudo.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    plan = json.load(io.open(f'{REPO}/pipeline/{FID}.plan.json', encoding='utf-8'))['festival']
    cats = json.load(io.open(f'{DIR}/categorias.json', encoding='utf-8'))

    por_tarjeta = {f['_src']['tarjeta']: f for f in crudo['funciones']}
    # las que el crudo declara FUERA por su id (hoy: sede nueva sin pin, 8 oct)
    declaradas = {int(n) for n in re.findall(r'tarjeta (\d+) ·', ' '.join(crudo.get('_fuera') or []))}
    fallos, vistas = [], set()
    for r in rest:
        tag = next((t for t in r.get('class_list', []) if re.fullmatch(r'tag-\d{2}-\d{2}-\d{4}', t)), None)
        if not tag:
            fallos.append(f'tarjeta {r["id"]}: sin etiqueta de fecha en la API')
            continue
        d, m, a = tag[4:].split('-')
        dia = f'{a}-{m}-{d}'
        if not (DESDE <= dia <= HASTA):
            continue
        h = hora(pag.txt.get(str(r['id']), []))
        if not h:
            if r['id'] in por_tarjeta:
                fallos.append(f'tarjeta {r["id"]} «{html.unescape(r["title"]["rendered"])[:40]}»: sin hora en la página y publicada')
            continue
        f = por_tarjeta.get(r['id'])
        if not f and r['id'] in declaradas:
            continue
        if not f:
            fallos.append(f'en la API y NO en el crudo: {dia} {h} «{html.unescape(r["title"]["rendered"])[:50]}»')
            continue
        vistas.add(r['id'])
        if f['dia'] != dia:
            fallos.append(f'tarjeta {r["id"]}: día {f["dia"]} en el crudo, {dia} en la API')
        if f['hora'] != h:
            fallos.append(f'tarjeta {r["id"]}: hora {f["hora"]} en el crudo, {h} en la página')
        cat_sede = next((cats.get(str(c), [''])[0] for c in r.get('categories', [])), '')
        if cat_sede and cat_sede.strip().lower() != f['sede_cruda'].strip().lower():
            fallos.append(f'tarjeta {r["id"]}: sede «{f["sede_cruda"]}» en la tarjeta, «{cat_sede}» en su categoría')
    for t, f in por_tarjeta.items():
        if t not in vistas:
            fallos.append(f'en el crudo y en NINGUNA tarjeta del 16–25 de la API: {f["dia"]} {f["hora"]} «{f["titulo"][:50]}»')
    # el build es el crudo ensamblado: misma cuenta, mismas franjas
    bk = sorted((x['day'], x['time']) for x in build['films'])
    ck = sorted((f['dia'], f['hora']) for f in crudo['funciones'])
    if bk != ck:
        fallos.append(f'el build ({len(bk)}) no tiene las mismas franjas que el crudo ({len(ck)})')
    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {plan["city"]}', ''), {})
        if x.get('lat') is None and g.get('_prec') != 'en_linea':
            fallos.append(f'sede {v!r} sin pin')
        elif x.get('lat') is not None and g.get('_prec') not in ('manual', 'aproximado'):
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')
    if fallos:
        sys.exit('✗ el build no coincide con el festival:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ las {len(vistas)} tarjetas del 16–25 (API + página) están en el build con su día, hora y sede, '
          f'y el build no publica ninguna más · {len(build["venues"])} sedes con pin')


if __name__ == '__main__':
    main()
