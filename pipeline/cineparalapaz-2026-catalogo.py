#!/usr/bin/env python3
"""cineparalapaz-2026-catalogo.py — la Selección Oficial del IV Festival Cine para
la Paz (Bogotá, 18–21 nov 2026). PRE-ONBOARDING.

LA FUENTE: el carrusel de @cineparalapaz Dfk4smulKBB (10 nov 2026), 18 láminas
(portada + 17 obras), bajado sin sesión con el vigía (Apify) a
fuentes/cineparalapaz-2026/ig/ (00.jpg … 17.jpg) y su pie a ig-posts.json.
Cada lámina trae pintado: N/17, la categoría (sección), título, tipo · duración,
sinopsis, créditos y la FRANJA (día y rango horario). Se leyeron a ojo, una por
una (11 nov 2026). Ninguna lámina ni post dice la SEDE: solo «Bogotá».

La franja es un bloque de varias obras, no la hora de cada una: se guarda tal
cual en `franja` para montar la parrilla cuando aparezca la sede.

Las láminas no traen país ni año: la convocatoria es colombiana pero el pie dice
que llegaron obras de Perú, Argentina, Ecuador, Honduras y Alemania, así que el
país NO se deduce. «Hecho a mano» es de Maimará (Jujuy, Argentina): lo dice su
sinopsis.

Escribe festivals/staging/cineparalapaz-2026-catalogo.json
"""
import io, json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/cineparalapaz-2026-catalogo.json'
FECHA = '2026-11-11'
URL = 'https://www.instagram.com/p/Dfk4smulKBB/'

RO, MT, FP = 'Resistencias al Olvido', 'Miradas que Transforman', 'Futuros de la Paz'
F18M, F18T = 'Mié. 18 de noviembre · 9:30–11:00 a. m.', 'Mié. 18 de noviembre · 2:00–5:00 p. m.'
F19T, F20T = 'Jue. 19 de noviembre · 2:00–5:00 p. m.', 'Vie. 20 de noviembre · 2:00–3:30 p. m.'

# (n, sección, título, tipo, duración, dirección, franja, sinopsis)
LAMINAS = [
    (1, RO, 'Por una gota de leche', 'Documental', '59:33', 'Esteban J. Corzo', F18T,
     'En 1985, un grupo de jóvenes roba un camión de leche para repartirla en el sur de Bogotá. Tras su asesinato, las familias y una nueva generación encuentran en el arte una forma de hacer memoria.'),
    (2, RO, 'La niebla de la paz', 'Documental', '1:26:34', 'Joel Stangle', F18M,
     'Teo escribe las memorias de sus compañeros y Boris filma las negociaciones de paz. Al dejar el campamento, los dos buscan un archivo enterrado que puede cambiar la forma de contar la guerra.'),
    (3, RO, 'Medellín, yo te saludo', 'Documental', '3:30', 'Lucas Muñoz Cataño', F18T,
     'Imágenes de archivo de guerras lejanas se cruzan con rostros y ruinas de Medellín. El montaje hace resonar violencias separadas por el tiempo y el territorio.'),
    (4, RO, 'Refugiar el Gesto', 'Documental', '10:56', 'Adrián Villa Dávila, Andrés Prado Rojas', F18T,
     'En San Antonio, un grupo de jóvenes aprende de los mayores la Danza de las Tablíteras. Cada paso devuelve al presente una tradición ritual afrocolombiana.'),
    (5, MT, 'LA', 'Experimental', '1:02:00', 'Tephy Piedrahita Avellaneda', F19T,
     '¿Qué memorias guarda la sangre? Un ensayo audiovisual entrelaza la menstruación con relatos de mujeres que han atravesado la lucha armada y defendido sus territorios.'),
    (6, MT, 'La pandemia del feminicidio en Colombia', 'Documental', '22:45', 'Yesika Alejandra Calderón Hernández', F19T,
     'Detrás de cada cifra hay un nombre. Mujeres organizadas alzan la voz frente al feminicidio en Colombia y acompañan una lucha colectiva contra la impunidad.'),
    (7, MT, 'Manos que dan vida', 'Documental', '15:18', 'Juan Sebastián Arias Carvajal', F19T,
     'A los 75 años, Blanca sigue acompañando nacimientos en el Guaviare. En sus manos perdura un saber que ha sostenido a su comunidad entre la violencia y el abandono.'),
    (8, MT, 'Hecho a mano', 'Documental', '10:15', 'Carolina Miy', F19T,
     'En Maimará, el artista Nicolás Anún y su comunidad pintan un mural inspirado en el Día de las Almas. Cada pincelada trae al presente a quienes ya se fueron.'),
    (9, MT, 'Kinesis', 'Documental', '10:29', 'Yuliana Puentes', F19T,
     'Entre ensayos y funciones, el Departamento Coreográfico prepara dos obras. Sus bailarines exploran cómo cambia el movimiento cuando aprenden a escuchar el cuerpo de los demás.'),
    (10, MT, 'Un berraco Partido', 'Documental', '10:04', 'Andrea Ortiz Ardila', F19T,
     'Sesenta y dos años después de perder a su padre, María Irma Trigueros vuelve a contar lo ocurrido. Su memoria abre una ventana a la violencia bipartidista en Yaguará, Huila.'),
    (11, FP, 'De la misma Tierra', 'Documental', '18:44', 'Diego Pachón Castro', F20T,
     'En la Casa de la Paz de Bogotá conviven Doris, firmante de paz, y Virgelina, defensora de derechos humanos. Dos vidas atravesadas por la guerra comparten un lugar para construir paz a diario.'),
    (12, FP, 'Paseando Te Cuento', 'Documental', '8:50', 'Diego Alejandro Camargo Ardila', F20T,
     'Jairo López Achury, firmante de paz y cronista, convierte las calles de La Candelaria en un salón de clases. Cada parada abre una conversación sobre el conflicto, la resistencia y la memoria.'),
    (13, FP, '¿Una pola o qué?', 'Ficción', '15:17', 'Mateo Ramirez', F18T,
     'Un conductor y su ayudante transportan en silencio a un grupo de jóvenes. A bordo, los pasajeros creen que el viaje los acerca a un futuro mejor.'),
    (14, FP, 'Un Milagro Cada Día', 'Documental', '26:00', 'Lorena Forero', F20T,
     'En la cárcel El Buen Pastor, mujeres del patio 3 ponen en escena la vida de Milagros. A través de su relato aparecen cinco historias que revelan la complejidad de vivir entre rejas.'),
    (15, FP, 'Nueve jueves en Riachuelo', 'Documental', '24:00', 'Nelson Silva', F18T,
     'Edson Velandia tiene nueve jueves y los recreos de un colegio para formar una orquesta. En Riachuelo, Santander, el primer reto es descubrir qué quiere tocar cada estudiante.'),
    (16, FP, 'La coca: Buen vivir del pueblo Nasa', 'Documental', '19:16', 'Dubier Baicue, Ignacio Ramos, Sonica Cifuentes, Darinson Amaya', F20T,
     'En el resguardo Kiwnas Cxhab, el pueblo Nasa cuenta lo que la hoja de coca significa para su vida. Ante la erradicación forzada, defiende sus saberes y el derecho a decidir sobre su territorio.'),
    (17, FP, 'Cajamarca: El viaje del desengaño', 'Documental', '21:22', 'Ernesto Ciurlizza', F18T,
     'En Cajamarca, un campesino defiende el futuro agrícola de su pueblo frente al proyecto minero La Colosa. Una consulta popular pone en manos de la comunidad una decisión que cambiaría su territorio.'),
]
PAIS = {'Hecho a mano': 'Argentina'}   # Maimará, Jujuy (su sinopsis)


def minutos(t):
    p = [int(x) for x in t.split(':')]
    h, m, s = ([0] + p)[-3:] if len(p) == 2 else p
    return h * 60 + m + (1 if s >= 30 else 0)


def main():
    assert [l[0] for l in LAMINAS] == list(range(1, 18)), 'faltan láminas: son 17'
    obras = []
    for n, sec, tit, tipo, dur, dire, franja, sin in LAMINAS:
        m = minutos(dur)
        o = {'titulo': tit, 'director': dire, 'duracion_txt': dur, 'duracion_min': m,
             'genero': tipo, 'tipo': 'largo' if m >= 60 else ('mediometraje' if m > 30 else 'corto'),
             'seccion': sec, 'franja': franja, 'sinopsis': sin,
             'imagen_web': f'fuentes/cineparalapaz-2026/ig/{n:02d}.jpg',
             '_src': {'url': f'{URL}?img_index={n + 1}', 'date': FECHA}}
        if tit in PAIS:
            o['pais'] = PAIS[tit]
        obras.append(o)
    d = {'_provenance': {'fuente': f'@cineparalapaz, carrusel Selección Oficial 2026 ({URL})',
                         'capturado': FECHA, 'metodo': 'lectura a ojo de las 17 láminas'},
         'obras': obras}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(obras)} obras → {OUT}')


if __name__ == '__main__':
    main()
