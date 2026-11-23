#!/usr/bin/env python3
"""under-2026-crudo.py — la PROGRAMACIÓN del XXII Festival Transterritorial de
Cine Underground, sede Medellín (25 nov – 3 dic 2026) → crudo.

LA FUENTE QUE MANDA (18 nov 2026): el PDF oficial de 6 páginas que el festival
(José Fernando Duque) mandó a hola@ — fuentes/under-2026/correo-2026-11-18/
Programa_UNDER_Medellin_2026_def.pdf (tipo festival-mensaje). Pág. 1 afiche,
2 (25–26 nov), 3 (27–28 nov), 4 (1 dic), 5 (2–3 dic), 6 OTRAS ACTIVIDADES.
Triple lectura: capa de texto (pdftotext), OCR del sistema (pipeline/ocr.py
sobre las páginas a 200 dpi) y a ojo; las tres coinciden en todo token de
programación (las únicas diferencias son logotipos y tildes del OCR).

LA FUENTE ANTERIOR (16 nov): reel IG @cineundermedellin Df0rYtRxmgp, solo
25–29 nov y solo Perpetua Lab. Del reel se conservan, porque el PDF no los
trae y no los contradice: las DURACIONES de sus obras, los rótulos de sección
de cada día, el título de los programas («Programa 1», «verdever»,
«Experimental»), la descripción de la fiesta y de las charlas, el aporte de la
fiesta, la inscripción del taller del 28 y la HORA de la proyección sorpresa
del 29 (el PDF la lista sin hora, después del taller de las 3:00 PM).

HORAS SIN AM/PM: «6:30 / BEBOP» (25 nov), «6:30 / LIBRERÍA ANTIMATERIA» (1 y
2 dic) y «7:00 / PERPETUA LAB» (3 dic) → 18:30 y 19:00: es la franja de todo
el programa y no hay nada de mañana en el festival.

30 NOV: el PDF no programa nada ese día (ni la pág. 6).

ACCESO: solo la fiesta dice precio (reel: «Aporte 10k»). Regla de Juan
(13 oct): sin aviso de pago = entrada libre.

Escribe festivals/staging/under-2026-crudo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/under-2026-crudo.json'
PDF = 'fuentes/under-2026/correo-2026-11-18/Programa_UNDER_Medellin_2026_def.pdf'
REEL = 'https://www.instagram.com/p/Df0rYtRxmgp/'
LIBRE = 'Entrada libre'
PL, BB, DR, AM = 'Perpetua Lab', 'Bebop Bar', 'Donde Robin', 'Librería Antimateria'

# Secciones: el rótulo de cada día en el reel, VERBATIM (propuesta: lo decide Juan).
# Las funciones que solo trae el PDF van en «Muestra Oficial» (seccion_default del plan, Juan 18 nov).
DOC = 'Documental Activismo Social'
ANI = 'Animación'
FEM = 'Feminismos y disidencias sexuales'
CRE = 'Actividad creativa'
EXP = 'Cine experimental'
ACA = 'Actividad académica'

# (día, hora, sede, título, sección, página del PDF, obras[(título, director, país, año, min|None)], extra)
# Título/director/país/año: el PDF. Minutos: el reel (el PDF no trae duraciones).
F = [
    ('11-25', '18:30', PL, 'Apertura', DOC, 2,
     [('Borrachos mientras escuchamos las gotas caer', 'Santiago Gómez Ramírez', 'Colombia', 2026, 21),
      ('The sight is a wound', 'Parham Ghalamdar', 'Irán', 2025, 7)],
     # Reel de @cineundermedellin, 22 nov (https://www.instagram.com/p/DgDZtCwP9sY/): portada «con presencia
     # del realizador»; pie «un encuentro y diálogo alrededor de la película». El PDF no lo dice ni lo niega.
     dict(has_qa=True)),
    ('11-25', '20:00', PL, 'Las muertes más bellas del mundo', DOC, 2,
     [('Las muertes más bellas del mundo', 'Quique Avilés, Ellie Walton', 'Estados Unidos', 2024, 71)], {}),
    ('11-25', '18:30', BB, 'Bisou ACAB + Memoria colectiva + 8 metros: La palabra subterránea', None, 2,
     [('Bisou ACAB', 'Guillermo Gallo', 'Francia', 2026, None),
      ('Memoria colectiva', 'Cristina Colmenares', 'Perú', 2025, None),
      ('8 metros: La palabra subterránea', 'Pablo Fernández Alberti', 'Argentina', 2026, None)], {}),
    ('11-25', '18:30', DR, 'El coloquio de los pájaros', None, 2,
     [('El coloquio de los pájaros', 'Sofía Velázquez', 'Perú', 2026, None)], {}),
    ('11-26', '19:00', PL, 'Programa 1', ANI, 2,
     [('Duelo', 'Sebastian Barnes', 'Argentina', 2025, 12),
      ('1 paseo por la ciudad', 'Alejandro Acuña Sevilla, Sara Coello Coello', 'México', 2025, 8),
      ('Comb story', 'Ernesto Rodriguez Cruz', 'Estados Unidos', 2026, 3),
      ('Cyclotron', 'Brian Gibson', 'Estados Unidos', 2026, 4),
      ('SKRFF', 'Corrie Francis Parks, Daniel Nuderscher', 'Austria', 2024, 7),
      ('Tapeworm Alexis & the Opera Diva', 'Thaïs Odermatt', 'Suiza', 2025, 11),
      ("The Shapeshifter's lament", 'Gaele Sobott', 'Australia', 2025, 10),
      ('Teatime', 'David Mathews', 'Austria', 2026, 4),
      ('Rattling', 'Nguyen Thao Nguyen', 'Vietnam', 2026, 3)], {}),
    ('11-26', '18:30', DR, 'Amor trava', None, 2,
     [('Amor trava', 'Lucrecia Mastrangelo', 'Argentina', 2026, None)], {}),
    # Pág. 3 (obras, 5:00 PM) y pág. 6 («5:00 PM — 7:00 PM Muestra cine feminismos y
    # disidencias sexuales con conversatorio…») son LA MISMA función.
    ('11-27', '17:00', PL, 'verdever', FEM, 3,
     [('Elegy for the Lost', 'William Hong-xiao Wei', 'Francia, España, Reino Unido', 2025, 29),
      ('Objectionable Fruit', 'Hogan Seidel, Gabby Follett', 'Estados Unidos', 2026, 15),
      ('Ser, no ser, ser muchas', 'Silbando bembas', 'Argentina', 2025, 13),
      ('Perros', 'Ezequiel Rossi, Facundo Salomón', 'Argentina', 2026, 10)],
     dict(descripcion='Conversatorio con el Club de lectura y escritura de ciencia ficción anarco feminista.')),
    ('11-27', '21:00', PL, 'Fiesta Under · El Vikingo Selektor', FEM, 6, [],
     # hasta la 1:30 a. m. (dato del festival que pasó Juan, 20 nov): 270 min
     dict(tipo='evento', event_kind='fiesta', acceso='Con boleta: aporte $10.000', duracion_min=270,
          descripcion='El Vikingo Selektor: post punk, dark wave, dark techno, industrial y EBM. Aporte $10.000.')),
    # Título y texto del formulario de inscripción que mandó el festival (20 nov):
    # https://docs.google.com/forms/d/e/1FAIpQLSfPOmpRt-XqqxNssm_S76cmQb0QR35cQu81IJB9Ua3PiJplTQ/viewform
    ('11-28', '15:00', PL, 'Orígenes de los lenguajes audiovisuales experimentales y laboratorio de creación', CRE, 6, [],
     # 4 horas (dato del festival que pasó Juan, 20 nov)
     dict(tipo='evento', event_kind='taller', acceso='Entrada libre con inscripción previa. Cupos limitados', duracion_min=240,
          registration_url='https://docs.google.com/forms/d/e/1FAIpQLSfPOmpRt-XqqxNssm_S76cmQb0QR35cQu81IJB9Ua3PiJplTQ/viewform',
          descripcion='Un recorrido por los antecedentes y el origen de los lenguajes audiovisuales experimentales, '
                      'centrado en la animación experimental de pioneros como Walter Ruttmann, Hans Richter y Viking '
                      'Eggeling. Con esas referencias, los participantes hacen un ejercicio práctico de exploración '
                      'colectiva en el que la imagen se aborda como materia plástica mediante técnicas manuales sobre '
                      'papel, digitalización y montaje. No se requieren conocimientos previos. A cargo de Hernán D. '
                      'Arango S., realizador audiovisual, editor y docente universitario con más de 20 años de '
                      'experiencia en cine y televisión, magíster en Artes Digitales; ha trabajado en creación e '
                      'investigación, y su obra ha sido exhibida en museos y festivales nacionales e internacionales.')),
    ('11-28', '19:00', PL, 'Experimental', EXP, 3,
     [('Cosmopoética: el ciclo de vida de una estrella masiva', 'Sofía Orozco Payares', 'Colombia', 2026, 10),
      ('Antifragility', 'Serafim Chikhladze', 'Rusia', 2026, 19),
      ('Fata Morgana', 'Hannu Nieminen', 'Finlandia', 2026, 5),
      ('Ghost Noon', 'Ting-Kin Chan', 'China', 2026, 7),
      ('Spheres', 'Martin Gerigk', 'Alemania', 2026, 6),
      ('Und Ich behaupte', 'Patrick Müller', 'Alemania', 2026, 3),
      ('Hansel and Gretel Get Kicked Out', 'MilleFeuille', 'Canadá', 2026, 11)], {}),
    ('11-29', '15:00', PL, 'Hacerlo sin permiso. Laboratorio de apropiación', ACA, 6, [],
     dict(tipo='evento', event_kind='taller',
          descripcion='A cargo de: El Gabinete Cine Club / Manifiesto / La Pola Records.')),
    ('11-29', '17:00', PL, 'Proyección sorpresa', ACA, 6, [],
     dict(tipo='evento', event_kind='evento', descripcion='El Gabinete Cine Club.')),  # el PDF no da hora: 17:00 es la del reel
    ('12-01', '18:00', BB, 'Jubiladxs le enseñan + Norma también + To the rhythm of love and hate', None, 4,
     [('Jubiladxs le enseñan', 'Silbando Bembas', 'Argentina', 2025, None),
      ('Norma también', 'Natalia Andrea Vinelli, Alejandra Guzzo', 'Argentina', 2025, None),
      ('To the rhythm of love and hate: A punkumentary on salsa with the Macabeo Orchestra',
       'Nelson Varas-Díaz', 'Puerto Rico', 2026, None)], {}),
    ('12-01', '18:30', AM, 'Una persona distinta + 5 obras', None, 4,
     [('Una persona distinta', 'Sergio Quatraro', 'Argentina', 2026, None),
      ('Atombombenabend', 'Thorsten Fleisch', 'Alemania', 2026, None),
      ('Binary', 'Padrick Ritch', 'Estados Unidos', 2026, None),
      ('Distillery Dance', 'Elly Moghtaderi', 'Irán', 2026, None),
      ('Echoes of a zephyr', 'Josh Weissbach', 'Albania', 2025, None),
      ('Chaika', 'Ingrid Paola Bonilla Rodriguez', 'Colombia', 2025, None)], {}),
    ('12-02', '18:30', AM, 'Cut your wings and fly + Quizás nunca + Mall + Shell Shock O\'K', None, 5,
     [('Cut your wings and fly', 'Meryem Lahlou', 'Estados Unidos', 2026, None),
      ('Quizás nunca', 'Loana Isabel Pagani', 'Argentina', 2026, None),
      ('Mall', 'Frida Balca', 'España', 2026, None),
      ("Shell Shock O'K", 'Dmytro Grynov', 'Alemania, Ucrania', 2026, None)], {}),
    ('12-02', '19:00', PL, 'A Perfect Maryam + Pluvia + Sinforme sinfinal + Les Voyageurs', None, 5,
     [('A Perfect Maryam', 'Solmaz Etemadzadeh, Ara Torosian', 'Irán, Estados Unidos', 2025, None),
      ('Pluvia', 'Iñigo Floristán', 'España', 2025, None),
      ('Sinforme sinfinal', 'Patricio Lagos', 'Perú', 2026, None),
      ('Les Voyageurs', 'David Bingong', 'Camerún, España', 2025, None)], {}),
    ('12-03', '19:00', PL, 'Tuktu, padre maíz + 7 obras', None, 5,
     [('Tuktu, padre maíz', 'Mauricio Prieto Muriel', 'Colombia', 2026, None),
      ('Salman Wants to Go', 'Ozan Takış', 'Turquía', 2025, None),
      ('Esas ruinas', 'Gabriel Piñeiro', 'Argentina', 2023, None),
      ('Quisiera volverme río', 'Susana Parejas', 'Argentina', 2024, None),
      ('Lo que aún queda de mí', 'Elena Bursztein', 'Argentina', 2026, None),
      ('Mamma', 'Mike Montagna', 'Italia', 2025, None),
      ('Analogue natives', 'Bernd Lützeler', 'Alemania, India', 2025, None),
      ('Vlasta, el recuerdo no es eterno', 'Candela Vey, Tino Pereira', 'Argentina', 2025, None)], {}),
]


# Sinopsis traducidas por nosotros (solo había inglés): pipeline/under-2026-sinopsis.json
_SIN = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'under-2026-sinopsis.json'), encoding='utf-8'))


def main():
    funciones = []
    for dia, hora, sede, tit, sec, pag, obras, extra in F:
        extra = dict(extra)
        r = {'titulo': tit, 'dia': f'2026-{dia}', 'hora': hora, 'sede': sede,
             'acceso': extra.pop('acceso', LIBRE),
             '_src': {'url': PDF, 'lamina': f'p. {pag}', 'date': '2026-11-18', 'tipo': 'festival-mensaje'}}
        if sec:
            r['seccion'] = sec
        ob = []
        for t, d, p, a, m in obras:
            o = {'titulo': t, 'director': d, 'pais': p, 'anio': a}
            if m:
                o['duracion_min'] = m
            if t in _SIN['sinopsis']:
                o['sinopsis'] = _SIN['sinopsis'][t]
                o['_sinopsis_fuente'] = _SIN['_fuente']
            ob.append(o)
        if len(ob) == 1:
            r.update({k: v for k, v in ob[0].items() if k != 'titulo'})
        elif ob:
            r['obras'] = ob
            r['tipo'] = 'programa'
            if all(o.get('duracion_min') for o in ob):
                r['duracion_min'] = sum(o['duracion_min'] for o in ob)
        r.update(extra)
        funciones.append(r)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(PDF, metodo='PDF oficial (correo 18 nov): capa de texto + OCR + a ojo; '
                                              'duraciones y rótulos de sección del reel ' + REEL,
                                  que_aporta='día, hora, sede, obras de cada función, director/país/año, acceso'),
        'funciones': funciones,
        '_sin_funciones': '30 nov: el PDF oficial no programa nada'},
        ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
