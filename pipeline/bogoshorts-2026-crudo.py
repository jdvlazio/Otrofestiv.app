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
import html, io, json, os, re, subprocess, sys

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
DESCARTES = {'Fiestas': 'fila «Fiestas» (13 nov): la grilla no dice dónde son',
             'BFM - BOGOSHORTS Film Market': 'franja de industria de varios días, no una función',
             'Acreditaciones': 'punto de acreditación, no una función',
             'City U': 'la fila de City U es la franja del BFM - BOGOSHORTS Film Market (industria, varios días)',
             'Alianza Francesa Sótano 1': 'Acreditaciones, 10:00 a.m. - 6:00 p.m.: no es una función',
             'Retina Latina': 'FI-ENA1 / FI-ENA2 en línea, «Disponibles entre el 1 y el 15 de diciembre»: sin sala ni hora',
             'Franja Encuentros Cercanos Competencia Nacional***': 'rótulo de la fila (flecha al mié 2), no una celda'}
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
            hora = '11:00' if DIAS[col] in ('2026-12-05', '2026-12-06', '2026-12-08') else '14:00'
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
            if cod[2] == '***':
                f['_nota'] = '*** Solo Encuentros Cercanos, tras la proyección del programa en Sala Capital'
        elif txt.startswith('Noche Frankenstein'):   # trae «Aliens (52')» = F3-ALIENS
            f.update({'codigo': 'F3-ALIENS', 'seccion': 'Fanático Freak Fantástico F3',
                      'titulo': 'Noche Frankenstein Vol 10', 'has_qa': False,
                      '_nota': "la celda trae «Aliens (52')»: el programa F3-ALIENS (IG DehCoz4kZkM)"})
        elif cod and cod[1] in ('HOM-CESAR', 'HUMOR', 'CI-VC/CN-VC'):
            f.update({'codigo': cod[1], 'titulo': re.sub(r"\s*\(\d+'\)", '', txt).replace('**', ''),
                      'seccion': '', 'has_qa': cod[2] == '**',
                      '_nota': 'el código no está en la leyenda de la grilla'})
        else:
            f.update({'titulo': txt.replace('*', '').strip(), 'seccion': '', 'tipo': 'evento'})
            if e[3].startswith('Lounge') and hora == '16:30':
                f['seccion'] = 'Franja Encuentros Cercanos'
        # «* Entrada con invitación»: un asterisco solo (** es Q&A, *** Encuentros)
        f['acceso'] = 'Entrada con invitación' if re.search(r'(?<!\*)\*(?!\*)', txt) else DESCONOCIDO
        # la sala vende: el enlace de TuBoleta de esa función en la agenda de la Cinemateca
        b = BOLETA.get((f['dia'], f['hora'], f['sala'])) if e[2] == 'Cinemateca de Bogotá' else None
        if b:
            f['acceso'], f['ticket_url'] = 'Con boleta', b['ticket_url']
        if f.get('codigo') in progs:
            f['obras'] = progs[f['codigo']]
        funciones.append(f)
    json.dump({'_provenance': provenance(URL, metodo='pdftotext -bbox: columna por x del encabezado, '
                                         'fila por la hora más cercana dentro del espacio'),
               'funciones': funciones, '_descartadas': descartadas},
              io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("obras"))} con obras), '
          f'{len(descartadas)} descartadas → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
