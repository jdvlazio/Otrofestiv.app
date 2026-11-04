#!/usr/bin/env python3
"""miradas-2026-formacion.py — las 5 actividades de mediación y formación de
Miradas Medellín 2026. PRE-ONBOARDING.

LA FUENTE: el carrusel Dep67rsCZmE (18 oct) de @cinematecademedellin, leído sin
sesión por el embed público. El pie nombra a Miradas («En Miradas Medellín 2026,
cinco propuestas de mediación y formación…»). Lámina 01 = portada, 07 = cierre;
02–06 = una actividad cada una.

Se TRANSCRIBEN a ojo (19 oct 2026), lámina por lámina, verbatim: título,
subtítulo, «Realizado por», descripción, lugar y horario tal cual. Las sesiones
se desglosan en (día, inicio, fin) sin interpretar nada más; el texto de la
lámina queda en `horario_lamina` para el crudo.

ACCESO: las láminas no dicen nada de pago ni de inscripción. Miradas es de
entrada libre y sin aviso de pago es gratis (regla de Juan, 13 oct). La
inscripción queda DESCONOCIDA: un taller suele pedirla y la lámina calla.

LAMINAS no es una tabla de excepciones ([excepcion-en-crudo]): es la FUENTE
principal transcrita, como HECHO_EN_MEDELLIN en el catálogo. Una corrección
posterior a una sesión va en festivals/staging/miradas2026-afirmaciones.json.

Escribe festivals/staging/miradas-2026-formacion.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/miradas-2026-formacion.json'
URL = 'https://www.instagram.com/p/Dep67rsCZmE/'
DIAS_FESTIVAL = range(3, 9)   # 3–8 de noviembre

# (lámina, título, subtítulo, realizado por, descripción, lugar, horario_lamina, sesiones[(día nov, inicio, fin)])
LAMINAS = [
    (2, 'Cine Corto detrás de cámara', None, 'Festival Cine Corto',
     'Un cineclub formativo para jóvenes que combina cortometrajes, cineforos y ejercicios prácticos para '
     'acercarse al lenguaje audiovisual y descubrir los procesos creativos detrás de la realización cinematográfica.',
     'Institución Educativa La Independencia (calle 39D # 112-81, San Javier)',
     'Miércoles 4, jueves 5 y viernes 6 de noviembre - De 10:00 a. m a 12:00 m.',
     [(4, '10:00', '12:00'), (5, '10:00', '12:00'), (6, '10:00', '12:00')]),
    (3, 'Colombia es fantástica', 'Laboratorio de cine fantástico y terror colombiano', 'Festival Fantasmagoria',
     'Un laboratorio de cinco sesiones para explorar leyendas, imaginarios y nuevas miradas del terror y el '
     'fantástico colombiano, y descubrir cómo contamos nuestros propios miedos desde el cine.',
     'Centro Colombo Americano, Aula Múltiple.',
     'Sesión 1 y 2: viernes 6 de noviembre a las 2:00 p. m. y 4:00 p. m. '
     'Sesión 3, 4 y 5: sábado 7 de noviembre a las 10:00 a. m. 2:00 p. m. y 4:00 p. m.',
     # la lámina da solo la hora de inicio de cada sesión
     [(6, '14:00', None), (6, '16:00', None), (7, '10:00', None), (7, '14:00', None), (7, '16:00', None)]),
    (4, 'La otra orilla:', 'Revolver la mirada autorizada para manchar la cámara de barro', 'Cine-Foro "En Construcción"',
     'Un taller sobre obras de cineastas mujeres latinoamericanas para explorar sus herramientas expresivas y la '
     'potencia de sus propuestas, poniendo en diálogo sus formas de hacer cine con las de sus contemporáneos.',
     'Librería y Espacio Cultural Antimateria (calle 45E # 72-09, Laureles)',
     'Martes 3, jueves 5 y sábado 7 de noviembre - De 6:00 p. m. a 8:00 p. m.',
     [(3, '18:00', '20:00'), (5, '18:00', '20:00'), (7, '18:00', '20:00')]),
    (5, 'Luces, cámara y estampa', None, 'KXVRX Cineclub',
     'Tres sesiones de mediación y formación alrededor del cortometraje colombiano, con proyecciones, '
     'conversaciones y microtalleres de serigrafía para reflexionar sobre memoria, identidad, territorio y los '
     'lugares que habitamos.',
     'Edificio Paraninfo Universidad de Antioquia (carrera 44 # 48-72, La Candelaria)',
     'Viernes 6 de noviembre, de 2:00 p. m. a 4:00 p. m. '
     'Sábado 7 de noviembre, de 10:00 a. m. a 12:00 m. y de 1:00 p. m. a 3:00 p. m.',
     [(6, '14:00', '16:00'), (7, '10:00', '12:00'), (7, '13:00', '15:00')]),
    (6, 'Rodando formación:', 'Mediaciones en comunidad', 'CorpoTEA',
     'Un espacio de encuentro con el audiovisual desde las experiencias territoriales. Comunicación, expresión y '
     'apreciación se combinan para explorar, experimentar y crear junto a las comunidades y sus distintas formas '
     'de relacionarse con el entorno.',
     'Sede cultural Casa TEA (calle 53 # 47-44, La Candelaria)',
     'Martes 3, jueves 5 y viernes 6 de noviembre, de 7:00 p. m. a 9:00 p. m. '
     'Sábado 7 de noviembre, de 6:00 p. m. a 8:00 p. m.',
     [(3, '19:00', '21:00'), (5, '19:00', '21:00'), (6, '19:00', '21:00'), (7, '18:00', '20:00')]),
]


def main():
    acts = []
    for lam, tit, sub, por, desc, lugar, horario, sesiones in LAMINAS:
        fuera = [s for s in sesiones if s[0] not in DIAS_FESTIVAL]
        if fuera:
            sys.exit(f'✗ {tit}: sesiones fuera del 3–8 nov: {fuera}')
        acts.append({'titulo_lamina': tit, 'subtitulo_lamina': sub, 'realizado_por': por,
                     'seccion_lamina': 'Mediación y formación', 'descripcion_es': desc,
                     'lugar_lamina': lugar, 'horario_lamina': horario,
                     'sesiones': [{'fecha': f'2026-11-{d:02d}', 'inicio': i, 'fin': f} for d, i, f in sesiones],
                     'acceso': {'is_free': True, '_por': 'sin aviso de pago = gratis; Miradas es de entrada libre',
                                'requires_registration': 'DESCONOCIDO'},
                     '_src': {'url': URL, 'lamina': lam, 'date': '2026-10-19'}})
    json.dump({'_provenance': provenance('@cinematecademedellin Dep67rsCZmE (embed sin sesión)',
                                         metodo='transcripción a ojo de las láminas 02–06'),
               'actividades': acts}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(acts)} actividades, {sum(len(a["sesiones"]) for a in acts)} sesiones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
