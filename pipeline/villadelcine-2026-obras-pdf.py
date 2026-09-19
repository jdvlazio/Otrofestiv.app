#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-obras-pdf.py — las fichas del PDF, obra por obra.

QUÉ SACA. Las páginas 12–50 del programa traen una ficha por obra, agrupadas
bajo la cabecera de su programa («NUEVAS MIRADAS TRÁNSITO»), que es exactamente
el nombre con que la retícula anuncia el bloque. De cada ficha salen el título,
la dirección, la duración, el país, el género y la SINOPSIS EN ESPAÑOL —que la
web no tiene: la web las publica en inglés—.

CÓMO SE CORTA UNA FICHA. La única línea fiable es la de dirección: «Dir. X» o
«DIR. X». A partir de ella se lee hacia arriba (título y, antes, el formato:
WIP, VERTICAL, VIDEO MUSICAL, CORTOMETRAJE NACIONAL…) y hacia abajo (la línea
de metadatos y la sinopsis). Anclar en el título no funciona: unos van en
mayúsculas y otros no, y varias páginas traen dos y hasta tres obras seguidas.

LO QUE NO SE INVENTA. Una ficha sin línea de metadatos se queda sin duración y
sin país —«QUAZAR» es una de ellas—, y esos huecos los llena después el cruce
con la web o con TMDB, nunca este paso. Una obra sin «Dir.» no se publica como
obra: se anota en `sin_direccion` para mirarla.

Lee   festivals/staging/villadelcine-2026-parrilla.json  (bloque `fichas`)
Esc.  festivals/staging/villadelcine-2026-obras-pdf.json
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PAR = f'{ST}/villadelcine-2026-parrilla.json'
OUT = f'{ST}/villadelcine-2026-obras-pdf.json'

RE_DIR = re.compile(r'^\s*(?:Dir|DIR|Dirección|DIRECCIÓN)\.?\s*[:.]?\s*(.+)$')
# «0:17:40 | México | Ficción» o «120 minutos | Ficción / Drama»
RE_META = re.compile(r'^\s*(?:(\d{1,2}):(\d{2}):(\d{2})|(\d{1,3})\s*minutos?)\s*\|?\s*(.*)$')
RE_SOLO_DUR = re.compile(r'^\s*(\d{1,2}):(\d{2}):(\d{2})\s*$')
# El FORMATO que el festival imprime encima del título. Verbatim, tal como lo
# escribe: es su vocabulario y no se normaliza.
FORMATOS = {
    'WIP', 'VERTICAL', 'CELULAR', 'IA', 'VR', 'VIDEO MUSICAL', 'ESCOLAR',
    'INFANTIL', 'YOUNGFILM', 'APASIONADO NACIONAL', 'CORTOMETRAJE NACIONAL',
    'CORTOMETRAJE INTERNACIONAL', 'ÓPERA PRIMA NACIONAL', 'OPERA PRIMA NACIONAL',
    'ÓPERA PRIMA INTERNACIONAL', 'PODEROSAS', 'VOCES', 'PLANETA', 'RAÍCES',
    'KOREBAJU', 'BOYACÁ EN LOS CAMPOS', 'INT', 'DISCAPACIDADES',
}
# EL PAÍS ES UNA LISTA, NO UNA HEURÍSTICA. El comodín «varias palabras
# separadas por coma o barra» se tragaba los géneros: «Ficción / Drama /
# Comedia / Fantasia» entraba como país y la app lo iba a pintar con un globo
# terráqueo en vez de una bandera. Un país o está en la lista o no es país.
PAISES = ['colombia', 'méxico', 'mexico', 'brasil', 'brasi', 'argentina', 'chile',
          'perú', 'peru', 'ecuador', 'venezuela', 'uruguay', 'paraguay', 'bolivia',
          'guatemala', 'cuba', 'panamá', 'costa rica', 'españa', 'france', 'francia',
          'italia', 'italy', 'alemania', 'portugal', 'reino unido', 'inglaterra',
          'bélgica', 'belgium', 'holanda', 'países bajos', 'suiza', 'austria',
          'suecia', 'noruega', 'dinamarca', 'polonia', 'rusia', 'ucrania', 'grecia',
          'turquía', 'usbekistán', 'uzbekistán', 'uzbekistan', 'india', 'china',
          'japón', 'taiwán', 'taiwan', 'corea', 'irán', 'israel', 'nigeria',
          'sudáfrica', 'australia', 'canadá', 'usa', 'estados unidos', 'spain']
# Como el festival las escribe → como se escriben. Solo ortografía: no se
# cambia el país, se corrige la letra.
ERRATA_PAIS = {'brasi': 'Brasil', 'usbekistán': 'Uzbekistán', 'mexico': 'México',
               'peru': 'Perú', 'taiwan': 'Taiwán', 'uzbekistan': 'Uzbekistán',
               'france': 'Francia', 'italy': 'Italia', 'belgium': 'Bélgica',
               'spain': 'España'}


def es_pais(t):
    """Una celda de metadatos es el país si TODAS sus partes lo son: «Brasil,
    India, Italia, España» sí; «Ficción y Drama» no."""
    partes = [x.strip().lower() for x in re.split(r'[,/]| y ', t or '') if x.strip()]
    return bool(partes) and all(x in PAISES for x in partes)


def limpia_pais(t):
    partes = [x.strip() for x in re.split(r'([,/])', t or '') if x.strip()]
    return ''.join(ERRATA_PAIS.get(x.lower(), x) if x not in ',/' else x + ' '
                   for x in partes).strip()


# LAS CUATRO PÁGINAS SIN «Dir.». No son obras en competencia: son un tributo,
# dos reconocimientos y dos talleres infantiles, y por eso el festival no les
# imprime dirección. Se declaran con lo que dice su página —no se fuerzan por
# el parser ni se dejan caer— y salen marcadas como actividad.
IRREGULARES = [
    {'pagina': 14, 'titulo': 'AQUILEO VENGANZA', 'credito': 'Ciro Durán',
     'rol': 'tributo', 'nota': 'TRIBUTO A CIRO DURÁN. Filmada en Villa de Leyva en '
            '1968; se proyecta por primera vez donde nació'},
    {'pagina': 15, 'titulo': 'FUNDACIÓN PATRIMONIO FILMICO', 'credito': '',
     'rol': 'reconocimiento', 'nota': 'POR SUS 40 AÑOS'},
    {'pagina': 15, 'titulo': 'MABEL VELOSA', 'credito': '',
     'rol': 'reconocimiento', 'nota': 'CAMINOS DEL TIEMPO'},
    {'pagina': 21, 'titulo': 'CIANOTIPIA', 'credito': 'Isabella Bobadilla Monsalve',
     'rol': 'tallerista',
     'nota': 'Laboratorio de experimentación y fotografía analógica'},
    {'pagina': 22, 'titulo': 'FARMEANDO EL TUNJO: CREACIÓN CINEMATOGRÁFICA CON '
                             'INTELIGENCIA ARTIFICIAL',
     'credito': 'Jimena Guerrero, Vanessa Vega y PiPo Aranguren',
     'rol': 'talleristas', 'nota': 'el título va DEBAJO del crédito y partido en '
            'nueve líneas por la caja de texto de Canva'},
]


# Palabras que NO se capitalizan dentro de un título en español, y siglas que
# SÍ van enteras en mayúscula. Ver `a_titulo`.
# LA CAJA DE LOS TÍTULOS QUE LA WEB NO TRAE, escrita a mano. Se respeta la
# ortografía del festival; lo único que cambia es la mayúscula sostenida de la
# plantilla del PDF.
CAJA = {
    'UN POETA': 'Un poeta',
    'LLUEVE SOBRE BABEL': 'Llueve sobre Babel',
    'AQUILEO VENGANZA': 'Aquileo Venganza',
    'FUNDACIÓN PATRIMONIO FILMICO': 'Fundación Patrimonio Fílmico',
    'MABEL VELOSA': 'Mabel Velosa',
    'MI TESORO': 'Mi tesoro',
    'LA ÚLTIMA HISTORIA': 'La última historia',
    'LE JEUNE SOFIANE': 'Le jeune Sofiane',
    'CIANOTIPIA': 'Cianotipia',
    'BEHIND THE DOOR': 'Behind the Door',
    'CON LA MANO ARRIBA': 'Con la mano arriba',
    'AMOR A PRIMERA VISTA': 'Amor a primera vista',
    'SABOR A MI (ACÚSTICO / BOLERO JAZZ)': 'Sabor a mí (acústico / bolero jazz)',
    'MOMENTOS EN MOVIMIENTO. PRIMEROS PASOS DEL BALLET EN COLOMBIA.':
        'Momentos en movimiento. Primeros pasos del ballet en Colombia',
    'KOREBAJU PAI REKOCHO': 'Korebaju Pai Rekocho',
    'CUADRILEROS ORGULLO Y LEGADO': 'Cuadrileros, orgullo y legado',
    'THE GUANENTÁ SYMPHONY': 'The Guanentá Symphony',
    'FARMEANDO EL TUNJO: CREACIÓN CINEMATOGRÁFICA CON INTELIGENCIA ARTIFICIAL':
        'Farmeando el Tunjo: creación cinematográfica con inteligencia artificial',
}

MINUS = {'a', 'al', 'ante', 'con', 'contra', 'de', 'del', 'desde', 'e', 'el', 'en',
         'entre', 'hacia', 'hasta', 'la', 'las', 'lo', 'los', 'más', 'ni', 'o', 'para',
         'por', 'que', 'se', 'según', 'si', 'sin', 'sobre', 'su', 'sus', 'tras', 'un',
         'una', 'unos', 'unas', 'y', 'the', 'of', 'and', 'in', 'on', 'to', 'for', 'a'}
SIGLAS = {'IA', 'VR', 'WIP', 'USA', 'UBPD', 'AI', 'DASC', 'ENACC', 'TV', 'II', 'III'}


def a_titulo(t, natural=None):
    """«AMOR A PRIMERA VISTA» → «Amor a primera vista».

    El PDF imprime TODOS los títulos en mayúscula sostenida. Eso es una
    decisión tipográfica de la plantilla, no el nombre de la obra, y publicarlo
    así se lee a gritos (además de romper el gate de la app).

    PRIMERO, LA WEB DEL PROPIO FESTIVAL: publica los mismos títulos en caja
    natural, así que si la obra está allí se usa SU escritura y no la nuestra.
    Es la diferencia entre respetar cómo lo escribe el festival y adivinarlo:
    ninguna regla automática sabe que en «Sierra: el álbum mortuorio» la sierra
    va en mayúscula y el álbum no.

    SOLO SI NO ESTÁ EN LA WEB se busca en CAJA, que es una lista escrita a
    mano. NO se aplica una regla automática: probé con caja de oración y
    «LLUEVE SOBRE BABEL» quedó «Llueve sobre babel». Ninguna regla sabe que
    Babel es un nombre propio y el álbum no, así que las pocas que la web no
    trae se escriben una por una, mirando la obra.
    """
    # CAJA va PRIMERO: «BEHIND THE DOOR» y «AMOR A PRIMERA VISTA» están en
    # mayúscula sostenida también en la web, así que preferir la web sin más
    # las dejaba gritando. La lista escrita a mano es una decisión tomada
    # mirando la obra y gana sobre las dos fuentes.
    if t.strip() in CAJA:
        return CAJA[t.strip()]
    return natural or t


def _sinacento(x):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', x or '')
                   if unicodedata.category(c) != 'Mn').lower()


def parte_cabecera(cab):
    """«NUEVAS MIRADAS TRÁNSITO» → (sección, programa). Las secciones son las
    once que aprobó Juan; lo que sobra del nombre es el programa."""
    SECC = ['NARRATIVAS DIVERGENTES', 'PROGRAMACIÓN INFANTIL', 'LENGUAJES EMERGENTES',
            'NUEVAS MIRADAS', 'RUMBO A LOS MACONDO', 'EXHIBICIÓN ESPECIAL',
            'EVENTOS ESPECIALES', 'TERRITORIOS', 'INDUSTRIA', 'RUTA ACADÉMICA',
            'COMUNICACIONES']
    c = re.sub(r'\s+', ' ', cab).strip()
    for s in SECC:
        if c.upper().startswith(s):
            return s.title().replace('Rumbo A Los Macondo', 'Rumbo a los Macondo'), \
                   c[len(s):].strip()
    return '', c


def main():
    d = json.load(open(PAR, encoding='utf-8'))
    # los mismos títulos, como los escribe la web del festival
    natural = {}
    web_p = f'{ST}/villadelcine-2026-obras-web.json'
    if os.path.exists(web_p):
        for o in json.load(open(web_p, encoding='utf-8'))['obras']:
            natural[re.sub(r'[^a-z0-9]+', '', _sinacento(o['titulo']))] = o['titulo']
    obras, sin_dir = [], []

    for f in d['fichas']:
        seccion, programa = parte_cabecera(f['cabecera'])
        ls = [x.strip() for x in f['texto'].split('\n') if x.strip()]
        idx = [i for i, l in enumerate(ls) if RE_DIR.match(l)]
        for n, i in enumerate(idx):
            director = RE_DIR.match(ls[i]).group(1).strip()
            crudo_t = ls[i - 1].strip() if i else ''
            titulo = a_titulo(crudo_t, natural.get(
                re.sub(r'[^a-z0-9]+', '', _sinacento(crudo_t))))
            formato = ''
            if i >= 2 and ls[i - 2].strip().upper() in FORMATOS:
                formato = ls[i - 2].strip()
            # hacia abajo: metadatos (si los hay) y sinopsis hasta la ficha siguiente
            fin = idx[n + 1] - 1 if n + 1 < len(idx) else len(ls)
            if n + 1 < len(idx) and idx[n + 1] >= 2 and \
                    ls[idx[n + 1] - 2].strip().upper() in FORMATOS:
                fin = idx[n + 1] - 2
            cuerpo = ls[i + 1:fin]
            dur_min, pais, genero = None, '', ''
            if cuerpo:
                m = RE_META.match(cuerpo[0])
                solo = RE_SOLO_DUR.match(cuerpo[0])
                if m and (m.group(1) or m.group(4)):
                    if m.group(1):
                        dur_min = int(m.group(1)) * 60 + int(m.group(2)) + \
                                  (1 if int(m.group(3)) >= 30 else 0)
                    else:
                        dur_min = int(m.group(4))
                    resto = [x.strip() for x in (m.group(5) or '').split('|') if x.strip()]
                    for r in resto:
                        if not pais and es_pais(r):
                            pais = limpia_pais(r)
                        elif not genero:
                            genero = r
                    cuerpo = cuerpo[1:]
                elif solo:
                    dur_min = int(solo.group(1)) * 60 + int(solo.group(2)) + \
                              (1 if int(solo.group(3)) >= 30 else 0)
                    cuerpo = cuerpo[1:]
            obras.append({
                'titulo': titulo, 'director': director,
                'seccion': seccion, 'programa': programa,
                **({'formato': formato} if formato else {}),
                'duracion_min': dur_min, 'pais': pais, 'genero': genero,
                'sinopsis': ' '.join(cuerpo).strip(),
                'pagina': f['pagina'],
                '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                                f'p{f["pagina"]}', 'date': '2026-09-19'},
            })
        for irr in [x for x in IRREGULARES if x['pagina'] == f['pagina']]:
            cuerpo = [l for l in ls if len(l) > 60]
            obras.append({
                'titulo': a_titulo(irr['titulo']), 'director': irr['credito'],
                'seccion': seccion, 'programa': programa,
                'rol_credito': irr['rol'], '_nota': irr['nota'],
                'es_actividad': True,
                'duracion_min': None, 'pais': '', 'genero': '',
                'sinopsis': ' '.join(cuerpo).strip(),
                'pagina': f['pagina'],
                '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                                f'p{f["pagina"]}', 'date': '2026-09-19'},
            })
        if not idx and not any(x['pagina'] == f['pagina'] for x in IRREGULARES):
            sin_dir.append({'pagina': f['pagina'], 'cabecera': f['cabecera'],
                            'texto': f['texto'][:180]})

    json.dump({'_provenance': provenance(
        'PROGRAMACIÓN «Caminos del tiempo» 2026, páginas 12–50: una ficha por obra',
        que_aporta='título, dirección, duración, país, género y la SINOPSIS EN '
                   'ESPAÑOL, además del programa al que pertenece cada obra',
        url='https://villadelcine.com/wp-content/uploads/2026/09/'
            'Programacion-caminos-del-tiempo-2026_compressed.pdf',
        metodo='cada ficha se corta por su línea de dirección, que es la única '
               'constante: el título va en mayúsculas o no según la página, y hay '
               'páginas con dos y tres obras'),
        'obras': obras, 'sin_direccion': sin_dir},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    con_dur = sum(1 for o in obras if o['duracion_min'])
    con_sin = sum(1 for o in obras if o['sinopsis'])
    progs = {(o['seccion'], o['programa']) for o in obras}
    print(f'{len(obras)} obras · {con_dur} con duración · {con_sin} con sinopsis · '
          f'{len(progs)} programas → {os.path.basename(OUT)}')
    for s, p in sorted(progs):
        n = sum(1 for o in obras if (o['seccion'], o['programa']) == (s, p))
        print(f'   {n:>3}  {s or "—":24} {p}')
    if sin_dir:
        print(f'⚠ {len(sin_dir)} página(s) de ficha sin ninguna línea «Dir.»: '
              + ', '.join(f'p{x["pagina"]} ({x["cabecera"][:28]})' for x in sin_dir))


if __name__ == '__main__':
    main()
