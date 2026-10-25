#!/usr/bin/env python3
"""funza-2026-crudo.py — la agenda del 4.º Festival de Cine Funza → crudo.

LA FUENTE es «AGENDA GENERAL ACTUALIZADA – IV FESTIVAL DE CINE | 18 AL 21 DE
NOVIEMBRE DE 2026», PDF de 2 páginas con texto que el festival le mandó a Juan
(fuentes/funza-2026/agenda-2026.pdf, recibido el 25 oct 2026; tipo
festival-mensaje). 23 filas: fecha, hora, componente, actividad, duración,
observación. NO trae columna de sede: la sede es la del afiche oficial
(«CENTRO CULTURAL BACATÁ», fuentes/funza-2026/afiche-oficial.png) y la que
dijo el festival a Juan.

TRES LECTURAS INDEPENDIENTES (PROTOCOLO §2·ter):
  A · transcripción a ojo, fila por fila (fuentes/funza-2026/funza-2026-agenda-ojos.json)
      → ES la que lee este script;
  B · la capa de texto del PDF (`pdftotext -raw`);
  C · el OCR del sistema sobre las páginas renderizadas (pipeline/ocr.py).
B y C las cruza pipeline/funza-2026-verificar.py contra el BUILD.

DECISIONES (pedido de Juan, 25 oct 2026):
  · se publica lo público: inauguración (sus cuatro tramos, como actividades
    separadas — la agenda les da hora y nombre propio a cada una),
    conversatorios, proyecciones, premiación y el Encuentro Departamental
    (aperturas, paneles, conferencia, charla, rueda, cierre);
  · la LOGÍSTICA no se publica (registro, pausa de café, almuerzo);
  · los dos «Taller audiovisual escolar» (Formación descentralizada) parecen
    para colegios: no se publican salvo evidencia (DUDA abierta con Juan);
  · títulos de actividad VERBATIM; sección = el «Componente» en caja de Título;
  · las proyecciones llevan el título de la obra («Proyección Reflejos» →
    Reflejos). «HORIZONTES» es «Horizonte» (César Augusto Acevedo, 2024,
    125 min — la duración que da la propia agenda): el título de distribución,
    el mismo de guatape2026.

ACCESO: la agenda no anuncia pago → entrada libre (regla de Juan, 13 y 16
oct). El Encuentro Departamental habla de «participantes inscritos e
invitados» (fila del almuerzo): sus actividades van con inscripción previa,
sin formulario aún.

Escribe festivals/staging/funza-2026-crudo.json
"""
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'funza-2026'
OJOS = f'{REPO}/fuentes/{FID}/{FID}-agenda-ojos.json'
OUT = f'{REPO}/festivals/staging/funza-2026-crudo.json'
SEDE = 'Centro Cultural Bacatá'
SRC = {'url': 'fuentes/funza-2026/agenda-2026.pdf', 'date': '2026-10-25', 'tipo': 'festival-mensaje'}

# lo que NO se publica, con su porqué (actividad → razón)
NO_SE_PUBLICA = {
    'Registro y bienvenida': 'logística del Encuentro (registro y estación de café)',
    'Pausa de café': 'logística',
    'Almuerzo Encuentro': 'logística: «Almuerzo de participantes inscritos e invitados»',
    'Taller audiovisual escolar': 'Formación descentralizada para colegios; no consta que sea abierto (duda con Juan)',
}
# proyección → la obra
OBRAS = {
    'Proyección Reflejos': {'titulo': 'Reflejos', 'director': 'Miguel Urrutia'},
    'Proyección Basta Mamá': {'titulo': 'Basta Mamá', 'director': 'Flora Martínez'},
    'Proyección HORIZONTES': {'titulo': 'Horizonte', 'director': 'César Augusto Acevedo',
                              'titulo_fuente': 'HORIZONTES'},
}
# la clase de actividad: la palabra del festival cuando la app la conoce;
# «evento» (genérico) cuando no — panel, conferencia, performance y rueda de
# negocios no existen en _kindMapES/EN (eso es código de la app: Main)
KIND = {
    'Apertura IV Festival de Cine': 'apertura',
    'Performance en inglés: literatura que llegó al cine': 'evento',
    'Espacio de circulación e integración': 'evento',
    'Cierre jornada inaugural': 'evento',
    'Conversatorio con Miguel Urrutia': 'conversatorio',
    'Taller efectos especiales o stop motion': 'taller',
    'Apertura institucional': 'apertura',
    'Panel comunicación nuevas narrativas': 'evento',
    'Panel cine desde región': 'evento',
    'Conferencia fotografía y territorio': 'evento',
    'Charla app de festivales de cine': 'charla',
    'Rueda de negocios audiovisual': 'evento',
    'Cierre del Encuentro': 'evento',
    'Conversatorio Basta Mamá y cierre': 'conversatorio',
    'Premiación IV Festival de Cine': 'premiación',
}
# el Encuentro Departamental del 20 nov (de la apertura institucional al cierre)
ENCUENTRO = {'Apertura institucional', 'Panel comunicación nuevas narrativas',
             'Panel cine desde región', 'Conferencia fotografía y territorio',
             'Charla app de festivales de cine', 'Rueda de negocios audiovisual',
             'Cierre del Encuentro'}
MENORES = {'de', 'y', 'o', 'en', 'a', 'del', 'la', 'el', 'con'}


def seccion(componente):
    """«Exhibición cinematográfica» → «Exhibición Cinematográfica» (Título)."""
    return ' / '.join(' '.join(p if (i and p in MENORES) else p[:1].upper() + p[1:]
                               for i, p in enumerate(parte.split()))
                      for parte in componente.split(' / '))


def hora_ini(txt):
    """«4:30 p. m. – 6:30 p. m.» → '16:30'. «12:00 m.» es mediodía."""
    m = re.match(r'\s*(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?', txt)
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3)
    if ap == 'p' and h != 12:
        h += 12
    return f'{h:02d}:{mm}'


def minutos(txt):
    """«1 h 30 min» → 90 · «2h» → 120 · «88 min» → 88."""
    h = re.search(r'(\d+)\s*h', txt)
    m = re.search(r'(\d+)\s*min', txt)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def main():
    filas = json.load(io.open(OJOS, encoding='utf-8'))['filas']
    if len(filas) != 23:
        sys.exit(f'✗ la agenda trae {len(filas)} filas, no 23: revisar antes de seguir')
    funciones, fuera = [], []
    for dia, hora, comp, act, dur, obs in filas:
        if act in NO_SE_PUBLICA:
            fuera.append((dia, hora, act))
            continue
        reg = {'dia': dia, 'hora': hora_ini(hora), 'sede': SEDE,
               'acceso': ('Entrada libre con inscripción previa (participantes inscritos)'
                          if act in ENCUENTRO else 'Entrada libre (no se anuncia pago)'),
               'duracion_min': minutos(dur), 'seccion': seccion(comp),
               '_src': dict(SRC, fila=f'{hora} · {act}')}
        if act in OBRAS:
            o = OBRAS[act]
            reg.update(titulo=o['titulo'], director=o['director'], titulo_fuente=act)
            reg['_nota'] = obs
        else:
            reg.update(titulo=act, tipo='evento', event_kind=KIND[act])
            # «Instalación del 1.er Encuentro…» haría saltar [abierta-sin-info]
            # (lee «instalación» como exposición): esa observación no va de sinopsis
            if not obs.startswith('Instalación'):
                reg['sinopsis'] = obs
        funciones.append(reg)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('Agenda general actualizada del IV Festival de Cine (PDF del festival a Juan, 25 oct 2026)',
                                  metodo='transcripción a ojo fila por fila; cruzada con la capa de texto y el OCR en funza-2026-verificar.py',
                                  que_aporta='la programación entera: día, hora, componente, actividad, duración'),
        '_acceso': {'estado': 'Entrada libre', 'revisado': '2026-10-25',
                    'fuentes': ['agenda PDF del festival (25 oct 2026)', 'afiche oficial'],
                    '_por_que': 'Ninguna fuente anuncia boletería; regla de Juan: sin aviso de pago es gratis. '
                                'El Encuentro Departamental es de «participantes inscritos»: inscripción previa, sin formulario publicado.'},
        '_no_se_publica': [{'dia': d, 'hora': h, 'actividad': a, 'por_que': NO_SE_PUBLICA[a]} for d, h, a in fuera],
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("tipo") != "evento")} proyecciones) · '
          f'{len(fuera)} filas no se publican → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
