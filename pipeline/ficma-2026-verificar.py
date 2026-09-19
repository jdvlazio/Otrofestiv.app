#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-verificar.py — la parrilla contra sí misma, y contra lo publicado.

POR QUÉ. El crudo sale de UNA lectura: el OCR de la plantilla, con las cajas
diciendo qué campo es cada línea. Que esa lectura sea buena no lo prueba ella
misma. Esto la contrasta con lo que el mismo PDF dice por OTRO lado y con lo
que terminó publicado.

LAS CUATRO PRUEBAS, y cada una puede fallar sola:

  1 · CADA PÁGINA, CONTADA. Las 78 páginas tienen que ser portada de día o
      función, sin saltarse ninguna. Es la cobertura inversa: verificar lo
      transcrito no verifica lo descartado. Una página PUEDE dar más de una
      función —«HORA: 1:30 pm y 4:00 pm» son dos pases de la misma obra el
      mismo día— y esos registros extra lo declaran con `_mismo_dia_otro_pase`;
      repetirse SIN declararlo sigue siendo un fallo.

  2 · EL DÍA, DOS VECES. El día de una función sale de la ÚLTIMA portada
      («PROGRAMACIÓN / SÁBADO 19 DE SEPTIEMBRE»), que es un arrastre: si una
      portada se leyera mal, todas las páginas que la siguen quedarían con el
      día equivocado y nada lo delataría. Pero cada página lleva ADEMÁS su
      propio badge arriba a la derecha («SÁBADO 19»). Se comparan.

  3 · LA HORA, DOS VECES. Abajo, en la columna, «HORA: 9:00 am». Arriba, en el
      badge, «9:00 AM». El parser usa la de abajo y cae en la de arriba solo si
      falta; acá se exige que coincidan.

  4 · LO PUBLICADO ES LO LEÍDO. Cada función del crudo tiene que estar en
      `festivals/ficma-2026.json` con su día y su hora, y el JSON no puede
      traer funciones que el crudo no tenga —salvo la franja académica, que
      viene de otra fuente, y salvo las horas que el festival contradijo en
      Instagram, que están DECLARADAS en `ficma-2026-ig-dias.json`—. Una
      diferencia declarada se imprime; una sin declarar falla.

Sale con código 1 si algo no casa. Un verificador que no puede fallar no sirve.

    python3 pipeline/ficma-2026-verificar.py
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CRUDO = f'{ST}/ficma-2026-crudo-septiembre.json'
OCR = f'{ST}/ficma-2026-ocr-septiembre.json'
PUB = f'{REPO}/festivals/ficma-2026.json'

DIAS_SEM = {'LUNES': 0, 'MARTES': 1, 'MIERCOLES': 2, 'JUEVES': 3, 'VIERNES': 4,
            'SABADO': 5, 'DOMINGO': 6}
# La franja académica NO sale del PDF: son las once actividades de
# /talleresficma17/. Se declaran para que la prueba 4 no las cuente como
# funciones inventadas.
OTRA_FUENTE = {'taller', 'ponencia'}


def hhmm(s):
    m = re.search(r'(\d{1,2})[:.](\d{2})\s*([ap])', (s or ''), re.I)
    if not m:
        return ''
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == 'p' and h != 12:
        h += 12
    if ap == 'a' and h == 12:
        h = 0
    return f'{h:02d}:{mm}'


def main():
    crudo = json.load(open(CRUDO, encoding='utf-8'))
    ocr = json.load(open(OCR, encoding='utf-8'))
    ocr.pop('_provenance', None)
    pub = json.load(open(PUB, encoding='utf-8'))
    igd = json.load(open(f'{ST}/ficma-2026-ig-dias.json', encoding='utf-8'))['discrepa']
    fallos, mirar = [], []

    # ── 1 · cada página, una cosa ────────────────────────────────────────────
    vistas = [f['pagina'] for f in crudo['funciones']] + \
             [p['pagina'] for p in crudo['portadas']] + \
             [s['pagina'] for s in crudo.get('sin_clasificar', [])]
    _declarados = sum(1 for f in crudo['funciones'] if f.get('_mismo_dia_otro_pase'))
    if len(vistas) - _declarados != len(set(vistas)):
        rep = {p for p in vistas if vistas.count(p) > 1}
        fallos.append(f'páginas contadas dos veces sin declararlo: {sorted(rep)}')
    faltan = sorted(set(ocr) - set(vistas))
    if faltan:
        fallos.append(f'páginas del PDF que nadie leyó: {faltan}')
    if crudo.get('sin_clasificar'):
        fallos.append(f"{len(crudo['sin_clasificar'])} página(s) sin clasificar: "
                      + ', '.join(s['pagina'] for s in crudo['sin_clasificar']))

    # ── 2 y 3 · el día y la hora, dos veces cada uno ─────────────────────────
    for f in crudo['funciones']:
        badge = lib.sinacento(f.get('dia_badge', '')).upper()
        m = re.match(r'([A-ZÁÉÍÓÚ]+)\s+(\d{1,2})', badge)
        if not m:
            mirar.append(f"{f['pagina']}: sin badge de día para contrastar "
                         f"(«{f['titulo'][:40]}»)")
        else:
            dia_badge = int(m.group(2))
            if dia_badge != int(f['dia'][-2:]):
                fallos.append(f"{f['pagina']}: la portada dice {f['dia']} y el badge "
                              f"de la página dice «{f.get('dia_badge')}» — «{f['titulo'][:40]}»")
            # y que el nombre del día case con la fecha real
            import datetime
            dow = datetime.date.fromisoformat(f['dia']).weekday()
            if DIAS_SEM.get(m.group(1)) not in (None, dow):
                fallos.append(f"{f['pagina']}: «{f.get('dia_badge')}» no cae en "
                              f"{f['dia']} (ese día es otro)")

        # la hora del badge, contra la del campo
        ls = [l for l in ocr.get(f['pagina'], []) if l['w'] > l['h'] and l['y'] < 0.08]
        # El badge puede traer las DOS horas («1:30 PM Y 4:00 PM»): se aceptan
        # todas, no solo la primera, o el segundo pase parecería un error.
        badge_hs = [hhmm(x) for l in ls
                    for x in re.findall(r'\d{1,2}:\d{2}\s*[AP]M?', l['t'], re.I)]
        badge_hs = [h for h in dict.fromkeys(badge_hs) if h]
        badge_h = badge_hs[0] if badge_hs else ''
        if not badge_h:
            mirar.append(f"{f['pagina']}: sin hora en el badge («{f['titulo'][:40]}»)")
        elif f.get('_hora_errata'):
            mirar.append(f"{f['pagina']}: errata declarada — {f['_hora_errata']}")
        elif f['hora'] not in badge_hs:
            fallos.append(f"{f['pagina']}: la columna dice {f['hora']} y el badge "
                          f"dice {badge_h} — «{f['titulo'][:40]}»")

    # ── 4 · lo publicado es lo leído ─────────────────────────────────────────
    del_crudo = set()
    for f in crudo['funciones']:
        d = igd.get(f['titulo'])
        if d:
            mirar.append(f"«{f['titulo'][:40]}»: el PDF dice {f['hora']} y se publica "
                         f"{d['hora']} por Instagram — {d['por_que'][:80]}…")
        del_crudo.add((lib.norm(f['titulo']), f['dia'], d['hora'] if d else f['hora']))
    publicadas = {(lib.norm(f['title']), f['day'], f['time']) for f in pub['films']
                  if f.get('event_kind') not in OTRA_FUENTE}
    perdidas = del_crudo - publicadas
    if perdidas:
        fallos.append(f'{len(perdidas)} función(es) del programa que NO se publicaron: '
                      + '; '.join(f'{t} {d[-2:]}·{h}' for t, d, h in sorted(perdidas)))
    inventadas = publicadas - del_crudo
    if inventadas:
        fallos.append(f'{len(inventadas)} función(es) publicadas que el programa no trae: '
                      + '; '.join(f'{t} {d[-2:]}·{h}' for t, d, h in sorted(inventadas)))

    print(f'{len(ocr)} páginas · {len(crudo["portadas"])} portadas · '
          f'{len(crudo["funciones"])} funciones · {len(pub["films"])} publicadas')
    for m in mirar:
        print('   · para mirar:', m)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for f in fallos:
            print('   ✗', f)
        sys.exit(1)
    print('\n✓ el día y la hora de cada función casan por los dos lados, '
          'ninguna página quedó sin leer y lo publicado es exactamente lo leído')


if __name__ == '__main__':
    main()
