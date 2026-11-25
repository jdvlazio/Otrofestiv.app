#!/usr/bin/env python3
"""festicine-antioquia-2026-catalogo.py — 27.° Festival de Cine de Santa Fe de Antioquia (4–8 dic 2026).

LA FUENTE: el PDF «Festicine 2026 Programación» (24 nov, 2 páginas, texto en curvas),
leído a ojo a 300 dpi y transcrito acá fila por fila. Segunda lectura ciega:
fuentes/festicine-antioquia-2026/lectura-2.json, y OCR; las compara -verificar.py.
Caja de Pandora además en texto (wp-json, 25 ago: 21 filas) y en IG DgISGJ7ESMG.
Óperas Primas además en texto (wp-json, 24 nov).

PARRILLA: día|hora|sede|rótulo|título|presencia. OBRAS: título|dirección|país|año|min.
CORRECCIONES declaradas abajo (la palabra del PDF queda en `impreso`).
Escribe festivals/staging/festicine-antioquia-2026-catalogo.json
"""
import io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

PDF = 'https://festicineantioquia.org/wp-content/uploads/2026/11/Festicine-2026-Programacion.web_.pdf'
OUT = f'{REPO}/festivals/staging/festicine-antioquia-2026-catalogo.json'
FECHA = '2026-11-24'

# U Universidad de Antioquia (auditorio) · A su Aula 201 · M Museo Juan del Corral ·
# H Hotel Mariscal Robledo · C Cámara de Comercio · P Plaza Mayor
PARRILLA = '''
4|20:00|P|Inauguración|Subterráneo + Pacífico|director Riccardo Gabrielli; participantes del taller Crea con contenido
5|09:00|U|Película|A Piece of Sky|
5|09:00|K|Conversando de…|Consejo departamental de cinematografía|Gobernanza, territorio y economía audiovisual: articulación de los Consejos de Cine y las Comisiones Fílmicas en las regiones. Invitados: Gonzalo Castellanos y Jerónimo Rivera.
5|10:00|H|Película|Yo y las bestias|
5|10:00|C|Película|Cría cuervos|
5|11:00|M|Tómate un café con…|Tómate un café con Riccardo Gabrielli y Samuel Castro|
5|11:30|H|Película|130 hermanos|
5|12:00|U|Competencia Internacional de Óperas Primas|Rodeo de campo|
5|12:00|C|Película|Soñé su nombre|directora Ángela Carabalí
5|14:00|U|Película|Tres hermanas|
5|14:00|H|Muestra especial y conversación|TV Cámaras | Microhistorias digitales|conversación
5|15:00|C|Película|Lactar|actriz María Helena Doering
5|15:00|A|Taller|Espacios de película: lo que el cine nos enseña sobre los lugares que habitamos|Taller (abierto al público general). Tallerista: Luis Felipe Ramírez, director de arte.
5|16:00|U|Película|Bye Bye Tiberias|
5|16:00|H|Película|Forest|
5|16:30|M|Película|Poker|Jorge Mario Vera, director de fotografía
5|17:00|P|Tómate un café con…|Tómate un café con Gastón Pauls, actor, y Samuel Castro|
5|18:00|U|Película|Estancia|
5|18:00|H|Película|Noviembre|actriz Aida Morales
5|18:00|M|Conversando de…|El universo de los cortos: Caja de Pandora|Con Maria Julia Grillo y Alejandro Alzate.
5|19:00|M|Caja de Pandora|Caja de Pandora: Primera sesión|
5|19:00|E|Película familiar|Hoppers: Operación castor|
5|20:00|P|Película|Nueve reinas|actor Gastón Pauls
5|22:00|P|Competencia Internacional de Óperas Primas|Ma, despierta|
6|09:00|U|Película|Alpha|
6|09:30|H|Película|Walchensee Forever|
6|10:00|A|Taller|Taller de actuación: "Actuar es confiar"|Taller (abierto al público general). Con la actriz Patricia Ércole.
6|11:00|U|Competencia Internacional de Óperas Primas|Kueka, memoria ancestral|
6|11:00|M|Conversando de…|La unión hace la industria|Con Cristina Echeverri, representante ASOCINDE; Alejandro Melo, representante ACA; María Carolina Barrera, representante ECO; Jorge Mario Vera, representante ADFC. Modera Lucía Cedeño.
6|11:30|H|Película|Die Odyssee|
6|13:00|U|Película|Libertad|
6|14:00|H|Película|Lágrimas de fuego|actor Gastón Pauls
6|15:00|U|Película|Noviembre|
6|15:00|M|Conversando de…|El arte de escribir comedias: por qué necesitamos historias que nos hagan reír|Con César Betancur «Pucheros», guionista, y Samuel Castro.
6|16:00|H|Competencia Internacional de Óperas Primas|Ma, despierta|
6|16:30|M|Película familiar|Mu-ki-ra|
6|17:00|P|Conversando con los actores|Conversando con los actores: María Helena Doering, Patricia Ércole, Ángela Cano, Viviana Santos, Gastón Pauls y Julio Sánchez Coccaro, con Samuel Castro|
6|17:00|U|Película|Toni Erdmann|
6|18:00|H|Competencia Internacional de Óperas Primas|Fang i vidre|
6|18:30|M|Película familiar|La sinfonía de los bichos raros|Lina Pérez, distribuidora de la película
6|19:00|B|Película|Koatí|
6|20:00|P|Película|Lactar|actriz María Helena Doering
6|20:00|M|Caja de Pandora|Caja de Pandora: Segunda sesión|
6|22:00|P|Película|Los iniciados|Cristina Echeverri, productora ejecutiva
7|09:00|U|Película|Stop-Zemlia|
7|10:00|H|Película|Anima: Die Kleider meines Vaters|
7|10:00|C|Película|Sublime|
7|10:00|A|Taller|Taller del Consejo de Cultura: Guion de ficción para cortometraje|Taller con inscripción previa. Con Carolina Barrera.
7|11:00|M|Tómate un café con…|Tómate un café con la actriz María Helena Doering y Samuel Castro|
7|11:30|U|Muestra especial y conversación|Muestra del Tecnológico de Artes Débora Arango|conversación
7|12:00|H|Película familiar|Koatí|
7|12:00|C|Competencia Internacional de Óperas Primas|La Miss|
7|13:30|U|Película|Los tortuga|
7|14:00|H|Película familiar|Fiebre|
7|14:30|C|Película|Horizonte|actriz Ángela Cano
7|15:00|M|Conversando de…|Cuando el set se vuelve familia: los vínculos que nacen haciendo cine|Con Jorge Forero, director y productor, y Samuel Castro.
7|15:30|U|Película|Campeones|
7|16:00|D|Muestra cultural|Concierto de Navidad: Escuela de Música Jorge Robledo Ortiz|
7|16:00|H|Película|El rey de la montaña|
7|17:00|P|Competencia Internacional de Óperas Primas|Fang i vidre|
7|18:00|U|Película|Llueve sobre Babel|actor y productor Felipe Aguilar
7|18:00|H|Película|Los tortuga|
7|20:00|P|Película|Susana y Elvira: sin plan B|actriz Viviana Santos Pulido; productor Juan Pablo Solano
7|22:00|P|Película|Pablo|actor Julio Sánchez Cóccaro
8|09:00|U|Película|Almanya – Willkommen in Deutschland|
8|10:00|H|Película|Casa en llamas|
8|10:00|A|Taller|Taller del Consejo de Cultura: Producción para cortometrajes|Taller con inscripción previa. Con Lucía Cedeño, productora.
8|11:00|U|Película|Make Way for Tomorrow|
8|11:00|M|Tómate un café con…|Tómate un café con Julio Sánchez Cóccaro y Samuel Castro|
8|12:00|H|Película|Bye Bye Tiberias|
8|13:00|U|Competencia Internacional de Óperas Primas|Aunque seamos islas|
8|14:00|H|Película familiar|The Unbreakable Boy|
8|14:30|U|Película|Un poeta|
8|15:00|M|Conversando de…|Socios en las buenas y en las malas: el vínculo entre el mánager y el artista|Con Pilar Fernández, mánager, y Samuel Castro.
8|16:00|H|Película|El rey de la montaña|
8|16:30|P|Muestra cultural|Sexta versión del Encuentro Artístico y Cultural "Entre ritmos, danzas y colores"|Antioquia Latina.
8|17:00|U|Película|Yo y las bestias|
8|18:00|H|Película|El juego de la vida|
8|20:00|P|Clausura|Matrioshka|director Jorge Forero
'''
OBRAS = '''
Subterráneo|David Berrío, Alejandro Alzate|Colombia|2026|13
Pacífico|Riccardo Gabrielli|Colombia|2026|95
A Piece of Sky|Michael Koch|Suiza, Alemania|2022|136
Yo y las bestias|Nico Manzano|Venezuela|2021|78
Cría cuervos|Carlos Saura|España|1976|110
130 hermanos|Ainara Aparici|Chile|2022|71
Rodeo de campo|Rodrigo Domínguez, José Lecaros|Chile|2026|60
Soñé su nombre|Ángela Carabalí|Colombia|2026|86
Tres hermanas|Joyce Ventura|Colombia|2026|80
Lactar|Harold Trompetero|Colombia|2026|75
Bye Bye Tiberias|Lina Soualem|Palestina|2023|82
Forest|Lidia Duda|Polonia, República Checa|2024|84
Poker|Juan Sebastián Valencia|Colombia|2011|76
Estancia|Andrés Carmona Rivera|Colombia|2025|85
Noviembre|Tomás Corredor|Colombia|2025|78
Hoppers: Operación castor|Daniel Chong|Estados Unidos|2026|104
Nueve reinas|Fabián Bielinsky|Argentina|2000|114
Ma, despierta|Rolando Gil|Puerto Rico|2026|117
Alpha|Jan-Willem van Ewijk|Países Bajos|2024|100
Walchensee Forever|Janna Ji Wonders|Alemania|2020|110
Kueka, memoria ancestral|María de los Ángeles Peña Fonseca|Venezuela|2025|64
Die Odyssee|Florence Miailhe|Alemania|2021|122
Libertad|Clara Roquet|España, Bélgica|2021|109
Lágrimas de fuego|Gabriel Grieco|Argentina|2024|82
Mu-ki-ra|Estefanía Piñeres|Estados Unidos|2022|81
Toni Erdmann|Maren Ade|Alemania|2016|182
Fang i vidre|Alberto Martínez|España|2026|79
La sinfonía de los bichos raros|Julián Duque|Colombia|2026|91
Koatí|Rodrigo Pérez-Castro|México, Estados Unidos|2021|92
Los iniciados|Juan Felipe Orozco|Colombia|2023|111
Stop-Zemlia|Kateryna Gornostai|Ucrania|2021|122
Anima: Die Kleider meines Vaters|Uli Decker|Alemania|2022|95
Sublime|Mariano Biasin|Argentina|2022|100
La Miss|Daniel Porto|Brasil|2026|106
Los tortuga|Belén Funes|España, Chile|2024|110
Fiebre|Elisa Eliash|Chile, Perú|2022|84
Horizonte|César Augusto Acevedo|Colombia|2025|125
Campeones|Javier Fesser|España|2018|124
El rey de la montaña|Camilo Vega|Colombia|2023|83
Llueve sobre Babel|Gala del Sol|Colombia|2025|111
Susana y Elvira: sin plan B|María Gamboa Jaramillo|Colombia|2026|113
Pablo|Sebastián Vega|Colombia|2016|81
Almanya – Willkommen in Deutschland|Yasemin Samdereli|Alemania|2010|116
Casa en llamas|Dani de la Orden|España, Italia|2024|105
Make Way for Tomorrow|Leo McCarey|Estados Unidos|1937|92
Aunque seamos islas|Cristina Rodríguez Paz|España|2025|69
The Unbreakable Boy|Jon Gunn|Estados Unidos, India|2025|109
Un poeta|Simón Mesa Soto|Colombia|2025|124
El juego de la vida|Andrés Ruiz|Colombia|2026|95
Matrioshka|Jorge Forero|Colombia|2025|89
'''
# Caja de Pandora (tabla del PDF, p. 2): título|dirección|categoría|min
PANDORA = {'Caja de Pandora: Primera sesión': '''
A las 9 es la cita|Carlos Ospina|Ficción|18
Aitana|Isabella Cárdenas Marín|Documental|16
Akababuru|Irati Dojura|Ficción|14
Cayenas libertarias|Javier Camilo Aranguren Montañez|Documental|17
Decaer|Juan Camilo González|Animación|7
Discómanos|Luis Montealegre|Ficción|15
La habitación del macho cabrío|Duban Pinzon|Animación|12
La Mona|Laura Gutiérrez Ardila|Ficción|18
Make up: El arte de amar|Daniel Eduardo Calderón Arana|Ficción|20
''', 'Caja de Pandora: Segunda sesión': '''
Animero son de la muerte|Nadine Holguín Urrego|Ficción|11
Chaika|Ingrid Paola Bonilla Rodríguez|Ficción|15
El amor no olvida|Anselmo Calvo|Ficción|15
La gran hazaña|Luber Yesid Zúñiga Ordóñez|Ficción|15
Maleza|Nicolle Estrada, Marcela Palacio|Ficción|11
Maricones|María Paz Ruiz González|Documental|14
No te despiertes|Hernán Velásquez Villa|Ficción|8
Persiguiendo sueños|Chhamber, Lexx|Ficción|13
Refracción|Isabella Palacio Mesa|Ficción|11
Replay|Simón Matallana Nossa|Animación|6
Suelo|Eduar Yosniel Pájaro Peña|Animación|4
Una mujer de rostro ya olvidado|Miguel Solano J|Ficción|15
'''}
# muestras: solo título y min en el PDF. El país no lo dice.
MUESTRAS = {'TV Cámaras | Microhistorias digitales': '''
Entre patas y sentimientos|3
Dos realidades, una oportunidad|3
Una segunda oportunidad|3
¿Por qué me olvidaste?|3
Rescatar por amor|3
''', 'Muestra del Tecnológico de Artes Débora Arango': '''
Banda Paniagua: 200 años, legado y tradición|9
El ritmo de un círculo|8
La barbería|7
La sombra del zaguán|6
Mácula|7
Los ignorantes|8
Donde todo termina|2
Gente de bien|8
La máquina de los sueños|8
Made to Shine|5
Mi caballo|2
Vástago|9
'''}
# dirección que el PDF no da: canal Sello Editorial Débora Arango, https://youtu.be/SXDhMr6nLDs (6:14)
DIRECTOR = {'La barbería': 'Juan Esteban Aristizábal'}
# dato de la obra que el PDF abrevia o trae distinto; la obra manda (almacén o TMDB, 24 nov)
OBRA = {
    'Mu-ki-ra': {'pais': 'Colombia, España', 'anio': 2026},                       # PDF: Estados Unidos, 2022
    'Tres hermanas': {'anio': 2025}, 'Estancia': {'anio': 2024},                  # almacén
    'El juego de la vida': {'anio': 2025, 'director': 'Mario Andrés Ruiz Zuluaga'},
    'Los iniciados': {}, '130 hermanos': {'pais': 'Chile, Costa Rica', 'anio': 2021},
    'Die Odyssee': {'pais': 'Francia, Alemania, República Checa'},                # PDF: Alemania
    'Bye Bye Tiberias': {'pais': 'Francia, Bélgica, Palestina'},                  # PDF: Palestina
    'Toni Erdmann': {'pais': 'Alemania, Austria, Francia, Rumania'},
    'Noviembre': {'pais': 'Colombia, Brasil, Noruega, México'},
    'Horizonte': {'pais': 'Colombia, Chile, Francia, Alemania, Luxemburgo'},
    'Llueve sobre Babel': {'pais': 'Colombia, Estados Unidos, España'},
    'Un poeta': {'pais': 'Colombia, Alemania, Suecia'},
    'Fiebre': {'pais': 'Chile, Perú, Brasil'},
    'The Unbreakable Boy': {'pais': 'Estados Unidos'},                            # PDF: Estados Unidos, India
    'A las 9 es la cita': {'anio': 2024}, 'Discómanos': {'anio': 2024},           # Feelsales; Bogoshorts 2024
    'Animero son de la muerte': {'anio': 2025}, 'Make up: El arte de amar': {'anio': 2025},
    'No te despiertes': {'anio': 2025, 'director': 'Hernán Velásquez'},
    'Suelo': {'anio': 2026}, 'Chaika': {'pais': 'Colombia, Cuba'}, 'Alpha': {'pais': 'Países Bajos, Eslovenia, Suiza'}, 'Almanya – Willkommen in Deutschland': {'anio': 2011},
}
TEXTOS = f'{REPO}/festivals/staging/festicine-antioquia-2026-sinopsis-cortas.json'
# La 2.ª línea de título del PDF (en español: «Un pedazo de cielo», «La odisea»…) no se usa.
# dirección mal escrita en el PDF (TMDB y la obra dicen otra)
IMPRESO = {'Campeones': 'Javier Fasser', 'Almanya – Willkommen in Deutschland': 'Yasemin Semdereli'}
ESTRENO = {'Ma, despierta': 'Estreno mundial', 'Fang i vidre': 'Estreno nacional',
           'La Miss': 'Estreno nacional', 'Aunque seamos islas': 'Estreno nacional'}


def filas(t):
    return [x.strip() for x in t.strip().splitlines() if x.strip()]


def parrilla():
    out = []
    for x in filas(PARRILLA):
        # «TV Cámaras | Microhistorias digitales»: la barra rodeada de espacios es del título
        c = [p.replace('\x00', ' | ') for p in x.replace(' | ', '\x00').split('|')]
        assert len(c) == 6, x
        out.append({'dia': f'2026-12-0{c[0]}', 'hora': c[1], 'sede': c[2], 'rotulo': c[3],
                    'titulo': c[4], 'nota': c[5]})
    return out


def obras():
    src = {'url': PDF, 'date': FECHA, 'tipo': 'festival-pdf'}
    out = []
    sec = {p['titulo']: p['rotulo'] for p in reversed(parrilla())}
    sec.update({'Subterráneo': 'Inauguración', 'Pacífico': 'Inauguración'})
    for x in filas(OBRAS):
        t, d, pais, an, mi = x.split('|')
        o = {'titulo': t, 'director': d, 'pais': pais, 'anio': int(an), 'duracion_min': int(mi),
             'tipo': 'corto' if int(mi) < 40 else 'largo', 'seccion': sec[t], '_src': src}
        if t in IMPRESO:
            o['impreso'] = IMPRESO[t]
        if t in ESTRENO:
            o['premiere'] = ESTRENO[t]
        out.append(o)
    for prog, tab in PANDORA.items():
        for x in filas(tab):
            t, d, cat, mi = x.split('|')
            out.append({'titulo': t, 'director': d, 'pais': 'Colombia', 'duracion_min': int(mi), 'tipo': 'corto',
                        'categoria': cat, 'seccion': 'Caja de Pandora', 'programa': prog, '_src': src})
    for prog, tab in MUESTRAS.items():
        for x in filas(tab):
            t, mi = x.rsplit('|', 1)
            out.append({'titulo': t, 'duracion_min': int(mi), **({'director': DIRECTOR[t]} if t in DIRECTOR else {}), 'tipo': 'corto',
                        'seccion': 'Muestra especial y conversación', 'programa': prog, '_src': src})
    txt = json.load(io.open(TEXTOS, encoding='utf-8'))['obras']
    for o in out:
        o.update(OBRA.get(o['titulo'], {}))
        if o['titulo'] in txt:
            o['sinopsis'], o['synopsis_en'] = txt[o['titulo']]['es'], txt[o['titulo']]['en']
    return out


if __name__ == '__main__':
    p, o = parrilla(), obras()
    ts = {x['titulo'] for x in o}
    progs = {x.get('programa') for x in o}
    for f in p:   # toda función de obra apunta a una obra o a un programa
        if f['rotulo'] in ('Película', 'Película familiar', 'Competencia Internacional de Óperas Primas', 'Clausura'):
            assert f['titulo'] in ts, f
    assert len(p) == 79 and len(filas(PANDORA['Caja de Pandora: Primera sesión'])) == 9, len(p)
    json.dump({'_provenance': provenance(PDF, metodo='PDF a ojo + lectura ciega + OCR', publicado=FECHA),
               'obras': o, 'parrilla': p}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(p)} funciones y actividades, {len(o)} obras → {os.path.relpath(OUT, REPO)}')
