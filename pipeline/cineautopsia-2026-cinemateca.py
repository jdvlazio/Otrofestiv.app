# -*- coding: utf-8 -*-
"""Fichas de la Cinemateca de Bogotá → programas de CineAutopsia.

La agenda de la Cinemateca publica lo que el festival no: obras de cada
programa, SEDE, DÍA y HORA. Es la misma fuente que resolvió las salas de
FICDEH, y aquí trae catálogo y parrilla a la vez.

Cada ficha es server-rendered y rígida: tras el bloque de metadatos vienen las
obras en pares de líneas —título, y luego «(Dir. Nombre, año) País. NN min.»—
y al final la sede con «Mes DD H:MM AM/PM».
"""
import json, re, io, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/cineautopsia-2026'
NODOS = ['2823', '2841', '2845', '2846', '2848', '2849', '2850']

MESES = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,
         'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}


def texto(html):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t)
    t = t.replace('&nbsp;', ' ').replace('&amp;', '&')
    return [x.strip() for x in t.split('\n') if x.strip()]


def parse(nodo, html):
    L = texto(html)
    d = {'nodo': nodo, '_src': f'https://cinematecadebogota.gov.co/node/peliculas/{nodo}'}
    # El título del programa es la primera línea que se repite en <title>
    d['programa'] = re.sub(r'\s*\|\s*Cinemateca\s*$', '', L[0])
    # El festival viene justo después de «Festivales y Muestras»
    for i, x in enumerate(L):
        if x == 'Festivales y Muestras' and i + 1 < len(L):
            d['festival'] = L[i + 1]; break
    # Bloque de metadatos: año, duración total, países
    for x in L:
        if re.fullmatch(r'(19|20)\d\d', x): d.setdefault('anio', int(x))
        elif re.fullmatch(r'\d+\s*min\.?', x): d.setdefault('duracion_min', int(re.search(r'\d+', x).group()))
    for k, et in (('clasificacion','Clasificación:'), ('idioma','Idioma:'),
                  ('subtitulos','Subtítulos:'), ('formato','Formato:')):
        if et in L: d[k] = L[L.index(et) + 1]
    # OBRAS: la línea siguiente empieza por «(Dir. …»
    obras = []
    for i, x in enumerate(L[:-1]):
        m = re.match(r'^\(Dir\.\s*(.+?),\s*((?:19|20)\d\d)\)\s*(.*?)\.\s*(\d+)\s*min', L[i + 1])
        if m and len(x) < 90 and not x.endswith(':'):
            obras.append({'titulo': x, 'director': m.group(1).strip(),
                          'anio': int(m.group(2)), 'pais': m.group(3).strip(),
                          'duracion_min': int(m.group(4))})
    d['obras'] = obras
    # SEDE + FECHA: «Cinemateca de Bogotá Centro» / «Agosto 22 4:30 PM»
    for i, x in enumerate(L):
        m = re.match(r'^([A-Za-zÁÉÍÓÚáéíóú]+)\s+(\d{1,2})\s+(\d{1,2}):(\d{2})\s*([AP])\.?M\.?$', x)
        if m:
            mes = MESES.get(m.group(1).lower())
            h = int(m.group(3)) % 12 + (12 if m.group(5).upper() == 'P' else 0)
            d['sede'] = L[i - 1] if i else None
            d['dia'] = f'2026-{mes:02d}-{int(m.group(2)):02d}' if mes else None
            d['hora'] = f'{h:02d}:{m.group(4)}'
            break
    # sinopsis: el párrafo largo anterior a la primera obra
    largos = [x for x in L if len(x) > 110 and 'Dir.' not in x]
    if largos: d['sinopsis'] = largos[0]
    # póster del programa
    m = re.search(r'(?:src|data-src)="(/sites/default/files/\d{4}-\d{2}/[^"]+\.(?:png|jpg|jpeg|webp))"', html, re.I)
    if m: d['poster'] = 'https://cinematecadebogota.gov.co' + m.group(1)
    return d


def bajar(n):
    """Ficha cacheada en fuentes/ (fuera del repo publicado). Sin caché, se baja."""
    p = f'{CACHE}/ca-{n}.html'
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        return io.open(p, encoding='utf-8', errors='replace').read()
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA,
                    f'https://cinematecadebogota.gov.co/node/peliculas/{n}?sede=11',
                    '-o', p], check=True)
    time.sleep(0.6)
    return io.open(p, encoding='utf-8', errors='replace').read()


nodos = sys.argv[1:] or NODOS
out = [parse(n, bajar(n)) for n in nodos]
os.makedirs(ST, exist_ok=True)
salida = f'{ST}/cineautopsia-2026-cinemateca.json'
json.dump({'_provenance': provenance(
               'cinematecadebogota.gov.co/node/peliculas/<nodo>?sede=11',
               metodo='fichas server-rendered de la agenda de la Cinemateca',
               nota='la sede publica obras, dia, hora y sala que el festival no publica'),
           '_programas': len(out),
           '_obras': sum(len(d['obras']) for d in out),
           'programas': out},
          io.open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'── {salida}\n')

for d in out:
    print(f"══ [{d['nodo']}] {d['programa']}")
    print(f"   {d.get('festival','?')}")
    print(f"   {d.get('dia','?')} {d.get('hora','?')} · {d.get('sede','?')} · {d.get('duracion_min','?')} min · {d.get('clasificacion','?')}")
    print(f"   obras: {len(d['obras'])} · póster: {'sí' if d.get('poster') else '—'}")
    for o in d['obras']:
        print(f"      {o['duracion_min']:3} min · {o['titulo'][:40]:42} {o['director'][:26]:28} {o['pais']}")
    print()
print(f"── total programas {len(out)} · obras {sum(len(d['obras']) for d in out)}")
