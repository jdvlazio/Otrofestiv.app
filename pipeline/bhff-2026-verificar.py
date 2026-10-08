#!/usr/bin/env python3
"""bhff-2026-verificar.py — el build de Bogotá Horror contra el festival, por OTRO camino.

El crudo convierte el arreglo `PROGRAMACION` del HTML a JSON con expresiones
regulares. Este paso NO reusa esa conversión: le pasa el literal a Node, que lo
EVALÚA como el JavaScript que es (lo mismo que hace el navegador del público),
y del resultado exige, en los dos sentidos:

  · cada evento de la parrilla es UNA función del build con su día, su hora
    (leída del par hora/periodo con otra regla: «7:30» + «PM»), su sede y su
    título; salvo las declaradas fuera en el crudo (`_fuera`);
  · cada corto de una franja, en el orden de la parrilla, está en la lista de
    obras de esa función;
  · cada función del build sale de la parrilla (o de un taller declarado);
  · toda sede del build tiene pin verificado a mano.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = f'{REPO}/fuentes/bhff-2026/programacion.html'
BUILD = f'{REPO}/festivals/staging/bhff-2026-build.json'
CRUDO = f'{REPO}/festivals/staging/bhff-2026-crudo.json'
SALA = {'Sala Capital': ('Cinemateca de Bogotá - Bogotá', 'Sala Capital'),
        'Sala 3': ('Cinemateca de Bogotá - Bogotá', 'Sala 3'),
        'Casa 32': ('Casa 32 - Bogotá', None), 'CEFE Chapinero': ('Centro Felicidad Chapinero - Bogotá', None),
        'Co - Laboratorio': ('Co.Laboratorio - Bogotá', None)}


def plano(s):
    s = unicodedata.normalize('NFD', html_sin(s).lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def html_sin(s):
    return re.sub(r'<[^>]+>', '', s or '')


def parrilla():
    c = io.open(HTML, encoding='utf-8').read()
    m = re.search(r'const PROGRAMACION = (\[.*?\n\]);', c, re.S)
    if not m:
        sys.exit('✗ no está el arreglo PROGRAMACION en la página')
    r = subprocess.run(['node', '-e', f'const P = {m.group(1)};\nprocess.stdout.write(JSON.stringify(P))'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit('✗ Node no pudo evaluar la parrilla: ' + r.stderr[:300])
    return json.loads(r.stdout)


def hora_de_la_parrilla(h, p):
    hh, mm = h.split(':')
    hh = int(hh) % 12 + (12 if p.strip().lower() in ('pm', 'p.m.', 'p. m.') else 0)
    return f'{hh:02d}:{mm}'


def main():
    P = parrilla()
    B = json.load(io.open(BUILD, encoding='utf-8'))
    fuera = json.load(io.open(CRUDO, encoding='utf-8'))['_fuera']
    films = B['films']
    usadas, fallos, n = set(), [], 0
    for d in P:
        dia = f'2026-10-{int(d["dia"]):02d}'
        for e in d['eventos']:
            n += 1
            t = e['titulo'].split('·', 1)[-1].strip() if e['titulo'].startswith('Franja') else e['titulo']
            if any(x.startswith(dia) and e['titulo'] in x for x in fuera):
                continue
            if e['sala'] not in SALA:
                fallos.append(f'{dia} «{t}»: sala {e["sala"]!r} sin equivalencia y no declarada fuera')
                continue
            sede, sala = SALA[e['sala']]
            h = hora_de_la_parrilla(e['hora'], e['periodo'])
            c = [i for i, f in enumerate(films) if f['day'] == dia and f['time'] == h and f['venue'] == sede
                 and (sala is None or f.get('sala') == sala) and plano(f['title']).startswith(plano(t))]
            if len(c) != 1:
                fallos.append(f'{dia} {h} {e["sala"]} «{t}»: {len(c)} funciones en el build')
                continue
            usadas.add(c[0])
            f = films[c[0]]
            cortos = [plano(re.match(r'<b>(.*?)</b>', x).group(1)) for x in e.get('cortos') or []]
            if cortos and [plano(x['title']) for x in f.get('film_list') or []] != cortos:
                fallos.append(f'{dia} «{t}»: los cortos del build no son los de la parrilla')
    talleres = [i for i, f in enumerate(films) if f.get('event_kind') == 'taller']
    for i, f in enumerate(films):
        if i not in usadas and i not in talleres:
            fallos.append(f'en el build y no en la parrilla: {f["day"]} {f["time"]} «{f["title"]}»')
    for k, v in B['venues'].items():
        if v.get('_prec') != 'manual' or not v.get('lat'):
            fallos.append(f'sede sin pin a mano: {k}')
    if fallos:
        sys.exit('✗ el build no coincide con el festival:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {n} eventos de la parrilla (evaluada por Node) · {len(usadas)} funciones · '
          f'{len(talleres)} talleres · {len(B["venues"])} sedes con pin')


if __name__ == '__main__':
    main()
