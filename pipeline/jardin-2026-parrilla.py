#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-parrilla.py — la parrilla que el festival publicó COMO IMÁGENES.

El 11° Festival de Cine de Jardín no publica parrilla en su web: el enlace de
«programación» de la home sigue apuntando al PDF de 2025. La publicó el 21 sep
2026 en un carrusel de Instagram de 14 láminas, y ahí está entera.

LA MAQUETA, que es lo que permite leerla sin adivinar:

  · CABECERA con el día: «Viernes 25 de septiembre - Día 2», arriba del todo.
    El lector genérico (ig-programa.py) no la miraba y fechó las 14 láminas el
    mismo día: sacaba las horas bien y el día mal, que es peor que no sacar
    nada. La cabecera es un dato del propio festival, no una deducción.
  · TRES COLUMNAS por posición horizontal: la hora a la izquierda, la sede en
    el medio, la ficha a la derecha.
  · UNA HORA VALE PARA VARIAS SEDES. A las 10:00 del viernes hay función en el
    Teatro Municipal, en la Casa de la cultura y en la Placa deportiva; la hora
    se imprime UNA vez y las tres filas cuelgan de ella. Leer «una fila = una
    hora» perdería dos de cada tres.

Láminas: 00 portada · 01 índice de secciones · 02–11 la parrilla por día ·
12 TALLERES (otra maqueta, con «Lugar:» y «Hora:» rotulados) · 13 cierre.

Esc.  festivals/staging/jardin-2026-parrilla.json
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
from lib import provenance

POST = 'DdkY5ejlraV'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
SWIFT = f'{REPO}/pipeline/ficma-2026-ocr.swift'
OUT = f'{REPO}/festivals/staging/jardin-2026-parrilla.json'

# Las tres columnas, medidas sobre las láminas (x normalizado 0–1).
COL_HORA, COL_FICHA = 0.20, 0.44
# CON QUÉ PALABRA EMPIEZA UNA SEDE. La columna del medio parte los nombres
# largos en dos líneas («Teatro Municipal» / «de Jardín», «Placa deportiva» /
# «Barrio Simón Bolívar») y no hay separación vertical que distinga esa
# continuación del comienzo de la sede siguiente: probé por distancia y fundió
# «Casa de la cultura» con «Coliseo municipal» en una sola. Así que la fila
# nueva la marca el VOCABULARIO, que es lo que el festival imprime de verdad.
CABEZA_SEDE = re.compile(r'^(Teatro|Casa|Placa|Coliseo|Escuela|Fonda|I\.?E\b|'
                         r'Instituci[óo]n|Biblioteca|Parque|Auditorio)', re.I)

# LA MISMA SEDE, ESCRITA DE DOS MANERAS por el propio festival. No es
# normalizar por gusto: la retícula imprime «Placa deportiva» a secas en las
# láminas del domingo y «Placa deportiva Barrio Simón Bolívar» en las del
# viernes, y son el mismo sitio —el que el festival anunció como reemplazo de
# la cancha Moisés Rojas tras el sismo—.
ALIAS_SEDE = {
    'Placa deportiva': 'Placa deportiva Barrio Simón Bolívar',
    'Casa de la Cultura': 'Casa de la cultura',
    'Teatro municipal de Jardín': 'Teatro Municipal de Jardín',
}
DIAS = {'jueves': 24, 'viernes': 25, 'sábado': 26, 'sabado': 26, 'domingo': 27}
RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)
# «Colombia, 2026, 84 min, documental» — país(es), año, duración, género.
RE_FICHA = re.compile(r'^(.+?),\s*((?:1[89]|20)\d{2}),\s*(\d{1,3})\s*min,\s*(.+)$')


def ocr(rutas):
    """{basename: [líneas con caja]} — Vision, con posición."""
    r = subprocess.run(['swift', SWIFT] + rutas, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ OCR falló: {r.stderr[:300]}')
    return json.loads(r.stdout)


def h24(m):
    h, mm, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if ap == 'p' and h != 12:
        h += 12
    if ap == 'a' and h == 12:
        h = 0
    return f'{h:02d}:{mm:02d}'


def dia_de(lineas):
    """El día que anuncia la cabecera de la lámina, o '' si no la lleva."""
    cab = ' '.join(c['t'] for c in lineas if c['y'] < 0.075)
    m = re.search(r'(jueves|viernes|s[áa]bado|domingo)\s+(\d{1,2})', cab, re.I)
    if not m:
        return ''
    d = int(m.group(2))
    # el nombre del día y el número tienen que decir lo MISMO: si no, no se
    # inventa ninguno de los dos.
    if DIAS.get(m.group(1).lower()) != d:
        return ''
    return f'2026-09-{d:02d}'


def filas(lineas, dia):
    """Las funciones de una lámina de parrilla.

    NO se recorre un solo flujo ordenado por altura: las tres columnas se
    entrelazan y la ficha de una fila puede quedar por encima de la sede de la
    siguiente. Se arma al revés —primero las FILAS, que las define la columna
    de la sede, y después cada línea de ficha cae en su banda—. Leyéndolo como
    un flujo, «Teatro Municipal» / «de Jardín» salían como dos funciones y la
    lámina del viernes daba 12 donde los ojos cuentan 9.
    """
    util = [c for c in lineas if c['y'] >= 0.075 and c['t'].strip()]
    horas = sorted(((c['y'], h24(m)) for c in util if c['x'] < COL_HORA
                    for m in [RE_HORA.match(c['t'].strip())] if m))
    sedes = sorted((c for c in util if COL_HORA <= c['x'] < COL_FICHA),
                   key=lambda c: c['y'])
    # una sede partida en dos líneas («Teatro Municipal» / «de Jardín») es UNA
    filas_, colados = [], []
    for c in sedes:
        # UNA SEDE EMPIEZA POR PALABRA DE SEDE. Lo que cae en esa columna y no
        # lo hace, ni continúa la fila de arriba, NO es una sede: el OCR lee el
        # pie de la lámina («FABIOLA LALINDE», a 97% de altura) y la letra
        # pequeña de los afiches que el festival pega debajo de la parrilla
        # («DÍA MEAS DE LA LONA», que es el cartel de Mûpã). Las dos salían
        # publicadas como funciones sin título. Se descartan CONTÁNDOLAS, para
        # que el día que se caiga una sede de verdad se vea en el número.
        if filas_ and not CABEZA_SEDE.match(c['t'].strip()) \
                and c['y'] - filas_[-1]['_y2'] < 0.05:
            filas_[-1]['sede'] += ' ' + c['t'].strip()
            filas_[-1]['_y2'] = c['y']
        elif CABEZA_SEDE.match(c['t'].strip()):
            filas_.append({'dia': dia, 'sede': c['t'].strip(),
                           '_y': c['y'], '_y2': c['y'], 'ficha': []})
        else:
            colados.append(c['t'].strip())
    for f in filas_:
        previas = [h for y, h in horas if y <= f['_y'] + 0.012]
        f['hora'] = previas[-1] if previas else ''
    # cada línea de ficha, a la fila cuya banda empieza más cerca por encima
    for c in sorted((c for c in util if c['x'] >= COL_FICHA), key=lambda c: c['y']):
        cand = [f for f in filas_ if f['_y'] <= c['y'] + 0.012]
        if cand:
            cand[-1]['ficha'].append(c['t'].strip())
    for f in filas_:
        f.pop('_y2', None)
        f['sede'] = ALIAS_SEDE.get(f['sede'], f['sede'])
    return [f for f in filas_ if f['hora']], colados


def una_columna(lineas, dia):
    """La lámina del jueves, que NO tiene tres columnas.

    El día inaugural se maqueta en una sola columna alineada a la izquierda, con
    dos bloques rotulados —LECCIÓN INAUGURAL y ACTO INAUGURAL—, cada uno con su
    hora, su sede y su ficha debajo. Leído con la regla de las tres columnas
    daba CERO funciones: no hay nada a la derecha de 0,44.
    """
    ls = [c for c in sorted(lineas, key=lambda c: c['y'])
          if c['y'] >= 0.075 and c['t'].strip()]
    out, act = [], None
    for c in ls:
        t = c['t'].strip()
        if re.match(r'^[A-ZÁÉÍÓÚÑ ]{6,}$', t) and 'PONENTES' not in t.upper():
            act = {'dia': dia, 'hora': '', 'sede': '', 'rotulo': t, 'ficha': []}
            out.append(act)
            continue
        if act is None:
            continue
        m = RE_HORA.match(t)
        if m and not act['hora']:
            act['hora'] = h24(m)
        elif not act['sede'] and re.search(r'teatro|casa|placa|coliseo|escuela|i\.e', t, re.I):
            act['sede'] = t
        else:
            act['ficha'].append(t)
    return [f for f in out if f['hora'] and f['sede']]


def talleres(lineas):
    """La lámina de TALLERES, que no es una parrilla.

    Es una lista de bloques, cada uno con lo que el festival quiso ponerle:
    nombre, quién organiza o dicta, y a veces «Jueves 24 de septiembre»,
    «Lugar: …» y «Hora:/Horario: …» ROTULADOS. Se lee por rótulo, no por
    posición: acá no hay columnas.

    TRES DE LOS SIETE NO SE PUBLICAN, y queda escrito cuál y por qué: el de la
    Escuela de Cine ITM y el de fotografía cinematográfica no traen ni día ni
    lugar ni hora, y el de la IU Digital trae día y lugar pero NO hora. Sin
    hora no es una función —regla de la casa— y una hora inventada es peor que
    una ausencia.
    """
    ls = [c['t'].strip() for c in sorted(lineas, key=lambda c: c['y'])
          if c['y'] >= 0.075 and c['t'].strip()]
    bloques, act = [], None
    for t in ls:
        md = re.search(r'(jueves|viernes|s[áa]bado|domingo)\s+(\d{1,2})\s+de\s+septiembre', t, re.I)
        ml = re.match(r'Lugar:\s*(.+)$', t, re.I)
        mh = re.match(r'Hora(?:rio)?:\s*(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', t, re.I)
        # «Horario: 11:00 a.m. - 12:00 p.m.» trae también el FIN, y con él la
        # duración real. Sin leerlo les puse 120 minutos por defecto a los
        # cuatro y el verificador cazó nueve solapes falsos: el taller de
        # cartografías dura una hora, no dos.
        mf = re.match(r'Hora(?:rio)?:\s*\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?\s*[-–]\s*'
                      r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', t, re.I)
        mo = re.match(r'(Organiza|Tallerista):\s*(.+)$', t, re.I)
        if not (md or ml or mh or mo):
            # Línea sin rótulo: título nuevo, o subtítulo del bloque en curso.
            # EL CORTE LO MARCA HABER VISTO YA UN RÓTULO, no tener día. Con la
            # regla anterior —«nuevo bloque solo si el actual ya tiene día,
            # lugar u hora»— el taller de la Escuela de Cine ITM, que no trae
            # ninguno de los tres, se tragó el título siguiente y encima se
            # quedó con SU día, SU lugar y SU hora: «Lo que vemos, lo que
            # decimos» desapareció de la lista y el de la ITM salía publicable
            # con datos ajenos. Los ojos cuentan siete bloques en la lámina.
            if act is None or act.get('_rotulado'):
                act = {'titulo': t, '_lineas': [t]}
                bloques.append(act)
            else:
                act['_lineas'].append(t)
            continue
        act['_rotulado'] = True
        if act is None:
            continue
        if md:
            d = int(md.group(2))
            # «Viernes 25 y sábado 26» — se quedan los dos, sin elegir
            act.setdefault('dias', []).append(f'2026-09-{d:02d}')
            act['dia'] = act['dias'][0]
        if ml:
            act['lugar'] = ml.group(1).strip()
        if mh:
            act['hora'] = h24(mh)
        if mf:
            fin = h24(mf)
            ini = act.get('hora') or ''
            if ini:
                d_ = (int(fin[:2]) * 60 + int(fin[3:])) - (int(ini[:2]) * 60 + int(ini[3:]))
                if d_ > 0:
                    act['duracion_min'] = d_
        if mo:
            act[mo.group(1).lower()] = mo.group(2).strip(' .')
    out = []
    for b in bloques:
        b.pop('_rotulado', None)
        b['subtitulo'] = ' '.join(b.pop('_lineas')[1:])
        if b.get('dia') and b.get('lugar') and b.get('hora'):
            out.append(b)
        else:
            falta = [k for k in ('dia', 'lugar', 'hora') if not b.get(k)]
            b['_no_se_publica'] = 'sin ' + ', sin '.join(falta)
            out.append(b)
    return out


# «Título (Director) 17 min.» — cada corto de un bloque de Caleidoscopio, en
# una línea. El paréntesis de apertura falta en alguna («El mundo es afuera
# Dir. Pablo Roldán) 22 min.»), así que se ancla por el CIERRE y los minutos.
RE_CORTO = re.compile(r'^(.*?)[\(]?\s*(?:Dir\.\s*)?([^()]+)\)\s*(\d{1,3})\s*min', re.I)


def cortos_de(lineas):
    """Los cortos que un bloque de Caleidoscopio proyecta.

    La lámina los lista uno por línea DENTRO de la ficha del bloque, con su
    director y su metraje. Sin esto, «Competencia nacional de cortometrajes»
    se publicaría como una función opaca de dos horas y las 22 obras del
    catálogo se quedarían sin función: son las que el festival compite.

    Un título largo se parte y su paréntesis cae en la línea siguiente
    («Un aparato para detectar fantasmas» / «(Mauricio Maldonado) 18 min.»),
    así que se intenta primero la línea sola y después pegada a la anterior.
    """
    out, pend = [], ''
    for x in lineas:
        x = x.strip()
        if not x or 'CALEIDOSCOPIO' in x or 'ompetencia nacional' in x:
            continue
        m = RE_CORTO.match(x) or (RE_CORTO.match(f'{pend} {x}') if pend else None)
        if not m:
            pend = x
            continue
        t, dire = m.group(1).strip(' .-'), m.group(2).strip(' .')
        # DOS LÍNEAS QUE DEJABAN EL TÍTULO VACÍO, y las cazó la cuenta del
        # catálogo: 20 cortos leídos contra 22 fichas de Caleidoscopio.
        #   · «El mundo es afuera Dir. Pablo Roldán) 22 min.» — al impreso le
        #     falta el paréntesis de apertura, así que todo cae en el director.
        #   · «Un aparato para detectar fantasmas» / «(Mauricio Maldonado) 18
        #     min.» — el título va en la línea de arriba.
        if not t and 'Dir.' in dire:
            t, dire = [x.strip(' .') for x in dire.split('Dir.', 1)]
        if not t and pend:
            t = pend.strip(' .-')
        if t:
            out.append({'titulo': t, 'director': dire, 'duracion_min': int(m.group(3))})
        pend = ''
    return out


def ficha(f):
    """Título, dirección y metadatos de la columna derecha."""
    ls = [x for x in f['ficha'] if x.strip()]
    d = {}
    # la FRANJA, cuando la lámina la rotula encima del título
    # SOLO «Franja …». Antes entraban también «Muestra …» y «Competencia …»,
    # y la «Muestra Red de Audiovisuales de Medellín» del viernes perdía su
    # título entero: el rótulo se lo comía y la función salía sin nombre.
    if len(ls) > 1 and re.match(r'^Franja\b', ls[0], re.I):
        d['franja'] = ls.pop(0)
    # UN RÓTULO NO ES UN TÍTULO. La lámina grita «ESTRENO» o «ACTO DE
    # CLAUSURA» encima de la obra, y tomando la primera línea como título la
    # clausura del domingo se llamaba «ACTO DE CLAUSURA» y «Mûpã (Madre)»
    # desaparecía. La mayúscula sostenida de una línea corta, con la obra
    # debajo, es el rótulo del festival.
    while len(ls) > 1 and re.match(r'^[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ .:·-]{4,}$', ls[0]):
        d.setdefault('rotulo', ls.pop(0).strip())
    if not ls:
        return d
    # EL TÍTULO QUE SIGUE EN LA LÍNEA DE ABAJO. La columna es estrecha y el
    # festival parte los títulos largos: «Cien años de soledad (SO2E6):» /
    # «Eran más de tres mil», «Panel: Diversidad de liderazgos y» / «relevo
    # generacional». Tomando solo la primera línea salían ocho funciones con
    # el título a medias, una de ellas terminada en dos puntos.
    #
    # Se une SOLO cuando la primera línea pide continuación —acaba en dos
    # puntos o en conjunción/preposición—, que es lo que se puede afirmar sin
    # adivinar. «Charla: Arte, verdad y compromiso social» está completa y la
    # línea siguiente («Ponentes:») no se le pega.
    # El guión final parte una PALABRA («Días de noche. Cró-» / «nica…») y se
    # une sin espacio; lo demás se une con espacio.
    corte = re.compile(r'(-|:|\b(?:y|e|o|u|de|del|la|el|los|las|en|con|para|'
                       r'por|a|al|que|su)\.?)$', re.I)
    titulo = [ls.pop(0).strip()]
    while ls and corte.search(titulo[-1]) and not ls[0].startswith('Dir.') \
            and not RE_FICHA.match(ls[0]) \
            and not re.match(r'^(Ponentes|Conversatorio|Organiza|Producci[óo]n|'
                             r'Tallerista|Modera)\b', ls[0], re.I):
        titulo.append(ls.pop(0).strip())
    t0 = titulo[0]
    for x in titulo[1:]:
        t0 = t0[:-1] + x if t0.endswith('-') else t0 + ' ' + x
    d['titulo'] = t0
    resto = ls
    for x in resto:
        if x.startswith('Dir.'):
            d['director'] = x[4:].strip(' .')
        m = RE_FICHA.match(x)
        if m:
            d['pais'] = m.group(1).strip()
            d['anio'] = int(m.group(2))
            d['duracion_min'] = int(m.group(3))
            d['genero'] = m.group(4).strip()
    if d.get('rotulo') == 'CALEIDOSCOPIO':
        cortos = cortos_de(resto)
        if cortos:
            d['cortos'] = cortos
            d['duracion_min'] = sum(c['duracion_min'] for c in cortos)
            return d
    notas = [x for x in resto if not x.startswith('Dir.') and not RE_FICHA.match(x)]
    if notas:
        d['_extra'] = ' '.join(notas)
    return d


def main():
    rutas = sorted(f'{LAMINAS}/{n}' for n in os.listdir(LAMINAS) if n.endswith('.jpg'))
    crudo = ocr(rutas)
    funciones, sin_dia, tall, colados = [], [], [], []
    for ruta in rutas:
        k = os.path.basename(ruta)
        ls = crudo.get(k) or crudo.get(ruta) or []
        if any('TALLERES' == c['t'].strip() for c in ls if c['y'] < 0.075):
            tall = talleres(ls)
            continue
        dia = dia_de(ls)
        if not dia:
            sin_dia.append(k)
            continue
        hay_cols = any(c['x'] >= COL_FICHA and c['y'] > 0.075 for c in ls)
        if hay_cols:
            fs, col = filas(ls, dia)
            colados += [f'{k}: {c}' for c in col]
        else:
            fs = una_columna(ls, dia)
        for f in fs:
            f.pop('_y', None)
            f.update(ficha(f))
            f.pop('ficha', None)
            f['_lamina'] = k
            funciones.append(f)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    json.dump({'_provenance': provenance(
        'Instagram @festicinejardin — el carrusel de programación',
        que_aporta='la parrilla entera: día, hora, sede y ficha. La web del '
                   'festival no publica programación de 2026',
        url=f'https://www.instagram.com/p/{POST}/',
        metodo='OCR con cajas sobre las 14 láminas; el día sale de la cabecera '
               'de cada una y la hora vale para todas las sedes que cuelgan'),
        'funciones': funciones,
        'talleres': tall,
        '_laminas_sin_dia': sin_dia,
        '_colados_en_la_columna_de_sede': colados},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if colados:
        print(f'   {len(colados)} línea(s) descartadas de la columna de sede: '
              + ' · '.join(colados[:4]))
    pub = [t for t in tall if not t.get('_no_se_publica')]
    print(f'   talleres: {len(pub)} publicables de {len(tall)}')
    for t in tall:
        if t.get('_no_se_publica'):
            print(f"      ✗ «{t['titulo'][:44]}» — {t['_no_se_publica']}")
    print(f'{len(funciones)} funciones · {len(rutas)} láminas '
          f'({len(sin_dia)} sin día: {", ".join(sin_dia)}) → {os.path.basename(OUT)}')
    import collections
    for d, n in sorted(collections.Counter(f['dia'] for f in funciones).items()):
        print(f'   {d}: {n}')


if __name__ == '__main__':
    main()
