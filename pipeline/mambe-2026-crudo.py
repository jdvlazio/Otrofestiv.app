#!/usr/bin/env python3
"""mambe-2026-crudo.py — la programación del 13.º Festival MAMBE (Florencia, Caquetá,
3–7 nov 2026) → crudo.

LA FUENTE es el carrusel oficial de programación de @festivalmambe,
`p/DfIOLhBloOw` del 30 oct 2026: 12 láminas. 00 es la portada, 01 las
«Exposiciones permanentes» (sin hora: no son funciones), 02–09 la agenda día por
día y 10–11 los logos. El pie dice «Todo es gratis y de entrada libre».

DOS LECTURAS: la transcripción A OJO (fuentes/mambe-2026/mambe-2026-laminas-ojos.json),
verbatim y con las erratas, y el OCR de la lámina oficial (pipeline/ocr.swift).
Cada hora y cada palabra del encabezado tienen que aparecer en SU lámina, o el
paso falla. `ig-lecturas.py DfIOLhBloOw` corrió además sus tres lecturas de OCR
sin discrepancias (el ALT no lo sirvió Instagram). El radar #1323
(festivals/staging/mambe-2026-radar.json) no nombra salas ni horas.

LA CAJA: las láminas van en mayúscula sostenida. Las obras pasan a caja de
frase («SOÑÉ SU NOMBRE» → «Soñé su nombre»); las actividades, que el festival
nombra como programa («TALLER: CINE COMUNITARIO»), a Título.

LO QUE NO ENTRA AL CRUDO (pendiente de Juan, ver NO_SE_PUBLICA):
  · las dos proyecciones de «Cuando las palabras vuelan se hacen búsqueda» en
    la Cárcel Heliconias y la Cárcel El Cunduy: una función dentro de un penal
    no es abierta al público;
  · el «Encuentro: Taller Mujeres Buscadoras» del sábado: «Todo el día», sin hora.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'mambe-2026'
POST = 'DfIOLhBloOw'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
OJOS = f'{REPO}/fuentes/{FID}/{FID}-laminas-ojos.json'
OUT = f'{REPO}/festivals/staging/mambe-2026-crudo.json'
SRC = {'url': f'https://www.instagram.com/p/{POST}/', 'date': '2026-10-30'}

PROYECCIONES = 'Proyecciones'
ACTIVIDADES = 'Actividades'

# ── LAS PROYECCIONES: (día, hora, encabezado) → título y obras ──────────────
# has_qa: el encabezado dice «+ CONVERSATORIO».
H = '2026-11-'
PROYECCION = {
    (H + '03', '19:30', 'APERTURA FESTIVAL · PROYECCIÓN + CONVERSATORIO: HORIZONTE'):
        {'titulo': 'Horizonte', 'premiere': 'Apertura Festival'},
    (H + '04', '19:30', 'PROYECCIÓN + CONVERSATORIO: PROVISORIUM'): {'titulo': 'Provisorium'},
    # la lámina no dice si es una obra o dos; se publica tal cual
    (H + '04', '19:00', 'PROYECCIÓN: VOLAR Y TRES CLAVELES'): {'titulo': 'Volar y tres claveles'},
    # la «y» va en minúscula y más chica que los títulos: son dos obras
    (H + '04', '19:30', 'PROYECCIÓN + CONVERSATORIO: EL RÍO QUE SIEMPRE SE VA y ANTES DE LA NIEVE'): {
        'titulo': 'El río que siempre se va y Antes de la nieve',
        'obras': [{'titulo': 'El río que siempre se va'}, {'titulo': 'Antes de la nieve'}]},
    # dos encabezados con un solo lugar y una sola hora: una sesión con dos obras
    (H + '05', '19:00', 'PROYECCIÓN + CONVERSATORIO: GUARDIANES DE LA FAUNA AMAZÓNICA: Plecturocebus '
                        'Caquetensis · PROYECCIÓN + CONVERSATORIO: LOS GUARDIANES DE LAS AVES'): {
        'titulo': 'Guardianes de la fauna amazónica: Plecturocebus caquetensis y Los guardianes de las aves',
        'obras': [{'titulo': 'Guardianes de la fauna amazónica: Plecturocebus caquetensis'},
                  {'titulo': 'Los guardianes de las aves'}]},
    (H + '05', '19:30', 'PROYECCIÓN + CONVERSATORIO: LA MEMORIA DE LAS MARIPOSAS'):
        {'titulo': 'La memoria de las mariposas'},
    (H + '06', '16:00', 'PROYECCIÓN + CONVERSATORIO: SOÑÉ SU NOMBRE'): {'titulo': 'Soñé su nombre'},
    (H + '06', '19:30', 'PROYECCIÓN + CONVERSATORIO: LACTAR'): {'titulo': 'Lactar'},
    (H + '07', '19:30', 'PROYECCIÓN + CONVERSATORIO: CHIRIBIQUETE'): {'titulo': 'Chiribiquete'},
}

# ── LAS ACTIVIDADES: título = el encabezado en Título; event_kind = la palabra
# del festival antes de los dos puntos cuando la app la conoce (taller,
# conversatorio, encuentro, fiesta). «Inauguración», «Laboratorio», «Proyección»
# y «Exhibición» no están en _kindMapES (código de la app): van como «evento»,
# que no traduce nada —la palabra del festival sigue en el título—. Si Main
# suma esas claves, se cambian acá. «Comunitarioy» es errata de la lámina.
ACTIVIDAD = {
    (H + '03', '18:00', 'INAUGURACIÓN EXPOSICIÓN: JAVIER MURILLO'):
        {'titulo': 'Inauguración Exposición: Javier Murillo', 'kind': 'evento'},
    (H + '04', '09:00', 'TALLER: CINE COMUNITARIO'): {'titulo': 'Taller: Cine Comunitario', 'kind': 'taller'},
    (H + '05', '09:00', 'TALLER: CINE COMUNITARIO'): {'titulo': 'Taller: Cine Comunitario', 'kind': 'taller'},
    (H + '06', '09:00', 'TALLER: CINE COMUNITARIO'): {'titulo': 'Taller: Cine Comunitario', 'kind': 'taller'},
    (H + '04', '17:00', 'TALLER: STOP MOTION PEDALIANDO CINE'):
        {'titulo': 'Taller: Stop Motion Pedaliando Cine', 'kind': 'taller'},
    (H + '04', '17:00', 'LABORATORIO: SERIGRAFÍA'): {'titulo': 'Laboratorio: Serigrafía', 'kind': 'evento'},
    (H + '05', '17:00', 'LABORATORIO: SERIGRAFÍA'): {'titulo': 'Laboratorio: Serigrafía', 'kind': 'evento'},
    (H + '05', '08:00', 'TALLER: STENOPEICA'): {'titulo': 'Taller: Stenopeica', 'kind': 'taller'},
    (H + '05', '15:00', 'TALLER ACTUACIÓN: MARÍA CECILIA SANCHEZ'):
        {'titulo': 'Taller Actuación: María Cecilia Sanchez', 'kind': 'taller'},
    (H + '06', '15:00', 'TALLER ACTUACIÓN: MARÍA CECILIA SANCHEZ'):
        {'titulo': 'Taller Actuación: María Cecilia Sanchez', 'kind': 'taller'},
    (H + '05', '15:30', 'COCTEL + CONVERSATORIO: EXPOSICIÓN FOTOGRÁFICA GERSON SAENZ'):
        {'titulo': 'Coctel + Conversatorio: Exposición Fotográfica Gerson Saenz', 'kind': 'conversatorio'},
    (H + '05', '16:00', 'FESTIVAL DE CORTOS PSICOACTIVOS + CONVERSATORIO'):
        {'titulo': 'Festival de Cortos Psicoactivos + Conversatorio', 'kind': 'evento'},
    (H + '05', '16:00', 'TALLER: CIANOTIPIA'): {'titulo': 'Taller: Cianotipia', 'kind': 'taller'},
    (H + '06', '09:00', 'ENCUENTRO: TALLER MUJERES BUSCADORAS'):
        {'titulo': 'Encuentro: Taller Mujeres Buscadoras', 'kind': 'encuentro'},
    (H + '06', '17:00', 'TALLER: SERIGRAFÍA'): {'titulo': 'Taller: Serigrafía', 'kind': 'taller'},
    (H + '07', '17:00', 'TALLER: SERIGRAFÍA'): {'titulo': 'Taller: Serigrafía', 'kind': 'taller'},
    (H + '07', '17:00', 'EXHIBICIÓN: TALLER CINE COMUNITARIO'):
        {'titulo': 'Exhibición: Taller Cine Comunitario', 'kind': 'evento'},
    (H + '07', '17:00', 'EXHIBICIÓN: TALLER CIANOTIPIA'):
        {'titulo': 'Exhibición: Taller Cianotipia', 'kind': 'evento'},
    (H + '07', '17:00', 'EXHIBICIÓN: TALLER STENOPEICA'):
        {'titulo': 'Exhibición: Taller Stenopeica', 'kind': 'evento'},
    (H + '07', '19:00', 'PROYECCIÓN: RESULTADO TALLER CINE COMUNITARIOY GANADORES FILMEMORIA'):
        {'titulo': 'Proyección: Resultado Taller Cine Comunitario y Ganadores Filmemoria', 'kind': 'evento'},
    (H + '07', '22:00', 'FIESTA DE CIERRE'): {'titulo': 'Fiesta de Cierre', 'kind': 'fiesta'},
}

# Exposiciones y exhibiciones: actividad abierta (`info`), no se reserva
# ([abierta-sin-info]). La inauguración y el coctel de las exposiciones tienen
# hora, pero el guardián las lee como exposición: van abiertas, PENDIENTE de Juan.
ABIERTAS = {'Inauguración Exposición: Javier Murillo',
            'Coctel + Conversatorio: Exposición Fotográfica Gerson Saenz',
            'Exhibición: Taller Cine Comunitario', 'Exhibición: Taller Cianotipia',
            'Exhibición: Taller Stenopeica'}

# Los talleres de varias jornadas: un bloque (PROTOCOLO §4)
RECURRENTES = {'Taller: Cine Comunitario', 'Taller Actuación: María Cecilia Sanchez',
               'Laboratorio: Serigrafía', 'Taller: Serigrafía'}

NO_SE_PUBLICA = {
    (H + '05', '09:00', 'PROYECCIÓN: CUANDO LAS PALABRAS VUELAN SE HACEN BUSQUEDA'):
        'proyección dentro de la Cárcel Heliconias: no es abierta al público',
    (H + '06', '09:00', 'PROYECCIÓN: CUANDO LAS PALABRAS VUELAN SE HACEN BUSQUEDA'):
        'proyección dentro de la Cárcel El Cunduy: no es abierta al público',
    (H + '07', '', 'ENCUENTRO: TALLER MUJERES BUSCADORAS'): 'la lámina dice «Todo el día», sin hora',
}

ACCESO = 'Entrada libre'
_ACCESO = {
    'estado': ACCESO,
    'revisado': '2026-10-31',
    'fuentes': ['el pie del carrusel oficial (instagram.com/p/DfIOLhBloOw/)'],
    '_por_que': '«Todo es gratis y de entrada libre» (pie del post de programación, 30 oct 2026).',
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def ocr(n):
    r = subprocess.run(['swift', f'{REPO}/pipeline/ocr.swift', f'{LAMINAS}/{n:02d}.jpg'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ el OCR de la lámina {n:02d} falló: {r.stderr[:200]}')
    return plano(' '.join(json.loads(r.stdout)['lineas']))


def hora12(h):
    a, b = map(int, h.split(':'))
    a = a - 12 if a > 12 else a
    return {f'{a} {b:02d}', f'{a:02d} {b:02d}'}


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['items']
    texto = {n: ocr(n) for n in sorted({f['lamina'] for f in ojos})}
    fallos, funciones, vistos = [], [], set()
    for f in ojos:
        k = (f['dia'], f['hora'], f['encabezado'])
        if k in vistos:
            fallos.append(f'clave repetida en la transcripción: {k}')
        vistos.add(k)
        t = texto[f['lamina']]
        w = set(t.split())
        if f['hora'] and not any(h in t for h in hora12(f['hora'])):
            fallos.append(f'{k}: el OCR no encuentra la hora en la lámina {f["lamina"]:02d}')
        faltan = [x for x in plano(f['encabezado']).split() if len(x) >= 4 and x not in w]
        if faltan:
            fallos.append(f'{k}: el OCR no encuentra {faltan} en la lámina {f["lamina"]:02d}')
        p, a, fuera = PROYECCION.get(k), ACTIVIDAD.get(k), NO_SE_PUBLICA.get(k)
        if sum(map(bool, (p, a, fuera))) != 1:
            fallos.append(f'{k}: sin clasificar, o en más de una tabla')
            continue
        if fuera:
            continue
        base = {'dia': f['dia'], 'hora': f['hora'], 'sede': f['lugar'], 'acceso': ACCESO,
                '_src': dict(SRC, lamina=f['lamina'])}
        if f.get('fin'):
            base['duracion_min'] = mins(f['fin']) - mins(f['hora'])
        if p:
            reg = {**base, 'titulo': p['titulo'], 'seccion': PROYECCIONES,
                   'has_qa': 'CONVERSATORIO' in f['encabezado']}
            if p.get('premiere'):
                reg['premiere'] = p['premiere']
            if p.get('obras'):
                reg['obras'] = p['obras']
        else:
            reg = {**base, 'titulo': a['titulo'], 'tipo': 'evento', 'event_kind': a['kind'],
                   'seccion': ACTIVIDADES}
            if a['titulo'] in ABIERTAS:
                reg['info'] = True
            if a['titulo'] in RECURRENTES:
                reg['is_recurring'] = True
        funciones.append(reg)
    sin_usar = (set(PROYECCION) | set(ACTIVIDAD) | set(NO_SE_PUBLICA)) - vistos
    if sin_usar:
        fallos.append(f'entradas de las tablas que ninguna lámina tiene: {sorted(sin_usar)}')
    if fallos:
        sys.exit('✗ la transcripción, el OCR y las tablas no coinciden:\n  · ' + '\n  · '.join(fallos))

    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @festivalmambe — el carrusel oficial de programación (12 láminas)',
            que_aporta='la programación entera: día, hora, lugar y actividad',
            url=SRC['url'],
            metodo='transcripción a ojo lámina por lámina, confirmada hora por hora y palabra por '
                   'palabra con el OCR de la lámina oficial'),
        '_acceso': _ACCESO,
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} ({len(funciones) - n_ev} proyecciones + {n_ev} actividades) · '
          f'{len({f["sede"] for f in funciones})} lugares · OCR de acuerdo → '
          f'{os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
