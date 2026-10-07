#!/usr/bin/env python3
"""ficcali-2026-programacion.py — la programación de FICCALI 18, tarjeta por tarjeta.

LA FUENTE es la página «Programación» de ficcali.com (WP 14870), que el sitio
arma con un loop de Elementor: una TARJETA por función o actividad (tipo
`programacion-ficcali`). Cada tarjeta, leída en orden:

    Sábado / 17 / octubre / CINEMATECA LA TERTULIA / Luis Tercero / 6:00 p.m.
    Colombia Q&A (dir.) | 110 min / Proyecciones

día de la semana, día, mes, SEDE, TÍTULO, HORA (o un rango, en las
actividades), una línea de meta («país [Q&A …] | duración», a veces invertida,
o un texto) y la CATEGORÍA (Proyecciones, Académico, Conexiones, Cine sin
límites). La fecha también viene en la etiqueta de la tarjeta (`tag-17-10-2026`)
y la sede en su categoría de WordPress: se cruzan las dos lecturas.

La API REST trae el mismo tipo, pero sin sus campos (ACF vacío): el dato está
en el HTML de la página.

Escribe festivals/staging/ficcali-2026-programacion.json (una entrada por
tarjeta, sin interpretar títulos ni sedes: eso lo hace el crudo).

    python3 pipeline/ficcali-2026-programacion.py          # usa la copia guardada
    python3 pipeline/ficcali-2026-programacion.py --bajar  # baja la página vigente
"""
import html
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

DIR = f'{REPO}/fuentes/ficcali-2026'
FUENTE = f'{DIR}/programacion.json'
URL = 'https://ficcali.com/programacion-ficcali-2026/'
DESTINO = f'{REPO}/festivals/staging/ficcali-2026-programacion.json'
MESES = {'octubre': 10, 'noviembre': 11, 'septiembre': 9}
DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
_H = r'(\d{1,2})(?::(\d{2}))?\s*(a\.?\s*m\.?|p\.?\s*m\.?|m\.)?'
RANGO = re.compile(rf'^{_H}\s*(?:a|–|-)\s*{_H}\s*\|?$', re.I)
SOLA = re.compile(rf'^{_H}$', re.I)


def bajar():
    r = subprocess.run(['curl', '-s', 'https://ficcali.com/wp-json/wp/v2/pages/14870'],
                       capture_output=True, text=True).stdout
    d = json.loads(r, strict=False)
    if not d.get('content'):
        sys.exit('✗ la página de programación no devolvió contenido')
    json.dump(d, io.open(FUENTE, 'w', encoding='utf-8'), ensure_ascii=False)


def _ampm(x):
    x = (x or '').lower().replace(' ', '').replace('.', '')
    return 'm' if x == 'm' else x[:1] if x else ''


def _hhmm(h, m, ap):
    h, m = int(h), int(m or 0)
    if ap == 'p' and h < 12:
        h += 12
    if ap == 'a' and h == 12:
        h = 0
    return f'{h:02d}:{m:02d}'


def horas(t):
    """«6:00 p.m» → ('18:00', None) · «6:00 a 8:00 p.m.» → ('18:00', '20:00').
    En un rango, el inicio sin a.m./p.m. toma el del final si cabe antes de él
    («3:00 a 7:00 p.m.» = 15:00); «12:00 m.» es el mediodía."""
    t = t.strip().rstrip('|').strip()
    m = RANGO.match(t)
    if m:
        h1, m1, a1, h2, m2, a2 = m.groups()
        a1, a2 = _ampm(a1), _ampm(a2)
        if a2 == 'm':
            a2 = 'p'                                     # 12:00 m. = mediodía
        fin = _hhmm(h2, m2, a2)
        if not a1:
            a1 = a2 if _hhmm(h1, m1, a2) <= fin else 'a'
        ini = _hhmm(h1, m1, 'p' if a1 == 'm' else a1)
        # «10:00 a.m. a 12:00 a.m.» (Foro local de proyectos): un rango no
        # termina antes de empezar; un «12 a.m.» que lo haría es el mediodía
        if fin <= ini and int(h2) == 12:
            fin = _hhmm(h2, m2, 'p')
        return ini, fin
    m = SOLA.match(t)
    if m and m.group(3):
        a = _ampm(m.group(3))
        return _hhmm(m.group(1), m.group(2), 'p' if a == 'm' else a), None
    return None, None


def meta(t):
    """«Colombia Q&A (dir.) | 110 min» · «106 min | Cuba» · «Cali, Colombia» · texto."""
    partes = [p.strip() for p in t.replace('\t', ' ').split('|')]
    dur, resto = None, []
    for p in partes:
        m = re.fullmatch(r'(\d{2,3})\s*min', p)
        if m:
            dur = int(m.group(1))
        elif p:
            resto.append(p)
    txt = ' | '.join(resto)
    qa = re.search(r'Q&A.*$', txt)
    pais = txt[:qa.start()].strip() if qa else txt
    return {'pais': pais or None, 'qa': qa.group().strip() if qa else None, 'duracion_min': dur}


def main():
    if '--bajar' in sys.argv or not os.path.exists(FUENTE):
        bajar()
    d = json.load(io.open(FUENTE, encoding='utf-8'))
    c = re.sub(r'<style.*?</style>', '', d['content']['rendered'], flags=re.S)
    partes = re.split(r'(?=<div[^>]*class="[^"]*\be-loop-item\b)', c)[1:]
    out, fallos = [], []
    for p in partes:
        cls = re.search(r'class="([^"]*)"', p).group(1)
        pid = re.search(r'e-loop-item-(\d+)', cls).group(1)
        tag = re.search(r'tag-(\d{2})-(\d{2})-(\d{4})', cls)
        cat = re.search(r'category-([a-z0-9-]+)', cls)
        L = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', p)).split('\n') if x.strip()]
        if len(L) < 7 or L[0].lower() not in DIAS or L[2].lower() not in MESES:
            fallos.append(f'tarjeta {pid}: no tiene la forma esperada — {L[:8]}')
            continue
        dia = f'2026-{MESES[L[2].lower()]:02d}-{int(L[1]):02d}'
        if not tag or f'{tag.group(3)}-{tag.group(2)}-{tag.group(1)}' != dia:
            fallos.append(f'tarjeta {pid}: el día impreso ({dia}) no es el de su etiqueta ({tag and tag.group()})')
        sede, titulo = L[3], L[4]
        ini, fin = horas(L[5])
        if ini:
            resto = L[6:]
        else:
            resto = L[5:]                       # sin hora: la línea 5 ya es la meta
        categoria = resto[-1] if resto else None
        linea_meta = resto[0] if len(resto) > 1 else ''
        r = {'id': int(pid), 'dia': dia, 'hora': ini, 'hasta': fin, 'sede': sede,
             'sede_slug': cat.group(1) if cat else None, 'titulo': titulo,
             'categoria': categoria, 'meta_impresa': linea_meta or None, **meta(linea_meta),
             'hora_impresa': L[5] if ini else None}
        out.append({k: v for k, v in r.items() if v is not None})
    if fallos:
        sys.exit('✗ la programación no cuadra:\n  · ' + '\n  · '.join(fallos))
    # COBERTURA: toda tarjeta del loop terminó en una entrada
    n_loop = len(set(re.findall(r'e-loop-item-(\d+)', c)))
    if n_loop != len(out):
        sys.exit(f'✗ {n_loop} tarjetas en la página y {len(out)} leídas')
    sin_hora = [f'{x["dia"]} {x["titulo"]}' for x in out if not x.get('hora')]
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('ficcali.com, Programación 2026 (WP 14870)', url=URL,
                                  metodo='una tarjeta del loop de Elementor por función; fecha cruzada con su etiqueta'),
        '_modificada': d.get('modified_gmt'), 'sin_hora': sin_hora,
        'tarjetas': sorted(out, key=lambda x: (x['dia'], x.get('hora') or '', x['titulo']))},
        ensure_ascii=False, indent=1))
    print(f'✓ {len(out)} tarjetas · {len(sin_hora)} sin hora · {len({x["sede"] for x in out})} sedes '
          f'→ {os.path.relpath(DESTINO, REPO)}')
    for x in sin_hora:
        print(f'   sin hora · {x}')


if __name__ == '__main__':
    main()
