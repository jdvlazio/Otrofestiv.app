# -*- coding: utf-8 -*-
"""El crudo de QAFF 2026 en Bogotá, armado desde el PDF OFICIAL del programa.

    quibdoafricafilmfestival.com/es/program-2026  ·  prog2.pdf  ·  86 páginas

Por qué el PDF y no el flip book: el PDF tiene CAPA DE TEXTO. No es OCR, así que
no puede tener errores de lectura —o el festival lo escribió así, o no está—.
Dos cosechas por OCR del flip book no lograron sacar las sinopsis en español sin
pegarle a una obra el texto de la de al lado; aquí eso no puede pasar.

El PDF trae la misma información DOS VECES y por eso se puede auditar solo:

  1. la PARRILLA de cada sede: sede, día, hora, sala y, junto a cada obra,
     «(Director) - 12'44 - País»;
  2. la FICHA de cada obra: país, año, duración, tipo, idioma y sinopsis.

Las dos se cruzan aquí y las 13 diferencias que aparecieron están resueltas o
declaradas una por una (ver DISCREPANCIAS). Encima de eso, la transcripción de
la parrilla se verifica contra la página que declara (scratchpad/qaff/verifica.py)
y coincide con dos auditorías independientes del flip book en las 29 funciones y
en 28 de las 29 listas de obra.

Quibdó quedó CANCELADO por el terremoto: todo es en Bogotá. El prelanzamiento
del 5 SEP en el Museo Nacional NO se incluye.
"""
import json, os, re, sys, unicodedata, datetime, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ENTRADA LIBRE, y nada más. El director dijo por correo que el acceso es
# gratuito con inscripcion previa, pero el formulario NO existe en ninguna parte:
# ni en el PDF, ni en la pagina del programa —el widget de Boom desaparecio y
# ahora hay un flipbook—, ni en su web. Decirle a alguien que TIENE que
# inscribirse sin poder decirle donde es peor que no decirlo: le inventa un
# tramite y lo deja sin salida. Decision de Juan, 4 sep 2026.
#
# Si publican el formulario: volver a «Entrada libre con inscripcion previa» y
# pasar su URL como ticket_url — lib.acceso_campos hace el resto.
SCR  = os.path.join(BASE, 'pipeline', 'qaff_pdf')
sys.path.insert(0, SCR)
import programa as pr                                        # noqa: E402
from parrilla import presencias                              # noqa: E402

SALIDA = os.path.join(BASE, 'festivals', 'staging', 'qaff-2026-bogota-crudo.json')


def n(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())


# El propio PDF publica algunas obras con su título en español y otras con el
# original: la ficha de «AISHA CAN'T FLY AWAY» es la de «AISHA NO PUEDE VOLAR
# LEJOS», y la de «ONE SUNDAY» la de «UN DOMINGO». El puente sale del PDF —de
# la ficha bilingüe de MI VICHE TODO EL DÍA / MY DAILY VICHE hacia abajo—, no
# de una conjetura nuestra.
PUENTE = {
 'AISHA NO PUEDE VOLAR LEJOS': "AISHA CAN'T FLY AWAY",
 'UN DOMINGO': 'ONE SUNDAY',
 'MI VICHE TODO EL DIA': 'MI VICHE TODO EL DÍA MY DAILY VICHE',
 'SISTERS IN DESTINY: ANGELA DAVIS & GERTY ARCHIMEDE': 'ANGELA DAVIS & ARCHIMÈDE GERTY',
 'HERMANAS EN EL DESTINO - ANGELA & GERTY ARCHIMÈDE': 'ANGELA DAVIS & ARCHIMÈDE GERTY',
 'UN REY DESPLAZADO': 'A KING DISPLACED',
 'AMAZONAS COCINAS INDIGENAS DE SELVA Y RIO': 'AMAZONAS COCINAS INDÍGENAS DE SELVA Y RÍO',
 'AMAZONAS COCINAS INDÍGENAS': 'AMAZONAS COCINAS INDÍGENAS DE SELVA Y RÍO',
 'SOÑÉ SU NOMBRE': 'SOÑE SU NOMBRE',
 'CAIDA LIBRE': 'CAÍDA LIBRE',
 'CAFE ?': 'CAFÉ ?',
}

# Las 13 diferencias entre la parrilla y la ficha del MISMO PDF. Diez son de
# idioma o grafía y se normalizan al español; tres eran de fondo:
#   · «La obra de Dios» 122' (ficha) vs 126' (parrilla) → TMDB dice 126: manda
#     la parrilla, la ficha se equivocó.
#   · «Relatos de la Guajirita» país Nigeria (ficha) vs Colombia (parrilla) → la
#     propia sinopsis de la ficha habla de Becerril, Cesar: manda la parrilla.
#   · «Un domingo» 12' (ficha) vs 20' (parrilla) → TMDB (1742409, «Domingo»,
#     mismo director) dice 20': manda la parrilla. Las TRES discrepancias de
#     fondo quedaron resueltas por una tercera fuente, ninguna por criterio
#     nuestro.
PAIS_ES = {'brazil': 'Brasil', 'united states': 'Estados Unidos',
           'guyana frances': 'Guayana Francesa', 'colomnbia': 'Colombia',
           'egypt': 'Egipto', 'lebanon': 'Líbano', 'south africa': 'Sudáfrica',
           'cameroon': 'Camerún', 'france': 'Francia'}
DISCREPANCIAS = {
 'LA OBRA DE DIOS': "la ficha del programa dice 122' y la parrilla 126'; TMDB confirma 126",
 'RELATOS DE LA GUAJIRITA': 'la ficha del programa imprime «Nigeria» como país, pero su propia '
                            'sinopsis sitúa la obra en Becerril, Cesar: es Colombia',
 'UN DOMINGO': "la ficha del programa dice 12' y la parrilla 20'; TMDB confirma 20'",
}
# Obras cuya FICHA está en la sección de una sede que no publicó parrilla. El
# festival las ubicó ahí: son su programación en esa sede, sin hora impresa.
SIN_HORA = {
 'Museo Nacional de Colombia': ['POSESAS', 'LA TINAJA', 'WATERFRONT MEMORIES', 'MANMAN CHADWON'],
 'Universidad Nacional de Colombia': ['KANEKALON', 'AMELIA', 'ONE SUNDAY'],
}

MINUS = {'de','del','la','las','el','los','y','a','en','un','una','al','con','por',
         'the','of','and','to','in','on','for','a',
         'e','o','da','do','das','dos','du','le','les','ni'}


def titulo_casa(t):
    """VERSALES → capital normal. El programa imprime TODO en mayúsculas; la app
    no. Si el título ya viene mixto (marcas, siglas), no se toca."""
    if not t or t != t.upper():
        return t
    out = []
    for i, p in enumerate(t.split()):
        b = p.lower()
        out.append(p if len(p) <= 2 and p.isupper() and not p.isalpha()
                   else (b if i and b in MINUS else b.capitalize()))
    return ' '.join(out)


# El festival imprime el mismo título de dos formas y ninguna de las dos fuentes
# gana siempre: la parrilla escribe «SOÑÉ SU NOMBRE» y su ficha «SOÑE SU NOMBRE»;
# con «CAIDA LIBRE» pasa al revés. La regla no puede ser «manda la ficha»: manda
# LA VARIANTE ACENTUADA, porque la tilde es información y su ausencia es una
# errata de imprenta. Las dos son del festival, así que no inventamos nada.
TITULO_ES = {
 # título bilingüe en una sola ficha: nos quedamos con el español y el original
 # viaja aparte, no pegado al nombre de la obra
 'MI VICHE TODO EL DIA': 'MI VICHE TODO EL DÍA',
 # el programa la imprime corta en Cinemateca y larga en Javeriana; es LA MISMA
 # obra (Jairo Garrido, 13', Colombia). Dos títulos para una obra rompen la
 # identidad: quien la marca en una función no la reconoce en la otra.
 'AMAZONAS COCINAS INDÍGENAS': 'AMAZONAS COCINAS INDÍGENAS DE SELVA Y RÍO',
 'AMAZONAS COCINAS INDIGENAS DE SELVA Y RIO': 'AMAZONAS COCINAS INDÍGENAS DE SELVA Y RÍO',
 # dos obras que el programa titula en inglés en Alianza Francesa y en español en
 # Cinemateca. Mismo director, misma duración, misma obra. El catálogo de Bogotá
 # va en español; el título original viaja en `titulo_original`.
 'A KING DISPLACED': 'UN REY DESPLAZADO',
 # Igual que las anteriores: la Cinemateca la programa «UN DOMINGO» el 19 y la
 # Universidad Nacional «ONE SUNDAY» el 22. Misma obra (Day Sena, 20', Brasil).
 # Sin unificar salían como dos obras con la MISMA sinopsis, que es lo que el
 # guardián [sinopsis-duplicada] llama cross-contaminación — y en pantalla
 # parecerían dos películas distintas que cuentan lo mismo.
 'ONE SUNDAY': 'UN DOMINGO',
 'SISTERS IN DESTINY: ANGELA DAVIS & GERTY ARCHIMEDE':
     'HERMANAS EN EL DESTINO - ANGELA & GERTY ARCHIMÈDE',
}
ORIGINAL = {'UN REY DESPLAZADO': 'A King Displaced',
            'HERMANAS EN EL DESTINO - ANGELA & GERTY ARCHIMÈDE':
                'Sisters in Destiny: Angela Davis & Gerty Archimede',
            'MI VICHE TODO EL DIA': 'My Daily Viche'}


def _tildes(s):
    return sum(1 for c in (s or '') if unicodedata.combining(
        unicodedata.normalize('NFD', c)[-1]) or c in 'ñÑçÇ')


def titulo_obra(titulo, fichas):
    if titulo in TITULO_ES:
        return titulo_casa(TITULO_ES[titulo])
    f = fichas.get(n(titulo)) or fichas.get(n(PUENTE.get(titulo, ''))) or {}
    otra = f.get('titulo')
    if otra and n(otra) == n(titulo) and _tildes(otra) > _tildes(titulo):
        titulo = otra
    return titulo_casa(titulo)


# El «Tipo de Proyecto» de la ficha mezcla FORMATO y GÉNERO en una sola frase:
# «Cortometraje de Ficción», «Largometraje Documental». El formato ya lo dice la
# duración; lo que la app muestra en la ficha es el GÉNERO, y lo traduce al
# inglés con _GENRE_EN, que espera la forma en español —la canónica del repo—.
# Así que el género sale del propio festival, no de TMDB: nadie clasifica su
# programa mejor que quien lo programó.
FORMATO = {'cortometraje', 'largometraje', 'mediometraje', 'corto', 'largo', 'de', 'estudiante'}

# El vocabulario de género de la app (_GENRE_EN, sheets-controller.js) más
# «Ficción», que no está en el mapa pero lleva 110 obras en el repo. El guardián
# [genero-unico] exige UNO: «Doc-Drama, Experimental» no es un género compuesto,
# es una descripción, y la app la pintaría entera en la ficha.
GENEROS = {'accion', 'aventura', 'comedia', 'drama', 'documental', 'experimental',
           'romance', 'satira', 'terror', 'thriller', 'animacion', 'cienciaficcion',
           'fantasia', 'misterio', 'musical', 'musica', 'crimen', 'historia',
           'suspense', 'belica', 'familia', 'western', 'ficcion'}


def _genero(tipo):
    for trozo in re.split(r'[,/]| y ', tipo or ''):
        palabras = [w for w in trozo.split() if n(w) not in FORMATO]
        g = ' '.join(palabras).strip()
        if g and n(g) in GENEROS:
            return g
    return None


def sin_emoji(sec):
    """«🌊 Fronteras Latam» → «Fronteras Latam», y «Fronteras Latam» → igual.

    Quitar «el primer token» a ciegas funciona hasta que la sección llega SIN
    emoji —y llega: el festival publicado guarda la sección con emoji en la
    función y sin él en la obra—. Ahí «Fronteras Latam» se convertía en «Latam»,
    que no existe en el mapa, y el ensamblador paraba. Se quita solo lo que no
    es letra ni dígito."""
    return re.sub(r'^[^\w]+\s*', '', sec or '', flags=re.UNICODE).strip()


def _pais(p):
    if not p:
        return None
    p = p.strip()
    return PAIS_ES.get(p.lower(), p)


def cargar():
    fichas = json.load(open(os.path.join(BASE, 'festivals', 'staging',
                        'qaff-2026-bogota-fichas.json'), encoding='utf-8'))['obras']
    idx = {}
    for f in fichas:                       # entre copias, la más completa
        k = n(f['titulo'])
        if k not in idx or sum(1 for v in f.values() if v) > sum(1 for v in idx[k].values() if v):
            idx[k] = f
    cred = json.load(open(os.path.join(BASE, 'festivals', 'staging',
                      'qaff-2026-bogota-creditos-parrilla.json'), encoding='utf-8'))['obras']
    return idx, cred


def obra(titulo, fichas, cred):
    """Una obra = lo que dicen las dos fuentes del PDF, con la parrilla mandando
    en lo que ella programó (país y duración de la franja) y la ficha aportando
    lo que solo ella tiene (sinopsis, año, tipo, idioma)."""
    f = fichas.get(n(titulo)) or fichas.get(n(PUENTE.get(titulo, ''))) or {}
    c = (cred.get(titulo) or [{}])[0]
    o = {'titulo': titulo_obra(titulo, fichas)}
    o['director'] = c.get('director') or f.get('director') or None
    o['duracion_min'] = c.get('duracion_min') or f.get('duracion_min')
    o['pais'] = _pais(c.get('pais')) or _pais(c.get('pais_cola')) or _pais(f.get('pais'))
    if c.get('anio'):
        o['anio'] = c['anio']
    if c.get('tipo'):
        o['tipo'] = c['tipo']
    for k_src, k_dst in (('anio','anio'), ('tipo','tipo'), ('idioma','idioma')):
        if f.get(k_src):
            o[k_dst] = f[k_src]
    g = _genero(o.get('tipo') or (c.get('tipo') if c else None))
    if g:
        o['genre'] = g
    if f.get('sinopsis'):
        o['sinopsis'] = f['sinopsis']
        o['synopsis_lang'] = 'es'
    orig = ORIGINAL.get(TITULO_ES.get(titulo, titulo)) or ORIGINAL.get(titulo)
    if not orig and f.get('titulo') and n(f['titulo']) != n(TITULO_ES.get(titulo, titulo)):
        orig = titulo_casa(f['titulo'])
    if orig:
        # `title_en` es lo que la app muestra como título principal cuando está en
        # inglés (sheets-controller.js:1544) y lo que usa para buscar. Los cinco
        # originales que trae este programa son ingleses; si algún día uno no lo
        # fuera, iría a `titulo_original` y NO aquí.
        o['titulo_original'] = orig
        o['title_en'] = orig
    o['_obra_src'] = ('ficha y parrilla del PDF oficial del programa (capa de texto, no OCR)'
                      if f else 'parrilla del PDF oficial del programa')
    if titulo in DISCREPANCIAS:
        o['_ojo'] = DISCREPANCIAS[titulo]
    return {k: v for k, v in o.items() if v not in (None, '', [], {})}


def _canon_seccion():
    """El festival escribe sus categorías en MAYÚSCULAS («PANORAMA COLOMBIANO»)
    y el plan las declara con su grafía de publicación («Panorama Colombiano»).
    Es la MISMA sección: se canoniza a la del plan, que es la que lleva emoji,
    arquetipo y traducción. Lo que no esté declarado se deja tal cual, para que
    el ensamblador lo cante en vez de inventarle una."""
    pl = os.path.join(BASE, 'pipeline', 'qaff-2026.plan.json')
    if not os.path.exists(pl):
        return {}
    dec = json.load(open(pl, encoding='utf-8'))['festival']['secciones']
    out = {n(k): k for k in dec}
    # El festival escribe «PRISMA FEMININO» (con i) en su calendario y en su web.
    # Ya publicamos Quibdó con «Prisma Femenino», que es la grafía correcta y la
    # que lleva emoji y traducción; dos grafías de la misma sección parten la
    # sección en dos en la app.
    out.setdefault('prismafeminino', 'Prisma Femenino')
    # El calendario dice «FUERA DE COMPETICION»; la propia web del festival
    # titula esa página «MIRADAS ESPECIALES», que es el nombre publicable.
    out.setdefault('fueradecompeticion', 'Miradas Especiales')
    return out


def del_calendario():
    """La SEGUNDA fuente de secciones, y la que de verdad manda: el calendario
    oficial del festival, con sus 15 categorías propias.

    Estaba capturado desde el 2 de agosto y no se consultaba. El cruce miraba
    solo el build de Quibdó, que lleva los títulos en ESPAÑOL, y el calendario
    los lleva en ORIGINAL: «Los Chicos del Banjo» nunca iba a encontrar a «THE
    BANJO BOYS». Por eso 26 de 44 programas salían sin sección y dábamos por
    ausente algo que el festival sí había publicado. El fallo no fue de lectura
    —eso lo vigilan verifica.py y cobertura.py— sino de CRUCE, que no lo miraba
    nadie: se buscó en una fuente por una clave que esa fuente no usa.

    Devuelve {clave normalizada → categoría}. La categoría dueña es la PRIMERA
    del evento (decisión de Juan, 2 ago): varias obras traen dos o tres."""
    p = os.path.join(BASE, 'festivals', 'staging', 'qaff-2026-programacion-raw.json')
    if not os.path.exists(p):
        return {}
    raw = json.load(open(p, encoding='utf-8'))
    out = {}
    for e in raw.get('events', []):
        if not str(e.get('start', '')).startswith('2026-09'):
            continue
        cats = [c['name'] for c in (e.get('categories') or []) if c.get('name')]
        t = (e.get('title') or '').strip()
        if not t or not cats:
            continue
        # «GOD'S WORK (Copy)» es la segunda función de la misma obra, no otra obra
        t = re.sub(r'\s*\(copy\)\s*$', '', t, flags=re.I)
        out.setdefault(n(t), cats[0])
    return out


# Títulos que el PDF de Bogotá castellaniza y el calendario NO. Cada uno se
# comprobó contra la selección oficial del sitio, no se adivinó.
PUENTE_SECCION = {
    'Los Chicos del Banjo': 'THE BANJO BOYS',
    'El Anclaje del Tiempo': 'THE ANCHORAGE OF THE TIME',
    'Sobreviviendo a Biafra': 'SURVIVING BIAFRA',
    'Tres Hombres Negros': 'THREE BLACK MEN',
    'De Barro y Sangre': 'OF MUD AND BLOOD',
    'La Obra de Dios': "GOD'S WORK",
    'Los Viajeros': 'THE TRAVELERS',
    'Iniciación en la Octava Dimensión': 'INITIATION INTO THE EIGHTH DIMENSION',
    'Generación Equivocada': 'WRONG GENERATION',
    'Día del Padre': "FATHER'S DAY",
    'El Coach de los Locos': 'THE MADMEN COACH',
    'Performance Artistica e Musical': 'MUESTRA ARTISTICA',
    'Avenida Fishkill 305': '305 FISHKILL AVENUE',
    # En la selección oficial del sitio va marcada «(out of competition)», que es
    # una sección del festival, no una nota.
}

# Sección que NO sale de cruzar nada, sino de lo que el propio festival IMPRIME.
# Va aparte del puente para que se vea de dónde viene cada una.
SECCION_DIRECTA = {
    # La selección oficial de su web la marca «(out of competition)».
    'hyphen': ('FUERA DE COMPETICION', 'marcada «(out of competition)» en la '
               'selección oficial del sitio del festival'),
    # La ÚNICA que no estaba publicada en ninguna parte: ni en el calendario, ni
    # en /catalog, ni en las páginas de sección. La respondió el festival por
    # correo el 4 sep 2026: «Orango lo encontrará en la sección África
    # Panorama». Es su nombre; se canoniza a «Panorama Africano», que es como la
    # titula su propia web y como ya la publicamos.
    'orango': ('PANORAMA AFRICANO', 'respuesta del festival por correo, 4 sep 2026 '
               '(Wilfrid Massamba): «Orango lo encontrará en la sección África Panorama»'),
}
_PUENTE_N = None


def del_chocho():
    """La SECCIÓN no está en el programa de Bogotá: no la imprime ni la parrilla
    ni la ficha, en ninguna de las 86 páginas. Pero es el MISMO festival y
    muchas de estas obras ya venían de la selección oficial del Chocó, que sí
    las clasificó y que ya publicamos. Heredarla de ahí no es adivinar: es
    nuestro propio onboarding de agosto. Va marcada como heredada, para que se
    vea que Bogotá no la imprimió —y para que el festival pueda desmentirla."""
    # el QAFF publicado de Quibdó, tal como está en el repo: no se copia a staging,
    # porque una copia se queda vieja y nadie se entera
    p = os.path.join(BASE, 'festivals', 'qaff-2026.json')
    if not os.path.exists(p):
        return {}
    pub = json.load(open(p, encoding='utf-8'))
    out = {}

    def guarda(t, o, sec):
        if not t:
            return
        d = out.setdefault(n(t), {})
        if sec:
            d.setdefault('section', sec)
        for k in ('poster', 'posterSource', 'lbSlug', 'tmdb_id', 'synopsis_en',
                  'title_en', 'genre'):
            if o.get(k):
                d.setdefault(k, o[k])

    for f in pub.get('films', []):
        guarda(f.get('title'), f, f.get('section'))
        for i in (f.get('film_list') or []):
            guarda(i.get('title'), i, f.get('section'))
    return out


def main():
    fichas, cred = cargar()
    choco = del_chocho()
    calen = del_calendario()
    canon = _canon_seccion()
    fuente_sec = collections.Counter()
    _cn = lambda x: canon.get(n(x), x)
    sin_cruce = []
    # El Q&A no se escribe a mano: se lee del PDF. «con la presencia de la
    # directora» va pegada a UNA obra, y el extractor exige que cada marca caiga
    # en una sola función. Si el festival mueve una obra de franja, esto deja de
    # resolver y avisa, en vez de arrastrar un dato viejo.
    qa, huerfanas = presencias()
    assert not huerfanas, f'marcas de invitado sin función única: {huerfanas}'
    funciones = []
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        obs = [obra(t, fichas, cred) for t in obras]
        for o, t in zip(obs, obras):
            h = (choco.get(n(o['titulo'])) or choco.get(n(t))
                 or choco.get(n(o.get('titulo_original') or '')) or {})
            # 1º el calendario oficial (la categoría que declara el FESTIVAL),
            # 2º la selección del Chocó que ya publicamos. El calendario manda:
            # es su dato, no nuestra herencia.
            global _PUENTE_N
            if _PUENTE_N is None:
                _PUENTE_N = {n(k): v for k, v in PUENTE_SECCION.items()}
            _dir = SECCION_DIRECTA.get(n(t)) or SECCION_DIRECTA.get(n(o['titulo']))
            _cat = (calen.get(n(_PUENTE_N.get(n(t)) or ''))
                    or calen.get(n(o['titulo'])) or calen.get(n(t))
                    or calen.get(n(o.get('titulo_original') or ''))
                    or calen.get(n(o.get('title_en') or '')))
            if _dir:
                o['_seccion'] = _cn(sin_emoji(_dir[0]))
                o['_section_src'] = _dir[1]
                fuente_sec['sitio del festival'] += 1
            elif _cat:
                o['_seccion'] = _cn(sin_emoji(_cat))
                o['_section_src'] = ('categoría del calendario oficial del festival '
                                     '(qaff-2026-programacion-raw.json, 2 ago)')
                fuente_sec['calendario oficial'] += 1
            elif h.get('section'):
                # Clave INTERNA: solo sirve para votar la sección de la función.
                # Publicada en la obra, el festival acaba con dos strings para la
                # misma sección —«🛶 Panorama Colombiano» en la función y
                # «Panorama Colombiano» en la obra— y el guardián de arquetipo
                # no reconoce la segunda: color gris ilegible.
                o['_seccion'] = sin_emoji(h['section'])
                fuente_sec['herencia del Chocó'] += 1
                o['_section_src'] = ('heredada de la selección oficial del Chocó ya publicada; '
                                     'el programa de Bogotá no imprime secciones')
            # El PÓSTER y el identificador de TMDB también son nuestros, de agosto.
            # El PDF manda en lo que el PDF dice (sinopsis, país, año, duración);
            # esto solo rellena lo que el papel no puede traer.
            for k in ('poster', 'posterSource', 'lbSlug', 'tmdb_id', 'synopsis_en',
                      'title_en', 'genre'):
                if h.get(k) and not o.get(k):
                    o[k] = h[k]
            if h.get('poster'):
                o['_poster_src'] = 'heredado del onboarding de QAFF Quibdó (agosto 2026)'
        nombre, sinopsis = pr.BLOQUES.get((sede, dia, hora), (None, None))
        # El ensamblador toma la SALA de la tabla del plan, no de `f['sala']`
        # (ensamblar.py:123). Una sala puesta suelta en el crudo se pierde sin
        # avisar, y la Cinemateca usa tres salas distintas. Por eso la clave de
        # sede lleva la sala dentro y el plan la desdobla: es la tabla explícita
        # que el contrato pide, no una heurística sobre el guion.
        f = {'dia': f'2026-09-{int(dia):02d}', 'hora': hora,
             'sede': f'{sede} · {sala}' if sala else sede,
             'titulo': nombre or ' + '.join(o['titulo'] for o in obs),
             'obras': obs,
             # La palabra es del festival: Wilfrid Massamba, director de la
             # Fundación QAFF, por correo el 4 sep 2026 — «la entrada es libre en
             # todas las sedes, con inscripción previa». lib.acceso_campos() la
             # traduce sola a is_free + requires_registration. FALTA el enlace de
             # inscripción: sin él la app dice que hay que registrarse y no a dónde.
             'acceso': 'Entrada libre',
             '_src': f'parrilla impresa en el PDF oficial del programa, p{pag}'}
        for o in obs:
            if not o.get('_seccion'):
                sin_cruce.append(o['titulo'])
        _s = [o['_seccion'] for o in obs if o.get('_seccion')]
        if _s:
            # La sección del programa es la de la MAYORÍA de sus obras. En
            # empate NO vale `max(set(...))`: el orden de iteración de un set de
            # strings cambia en cada proceso, así que la misma entrada daba tres
            # secciones distintas en tres corridas — medido. Empate lo rompe la
            # primera obra del programa, que es la que lo encabeza.
            _orden = {x: i for i, x in enumerate(dict.fromkeys(_s))}
            f['seccion'] = max(dict.fromkeys(_s), key=lambda x: (_s.count(x), -_orden[x]))
        if nombre:
            f['sinopsis'] = sinopsis
            f['synopsis_lang'] = 'es'
        inv = qa.get((sede, sala, dia, hora))
        if inv:
            f['has_qa'] = True
            quienes = ' y '.join(sorted(
                (f'la {q} de «{titulo_obra(t, fichas)}»' if q.endswith('a')
                 else f'el {q} de «{titulo_obra(t, fichas)}»') for q, t in inv))
            f['_qa_src'] = ('el programa anuncia la presencia de ' + quienes
                            ).replace('de el ', 'del ')
        funciones.append(f)

    for tipo, sede, sala, dia, ini, fin, titulo, quien, pag in pr.ACTIVIDADES:
        a = {'dia': f'2026-09-{int(dia):02d}', 'hora': ini,
             'sede': f'{sede} · {sala}' if sala else sede,
             'titulo': titulo, 'obras': [],
             'event_kind': 'dialogo' if tipo == 'dialogo' else tipo,
             'acceso': 'Entrada libre',
             'sinopsis': quien, 'synopsis_lang': 'es',
             '_src': f'PDF oficial del programa, p{pag}'}
        # La sección de una actividad NO se inventa: «DIÁLOGO IMPROBABLE» está
        # impreso en su propia página del programa, y es además una de las 15
        # categorías del calendario oficial. La Muestra Artística, igual.
        a['seccion'] = {'dialogo': 'DIALOGO IMPROBABLE',
                        'muestra': 'MUESTRA ARTISTICA',
                        'vernissage': 'MUESTRA ARTISTICA'}.get(tipo)
        a['seccion'] = _cn(a['seccion']) if a['seccion'] else None
        a['_section_src'] = ('impresa en la página del programa y declarada como '
                             'categoría en el calendario oficial')
        if fin:
            a['hora_fin'] = fin
            # La duración de una actividad es OBLIGATORIA: alimenta el plan, y sin
            # ella el planificador no puede reservarle sitio ni ver si choca con
            # una función. Aquí no hay que estimarla: el programa imprime la
            # franja completa de cada Diálogo en su propia página.
            h1, m1 = (int(x) for x in ini.split(':'))
            h2, m2 = (int(x) for x in fin.split(':'))
            a['duracion_min'] = (h2 * 60 + m2) - (h1 * 60 + m1)
        funciones.append(a)

    # Una obra con dos títulos se parte en dos obras distintas: quien la marca en
    # una función no la reconoce en la otra. El programa lo hace tres veces, y
    # las tres están unificadas arriba —pero si el festival añade una cuarta,
    # esto tiene que gritar, no dejarla pasar.
    porobra = {}
    for f in funciones:
        for o in f.get('obras', []):
            if not o.get('director'):
                continue
            porobra.setdefault((n(o['director'])[:14], o.get('duracion_min')), set()).add(o['titulo'])
    partidas = {k: v for k, v in porobra.items() if len(v) > 1}
    assert not partidas, f'la misma obra con dos títulos, sin unificar: {partidas}'

    # ── la parte de la actividad dentro de una franja compartida ───────────
    # Nueve de las doce actividades comparten día, hora y sede con una
    # proyección, porque el programa las imprime así: una ventana de «3:00 - 5:00
    # pm» con las obras Y el Diálogo dentro. El modelo B de la doctrina —anclaje,
    # `sharedSlotIsOneScreening`— ya dice qué hacer con eso: las entradas no
    # rivalizan y la sala se ocupa con la SUMA. Pero entonces la duración de la
    # actividad no puede ser la ventana entera: sumada a las obras daba 162
    # minutos para una sesión de 120. Su parte es lo que sobra tras las
    # proyecciones, y así la suma vuelve a ser exactamente la ventana impresa.
    # Las tres actividades que van solas —Museo ×2 y la Nacional— conservan su
    # ventana completa, que ahí sí es toda suya.
    obras_por_franja = {}
    for f in funciones:
        if f.get('obras'):
            k = (f['sede'], f['dia'], f['hora'])
            obras_por_franja[k] = sum(o.get('duracion_min') or 0 for o in f['obras'])
    cuantas = {}
    for a in funciones:
        if a.get('event_kind'):
            k = (a['sede'], a['dia'], a['hora'])
            cuantas[k] = cuantas.get(k, 0) + 1
    for a in funciones:
        if not a.get('event_kind'):
            continue
        k = (a['sede'], a['dia'], a['hora'])
        vent = pr.VENTANAS.get((a['sede'].split(' · ')[0], a['dia'][8:], a['hora']))
        films = obras_por_franja.get(k)
        if vent and films is not None:
            # Con DOS actividades en la misma franja —el 17 en Alianza tiene el
            # Diálogo y el vernissage— el resto se reparte entre ellas. Darle el
            # resto entero a cada una duplicaba la franja.
            resto = (vent[0] - films) // cuantas[k]
            if resto > 0:
                a['duracion_min'] = resto
                a['_duracion_src'] = (f"la parrilla imprime una ventana de {vent[0]} min "
                                      f"(p{vent[1]}), las obras ocupan {films} y el resto se "
                                      f"reparte entre {cuantas[k]} actividad(es)"
                                      if cuantas[k] > 1 else
                                      f"la parrilla imprime una ventana de {vent[0]} min "
                                      f"(p{vent[1]}) y las obras ocupan {films}")
            else:
                # el propio programa sobrevende la franja: no hay resto que
                # repartir. Se declara y se le pregunta al festival.
                a['_ojo'] = (f'la franja impresa es de {vent[0]} min y solo las obras ya '
                             f'suman {films}: no cabe además la actividad')
        a['duration'] = f"{a['duracion_min']} min"

    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
    crudo = {
     '_provenance': {
       'fuente': 'PDF oficial del programa QAFF 2026 — quibdoafricafilmfestival.com/es/program-2026',
       'capturado': datetime.date.today().isoformat(),
       'metodo': 'capa de texto del PDF (no OCR). Parrilla y fichas cruzadas entre sí; '
                 'la transcripción verificada contra la página que declara; contrastada '
                 'con dos auditorías independientes del flip book',
       'quibdo': 'CANCELADO por el terremoto — la 8ª edición es solo en Bogotá',
       'prelanzamiento': 'el 5 SEP en el Museo Nacional NO se incluye',
     },
     '_pendiente_del_festival': {
       'fechas': 'el lomo dice «14 - 18 SEPTIEMBRE» en 10 páginas y «14 - 17» en las 2 de '
                 'Alianza Francesa, pero hay parrillas del 19 y el 20 en Cinemateca',
       'secciones': 'el programa de Bogotá NO imprime secciones en ninguna parte',
       'museo_y_unal': {sede: obs for sede, obs in SIN_HORA.items()},
       'franjas_que_no_caben': [
         "Alianza Francesa 15 SEP 15:00: 4 obras suman 79' en una franja de 60 min",
         "Universidad de los Andes 15 SEP 14:00: 2 obras suman 128' en una franja de 120 min"],
       # las tres discrepancias internas del PDF quedaron resueltas por tercera
       # fuente (TMDB, o la propia sinopsis del festival); no queda ninguna que
       # preguntar
     },
     'programas': funciones,
    }
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    # DE DÓNDE salió cada sección, y cuántas no salieron de ninguna parte.
    # Sin esta línea, 26 obras sin sección pasaban por «el festival no las
    # publica» — y sí las publicaba, en una fuente que no estábamos cruzando.
    # Un cruce que no dice cuánto pegó es un cruce que no se puede auditar.
    print('  sección, por fuente: '
          + ' · '.join(f'{v} {k}' for k, v in fuente_sec.most_common())
          + (f' · {len(set(sin_cruce))} SIN CRUZAR: {sorted(set(sin_cruce))}'
             if sin_cruce else ' · 0 sin cruzar'))
    json.dump(crudo, open(SALIDA, 'w'), ensure_ascii=False, indent=1)
    proy = [f for f in funciones if f.get('obras')]
    print(f"{len(proy)} funciones · {sum(len(f['obras']) for f in proy)} cupos de obra · "
          f"{len(funciones) - len(proy)} actividades")
    for s, k in collections.Counter(f['sede'] for f in funciones).most_common():
        print(f'   {k:3}  {s}')


if __name__ == '__main__':
    main()
