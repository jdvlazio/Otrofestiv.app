# -*- coding: utf-8 -*-
"""Arma el crudo de Cinemancia 2026 desde las DOS fuentes oficiales.

  · la PARRILLA del PDF  → las 86 funciones: día, hora, sede, duración
  · la HOJA del festival → qué obras van en cada programa, y las 10 charlas

La parrilla dice CUÁNDO y DÓNDE; la hoja dice QUÉ. Ninguna de las dos basta:
la parrilla anuncia «Competencia de cortometrajes Programa 1» sin listar sus
cortos, y la hoja no tiene las funciones que no son programa.

El catálogo previo (build.json) aporta sinopsis y datos de las obras que ya
teníamos; las 15 obras nuevas de la competencia internacional entran con lo
que trae la hoja.
"""
import json, re, unicodedata, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = f'{REPO}/festivals/staging'

# La parrilla del PDF mete la nota al pie DENTRO de la celda del título:
# «Foro de la Crítica Sesión 1 Inscripción previa*», «Seminario de la imagen
# con Luciana Decker *Inscripción previa». Eso no es el nombre de la actividad
# — es una condición de acceso, y viajaba hasta la ficha, el plan y lo que el
# usuario comparte. Peor: partía en dos el seminario de Luciana Decker, que son
# TRES sesiones (9, 10 y 11 SEP, 09:00, misma sede) y parecían dos actividades
# distintas porque una llevaba el asterisco.
# El dato de acceso NO se pierde al limpiar: CON_INSCRIPCION ya lo deduce
# del nombre de la actividad, y lo hacía bien desde antes de este arreglo.
_INSCRIPCION = re.compile(r'\s*\*?\s*Inscripci[óo]n\s+previa\s*\*?\s*', re.I)


def sin_nota_de_inscripcion(t):
    """El título sin la nota al pie. NO decide si pide inscripción: ese hecho
    ya tiene dueño único en CON_INSCRIPCION, que lo deduce del NOMBRE de la
    actividad y no del asterisco — más robusto, porque el PDF marcó solo una
    de las tres sesiones del seminario de Luciana Decker."""
    return re.sub(r'\s+', ' ', _INSCRIPCION.sub(' ', t)).strip()


def clave(s):
    """Clave de comparación SIN espacios. No es lib.clave(), que los conserva:
    acá se busca un título DENTRO de otro («Macho Dancer» dentro de «Macho
    Dancer Lino Brocka») y los espacios del original estorban."""
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

# Afiches de TMDB hallados en una segunda búsqueda POR TÍTULO. La primera
# pasada consultó solo las obras que ya traían tmdbId y las 11 volvieron sin
# arte; estas tres llegaron después, con los programas que envió el festival,
# y nunca se habían buscado.
#
# Verificadas contra director, año y duración antes de aceptarlas. La búsqueda
# devolvió TAMBIÉN un «Valparaíso Eterno» con afiche, y NO es el nuestro: es de
# 2003, alemana-chilena-austríaca, dirigida por Rosana Saavedra y Birgit
# Foerster; el nuestro es de Sergio Navarro, 1991. Coincidir en título no es
# coincidir en obra.
AFICHES_TMDB = {
    # Rajendra Gour, 1968, 23′ — coincide con nuestro dato (22′). TMDB 1004090.
    'Sight and desire (eyes)': 'https://image.tmdb.org/t/p/w500/1k65lhMLIibhiTKXwricC9peNyb.jpg',
}


# Afiches ORIGINALES que envió el festival (21 AGO). No son fotogramas: son el
# arte de la obra, con su título y sus créditos. Van como `oficial` —a sangre,
# sin etiqueta ni título encima— y conservan su proporción: la regla de estirar
# a 2:3 es del keyArt del splash, no de los pósters.
AFICHES_OFICIALES = {
    'Lamentos de un balcón':                            '/assets/cinemancia/lamentos-de-un-balcon.jpg',
    'Hold My Hand':                                     '/assets/cinemancia/hold-my-hand.jpg',
    "Procès d'un jeune poète / Juicio a un joven poeta": '/assets/cinemancia/juicio-a-un-joven-poeta.jpg',
}


# ── Fotogramas oficiales del festival ─────────────────────────────────────────
# TMDB no sirve para estas obras: se consultaron las 11 que tenían tmdbId y las
# 11 devolvieron poster_path vacío. No es un fallo de la consulta —se verificó
# contra una ficha conocida, que sí trae afiche—: son cortos chilenos y
# experimentales que TMDB cataloga sin arte.
#
# La ficha de cada obra en cinemanciafestival.com sí publica un fotograma 16:9
# propio (se comprobó que cambia por obra, no es un genérico del sitio).
# Normalizados a 896x504 JPEG, el mismo estándar que las editoriales de VARTEX.
#
# NO están «El santo y el milagro» ni «Valparaíso eterno», las dos de Sergio
# Navarro: sus fotogramas traen incrustado el logo de Cineteca Universidad de
# Chile, grande y sobre la imagen. Se le piden al festival antes que publicar
# una tarjeta con la marca de un tercero. «Caminito al Cielo» tiene ficha en la
# web pero sin og:image, así que también se pide.
FOTOGRAMAS = {
    'El sueño de Ana':                    '/assets/cinemancia/el-sueno-de-ana.jpg',
    'Obreras saliendo de la fábrica':     '/assets/cinemancia/obreras-saliendo-de-la-fabrica.jpg',
    'Spot Fuera de campo 1':              '/assets/cinemancia/spot-fuera-de-campo-1.jpg',
    'Spot Fuera de campo 2':              '/assets/cinemancia/spot-fuera-de-campo-2.jpg',
    'Un aparato para detectar fantasmas': '/assets/cinemancia/un-aparato-para-detectar-fantasmas.jpg',
    'Ver y escuchar':                     '/assets/cinemancia/ver-y-escuchar.jpg',
    # De la carpeta de Drive que envió el festival (21 AGO). De las cuatro obras
    # que mandó ahí, solo estas dos vienen SIN el logo de Cineteca U. de Chile
    # incrustado — ver la nota de FOTOGRAMAS_CON_MARCA.
    'Caminito al Cielo':                  '/assets/cinemancia/caminito-al-cielo.jpg',
    'Todas las canciones del mundo':      '/assets/cinemancia/todas-las-canciones-del-mundo.jpg',
    # Los dos de Sergio Navarro llevaban el logo de Cineteca U. de Chile arriba
    # a la derecha, y por eso los descarté primero. Juan preguntó lo obvio: si
    # recortando no daba. Sí da — el logo ocupa una banda superior y estas
    # imágenes son 4:3, así que al recortar a 16:9 por DEBAJO de él se va
    # entero y la composición se sostiene (en «Valparaíso eterno» incluso
    # mejora: quedan los buques sobre la bahía y la ciudad abajo).
    # No es retocar la imagen: es encuadrarla, que es lo que ya se hace con
    # todos los fotogramas para llevarlos a 16:9.
    'El santo y el milagro':              '/assets/cinemancia/el-santo-y-el-milagro.jpg',
    'Valparaíso eterno':                  '/assets/cinemancia/valparaiso-eterno.jpg',
}

# El festival envió también fotogramas de «El santo y el milagro» y «Valparaíso
# eterno», y avisó que de esas obras no existe afiche. Revisé las tres imágenes
# de cada carpeta: TODAS llevan el logo de Cineteca U. de Chile sobre la imagen,
# porque son fotogramas de restauración del archivo que las conserva. Se quedan
# sin afiche antes que publicar una tarjeta con la marca de un tercero.
# Además, una de las de «El santo y el milagro» no era de esa obra: es el rótulo
# de «Contento señor, contento», otra película de Navarro.
# (Resuelto por recorte — ver la nota en FOTOGRAMAS.)


# ── Los cuatro programas que el festival mandó aparte ─────────────────────────
# La parrilla los anuncia por su nombre y NO lista su contenido, así que estas
# cuatro funciones se publicaban vacías. El festival envió el orden exacto en
# una hoja aparte (21 AGO), y de ahí sale
# `cinemancia-2026-otros-programas.json`.
#
# El hallazgo: la función de 55′ del miércoles 9 NO es un foco de Decker, como
# la titula la parrilla, sino su CARTA BLANCA — tres obras de otros directores
# que ella curó. El festival ya tiene sección «🃏 Carta blanca» y la parrilla
# la llamaba igual que los focos. Las duraciones lo confirman solas: los focos
# suman 82′ (las seis obras de Decker) y la carta blanca 55′ (19+30+6).
#
# Clave con SEDE: el viernes 4 a las 19:00 corren TRES funciones distintas.
OTROS_PROGRAMAS = {
    ('2026-09-04', '19:00', 'Antimateria Libros y Café Medellín'):
        'Alquimia de la luz el cine de Luciana Decker',
    ('2026-09-08', '15:00', 'La Capilla del Claustro Comfama Medellín'):
        'Alquimia de la luz el cine de Luciana Decker',
    ('2026-09-09', '16:00', 'Centro Colombo Americano Sede centro sala 2 Medellín'):
        'Carta Blanca Luciana Decker',
    ('2026-09-11', '17:00', 'Centro Colombo Americano Sede centro sala 2 Medellín'):
        'Programa de cortometrajes Rajenda Gour',
}


def otros_programas():
    """{nombre de programa: [obras en el orden del festival]}."""
    try:
        d = json.load(open(f'{S}/cinemancia-2026-otros-programas.json', encoding='utf-8'))
    except FileNotFoundError:
        return {}
    return {p['programa']: p['obras'] for p in d.get('programas', [])}


# ── Correcciones que confirmó el festival (21 AGO) ────────────────────────────
# Las levantó nuestra propia auditoría de duraciones: un programa cuya suma no
# cuadra con lo declarado es un programa al que le falta algo, o cuyo número
# está mal. Se le preguntó al festival y contestó las dos.
#
# 1) «Pere Portabella: legado inmarcesible» — la parrilla decía 80′ y sus tres
#    obras suman 99′. El festival: la correcta es 99. (El otro pase de las
#    mismas tres ya declaraba 99′, que fue lo que nos hizo dudar.)
DURACION_CORREGIDA = {
    ('2026-09-05', '18:00', 'Teatro Caribe Itagüí'): 99,
}

# 2) «Fuera de competencia programa 1» — declaraba 88′ y sus obras sumaban 74′.
#    Faltaba una, y el festival la mandó. Sus cinco duraciones suman 90′; los
#    dos minutos de diferencia con los 88′ de la parrilla son de su propio
#    dato y no se tocan.
OBRAS_AÑADIDAS = {
    ('2026-09-10', '16:00', 'Centro Colombo Americano Sede centro sala 1 Medellín'): [
        {'title': 'Ya se ven los tigres en la lluvia', 'director': 'Oscar Ruiz Navia',
         'country': 'Colombia, Canadá', 'year': 2025, 'duration': 16},
    ],
}


def catalogo():
    """Las 109 obras del catálogo, fusionando TRES fuentes por obra.

    Ninguna basta sola, y el publicador lo cazó al ver que el build perdía
    sinopsis contra producción:

      · el sidecar tmdb trae las 109 obras, pero solo 52 sinopsis;
      · el sidecar web trae 56 sinopsis sacadas de la ficha del festival;
      · y el JSON PUBLICADO trae 89, porque a lo largo del onboarding se
        arreglaron a mano ahí y nadie las devolvió aguas arriba.

    Se fusiona en ese orden y gana el primero que tenga el campo lleno, así
    que un arreglo hecho abajo no se pierde al regenerar."""
    d = json.load(open(f'{S}/cinemancia-2026-tmdb.json', encoding='utf-8'))
    # Se indexa el título ENTERO y además cada parte separada por «/». Los
    # títulos bilingües no vienen en el mismo orden ni con las mismas
    # variantes: el catálogo trae «La tercera opción / Die dritte Option / The
    # Third Option» y la parrilla solo las dos primeras, así que buscar la
    # clave entera dentro del crudo nunca casaba.
    # sinopsis de la ficha web del festival, por título
    web = {}
    try:
        for o in json.load(open(f'{S}/cinemancia-2026-web.json', encoding='utf-8'))['obras']:
            if o.get('synopsis_web'): web[clave(o.get('title_web'))] = o['synopsis_web']
    except FileNotFoundError:
        pass
    # DURACIÓN: manda el listado del festival, que la trae escrita en su propio
    # texto («Disciplina (Dir. Affonso Uchôa, Brasil, 2026, 45’)»). Las 109
    # obras la tienen. El sidecar tmdb no trae ninguna.
    lst = {}
    try:
        _l = json.load(open(f'{S}/cinemancia-2026-listado.json', encoding='utf-8'))
        for o in (_l if isinstance(_l, list) else _l.get('obras', [])):
            t = o.get('title') or o.get('titulo')
            if t and (o.get('duration') or o.get('duracion') or o.get('country')):
                lst[clave(t)] = o
    except FileNotFoundError:
        pass

    # lo que ya está PUBLICADO: último recurso, pero es donde viven los
    # arreglos a mano que nunca volvieron al sidecar.
    #
    # Un CONTENEDOR no es una obra. Indexarlo aquí abrió un bucle: la función
    # «Disciplina + Lolita en Honda» dura 106′ (lo que dice la celda), y cuando
    # esa función se titulaba solo «Disciplina» entraba a este índice como si
    # 106′ fuera la duración de la obra. De ahí volvía al catálogo en cada
    # regenerado, así que el error se volvía permanente y crecía: las DOS obras
    # del programa acababan con 106′ cada una, y el programa «sumaba» 212′.
    # Se indexan solo las funciones que NO son contenedor.
    pub = {}
    try:
        pd = json.load(open(f'{REPO}/festivals/cinemancia-2026.json', encoding='utf-8'))
        for f in pd['films']:
            hijos = list(f.get('film_list') or [])
            for o in ([f] if not hijos else []) + hijos:
                if o.get('title'): pub.setdefault(clave(o['title']), o)
    except FileNotFoundError:
        pass
    for o in d['obras']:
        k = clave(o.get('title'))
        p = pub.get(k, {})
        o.setdefault('tmdb_id', o.get('tmdbId'))
        if not o.get('synopsis'): o['synopsis'] = web.get(k) or p.get('synopsis')
        _l = lst.get(k) or {}
        if not o.get('duration'):
            _d = _l.get('duration') or _l.get('duracion')
            if _d: o['duration'] = f'{_d} min' if str(_d).isdigit() else str(_d)
        # El PAÍS venía en el mismo renglón del listado —«(Dir. Affonso Uchôa,
        # Brasil, 2026, 45’)»— para las 109 obras, y tampoco se usaba: 44 obras
        # se publicaban sin país, que es lo que alimenta la bandera.
        if not o.get('country') and _l.get('country'):
            o['country'] = _l['country']
        for campo_pub in ('synopsis_en', 'title_en', 'poster', 'posterSource', 'duration', 'country'):
            if not o.get(campo_pub) and p.get(campo_pub): o[campo_pub] = p[campo_pub]
        if not o.get('poster') and o.get('poster_tmdb'):
            o['poster'], o['posterSource'] = o['poster_tmdb'], 'tmdb'
        if not o.get('poster') and AFICHES_TMDB.get(o.get('title')):
            o['poster'], o['posterSource'] = AFICHES_TMDB[o['title']], 'tmdb'
        if not o.get('poster') and AFICHES_OFICIALES.get(o.get('title')):
            o['poster'], o['posterSource'] = AFICHES_OFICIALES[o['title']], 'oficial'
            o.setdefault('_poster_src', 'afiche original enviado por el festival (21 AGO)')
        if not o.get('poster') and FOTOGRAMAS.get(o.get('title')):
            o['poster'], o['posterSource'] = FOTOGRAMAS[o['title']], 'editorial'
            o.setdefault('_poster_src', 'fotograma de la ficha oficial del festival')
        if not o.get('duration') and o.get('runtime_tmdb'): o['duration'] = f"{o['runtime_tmdb']} min"
    out = {}
    for o in d['obras']:
        for campo in ('title', 'title_en'):
            t = o.get(campo)
            if not t: continue
            out.setdefault(clave(t), o)
            for parte in t.split('/'):
                if len(clave(parte)) > 6: out.setdefault(clave(parte), o)
    return out

def obra_de(o):
    """Ficha del catálogo → obra del crudo, con los nombres del contrato."""
    d = {'titulo': o.get('title'), 'director': o.get('director'),
         'seccion': o.get('section'),
         'pais': o.get('country'), 'anio': o.get('year'),
         'sinopsis': o.get('synopsis'), 'synopsis_en': o.get('synopsis_en'),
         'title_en': o.get('title_en'), 'poster': o.get('poster'),
         'posterSource': o.get('posterSource'), 'tmdb_id': o.get('tmdb_id'),
         'lbSlug': o.get('lbSlug')}
    dur = o.get('duration') or o.get('duracion_min') or o.get('runtime')
    m = re.match(r'^(\d+)', str(dur or ''))
    if m: d['duracion_min'] = int(m.group(1))
    if d.get('anio'):
        try: d['anio'] = int(d['anio'])
        except (TypeError, ValueError): d.pop('anio')
    return {k: v for k, v in d.items() if v not in (None, '', [], {})}

# CÓMO SE ENTRA — literal de la nota «Información importante · Boletería» del
# PDF oficial (pág. 2). No se deduce: el festival lo dice con todas las letras.
#
#   «A excepción de las funciones en Cineprox Las Américas y Cine MAMM, las
#    funciones del festival son de entrada libre.»
#
# El build anterior ponía is_free en las 89 funciones por igual, incluidas las
# de esas dos sedes, que SÍ cobran. En Cineprox las sillas son numeradas y la
# boleta se compra en taquilla; en Cine MAMM, en el primer piso del museo.
SEDES_PAGAS = {
    'Cineprox Las Américas': 'Boleta en taquilla — sillas numeradas',
    'Cine MAMM': 'Boleta en el primer piso del museo',
}
# Estas actividades piden inscripción previa (misma nota del PDF).
CON_INSCRIPCION = re.compile(r'Foro de la [Cc]r[íi]tica|C[áa]psula de Proyectos|'
                             r'Seminario de la imagen|Laboratorio Internacional de Montaje')


def acceso_de(sede, titulo):
    for k, v in SEDES_PAGAS.items():
        if k.lower() in (sede or '').lower(): return v
    if CON_INSCRIPCION.search(titulo or ''): return 'Entrada libre con inscripción previa'
    return 'Entrada libre'


def obras_en(crudo, cat):
    """TODAS las obras del catálogo que aparecen en un título de parrilla.

    Una celda de la parrilla junta varias películas con «+» y les intercala el
    director: «La tempestá + No contéis con los dedos + Vampir Cuadecuc Pere
    Portabella» son TRES. Quedarse con la coincidencia más larga —que era lo
    que hacía— perdía las otras dos, y eso pasaba en 28 funciones.

    Se buscan todas por posición y se descartan las que se solapan: si «Verano»
    cae dentro de un título más largo ya encontrado, no es una obra aparte.
    """
    c = clave(crudo)
    hits = []
    for k, o in cat.items():
        if len(k) < 6:
            continue
        i = c.find(k)
        if i >= 0:
            hits.append((i, i + len(k), k, o))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out, ocupado = [], []
    for ini, fin, k, o in hits:
        if any(ini < f2 and fin > i2 for i2, f2 in ocupado):
            continue
        if any(o is x for x in out):
            continue
        ocupado.append((ini, fin))
        out.append(o)
    return out


# ── Celdas que el lector posicional deja a medias ─────────────────────────────
# La parrilla se lee por coordenadas porque el texto plano aplasta las columnas.
# El precio: cuando el título de una celda pasa a una línea que cae fuera de la
# banda de su sede, esa línea se descarta y la celda queda cortada. Se ve a ojo
# cuando queda un «+» colgando, pero NO siempre deja rastro.
#
# Lo destapó el cruce contra el texto plano del mismo PDF, que sí trae la línea
# perdida. Cada corrección se justifica sola con la aritmética del festival, y
# NINGUNA inventa una obra: todas ya estaban en nuestro catálogo, huérfanas.
#
# Cuando el lector posicional aprenda a arrastrar la cola de la celda, esta
# tabla debe quedar VACÍA — no es un parche permanente, es una deuda anotada.
#
# La clave lleva SEDE, no solo día y hora: el 5 SEP a las 18:00 corren dos
# funciones en sedes distintas, y una clave sin sede pisaba las dos.
CELDAS_TRUNCADAS = {
    # pág. 3 y 9. El PDF en texto plano dice «Programa 1 Cuartito rosa +
    # Caminito al Cielo». Publicábamos la función como si fuera solo «Cuartito
    # rosa» (30'), y la duración declarada de la celda son 67' = 30' + 37',
    # que es justo lo que dura «Caminito al Cielo» en nuestro catálogo.
    ('2026-09-04', '16:00', 'Biblioteca Comfama Bello Centro Bello'): 'Retrospectiva Sergio Navarro Programa 1 Cuartito rosa + Caminito al Cielo',
    ('2026-09-08', '20:00', 'Antimateria Libros y Café Medellín'): 'Retrospectiva Sergio Navarro Programa 1 Cuartito rosa + Caminito al Cielo',
    # pág. 4. Cortado a media palabra: «Vampir Cuadec». Por eso el cruce
    # reconocía dos obras y no tres. La hoja oficial del propio festival
    # describe la función como «La tempestá, No contéis con los dedos y
    # Vampir Cuadecuc y diálogo posterior».
    ('2026-09-05', '18:00', 'Teatro Caribe Itagüí'): ('La tempestá + No contéis con los dedos + Vampir Cuadecuc '
                              'Pere Portabella + Conversaciones Cinemancia: '
                              '“Legado inmarcesible”. Participan Julio Lamaña y Juan Pablo Franky'),
}


# ── Actividades que NO son proyecciones ───────────────────────────────────────
# Se publicaban como type:'film' sin event_kind, así que la app les exigía
# póster y las trataba como obras. Son foros, seminarios, un debate, un
# encuentro y una charla. La palabra es la del festival, verbatim.
#
# OJO con lo que NO está aquí: los focos de Luciana Decker y el programa de
# Rajendra Gour SÍ son proyecciones —les falta el contenido, que es otra
# deuda—, y la charla de Koresky y Miccio a las 19:30 es un diálogo aparte de
# la proyección de «The Children's Hour», que tiene su propia función a las
# 17:30. Confundirlos habría borrado cuatro proyecciones del festival.
KIND = (
    (re.compile(r'^Foro de la Cr[íi]tica', re.I),           'foro'),
    # ANCLADO al inicio: sin ancla, «…Fuera de competencia Programa 2 Teoremas
    # sobre la mirada + Debate: Riesgos estéticos» —que es una PROYECCIÓN con
    # debate posterior— quedaba marcada como evento y desaparecía del catálogo.
    (re.compile(r'^Debate\b', re.I),                        'debate'),
    (re.compile(r'^Seminario de la imagen', re.I),          'seminario'),
    (re.compile(r'^Encuentro Internacional', re.I),         'encuentro'),
    (re.compile(r'^Michael Koresky y Jos[ée] Miccio', re.I), 'charla'),
)


def kind_de(titulo):
    for rx, k in KIND:
        if rx.search(titulo or ''): return k
    return None


def main():
    par = json.load(open(f'{S}/cinemancia-2026-programacion-oficial.json', encoding='utf-8'))['funciones']
    reparadas = 0
    for _f in par:
        _fix = CELDAS_TRUNCADAS.get((_f['dia'], _f['hora'], _f['sede']))
        if _fix and _fix != _f['titulo_crudo']:
            _f['titulo_crudo'] = _fix
            _f['_celda_reparada'] = 'cola de celda que el lector posicional descartó; recuperada del texto plano del MISMO PDF'
            reparadas += 1
    print(f'celdas truncadas reparadas: {reparadas}')
    of = json.load(open(f'{S}/cinemancia-2026-programas-oficial.json', encoding='utf-8'))
    cat = catalogo()

    # El índice lleva SEDE, no solo día y hora. Dos funciones distintas pueden
    # coincidir en horario en sedes distintas: el sábado 5 a las 18:00 corren a
    # la vez la Retrospectiva Navarro y el pase de Pere Portabella, y sin la
    # sede la charla de Portabella se pegaba a las dos.
    # Se agrupa por día y hora, y la sede desempata por CONTENCIÓN de prefijo:
    # la hoja escribe «Teatro Caribe» y la parrilla «Teatro Caribe Itagüí», así
    # que un corte fijo de N caracteres los separaba. Con una sola candidata en
    # ese horario no hace falta desempatar.
    def mete(d, k, v): d.setdefault((k['dia'], k['hora']), []).append((clave(k['sede']), v))
    pases, charlas = {}, {}
    for p in of['programas']:
        for x in p['pases']: mete(pases, x, p)
    for c in of['charlas']: mete(charlas, c, c)

    def busca(idx, f):
        cand = idx.get((f['dia'], f['hora']))
        if not cand: return None
        # La sede SIEMPRE tiene que coincidir. El atajo «si solo hay una
        # candidata, dásela» pegaba la misma charla a las dos funciones que
        # corren a esa hora en sedes distintas.
        cs = clave(f['sede'])
        for sede, v in cand:
            if cs.startswith(sede[:12]) or sede.startswith(cs[:12]): return v
        return None

    otros = otros_programas()
    programas, sin_obra = [], []
    for f in par:
        e = {'dia': f['dia'], 'hora': f['hora'], 'sede': f['sede'],
             '_src': 'PDF oficial de programación del festival'}
        if f.get('duracion_min'): e['duracion_min'] = f['duracion_min']
        if f.get('_hora_inferida'): e['_hora_inferida'] = True
        titulo_crudo = sin_nota_de_inscripcion(f['titulo_crudo'])
        e['acceso'] = acceso_de(f['sede'], titulo_crudo)

        p = busca(pases, f)
        ch = busca(charlas, f)          # un programa TAMBIÉN puede llevar debate
        if p:
            # PROGRAMA: las obras las manda la hoja del festival, en su orden.
            e['titulo'] = p['programa']
            e['obras'] = []
            for o in p['obras']:
                base = cat.get(clave(o['titulo']))
                d = obra_de(base) if base else {}
                d.update({k: v for k, v in o.items() if v not in (None, '')})
                e['obras'].append(d)
            e['_src'] = 'hoja oficial del festival (orden de programas)'
            if ch:
                e['_charla'] = {'descripcion': ch['descripcion'], 'invitados': ch['invitados']}
        else:
            # Función simple: la obra sale del catálogo por el título crudo.
            halladas = obras_en(titulo_crudo, cat)
            hallada = halladas[0] if halladas else None
            # Un PROGRAMA DOBLE se titula con las dos, unidas por «+», que es
            # como lo escribe el festival en su parrilla. Ponerle el nombre de
            # la primera escondía la segunda: quien leía «La corazonada» no
            # tenía manera de saber que también se proyecta «Cairo Streets».
            if ch:
                e['titulo'] = ch['titulo']
            elif len(halladas) > 1:
                # Si la celda ARRANCA con el nombre de un programa del festival
                # («Retrospectiva Sergio Navarro Programa 1 Cuartito rosa +
                # Caminito al Cielo»), ese nombre manda: es como el festival la
                # anuncia, y su hermana «…Programa 2» ya se publica así porque
                # viene de la hoja oficial. Titularla «A + B» las dejaba como si
                # fueran cosas distintas.
                _prog = re.match(r'^(.*?\bPrograma\s*\d)\b', titulo_crudo, re.I)
                e['titulo'] = (_prog.group(1).strip() if _prog
                               else ' + '.join(o['title'] for o in halladas))
            elif hallada:
                e['titulo'] = hallada['title']
            else:
                e['titulo'] = titulo_crudo
            e['obras'] = [obra_de(o) for o in halladas]
            if not hallada: sin_obra.append(f)
            if ch:
                e['_charla'] = {'descripcion': ch['descripcion'], 'invitados': ch['invitados']}
                e['_src'] = 'hoja oficial del festival (conversatorios y charlas)'
        # La sección es de la FUNCIÓN, no solo de la obra: el ensamblador la
        # lee de f['seccion']. En un programa, todas sus obras comparten
        # sección; en una función simple, es la de su única obra.
        secs = [o.get('seccion') for o in e['obras'] if o.get('seccion')]
        if secs:
            e['seccion'] = max(set(secs), key=secs.count)
        for o in e['obras']: o.pop('seccion', None)
        # Los cuatro programas que el festival envió aparte: su contenido manda
        # sobre lo que dedujo el cruce, y su nombre sobre el de la parrilla.
        _op = OTROS_PROGRAMAS.get((f['dia'], f['hora'], f['sede']))
        if _op and otros.get(_op):
            e['titulo'] = _op
            # Las obras vienen de la hoja del festival, que manda en el ORDEN y
            # en los datos que trae. Pero hay que pasarlas por el catálogo o se
            # quedan sin afiche ni sinopsis: la hoja no los lleva. Gana la hoja
            # campo a campo; el catálogo solo rellena lo que ella no dice.
            e['obras'] = []
            for _o in otros[_op]:
                # La hoja del festival y el catálogo no siempre escriben igual
                # el mismo título: «Sight and desire (eyes)» contra «Sight and
                # Desire». Si no casa, se reintenta sin el paréntesis final —
                # sin él, esa obra se quedaba sin afiche teniéndolo el catálogo.
                _base = (cat.get(clave(_o['title']))
                         or cat.get(clave(re.sub(r'\s*\([^)]*\)\s*$', '', _o['title']))))
                _d = obra_de(_base) if _base else {}
                _d.update({k: v for k, v in _o.items() if v not in (None, '')})
                e['obras'].append(_d)
            e['is_cortos'] = True
            e['_src'] = 'hoja «Otros programas» que envió el festival (orden de proyección)'

        _k2 = (f['dia'], f['hora'], f['sede'])
        if _k2 in DURACION_CORREGIDA:
            e['duracion_min'] = DURACION_CORREGIDA[_k2]
            e['_duracion_src'] = 'confirmada por el festival (21 AGO)'
        for _extra in OBRAS_AÑADIDAS.get(_k2, []):
            if not any((o.get('title') or o.get('titulo')) == _extra['title'] for o in e.get('obras') or []):
                e.setdefault('obras', []).append(dict(_extra))
                e['_obras_src'] = 'obra que faltaba, enviada por el festival (21 AGO)'

        # El kind se decide sobre el título FINAL: el de «Michael Koresky y José
        # Miccio» lo pone la hoja de charlas, no la celda de la parrilla.
        # Y NUNCA sobre algo que ya trae obras: una proyección con debate
        # posterior sigue siendo una proyección.
        # Se miran las DOS formas del nombre: el título final —que para la
        # charla de Koresky y Miccio lo pone la hoja de charlas— y la celda
        # cruda, que es donde el debate se anuncia como «Debate “Todos los
        # planos del mundo”…». La guarda de «sin obras» es la que evita el
        # falso positivo: una proyección con debate posterior tiene obras y
        # sigue siendo proyección.
        if not e.get('obras'):
            _k = kind_de(e.get('titulo')) or kind_de(titulo_crudo)
            if _k: e['event_kind'] = _k
            # Una actividad sin obras no tiene de dónde sacar sinopsis: el
            # catálogo describe películas, no foros. Pero la hoja del festival
            # SÍ describe sus conversatorios, y esa descripción es la sinopsis
            # de la actividad. Sin esto, la ficha de un debate salía vacía.
            if _k and ch and ch.get('descripcion') and not e.get('sinopsis'):
                e['sinopsis'] = ch['descripcion']
                e['_sinopsis_src'] = 'hoja oficial del festival (conversatorios y charlas)'
        programas.append(e)

    # Un programa que se repite se anuncia dos veces, y la parrilla solo lista
    # su contenido en UNO de los pases: «Retrospectiva Sergio Navarro Programa
    # 2» sale vacío el sábado 5 y con sus dos títulos el jueves 10, ambos con
    # 87'. Mismo nombre de programa y misma duración = mismo programa, y las
    # obras del pase que sí las trae valen para el otro.
    porprog = {}
    for e, f in zip(programas, par):
        nom = sin_nota_de_inscripcion(f['titulo_crudo'])
        m = re.match(r'^(.*?\bPrograma\s*\d)\b', nom, re.I)
        if not m or not e['obras']: continue
        porprog.setdefault((clave(m.group(1)), e.get('duracion_min')), e['obras'])
    heredadas = 0
    for e, f in zip(programas, par):
        if e['obras']: continue
        nom = sin_nota_de_inscripcion(f['titulo_crudo'])
        m = re.match(r'^(.*?\bPrograma\s*\d)\b', nom, re.I)
        if not m: continue
        src = porprog.get((clave(m.group(1)), e.get('duracion_min')))
        if src:
            e['obras'] = [dict(o) for o in src]
            e['_obras_src'] = 'contenido tomado del otro pase del MISMO programa (mismo nombre y misma duración)'
            heredadas += 1
    print(f'programas que heredan su contenido del otro pase: {heredadas}')

    out = {'_provenance': {
        'fuente': 'PDF oficial de programación + hoja de programas y charlas enviada por el festival',
        'capturado': '2026-08-20',
        'metodo': 'la parrilla da cuándo y dónde; la hoja da qué obras van en cada programa',
        'nota': 'el barrido anterior sacaba el horario de la ficha de cada película: salían 89 funciones sueltas en vez de programas, sin la inauguración ni la clausura'},
        '_funciones': len(programas), 'programas': programas}
    json.dump(out, open(f'{S}/cinemancia-2026-crudo.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'{len(programas)} funciones · {sum(len(p["obras"]) for p in programas)} obras')
    print(f'funciones sin obra identificada: {len(sin_obra)}')
    for f in sin_obra[:30]: print(f'   {f["dia"]} {f["hora"]} · {f["titulo_crudo"][:62]}')

if __name__ == '__main__':
    main()
