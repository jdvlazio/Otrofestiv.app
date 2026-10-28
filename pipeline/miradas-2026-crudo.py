#!/usr/bin/env python3
"""miradas-2026-crudo.py — la programación oficial de Miradas Medellín 2026 → crudo.

LA FUENTE es «Programación Miradas 2026-Liviano.pdf» (112 págs., InDesign,
creado el 20 oct 2026), enlazado desde la web de la Alcaldía
(medellin.gov.co/estimuloscultura/miradasProgramacion, QR de la pág. 2).
Copia en fuentes/miradas-2026/pdf-programacion/ (gitignored). Tipo
festival-pdf. Es POSTERIOR a los carruseles de @cinematecademedellin
(11–25 oct) que leyó el pre-onboarding; donde difieren, manda el PDF, y la
diferencia queda declarada en DIFERENCIAS_IG.

QUÉ SE LEE Y DÓNDE (transcrito a mano, página por página):
  · págs. 71–96  «Programación diaria festival»: día, hora, sede, sala, obras;
  · págs. 56–63  «Cinemateca móvil» (7 y 8 nov, Parque de los Deseos);
  · págs. 64–70  «Cine expandido y Domo»;
  · págs. 40–44  fichas de Cine Comunitario: la función en el barrio de cada
                 obra NO está en la grilla diaria, solo en la ficha;
  · págs. 45–47  talleres de mediación (los lee miradas-2026-formacion.py,
                 cruzados con el PDF: mismas fechas, horas y lugares);
  · págs. 108–110 Días de Industria: SOLO lo abierto al público (pág. 107).
Las grillas de las secciones (56–70) REPITEN lo de la diaria (71–96): cada
actividad entra una vez. Lo que solo trae una de las dos, entra igual.

ACCESO: entrada libre en todo el festival — «con entrada libre» y «sin costo»
(@cinematecademedellin, De4MmOSj8gv 24 oct y De-hVjhCTMG 27 oct). Talleres y
laboratorios: «Entrada libre hasta completar cupos». «Encuentros con»:
inscripción previa con el formulario del QR de las págs. 109–110 (decodificado
el 27 oct: Google Form «Formulario de inscripción - Encuentros con - Miradas
Medellín 2026»).

Escribe festivals/staging/miradas-2026-crudo.json
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'miradas-2026'
OUT = os.path.join(REPO, 'festivals/staging/miradas-2026-crudo.json')
FORMACION = f'{REPO}/festivals/staging/{FID}-formacion.json'
PDF = 'https://drive.google.com/uc?export=download&id=1TaDM4ZWcoOuMmoGk7ToeVKfieMjdD00b'
LIBRE = 'Entrada libre'
CUPOS = 'Entrada libre hasta completar cupos'
FORM_ENCUENTROS = 'https://docs.google.com/forms/d/e/1FAIpQLSfKw4WDoDIq9qhpB1ND0AYB8HrHZvRm4XyKhgjfun1il9Qajg/viewform'

# ── las obras: ficha del PDF (título de la ficha, dirección, país, año, min) ──
O = {
    'Seis meses en el edificio rosa con azul': ('Bruno Santamaría Razo', 'México, Brasil, Dinamarca', 2026, 105, 'Ficción, documental'),
    'Chapecó, el último sobreviviente: nace una hermandad': ('Edison Vanegas Álvarez', 'Colombia', 2026, 72, 'Documental'),
    'Las pesadillas del siervo': ('Manuel Villa Machado', 'Colombia', 2026, 76, 'Documental'),
    'Uno vuelve siempre': ('Camilo Ríos', 'Colombia', 2025, 95, 'Documental'),
    'De: Saúl': ('Santiago Gomxz', 'Colombia', 2026, 4, 'Ficción, experimental'),
    'Kof-kof': ('Juan David Cardona Arboleda', 'Colombia', 2026, 7, 'Experimental'),
    'La danza de los ángeles': ('Juan Restrepo Molina', 'Colombia', 2026, 15, 'Ficción, experimental'),
    'La escucha, la razón. Memoria acústica de un mural': ('Juan David Bolívar Araque', 'Colombia', 2026, 15, 'Documental'),
    'La mona': ('Laura Gutiérrez', 'Colombia', 2025, 18, 'Ficción'),
    'La muerte nos declaró adultos': ('Luisa María Charry Valencia', 'Colombia', 2026, 2, 'Documental, experimental'),
    'Madres de nacimiento': ('Gloria Isabel Gómez Ceballos', 'Francia', 2026, 8, 'Documental'),
    'Mal de tierra': ('Camila Caballero Guzmán', 'Colombia', 2026, 10, 'Experimental'),
    'Refracción': ('Isabella Palacio Mesa', 'Colombia', 2025, 11, 'Ficción'),
    'Cómo limpiar una casa en 10 pasos fáciles': ('Carolina González Valencia', 'Colombia', 2026, 80, 'Documental'),
    'Iluminada': ('Nicolás Rincón Gille', 'Colombia, Bélgica', 2026, 120, 'Ficción'),
    'Relicto': ('Guillermo Quintero', 'Colombia, Francia', 2026, 97, 'Documental'),
    'Agachar el rostro': ('Camilo Medina Noy', 'Colombia', 2025, 12, 'Ficción'),
    'Decaer': ('Juan Camilo González', 'Colombia', 2026, 7, 'Animación'),
    'El león': ('Diana Bustamante Escobar', 'Colombia', 2026, 15, 'Documental, experimental'),
    'Emechiche, el renacer de los cabeciblancos': ('Juan Camilo González', 'Colombia, Argentina', 2025, 11, 'Animación'),
    'Las formas de la magia': ('María Paula Lorgia Garnica', 'Colombia', 2026, 17, 'Documental'),
    'Mi viche todo el día': ('Juan Camilo Moreno', 'Colombia', 2025, 26, 'Documental'),
    'Una vez en un cuerpo': ('María Cristina Pérez González', 'Colombia', 2025, 10, 'Animación'),
    'El deshielo': ('Manuela Martelli', 'Chile, Estados Unidos, España, México', 2026, 108, 'Ficción'),
    'El río de los espíritus': ('Colectivo Tawna, Nase Lino Sumpinanch', 'Ecuador, Estados Unidos', 2026, 61, 'Documental'),
    'El tren fluvial': ('Lorenzo Ferro, Lucas A. Vignale', 'Argentina', 2026, 75, 'Ficción'),
    'Iván & Hadoum': ('Ian de la Rosa', 'España, Alemania, Bélgica', 2026, 103, 'Ficción'),
    'Niñas escarlata': ('Paula Cury Melo', 'República Dominicana, México, Alemania', 2026, 70, 'Documental'),
    'Narciso': ('Marcelo Martinessi', 'Paraguay, Brasil, Portugal, Alemania, España, Francia, Uruguay', 2026, 101, 'Ficción'),
    'Nuestro secreto': ('Grace Passô', 'Brasil, Portugal', 2026, 104, 'Ficción'),
    'Un cabo suelto': ('Daniel Hendler', 'Uruguay, Argentina, España', 2025, 95, 'Ficción'),
    'Corazón azul': ('Samuel Suffren', 'Haití, Francia', 2025, 15, 'Ficción'),
    'Compraventa': ('Tomás Murphy', 'Argentina', 2025, 11, 'Ficción'),
    'La sangre': ('Joaquín León', 'España', 2025, 15, 'Ficción'),
    'Norheimsund': ('Ana A. Alpizar', 'Cuba, Estados Unidos', 2025, 12, 'Ficción'),
    'Planetario': ('Sofía Poncini', 'Argentina', 2025, 9, 'Ficción'),
    'Quem se move (Quien se mueve)': ('Stephanie Ricci', 'Brasil', 2025, 20, 'Ficción'),
    'Última vez hace mucho tiempo': ('Santiago Martín', 'Venezuela', 2026, 24, 'Ficción, experimental'),
    'Temporada de patos': ('Fernando Eimbcke', 'México', 2004, 90, 'Ficción'),
    'Club sándwich': ('Fernando Eimbcke', 'México', 2013, 82, 'Ficción'),
    'Moscas': ('Fernando Eimbcke', 'México, España, Argentina', 2026, 102, 'Ficción'),
    'Mu-ki-ra': ('Estefanía Piñeres Duque', 'Colombia, España', 2026, 82, 'Ficción, animación'),
    'Los nuevos': ('Rodrigo Plá', 'México', 2026, 79, 'Ficción'),
    'Papaya': ('Priscilla Kellen', 'Brasil', 2026, 75, 'Animación'),
    'Luis Antonio': ('Juan José Arias Gil', 'Colombia', 2025, 12, 'Ficción'),
    'Planeta fome': ('Édier William Medeiros da Silva', 'Brasil', 2025, 15, 'Animación'),
    'Falcon 98': ('Yosman Serrano Lindarte', 'Colombia', 2024, 8, 'Ficción'),
    'Ficus': ('Isabella Bobadilla Monsalve', 'Colombia', 2023, 4, 'Animación'),
    'Nangulví': ('Segundo Fuérez', 'Ecuador', 2022, 5, 'Animación'),
    'Sputnik': ('Juan Pablo Sánchez', 'Colombia', 2023, 9, 'Ficción'),
    'Mi casa es su casa': ('Joan Mayorga', 'Colombia', 2025, 5, 'Animación'),
    'Cuentos de hadas': ('Daniela Soria', 'México', 2023, 15, 'Ficción'),
    'La sixtina': ('Juan Camilo Fonnegra', 'Colombia', 2022, 8, 'Animación'),
    'El segundo entierro de Alejandrino': ('Raúl Soto Rodríguez', 'Colombia', 2021, 75, 'Documental'),
    'Tierra en la lengua': ('Rubén Mendoza', 'Colombia, Francia', 2014, 89, 'Ficción'),
    'El paradero': ('Semillero Colectivo Cinestrato', 'Colombia', 2024, 9, 'Ficción, documental'),
    'El teléfono morado': ('Taller de Cine Corporación Mi Comuna', 'Colombia', 2024, 10, 'Documental'),
    'Éther, somos todo': ('Fabián Cataño Torres', 'Colombia', 2024, 39, 'Documental'),
    'Mamá chila: raíz y corazón de la comunidad': ('Arbey Antonio Gómez Muñoz', 'Colombia', 2025, 18, 'Documental'),
    'Oro molido # 2': ('Juan David Medrano', 'Colombia', 2024, 35, 'Documental'),
    'Paralelo': ('Escuela de Comunicación Comunitaria', 'Colombia', 2025, 5, 'Ficción'),
    'Chico de barrio': ('Juan David Echavarría Urrego', 'Colombia', 2026, 4, 'Animación'),
    # «80 min 40 s» (pág. 93) y «80 min.» (ficha, pág. 48): 80. Año «1985–1987»: la serie; sin año
    'Un día en la vida de...': ('Carlos Álvarez', 'Colombia', None, 80, 'Documental'),
    'Aún es de noche en Caracas': ('Mariana Rondón, Marité Ugás', 'Venezuela', 2025, 97, 'Ficción'),
    # Cine en el Domo (págs. 51–52): sin año en la ficha
    'Alga-Rio': ('Cristóbal Parra, Almendra Díaz', 'Chile', None, 6, None),
    'ACDM': ('Ilgin İçözü, Bruno Tripodi, Jana Tox', 'España', None, 9, None),
    'ASCII Sound Experience': ('Julián Angarita', 'Colombia', None, 11, None),
    'El vuelo 2.0': ('Jhon Melo', 'Colombia', None, 6, None),
    'Entreluz': ('Jorge Bandera', 'Colombia', None, 9, None),
    'Sentidos en disputa': ('Carlos Serrano, José Miguel Mejía', 'Colombia', None, 7, None),
    'Materia ondulatoria': ('Daniel Shambo, Pierre Puentes', 'Colombia', None, 12, None),
}

# ── sedes: el nombre que imprime el PDF → (sede canónica, sala) ─────────────
MAMM, COLOMBO, CINEPROX = 'Museo de Arte Moderno de Medellín - MAMM', 'Centro Colombo Americano', 'Cineprox Las Américas'
DESEOS, EXPLORA, PLANETARIO = 'Parque de los Deseos', 'Parque Explora', 'Planetario de Medellín'
CAPILLA, MORAVIA = 'Comfama La Capilla', 'Centro de Desarrollo Cultural de Moravia'
MOVIL = 'Cinemateca móvil'   # la sala itinerante en el Parque de los Deseos

# ── programas (el festival los nombra «Programa de cortos N») ───────────────
P1 = ['Las formas de la magia', 'La danza de los ángeles', 'Decaer', 'El león',
      'La muerte nos declaró adultos', 'Última vez hace mucho tiempo']                    # 80
P2 = ['Una vez en un cuerpo', 'Madres de nacimiento', 'Norheimsund', 'Refracción',
      'Mal de tierra', 'Quem se move (Quien se mueve)']                                  # 71
P3 = ['La mona', 'Compraventa', 'De: Saúl', 'Agachar el rostro', 'Kof-kof', 'La sangre']  # 67
P4 = ['Planetario', 'Emechiche, el renacer de los cabeciblancos',
      'La escucha, la razón. Memoria acústica de un mural', 'Mi viche todo el día', 'Corazón azul']  # 76
CHIQUI = ['Planeta fome', 'Falcon 98', 'Ficus', 'Nangulví', 'Sputnik', 'Mi casa es su casa',
          'Cuentos de hadas', 'La sixtina']                                              # 69
COMUNITARIO = ['El paradero', 'El teléfono morado', 'Éther, somos todo',
               'Mamá chila: raíz y corazón de la comunidad', 'Oro molido # 2', 'Paralelo', 'Chico de barrio']  # 120
DOMO = ['Alga-Rio', 'ACDM', 'ASCII Sound Experience', 'El vuelo 2.0', 'Entreluz',
        'Sentidos en disputa', 'Materia ondulatoria']                                    # 60
CLAUSURA = ['Norheimsund', 'Una vez en un cuerpo', 'Planetario',
            'Emechiche, el renacer de los cabeciblancos', 'La sangre', 'Corazón azul', 'Refracción']  # 83
EXPANDIDO = 'Obras: El sueño de Sedna, Sosiego al atardecer, Todas las cosas que algún día se desvanecieron y Vórtice Nebular.'

S_HM, S_COL, S_IB = 'Cine Hecho en Medellín', 'Cine Colombiano', 'Cine Iberoamericano'
S_RET, S_FAM, S_ACC = 'Retrospectiva Fernando Eimbcke', 'Cine Familiar', 'Cine Accesible'
S_COM, S_MEM, S_EXP = 'Cine Comunitario - Hecho en Medellín', 'Cine Memoria', 'Cine Expandido - Hecho en Medellín'
S_DOMO, S_CLA, S_MOV = 'Cine en el Domo', 'Evento de Clausura', 'Cinemateca Móvil'
S_IND, S_PROG, S_INAU = 'Días de Industria', 'Programas de Cortos', 'Película Inaugural'
S_TAL = 'Talleres de Desarrollo y Mediación de Audiencias'

QA_EQ = 'Función con presencia de los equipos'


def obra(t):
    d, p, a, m, g = O[t]
    g = g.split(',')[0].strip().capitalize() if g else None   # va UN género ([genero-unico]): el primero de la ficha
    return {k: v for k, v in {'titulo': t, 'director': d, 'pais': p, 'anio': a,
                              'duracion_min': m, 'genero': g}.items() if v is not None}


def peli(dia, hora, t, sec, sede, sala='', pag=0, qa=None, **kw):
    r = {**obra(t), 'dia': dia, 'hora': hora, 'sede': sede, 'sala': sala, 'seccion': sec,
         'acceso': LIBRE, '_src': {'url': PDF, 'pag': pag, 'tipo': 'festival-pdf'}}
    if qa:
        r.update(has_qa=True, qa_type='team')
    r.update(kw)
    return r


def prog(dia, hora, titulo, obras, sec, sede, sala='', pag=0, qa=None, **kw):
    r = {'titulo': titulo, 'dia': dia, 'hora': hora, 'sede': sede, 'sala': sala, 'seccion': sec,
         'obras': [obra(t) for t in obras], 'acceso': LIBRE,
         '_src': {'url': PDF, 'pag': pag, 'tipo': 'festival-pdf'}}
    if qa:
        r.update(has_qa=True, invitados=qa)
    r.update(kw)
    return r


def ev(dia, hora, titulo, kind, sec, sede, sala='', pag=0, dur=None, acceso=LIBRE, sinopsis=None, **kw):
    r = {'titulo': titulo, 'tipo': 'evento', 'event_kind': kind, 'dia': dia, 'hora': hora,
         'sede': sede, 'sala': sala, 'seccion': sec, 'acceso': acceso,
         '_src': {'url': PDF, 'pag': pag, 'tipo': 'festival-pdf'}}
    if dur:
        r['duracion_min'] = dur
    if sinopsis:
        r['sinopsis'] = sinopsis
    r.update(kw)
    return r


def abierta(dia, hora, titulo, sec, sede, sala, pag, dur, hasta=None, sinopsis=None):
    """se lleva, no se planifica (info): exposición, domo móvil, muestra"""
    r = ev(dia, hora, titulo, 'evento', sec, sede, sala, pag, dur, sinopsis=sinopsis, info=True)
    if hasta:
        r['hasta'] = hasta
    return r


D3, D4, D5, D6, D7, D8 = (f'2026-11-0{d}' for d in range(3, 9))

F = [
    # ── martes 3 (pág. 71; ficha pág. 12) ──
    peli(D3, '18:30', 'Seis meses en el edificio rosa con azul', S_INAU, 'Teatro Pablo Tobón Uribe', pag=71,
         qa='Conversatorio con su director Bruno Santamaría y su productora Bruna Haddad'),
    # ── miércoles 4 (págs. 71–73) ──
    peli(D4, '10:00', 'Papaya', S_FAM, 'Coocine', 'Sala 0', 71),
    prog(D4, '14:00', 'Programa de Cortos 1', P1, S_PROG, MAMM, 'Teatro MAMM', 71, qa=QA_EQ),
    peli(D4, '16:30', 'Iván & Hadoum', S_IB, MAMM, 'Teatro MAMM', 72),
    prog(D4, '17:00', 'Programa de Cortos 4', P4, S_PROG, COLOMBO, 'Sala 2', 72, qa=QA_EQ),
    peli(D4, '17:00', 'Un cabo suelto', S_IB, MORAVIA, 'Auditorio', 73),
    # la sala 3 de Cineprox la da la ficha (pág. 13); la grilla no la dice
    peli(D4, '19:00', 'Las pesadillas del siervo', S_HM, CINEPROX, 'Sala 3', 73, qa='Con la presencia del director'),
    peli(D4, '19:00', 'Tierra en la lengua', S_ACC, DESEOS, '', 73,
         sinopsis_nota='Proyección accesible con Lengua de Señas Colombiana, audiodescripción y subtitulación enriquecida.'),
    peli(D4, '19:30', 'Narciso', S_IB, MAMM, 'Teatro MAMM', 73),
    peli(D4, '19:30', 'Temporada de patos', S_RET, COLOMBO, 'Sala 1', 73, qa='Con la presencia del director'),
    # Cine Comunitario en el barrio (fichas, págs. 41 y 44)
    peli(D4, '18:00', 'El paradero', S_COM, 'Café Pletórico', '', 41),
    peli(D4, '18:00', 'Chico de barrio', S_COM, 'Teatro UVA Tricentenario', '', 44),
    # ── jueves 5 (págs. 74–78) ──
    ev(D5, '10:00', 'Laboratorio Materia expandida: representación e imagen en contextos digitales',  # UN laboratorio en 2 sesiones (págs. 63–66): encadenado, el nombre de la sesión va en la sinopsis
       'evento', S_EXP, EXPLORA, 'Exploratorio', 64, 180, acceso=CUPOS, is_recurring=True,
       sinopsis='Sesión 1 – Materia y representación. Realizado por Almendra Díaz y Cristóbal Parra (Chile). Un laboratorio práctico para explorar la relación entre materia física e imagen digital, transformando objetos del entorno en modelos 3D y experiencias audiovisuales mediante fotogrametría, programación visual y videomapping.'),
    prog(D5, '14:00', 'Programa de Cortos 2', P2, S_PROG, MAMM, 'Teatro MAMM', 74, qa=QA_EQ),
    peli(D5, '15:00', 'Iluminada', S_COL, 'Comfama Otraparte', '', 75, qa='Con la presencia del actor Pedro Suárez'),
    peli(D5, '16:00', 'Nuestro secreto', S_IB, MORAVIA, 'Auditorio', 75),
    ev(D5, '16:30', 'Cine performativo y la puesta en escena más allá de la pantalla', 'conversatorio', S_EXP, EXPLORA,
       'Exploratorio', 65, 60,
       invitados='Con Carlos Eduardo Castaño Correa (Todas las cosas que algún día se desvanecieron) y José Luis Ruiz Peláez (Sosiego al atardecer), con la moderación de Alannath Naslyllalyla (artista y curadora)'),
    prog(D5, '16:30', 'Programa de Cortos 3', P3, S_PROG, MAMM, 'Teatro MAMM', 76, qa=QA_EQ),
    peli(D5, '17:00', 'El segundo entierro de Alejandrino', S_ACC, COLOMBO, 'Sala 1', 76,
         sinopsis_nota='Proyección con Lengua de Señas Colombiana y audiodescripción.'),
    peli(D5, '18:00', 'Los nuevos', S_FAM, 'Junta de Acción Comunal El Faro', '', 77),
    peli(D5, '18:00', 'El río de los espíritus', S_IB, CAPILLA, '', 77),
    prog(D5, '18:00', 'Perder la Escala: Experiencias Cine Domo para Otros Mundos', DOMO, S_DOMO, PLANETARIO, 'Domo', 77),
    ev(D5, '19:00', 'Letanía, performance audiovisual', 'concierto', S_EXP, PLANETARIO, 'Auditorio', 77, 60,
       _duracion_de='estimada: el PDF no da hora de fin',
       sinopsis='Concierto inaugural de Cine expandido. Realizado por Cristóbal Parra (Chile). Una performance audiovisual que explora los rituales latinoamericanos y la relación entre industria, territorio y memoria, con video, sonido, láser y archivos históricos.'),
    peli(D5, '19:00', 'Chapecó, el último sobreviviente: nace una hermandad', S_HM, CINEPROX, 'Sala 3', 78,
         qa='Con la presencia del director'),
    peli(D5, '19:00', 'Uno vuelve siempre', S_HM, DESEOS, '', 78),
    peli(D5, '19:00', 'Seis meses en el edificio rosa con azul', S_IB, COLOMBO, 'Sala 1', 78, qa='Con la presencia del director'),
    peli(D5, '19:30', 'Niñas escarlata', S_IB, MAMM, 'Teatro MAMM', 78, qa='Con la presencia de la directora'),
    peli(D5, '10:00', 'Oro molido # 2', S_COM, 'Escuela Vereda El Placer', '', 43),
    # ── viernes 6 (págs. 79–82) ──
    ev(D6, '10:00', 'Laboratorio Materia expandida: representación e imagen en contextos digitales',
       'evento', S_EXP, EXPLORA, 'Exploratorio', 67, 180, acceso=CUPOS, is_recurring=True,
       sinopsis='Sesión 2 – Imagen y expansión. Realizado por Almendra Díaz y Cristóbal Parra (Chile). Segunda sesión del laboratorio de fotogrametría, programación visual y videomapping.'),
    peli(D6, '14:00', 'El tren fluvial', S_IB, MAMM, 'Teatro MAMM', 79),
    peli(D6, '15:00', 'Un cabo suelto', S_IB, 'Parque de Cristo Rey', '', 79, _nota='«En alianza con Cultura Parque»'),
    peli(D6, '16:00', 'Narciso', S_IB, 'Biblioteca Comfama Bello', '', 80),
    peli(D6, '16:00', 'Uno vuelve siempre', S_HM, MORAVIA, 'Auditorio', 80, qa='Con la presencia del director'),
    peli(D6, '16:00', 'Cómo limpiar una casa en 10 pasos fáciles', S_COL, MAMM, 'Teatro MAMM', 80),
    ev(D6, '16:30', 'La imagen como territorio', 'conversatorio', S_EXP, EXPLORA, 'Exploratorio', 80, 60,
       invitados='Con Cristóbal Parra y Almendra Díaz, modera Alannath Naslyllalyla (artista y curadora)'),
    prog(D6, '17:00', 'Programa de Cortos 1', P1, S_PROG, COLOMBO, 'Sala 2', 81, qa=QA_EQ),
    prog(D6, '17:00', 'Luis Antonio y Los Nuevos', ['Luis Antonio', 'Los nuevos'], S_FAM,
         'Estación Trece de Noviembre', '', 81),
    peli(D6, '18:00', 'Las pesadillas del siervo', S_HM, CAPILLA, '', 81, qa='Con la presencia del director'),
    peli(D6, '19:00', 'Moscas', S_RET, MAMM, 'Plazoleta', 82, qa='Con la presencia del director'),
    peli(D6, '19:00', 'Chapecó, el último sobreviviente: nace una hermandad', S_HM, DESEOS, '', 82),
    peli(D6, '19:00', 'El deshielo', S_IB, CINEPROX, 'Sala 3', 82),
    prog(D6, '19:00', 'Perder la Escala: Experiencias Cine Domo para Otros Mundos', DOMO, S_DOMO, PLANETARIO, 'Domo', 82),
    peli(D6, '19:30', 'Iluminada', S_COL, COLOMBO, 'Sala 1', 82, qa='Con la presencia del actor Pedro Suárez'),
    peli(D6, '19:00', 'Éther, somos todo', S_COM, 'Institución Educativa Pío XII', '', 42),
    peli(D6, '19:00', 'Paralelo', S_COM, 'JAC Santa Cruz parte alta', '', 43),
    # ── sábado 7 (págs. 83–90 y 56–59) ──
    abierta(D7, '08:00', 'Red de Creación Audiovisual de Medellín', S_HM, MAMM, 'Teatro MAMM', 83, 540,
            sinopsis='La Red de Creación Audiovisual de Medellín presenta los frutos de sus laboratorios de creación y formación artística comunitaria: niños y adolescentes de la ciudad estrenan sus primeras películas.'),
    abierta(D7, '10:00', 'Exposición: El cine analógico: máquinas, formatos y memoria', S_MOV, DESEOS, 'Cinemateca móvil, galería',
            57, 600, hasta=D8,
            sinopsis='Dedicada al Archivo Fílmico de la Cinemateca Distrital de Medellín: tres proyectores de 8, 16 y 35 mm con películas de cada formato, y sesiones de socialización con proyecciones en 35 mm. Sábado 7 y domingo 8, de 10:00 a. m. a 8:00 p. m.'),
    abierta(D7, '10:00', 'Domo móvil: Animales celestes', S_MOV, DESEOS, MOVIL, 56, 480,
            sinopsis='Autor: Parque Explora. Los paisajes de Colombia junto a la cangreja azul, la bagra rayada y el puma, cuyos recorridos se vuelven constelaciones.'),
    abierta(D7, '10:00', 'Domo móvil: Arrecifes', S_MOV, DESEOS, 'Cinemateca móvil, galería', 57, 480,
            sinopsis='Autor: California Academy of Sciences. El océano junto a Sofía Gómez, campeona mundial de apnea, para descubrir los arrecifes de coral.'),
    abierta(D7, '10:00', 'Domo móvil: Viaje por el sistema solar', S_MOV, DESEOS, MOVIL, 57, 480,
            sinopsis='Autor: Parque Explora. Recorrido en vivo por el sistema solar con el software Uniview.'),
    ev(D7, '10:00', 'Laboratorio: Creación audiovisual con inteligencia artificial generativa', 'evento', S_MOV, DESEOS,
       'Cinemateca móvil, laboratorio', 58, 240, _duracion_de='hasta el laboratorio de las 2:00 p. m. en el mismo espacio', acceso=CUPOS,
       sinopsis='Impartido por Centro Ático de la Pontificia Universidad Javeriana. Exploración de posibilidades creativas con herramientas de generación de imágenes y video con inteligencia artificial.'),
    peli(D7, '11:00', 'Mu-ki-ra', S_FAM, 'Comfama Aranjuez', 'Auditorio', 83),
    prog(D7, '11:00', 'Programa de Cortos ChiquiShorts', CHIQUI, S_FAM, 'Biblioteca Comfama Caldas', '', 84,
         _nota='Curaduría por Bogoshorts (págs. 36–39)'),
    prog(D7, '13:00', 'Cine Comunitario: Función con Presencia de Directores y Conversatorio', COMUNITARIO, S_COM, DESEOS,
         MOVIL, 58, qa='Con la presencia de los directores y conversatorio'),
    ev(D7, '14:00', 'Laboratorio: Postproducción de video para dispositivos móviles', 'evento', S_MOV, DESEOS,
       'Cinemateca móvil, laboratorio', 58, 120, _duracion_de='hasta el taller de collage de las 4:00 p. m. en el mismo laboratorio', acceso=CUPOS,
       sinopsis='Impartido por el Centro Ático de la Pontificia Universidad Javeriana. Edición de video desde el celular: audio, luz, color, filtros, efectos y montaje.'),
    peli(D7, '14:00', 'Relicto', S_COL, 'Coocine', 'Sala 0', 86, qa='Con la presencia del director'),
    ev(D7, '16:00', 'Taller de collage: Cine en retazos', 'taller', S_MOV, DESEOS, 'Cinemateca móvil, laboratorio', 59, 120, _duracion_de='estimada: el PDF no da hora de fin',
       acceso=CUPOS, sinopsis='A partir de la proyección de un cortometraje, los participantes crean un collage como reinterpretación libre e intuitiva. Materiales incluidos.'),
    peli(D7, '16:00', 'Cómo limpiar una casa en 10 pasos fáciles', S_COL, CAPILLA, '', 86),
    peli(D7, '16:00', 'Nuestro secreto', S_IB, COLOMBO, 'Sala 1', 87),
    peli(D7, '16:00', 'Papaya', S_FAM, DESEOS, MOVIL, 59),
    ev(D7, '16:30', 'Ecologías emergentes del cine expandido', 'conversatorio', S_EXP, EXPLORA, 'Exploratorio', 69, 60,
       invitados='Con Diego Alberto Pérez Osorno (Vórtice Nebular) y el Colectivo Axiz (Felipe López y Yoana Casanova, El sueño de Sedna), con la moderación de Alannath Naslyllalyla (artista y curadora)'),
    prog(D7, '18:00', 'Perder la Escala: Experiencias Cine Domo para Otros Mundos', DOMO, S_DOMO, PLANETARIO, 'Domo', 87),
    ev(D7, '18:00', 'Especiales Cinemateca con Natalia Reyes', 'conversatorio', S_MOV, DESEOS, 'Cinemateca móvil, sala de cine', 59, 60,
       sinopsis='Víctor Gaviria conversa con Natalia Reyes, actriz y productora colombiana, sobre su experiencia en la película Aún es de noche en Caracas y los procesos creativos detrás de esta producción.'),
    peli(D7, '18:00', 'Iván & Hadoum', S_IB, CAPILLA, '', 88),
    prog(D7, '18:30', 'Programa de Cortos 3', P3, S_PROG, COLOMBO, 'Sala 2', 88, qa=QA_EQ),
    peli(D7, '19:00', 'Aún es de noche en Caracas', S_MOV, DESEOS, MOVIL, 59),
    peli(D7, '19:00', 'Club sándwich', S_RET, CINEPROX, 'Sala 3', 89, qa='Con la presencia del director'),
    prog(D7, '19:00', 'Programa de Cortos 4', P4, S_PROG, MAMM, 'Teatro MAMM', 90, qa=QA_EQ),
    peli(D7, '19:00', 'El teléfono morado', S_COM, 'Finca Agroturística El Encanto de Mis Abuelos', '', 41),
    # ── domingo 8 (págs. 90–96 y 60–63) ──
    ev(D8, '10:00', 'Taller: Pintar el cine: intervención y proyección de material fílmico', 'taller', S_MOV, 'Casa de la Música',
       '', 60, 120, _duracion_de='estimada: el PDF no da hora de fin', acceso=CUPOS,
       sinopsis='La Corporación Otraparte invita a jóvenes a intervenir fragmentos de película de 35 mm con dibujos, tintas y pigmentos. Materiales incluidos.'),
    ev(D8, '10:00', 'Taller de cianotipia: fotografía en papel sin recurrir a la cámara', 'taller', S_MOV, DESEOS,
       'Cinemateca móvil, laboratorio', 60, 240, _duracion_de='hasta el laboratorio de las 2:00 p. m. en el mismo espacio', acceso=CUPOS,
       sinopsis='La cianotipia, un proceso fotográfico analógico sin cámara: con luz solar y agua se imprimen fotogramas de obras cinematográficas en azul de Prusia. Materiales incluidos.'),
    peli(D8, '11:00', 'Mu-ki-ra', S_FAM, DESEOS, MOVIL, 60),
    peli(D8, '14:00', 'Relicto', S_COL, MAMM, 'Teatro MAMM', 91),
    peli(D8, '14:00', 'Niñas escarlata', S_IB, COLOMBO, 'Sala 1', 92),
    prog(D8, '14:00', 'Programa de Cortos', CHIQUI + ['Luis Antonio'], S_FAM, DESEOS, MOVIL, 61),
    ev(D8, '14:00', 'Laboratorio Vivo: Hilos de memoria', 'evento', S_MOV, DESEOS, 'Cinemateca móvil, laboratorio', 61, 120, _duracion_de='hasta el taller de máscaras de las 4:00 p. m. en el mismo laboratorio',
       acceso=CUPOS, sinopsis='Impartido por la Red Audiovisual. Intervención analógica de fotogramas (foto-bordado) y animación stop motion a partir del archivo de la Red de Audiovisuales. Materiales incluidos.'),
    ev(D8, '16:00', 'Taller de máscaras: Conviértete en un Bicho Raro', 'taller', S_MOV, DESEOS, 'Cinemateca móvil, laboratorio', 62, 120, _duracion_de='estimada: el PDF no da hora de fin',
       acceso=CUPOS, sinopsis='Construye tu máscara de Macha, la cucaracha, o Yeisy, la araña, personajes de La Sinfonía de los Bichos Raros. Materiales incluidos.'),
    peli(D8, '16:00', 'Un día en la vida de...', S_MEM, COLOMBO, 'Sala 1', 93),
    prog(D8, '16:00', 'Programa de Cortos 2', P2, S_PROG, CINEPROX, 'Sala 3', 94, qa=QA_EQ),
    peli(D8, '16:00', 'El deshielo', S_IB, CAPILLA, '', 94),
    ev(D8, '17:30', 'Juancho Valencia y su relación con el cine', 'conversatorio', S_MOV, DESEOS, 'Cinemateca móvil, sala de cine', 95, 60,
       sinopsis='Juancho Valencia, ganador del Grammy Latino, dialoga con Diego Londoño (El Fan Fatal) sobre cómo ha tejido una relación entre su música y el cine.'),
    prog(D8, '18:30', 'Proyección y Concierto de Clausura', CLAUSURA, S_CLA, DESEOS, 'Plazoleta', 95, event_kind='clausura',
         sinopsis='Selección de cortometrajes; especial: estreno del cortometraje más destacado de la Red de Audiovisuales 2026; y concierto de clausura de la Orquesta Sinfónica Juvenil de la Red de Músicas de Medellín con Los Cumbia Stars.'),
]

# Recorrido guiado y Muestra de Cine Expandido (jue 5, vie 6 y sáb 7; págs. 65, 67, 69)
for d, pag in ((D5, 65), (D6, 67), (D7, 69)):
    F.append(ev(d, '14:00', 'Recorrido guiado: Muestra de Cine Expandido', 'evento', S_EXP, EXPLORA, 'Exploratorio', pag, 60,
                sinopsis='Un recorrido por cuatro obras que exploran nuevas formas de experimentar el cine mediante realidad virtual, instalaciones interactivas y entornos inmersivos. ' + EXPANDIDO))
F.append(abierta(D5, '14:00', 'Muestra de Cine Expandido', S_EXP, EXPLORA, 'Exploratorio', 65, 240, hasta=D7,
                 sinopsis='Jueves 5, viernes 6 y sábado 7 de noviembre, de 2:00 p. m. a 6:00 p. m. ' + EXPANDIDO))

# Días de Industria (págs. 107–110): lo ABIERTO AL PÚBLICO, en el MAMM, quinto piso
IND = [
    (D4, '09:00', 120, 'Clase maestra inaugural - Manual para observar moscas: descubrir lo extraordinario en lo simple', 'evento', 'con Fernando Eimbcke', LIBRE),
    (D4, '11:30', 60, 'Encuentro con festivales de cine, agente de ventas y distribuidores invitados a Miradas 2026', 'encuentro',
     'Alfredo Calvino (Habanero Films), Elba McAllister (Cineplex), Jim Kolmar (SXSW), Carlos Ramos (IndieLisboa), Guillermo Olivares (FicValdivia)', 'Entrada libre con inscripción previa'),
    (D4, '15:00', 90, 'Caso de estudio - La coproducción de Seis meses en el edificio rosa con azul', 'evento', 'con Bruna Haddad', LIBRE),
    (D4, '17:00', 60, 'Miradas a la distribución - Luces y sombras: exponiendo las realidades de la distribución', 'evento',
     'Con Alfredo Calvino, Elba McAllister y Linda Díaz Pernía, con la moderación de Yira Plaza O’Byrne', LIBRE),
    (D5, '09:00', 120, 'Clase maestra - Transformando el dolor en belleza: memoria, ficción y realidad, como herramientas que desdibujan etiquetas y fronteras', 'evento', 'con Bruno Santamaría', LIBRE),
    (D5, '11:30', 60, 'Encuentro con productoras, directoras y guionistas invitadas de Miradas 2026', 'encuentro',
     'Bruna Haddad, Verónica Triana, Federico Durán, Iván Gaona, Paula Cury Melo', 'Entrada libre con inscripción previa'),
    (D5, '15:00', 90, 'Caso de estudio - La coproducción desde Colombia', 'evento', 'con Federico Durán', LIBRE),
    (D5, '17:00', 60, 'Miradas al oficio - La disidencia autoral en los formatos comerciales', 'evento',
     'Con Sol Clemente (Fox), Laura Mora y Verónica Triana, con la moderación de Diógenes Cuevas', LIBRE),
    (D6, '09:00', 120, 'Clase maestra - El cine como testimonio colectivo', 'evento', 'con Paula Cury Melo', LIBRE),
    (D6, '11:30', 60, 'Encuentro con directores y directoras invitadas de Miradas 2026', 'encuentro',
     'Carolina González, Guillermo Quintero, Manuel Villa, Bruno Santamaría, Fernando Eimbcke', 'Entrada libre con inscripción previa'),
]
for d, h, dur, t, kind, inv, acc in IND:
    r = ev(d, h, t, kind, S_IND, MAMM, 'Quinto piso', 108, dur, acceso=acc, invitados=inv)
    if 'inscripción' in acc:
        r['registration_url'] = FORM_ENCUENTROS
    F.append(r)

# Talleres de mediación (págs. 45–47): del sidecar de formación, cruzado con el PDF
# el título como lo imprime el PDF (pág. 45–47): manda sobre la lámina de IG
TIT_PDF = {'Cine Corto detrás de cámara': 'Cine corto detrás de cámaras',
           'Colombia es fantástica': 'Colombia es fantástica: laboratorio de cine fantástico y terror colombiano',
           'La otra orilla:': 'La otra orilla: Revolver la mirada autorizada para manchar la cámara de barro',
           'Luces, cámara y estampa': 'Luces, cámara y estampa',
           'Rodando formación:': 'Rodando formación: mediaciones en comunidad'}
form = json.load(io.open(FORMACION, encoding='utf-8'))['actividades']
for a in form:
    for s in a['sesiones']:
        dur = None
        if s.get('fin'):
            h1, m1 = map(int, s['inicio'].split(':')); h2, m2 = map(int, s['fin'].split(':'))
            dur = (h2 * 60 + m2) - (h1 * 60 + m1)
        if not dur:   # Colombia es fantástica: sesiones cada 2 h (2:00 y 4:00 p. m.)
            dur, s['_duracion_de'] = 90, 'estimada: el PDF solo da la hora de inicio de cada sesión, cada 2 h'
        F.append(ev(s['fecha'], s['inicio'], TIT_PDF[a['titulo_lamina']], 'taller', S_TAL, a['lugar_lamina'], '', 45, dur,
                    sinopsis=f"Realizado por {a['realizado_por']}. {a['descripcion_es']}", is_recurring=len(a['sesiones']) > 1))

# Lo que el PDF trae y NO se publica, con su porqué (cobertura inversa)
NO_SE_PUBLICA = [
    {'pag': 42, 'que': 'Mamá chila: raíz y corazón de la comunidad — mié 28 oct, 7:00 p. m., Cr 58 con Calle 83e',
     'por_que': 'fuera de las fechas oficiales (3–8 nov); regla de Juan, solo días oficiales'},
    {'pag': 63, 'que': 'Clausura: «Especial: Estreno del cortometraje más destacado de la Red de Audiovisuales 2026»',
     'por_que': 'sin título ni duración; va dicho en la descripción de la clausura'},
    {'pag': 104, 'que': 'Encuentro de Coproducción, Encuentros uno a uno, Espacios de relacionamiento, Talleres especializados, Rueda de Negocios',
     'por_que': '«Solo para seleccionados» (pág. 107) o con participantes «previamente seleccionados» (pág. 106): industria cerrada'},
    {'pag': 107, 'que': 'Encuentro con los proyectos',
     'por_que': 'el PDF no le da día, hora ni sede (y lo describe «ante las personas acreditadas» y «Abierto al público» a la vez)'},
]

# Lo que el PDF (20 oct) cambia respecto a las láminas de IG del pre-onboarding (11–25 oct)
DIFERENCIAS_IG = [
    ('Seis meses en el edificio rosa con azul', 'mar 3', 'IG 7:00 p. m.', 'PDF 6:30 p. m. (y el post Dekwxvdsblt)'),
    ('Narciso', 'mié 4', 'IG 4:00 p. m. Teatro MAMM', 'PDF 7:30 p. m. Teatro MAMM'),
    ('Un cabo suelto', 'mié 4', 'IG 7:30 p. m. Moravia', 'PDF 5:00 p. m. Moravia'),
    ('Papaya', 'mié 4', 'IG 4:00 p. m. COOCINE', 'PDF 10:00 a. m. COOCINE'),
    ('Programa de Cortos 2', 'dom 8', 'IG Cineprox «Sala 2» en 2 de sus láminas, «Sala 3» en otras', 'PDF: Sala 3 en las fichas'),
    ('Seis meses en el edificio rosa con azul', 'título', 'IG «6 meses…»', 'PDF «Seis meses…»'),
]


def main():
    fs = sorted(F, key=lambda f: (f['dia'], f['hora'], f['titulo']))
    for f in fs:
        if f.get('sinopsis_nota'):
            f['_nota'] = f.pop('sinopsis_nota')
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('Programación Miradas 2026-Liviano.pdf (Alcaldía de Medellín, 20 oct 2026)',
                                  metodo='transcripción a mano página por página (71–96, 56–70, 40–48, 108–110); cruzada con tres lecturas independientes',
                                  que_aporta='la programación completa: día, hora, sede, sala, obras y acceso'),
        '_acceso': {'estado': 'Entrada libre', 'revisado': '2026-10-27',
                    'fuentes': ['@cinematecademedellin De4MmOSj8gv («con entrada libre»)', 'De-hVjhCTMG («sin costo»)',
                                'PDF págs. 58–62 («Entrada libre hasta completar cupos»)', 'PDF págs. 107–110 (Encuentros con: inscripción previa por QR)']},
        '_no_se_publica': NO_SE_PUBLICA,
        '_diferencias_ig': [dict(zip(('obra', 'cuando', 'antes', 'ahora'), x)) for x in DIFERENCIAS_IG],
        'funciones': fs}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in fs if f.get('tipo') == 'evento')
    print(f'✓ {len(fs)} funciones ({len(fs) - n_ev} proyecciones, {n_ev} actividades) · '
          f'{len(NO_SE_PUBLICA)} entradas del PDF fuera, con su porqué → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
