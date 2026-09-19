#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-ig-dias.py — la programación día por día que el festival puso en IG.

LA SEGUNDA FUENTE DE LA MISMA PARRILLA. El 18 de septiembre el festival publicó
DOS cosas: el PDF de programación en su web y, horas después, un post por día en
Instagram con la lista de funciones. No son copias: el post trae cosas que el
PDF no dice y en tres puntos lo contradice. Tenerlas las dos permite cruzarlas,
que es la única forma de saber si lo que publicamos es verdad.

QUÉ TRAE IG Y EL PDF NO:

  · EL PRECIO. El PDF solo marca COSTO en dos actividades y la web del festival
    dice que «todas las actividades son de acceso libre». Los posts muestran que
    las funciones de Fama - Cinespiral piden «aporte voluntario desde $20k o
    acreditación» —tres— y dan el precio completo de la fiesta de clausura.
    Publicar como gratis algo que se paga es el peor error de esta app.
  · QUIÉN ESTARÁ. «Presencia de la productora», «presencia de la directora»:
    conversatorios que el sello del PDF no marca.

EN QUÉ SE CONTRADICEN (no se resuelve acá: se reporta, y se le pregunta al
festival):

  · La MUESTRA DE CORTOMETRAJES del sábado 26: el PDF y la lámina la ponen a
    las 10:00 y el pie del post, de «1:00 p.m. a 8:00 p.m.». Se publica 10:00.
  · «La Marcha del Hambre» tiene página propia en el PDF (viernes 25, 8:00 PM)
    y NO aparece en el post de ese día.
  · «Entrelazados»: el PDF se contradice solo —badge 7:20 PM, campo HORA 7:00
    pm— y el post la pone a las 7:00 junto a «Cómo limpiar un espejo».

Y UNA FUNCIÓN QUE SOLO ESTÁ EN IG: «Largometrajes UBPD», sábado 26 de 10:00 a
12:00. El post no dice dónde, así que no se publica — la misma regla de siempre.

TRANSCRITO A MANO, y aquí sí es lo correcto: son siete posts leídos en el
navegador con sesión, y el pie de Instagram no se puede parsear sin ella. Lo que
se transcribe es lo que el festival escribió, verbatim.

Esc.  festivals/staging/ficma-2026-ig-dias.json
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/ficma-2026-ig-dias.json'
IG = 'https://www.instagram.com/cinemanizales_ficma/p/'

# EL POST DEL SÁBADO 19 EXISTE Y CASI SE NOS PASA. En la grilla del perfil se ve
# como «Photo shared by FICMA 17…», sin pie: lo descarté mirando ese preview en
# vez de abrirlo, y dije que ese día no tenía post de programación. Lo tiene, es
# un carrusel de NUEVE LÁMINAS —una por función— y ahí estaba lo que faltaba.
# Un post no se juzga por su preview.
POSTS = {
    '2026-09-19': 'DdcEwsJmvmy',
    '2026-09-20': 'DdcEFYkGnCR', '2026-09-21': 'DdcDr3Zmtjf',
    '2026-09-22': 'DdcDTCamlsP', '2026-09-23': 'DdcC4ydG1Jt',
    '2026-09-24': 'DdcCLKum08D', '2026-09-25': 'DdcBl--G0Ub',
    '2026-09-26': 'DdcA4G8m6O0',
}

# EL ACCESO, verbatim del post. Va por TÍTULO porque es de la sede y se repite:
# las tres funciones de Fama llevan la misma línea.
ACCESO = {
    'La infiltrada': 'Aporte voluntario desde $20k o acreditación',
    'La Grazia': 'Aporte voluntario desde $20k o acreditación',
    'O Último Azul': 'Aporte voluntario desde $20k o acreditación',
    'Noche de Vinilos': '20k (incluye Poker) o acreditación',
    'Sonora Vol. 4': 'Preventa $30k · en sitio $45k · gratis con acreditación',
}

# EL CONTENIDO QUE SOLO ESTÁ EN EL POST DE UN TERCERO. El concierto sinfónico
# del jueves 24 lo anuncia la Orquesta Sinfónica de Caldas —etiquetando al
# festival— con su programa completo. El PDF solo dice «Concierto Sinfónico».
FICHA_EXTRA = {
    'Concierto Sinfónico': {
        'director': 'Orquesta Sinfónica de Caldas · dirige Leonardo Marulanda',
        'sinopsis': 'Una noche de música sinfónica con la Orquesta Sinfónica de '
                    'Caldas bajo la dirección de Leonardo Marulanda. En el programa: '
                    '«Capricho español», Op. 34 de Nikolái Rimski-Kórsakov; «Vals '
                    'triste» de Jean Sibelius; «Petite Suite» de Claude Debussy; y la '
                    '«Danza ritual del fuego» de Manuel de Falla.',
        '_src': 'https://www.instagram.com/p/DdcUAxysh0p/ (@sinfonicadecaldas)'},
}

# Conversatorio o presencia, dicho en el post y NO marcado en el sello del PDF.
PRESENCIA = {
    'En Tierra': 'Presencia de la productora',
    'Llueve sobre Babel': 'Presencia de la directora',
    'Bien inmueble': 'Presencia del director',
    'El Juego de la Vida': 'Presencia del director',
    'Andariega': 'Presencia del director',
    'Habitante': 'Presencia del director',
    'Apuntes sobre anomalías y fantasmas': 'Presencia del director',
}

# LO QUE EL POST DICE DISTINTO DEL PDF. Cada entrada dice qué se publica y por
# qué; lo que no está acá se publica como lo dice el PDF.
DISCREPA = {
    # LA FUNCIÓN INAUGURAL: 7:00 EL CORTO, 7:30 EL LARGO. Y aquí me equivoqué
    # yo. Los posts sueltos de las dos obras dicen «7:00 p. m.» —el del largo
    # también— así que las publiqué a las dos a las 19:00, razonando que era una
    # sola función. Las LÁMINAS del carrusel del sábado lo desmienten: la 8 dice
    # 7:00 PM para «Que el cielo nos perdone» (17 min) y la 9 dice 7:30 PM para
    # «El hogar fue sepultado» (92 min). Coinciden con el PDF, que decía lo
    # mismo. Manda eso: se publica 19:00 y 19:30.
    #
    # La lección es del método, no del dato: el pie de un post redondea, la
    # lámina es el programa. Si las dos están, gana la lámina.
    # «Entrelazados» NO está acá aunque el post también opine: su caso se
    # resuelve donde nace, en HORA_ERRATA de ficma-2026-parse.py, porque lo que
    # hay que explicar es que la LÁMINA se contradice. Declararlo dos veces
    # obligaba a seguir dos saltos para entender una sola hora.
    # LA MUESTRA DE CORTOS DEL SÁBADO 26 NO ESTÁ ACÁ (19 sep). El pie del post
    # dice «1:00 p.m. a 8:00 p.m.» y la publiqué así. Juan: «es 10 am, el PDF es
    # claro» — y la LÁMINA del mismo post también dice 10:00 AM, dos veces
    # (badge y campo HORA). Un pie contra dos imágenes: ganan las imágenes.
    # Y mi argumento de que «a las 10:00 el post pone otra función en esa sede»
    # era falso: los Largometrajes UBPD no dicen sede.
}

# EN EL POST Y NO EN EL PDF. Sin sede no se publica: es la misma regla que dejó
# fuera la masterclass de Andrés Buitrago.
SOLO_EN_IG = {
    'Largometrajes UBPD': {
        'dia': '2026-09-26', 'hora': '10:00', 'hasta': '12:00',
        'nota': 'Unidad de Búsqueda de Personas dadas por Desaparecidas. El post NO '
                'dice sede. No se publica hasta que el festival diga dónde.'},
}

# EN EL PDF Y NO EN EL POST DE SU DÍA.
SOLO_EN_PDF = {
    'La Marcha del Hambre': 'tiene página propia en el PDF (viernes 25, badge 8:00 PM, '
                            '90 min) y el post del viernes no la nombra. Se publica '
                            '—el programa oficial es fuente suficiente— y se pregunta.',
}


def main():
    json.dump({'_provenance': provenance(
        'Instagram @cinemanizales_ficma — un post por día con la programación, '
        'publicados el 18 sep 2026',
        que_aporta='el precio de las funciones que no son gratis y la presencia de '
                   'directores; y el contraste, función por función, contra el PDF',
        metodo='leídos en el navegador CON SESIÓN y transcritos verbatim: el pie de '
               'Instagram no se obtiene sin ella',
        posts={d: IG + s + '/' for d, s in POSTS.items()}),
        'acceso': ACCESO, 'presencia': PRESENCIA, 'ficha_extra': FICHA_EXTRA,
        'discrepa': DISCREPA,
        'solo_en_ig': SOLO_EN_IG, 'solo_en_pdf': SOLO_EN_PDF},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(POSTS)} días · {len(ACCESO)} con precio · {len(PRESENCIA)} con '
          f'presencia · {len(DISCREPA)} discrepancias · {len(SOLO_EN_IG)} solo en IG')


if __name__ == '__main__':
    main()
