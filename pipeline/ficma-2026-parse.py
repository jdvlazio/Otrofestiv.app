# -*- coding: utf-8 -*-
"""Del OCR de FICMA 17 → un registro por función.

SIRVE PARA LAS DOS EDICIONES. La plantilla del PDF de SEPTIEMBRE —la parrilla
de la reprogramación, 78 páginas— es la misma que la de agosto, campo por
campo. Copiar el parser habría sido la forma conocida de que dos copias del
mismo criterio diverjan, así que el archivo de entrada y el de salida se pasan
por argumento:

    python3 pipeline/ficma-2026-parse.py [ocr.json] [crudo.json]

Sin argumentos lee el OCR de agosto, que es como corrió hasta el 17 sep 2026.

La plantilla del PDF es rígida y eso es lo que hace fiable el parseo: la
columna de DATOS vive a la derecha (x≳0.55) y el póster ocupa la izquierda.
Sin ese corte, las críticas impresas en el afiche («UMA AVENTURA SOBRE
RESISTÊNCIA») se cuelan como si fueran campos.

Cada etiqueta —DIRECCIÓN:, PAÍS:, DURACIÓN:, AÑO:, LUGAR:, HORA:— toma como
valor la línea siguiente de SU columna, no la siguiente del documento.
"""
import json, re, os, unicodedata, collections
import sys, os as _os; sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import lib  # dueño único de norm/hora24/sinacento — [lib-unica]

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
# La columna de datos está acotada por AMBOS lados. A la izquierda para dejar
# fuera el póster —sus críticas impresas se colaban como campos—; a la derecha
# porque el rótulo «FERIA INTERNACIONAL DE CINE DE MANIZALES» va rotado en el
# margen y pdftotext/Vision lo devuelven como líneas sueltas en x≳0.88, que
# aterrizaban como nombre de sede.
COL_X, COL_X_MAX = 0.55, 0.88
# LA OTRA MAQUETA. Cinco páginas del PDF de septiembre no son ficha de obra sino
# ACTIVIDAD —un concierto, una noche de vinilos, dos muestras de cortos, la
# fiesta de clausura—: no llevan afiche a la izquierda y la columna de datos va
# CENTRADA. Con el corte de la maqueta de película no se leía ni la sede ni la
# hora y las cinco caían en «sin clasificar». Solo se usa cuando la columna de
# la derecha no devolvió nada: en una ficha de obra, esta ventana se comería las
# críticas impresas en el póster.
COL_X_CENTRO, COL_X_CENTRO_MAX = 0.28, 0.80
DIAS = 'LUNES|MARTES|MIÉRCOLES|MIERCOLES|JUEVES|VIERNES|SÁBADO|SABADO|DOMINGO'
MES = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,'JULIO':7,
       'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}
# Tabla canónica sede→(sede, sala). Explícita y no heurística sobre el guion:
# «Cine al barrio - Samaria» también lo lleva y ahí Samaria es el LUGAR, no una
# sala. Confirmado por el festival (8 ago): Olimpia y Fundadores son salas del
# Teatro los Fundadores, y Fundadores es la sala grande.
SEDE_SALA = {
    'Auditorio Olimpia - Teatro los Fundadores': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Olimpia':                                   ('Teatro los Fundadores', 'Sala Olimpia'),
    'Sala Fundadores':                           ('Teatro los Fundadores', 'Sala Fundadores'),
    'Fundadores':                                ('Teatro los Fundadores', 'Sala Fundadores'),
    # Las universidades traen el auditorio dentro del nombre, igual que el Teatro.
    # Sin esto, cada auditorio era una «sede» distinta en el mismo campus y el
    # chequeo de sedes apiladas las habría marcado a metros una de otra.
    'Auditorio Roberto Vélez Correa - Universidad de Caldas':
        ('Universidad de Caldas', 'Auditorio Roberto Vélez Correa'),
    # Los dos campus de la Nacional son SITIOS distintos —Palogrande y El
    # Cable, a más de un km—: fundirlos bajo «Universidad Nacional» los habría
    # puesto en el mismo punto del mapa.
    'Auditorio Juan Hurtado - Universidad Nacional':
        ('Universidad Nacional · Palogrande', 'Auditorio Juan Hurtado'),
    'Auditorio principal Campus El Cable - Universidad Nacional de Colombia':
        ('Universidad Nacional · El Cable', 'Auditorio principal'),
    'Universidad Autónoma - Aula Torreón F-101':
        ('Universidad Autónoma', 'Aula Torreón F-101'),
}
# Ciclos itinerantes del festival: la marca va delante y el lugar real detrás.
# OJO con «Expoferias - Cine fest», que va al revés: Expoferias es el LUGAR (el
# recinto ferial) y «Cine fest» el nombre que el festival le da a su actividad
# ahí. Se supo por el PDF de la Franja Académica, que lo llama solo «Expoferias».
# Por eso el ciclo no se deduce del guion: se declara.
CICLOS = ('Cine al barrio', 'Cine bajo la niebla', 'Cine al aire libre')
CICLO_DETRAS = {'Expoferias - Cine fest': ('Expoferias', 'Cine fest')}
# La etiqueta LUGAR a veces recoge la línea de abajo, que no es el lugar: en la
# noche de vinilos, «Clandestino Records / Dj Kalibre» — el DJ es el cartel, no
# la sede. Se declara el recorte, no se adivina con una heurística sobre quién
# parece nombre propio.
COLA_QUE_NO_ES_SEDE = {'Clandestino Records Di Kalibre': 'Clandestino Records',
                       'Clandestino Records Dj Kalibre': 'Clandestino Records'}
# LA LÁMINA QUE SE CONTRADICE A SÍ MISMA. Cada página lleva la hora DOS veces:
# en el badge de arriba y en el campo HORA de abajo. En 68 de 70 coinciden. En
# las dos de la función de clausura no, y el campo es el que miente: los tres
# cortos del viernes 25 en Redentoristas llevan «7:00 pm» abajo —copiado de la
# primera lámina— mientras los badges dicen 7:00, 7:20 y 8:00 PM, que es lo
# único coherente con sus duraciones (11, 30 y 90 min). Verificado mirando las
# dos páginas. Se corrige por página, no con una regla general: dos casos no
# alcanzan para decidir quién manda siempre.
HORA_ERRATA = {
    'p-70.jpg': ('19:20', '«Entrelazados»: el badge dice 7:20 PM y el campo HORA '
                          '7:00 pm, copiado de la lámina anterior'),
    'p-71.jpg': ('20:00', '«La Marcha del Hambre»: el badge dice 8:00 PM y el campo '
                          'HORA 7:00 pm, copiado de la lámina anterior'),
}
ETIQUETAS = {'DIRECCIÓN':'director','DIRECCION':'director','PAÍS':'pais','PAIS':'pais',
             'DURACIÓN':'duracion','DURACION':'duracion','AÑO':'anio','ANO':'anio',
             'LUGAR':'sede','HORA':'hora',
             # Solo aparece en las actividades que se PAGAN, y aparece: la
             # noche de vinilos cuesta 20k y la fiesta de clausura tiene
             # preventa. El festival dice en su web que «todas las actividades
             # son de acceso libre» — con su propio programa en la mano, eso ya
             # no es cierto, y una entrada que se cobra no puede publicarse
             # como gratis.
             'COSTO':'costo'}


# [lib-unica] renombrada desde `hora24` el 17 ago 2026.
# Devuelve «» cuando la hora YA viene en 24h — es un parser de la franja del
# PDF, no un conversor. `lib.hora24` devuelve la hora tal cual.
def hora24_pdf(s):
    m = re.search(r'(\d{1,2})[:.](\d{2})\s*([ap])', s.strip(), re.I)
    if not m:
        return ''
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == 'p' and h != 12: h += 12
    if ap == 'a' and h == 12: h = 0
    return f'{h:02d}:{mm}'


# La COMILLA DE APERTURA es lo único que Vision falla sistemáticamente en esta
# plantilla: la devuelve como «¿'», «*», «ii» o «'» según la tipografía del
# afiche de fondo. La de cierre sale bien. Por eso el título se toma hasta el
# cierre y se le limpia el arranque — no hay título de esta parrilla que empiece
# de verdad por un signo, y el original queda guardado en `_titulo_ocr`.
# Las letras sueltas SOLO cuentan como basura si van seguidas de espacio: sin
# esa condición la regla le comió el «Ll» a «Llueve sobre Babel» y lo publicó
# como «ueve sobre Babel». Una limpieza que muerde el dato es peor que el dato
# sucio, y por eso el título original se guarda siempre.
_BASURA = re.compile(r'^\s*(?:[“"«*\'`~.,;:•·—–¿¡-]+\s*|(?:ii|ll|Il)\s+)+')


def limpia_titulo(t):
    t = re.sub(r'\s+', ' ', (t or '')).strip()
    m = re.match(r'^(.*?)\s*["”»]\s*$', t)
    if m:
        t = m.group(1)
    return _BASURA.sub('', t).strip(' "\'“”«»')


def main():
    ENTRADA = sys.argv[1] if len(sys.argv) > 1 else f'{ST}/ficma-2026-ocr.json'
    SALIDA = sys.argv[2] if len(sys.argv) > 2 else f'{ST}/ficma-2026-crudo.json'
    d = json.load(open(ENTRADA, encoding='utf-8'))
    # el bloque de procedencia no es una página
    proc = d.pop('_provenance', None)
    paginas = sorted(d, key=lambda k: int(re.search(r'(\d+)', k).group(1)))

    dia_actual = None
    funcs, portadas, sin_clasificar = [], [], []

    for pag in paginas:
        # El rótulo «FERIA INTERNACIONAL DE CINE DE MANIZALES» va ROTADO en los
        # márgenes. Vision lo devuelve como líneas normales y sus fragmentos
        # («PE MANIZALES», «pENANIZALES» — rotado, el OCR lo destroza) se pegaban
        # al nombre de la sede. Se reconocen por geometría, no por texto: una
        # línea horizontal es más ancha que alta; una rotada, al revés.
        ls = sorted([l for l in d[pag] if l['w'] > l['h']], key=lambda l: l['y'])
        texto = ' '.join(l['t'] for l in ls)
        # El sello «PRESENCIA DEL DIRECTOR / DE LA DIRECTORA» flota sobre la
        # maqueta y su posición varía: unas veces cae en la cabecera y se lee
        # como sección, otras junto a la columna y se lee como país. Se guarda
        # como has_qa (arriba, sobre el texto completo) y se saca del flujo.
        SELLO = re.compile(r'^(PRESENCIA|DEL DIRECTOR|DE LA DIRECTOR)', re.I)
        ls = [l for l in ls if not SELLO.match(lib.sinacento(l['t']).strip())]

        # ── portada de día: «PROGRAMACIÓN / LUNES 10 DE AGOSTO DE 2026» ──
        mp = re.search(rf'({DIAS})\s+(\d{{1,2}})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{{4}})',
                       lib.sinacento(texto).replace('  ', ' '), re.I)
        if mp and 'PROGRAMACION' in lib.sinacento(texto):
            mes = MES.get(lib.sinacento(mp.group(3)), 0)
            dia_actual = f'{mp.group(4)}-{mes:02d}-{int(mp.group(2)):02d}'
            portadas.append({'pagina': pag, 'dia': dia_actual, 'rotulo': mp.group(0)})
            continue

        # ── página de función ──
        es_etiqueta = lambda t: ETIQUETAS.get(lib.sinacento((re.match(r'^([A-ZÁÉÍÓÚÑ]+)\s*:', t.strip()) or [None, ''])[1]))
        col = [l for l in ls if COL_X <= l['x'] <= COL_X_MAX]
        if not any(es_etiqueta(l['t']) for l in col):
            col = [l for l in ls if COL_X_CENTRO <= l['x'] <= COL_X_CENTRO_MAX]
            maqueta = 'centrada'
        else:
            maqueta = 'ficha'
        campos = {}
        for i, l in enumerate(col):
            k = es_etiqueta(l['t'])
            if not k:
                continue
            # El valor puede venir pegado a la etiqueta o debajo, y ocupar VARIAS
            # líneas: «Auditorio Olimpia - / Universidad de Caldas» se partía en
            # dos y la sede quedaba en «Auditorio Olimpia -». Se toma todo hasta
            # la etiqueta siguiente.
            partes = [l['t'].split(':', 1)[1].strip()]
            for sig in col[i + 1:]:
                if es_etiqueta(sig['t']):
                    break
                partes.append(sig['t'].strip())
            v = ' '.join(p for p in partes if p)
            # Cola de basura del rótulo rotado que sobrevivió al filtro de
            # geometría: un token suelto de 1–2 caracteres al final («… Cine
            # fest ~», «… Universidad Nacional- g»). Nunca es parte del nombre.
            v = re.sub(r'[\s\-~]+\S{1,2}$', '', v) if re.search(r'[\s\-~]+\S{1,2}$', v) and len(v) > 12 else v
            campos[k] = re.sub(r'\s*[-~]\s*$', '', v).strip()

        if not campos.get('hora') and not campos.get('sede'):
            sin_clasificar.append({'pagina': pag, 'texto': texto[:160]})
            continue

        # Sección y título: las líneas centradas de arriba, antes de la primera
        # etiqueta. El título va entre comillas, pero puede ocupar DOS líneas
        # («"El hogar fue sepultado en esa tierra / que nunca pudimos
        # encontrar"»): se unen y se extrae el tramo entrecomillado completo.
        # y>0.10 deja fuera la franja superior (logo, badge de día y hora): sin
        # ese corte, «MIÉRCOLES 12» ganaba como sección por ser mayúscula y larga.
        # La cabecera es un bloque centrado: primero la SECCIÓN en mayúsculas,
        # debajo el TÍTULO. Se lee por orden y no por forma —«ARTE» y «MÚSICA»
        # son secciones de 4 y 6 letras, y un umbral de longitud las perdía—.
        # x<0.70 deja fuera el sello «PRESENCIA / DEL DIRECTOR» de la esquina.
        cabeza = [l['t'].strip() for l in ls if 0.10 < l['y'] < 0.26 and l['x'] < 0.70]
        # La sección puede ocupar VARIAS líneas: «EN ALIANZA CON / EL FESTIVAL
        # DE DERECHOS HUMANOS». Se toman todas las mayúsculas seguidas del tope.
        # El nombre va verbatim como lo escribe el festival — no se normaliza.
        k = 0
        while k < len(cabeza) and cabeza[k].isupper():
            k += 1
        seccion = ' '.join(cabeza[:k])
        resto = ' '.join(cabeza[k:])
        # El título va entrecomillado y puede ocupar dos líneas. Cuando el OCR
        # pierde las comillas, se toma el resto de la cabecera tal cual.
        mt = re.search(r'[“"«]\s*(.+?)\s*[”"»]', resto, re.S)
        titulo_ocr = re.sub(r'\s+', ' ', mt.group(1) if mt else resto).strip()
        titulo = limpia_titulo(titulo_ocr)
        # «PRESENCIA DEL DIRECTOR», sello en la esquina: es un Q&A. Solo lo trae
        # esta fuente; ninguna otra lo publica.
        has_qa = 'PRESENCIA' in lib.sinacento(texto) and 'DIRECTOR' in lib.sinacento(texto)
        # badge superior derecho: «JUEVES 13» y «3:00 PM»
        # El badge superior derecho trae el día y la hora, a veces en dos líneas
        # («9:00 AM» / «SÁBADO 19») y a veces en UNA sola («4:00 PM DOMINGO 20»).
        # Buscarlos al PRINCIPIO de la línea perdía la mitad de las páginas —40
        # de 70— y con ellas el contraste que hace de segunda lectura.
        _alto = [l['t'] for l in ls if l['y'] < 0.08]
        badge_dia = next((m.group(0) for t in _alto
                          for m in [re.search(rf'({DIAS})\s+\d{{1,2}}', lib.sinacento(t))] if m), '')
        badge_hora = next((m.group(0) for t in _alto
                           for m in [re.search(r'\d{1,2}:\d{2}\s*[AP]M?', t, re.I)] if m), '')

        hora = hora24_pdf(campos.get('hora', '')) or hora24_pdf(badge_hora)
        errata = HORA_ERRATA.get(pag)
        dur = re.search(r'(\d+)', campos.get('duracion', ''))
        anio = re.search(r'(19|20)\d{2}', campos.get('anio', ''))
        funcs.append({
            'pagina': pag,
            'maqueta': maqueta,
            'costo': campos.get('costo', ''),
            'dia': dia_actual,
            'dia_badge': badge_dia,
            'hora': errata[0] if errata else hora,
            **({'_hora_errata': f'{errata[1]}; se publica {errata[0]} y no {hora}'}
               if errata else {}),
            'sede': campos.get('sede', ''),
            'seccion': seccion,
            'titulo': titulo,
            **({'_titulo_ocr': titulo_ocr} if titulo != titulo_ocr else {}),
            'director': campos.get('director', ''),
            'pais': campos.get('pais', ''),
            'duracion_min': int(dur.group(1)) if dur else None,
            'anio': int(anio.group(0)) if anio else None,
            'has_qa': has_qa,
        })

    # sede/sala/ciclo, en el mismo paso: si vive fuera, una recorrida del parser
    # lo pisa (pasó en FICDEH y costó una tarde).
    for f in funcs:
        cruda = COLA_QUE_NO_ES_SEDE.get(f['sede'], f['sede'])
        if cruda in CICLO_DETRAS:
            f['sede'], f['ciclo'] = CICLO_DETRAS[cruda]
            f['sala'] = ''
        elif cruda in SEDE_SALA:
            f['sede'], f['sala'], f['ciclo'] = (*SEDE_SALA[cruda], '')
        else:
            c = next((x for x in CICLOS if cruda.lower().startswith(x.lower())), '')
            f['sede'] = cruda.split('-', 1)[1].strip() if (c and '-' in cruda) else cruda
            f['sala'], f['ciclo'] = '', c
        f['_sede_cruda'] = cruda

    json.dump({'_fuente': (proc or {}).get('fuente',
                   'FICMA 17 - PROGRAMACIÓN.pdf · páginas de imagen, OCR con Vision (macOS)'),
               '_provenance': proc,
               'portadas': portadas, 'funciones': funcs, 'sin_clasificar': sin_clasificar},
              open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    faltan = lambda k: sum(1 for f in funcs if not f[k])
    print(f'páginas {len(paginas)} · portadas de día {len(portadas)} · funciones {len(funcs)} · sin clasificar {len(sin_clasificar)}')
    print(f'días detectados: {sorted(p["dia"] for p in portadas)}')
    print(f'obras distintas: {len({f["titulo"] for f in funcs if f["titulo"]})}')
    for k in ('titulo','hora','sede','seccion','director','pais','duracion_min','anio','dia'):
        print(f'  sin {k:13} {faltan(k)}')
    print('\nsedes:', dict(collections.Counter(f['sede'] for f in funcs)))


if __name__ == '__main__':
    main()
