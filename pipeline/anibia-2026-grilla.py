#!/usr/bin/env python3
"""anibia-2026-grilla.py — BORRADOR del crudo de ANIBIA 2026 (20 oct–1 nov).
PRE-ONBOARDING: no lo lee ningún paso todavía; es la parrilla transcrita para
que el montaje solo tenga que confirmarla.

LAS FUENTES (fuentes/anibia-2026/, 21 oct 2026):
  · programacion.pdf — la programación oficial (Linktree), con texto: es el
    mismo diseño que el carrusel de IG DeQG0NPGy2f (13 láminas, fuentes/ig/).
    Da día, hora, sede, acceso y edad. Se transcribió A MANO (abajo, FUNCIONES).
  · agenda-11.html / agenda-80.html / agenda-112.html — la agenda de la
    Cinemateca (Centro, Fontanar del Río, CEFE Chapinero). Da la SALA, que el
    PDF no trae, y es la verificación independiente de día y hora: el script
    FRENA si una función de la Cinemateca no aparece en su agenda a esa hora.
    (Las del Centro anteriores al 21 oct ya no salen en la agenda.)

Escribe festivals/staging/anibia-2026-grilla.json
"""
import html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance, DESCONOCIDO  # noqa: E402

SRC = f'{REPO}/fuentes/anibia-2026'
OUT = f'{REPO}/festivals/staging/anibia-2026-grilla.json'

# Pines: Google Maps, navegador integrado, 21 oct 2026 (_prec manual)
SEDES = {
    'Cinemateca de Bogotá - Bogotá': {'lat': 4.6031614, 'lng': -74.0676717, 'address': 'Cra. 3 # 19-10',
                                      '_prec': 'manual', '_gmaps': 'Cinemateca de Bogotá'},
    'Cinemateca Fontanar del Río - Bogotá': {'lat': 4.7561244, 'lng': -74.1110572, 'address': 'Calle 146 # 138A-99',
                                             '_prec': 'manual', '_gmaps': 'CEFE Fontanar del río'},
    'CEFE Chapinero - Bogotá': {'lat': 4.6654518, 'lng': -74.0527949, 'address': 'Calle 82 # 10-69',
                                '_prec': 'manual', '_gmaps': 'Cefe Chapinero'},
    'Universidad Nacional, Edificio 303 (NEA) - Bogotá': {
        'lat': 4.6370447, 'lng': -74.0816443, 'address': 'Av. Cra. 30 # 45-03',
        '_prec': 'manual', '_gmaps': '303C - Espacios para las Artes',
        '_nota': 'la Cinemateca Sala Alterna UNAL ES el Auditorio 422 del 303C (Facultad de Artes); '
                 'el Aula Múltiple 105 del Bloque A está en el mismo edificio: una sede, tres salas'},
    'Universidad Jorge Tadeo Lozano, Ed. Biblioteca - Bogotá': {
        'lat': 4.6063616, 'lng': -74.0673857, 'address': 'Cra. 4 # 22-40',
        '_prec': 'manual', '_gmaps': 'Auditorio Fabio Lozano - Universidad Jorge Tadeo Lozano'},
    'Universidad Jorge Tadeo Lozano, Módulo 4 - Bogotá': {
        'lat': 4.606567, 'lng': -74.067801, 'address': 'Cra. 4 # 22-40 (entrada calle 23)',
        '_prec': 'manual', '_gmaps': 'Universidad de Bogotá Jorge Tadeo Lozano',
        '_nota': 'APROXIMADO: el Módulo 4 no tiene pin propio en Google Maps; pin del campus (a ~25 m del Fabio Lozano). '
                 'Se declara con nota por [sedes-apiladas]'},
    'Pontificia Universidad Javeriana, Ed. Gerardo Arango - Bogotá': {
        'lat': 4.626481, 'lng': -74.0644571, 'address': 'Calle 40B # 5-37',
        '_prec': 'manual', '_gmaps': 'Edificio Gerardo Arango S,J. - Facultad de Artes'},
    'Pontificia Universidad Javeriana, Edificio Ático - Bogotá': {
        'lat': 4.6268009, 'lng': -74.0650103, 'address': 'Calle 40B # 6-23',
        '_prec': 'manual', '_gmaps': 'Edificio Atico'},
}
LIBRE = 'Entrada libre / hasta completa aforo'
ALIADOS = 'Evento para aliados'
CIN, FON = 'Cinemateca de Bogotá - Bogotá', 'Cinemateca Fontanar del Río - Bogotá'
NAL, TAD4 = 'Universidad Nacional, Edificio 303 (NEA) - Bogotá', 'Universidad Jorge Tadeo Lozano, Módulo 4 - Bogotá'
JAV = 'Pontificia Universidad Javeriana, Ed. Gerardo Arango - Bogotá'
ATI = 'Pontificia Universidad Javeriana, Edificio Ático - Bogotá'

# (día, hora, hora_fin, título VERBATIM del PDF, tipo, sede, sala, acceso, edad, nodo Cinemateca, nota)
F = [
    ('2026-10-20', '15:00', '', 'Las orejas no tienen párpados', 'Cine concierto & panel',
     'Universidad Jorge Tadeo Lozano, Ed. Biblioteca - Bogotá', 'Auditorio Fabio Lozano', LIBRE, None, None,
     'En alianza entre el Festival Eureka, el Festival Anibia y la Universidad Jorge Tadeo Lozano'),
    ('2026-10-21', '09:00', '12:00', 'Un arból que . . .', 'Taller Anibia-ASIFA', None, '', ALIADOS, None, None,
     'taller del 21 al 23 oct (3 sesiones), con el apoyo de Caballo Loco Studio; el PDF no da sede'),
    ('2026-10-22', '09:00', '12:00', 'Un arból que . . .', 'Taller Anibia-ASIFA', None, '', ALIADOS, None, None, 'sesión 2 de 3'),
    ('2026-10-23', '09:00', '12:00', 'Un arból que . . .', 'Taller Anibia-ASIFA', None, '', ALIADOS, None, None, 'sesión 3 de 3'),
    ('2026-10-21', '19:00', '', 'El hijo de puta (O filho da puta)', 'Surgentes - Película inaugural', CIN, None,
     'Entrada libre / hasta completa aforo. Entrega de boletería una hora antes de la función', 15, 3590,
     'edad: la ficha de la Cinemateca dice «Apta para mayores de 15 años»; el PDF no la da'),
    ('2026-10-22', '16:00', '', 'Surgentes - Animage', 'Proyección', CIN, None, DESCONOCIDO, 12, 3591, None),
    ('2026-10-22', '17:00', '', 'Surgentes - Con extremos', 'Proyección', CIN, None, DESCONOCIDO, 12, 3592, None),
    ('2026-10-22', '17:30', '', 'Mukira', 'Todxs a bordo - Estreno nacional', 'CEFE Chapinero - Bogotá', '', LIBRE, 12, 3513,
     'Proyección con presencia del equipo. Hablada en español'),
    ('2026-10-22', '19:30', '', 'Conexión - Foco Pez Dorado', 'Proyección', CIN, None, DESCONOCIDO, 12, 3593,
     'Proyección con presencia del equipo'),
    ('2026-10-23', '16:00', '', 'Con acento nacional - Procesos de formación - Programa 1', 'Proyección', CIN, None, DESCONOCIDO, 12, 3594, None),
    ('2026-10-23', '17:00', '', 'Con acento nacional - Profesional - Programa 1', 'Proyección', CIN, None, DESCONOCIDO, 12, 3595, None),
    ('2026-10-23', '19:30', '', 'Surgentes - Miyu', 'Proyección', CIN, None, DESCONOCIDO, 12, 3596, None),
    ('2026-10-24', '14:00', '', 'Surgentes - Animage', 'Proyección', CIN, None, DESCONOCIDO, 12, 3591, None),
    ('2026-10-24', '15:30', '', 'Costa a costa - Lo mejor de Annecy 2026', 'Proyección', CIN, None, DESCONOCIDO, 12, 3692, None),
    ('2026-10-24', '16:00', '', 'Costa a costa', 'Proyección', CIN, None, DESCONOCIDO, 12, 3616, None),
    ('2026-10-24', '17:30', '', 'Con acento nacional - Procesos de formación - Programa 2', 'Proyección', CIN, None, DESCONOCIDO, 12, 3617, None),
    ('2026-10-24', '20:00', '', 'Con acento nacional - Profesional - Programa 2', 'Proyección', CIN, None, DESCONOCIDO, 12, 3618, None),
    ('2026-10-25', '14:00', '', 'Costa a costa', 'Proyección', CIN, None, DESCONOCIDO, 12, 3616, None),
    ('2026-10-25', '16:00', '', 'Con acento nacional - Profesional - Programa 1', 'Proyección', CIN, None, DESCONOCIDO, 12, 3595, None),
    ('2026-10-25', '17:30', '', 'Con acento nacional - Profesional - Programa 2', 'Proyección', CIN, None, DESCONOCIDO, 12, 3618, None),
    ('2026-10-25', '19:30', '', 'Costa a costa - Lo mejor de Annecy 2026', 'Proyección', CIN, None, DESCONOCIDO, 12, 3692, None),
    ('2026-10-27', '14:00', '', 'Con acento nacional - Procesos de formación - Programa 1', 'Proyección', TAD4,
     'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None,
     'DUDA: la lámina pone la sede una sola vez, bajo «Entrega de reconocimientos»; se lee como sede de los tres bloques'),
    ('2026-10-27', '15:30', '', 'Con acento nacional - Procesos de formación - Programa 2', 'Proyección', TAD4,
     'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None, 'ver la duda del Programa 1'),
    ('2026-10-27', '17:30', '', 'Entrega de reconocimientos', 'Premiación', TAD4, 'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None,
     'Módulo 4, planta baja, entrada calle 23'),
    ('2026-10-27', '18:30', '', 'Surgentes - Animage', 'Proyección', NAL, 'Cinemateca Sala Alterna UNAL', LIBRE, None, None,
     'el PDF da la dirección Av Cra 30 # 45-3; la Sala Alterna es el Auditorio 422 del 303C'),
    ('2026-10-28', '13:00', '17:00', 'Reel / WIP Day', 'Día Internacional de la Animación', NAL,
     'Bloque A, Aula Múltiple 105', ALIADOS, None, None,
     'Profesionales y estudios observan los reels y proyectos en progreso (wips) de artistas noveles'),
    ('2026-10-28', '17:00', '', 'Caballo Loco Studio: Crear antes de animar', 'Charla', NAL, 'Bloque C, Auditorio 422', LIBRE, None, None, None),
    ('2026-10-30', '16:00', '', 'Mi papá el camión', 'Conexión de largo aliento', ATI, 'Auditorio piso 5', LIBRE, None, None,
     'Pez Dorado. Conversación sobre el inicio de la producción de un largometraje'),
    ('2026-10-30', '18:00', '', 'Desechable', 'Conexión de largo aliento', ATI, 'Auditorio piso 5', LIBRE, None, None,
     'Nocroma. Conversación sobre el inicio de la producción de un largometraje'),
    ('2026-10-31', '16:00', '', 'Surgentes - Animage', 'Proyección', FON, '', LIBRE, 12, 3579,
     'DUDA DE HORA: el PDF dice 4:00 p.m.; la agenda de la Cinemateca (Fontanar, ficha 3579) dice 2:00 pm'),
    ('2026-11-01', '14:00', '', 'Surgentes - Con extremos', 'Proyección', FON, '', LIBRE, 12, None,
     'todavía no está en la agenda de Fontanar (21 oct)'),
]
# La exposición: 22 oct–13 nov, 8:00–17:00 (el PDF la repite cada día del festival)
EXPO = {'titulo': 'Una vez en un cuerpo: Habitar la imagen', 'tipo': 'Exposición', 'desde': '2026-10-22',
        'hasta': '2026-11-13', 'hora': '08:00', 'hora_fin': '17:00', 'sede': JAV,
        'sala': 'Hall entrada admin. Facultad de Artes', 'acceso': 'Entrada libre'}


def agenda():
    """{(nodo, 'AAAA-MM-DD', 'HH:MM'): sala} de las agendas bajadas."""
    out = {}
    meses = {'Octubre': '10', 'Noviembre': '11', 'Diciembre': '12'}
    for s in (11, 80, 112):
        d = open(f'{SRC}/agenda-{s}.html', encoding='utf-8').read()
        for it in d.split('views-view-responsive-grid__item-inner')[1:]:
            n = re.search(r'peliculas/(\d+)', it)
            sala = re.search(r"funcion-sala'>([^<]*)", it)
            f = re.search(r"funcion-fecha'>(\w+) (\d+)", it)
            h = re.search(r"funcion-hora'>(\d+):(\d+) (am|pm)", it)
            if not (n and f and h):
                continue
            hh = int(h[1]) % 12 + (12 if h[3] == 'pm' else 0)
            out[(int(n[1]), f'2026-{meses[f[1]]}-{int(f[2]):02d}', f'{hh:02d}:{h[2]}')] = html.unescape(sala[1]).strip()
    return out


def main():
    ag = agenda()
    funciones, dudas = [], []
    for dia, hora, fin, tit, tipo, sede, sala, acceso, edad, nodo, nota in F:
        if sede is not None and sede not in SEDES:
            sys.exit(f'✗ sede sin pin: {sede}')
        f = {'titulo': tit, 'tipo': tipo, 'dia': dia, 'hora': hora, 'sede': sede or DESCONOCIDO,
             'sala': sala or '', 'ciudad': 'Bogotá', 'acceso': acceso}
        if fin:
            f['hora_fin'] = fin
        if edad:
            f['edad'] = f'Mayores de {edad} años'
        if nota:
            f['_nota'] = nota
        if nodo:
            f['_cinemateca'] = nodo
            k = (nodo, dia, hora)
            if sala is None:                       # la sala la da la agenda
                if k not in ag:
                    sys.exit(f'✗ {dia} {hora} {tit}: no está en la agenda de la Cinemateca')
                f['sala'] = ag[k]
            elif k not in ag and nodo not in (3579, 3513):
                dudas.append(f'{dia} {hora} {tit}: no está en la agenda')
            if nodo == 3513 and k not in ag:
                sys.exit('✗ Mukira (CEFE) no está en la agenda a esa hora')
        funciones.append(f)
    # que la agenda no tenga funciones de Anibia que el PDF no trae
    nodos = {x[9] for x in F if x[9]}
    pdf = {(x[9], x[0], x[1]) for x in F if x[9]}
    extra = sorted(k for k in ag if k[0] in nodos and k not in pdf)
    json.dump({'_provenance': provenance('programación PDF de Anibia 2026 (= carrusel IG DeQG0NPGy2f) + agenda de la Cinemateca de Bogotá',
                                         metodo='PDF transcrito a mano; sala y verificación de hora desde la agenda (HTML)'),
               '_nota': 'BORRADOR del crudo: pre-onboarding, no lo lee ningún paso todavía',
               '_agenda_sin_pdf': [f'{n} {d} {h} ({ag[(n, d, h)]})' for n, d, h in extra],
               'sedes': SEDES, 'exposicion': EXPO, 'funciones': funciones},
              io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(funciones)} funciones + 1 exposición → {os.path.relpath(OUT, REPO)}')
    for x in extra:
        print('  ⚠ en la agenda y no en el PDF:', x, ag[x])
    for x in dudas:
        print('  ⚠', x)


if __name__ == '__main__':
    main()
