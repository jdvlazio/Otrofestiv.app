#!/usr/bin/env python3
"""feciso-2026-catalogo.py — la selección oficial del 10.º Festival de Cine
Independiente de Sogamoso (FECISO, Sogamoso / Sugamuxi, 1–7 nov 2026).
PRE-ONBOARDING. Radar #1233.

LA FUENTE: siete carruseles de @fecisofest, leídos SIN SESIÓN por el embed
(pipeline/ig_sin_sesion.py) y bajados con ig.bajar_laminas a fuentes/ig/<sc>/.
El dato está PINTADO en las láminas (título, «Dir.», y país en las
internacionales); el pie no lo repite. Transcripción a ojo, lámina por lámina,
cruzada con pipeline/ig-lecturas.py <sc> --ojos (3 lecturas OCR, sin ALT).

  DeseCXgEU_t (19 oct)  Selección Oficial Cortometraje Boyacense 2026   11
  Decuil8klP4 (13 oct)  Selección Oficial Largometraje Nacional 2026     6
  DedeCs2keOk (13 oct)  Selección Oficial Videoclip 2026                 8
  DehVQ63Ee7e (15 oct)  Selección Oficial Cortometraje Internacional     9
  DezbvdKEdBP           Selección Oficial Nuevos Realizadores 2026      11
  De0MXC6ESng           Selección Oficial Cortometraje Animación Nacional 2026   4
  De4bPYXkf4D           Selección Oficial Cortometraje Documental Nacional 2026 12
    (pie: Cinemateca del Sol, Sogamoso, 1–7 nov)

La lámina 00 de cada post es la portada. Las láminas son STILLS con el laurel
encima, no afiches: de aquí no sale ningún afiche.

Sección: la cabecera de la lámina sin el año (verbatim). El pie de los largos
dice «Competencia Nacional de Largometraje»; la lámina, «Largometraje Nacional».
País: lo pinta la lámina en Videoclip e Internacional; Boyacense y Nacional son
Colombia por definición de la convocatoria. Títulos: la lámina está en
MAYÚSCULA sostenida; se pasan a caja de oración sin tocar letra ni tilde
(«Orígen» va como está pintado). Errata pintada que se conserva y se anota:
«THE FOLLLWERS» (seguramente «The Followers»).

Sin web oficial (21 oct 2026). Falta: año y duración de todo; cortometraje
nacional y otras secciones, si existen, no aparecen en los ~12 posts visibles
sin sesión.

El script FRENA si un post no da tantas obras como láminas menos la portada.
Escribe festivals/staging/feciso-2026-catalogo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/feciso-2026-catalogo.json'
IG = 'https://www.instagram.com/p/{}/'

# (shortcode, fecha, sección verbatim, tipo, láminas, [(título, director, país)])
POSTS = [
    ('DeseCXgEU_t', '2026-10-19', 'Cortometraje Boyacense', 'corto', 12, [
        ('Vuelo de una golondrina', 'Natalia Pérez', 'Colombia'),
        ('La bondad de la feijoa', 'Karen Sofía Gómez Estupiñán', 'Colombia'),
        ('Huellas: volviendo a la tierra campesina', 'Juan Pablo Gutiérrez Nossa', 'Colombia'),
        ('El legado de Bochica', 'Jhonattan Acosta Beltrán', 'Colombia'),
        ('Aguarruz - Memorias de maíz', 'Darwin Cristiano Bello', 'Colombia'),
        ('Nuevo sendero', 'Susan Ximena Moreno Izaquita', 'Colombia'),
        ('Tentado de difunto', 'Daniel Santiago Ruiz Sandoval', 'Colombia'),
        ('Hytcha', 'Carlos Eduardo Morales Chaparro', 'Colombia'),
        ('Mysk’fihizha´ - Nueva gente', 'Ignacio Murillo', 'Colombia'),
        ('Laurel: orígen de una lucha', 'Gustavo Enrique Rios Velandia', 'Colombia'),
        ('Raíces de amor', 'Daniel Josué Cardozo Figueredo', 'Colombia'),
    ]),
    ('Decuil8klP4', '2026-10-13', 'Largometraje Nacional', 'largo', 7, [
        ('Fragmentos de otra historia', 'César García Garzón, Laura Vera Jaramillo', 'Colombia'),
        ('¿Quién quemó el bus?', 'Juan José Jaramillo', 'Colombia'),
        ('La luz por primera vez', 'Frank Rodríguez Rojas, Ibeth Johanna Rey Jerez', 'Colombia'),
        ('Por una gota de leche', 'Esteban J. Corzo', 'Colombia'),
        ('Kaugsankamalla: mientras vivamos', 'Soraida Chindoy, Karoline Pelikan', 'Colombia'),
        ('El huaquero', 'Harold Devastén', 'Colombia'),
    ]),
    ('DedeCs2keOk', '2026-10-13', 'Videoclip', 'corto', 9, [
        ('El Edén', 'Andrea Torres Sánchez', 'España'),
        ('Ciudad de cristal', 'Nicolás Forero, Darwin Bello', 'Colombia'),
        ('Kraken – Hombre Mito, Hombre Leyenda', 'Esteban José Corzo, Iván Acosta', 'Colombia'),
        ('Árbol en pie', 'Red Comunitaria Trans, Mapa López, Rodrigo Torrijos', 'Colombia'),
        ('Figurante', 'Publio César De La Vega García', 'España'),
        ('¿Por qué así?', 'María Martelo', 'Colombia'),
        ('Sin fraktura', 'Santiago Rubio López', 'Colombia'),
        ('Iridescence', 'Adrien Lhoste', 'Francia'),
    ]),
    ('DehVQ63Ee7e', '2026-10-15', 'Cortometraje Internacional', 'corto', 10, [
        ('Bajo el polvo, nuestra tierra', 'Miguel Ángel Herrera', 'Brasil'),
        ('Despojo', 'Roma Corrales', 'Perú'),
        ('Blanco roto', 'Armando Buika, Rubén Salazar, Teresa Arilla', 'España'),
        ('After the Meteor Shower', 'Yu-Ching Shieh', 'Taiwán'),   # pintado «Tawián»
        ('La tempestad', 'Diego Müller', 'Brasil'),
        ('The Rusty Fish', 'Milad Fathiani', 'Irán'),
        ('La piel de nuestra memoria', 'Edmundo U. Galicia', 'México'),
        ('El día de mi suerte', 'Joavany Álvarez, Rafael Pedroza', 'Estados Unidos'),
        ('The Folllwers', 'Hsiang-Wen Lu, Wei-Hsuan Chen', 'Taiwán'),  # errata pintada
    ]),
    ('DezbvdKEdBP', '2026-10-22', 'Nuevos Realizadores', 'corto', 12, [
        ('Sol de niebla', 'Maria Jose Ibarra, Florentino Vargas', 'Colombia'),
        ('Puente Nacional', 'Juan Sebastian Cadena Bernal', 'Colombia'),
        ('Miguel Ángel, Federico, y el carro que pasó por encima de las gafas', 'Juan David Rodríguez', 'Colombia'),
        ('Entre la montaña', 'Jenny Berdugo Beltrán, Javier Ferreira Bohórquez', 'Colombia'),
        ('La última pieza', 'Juan Felipe Vargas', 'Colombia'),
        ('Entre el diario y el sueño', 'Daniela Callejas', 'Colombia'),
        ('El amor en tiempos de cumbia', 'Violeta Barrios', 'Colombia'),
        ('Los años del conejo', 'Raquel Tamayo Gutiérrez', 'Colombia'),
        ('Para no volver', 'Tania Galvis', 'Colombia'),
        ('Cinco paredes', 'Bastián Huerta', 'Chile'),
        ('Sintoniza la paz vol. 2', 'Jeyson David Beltrán', 'Colombia'),
    ]),
    ('De0MXC6ESng', '2026-10-22', 'Cortometraje Animación Nacional', 'corto', 5, [
        ('Tuktu, padre maíz', 'Mauricio Prieto Muriel', 'Colombia'),
        ('Pudor ante el asalto de los ojos furtivos', 'Laura María Rodríguez', 'Colombia'),
        ('¿Por qué me olvidaste?', 'Sofía Cadavid Ocampo', 'Colombia'),
        ('The Devil Room', 'Duban Pinzón', 'Colombia'),
    ]),
    ('De4bPYXkf4D', '2026-10-24', 'Cortometraje Documental Nacional', 'corto', 13, [
        ('Camino al Chicamocha', 'Frank Rodríguez', 'Colombia'),
        ('Cayenas libertarias', 'Javier Camilo Aranguren', 'Colombia'),
        ('Wëtcxa Ew Fxi´zenxi - El sentir de la palabra', 'Luis Pujimuy', 'Colombia'),
        ('Niña chilapa', 'Juana Lotero López', 'Colombia'),
        ('Obdulio', 'Erika Piragauta Marquez', 'Colombia'),
        ('La sinfonía de Guanentá', 'Victor Jaramillo', 'Colombia'),   # OCR «Cuanentá»; la lámina dice G
        ('Dios y suerte', 'Carol Duran Pulido', 'Colombia'),
        ('Agua - Guaviare', 'Adrián Villa Dávila', 'Colombia'),
        ('La asociación', 'Juan Camilo Muñoz Quintero', 'Colombia'),
        ('Memoria del agua', 'Rodrigo Torrijos Parra', 'Colombia'),
        ('Selva nublada: un viaje al corazón del bosque de niebla', 'Viviana Sánchez Prada', 'Colombia'),
        ('Tejiendo un árbol', 'Álvaro Cardona', 'Colombia'),
    ]),
]


def main():
    obras = []
    for sc, fecha, seccion, tipo, laminas, filas in POSTS:
        if len(filas) != laminas - 1:
            sys.exit(f'✗ {sc}: {len(filas)} obras y {laminas - 1} láminas de obra')
        dir_ig = f'{REPO}/fuentes/ig/{sc}'
        if not os.path.isdir(dir_ig):
            sys.exit(f'✗ faltan las láminas de {sc}: python3 pipeline/ig_sin_sesion.py {sc} + ig.bajar_laminas')
        for i, (titulo, director, pais) in enumerate(filas, 1):
            obras.append({'titulo': titulo, 'director': director, 'pais': pais,
                          'tipo': tipo, 'seccion': seccion,
                          '_src': {'url': IG.format(sc), 'date': fecha,
                                   'lamina': f'fuentes/ig/{sc}/{i:02d}.jpg'}})
    json.dump({'_provenance': provenance('https://www.instagram.com/fecisofest/',
                                         metodo='láminas de 7 carruseles IG (embed, sin sesión), a ojo + ig-lecturas',
                                         publicado='2026-10-13/19'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
