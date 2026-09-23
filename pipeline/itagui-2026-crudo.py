#!/usr/bin/env python3
"""itagui-2026-crudo.py — parrilla → formato intermedio (PROTOCOLO §4).

La parrilla sale de las 15 láminas de Instagram, leídas con cajas. Este paso
solo TRADUCE al formato que comen las herramientas genéricas y toma las cuatro
decisiones de contenido que no son del parser.

Esc.  festivals/staging/itagui-2026-crudo.json
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance, DESCONOCIDO  # noqa: E402

PARR = f'{REPO}/festivals/staging/itagui-2026-parrilla.json'
OUT = f'{REPO}/festivals/staging/itagui-2026-crudo.json'

# ── 1 · LA TABLA DE SEDES, a mano y explícita (PROTOCOLO §3) ────────────────
# La lámina imprime el nombre y la dirección de cada una. El nombre corto es el
# que va en la app; el largo del CAMI —«Centro Administrativo Municipal de
# Itagüí (CAMI)»— es el edificio, no el lugar al que va la gente.
SEDES = {
    'Teatro Caribe':                       'Teatro Caribe',
    'Teatro del Norte':                    'Teatro del Norte',
    'Cinemas de la empresa Royal Films':   'Royal Films Plaza Arrayanes',
    'Auditorio Juan Carlos Escobar':       'Auditorio Juan Carlos Escobar',
    'Auditorio Cultural Diego Echavarría Misas': 'Auditorio Diego Echavarría Misas',
    'I.E. Luis Carlos Galán':              'I.E. Luis Carlos Galán',
    'Cineprox':                            'Cineprox Mayorca',
}

# ── 2 · QUÉ ES CADA COSA QUE NO ES UNA PROYECCIÓN ──────────────────────────
# `event_kind` es la palabra del FESTIVAL, no la nuestra: la lámina dice
# «Conversatorio», «Evento», «Visita guiada», «Torneo», «Concierto de
# inauguración». Traducirlas acá es el error que llenó FICDEH de «PONENCIA».
ACTIVIDAD = [
    (r'^Torneo del juego',        'torneo'),
    (r'^Visita guiada',           'visita guiada'),
    (r'^Sección de cortometrajes', 'evento'),
    (r'^Concierto de inauguración', 'apertura'),
    (r'^La literatura en el cine', 'conversatorio'),
    (r'^Fausto, una vida',        'conversatorio'),
]

# ── 3 · LOS DOS RÓTULOS QUE NO SON SECCIÓN ─────────────────────────────────
# La lámina los pinta donde van las secciones, pero no lo son: «CONVERSATORIO:»
# rotula una actividad y la línea de INAUGURACIÓN anuncia el acto de apertura.
# Meterlos en `sections` inventaría dos secciones que el festival no tiene.
NO_ES_SECCION = ('CONVERSATORIO:', 'INAUGURACIÓN DEL 9°')

# ── 4 · EL ACCESO, declarado (PROTOCOLO §4) ────────────────────────────────
# El festival NO publica cómo se entra. Mirado el 23 sep 2026 en: las 15 láminas
# del carrusel de programación (una por una), el PDF oficial de programación de
# institutoitagui.gov.co (15 páginas, texto seleccionable — la única aparición de
# «precio» es la película «Piedras preciosas»), la portada de ese mismo sitio y
# la bio y los posts de @festicineoficial y @institutoitagui.
# Dos de sus siete sedes son cines comerciales (Royal Films, Cineprox), así que
# «es municipal, será gratis» sería una suposición nuestra, no un dato.
# LO QUE EL FESTIVAL SÍ DICE, y lo dice en OTRA serie. @festicineoficial
# publicó la misma programación del día 1 con un diseño distinto
# (instagram.com/p/DdhkrlBD6Xw/, 10 láminas verdes), y ahí, en la lámina de la
# inauguración: «Entrada libre con boletería entregada media hora antes del
# evento en las taquillas del teatro». Leído a ojo sobre la imagen.
#
# Se aplica SOLO a la inauguración, que es donde está escrito. Esa serie cubre
# únicamente el día 1 y las demás láminas no lo repiten; extenderlo a las 37
# funciones sería nuestra suposición, no su dato — y dos de sus sedes son cines
# comerciales.
ACCESO_INAUGURACION = ('Entrada libre con boletería entregada media hora antes '
                       'del evento en las taquillas del teatro')

_ACCESO = {
    'estado': DESCONOCIDO,
    'revisado': '2026-09-23',
    'fuentes': [
        'las 15 láminas del carrusel de programación (instagram.com/p/DdmhX7gFIZa/)',
        'el PDF oficial: institutoitagui.gov.co/uploads/ckbox/FESTIVAL DE CINE/'
        'programacion_festival_de_cine_2026.pdf (15 páginas con texto)',
        'institutoitagui.gov.co (portada)',
        '@festicineoficial y @institutoitagui (bio y posts de la edición)',
    ],
    '_por_que': 'Dos de las siete sedes son cines comerciales: suponer que es '
                'gratis por ser un festival municipal sería inventarlo.',
}


# Los dos títulos que la lámina imprime sin rótulos, partidos a ojo:
# título de verdad + lo que el festival escribe debajo.
TITULO_PARTIDO = {
    ('La literatura en el cine de Harold Trompetero Lanzamiento del libro Lactar '
     'del escritor, director y productor de cine Harold Trompetero Rafael Aguirre '
     '(escritor), Heidy Carrasco (actriz) y Harold Trompetero (escritor y director '
     'de cine)'): (
        'La literatura en el cine de Harold Trompetero',
        'Lanzamiento del libro Lactar, del escritor, director y productor de cine '
        'Harold Trompetero. Invitados: Rafael Aguirre (escritor), Heidy Carrasco '
        '(actriz) y Harold Trompetero (escritor y director de cine).'),
    ('Torneo del juego de TCG "Magic The Gathering" en las modalidades tradicional '
     '(principiante y avanzado) y Commander (avanzado, hasta brackets 3)'): (
        'Torneo del juego de TCG Magic The Gathering',
        'En las modalidades tradicional (principiante y avanzado) y Commander '
        '(avanzado, hasta brackets 3).'),
}



# La duración de una actividad, cuando el festival no la imprime.
#
# REGLA (Juan, 23 sep 2026): el HUECO HASTA LA SIGUIENTE FUNCIÓN EN LA MISMA
# SEDE. No es una suposición nuestra: es el propio horario del festival diciendo
# hasta cuándo ocupa la sala. Encaja fino donde más importa —el concierto de
# inauguración da 40 minutos, que es exactamente lo que dura hasta «Leonel»— y
# es lo que el plan necesita para no ofrecer dos cosas encima.
#
# Las tres que CIERRAN su sede no tienen siguiente, así que no hay horario que
# leer. Ahí va un valor declarado, y se declara: 90 minutos, marcado con
# `_duracion_inferida` para que se vea que lo pusimos nosotros y se corrija el
# día que el festival lo publique.
DURACION_POR_DEFECTO = 90


def duracion_de_actividades(funciones):
    def mins(h):
        a, b = h.split(':')
        return int(a) * 60 + int(b)
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede']
                     and mins(g['hora']) > mins(f['hora']))
        if sig:
            f['duracion_min'] = sig[0] - mins(f['hora'])
            f['_duracion_de'] = 'el hueco hasta la siguiente función en la misma sede'
        else:
            f['duracion_min'] = DURACION_POR_DEFECTO
            f['_duracion_de'] = (f'{DURACION_POR_DEFECTO} min declarados: cierra su '
                                 f'sede ese día, así que no hay horario que leer')
    return funciones


def main():
    parr = json.load(open(PARR, encoding='utf-8'))
    funciones = []
    for f in parr['funciones']:
        sede = SEDES.get(f.get('sede'))
        if not sede:
            sys.exit(f'✗ sede sin entrada en la tabla: {f.get("sede")!r} — la '
                     f'tabla es explícita a propósito (PROTOCOLO §3)')
        reg = {'titulo': f['titulo'], 'dia': f['dia'], 'hora': f['hora'],
               'sede': sede, 'acceso': DESCONOCIDO,
               '_src': {'url': 'https://www.instagram.com/p/DdmhX7gFIZa/',
                        'date': '2026-09-22'}}
        sec = f.get('seccion')
        if sec and not sec.startswith(NO_ES_SECCION):
            reg['seccion'] = sec
        for orig, dest in (('pais', 'pais'), ('director', 'director'),
                           ('duracion_min', 'duracion_min'),
                           ('titulo_original', 'titulo_original')):
            if f.get(orig):
                reg[dest] = f[orig]
        if f.get('has_qa'):
            reg['has_qa'] = True
            reg['qa_type'] = f.get('qa_type') or 'team'
        # «Actividad complementaria: Conversatorio al final de la película» ES
        # un Q&A, y el festival lo escribe en 22 de las 37. Sin esto la app
        # calcula los cruces sin contar la conversación de después.
        comp = (f.get('complementaria') or '')
        if re.search(r'conversatorio', comp, re.I):
            reg['has_qa'] = True
            reg.setdefault('qa_type', 'team')
        if re.match(r'^Concierto de inauguración', f['titulo'] or '', re.I):
            reg['acceso'] = 'Entrada libre'
            reg['sinopsis'] = ACCESO_INAUGURACION + '.'
        for pat, kind in ACTIVIDAD:
            if re.search(pat, f['titulo'] or '', re.I):
                reg['tipo'] = 'evento'
                reg['event_kind'] = kind
                break
        # LOS INVITADOS SON DATO, no adorno: la lámina nombra a quién va a estar
        # —el director, el actor, el equipo—, y es la razón por la que alguien
        # elige una función sobre otra. Van a la descripción con la palabra del
        # festival, que es «Invitado especial» / «Invitados especiales».
        # UN TÍTULO NO ES UNA TARJETA. Dos láminas no traen ningún campo con
        # rótulo conocido, así que el parser metió TODO en el título y salían
        # nombres de 180 caracteres. Se parten A MANO, leyendo la lámina: una
        # regla sobre prosa cortó «La literatura en el cine de» / «Harold
        # Trompetero…», que es peor que no cortar.
        corte = TITULO_PARTIDO.get(reg['titulo'])
        if corte:
            reg['titulo'], reg['_cola_titulo'] = corte

        inv = (f.get('invitados') or '').strip(' .')
        _desc = [x for x in (reg.pop('_cola_titulo', None),
                             f'Invitados: {inv}.' if inv else None) if x]
        if _desc:
            reg['sinopsis'] = ' '.join(_desc)
        funciones.append(reg)

    duracion_de_actividades(funciones)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @institutoitagui — el carrusel de 15 láminas de '
            'programación, y el PDF oficial de institutoitagui.gov.co',
            que_aporta='la programación entera: día, hora, sede, sección y ficha',
            url='https://www.instagram.com/p/DdmhX7gFIZa/',
            metodo='OCR con cajas sobre las láminas, verificado contra la '
                   'lectura a ojo función por función Y contra el PDF oficial, '
                   'donde aparecen los 37 títulos'),
        '_acceso': _ACCESO,
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones · {len({f["sede"] for f in funciones})} sedes '
          f'· {sum(1 for f in funciones if f.get("has_qa"))} con conversatorio '
          f'· {sum(1 for f in funciones if f.get("tipo") == "evento")} actividades → {OUT}')


if __name__ == '__main__':
    main()
