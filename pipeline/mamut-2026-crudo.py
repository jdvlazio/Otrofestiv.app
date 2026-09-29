#!/usr/bin/env python3
"""mamut-2026-crudo.py — la programación de Mamut 11 → crudo.

LA FUENTE es el carrusel de programación de @mamut_festival, `p/Dd2ckXgiYW9`
(28 sep 2026) — la VERSIÓN CORREGIDA del `p/Dd2bBTciVpN` que publicaron antes
el mismo día con el mismo pie. Las dos siguen arriba; la corregida mueve la
inaugural a las 6, la clausura a Coocine y Apocalipsur a la Capilla de Comfama,
agrega salas y conversatorios. Se lee la corregida: 11 láminas, una por día (2–9; el domingo ocupa dos) y la 10 con
las seis sedes y su dirección. El pie: «Entrada libre a todas las actividades».

LA DIAGRAMACIÓN ES LIBRE: bloques sueltos sobre la ilustración, dos columnas por
fila, el día en cualquier esquina. La OCR con cajas mezcla columnas (juntó las
dos sesiones de las 9 a. m. del miércoles, se saltó «Geographies of Solitude»),
así que MANDA LA LECTURA A OJO —fuentes/mamut-2026-ojos-programa.json— y la OCR
la confirma: toda palabra de 4+ letras del título y toda hora, en SU lámina, y
en sentido inverso que cada hora impresa tenga su actividad.

LO QUE QUEDA FUERA, por decisión de Juan (28 sep 2026): los tres laboratorios
con la convocatoria CERRADA —«Mitos, mitómanos y misterios», «Residencia de
archivos» y «Tarjetas de visita»—. Eligieron a sus participantes el 27 sep; nadie
que abra la app puede ir. Ver EXCLUIDOS.

LO QUE LAS LÁMINAS NO DICEN, y no se inventa:
  · qué cortos van en cada programa: las dos selecciones suman 108 y 120 min y
    los programas duran 60 (martes) y 30 (domingo) — no cuadra, se preguntó;
  · la duración de los programas sin obras publicadas: el hueco hasta la
    siguiente actividad EN LA MISMA SEDE (la regla de Itagüí y Girardota), con
    DURACION_POR_DEFECTO de tope — «Huella mi frente» tendría 210 min hasta
    «Minuto fatal»;
  · la dirección de «Lab UNAL», que no está en la lámina de sedes.
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

FID = 'mamut-2026'
POST = 'Dd2ckXgiYW9'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
OJOS = f'{REPO}/fuentes/mamut-2026-ojos-programa.json'
OCR = f'{REPO}/fuentes/mamut-2026-ocr-programa.json'
CATALOGO = f'{REPO}/festivals/staging/mamut-2026-programa-catalogo.json'
OUT = f'{REPO}/festivals/staging/mamut-2026-crudo.json'
DURACION_POR_DEFECTO = 90

EXCLUIDOS = {
    'Mitos, mitómanos y misterios': 'laboratorio con convocatoria cerrada (formulario '
        'forms.gle/VM95ezS8cbEfkSc37 ya no acepta respuestas); Juan, 28 sep',
    'Residencia de archivos': '«Residencia de archivos: laboratorio creativo de devolución», '
        '15 cupos por selección, cerrada el 25 sep; Juan, 28 sep',
    'Tarjetas de visita': 'laboratorio de 14 cupos por selección, cerrado el 25 sep; Juan, 28 sep',
}

# LA OCR SE EQUIVOCA DONDE LA LÁMINA NO. Cada diferencia, mirada en la imagen.
OCR_ENTENDIDO = {
    ('Huella mi frente', 'titulo_lamina'): 'la OCR lee «10ELLA MI FRENTE»; la lámina 4 dice HUELLA',
}

# ── LAS SEDES: el nombre que imprime la lámina de días → la sede que se publica.
# La lámina 10 nombra las mismas con su nombre largo («Cineprox Las Américas»,
# «Cooperativa Coocine»); en la de cada día van cortas. Se publica la corta, que
# es la que el público lee en la programación.
SEDES = {
    'Centro Colombo Americano': 'Centro Colombo Americano',
    'Persona': 'Persona',
    'Museo de Arte Moderno de Medellín - MAMM': 'Museo de Arte Moderno de Medellín - MAMM',
    'La Pascasia': 'La Pascasia',
    'Las Américas': 'Las Américas',
    'Coocine': 'Coocine',
    'Lab UNAL': 'Lab UNAL',
    # NUEVA en la versión corregida y AUSENTE de la lámina de sedes: Comfama
    # tiene varias sedes en Medellín y la lámina no dice cuál. Se publica tal
    # cual y sin pin hasta saberlo.
    'Capilla, Comfama': 'Capilla, Comfama',
    'Maker Lab, Colombo': 'Maker Lab, Colombo',
}

# ── LAS SECCIONES. El festival no agrupa por secciones; como en Girardota,
# proyecciones y actividades. Las dos palabras son nuestras.
SECCION_PROYECCION = 'Proyecciones'
SECCION_ACTIVIDAD = 'Actividades'

# ── LAS ACTIVIDADES que no son proyección: título → event_kind
# EL TALLER CON DOS NOMBRES. La versión corregida lo llama «Archivos no
# hegemónicos» en las sesiones 1 y 2 (mar, mié) y sigue diciendo «Archivistas
# salvajes» en la 3 y la 4 (jue, vie). Es UN taller —mismo tallerista, mismo
# lab, sesiones 01 a 04— y un bloque recurrente necesita UN título: se toma el
# de la corrección, que es el que el festival acaba de escribir. Pendiente del
# visto bueno de Juan.
TITULO_UNIFICADO = {'Archivistas salvajes': 'Archivos no hegemónicos'}
ACTIVIDAD = {
    'Archivos no hegemónicos': 'taller',
    'Fiesta clausura #MAMUT11': 'fiesta',
    # «Sesión de cine en vivo»: la palabra del festival es la de un kind que ya existe
    'Huella mi frente': 'live cinema',
    # el festival no lo rotula; «convite» es nuestra lectura (SiembraFest), por aprobar
    '¡Sancocho!': 'convite',
}
INSCRIPCION = {
    # linktr.ee/M.A.M.U.T, el único de los cuatro formularios que sigue abierto (28 sep)
    'Archivos no hegemónicos': 'https://docs.google.com/forms/d/e/1FAIpQLSdYPDQSwEfwWZ72Hz6gEO0S9HgGzT1s8MODSDHOKDCXl-hAlw/viewform',
}
# lo que el festival dice de un taller en su post, que la lámina no trae
SINOPSIS_TALLER = {
    'Archivos no hegemónicos': 'Taller teórico-práctico impartido por Daniel Delgado Saucedo '
        '(Archivistas Salvajes): cuatro jornadas para aproximarse a la identificación, '
        'inspección y conservación de soportes fotoquímicos y magnéticos, enfocándose en '
        'el valor de los cines amateurs, domésticos y comunitarios. Cupo: 12 personas.',
}
# LA SALA QUE LA LÁMINA NO DICE Y OTRA FUENTE DEL FESTIVAL SÍ. El post de la
# función (p/DdwI93AkW1e, 25 sep): «08 de octubre | 6:30 p. m. | Teatro MAMM».
SALA_DE_OTRA_FUENTE = {'Frío metal': 'Teatro'}
# y la SINOPSIS del mismo post, que es texto del festival: le gana a la de TMDB
# (que ni siquiera la tiene en español)
SINOPSIS_DE_OTRA_FUENTE = {
    'Frío metal': 'Mario despierta sin memoria al oriente de la Ciudad de México. A la deriva, '
                  'junto a Lázaro, aprende a habitar cuerpos ajenos a través de grietas en la '
                  'tierra. Un viaje hipnótico donde el territorio atraviesa la piel y el paisaje '
                  'se distorsiona al ritmo de los recuerdos.',
}

# El Q&A lo dice la lámina corregida («CONVERSACION CON DIRECTOR», `qa` en la
# transcripción). Con invitados nombrados, `guests` y la lista va a la ficha.


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def hora_ocr(h):
    a, b = map(int, h.split(':'))
    a = a - 12 if a > 12 else a
    return [f'{a} {b:02d}'] if b else [f'{a} p m', f'{a} a m', f'{a}p m', f'{a}a m', f'{a} 00']


def verifica(ojos):
    """Cada título, crédito, sede y hora en SU lámina; y cada hora impresa, con
    su actividad (cobertura inversa)."""
    cajas = json.load(io.open(OCR, encoding='utf-8'))
    texto = {int(k[:2]): plano(' '.join(b['t'] for b in v)) for k, v in cajas.items()}
    fallos = []
    for f in ojos:
        t, w = texto[f['lamina']], set(texto[f['lamina']].split())
        for campo in ('titulo_lamina', 'credito', 'sede'):
            faltan = [x for x in plano(f.get(campo, '')).split() if len(x) >= 4 and x not in w]
            if faltan and (f['titulo'], 'credito' if campo == 'credito' else campo) not in OCR_ENTENDIDO:
                fallos.append(f'«{f["titulo"]}»: la OCR no encuentra {faltan} ({campo}) en la lámina {f["lamina"]}')
        if not any(x in t for x in hora_ocr(f['hora'])) and (f['titulo'], 'hora') not in OCR_ENTENDIDO:
            fallos.append(f'«{f["titulo"]}» {f["hora"]}: la OCR no encuentra la hora en la lámina {f["lamina"]}')
    hora_re = re.compile(r'^\s*\d{1,2}(:\d{2})?\s*(a|p)\.?')
    for k, v in cajas.items():
        n = int(k[:2])
        impresas = sum(1 for b in v if hora_re.match(b['t']))
        propias = sum(1 for f in ojos if f['lamina'] == n and not f.get('_nota', '').startswith('va en el mismo bloque'))
        if impresas != propias:
            fallos.append(f'lámina {n}: {impresas} horas impresas y {propias} actividades con hora')
    return fallos


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def duracion_sin_dato(funciones):
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and mins(g['hora']) > mins(f['hora']))
        hueco = sig[0] - mins(f['hora']) if sig else None
        if hueco and hueco <= DURACION_POR_DEFECTO:
            f['duracion_min'] = hueco
            f['_duracion_de'] = 'el hueco hasta la siguiente actividad en la misma sede'
        else:
            f['duracion_min'] = DURACION_POR_DEFECTO
            f['_duracion_de'] = (f'{DURACION_POR_DEFECTO} min declarados: la lámina no la da'
                                 + (f' y el hueco hasta la siguiente en la sede es de {hueco} min'
                                    if hueco else ' y cierra su sede ese día'))


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['actividades']
    fallos = verifica(ojos)
    if fallos:
        sys.exit('✗ la transcripción y la OCR no coinciden:\n  · ' + '\n  · '.join(fallos))
    catalogo = {o['titulo']: o for o in json.load(io.open(CATALOGO, encoding='utf-8'))['obras']}

    funciones, fuera = [], []
    for a in ojos:
        t = TITULO_UNIFICADO.get(a['titulo'], a['titulo'])
        if t in EXCLUIDOS:
            fuera.append(f'{a["dia"]} {a["hora"]} {t}')
            continue
        if a['sede'] not in SEDES:
            sys.exit(f'✗ sede sin entrada en la tabla: {a["sede"]!r}')
        reg = {'titulo': t, 'dia': a['dia'], 'hora': a['hora'], 'sede': SEDES[a['sede']],
               **({'sala': a.get('sala') or SALA_DE_OTRA_FUENTE[t]}
                  if (a.get('sala') or t in SALA_DE_OTRA_FUENTE) else {}),
               'acceso': 'Entrada libre',
               '_src': {'url': f'https://www.instagram.com/p/{POST}/', 'date': '2026-09-28',
                        'lamina': a['lamina']}}
        if t in ACTIVIDAD:
            reg.update(tipo='evento', event_kind=ACTIVIDAD[t], seccion=SECCION_ACTIVIDAD)
        else:
            reg['seccion'] = SECCION_PROYECCION
            o = catalogo.get(t)
            if o:
                for c in ('director', 'pais', 'anio', 'duracion_min'):
                    if o.get(c):
                        reg[c] = o[c]
        if a.get('hora_fin'):
            reg['duracion_min'] = mins(a['hora_fin']) - mins(a['hora'])
        if a.get('rotulo') == 'Inauguración':
            reg['premiere'] = 'Inauguración'
        elif a.get('premiere'):
            reg['premiere'] = a['premiere']
        if a.get('qa'):
            reg['has_qa'] = True
            reg['qa_type'] = 'guests' if a.get('invitados') else 'team'
        if a.get('invitados'):
            reg['invitados'] = f'Invitados: {a["invitados"]}.'
        # un PROGRAMA con nombre y obras nombradas: modelo A (is_cortos + obras)
        if a.get('obras'):
            reg['obras'] = [{**{k: v for k, v in catalogo[o['titulo']].items()
                                if k in ('titulo', 'director', 'pais', 'anio', 'duracion_min')}}
                            for o in a['obras']]
            # la duración de un programa es la SUMA de sus obras (PROTOCOLO:
            # «Suma de las obras de un programa = duración declarada»); sin
            # esto, el hueco hasta la siguiente función le ponía 90 min a un
            # programa de 39
            reg['duracion_min'] = sum(o.get('duracion_min') or 0 for o in reg['obras'])
        if t in INSCRIPCION:
            reg['acceso'] = 'Entrada libre con inscripción previa'
            reg['registration_url'] = INSCRIPCION[t]
        if t in SINOPSIS_TALLER:
            reg['sinopsis'] = SINOPSIS_TALLER[t]
        if t in SINOPSIS_DE_OTRA_FUENTE:
            reg['sinopsis'] = SINOPSIS_DE_OTRA_FUENTE[t]
        # varias sesiones del mismo taller = UN bloque (PROTOCOLO §4)
        if sum(1 for x in ojos if TITULO_UNIFICADO.get(x['titulo'], x['titulo']) == t) > 1 and t in ACTIVIDAD:
            reg['is_recurring'] = True
        # el renglón que la lámina pone bajo un PROGRAMA es texto del festival
        # (no a las actividades: el renglón de un taller es «Taller: … Sesión 01 …»,
        # distinto en cada sesión, y un bloque recurrente lleva UNA sinopsis)
        if (not catalogo.get(t) and not a.get('obras') and not a.get('invitados')
                and t not in ACTIVIDAD and not reg.get('sinopsis') and a.get('credito')):
            c = a['credito'].strip().capitalize()
            reg['sinopsis'] = c if c.endswith('.') else c + '.'
        funciones.append(reg)

    duracion_sin_dato(funciones)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @mamut_festival — el carrusel de programación (11 láminas)',
            que_aporta='la programación entera: día, hora, lugar y créditos',
            url=f'https://www.instagram.com/p/{POST}/',
            metodo='lectura a ojo lámina por lámina, confirmada con la OCR de cajas '
                   'de las mismas láminas, en los dos sentidos'),
        '_excluidas': {'funciones': fuera, 'por_que': EXCLUIDOS},
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} actividades ({len(funciones) - n_ev} proyecciones + {n_ev} '
          f'actividades) · {len({f["sede"] for f in funciones})} sedes · '
          f'fuera por convocatoria cerrada: {len(fuera)} → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
