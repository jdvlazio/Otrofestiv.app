#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficica-2026-crudo.py — la Programación General de FICICA 2026 → crudo.

LA FUENTE: https://ficica.cinealacalle.org/programacion-general.html, guardada en
fuentes/ficica-2026/programacion-general.html (15 oct 2026). La página es
Webflow y pinta la parrilla con JavaScript desde bloques
<script class="ficica-prog-datos"> con JSON: `programas` (nombre y sinopsis de
los 20 programas), `dias` y `actividades` (50: día, inicio, fin, categoría,
tipo, título o número de programa, sede, sala, acceso, nota, invitados).

LAS REGLAS:
  · solo lo ABIERTO al público (`acceso: libre`). Las 17 restringidas —colegios,
    laboratorios de proyectos seleccionados, talleres de convocatoria cerrada—
    van a `_fuera` con la nota del festival (regla de viabilidad de Juan).
  · la sección es la CATEGORÍA del festival, tal cual: Exhibiciones, Academia,
    Industria, Eventos especiales.
  · UN CINEFORO QUE EMPIEZA CON SU PROGRAMA (mismo día, hora y sede) es la
    conversación de esa función, no otra actividad: se pega a la exhibición como
    conversatorio y su hora de fin da la duración. Son 6.
  · LOS CORTOS DE CADA PROGRAMA (16 oct): la página Programas ya los lista; los
    lee ficica-2026-programas.py → festivals/staging/ficica-2026-programas.json.
    El programa se reconoce por su FUNCIÓN (día, hora, sede), no por el nombre.
    Cada corto toma su título del catálogo (la Selección Oficial, ya en frase y
    con ficha) por título, título alterno o —si la web lo da traducido— por su
    director; el que no está en la Selección (Retrospectiva, comunitarios, MINI)
    va con lo que da la web, el título en frase como propuesta (caja-sostenida).
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'ficica-2026'
URL = 'https://ficica.cinealacalle.org/programacion-general.html'
FUENTE = f'{REPO}/fuentes/{FID}/programacion-general.html'
DESTINO = f'{REPO}/festivals/staging/ficica-2026-crudo.json'
CAPTURA = '2026-10-15'

SECCION = {'exhibiciones': 'Exhibiciones', 'academia': 'Academia', 'industria': 'Industria',
           'especiales': 'Eventos especiales'}
# el `tipo` del festival → event_kind de la app (los del mapa de makeEventPoster)
KIND = {'Foro': 'foro', 'Charla': 'charla', 'Networking': 'encuentro', 'Masterclass': 'masterclass',
        'Programa inaugural': 'apertura', 'Programa de clausura': 'clausura', 'Cineforo': 'foro'}


def datos():
    s = io.open(FUENTE, encoding='utf-8').read()
    D = {'programas': {}, 'dias': [], 'actividades': []}
    for m in re.finditer(r'<script[^>]*class="[^"]*ficica-prog-datos[^"]*"[^>]*>(.*?)</script>', s, re.S):
        d = json.loads(m.group(1))
        D['programas'].update(d.get('programas') or {})
        D['dias'] = d.get('dias') or D['dias']
        D['actividades'] += d.get('actividades') or []
    if not D['actividades']:
        sys.exit(f'✗ {os.path.relpath(FUENTE, REPO)}: sin bloques ficica-prog-datos')
    return D


PROGRAMAS = f'{REPO}/festivals/staging/ficica-2026-programas.json'
CATALOGO = f'{REPO}/festivals/staging/ficica-2026-catalogo.json'


def plano(t):
    import unicodedata
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


def frase(t):
    t = t.lower()
    return re.sub(r'^(\W*)(\w)', lambda m: m.group(1) + m.group(2).upper(), t)


def cortos_por_funcion():
    """{(dia, hora, sede): [obra…]} desde el sidecar de la página Programas."""
    cat = json.load(io.open(CATALOGO, encoding='utf-8'))['obras']
    por_tit = {plano(o['titulo_tabla']): o for o in cat}
    por_dir = {}
    for o in cat:
        por_dir.setdefault(plano(o.get('director')), []).append(o)
    out = {}
    for p in json.load(io.open(PROGRAMAS, encoding='utf-8'))['programas']:
        obras = []
        for c in p['cortos']:
            o = por_tit.get(plano(c['titulo'])) or por_tit.get(plano(c.get('alterno')))
            if not o and c.get('director') and len(por_dir.get(plano(c['director']), [])) == 1:
                o = por_dir[plano(c['director'])][0]          # el título vino traducido
            if o:
                obras.append({k: v for k, v in {'titulo': o['titulo'], 'director': o.get('director'),
                                                  'pais': o.get('pais')}.items() if v})
            else:
                obras.append({k: v for k, v in {'titulo': frase(c['titulo']), 'titulo_tabla': c['titulo'],
                                                  'director': c.get('director'), 'pais': c.get('pais'),
                                                  'fuera_de_seleccion': True}.items() if v})
        for f in p['funciones']:
            out[tuple(f)] = obras
    return out


def mins(h):
    return int(h[:2]) * 60 + int(h[3:5])


def invitados(a):
    xs = a.get('invitadxs') or []
    # [nombre, rol]; a veces el nombre viene vacío y el rol dice quiénes son
    # («Con la participación de los seleccionados…»)
    return ' · '.join(f'{n} ({r})' if n and r else (n or r) for n, r in xs if n or r) or None


def main():
    D = datos()
    A = D['actividades']
    CORTOS = cortos_por_funcion()
    funciones, fuera = [], []
    # los cineforos que abren con su programa
    exhib = {(a['dia'], a['inicio'], a['sede']): a for a in A
             if a['categoria'] == 'exhibiciones' and a.get('acceso') == 'libre'}
    pegados = {id(a): exhib[(a['dia'], a['inicio'], a['sede'])] for a in A
               if a.get('tipo') == 'Cineforo' and (a['dia'], a['inicio'], a['sede']) in exhib}
    foro_de = {id(p): a for a in A if id(a) in pegados for p in [pegados[id(a)]]}
    for a in A:
        tit = a.get('titulo') or D['programas'].get(str(a.get('programa')), {}).get('nombre')
        if a.get('acceso') != 'libre':
            fuera.append(f'{a["dia"]} {a["inicio"]} {tit[:60]} ({a["sede"][:40]}): '
                         f'{(a.get("nota") or "acceso restringido").rstrip(".")}')
            continue
        if id(a) in pegados:
            continue
        r = {'dia': a['dia'], 'hora': a['inicio'], 'sede': a['sede'],
             **({'sala': a['sala']} if a.get('sala') else {}),
             'acceso': 'Entrada libre', 'titulo': tit, 'seccion': SECCION[a['categoria']],
             '_src': {'url': URL, 'date': CAPTURA, 'fila': a.get('fila')}}
        nota = (a.get('nota') or '').strip()
        if a['categoria'] == 'exhibiciones':
            prog = D['programas'].get(str(a.get('programa'))) or {}
            r['is_programa'] = True
            desc = (prog.get('sinopsis') or '').strip()
            foro = foro_de.get(id(a))
            if foro:
                # el festival da la hora de fin del BLOQUE (proyección + cineforo).
                # Sin `has_qa`: la app le sumaría 30 min estimados a una duración
                # que ya los trae. El cineforo se dice en la descripción
                if foro.get('fin'):
                    r['duracion_min'] = mins(foro['fin']) - mins(a['inicio'])
                if invitados(foro):
                    r['invitados'] = invitados(foro)
                r['_src']['cineforo'] = foro.get('fila')
                nota = ' '.join(x for x in (nota, 'Con cineforo.') if x)
            r['sinopsis'] = ' '.join(x for x in (desc, nota) if x) or None
        else:
            r.update({'tipo': 'evento', 'event_kind': KIND[a['tipo']]})
            if a.get('fin'):
                r['duracion_min'] = mins(a['fin']) - mins(a['inicio'])
            r['sinopsis'] = ' '.join(x for x in ((a.get('descripcion') or '').strip(), nota) if x) or None
            if invitados(a):
                r['invitados'] = invitados(a)
            if a['tipo'] == 'Programa inaugural':
                r['premiere'] = 'Inauguración'
        if CORTOS.get((a['dia'], a['inicio'], a['sede'])):
            r['obras'] = CORTOS[(a['dia'], a['inicio'], a['sede'])]
        funciones.append({k: v for k, v in r.items() if v not in (None, '')})
    n_libres = sum(1 for a in A if a.get('acceso') == 'libre')
    if len(funciones) + len(pegados) != n_libres or len(funciones) + len(pegados) + len(fuera) != len(A):
        sys.exit(f'✗ no cuadra: {len(A)} actividades, {len(funciones)} funciones, '
                 f'{len(pegados)} cineforos pegados, {len(fuera)} fuera')
    # COMILLAS RECTAS en el título ([title-normalization]): «Un tinto con…» → "Un tinto con…"
    for f in funciones:
        f['titulo'] = f['titulo'].translate(str.maketrans({'«': '"', '»': '"', '“': '"', '”': '"'}))
    # LA DURACIÓN QUE EL FESTIVAL NO DA: las exhibiciones, la inauguración y la
    # clausura no traen hora de fin. El plan la necesita; se estima con la misma
    # regla de Ficcali —el hueco hasta la siguiente función en la misma sede,
    # tope 90 min, 60 si es la última— y queda anotado de dónde salió
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and g['hora'] > f['hora'])
        f['duracion_min'] = min(sig[0] - mins(f['hora']), 90) if sig else 60
        f['_duracion_de'] = 'estimada: el hueco hasta la siguiente en la misma sede (tope 90, 60 si es la última)'
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('ficica.cinealacalle.org — Programación General 2026 (JSON embebido '
                                  'en la página)', url=URL,
                                  metodo='actividad por función; solo acceso libre; cineforo pegado a su programa'),
        '_fuera': fuera, 'funciones': funciones}, ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("is_programa"))} programas, '
          f'{len(pegados)} con su cineforo) · {len(fuera)} fuera → {os.path.relpath(DESTINO, REPO)}')
    for x in fuera:
        print('   fuera ·', x)


if __name__ == '__main__':
    main()
