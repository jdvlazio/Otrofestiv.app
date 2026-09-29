#!/usr/bin/env python3
"""popayan-2026-verificar.py — lo que se va a publicar, contra la página de programación.

Relee la página del festival por su cuenta —del HTML, con otro corte: busca
cada «<sede> / <hora>» en el texto plano entero, sin partir en renglones— y
exige, en los dos sentidos:
  · cada horario impreso está en el build con su día, hora y título, y el
    build no publica ninguna función que la página no traiga;
  · cada bloque del build lleva tantas obras como créditos «dirigido…» hay
    entre su horario y el siguiente en la página;
  · toda sede tiene pin verificado a mano.
"""
import html
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'popayan-2026'
CIUDAD = 'Popayán'
MESES_DIA = re.compile(r'(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+(\d{1,2})\s+de\s+octubre')
# En texto plano no hay dónde cortar la sede del título anterior: se anclan las
# sedes que imprime la página, y TODO « / <hora>» del texto tiene que ser una
# de ellas (una sede nueva no pasa en silencio).
SEDES_PAGINA = ('Teatro Bolívar', 'Auditorio Maya Facultad de Artes Unicauca')
HORARIO = re.compile(r'(' + '|'.join(map(re.escape, SEDES_PAGINA)) + r')\s*/\s*(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\.?', re.I)
CUALQUIER_HORA = re.compile(r'/\s*\d{1,2}(?::\d{2})?\s*[ap]\.?\s*m\b', re.I)


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    d = json.load(io.open(f'{REPO}/fuentes/{FID}/programacion2026.json', encoding='utf-8'))
    texto = html.unescape(re.sub(r'<[^>]+>', ' ', d['content']['rendered']))
    texto = re.sub(r'\s+', ' ', texto)
    # cortes: días y horarios, en orden de aparición
    marcas = sorted([(m.start(), 'dia', m) for m in MESES_DIA.finditer(texto)] +
                    [(m.start(), 'hor', m) for m in HORARIO.finditer(texto)], key=lambda x: x[0])
    if len(CUALQUIER_HORA.findall(texto)) != len(HORARIO.findall(texto)):
        sys.exit(f'✗ hay horarios en una sede que el verificador no conoce: '
                 f'{len(CUALQUIER_HORA.findall(texto))} «/ hora» y {len(HORARIO.findall(texto))} con sede conocida')
    pagina, dia = [], None
    for n, (pos, tipo, m) in enumerate(marcas):
        if tipo == 'dia':
            dia = f'2026-10-{int(m.group(2)):02d}'
            continue
        h = int(m.group(2)) % 12 + (12 if m.group(4).lower() == 'p' else 0)
        hora = f'{h:02d}:{m.group(3) or "00"}'
        fin = marcas[n + 1][0] if n + 1 < len(marcas) else len(texto)
        tramo = texto[m.end():fin]
        titulo = re.split(r'\s+Películas(?:\s+|$)', tramo.strip(), maxsplit=1)[0].rstrip('. ')
        pagina.append({'dia': dia, 'hora': hora, 'titulo': titulo,
                       'creditos': len(re.findall(r'dirigid[oa]s?\s*(?:y\s+producid[oa]s?\s*)?por', tramo, re.I))})
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    pub = {(f['day'], f['time'], plano(f['title'])): f for f in build['films']}
    pag = {}
    for p in pagina:
        k = (p['dia'], p['hora'], plano(p['titulo']))
        pag[k] = max(pag.get(k, 0), p['creditos'])      # el par repetido del miércoles
    fallos = []
    for k, n in pag.items():
        f = pub.get(k)
        if not f:
            fallos.append(f'en la página y NO en el build: {k}')
        elif len(f.get('film_list') or []) != n:
            fallos.append(f'{k}: {n} créditos en la página, {len(f.get("film_list") or [])} obras en el build')
    for k in pub:
        if k not in pag:
            fallos.append(f'en el build y NO en la página: {k}')
    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None or g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r} sin pin verificado a mano')
    if fallos:
        sys.exit('✗ el build no coincide con la página:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ los {len(pag)} horarios de la página están en el build con sus obras '
          f'({sum(pag.values())}) y el build no publica ninguno más · {len(build["venues"])} sedes con pin manual')


if __name__ == '__main__':
    main()
