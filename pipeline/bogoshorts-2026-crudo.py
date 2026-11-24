#!/usr/bin/env python3
"""bogoshorts-2026-crudo.py — la grilla del 24.º BOGOSHORTS (1–8 dic 2026) → crudo.

LA FUENTE: 24BSFF_programacion2026.pdf (una página, Illustrator, CON TEXTO), del
23 oct 2026, en fuentes/bogoshorts-2026/programacion2026.pdf. Se lee con
`pdftotext -bbox` —coordenadas de cada palabra—, no con -layout: el layout
corría las columnas (ponía CN-EXP el martes 1, que es el miércoles 2).

  · COLUMNA = día: la x del centro de la celda contra la de su encabezado.
  · FILA = hora: la etiqueta de hora más cercana DENTRO del espacio; los
    espacios son bandas de y declaradas abajo (ESPACIOS), medidas en el PDF.
  · Una hora escrita dentro de la celda («2:00 p.m.», «11:30 a.m.») manda
    sobre la de la fila.

Los códigos se traducen al nombre con la LEYENDA de la propia grilla (tabla
LEYENDA, copiada verbatim del texto del PDF). Grupo de la leyenda = sección.

Acceso: el PDF dice «* Entrada con invitación.» y nada más; la boletería no está
publicada → lib.DESCONOCIDO, salvo las * (invitación, en `acceso` verbatim).
«** Q&A con realizadores» → has_qa.

Lo que NO entra como función, a propósito (DESCARTES): las franjas de varios días
(BFM Film Market, Acreditaciones) y Retina Latina (en línea, «Disponibles entre
el 1 y el 15 de diciembre»). La cobertura inversa de bogoshorts-2026-verificar.py
las cuenta.

Lee   fuentes/bogoshorts-2026/programacion2026.pdf
      festivals/staging/bogoshorts-2026-cortos.json     (los cortos por programa, del catálogo oficial: MANDA)
      festivals/staging/bogoshorts-2026-programas.json  (boletines e IG: solo si el catálogo no trae el código)
Esc.  festivals/staging/bogoshorts-2026-crudo.json
"""
import html, io, unicodedata, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance, DESCONOCIDO  # noqa: E402

PDF = f'{REPO}/fuentes/bogoshorts-2026/programacion2026.pdf'
URL = 'https://info.bogoshorts.com/sccs/prensa/2026/docs_2026/24BSFF_programacion2026.pdf'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-crudo.json'
PROG = f'{REPO}/festivals/staging/bogoshorts-2026-programas.json'
_CM = f'{REPO}/festivals/staging/bogoshorts-2026-cinemateca.json'   # bogoshorts-2026-cinemateca.py
BOLETA = {(c['dia'], c['hora'], c['sala']): c for c in json.load(open(_CM, encoding='utf-8'))['funciones']} \
    if os.path.exists(_CM) else {}
CORTOS = f'{REPO}/festivals/staging/bogoshorts-2026-cortos.json'
DIAS = ['2026-12-01', '2026-12-02', '2026-12-03', '2026-12-04',
        '2026-12-05', '2026-12-06', '2026-12-07', '2026-12-08']
X_MIN, X_MAX = 209, 852          # la grilla; a la derecha (x≥865) está la leyenda

# (y desde, y hasta, sede, sala) — bandas de los espacios, medidas en el PDF
ESPACIOS = [            # grilla republicada el 13 nov 2026 (medida en esa versión)
    (90, 110, 'Teatro Jorge Eliécer Gaitán', ''),
    (110, 131, 'City U', ''),
    (131, 172, 'City U', 'Lounge BFM Plazoleta UHeart'),
    (172, 317, 'Cinemateca de Bogotá', 'Sala Capital'),
    (317, 399, 'Cinemateca de Bogotá', 'Sala 2'),
    (399, 482, 'Cinemateca de Bogotá', 'Sala 3'),
    (482, 503, 'Cinemateca de Bogotá', 'Taller de la imagen'),
    (503, 544, 'Cinemateca de Bogotá Sede Fontanar del Río', ''),
    (544, 585, 'Teatro El Parque', ''),
    (585, 647, 'Alianza Francesa', ''),
    (647, 668, 'Alianza Francesa', 'Sótano 1'),
    (668, 709, 'Centro Ático', ''),
    (709, 730, 'CEFE', ''),
    (730, 771, 'Teatro Delia Zapata Olivella', ''),
    (771, 792, 'Teatro al aire libre La Media Torta', ''),
    (792, 813, 'Sala Gaitán Antigua Cinemateca', ''),
    (813, 833, 'Fiestas', ''),
    (833, 860, 'Retina Latina', ''),
]
# código → (grupo de la leyenda = sección, nombre del programa), verbatim del PDF
LEYENDA = {
    'SO-FCO': ('Fuera de Competencia', 'Selección Oficial'),
    'CN-FIC': ('Competencia Nacional', 'Ficción'), 'CN-DOC': ('Competencia Nacional', 'Documental'),
    'CN-ANI': ('Competencia Nacional', 'Animación'), 'CN-EXP': ('Competencia Nacional', 'Experimental'),
    'CN-VC': ('Competencia Nacional', 'Videoclip'),
    'CI-FIC': ('Competencia Internacional', 'Ficción'), 'CI-DOC': ('Competencia Internacional', 'Documental'),
    'CI-ANI': ('Competencia Internacional', 'Animación'), 'CI-EXP': ('Competencia Internacional', 'Experimental'),
    'CI-VC': ('Competencia Internacional', 'Videoclip'), 'CI-CP': ('Competencia Internacional', 'Corto periodístico'),
    'CVR': ('Competencia VR (Realidad virtual)', 'Competencia realidad virtual'),
    'F3-01': ('Fanático Freak Fantástico F3', 'Programa 01'), 'F3-02': ('Fanático Freak Fantástico F3', 'Programa 02'),
    'F3-03': ('Fanático Freak Fantástico F3', 'Programa 03'),
    'F3-ALIENS': ('Fanático Freak Fantástico F3', 'Aliens: 40 años de contacto hostil'),
    # la leyenda escribe «F3 - PIN»; la celda, «F3-PINI»
    'F3-PINI': ('Fanático Freak Fantástico F3', 'Jairo Pinilla, el origen de una obsesión'),
    'CON-LATAM': ('Conexión', 'Latinoamérica'), 'CON-ESP': ('Conexión', 'España'),
    'CON-LTX': ('Conexión', 'Latinxs en Norteamérica'), 'CON-BRA': ('Conexión', 'Brasil'),
    'PAC-FIC': ('Panorama', 'Colombia Ficción'), 'PAC-DOC': ('Panorama', 'Colombia Documental'),
    'PAC-EXP': ('Panorama', 'Colombia Experimental'),
    'ES-METRO': ('Especiales', 'Metrópolis: cuerpos del futuro'),
    'ES-ASTRO': ('Especiales', 'Especial astrológico: presagios del cielo'),
    'ES-MILES': ('Especiales', 'Miles Davis, 100 años de jazz'),
    'ES-ZOD': ('Especiales', 'Especial 40 años Caballeros del Zodiaco'),
    'ES-PER': ('Especiales', 'Volviendo a Persépolis sin Marjane Satrapi'),   # leyenda: «ES -PER»
    'ES-NEXOS': ('Especiales', 'Nexos femeninos'),
    'CITY-BCN1': ('Viva la ciudad', 'Sinfonías femeninas desde Barcelona'),
    'CITY-BCN2': ('Viva la ciudad', 'Año Gaudí, la ciudad animada'),
    'FI-ENA': ('Cortofilia', 'También los enanos empezaron pequeños'), 'FI-LARGO': ('Cortofilia', 'Largo de cortos'),
    'FES-LADRA': ('Festivaleando', 'El perro que ladra'),
    'WT-CRO': ('World Tour', 'Croacia'),
    'CHI-KIDS': ('chiquiSHORTS', 'BOGOSHORTS Kids'), 'CHI-ANCY': ('chiquiSHORTS', 'Annecy Kids'),
    'CLC-ADO': ('Colecciones', 'Crecer'), 'CLC-CINE': ('Colecciones', 'Cine dentro del cine'),
    'CLC-DIVX': ('Colecciones', 'Diversidades'), 'CLC-AMO': ('Colecciones', 'El amor es corto'),
    'CLC-FUT': ('Colecciones', 'El mundo es un balón'),
}
DESCARTES = {'Fiestas': 'fila «Fiestas» (13 nov): la grilla no dice dónde son (la Noche Sagitario entra con su sede, IG 23 nov)',
             'BFM': 'franja de industria de varios días, no una función',
             'Acreditaciones': 'punto de acreditación, no una función',
             'City U': 'la fila de City U es la franja del BFM - BOGOSHORTS Film Market (industria, varios días)',
             'Alianza Francesa Sótano 1': 'Acreditaciones, 10:00 a.m. - 6:00 p.m.: no es una función',
             'Retina Latina': 'FI-ENA1 / FI-ENA2 en línea, «Disponibles entre el 1 y el 15 de diciembre»: sin sala ni hora',
             'Franja Encuentros Cercanos Competencia Nacional***': 'rótulo de la fila (flecha al mié 2), no una celda'}
# EL NOMBRE del programa cuando el de la leyenda no basta: «Ficción 1» existe en la
# Competencia Nacional y en la Internacional. Se usa el rótulo del catálogo
# («Competencia Nacional Ficción - CN-FIC1») con el número que le pone la agenda de la
# Cinemateca («CN-FIC1 | Competencia Nacional Ficción 1», «F3-01 | Fanático Freak Fantástico 1»).
PREFIJO = {'Competencia Nacional': 'Competencia Nacional', 'Competencia Internacional': 'Competencia Internacional',
           'Conexión': 'Conexión', 'Panorama': 'Panorama'}
NOMBRE = {'CI-CP': 'Corto Periodístico', 'CVR': 'Competencia VR - Realidad Virtual',
          'F3-01': 'Fanático Freak Fantástico 1', 'F3-02': 'Fanático Freak Fantástico 2',
          'F3-03': 'Fanático Freak Fantástico 3',
          'WT-CRO1': 'World Tour: Croacia 1', 'WT-CRO2': 'World Tour: Croacia 2'}
# lo que la leyenda no trae (programas y actividades): bogoshorts-2026-actividades.json
GENERO = {f'{a}-{b}': g for a in ('CN', 'CI', 'PAC') for b, g in
          (('DOC', 'Documental'), ('ANI', 'Animación'), ('EXP', 'Experimental'))}


# el género que declara una fuente de la propia obra
GENERO_OBRA = {
    'Ekobio': 'Experimental',  # https://www.berlinale-talents.de/bt/project/profile/293156
    'Has estado aquí': 'Documental',  # https://dafilmfestival.com/es/movie/has-estado-aqui/
    'Querida A.': 'Documental',  # https://dafilmfestival.com/es/movie/querida-a/
    '跳房子': 'Documental',  # https://www.themoviedb.org/movie/1736821
    '环岛': 'Drama',  # https://www.themoviedb.org/movie/1599912
    'Běi Huí Gu− Xiàn': 'Drama',  # https://www.themoviedb.org/movie/1826831
    'Barra brava': 'Documental',  # https://www.labocine.com/films/barra-brava
    'Raj’in': 'Documental',  # https://www.btselem.org/we-shall-return/index.html
    'Nothing Happens After Your Absence': 'Documental',  # https://tiranafilmfest.org/?p=30711
    'The Tide Inside': 'Drama',  # https://www.phlaff.org/2026-film-guide/the-tide-inside
    'Meyolotl': 'Documental',  # https://www.nywift.org/?p=56218
    'Jazzed': 'Animación',  # https://www.annecyfestival.com/about/archives/2009/official-selection/film-index:film-20091336
    'Transastralisme': 'Animación',  # https://cccb.org/en/participants/file/eva-ortega-puig/247682
    'Szepty': 'Animación',  # https://filmpolski.pl/fp/index.php?film=1274634
    'Métae': 'Experimental',          # shortfilmwire.com/en/embedded/film/200142909 «Fiction, Experimental»
               'I Carry Them': 'Experimental'}   # web del director, «Experimental Narrative» (registro de altas)


def _hu(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


KORINCO = {'genero': 'Animación',  # minikino.org/en/korinco-2026-en: «stop-motion animated short film»
           'titulo': 'La primera estampilla de Korinco', 'pais': 'Colombia, Indonesia, Corea del Sur', 'anio': 2026, 'duracion_min': 5,
           'sinopsis': 'Una nueva producción nacida de la alianza creativa entre los festivales MINIKINO (Indonesia), SESIFF (Corea del Sur) y '
                       'BOGOSHORTS (Colombia), que continúa promoviendo el intercambio cinematográfico entre los tres países.',
           # el inglés del mismo párrafo del catálogo (chiquiSHORTS) y el título inglés de festival.bogoshorts.com/corto/4335
           'synopsis_en': 'A new production born from the creative partnership between the MINIKINO (Indonesia), SESIFF (South Korea), and '
                          'BOGOSHORTS (Colombia) festivals, which continues to promote cinematic exchange among the three countries.',
           'title_en': 'KORINCO’s first stamp',
           '_src': {'url': 'https://cinematecadebogota.gov.co/node/peliculas/3747?sede=11', 'date': '2026-11-23'}}
TEXTOS = json.load(open(f'{REPO}/festivals/staging/bogoshorts-2026-textos.json', encoding='utf-8'))
DEF_FONTANAR = 'Entrada libre'   # catálogo, aviso de la sala: «fontanar del río … viernes, sábados y domingos 2:00 p.m. y 4:00 p.m. entrada libre»
_act = json.load(open(f'{REPO}/festivals/staging/bogoshorts-2026-actividades.json', encoding='utf-8'))
HORA = re.compile(r'^(\d{1,2}):(\d\d)$')


def palabras():
    r = subprocess.run(['pdftotext', '-bbox', PDF, '-'], capture_output=True, text=True)
    return [(float(a), float(b), float(c), html.unescape(t)) for a, b, c, t in re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">(.*?)</word>', r.stdout)]


def h24(h, m, mer):
    h = int(h) % 12 + (12 if mer.startswith('p') else 0)
    return f'{h:02d}:{m}'


def main():
    ws = palabras()
    cab = [w for w in ws if 70 < w[1] < 85 and re.fullmatch(r'\d', w[3])]
    cols = sorted((w[0] + w[2]) / 2 for w in cab)
    assert len(cols) == 8, f'encabezados de día: {len(cols)}'
    # etiquetas de hora (columna de horas, x 135–205): (y, «HH:MM» de inicio)
    horas = []
    izq = sorted([w for w in ws if 129 < w[0] < 200], key=lambda w: (round(w[1]), w[0]))
    for i, w in enumerate(izq):
        m = HORA.match(w[3])
        if m:
            sig = [v for v in izq if abs(v[1] - w[1]) < 2 and v[0] > w[0]]
            mer = next((v[3] for v in sig if v[3] in ('a.m.', 'p.m.')), '')
            if not any(abs(y - w[1]) < 2 for y, _ in horas):
                horas.append((w[1], (m[1], m[2], mer)))

    def espacio(y):
        return next(e for e in ESPACIOS if e[0] <= y < e[1])

    # celdas: palabras de la grilla por (espacio, columna), partidas en racimos
    # por hueco vertical (>10 pt). Un racimo = una celda: así «2:00 p.m.» encima
    # de «CI-VC/CN-VC**» o «Noche Frankenstein» encima de «Aliens (52')» van juntas.
    grupos = {}
    for w in ws:
        cx = (w[0] + w[2]) / 2
        if not (X_MIN < w[0] < X_MAX and w[1] > 90):
            continue
        col = min(range(8), key=lambda i: abs(cols[i] - cx))
        grupos.setdefault((espacio(w[1]), col), []).append(w)
    celdas = []
    for (e, col), ws_ in grupos.items():
        ws_.sort(key=lambda w: (w[1], w[0]))
        rac = [[ws_[0]]]
        for w in ws_[1:]:
            if w[1] - rac[-1][-1][1] <= 10:
                rac[-1].append(w)
            else:
                rac.append([w])
        celdas += [(e, col, r) for r in rac]

    # el catálogo oficial (13 nov) manda sobre boletines e IG en qué cortos tiene
    # cada programa; «CI-VC/CN-VC» es una sola función con los dos videoclips
    progs = json.load(open(PROG, encoding='utf-8'))['programas']
    progs.update(json.load(open(CORTOS, encoding='utf-8'))['programas'])
    progs = {c: [{k: v for k, v in o.items() if k != '_duracion'} for o in os_] for c, os_ in progs.items()}
    # un título sin letras latinas (环岛) normaliza a '' y el ensamblador no puede cruzarlo con el
    # enriquecido: su ficha verificada viaja con la obra
    _e = f'{REPO}/festivals/staging/bogoshorts-2026-enriquecido.json'
    for e in (json.load(open(_e, encoding='utf-8'))['obras'] if os.path.exists(_e) else []):
        if not re.search(r'[A-Za-z0-9]', e['titulo']) and e.get('tmdb_id'):
            for o in (o for os_ in progs.values() for o in os_ if o['titulo'] == e['titulo']):
                o.update({k: e[k] for k in ('tmdb_id', 'lbSlug', 'poster') if e.get(k)})
                if e.get('poster'):
                    o['posterSource'] = 'tmdb'
    # el GÉNERO que el festival declara al programar (Competencia/Panorama Documental, Animación, Experimental), solo
    # donde TMDB no da uno; «Ficción» y «Videoclip» no son géneros y no se traducen a ninguno. Y el título inglés del
    # catálogo no pisa al de TMDB cuando solo cambia la caja o la puntuación.
    _enr = {o['titulo']: o for o in (json.load(open(_e, encoding='utf-8'))['obras'] if os.path.exists(_e) else [])}
    for c, os_ in progs.items():
        for o in os_:
            x = _enr.get(o['titulo'], {})
            g = (not _hu(o['titulo']) and x.get('genero')) or GENERO.get(re.sub(r'\d$', '', c)) or GENERO_OBRA.get(unicodedata.normalize('NFC', o['titulo']))
            # un título sin letras latinas (跳房子) no casa al ensamblar: su género va en el crudo
            if g and (not x.get('genero') or not _hu(o['titulo']) or 'genero' in (x.get('_heredado') or {})):
                o['genero'] = g
            if x.get('title_en') and 'title_en' not in (x.get('_heredado') or {}) \
                    and _hu(x['title_en']) == _hu(o.get('title_en')):
                o.pop('title_en')
    progs['CI-VC/CN-VC'] = progs['CI-VC'] + progs['CN-VC']
    funciones, descartadas = [], []
    for e, col, ws_ in sorted(celdas, key=lambda k: (k[1], k[0][0], k[2][0][1])):
        ws_.sort(key=lambda w: (round(w[1] / 3), w[0]))
        txt = ' '.join(w[3] for w in ws_)
        sede_sala = (e[2] + ' ' + e[3]).strip()
        if txt in DESCARTES or sede_sala in DESCARTES:
            descartadas.append({'texto': txt, 'dia': DIAS[col], 'sede': sede_sala,
                                'por_que': DESCARTES.get(txt) or DESCARTES[sede_sala]})
            continue
        # la fila: la etiqueta de hora más TEMPRANA a ±12 pt del racimo (una celda
        # que ocupa dos filas —Inauguración, IMAGINATÓN— empieza en la de arriba)
        y0, y1 = ws_[0][1], ws_[-1][1]
        dentro = [y for y, _ in horas if e[0] <= y < e[1]]
        cerca = [y for y in dentro if y0 - 12 <= y <= y1 + 12] or \
            sorted(dentro, key=lambda y: abs(y - y0))[:1]
        h, mi, mer = dict(horas)[min(cerca)] if cerca else ('', '', '')
        # hora escrita en la celda: manda; con «Cóctel» y «Evento», la del cóctel (empieza ahí)
        rango = re.search(r'(\d{1,2}):(\d\d) - (\d{1,2}):(\d\d) ([ap]\.m\.)', txt)
        mh = re.search(r'(\d{1,2}):(\d\d) ([ap]\.m\.)', txt)
        if rango:                       # «IMAGINATÓN 2:00 - 8:00 p.m.»: empieza en la primera
            h, mi, mer = rango[1], rango[2], rango[5]
            txt = txt.replace(rango[0], '').strip()
        elif mh:
            h, mi, mer = mh.groups()
            txt = re.sub(r'\s*\d{1,2}:\d\d [ap]\.m\.( - (Cóctel|Evento))?', '', txt).strip()
        hora = h24(h, mi, mer) if h else ''
        if txt == 'CVR':
            # «2:00 - 6:00 p.m.» y «S, d y f 11:00 a.m. - 6:00 p.m.» (sáb, dom y festivos;
            # el mar 8 dic es festivo en Colombia: Inmaculada Concepción)
            # el mar 8 (festivo) lo dicen expreso el catálogo del 18 nov («Mié. 2, Jue. 3, Vie. 4 y
            # Mar. 8 2:00 p.m. a 6:00 p.m.») y las fichas de la web (14:00): mandan sobre la nota genérica
            hora = '11:00' if DIAS[col] in ('2026-12-05', '2026-12-06') else '14:00'
        f = {'dia': DIAS[col], 'hora': hora, 'sede': e[2], 'sala': e[3],
             'ciudad': 'Bogotá', 'texto_grilla': txt,
             '_src': {'url': URL, 'date': '2026-11-13'}}
        md = re.search(r"\((\d+)'\)", txt)
        if md:
            f['duracion_min'] = int(md[1])
        cod = re.match(r"^([A-Z0-9]+(?:[-/][A-Z0-9]+)*)(\**)(?:\s|$)", txt)
        base = re.sub(r'\d$', '', cod[1]) if cod else None
        if cod and (cod[1] in LEYENDA or base in LEYENDA):
            grupo, nombre = LEYENDA.get(cod[1]) or LEYENDA[base]
            f.update({'codigo': cod[1], 'seccion': grupo, 'titulo': nombre,
                      'has_qa': cod[2] == '**'})
            if cod[1] not in LEYENDA:          # CN-FIC1 → «Ficción 1»
                f['titulo'] = f'{nombre} {cod[1][-1]}'
            if grupo in PREFIJO and not f['titulo'].startswith(PREFIJO[grupo]):
                f['titulo'] = f"{PREFIJO[grupo]} {f['titulo']}"
            f['titulo'] = NOMBRE.get(cod[1], f['titulo'])
            if cod[2] == '***':
                f['_nota'] = '*** Solo Encuentros Cercanos, tras la proyección del programa en Sala Capital'
        elif txt.startswith('Noche Frankenstein'):   # trae «Aliens (52')» = F3-ALIENS
            f.update({'codigo': 'F3-ALIENS', 'seccion': 'Fanático Freak Fantástico F3',
                      'titulo': 'Noche Frankenstein Vol 10', 'has_qa': False,
                      '_nota': "la celda trae «Aliens (52')»: el programa F3-ALIENS (IG DehCoz4kZkM)"})
        elif cod and cod[1] in ('HOM-CESAR', 'HUMOR', 'CI-VC/CN-VC'):
            sec_, tit_ = _act['programas'][cod[1]]
            f.update({'codigo': cod[1], 'titulo': tit_, 'seccion': sec_, 'has_qa': cod[2] == '**',
                      '_nota': 'el código no está en la leyenda de la grilla: sección y título del catálogo'})
        else:
            f.update({'titulo': txt.replace('*', '').strip(), 'seccion': '', 'tipo': 'evento', 'type': 'event',
                      'has_qa': '**' in txt and '***' not in txt})
            if e[3].startswith('Lounge') and hora == '16:30':
                f.update({'titulo': 'Encuentros Cercanos: ' + f['titulo'], 'seccion': 'Franja Encuentros Cercanos',
                          'event_kind': 'encuentro'})
            act = next((d for k, d in _act['actividades'] if txt.startswith(k)), None)
            if act:
                f['titulo'] = act.get('titulo', f['titulo'])
                f['seccion'] = act.get('seccion', 'Al Tablero')
                f['event_kind'] = act.get('event_kind', 'charla')
                if act.get('min'):
                    f['duracion_min'] = act['min']
                if act.get('franja'):
                    f['duracion_min'] = act['franja']
                if act.get('sala'):
                    f['sala'] = act['sala']
                if act.get('texto'):
                    f['descripcion'] = TEXTOS['textos'][act['texto']]['es']
                if act.get('participantes'):     # boletín 027, 24 nov
                    f['descripcion'] += ' ' + act['participantes']
                if act.get('acceso'):
                    f['acceso'] = act['acceso']
                if act.get('registration_url'):
                    f['registration_url'] = act['registration_url']
                if act.get('src'):
                    f['_src'] = act['src']
            elif f['seccion'] == '':
                sys.exit(f'✗ actividad sin sección: {txt}')
            if txt.startswith('Estreno BFM-IV'):     # la agenda de la sala da la obra
                f.update({'codigo': 'BFM-IV'})
                f.pop('event_kind'); f.pop('type'); f.pop('tipo')
        # «* Entrada con invitación»: un asterisco solo (** es Q&A, *** Encuentros)
        f.setdefault('acceso', 'Entrada con invitación' if re.search(r'(?<!\*)\*(?!\*)', txt) else DESCONOCIDO)
        if f.get('codigo') == 'F3-ALIENS':   # catálogo, escenarios y eventos especiales
            f['acceso'] = 'Entrada con invitación (manilla)'   # la grilla pone * (invitación); el catálogo y la web, más nuevos, manilla
        if e[2] == 'Cinemateca de Bogotá Sede Fontanar del Río':
            f['acceso'] = DEF_FONTANAR
        if e[2] == 'Alianza Francesa' and not f['sala']:
            f['sala'] = 'Sala Jules Verne'   # catálogo: «Alianza Francesa - Sala Jules Verne»
        # la sala vende: el enlace de TuBoleta de esa función en la agenda de la Cinemateca
        b = BOLETA.get((f['dia'], f['hora'], f['sala'])) if e[2] == 'Cinemateca de Bogotá' else None
        # Furia: la grilla (13 nov) la da a las 16:00; la agenda de la Cinemateca la pasó a las 17:00 el 24 nov y la
        # grilla del BFM (24 nov) trae In Vitro a las 16:00, 17:00 y 17:30 sin nombrarla. Sin resolver: queda la más
        # temprana, que es la de la grilla; de la agenda salen la obra y la entrada.
        if f.get('codigo') == 'BFM-IV':
            b = next(c for c in BOLETA.values() if c['dia'] == f['dia'] and 'Furia' in c['titulo_sala'])
        if b and b['ticket_url']:
            f['acceso'], f['ticket_url'] = 'Con boleta', b['ticket_url']
        elif b and b.get('entrada_libre'):
            f['acceso'] = 'Entrada libre'
        elif e[2] == 'Cinemateca de Bogotá' and f['acceso'] == DESCONOCIDO and (f.get('type') == 'event' or f.get('codigo') == 'CVR'):
            f['acceso'] = 'Entrada libre (no se anuncia pago)'   # charlas y VR: la agenda de la sala no les vende boleta
        elif e[2] == 'Cinemateca de Bogotá' and f.get('codigo') and f['codigo'] != 'CVR':
            f['acceso'] = 'Con boleta'       # sede que siempre cobra (funcion.py): CHI-ANCY, sin enlace todavía
        if f.get('codigo') in progs:
            f['obras'] = progs[f['codigo']]
        # KORINCO: está en la lista de la sala (CHI-KIDS, 6 obras) y en el texto del catálogo
        # («La primera estampilla de KORINCO…»), pero el catálogo no le hizo ficha
        if f.get('codigo') == 'CHI-KIDS':
            f['obras'] = f['obras'] + [KORINCO]
        if f.get('codigo') == 'CVR':
            # «2:00 - 6:00 p.m.» / «11:00 a.m. - 6:00 p.m.»: se entra por turnos, no es una
            # proyección con hora — el modelo de VR #OtrosMundosPosibles (NarrarElFuturo)
            f.update({'type': 'event', 'info': True, 'event_kind': 'experiencia',
                      'duracion_min': 420 if f['hora'] == '11:00' else 240})
        if f.get('codigo') == 'BFM-IV':
            f['obras'] = [{'titulo': 'Furia', 'director': 'Daniela Córdoba', 'pais': 'Colombia', 'anio': 2026,
                           'duracion_min': 14, 'sinopsis': TEXTOS['textos']['furia']['es'], 'title_en': 'Rage',
                           # catálogo del BFM 2026, «Furia / Rage»
                           'synopsis_en': 'Felipe sneaks into a gig and discovers that his boyfriend Eduardo is hiding him out of fear of accepting his own '
                                          'homosexuality. Amid a first chemical trip and a mosh pit, they let go and lose their inhibitions, until an '
                                          'attempted kiss threatens to unleash violence and their deepest fears.', '_src': {'url': b['pagina'], 'date': '2026-11-23'}}]
        # UN programa de UNA obra no es un programa: la función es esa obra (FI-LARGO, Furia)
        if len(f.get('obras') or []) == 1:
            u = f.pop('obras')[0]
            f.update({k: v for k, v in u.items() if k != '_src'})
        funciones.append(f)
    # La Entrega clave IMAGINATÓN no tiene celda: la grilla dice «IMAGINATÓN 2:00 - 8:00 p.m.».
    # El catálogo la trae aparte, y con dos horas: 7:00 p. m. (pág. 23) y 8:00 p. m. (escenarios
    # y eventos especiales). Contradicción sin sala → la más temprana.
    funciones.append({'dia': '2026-12-04', 'hora': '19:00', 'sede': 'Teatro El Parque', 'sala': '', 'ciudad': 'Bogotá',
                      'texto_grilla': 'IMAGINATÓN', 'titulo': 'Entrega clave IMAGINATÓN', 'seccion': 'IMAGINATÓN',
                      'tipo': 'evento', 'type': 'event', 'event_kind': 'evento', 'has_qa': False,
                      'acceso': DESCONOCIDO, '_src': {'url': 'https://info.bogoshorts.com/sccs/prensa/2026/docs_2026/24BSFF_catalogo2026.pdf', 'date': '2026-11-18'}})
    # La Noche Sagitario: la grilla la trae en «Fiestas» sin lugar; el festival lo dio el 23 nov (IG).
    funciones.append({'dia': '2026-12-05', 'hora': '21:00', 'sede': 'MonkeyDo', 'sala': '', 'ciudad': 'Bogotá',
                      'texto_grilla': 'Noche Sagitario', 'titulo': 'Noche Sagitario', 'seccion': 'Eventos especiales',
                      'tipo': 'evento', 'type': 'event', 'event_kind': 'fiesta', 'has_qa': False,
                      'descripcion': 'Acceso exclusivo para acreditados de las categorías: Aliado, Industria BFM y Participante.',
                      'acceso': 'Entrada con invitación (solo acreditados Aliado, Industria BFM y Participante)',
                      '_src': {'url': 'https://www.instagram.com/p/DgGg1WOu3FA/', 'date': '2026-11-23', 'tipo': 'festival-ig'}})
    # VR abierta varios días: UNA función info por tramo continuo del mismo horario ([abierta-varios-dias])
    vr = [f for f in funciones if f.get('codigo') == 'CVR']
    for desde, hasta in (('2026-12-02', '2026-12-04'), ('2026-12-05', '2026-12-06')):
        tramo = [f for f in vr if desde <= f['dia'] <= hasta]
        tramo[0]['hasta'] = hasta
        for f in tramo[1:]:
            funciones.remove(f)
    for f in funciones:
        # regla de Juan (13 y 16 oct 2026): sin aviso de pago es entrada libre
        if f['acceso'] == DESCONOCIDO:
            f['acceso'] = 'Entrada libre (no se anuncia pago)'
        for o in f.get('obras') or []:
            if o.get('pais') == 'Escocia':     # sin bandera propia en la app: Escocia es parte del Reino Unido
                o['pais'] = 'Reino Unido'
    def _nfc(x):
        if isinstance(x, str): return unicodedata.normalize('NFC', x)
        if isinstance(x, list): return [_nfc(y) for y in x]
        if isinstance(x, dict): return {k: _nfc(v) for k, v in x.items()}
        return x
    funciones = _nfc(funciones)
    json.dump({'_provenance': provenance(URL, metodo='pdftotext -bbox: columna por x del encabezado, '
                                         'fila por la hora más cercana dentro del espacio'),
               'funciones': funciones, '_descartadas': descartadas},
              io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("obras"))} con obras), '
          f'{len(descartadas)} descartadas → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
