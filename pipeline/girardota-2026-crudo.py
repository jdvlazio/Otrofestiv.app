#!/usr/bin/env python3
"""girardota-2026-crudo.py — la programación del 9° Festival Audiovisual de Girardota → crudo.

LA FUENTE es el carrusel de programación de @girardotaescultura (la cuenta de
cultura del municipio), `p/DdnD4hjHHnq` del 22 sep 2026: cinco láminas, la 1 de
portada y la 5 con los logos al pie. Cada actividad trae su rótulo —la palabra del
festival: «Proyección», «Taller», «Conversatorio», «Show de danza»…—, su título,
su lugar y su hora, y las proyecciones también año, dirección y duración.

DOS LECTURAS, como Mamut: la transcripción A OJO (fuentes/girardota-2026-ojos.json),
que es lo que se publica, y el OCR de las mismas láminas, que tiene que
encontrar cada título y cada hora en SU lámina. Si el OCR no confirma, el paso
falla.

LO QUE LAS LÁMINAS NO DICEN, y no se inventa:
  · cómo se entra — ver _ACCESO;
  · la dirección de ninguna sede — la tabla SEDES solo da el nombre, y el pin se
    resuelve en el paso de geocodificación, cruzado contra Google (cicatriz de
    Jahel, Jardín);
  · la duración de las actividades y de los tres programas de cortos: la de un
    taller sale de su «3:00 a 6:00»; las demás, del hueco hasta la siguiente
    actividad EN LA MISMA SEDE, la regla que Juan aprobó para Itagüí.
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
from lib import DESCONOCIDO, provenance  # noqa: E402

FID = 'girardota-2026'
POST = 'DdnD4hjHHnq'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
OJOS = f'{REPO}/fuentes/{FID}-ojos.json'
OUT = f'{REPO}/festivals/staging/{FID}-crudo.json'
DURACION_POR_DEFECTO = 90

# ── 1 · QUÉ ES CADA RÓTULO ─────────────────────────────────────────────────
# El rótulo es la palabra del festival y se respeta: `event_kind` es esa palabra
# en minúscula. Lo que el rótulo agrega a una proyección —«inaugural», «y
# conversatorio con la directora»— va a sus campos, no al título.
PROYECCION = {'Proyección', 'Proyección inaugural y conversatorio con la directora',
              'Proyección y social al parque'}
ACTIVIDAD = {   # rótulo → event_kind
    'Taller': 'taller',
    'Conversatorio': 'conversatorio',
    'Lanzamiento de libro y conversatorio con Vincent Gil y Cristián Jaramillo':
        'lanzamiento de libro',
    'Show de danza': 'show de danza',
    'Acto': 'acto',
    'Fiesta': 'fiesta',
    'Social al parque': 'social al parque',
}
# lo que el rótulo del lanzamiento nombra además de la actividad
INVITADOS_EN_EL_ROTULO = {
    'Lanzamiento de libro y conversatorio con Vincent Gil y Cristián Jaramillo':
        'Vincent Gil y Cristián Jaramillo',
}

# EL AÑO QUE LA LÁMINA IMPRIME MAL. No es vocabulario del festival: es un hecho
# sobre una película ajena, comprobable fuera. Tabla y no regla.
#   · «El libro de Lila» sale «(1986)» en la lámina 5, y la película de Marcela
#     Rincón es de 2017: TMDB 478795 (estreno 28 sep 2017, 76 min, Colombia y
#     Uruguay), la misma directora y la misma duración que imprime la lámina.
#     El 1986 parece arrastrado de «La mansión de Araucaima», que va en la
#     lámina anterior con ese año.
ANIO_ERRATA = {'El libro de Lila': 2017}

# ── 2 · LAS SEDES, en tabla ────────────────────────────────────────────────
# El nombre que imprime la lámina, tal cual. Ninguna lámina da direcciones.
SEDES = {
    'Comfama': 'Comfama',
    'Punto de Turismo': 'Punto de Turismo',
    'Palmas del Llano': 'Palmas del Llano',
    'I.E. San Andrés': 'I.E. San Andrés',
    'Biblioteca Municipal Alberto Aguirre Ceballos': 'Biblioteca Municipal Alberto Aguirre Ceballos',
    'Morning': 'Morning',
    'Escuela de Encenillos': 'Escuela de Encenillos',
    'Parque de la Poesía': 'Parque de la Poesía',
    'Parque Principal': 'Parque Principal',
}

# ── 3 · LAS SECCIONES ──────────────────────────────────────────────────────
# El festival no agrupa por secciones: rotula cada actividad. Se publican dos,
# como en Itagüí: las proyecciones y lo demás. Las dos palabras son nuestras y
# están pendientes del visto bueno de Juan.
SECCION_PROYECCION = 'Proyecciones'
SECCION_ACTIVIDAD = 'Actividades'

# ── 4 · EL ACCESO, declarado (PROTOCOLO §4) ────────────────────────────────
# El festival no publica cómo se entra. Mirado el 27 sep 2026 en: las 5 láminas
# del carrusel de programación, el afiche (@girardotaescultura p/DdSaAR7Jbua, con
# su pie) y el perfil y los posts de @festigirardota. Ninguno dice «entrada
# libre», ni precio, ni inscripción. Que sea un festival municipal no lo hace
# gratis: una de sus sedes es un bar (Morning) y otra una caja de compensación
# (Comfama).
_ACCESO = {
    'estado': DESCONOCIDO,
    'revisado': '2026-09-27',
    'fuentes': [
        'las 5 láminas del carrusel de programación (instagram.com/p/DdnD4hjHHnq/)',
        'el afiche y su pie (instagram.com/p/DdSaAR7Jbua/)',
        '@festigirardota (perfil y posts de la edición)',
    ],
    '_por_que': 'Ninguna fuente lo dice, y entre sus sedes hay un bar y una caja '
                'de compensación: suponer que es gratis sería inventarlo.',
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def ocr(n):
    r = subprocess.run(['swift', f'{REPO}/pipeline/ocr.swift', f'{LAMINAS}/{n:02d}.jpg'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ el OCR de la lámina {n} falló: {r.stderr[:200]}')
    return plano(' '.join(json.loads(r.stdout)['lineas']))


def hora_ocr(h):
    """«15:00» → «3 00» (así la imprime la lámina: «3:00 p.m.»)."""
    a, b = map(int, h.split(':'))
    return f'{a - 12 if a > 12 else a} {b:02d}'


def verifica(ojos):
    """Cada título (sus palabras, en orden) y cada hora, en SU lámina."""
    texto = {n: ocr(n) for n in sorted({f['lamina'] for f in ojos})}
    fallos = []
    for f in ojos:
        t = texto[f['lamina']]
        # LAS PALABRAS, NO SU ORDEN. Las láminas van a dos columnas y el OCR
        # mezcla renglones de una y otra: leyó «películas: Alberto Aguirre
        # Ceballos» (título + sede) y partió «El gótico / popular:» con otra
        # línea en medio. Se exige que TODA palabra de 4+ letras del título
        # esté en su lámina; la hora se sigue exigiendo aparte.
        palabras = set(t.split())
        faltan = [w for w in plano(f['titulo']).split() if len(w) >= 4 and w not in palabras]
        if faltan:
            fallos.append(f'«{f["titulo"]}»: el OCR no encuentra {faltan} en la lámina {f["lamina"]}')
        if hora_ocr(f['hora']) not in t:
            fallos.append(f'«{f["titulo"]}» {f["hora"]}: el OCR no encuentra la hora en la lámina {f["lamina"]}')
    return fallos


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def duracion_de_actividades(funciones):
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede']
                     and mins(g['hora']) > mins(f['hora']))
        if sig:
            f['duracion_min'] = sig[0] - mins(f['hora'])
            f['_duracion_de'] = 'el hueco hasta la siguiente actividad en la misma sede'
        else:
            f['duracion_min'] = DURACION_POR_DEFECTO
            f['_duracion_de'] = (f'{DURACION_POR_DEFECTO} min declarados: cierra su sede '
                                 'ese día, así que no hay horario que leer')


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['funciones']
    fallos = verifica(ojos)
    if fallos:
        sys.exit('✗ la transcripción y el OCR no coinciden:\n  · ' + '\n  · '.join(fallos))

    funciones = []
    for f in ojos:
        rot = f['rotulo']
        if f['sede'] not in SEDES:
            sys.exit(f'✗ sede sin entrada en la tabla: {f["sede"]!r} — la tabla es explícita a propósito')
        reg = {'titulo': f['titulo'], 'dia': f['dia'], 'hora': f['hora'],
               'sede': SEDES[f['sede']], 'acceso': DESCONOCIDO,
               '_src': {'url': f'https://www.instagram.com/p/{POST}/', 'date': '2026-09-22'}}
        if rot in PROYECCION:
            reg['seccion'] = SECCION_PROYECCION
            for c in ('director', 'anio', 'duracion_min'):
                if f.get(c):
                    reg[c] = f[c]
            if f['titulo'] in ANIO_ERRATA:
                reg['anio'] = ANIO_ERRATA[f['titulo']]
            if 'inaugural' in rot:
                reg['premiere'] = 'Proyección inaugural'
            if 'conversatorio' in rot:
                reg['has_qa'] = True
                reg['qa_type'] = 'team'      # «con la directora»: el equipo de la obra
        elif rot in ACTIVIDAD:
            reg['tipo'] = 'evento'
            reg['event_kind'] = ACTIVIDAD[rot]
            reg['seccion'] = SECCION_ACTIVIDAD
            if f.get('hora_fin'):
                reg['duracion_min'] = mins(f['hora_fin']) - mins(f['hora'])
            if rot in INVITADOS_EN_EL_ROTULO:
                reg['invitados'] = f'Invitados: {INVITADOS_EN_EL_ROTULO[rot]}.'
        else:
            sys.exit(f'✗ rótulo sin clasificar: {rot!r} — agregarlo a PROYECCION o ACTIVIDAD')
        # el renglón que acompaña al título: quién da el taller, quién conversa,
        # de qué editorial es el libro. Es texto del festival: va a la descripción.
        if f.get('credito'):
            c = f['credito'].strip()
            reg['sinopsis'] = c if c.endswith('.') else c + '.'
        funciones.append(reg)

    duracion_de_actividades(funciones)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @girardotaescultura — el carrusel de programación (5 láminas)',
            que_aporta='la programación entera: día, hora, lugar, rótulo y ficha',
            url=f'https://www.instagram.com/p/{POST}/',
            metodo='transcripción a ojo lámina por lámina, confirmada título por '
                   'título y hora por hora con el OCR de las mismas láminas'),
        '_acceso': _ACCESO,
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} actividades ({len(funciones) - n_ev} proyecciones + {n_ev} '
          f'actividades) · {len({f["sede"] for f in funciones})} sedes · 5 días · '
          f'OCR de acuerdo en las {len(funciones)} → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
