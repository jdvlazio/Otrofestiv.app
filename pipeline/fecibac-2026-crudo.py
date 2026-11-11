#!/usr/bin/env python3
"""fecibac-2026-crudo.py — la «Programación oficial» del 12 FECIBAC → crudo.

LA FUENTE son las 4 láminas del post de @festivaldecine.bc del 5 nov 2026
(instagram.com/p/DfYAPbqGyr0, copiadas a fuentes/fecibac-2026/). Transcritas a
ojo; las cruza pipeline/fecibac-2026-verificar.py contra el OCR.

DECISIONES:
  · La sección es la leyenda de la lámina; las actividades sin ícono, «Actividades».
  · «Entre dos aguas» es «Entre 2 Aguas», su título de estreno (la misma lámina
    lo escribe así en el conversatorio).
  · La selección de cortos no está publicada: las tandas van sin obras.
  · Ninguna fuente anuncia pago → entrada libre (regla de Juan, 13 oct 2026).
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/fecibac-2026-crudo.json'
POST = 'https://www.instagram.com/p/DfYAPbqGyr0/'
PLAYA, CAM, UDEA, PLAZO, MERC, BAR = ('Playa Río Cauca', 'Cámara de Comercio', 'UdeA Campus Caucasia',
                                      'Plazoleta UdeA', 'Plaza de mercado', 'Bar Yenyeré')
PEL, COR, TAL, CON, ACT = ('Proyección de Película', 'La Canoa Dorada', 'Talleres con Expertos',
                           'Conversatorios', 'Actividades')
D = '2026-11-'
# (lámina, día, hora, título, sede, sección, kind|None, extra)
F = [
 (1, '10', '17:00', 'Fiesta en el Playón', PLAYA, ACT, 'apertura', dict(sinopsis='Inauguración oficial FECIBAC 2026: Somos Chilapos.')),
 (1, '10', '18:30', 'La barca de los sueños olvidados', PLAYA, ACT, 'evento', dict(sinopsis='Espectáculo sobre el río Cauca.')),
 (1, '10', '19:00', 'La Creciente', PLAYA, 'Película Inaugural', None, dict(director='Pablo Andrés Muñoz Castrillón', clasificacion='+7')),
 (1, '10', '20:30', 'Remando con Pablo y Karla', PLAYA, CON, 'conversatorio', dict(invitados='Pablo Muñoz, director de «La Creciente», y Karla V. Corrales, productora y directora de fotografía')),
 (1, '11', '09:00', 'Narrativas chilapas', UDEA, TAL, 'taller', dict(invitados='Irina Petro de León')),
 (1, '11', '17:30', 'Los cuerpos que son caudal', CAM, ACT, 'evento', dict(sinopsis='Recital poético.', invitados='Irina Petro de León')),
 (1, '11', '19:00', 'Entre 2 Aguas', CAM, PEL, None, dict(director='Carlos Gabriel Vergara', pais='Colombia', genero='Thriller', clasificacion='+16', titulo_fuente='Entre dos aguas')),
 (1, '11', '20:30', 'Conversatorio Entre 2 Aguas', CAM, CON, 'conversatorio', dict(invitados='Los protagonistas: Nelson Camayo y María José Escorcia')),
 (2, '12', '16:00', 'El juego de la vida', CAM, PEL, None, dict(director='Mario Andrés Ruiz Zuluaga', clasificacion='+7')),
 (2, '12', '18:30', 'Brigitte Planeta B', PLAZO, PEL, None, dict(director='Santiago Posada', clasificacion='+12')),
 (2, '12', '20:30', 'Conversatorio con Brigitte Baptiste', PLAZO, CON, 'conversatorio', dict(invitados='Brigitte Baptiste, protagonista. Modera Yuliana Gómez Zapata, directora de Regionalización UdeA')),
 (2, '13', '08:00', 'Taller de creación de carteles cinematográficos para niños y niñas', UDEA, TAL, 'taller', dict(sinopsis='Un recorrido por el mundo del cine. Taller infantil Chico y Proqui.', invitados='Harold Blanco y Lenys López')),
 (2, '13', '09:00', 'Escuchando con la cámara', UDEA, TAL, 'taller', dict(sinopsis='Taller de dirección.', invitados='Sebastián Bright')),
 (2, '13', '15:00', 'Feria Chilapa', CAM, ACT, 'evento', dict(info=True, hasta='2026-11-14', sinopsis='Feria de emprendimientos de distintas zonas del país. Abierta desde las 3:00 p. m. el viernes y desde las 2:00 p. m. el sábado.')),
 (2, '13', '16:00', 'La Canoa Dorada (Tanda 1)', CAM, COR, None, dict(clasificacion='+7')),
 (2, '13', '19:00', 'En tierra', CAM, PEL, None, dict(director='Simón Uribe', clasificacion='+7')),
 (3, '13', '20:30', 'Una mirada a través del lente', CAM, CON, 'conversatorio', dict(invitados='Sebastián Bright, director de fotografía')),
 (3, '13', '22:00', 'Cine gótico popular', MERC, ACT, 'evento', dict(clasificacion='+12', sinopsis='Experiencias disruptivas en la plaza de mercado. Telonera: Esquizofrenia.')),
 (3, '14', '08:00', '2 Taller de creación de carteles cinematográficos para niños y niñas', UDEA, TAL, 'taller', dict(sinopsis='Un recorrido por el mundo del cine. Taller infantil Chico y Proqui.', invitados='Harold Blanco y Lenys López')),
 (3, '14', '14:00', 'Las pesadillas del siervo', CAM, PEL, None, dict(director='Manuel Villa', clasificacion='+12')),
 (3, '14', '16:00', 'Conversatorio con Manuel Villa', CAM, CON, 'conversatorio', dict(invitados='Manuel Villa, director de «Las pesadillas del siervo»')),
 (4, '14', '16:30', 'Actos babilónicos', CAM, CON, 'conversatorio', dict(sinopsis='Detrás de las mariposas amarillas en «Cien años de soledad».', invitados='David Palacios, Mauricio Babilonia en «Cien años de soledad»')),
 (4, '14', '17:30', 'La Canoa Dorada (Tanda 2)', CAM, COR, None, dict(clasificacion='+7')),
 (4, '14', '18:30', 'Gala de premiación La Canoa Dorada', CAM, ACT, 'premiación', {}),
 (4, '14', '20:30', 'Los hijos de Benkos', BAR, PEL, None, dict(director='Lucas Silva', anio=2000, clasificacion='+7')),  # director y año: pie del carrusel «Imperdibles» del festival, https://www.instagram.com/p/DfdSh_XFLWK/ (8 nov)
 (4, '14', '21:30', 'Champeta y picó', BAR, CON, 'conversatorio', dict(sinopsis='Herencia del Gran Caribe para los pueblos ribereños.', invitados='Juan Carbonel, académico de la champeta')),
 (4, '14', '23:00', 'Fiesta Chilapa', BAR, ACT, 'evento', dict(sinopsis='Show de cierre.', invitados='DJ Gabriela Morgan')),
]
# La lámina no da duración: es la franja hasta lo que sigue en el mismo lugar; la
# última de cada noche, una estimación. La app la exige para armar el plan.
DUR = {'Fiesta en el Playón': 90, 'La barca de los sueños olvidados': 30, 'Remando con Pablo y Karla': 60,
       'Narrativas chilapas': 120, 'Los cuerpos que son caudal': 90, 'Conversatorio Entre 2 Aguas': 60,
       'Conversatorio con Brigitte Baptiste': 60, 'Taller de creación de carteles cinematográficos para niños y niñas': 120,
       '2 Taller de creación de carteles cinematográficos para niños y niñas': 120, 'Escuchando con la cámara': 120,
       'La Canoa Dorada (Tanda 1)': 120, 'Una mirada a través del lente': 60, 'Cine gótico popular': 90,
       'Conversatorio con Manuel Villa': 30, 'Actos babilónicos': 60, 'La Canoa Dorada (Tanda 2)': 60,
       'Gala de premiación La Canoa Dorada': 90, 'Los hijos de Benkos': 60, 'Champeta y picó': 90, 'Fiesta Chilapa': 120}
funciones = []
for lam, dia, hora, tit, sede, sec, kind, extra in F:
    r = {'titulo': tit, 'dia': D + dia, 'hora': hora, 'sede': sede, 'seccion': sec, 'acceso': 'Entrada libre',
         '_src': {'url': POST, 'lamina': lam, 'date': '2026-11-05', 'tipo': 'festival-ig'}, **extra}
    if tit in DUR:
        r['duracion_min'] = DUR[tit]
    if kind:
        r.update(tipo='evento', event_kind=kind)
    funciones.append(r)
io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
    '_provenance': provenance('Programación oficial, 4 láminas de @festivaldecine.bc (5 nov 2026)', metodo='transcripción a ojo; cruzada con OCR en fecibac-2026-verificar.py', que_aporta='día, hora, lugar y clasificación'),
    '_acceso': {'estado': 'Entrada libre', 'revisado': '2026-11-05', 'fuentes': [POST], '_por_que': 'Ninguna fuente anuncia pago; regla de Juan: sin aviso de pago es gratis.'},
    'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')
