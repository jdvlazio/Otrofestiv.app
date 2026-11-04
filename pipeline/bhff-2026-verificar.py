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
  · toda sede del build tiene pin verificado a mano;
  · una función de «Cinematecas locales» (la parrilla no dice cuál) se espera
    en la sede que dice SU NODO de la agenda de la Cinemateca, leído aquí de
    fuentes/bhff-2026/cinemateca-node-*.html (no de la tabla del crudo).
"""
import glob
import html as htmlmod
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import funcion  # noqa: E402

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


def nodos_cinemateca():
    """[(título, día, hora, sede)] de las páginas de nodo guardadas de la Cinemateca."""
    out = []
    for fn in sorted(glob.glob(f'{REPO}/fuentes/bhff-2026/cinemateca-node-*.html')):
        t = io.open(fn, encoding='utf-8').read()
        t = re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S)
        t = re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', t)))
        m = re.search(r'<?(?:Inicio) (.+?) Función \w+, (\d+)/(\d+)/(\d{4}) - (\d\d:\d\d) .*?Sede Cinemateca de Bogotá (.+?) Cinemateca de Bogotá Carrera', t)
        if not m:
            sys.exit(f'✗ no leo la función en {os.path.basename(fn)}')
        out.append((m[1], f'{m[4]}-{m[3]}-{m[2]}', m[5], f'Cinemateca {m[6].strip()} - Bogotá'))
    return out


def hora_de_la_parrilla(h, p):
    hh, mm = h.split(':')
    hh = int(hh) % 12 + (12 if p.strip().lower() in ('pm', 'p.m.', 'p. m.') else 0)
    return f'{hh:02d}:{mm}'


def main():
    P = parrilla()
    B = json.load(io.open(BUILD, encoding='utf-8'))
    _crudo = json.load(io.open(CRUDO, encoding='utf-8'))
    fuera = _crudo['_fuera']
    # LO QUE ESPERA, POR EL MISMO CAMINO QUE EL BUILD (docs/FUNCION.md §5): la
    # lectura de la parrilla pasa por funcion.resolver con las afirmaciones del
    # festival. Una sala que la Cinemateca corrigió se espera corregida, sin
    # enseñarle la excepción a este verificador
    AFS = funcion.cargar('bhff-2026') or []
    _plan = json.load(io.open(f'{REPO}/pipeline/bhff-2026.plan.json', encoding='utf-8'))['festival']
    CTX = funcion.contexto(_crudo, _plan, funcion.ticketing_model_de('bhff-2026'))
    films = B['films']
    NODOS = nodos_cinemateca()
    usadas, fallos, n = set(), [], 0
    for d in P:
        dia = f'2026-10-{int(d["dia"]):02d}'
        for e in d['eventos']:
            n += 1
            t = e['titulo'].split('·', 1)[-1].strip() if e['titulo'].startswith('Franja') else e['titulo']
            if any(x.startswith(dia) and e['titulo'] in x for x in fuera):
                continue
            if e['sala'] == 'Cinematecas locales':
                h0 = hora_de_la_parrilla(e['hora'], e['periodo'])
                nd = [x for x in NODOS if x[1] == dia and x[2] == h0 and plano(t) in plano(x[0])]
                if len(nd) != 1:
                    fallos.append(f'{dia} «{t}»: Cinematecas locales con {len(nd)} nodos de la Cinemateca que la ubiquen')
                    continue
                sede, sala = nd[0][3], None
            elif e['sala'] not in SALA:
                fallos.append(f'{dia} «{t}»: sala {e["sala"]!r} sin equivalencia y no declarada fuera')
                continue
            else:
                sede, sala = SALA[e['sala']]
            h = hora_de_la_parrilla(e['hora'], e['periodo'])
            _ancla = (sede, dia, h)
            _esp = funcion.resolver([{'title': t, 'type': 'film', 'day': dia, 'time': h, 'venue': sede,
                                      'sala': sala, '_ancla': _ancla}],
                                    funcion.de_ancla(AFS, _ancla), CTX).funciones[0]
            h = _esp['time']
            sala = _esp.get('sala') if sala is not None else None
            c = [i for i, f in enumerate(films) if f['day'] == _esp['day'] and f['time'] == h and f['venue'] == sede
                 and (sala is None or f.get('sala') == sala) and plano(f['title']).startswith(plano(t))]
            if len(c) != 1:
                fallos.append(f'{dia} {h} {e["sala"]} «{t}»: {len(c)} funciones en el build')
                continue
            usadas.add(c[0])
            f = films[c[0]]
            cortos = [plano(re.match(r'<b>(.*?)</b>', x).group(1)) for x in e.get('cortos') or []]
            if cortos and [plano(x['title']) for x in f.get('film_list') or []] != cortos:
                fallos.append(f'{dia} «{t}»: los cortos del build no son los de la parrilla')
    # las funciones que agrega una afirmación `existe: {…}` (una sede que solo
    # publicó la sala, p. ej. Nico en Fontanar del Río): se esperan en el build,
    # una por afirmación, en su ancla y con su título (mismo patrón que Guatapé)
    for a in AFS:
        if a['casilla'] == 'existe' and isinstance(a['valor'], dict):
            v = a['valor']
            c = [i for i, f in enumerate(films) if (f['venue'], f['day'], f['time']) == (v['venue'], v['day'], v['time'])
                 and plano(f['title']) == plano(v['title'])]
            if len(c) != 1:
                fallos.append(f'{v["day"]} {v["time"]} «{v["title"]}» (afirmación existe): {len(c)} funciones en el build')
            usadas.update(c)
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
