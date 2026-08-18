# -*- coding: utf-8 -*-
"""PDF oficial de programación → crudo (formato intermedio).

LA FUENTE BUENA, y llegó tarde. Hasta el 17 ago 2026 CineAutopsia se montó
desde la agenda de la Cinemateca de Bogotá, que es una SEDE: publicaba sus 7
programas y nada más. El festival tiene 12 funciones en 6 sedes y 8 jornadas.
Este PDF es del propio festival (bogotaexperimental.com → «DESCARGUE AQUÍ EL
PDF DE PROGRAMACIÓN») y manda sobre la sede.

EL PDF NO TIENE CAPA DE TEXTO. `pdftotext` devuelve cero: son 25 páginas de
diseño a 1080×1920. Se rasteriza y se lee con Vision (el mismo OCR de FICMA):

    pdftoppm -r 110 -png fuentes/cineautopsia-2026/programacion-oficial-2026.pdf pg
    swiftc -O -o /tmp/ocr pipeline/ficma-2026-ocr.swift && /tmp/ocr pg-*.png > \\
        festivals/staging/cineautopsia-2026-ocr.json

LAS FECHAS SE RESUELVEN POR EL NOMBRE DEL DÍA, no por el número. El PDF titula
el día 6 «JUEVES.28» y el jueves fue 27 — errata del festival. El nombre de la
jornada es el dato fiable y el número el que se equivoca, así que se calcula la
fecha del nombre y se reporta cada choque en `_erratas`.
"""
import json, os, re, sys, unicodedata, datetime, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = f'{REPO}/festivals/staging/cineautopsia-2026-ocr.json'
OUT = f'{REPO}/festivals/staging/cineautopsia-2026-crudo.json'
FUENTE = ('PDF oficial de programación · bogotaexperimental.com/bogotaexp2026 '
          '(descargado 18 ago 2026) · OCR Vision sobre 25 páginas sin capa de texto')

DIAS = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
        'viernes': 4, 'sabado': 5, 'domingo': 6}
VENTANA = [datetime.date(2026, 8, d) for d in range(21, 30)]

RE_DIA = re.compile(r'^D[IÍ]A\s*([0-9G])', re.I)
RE_JORNADA = re.compile(r'^([A-ZÁÉÍÓÚÑ]{5,10})\.?\s*(\d{1,2})', re.I)
RE_HORA = re.compile(r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)
# «• Título (Dir. Nombre, 2024) País. 27 min.» — el año a veces falta y el
# separador entre Dir y año es coma o punto según la página.
# SIN ancla al inicio y con `finditer`: el OCR pega dos obras en una sola línea
# —«…15 min.Fort Garry Lions Pool (Dir. Ryan Steel, 2024) Canadá. 6 min.»— y
# leyendo solo la primera se perdían 8 obras de las 51.
# El director puede ser VARIOS —«(Dir. Ashima Shiraishi, Jess X. Snow, 2026)»—
# así que no se puede cortar en la primera coma: se toma todo hasta el cierre y
# el año se separa del final. Cortar en la coma perdía 4 obras, todas de dos
# directores, y el error era invisible porque las otras 47 entraban bien.
RE_OBRA = re.compile(
    r'[•*]?\s*(?P<titulo>[^\n]{2,90}?)\s*\((?:Dir[.:]?\s*)(?P<dir>[^)]*?)(?:[,.]\s*(?P<anio>\d{4}))?\)\s*'
    r'(?P<pais>[^.•]+?)\.?\s*(?P<min>\d{1,3})\s*min', re.I)


def _n(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def fecha_de(nombre, numero, erratas):
    """Fecha de una jornada. El NÚMERO manda; el nombre del día lo VERIFICA.

    Ambos datos existen y a veces se contradicen, así que el criterio importa:
    si el número cae en la ventana y su día de la semana coincide, se acepta y
    no hay nada que decir. Si NO coincide, se elige el día de esa semana más
    cercano al número escrito —«JUEVES.28» → jueves 27, no jueves 20— y se
    reporta. La primera versión de esto se quedaba con el primer viernes de la
    ventana y mandaba el día 7 al 21 de agosto.
    """
    idx = DIAS.get(_n(nombre))
    if idx is None:
        return None
    cand = [d for d in VENTANA if d.weekday() == idx]
    if not cand:
        return None
    if numero:
        n = int(numero)
        exacto = next((d for d in cand if d.day == n), None)
        if exacto:
            return exacto.isoformat()
        f = min(cand, key=lambda d: abs(d.day - n))
        erratas.append(f'el PDF dice «{nombre}.{numero}» y el {nombre.lower()} '
                       f'más cercano es {f.day} — se usa {f.isoformat()}')
        return f.isoformat()
    return cand[0].isoformat()


# ── correcciones de OCR, EXPLÍCITAS ─────────────────────────────────────────
# El título es la palabra del festival y no se toca… salvo cuando lo que
# tenemos no es su palabra sino lo que el OCR entendió. Cada línea de aquí es
# una lectura verificada contra la página, no una mejora de estilo: se corrige
# «OFICAL», no las minúsculas de «cortometrajes panorama», que son del diseño.
# Se casa por PREFIJO normalizado: el OCR corta la cola del título por donde
# quiere, y una tabla de igualdad exacta falla en cuanto sobra una palabra.
TITULO_OCR = {
    'actooficaldeapertura': 'Acto oficial de apertura · Muestra Expanded FullDome Internacional',
    'dlargometrajepanorama': 'Largometraje Panorama Colombia',
    'premiacionclausura': 'Premiación & Clausura',
    'encuentrocolombiaexperimental': 'Encuentro Colombia Experimental Contemporánea',
}

# El Encuentro es al aire libre, sin hora de fin publicada: se entra y se sale.
# `info` existe exactamente para eso — aparece en el programa y NO entra al plan
# ni a conflictos (docs/SCHEMA.md). Inventarle una duración sería peor.
SIN_HORA_FIN = {'encuentrocolombiaexperimental'}

# Las 7 obras de la muestra FullDome de apertura NO están en el PDF: el festival
# las publicó en Instagram (transcritas en el issue #565). Es su palabra, en otra
# superficie suya, así que entran con su procedencia declarada.
FULLDOME = [
    ('Perdidos en la nube', 'Lala Severi', 2026, 'Uruguay', 6),
    ('La methode des moments', 'Lydia Yakonowsky', 2025, 'Canadá', 10),
    ('Eternal Habitat', 'Sergey Prokofyev', 2025, 'Alemania', 6),
    ('Are We Gazing at the Same Moon?', 'Jeyun J Cloud', 2024, 'Estados Unidos', 3),
    ('Event Horizon', 'Zhipeng Wang', 2023, 'China', 5),
    ('Exo cortex 3.0', 'Jeremy Oury', 2023, 'Francia', 7),
    ('Este no es tu jardín', 'Carlos Velandia, Angélica Restrepo', 2025, 'Colombia', 13),
]


def main():
    ocr = json.load(open(OCR, encoding='utf-8'))
    ocr = ocr.get('paginas', ocr)   # el sidecar lleva _provenance delante
    erratas, programas = [], []
    dia_actual = None
    for pag in sorted(ocr):
        lineas = [l['t'].strip() for l in ocr[pag]]
        cab = next((RE_DIA.match(x) for x in lineas[:3] if RE_DIA.match(x)), None)
        if not cab:
            continue                      # página de manifiesto, portada o créditos
        jor = next((RE_JORNADA.match(x) for x in lineas[:4] if RE_JORNADA.match(x)), None)
        if jor:
            f = fecha_de(jor.group(1), jor.group(2), erratas)
            if f:
                dia_actual = f
        if not dia_actual:
            continue
        # cada función abre con su hora; lo que sigue hasta la próxima es suyo
        cortes = [i for i, x in enumerate(lineas) if RE_HORA.search(x) and len(x) < 22]
        for n, i in enumerate(cortes):
            bloque = lineas[i:cortes[n + 1] if n + 1 < len(cortes) else len(lineas)]
            m = RE_HORA.search(bloque[0])
            h = int(m.group(1)) % 12 + (12 if m.group(3).lower() == 'p' else 0)
            f = {'dia': dia_actual, 'hora': f'{h:02d}:{int(m.group(2)):02d}',
                 '_pagina': pag, 'obras': []}
            # EL DISEÑO PARTE LAS LÍNEAS y el OCR las devuelve partidas: una obra
            # puede terminar en la siguiente («…Estados» / «Unidos. 3:25 min.») y
            # un título apilado ocupa tres. Se reunifica ANTES de interpretar:
            # una línea que no abre viñeta ni es hora continúa la anterior.
            unidas = []
            for x in bloque[1:]:
                # SOLO se pega la continuación de una OBRA. La primera versión
                # pegaba cualquier línea suelta a la anterior y se comía los
                # títulos dentro de la línea de boletería: cuatro programas
                # salieron «SIN TÍTULO» y uno como «estacados Colombia».
                previa_es_obra = bool(unidas) and bool(re.match(r'^[•*]', unidas[-1]))
                if previa_es_obra and not re.match(r'^[•*]|^\d{1,2}:\d{2}', x.strip()) \
                   and not re.search(r'Gratuit|oleter|tuboleta', x, re.I) \
                   and len(unidas[-1]) < 160 and not unidas[-1].rstrip().endswith('min.'):
                    unidas[-1] = unidas[-1].rstrip() + ' ' + x.strip()
                else:
                    unidas.append(x.strip())
            # EL ORDEN DEL PDF ES FIJO: hora → sede → acceso → título → obras.
            # Se recorre en ese orden en vez de adivinar por palabras: mi primer
            # intento buscaba «Cra/Universidad/Museo» para la sede y se dejaba
            # fuera «Cartel Urbano, San Felipe», y tomaba la primera obra como
            # título cuando el título venía apilado en tres líneas.
            etapa, titulo = 'sede', []
            for x in unidas:
                # Se parte la línea ANTES de cada «(Dir.», no por la viñeta: el
                # título «Abjad Hawaz (i÷@-•g)» lleva su transliteración árabe y
                # el OCR mete un «•» DENTRO del paréntesis. Cortando por viñeta,
                # ese corto se llamaba «g)».
                # Una viñeta de verdad va tras espacio y antes de MAYÚSCULA. El
                # «•» de «(i÷@-•g)» va tras un guion y antes de minúscula, así
                # que deja de partir el título de esa obra.
                trozos = re.split(r'(?<=[\s.])•(?=\s*[A-ZÁÉÍÓÚÑ¿«"\d])', x)
                obras_en_linea = [m for t in trozos for m in RE_OBRA.finditer(t)]
                obra = obras_en_linea[0] if obras_en_linea else None
                # «Gratuit» exacto no vale: el OCR devolvió «-vento Gratulte».
                # Se busca la raíz que sobrevive al ruido.
                if re.search(r'gratu[il]', x, re.I):
                    f['acceso'] = 'Entrada libre'; etapa = 'titulo'; continue
                if re.search(r'oleter|tuboleta', x, re.I):
                    f['acceso'] = x; etapa = 'titulo'; continue
                if obra and len(obra.group('titulo')) > 1:
                    etapa = 'obras'
                    for o in obras_en_linea:
                        # El OCR no sabe leer alfabetos no latinos y devuelve
                        # basura entre paréntesis («Abjad Hawaz (i÷@-•g)»). Se
                        # quita: un título con ruido es peor que un título corto.
                        _t = re.sub(r'\s*\([^)]*[÷@|=~][^)]*\)', '', o.group('titulo'))
                        f['obras'].append({
                            'titulo': _t.strip(' •*.'),
                            'director': o.group('dir').strip(),
                            'anio': int(o.group('anio')) if o.group('anio') else None,
                            'pais': o.group('pais').strip(' .'),
                            'duracion_min': int(o.group('min')),
                        })
                    continue
                if x.lower().startswith('esta muestra') or re.match(r'^[\d°ºSIsi\W]{0,4}$', x):
                    continue
                if etapa == 'sede':
                    f['sede'] = x; etapa = 'titulo'
                elif etapa == 'titulo':
                    # La dirección larga parte la sede en dos renglones
                    # («…Universidad Francisco José de» / «Caldas (Distrital)…»).
                    # Mientras no haya título todavía, una línea con señas de
                    # dirección sigue siendo la sede.
                    if not titulo and re.search(r'Cra|Calle|Cl\.|#|Facultad|Edfici|Edifici|Auditorio', x):
                        f['sede'] = f['sede'].rstrip() + ' ' + x
                    else:
                        titulo.append(x)
            if titulo:
                t = ' '.join(titulo[:3])
                t = re.sub(r'[•*]\s*[A-Z]?[ID]?\b', ' ', t)      # marcas del diseño: «*D», «1D», «•»
                t = re.sub(r'^[\W\d°º]+|\s{2,}', ' ', t)
                f['titulo'] = re.sub(r'\s+', ' ', t).strip()
            f.setdefault('acceso', lib.DESCONOCIDO)
            if f.get('sede'):
                programas.append(f)
    # el título parte en varias líneas cuando el diseño lo apila
    print(f'  páginas de día leídas · funciones: {len(programas)}')
    for f in programas:
        print(f"   {f['dia']} {f['hora']} · {f.get('sede','?')[:36]:38} "
              f"{f.get('titulo','⚠ SIN TÍTULO')[:36]:38} obras={len(f['obras']):2} "
              f"{'libre' if f.get('acceso')=='Entrada libre' else 'boletería' if 'olet' in str(f.get('acceso')) else f.get('acceso')}")
    if erratas:
        print('\n  ERRATAS DEL FESTIVAL:')
        for e in dict.fromkeys(erratas):
            print('   ·', e)
    for f in programas:
        # _n conserva espacios; para casar prefijos se compara sin ellos.
        plano = re.sub(r'[^a-z0-9]', '', _n(f.get('titulo', '')))
        clave = next((k for k in TITULO_OCR if plano.startswith(k)), None)
        if clave:
            f['_titulo_ocr'] = f['titulo']
            f['titulo'] = TITULO_OCR[clave]
        if any(re.sub(r'[^a-z0-9]', '', _n(f.get('titulo', ''))).startswith(k) for k in SIN_HORA_FIN):
            f['info'] = True
        if 'apertura' in _n(f.get('titulo', '')) and not f['obras']:
            f['obras'] = [{'titulo': t, 'director': d, 'anio': a, 'pais': p,
                           'duracion_min': m, '_src': 'Instagram del festival (issue #565)'}
                          for t, d, a, p, m in FULLDOME]

    # ── la agenda de la Cinemateca completa lo que el PDF no trae ──────────
    # El PDF es la fuente del festival y manda en QUÉ y CUÁNDO. La Cinemateca es
    # una SEDE y aporta lo suyo: el enlace de compra, el póster del programa y la
    # sinopsis. Donde ambas hablan del mismo programa y NO coinciden, se declara.
    KIN = f'{REPO}/festivals/staging/cineautopsia-2026-cinemateca.json'
    disc = []
    if os.path.exists(KIN):
        cine = json.load(open(KIN, encoding='utf-8'))['programas']
        por_titulo = {_n(x['titulo']): x for x in cine}
        # …y también por día+hora: el PDF y la sede llaman distinto a la misma
        # función («Premiacion & Clausura» / «Clausura y premiación») y cruzar
        # solo por título perdía su póster y su sinopsis.
        por_slot = {(x['dia'], x['hora']): x for x in cine}
        for f in programas:
            # El respaldo por día+hora SOLO vale dentro de la Cinemateca: el 28
            # a las 19:30 hay dos funciones, una suya y otra en FUGA, y sin esta
            # condición la de FUGA se llevaba el póster y la sinopsis de la otra.
            # Lo cazó [posters-duplicados] antes de que llegara a la app.
            k = por_titulo.get(_n(f.get('titulo', '')))
            if not k and 'inemateca' in f.get('sede', ''):
                k = por_slot.get((f['dia'], f['hora']))
            if not k:
                continue
            if k.get('hora') and k['hora'] != f['hora']:
                # La sede es donde se vende la boleta y se reserva la sala: para
                # una función SUYA, su hora es la operativa. El PDF queda anotado.
                disc.append(f"«{f['titulo']}» {f['dia']}: el PDF dice {f['hora']} y "
                            f"la Cinemateca {k['hora']} — se usa la de la sede")
                f['_hora_pdf'], f['hora'] = f['hora'], k['hora']
            for campo in ('ticket_url', 'poster', 'sinopsis', 'duracion_min',
                          'idioma', 'clasificacion'):
                if k.get(campo) and not f.get(campo):
                    f[campo] = k[campo]
            if k.get('acceso') and f.get('acceso') == lib.DESCONOCIDO:
                f['acceso'] = k['acceso']
    if disc:
        print('\n  DISCREPANCIAS ENTRE FUENTES:')
        for d in disc:
            print('   ·', d)
    json.dump({'_provenance': lib.provenance(
                   FUENTE, erratas=list(dict.fromkeys(erratas)),
                   discrepancias=disc,
                   completado_con='agenda de la Cinemateca de Bogotá (enlace de compra, póster y sinopsis)'),
               'programas': programas},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n  → {OUT}')


if __name__ == '__main__':
    main()
