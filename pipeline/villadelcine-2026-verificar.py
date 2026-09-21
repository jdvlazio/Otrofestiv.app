#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-verificar.py — la parrilla contra la página que la dibuja.

POR QUÉ EXISTE (19 sep 2026). Leí la retícula, la di por buena y Juan preguntó
si había revisado el PDF dos veces. No: había abierto 4 de 10 páginas. Al abrir
la quinta salió un error que estaba en TODOS los bloques —la hora de fin corrida
una fila— y que no se veía por ninguna parte, porque el inicio sí caía bien y
una función de 105 minutos en vez de 120 parece perfectamente normal.

Este paso comprueba lo que un ojo no alcanza a revisar 53 veces:

  1. LAS DIEZ PÁGINAS se parsean y ninguna queda vacía.
  2. NINGÚN TEXTO SE PIERDE. Toda línea dentro de la tabla cae dentro de algún
     bloque. Una celda que el segmentador no vio no deja hueco visible: deja
     una función que nunca publicamos. Lo no asignado se declara en FANTASMAS.
  3. NINGÚN BLOQUE SE MONTA sobre otro en la misma sede. Dos celdas fundidas en
     una —lo que pasaba con el punteado gris— o una partida en dos se ven acá.
  4. TODA DURACIÓN ES MÚLTIPLO DE 15, que es el paso de la retícula. Es el
     chequeo que habría cazado el error del fin: con el fallo, la mitad de los
     bloques daba 45, 105 o 225 minutos, y todos eran 15 menos de lo dibujado.
  6. EL METRAJE IMPRESO DE UN PROGRAMA cabe en su bloque. Varias celdas traen
     el total («TRÁNSITOS … 3:05:11»): si no cabe, una de las dos horas está mal.
  5. CADA PROGRAMA NOMBRADO EN LA RETÍCULA TIENE FICHAS. Si la retícula anuncia
     «Nuevas Miradas: UMBRALES» y ninguna página de ficha lleva esa cabecera,
     o falta el programa o lo leímos mal.

Sale con 1 si algo no cuadra. Lo entendido se declara acá, con su razón.

    python3 pipeline/villadelcine-2026-verificar.py
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAR = f'{REPO}/festivals/staging/villadelcine-2026-parrilla.json'
PAGS_RETICULA = list(range(2, 12))

# TEXTO QUE ESTÁ EN EL PDF Y NO SE VE EN LA PÁGINA. Sobras de Canva: quedaron
# en la capa de texto de una versión anterior y no las pinta nada. No son
# contenido y no se publican.
FANTASMAS = {
    '#Hija': 'la página del jueves mañana lo trae en la capa de texto y no está '
             'pintado en ninguna parte; cae dentro del recuadro del CLUB DE PITCH',
}

# NO SON UN PROGRAMA: el festival los agrupa bajo una sección en las fichas,
# pero los proyecta por separado y cada uno tiene su propio bloque. Sumarlos
# daría un total que no corresponde a ninguna función.
PROGRAMA_SUELTO = {
    'Rumbo a los Macondo': 'son dos largos en dos funciones distintas — «Llueve '
                           'sobre Babel» el viernes y «Un Poeta» el sábado',
}
# Programas cuyo metraje NO CABE en su bloque y ya está preguntado al festival.
NO_CABE_OK = {
    'Territorios RAÍCES': 'son 19 min de más en el bloque del sábado 11:45–12:45. '
                          'Las cuatro duraciones están leídas de sus fichas y el '
                          'bloque, dibujado. Va en la lista de preguntas.',
}

# Duraciones que el festival dibujó y NO son múltiplo de 15. Ninguna por ahora:
# si aparece una, se mira la página antes de declararla.
DURACION_RARA_OK = {}


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def main():
    d = json.load(open(PAR, encoding='utf-8'))
    bs, fichas = d['bloques'], d['fichas']
    fallos, avisos = [], []

    # 1 · las diez páginas
    vistas = {b['pagina'] for b in bs}
    faltan = [p for p in PAGS_RETICULA if p not in vistas]
    if faltan:
        fallos.append(f'páginas de retícula sin ningún bloque: {faltan}')

    # 2 · ningún texto perdido
    sys.path.insert(0, f'{REPO}/pipeline')
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        'vp', f'{REPO}/pipeline/villadelcine-2026-programa-pdf.py')
    vp = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(vp)
    dentro = {norm(t) for b in bs for t in b['lineas']}
    sueltas = []
    for pag in PAGS_RETICULA:
        ls = vp.lineas(pag, pag)
        horas = [l for l in ls if vp.hora_reticula(l[5])]
        if not horas:
            continue
        y0 = min(l[2] for l in horas)
        for _, lx0, ly0, lx1, ly1, t in ls:
            if ly0 < y0 - 2 or vp.MARCA.match(t) or vp.RE_DIA.match(t) \
                    or vp.hora_reticula(t) or vp.RE_HORA_ROTA.match(t.strip()):
                continue
            if norm(t) not in dentro and t not in FANTASMAS:
                sueltas.append(f'p{pag}: «{t[:52]}»')
    if sueltas:
        fallos.append(f'{len(sueltas)} línea(s) de la tabla que NO quedaron en ningún '
                      f'bloque:\n       ' + '\n       '.join(sueltas[:10]))

    # 3 · sin solapes en la misma sede
    por_sede = {}
    for b in bs:
        por_sede.setdefault((b['dia'], b['sede']), []).append(b)
    for (dia, sede), lista in sorted(por_sede.items()):
        lista.sort(key=lambda b: b['hora'])
        for a, c in zip(lista, lista[1:]):
            if mins(c['hora']) < mins(a['hasta']):
                fallos.append(f'{dia[-2:]} {sede[:28]}: «{a["lineas"][0][:24]}» '
                              f'({a["hora"]}–{a["hasta"]}) se monta sobre '
                              f'«{c["lineas"][0][:24]}» ({c["hora"]}–{c["hasta"]})')

    # 4 · el paso de la retícula es de 15 minutos
    for b in bs:
        t = ' / '.join(b['lineas'])[:40]
        if b['duracion_min'] <= 0:
            fallos.append(f'{b["dia"][-2:]} {b["hora"]} «{t}»: duración {b["duracion_min"]}')
        elif b['duracion_min'] % 15 and t not in DURACION_RARA_OK:
            fallos.append(f'{b["dia"][-2:]} {b["hora"]} «{t}»: {b["duracion_min"]} min '
                          f'no es múltiplo de 15 — la retícula avanza de a 15')

    # 5 · cada programa de la retícula tiene fichas
    cabeceras = {norm(f['cabecera']) for f in fichas}
    RE_PROG = re.compile(r'^([A-Za-zÁÉÍÓÚÑáéíóúñ ]+):\s*(.+)$')
    for b in bs:
        linea = ' '.join(b['lineas'])
        if 'Ruta Acad' in linea or 'Ruta acad' in linea:
            continue
        m = RE_PROG.match(linea)
        if not m:
            continue
        # el rótulo de la celda intercala el formato entre sección y programa
        # («Nuevas Miradas: Cortometraje RESURGENCIAS Nacional…»), así que se
        # cruza por PALABRAS y no por prefijo.
        pal = set(norm(linea).split()) - {'seleccion', 'oficial', 'no', 'competitiva',
                                          'competencia', 'cortometraje', 'nacional',
                                          'internacional', 'opera', 'prima', 'de', 'la',
                                          'y', 'con', 'el', 'del', 'video', 'musical',
                                          'realidad', 'virtual', 'vertical', 'celular',
                                          'ia', 'escolar', 'apasionado', 'youngfilm',
                                          'universities', 'work', 'in', 'progress'}
        if not any(pal and pal <= set(c.split()) | pal - set(c.split()) and
                   len(pal & set(c.split())) >= 2 for c in cabeceras):
            avisos.append(f'{b["dia"][-2:]} {b["hora"]} «{linea[:44]}»: la retícula lo '
                          f'anuncia y ninguna página de ficha lleva esa cabecera')

    # 6 · EL METRAJE IMPRESO NO PUEDE SER MAYOR QUE EL BLOQUE. Varias celdas
    # traen el total del programa («TRÁNSITOS … 3:05:11»). Un bloque más corto
    # que su propio contenido significa que leímos mal una de las dos horas —es
    # el contraste independiente que no depende de mirar la página—.
    RE_METRAJE = re.compile(r'\b(\d):(\d{2}):(\d{2})\b')
    for b in bs:
        linea = ' '.join(b['lineas'])
        m = RE_METRAJE.search(linea)
        if not m:
            continue
        metraje = int(m.group(1)) * 60 + int(m.group(2)) + (1 if int(m.group(3)) else 0)
        if metraje > b['duracion_min']:
            avisos.append(f'{b["dia"][-2:]} {b["hora"]}–{b["hasta"]} '
                          f'«{linea[:34]}»: el bloque dura {b["duracion_min"]} min y su '
                          f'metraje impreso es {metraje} ({m.group(0)})')

    # 7 · LA SUMA DE LAS OBRAS CABE EN SU BLOQUE. Es información que ninguna
    # otra comprobación tiene: el chequeo 6 usa el metraje que la celda imprime,
    # y solo lo imprimen algunas. Este suma las fichas del programa. Una obra de
    # más, una duración mal leída o un programa mal asignado se ven acá.
    obras_p = f'{REPO}/festivals/staging/villadelcine-2026-obras-pdf.json'
    if os.path.exists(obras_p):
        obras = json.load(open(obras_p, encoding='utf-8'))['obras']
        por_prog = {}
        for o in obras:
            k = norm(o['programa']) or norm(o['seccion'])
            if not k:
                continue
            e = por_prog.setdefault(k, {'min': 0, 'n': 0, 'sin': 0,
                                        'nombre': f"{o['seccion']} {o['programa']}".strip()})
            e['n'] += 1
            if o['duracion_min']:
                e['min'] += o['duracion_min']
            else:
                e['sin'] += 1
        for k, e in sorted(por_prog.items()):
            cand = [b for b in bs if k in norm(' '.join(b['lineas']))]
            if not cand or e['nombre'] in PROGRAMA_SUELTO:
                continue
            tope = max(b['duracion_min'] for b in cand)
            if e['min'] > tope:
                aviso = (f'«{e["nombre"]}»: sus {e["n"]} obras suman {e["min"]} min y el '
                         f'bloque dura {tope}')
                if e['nombre'] in NO_CABE_OK:
                    avisos.append(aviso + f' — {NO_CABE_OK[e["nombre"]]}')
                else:
                    fallos.append(aviso)
            elif e['sin']:
                avisos.append(f'«{e["nombre"]}»: {e["sin"]} de {e["n"]} obras sin '
                              f'duración en el PDF; el hueco lo llena el cruce con la web')

    print(f'villadelcine-2026: {len(bs)} bloques · {len(vistas)}/10 páginas · '
          f'{len(fichas)} páginas de ficha')
    for a in avisos:
        print('   · para mirar:', a)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for f in fallos:
            print('   ✗', f)
        sys.exit(1)
    print('\n✓ cada celda dibujada tiene su bloque, sin solapes y con duración de retícula')


if __name__ == '__main__':
    main()
