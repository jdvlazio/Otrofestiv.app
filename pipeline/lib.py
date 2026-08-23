# -*- coding: utf-8 -*-
"""lib.py — las funciones que cada festival reescribía, escritas UNA vez.

Auditoría del 9 ago 2026: `norm()` existía 3 veces, `get()` 4, el parser de
horas 2, las banderas y las tablas de días por festival. Este módulo las
extrae TAL CUAL se comportan en los pipelines vivos (FICDEH, FICMA) — no las
mejora, las deduplica. `python3 pipeline/lib.py --selftest` corre los casos
reales que cada una resolvió, incluidos los que costaron un bug.

── EL FORMATO INTERMEDIO ─────────────────────────────────────────────────────

Los parsers son desechables (cada fuente es única: un PDF de imágenes, un
Excel con filas rojas, un sitio Next.js). Las HERRAMIENTAS son permanentes
(cruce TMDB verificado, Letterboxd por tmdb_id, geocoding verificado, la
página de sedes). Lo que las une es UN formato: todo parser, sea cual sea su
fuente, escribe

    { "_provenance": provenance(fuente, ...),   # capturado= es OBLIGATORIO
      "funciones": [ {
         "titulo": str,          # verbatim de la fuente
         "dia":    "AAAA-MM-DD",
         "hora":   "HH:MM",      # 24h — usar hora24()
         "sede":   str,          # nombre CANÓNICO (sala aparte, ver sede_sala)
         "sala":   str,          # "" si no aplica
         "ciudad": str,          # "" en festival de una ciudad
         # opcionales, si la fuente los da:
         "director": str, "pais": str, "anio": int, "duracion_min": int,
         "has_qa": bool, "acceso": str, "en_app": bool,
      } ... ] }

y las herramientas genéricas leen ESO, no el JSON de cada festival. N lectores
→ 1 formato → M herramientas. Documentado en pipeline/PROTOCOLO.md.
"""
import json, os, re, collections, subprocess, time, unicodedata, datetime

# User-Agent de navegador: ficdeh.com (Vercel) y varios CDN bloquean curl pelado.
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


# ── texto ────────────────────────────────────────────────────────────────────
def sinacento(s):
    """MAYÚSCULAS sin tildes — para casar etiquetas («DIRECCIÓN» ≡ «DIRECCION»)."""
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').upper())
                   if unicodedata.category(c) != 'Mn')


def norm(s):
    """minúsculas, sin tildes, solo alfanumérico — la clave de comparación de
    títulos y sedes en todos los cruces."""
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def slug(t):
    """nombre de archivo: pósters en assets/<fest>/<slug>.jpg."""
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:60]


# ── horas ────────────────────────────────────────────────────────────────────
def hora24(h):
    """«5:30 p.m.» → «17:30». Devuelve el texto intacto si no parece hora."""
    m = re.match(r'(\d{1,2})[:.](\d{2})\s*([apm])', (h or '').strip(), re.I)
    if not m:
        return (h or '').strip()
    hh, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == 'p' and hh != 12:
        hh += 12
    if ap == 'a' and hh == 12:
        hh = 0
    return f'{hh:02d}:{mm}'


def rango_horario(txt):
    """«8:00 - 5:00pm» → ('08:00', 540). «11:00 am» → ('11:00', None).

    El am/pm suele venir SOLO al final del rango: se resuelve por orden —si el
    fin queda antes que el inicio, el inicio era a.m.—, no asumiendo. (Leerlo
    literal daba talleres de 8 de la noche a 5 de la tarde: FICMA, franja.)"""
    t = (txt or '').lower().replace('.', '')
    def a24(h, m, ap):
        h = int(h)
        if ap == 'pm' and h != 12: h += 12
        if ap == 'am' and h == 12: h = 0
        return f'{h:02d}:{int(m or 0):02d}'
    r = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)?\s*[-–a]\s*'
                  r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)', t)
    if r:
        h1, m1, ap1, h2, m2, ap2 = r.groups()
        fin = a24(h2, m2, ap2)
        ini = a24(h1, m1, ap1 or ap2)
        if ini >= fin:
            ini = a24(h1, m1, 'am')
        d = (int(fin[:2]) * 60 + int(fin[3:])) - (int(ini[:2]) * 60 + int(ini[3:]))
        return ini, (d if d > 0 else None)
    u = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)', t)
    return (a24(*u.groups()) if u else ''), None


# ── red ──────────────────────────────────────────────────────────────────────
def curl_get(url, retries=3, min_bytes=3000, timeout=40):
    """GET con UA de navegador y reintentos. '' si no hay respuesta útil."""
    for _ in range(retries):
        r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', str(timeout),
                            '-A', UA, '-H', 'Accept: text/html,application/xhtml+xml', url],
                           capture_output=True)
        if r.returncode == 0 and len(r.stdout) > min_bytes:
            return r.stdout.decode('utf-8', 'ignore')
        time.sleep(1.2)
    return ''


def tmdb_get(path, api_key, **params):
    """GET a api.themoviedb.org v3. {} si falla."""
    url = f'https://api.themoviedb.org/3{path}?api_key={api_key}&' + '&'.join(
        f'{k}=' + str(v).replace(' ', '%20').replace('&', '%26') for k, v in params.items())
    for _ in range(3):
        r = subprocess.run(['curl', '-s', '--max-time', '25', url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except Exception:
                pass
        time.sleep(0.8)
    return {}


# ── verificación (la lección Tribeca, ejecutable) ────────────────────────────
def director_coincide(esperado, nombres):
    """¿Algún nombre de TMDB casa con el director de la fuente? Compara por
    tokens largos sin partículas: «Michaël Dudok de Wit» ≡ «Michael Dudok de
    Wit»; con 宮崎吾朗 casan los créditos romanizados (pedirlos en en-US)."""
    quita = {'de', 'la', 'del', 'y', 'van', 'der', 'le'}
    a = set(norm(esperado).split()) - quita
    for n in (nombres or []):
        b = set(norm(n).split()) - quita
        # tokens largos compartidos (apellidos), O casi-todos los tokens si son
        # cortos: «Gala del Sol» no tiene ninguno de >4 letras y aun así debe
        # casar consigo misma. Al extraer esta función a la lib se perdió la
        # segunda cláusula y la validación contra FICMA lo cazó (obra 68/68 con
        # una faltante). Ambas vienen del script original.
        if {x for x in a if len(x) > 4} & {x for x in b if len(x) > 4}:
            return True
        if a and b and len(a & b) >= min(2, len(a), len(b)):
            return True
    return False


def ficha_verifica(pdf, det, tol_anio=1, tol_dur=3):
    """El candado completo: director ✓ Y (año ±1 O duración ±3 min). `pdf` es
    la función del formato intermedio; `det` la ficha TMDB con credits."""
    dirs = [p['name'] for p in det.get('credits', {}).get('crew', [])
            if p.get('job') == 'Director']
    anio_t = int((det.get('release_date') or '0000')[:4] or 0)
    dur_t = det.get('runtime') or 0
    d_ok = director_coincide(pdf.get('director', ''), dirs)
    a_ok = pdf.get('anio') and abs(anio_t - pdf['anio']) <= tol_anio
    r_ok = pdf.get('duracion_min') and dur_t and abs(dur_t - pdf['duracion_min']) <= tol_dur
    return bool(d_ok and (a_ok or r_ok))


# ── sedes ────────────────────────────────────────────────────────────────────
def sede_sala(nombre, tabla):
    """Aplica la tabla canónica sede→(sede, sala) de cada festival. La tabla es
    EXPLÍCITA, nunca heurística sobre el guion: «Cine al barrio - Samaria»
    también lo lleva y ahí Samaria es el lugar. La lección más cara de FICDEH."""
    return tabla.get(nombre, (nombre, ''))


# ── config de días (idéntica en todos los festivales) ────────────────────────
_D = {'ab': ['LUN','MAR','MIÉ','JUE','VIE','SÁB','DOM'],
      'en': ['MON','TUE','WED','THU','FRI','SAT','SUN'],
      'es': ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']}

def dias_config(dias, mes_es='agosto'):
    """['2026-08-10',…] → los seis bloques de días de FESTIVAL_CONFIG/JSON."""
    f = datetime.date.fromisoformat
    return {
        'festivalDates': {x: x for x in dias},
        'days': [{'k': x, 'd': f(x).day, 'lbl': _D['ab'][f(x).weekday()]} for x in dias],
        'dayKeys': list(dias),
        'dayShort': {x: f'{_D["ab"][f(x).weekday()]} {f(x).day}' for x in dias},
        'dayShort_en': {x: f'{_D["en"][f(x).weekday()]} {f(x).day}' for x in dias},
        'dayLong': {x: f'{_D["es"][f(x).weekday()]} {f(x).day} de {mes_es}' for x in dias},
    }


# ── banderas ─────────────────────────────────────────────────────────────────
BANDERAS = {
    'colombia': '🇨🇴', 'argentina': '🇦🇷', 'brasil': '🇧🇷', 'chile': '🇨🇱', 'mexico': '🇲🇽',
    'peru': '🇵🇪', 'panama': '🇵🇦', 'ecuador': '🇪🇨', 'venezuela': '🇻🇪', 'bolivia': '🇧🇴',
    'uruguay': '🇺🇾', 'paraguay': '🇵🇾', 'cuba': '🇨🇺', 'espana': '🇪🇸', 'francia': '🇫🇷',
    'italia': '🇮🇹', 'alemania': '🇩🇪', 'reino unido': '🇬🇧', 'estados unidos': '🇺🇸',
    'canada': '🇨🇦', 'japon': '🇯🇵', 'china': '🇨🇳', 'iran': '🇮🇷', 'india': '🇮🇳',
    'rusia': '🇷🇺',
    'federacion rusa': '🇷🇺',   # así lo escribe CineAutopsia
    'polonia': '🇵🇱', 'dinamarca': '🇩🇰', 'suecia': '🇸🇪', 'noruega': '🇳🇴',
    'irlanda': '🇮🇪', 'belgica': '🇧🇪', 'paises bajos': '🇳🇱', 'portugal': '🇵🇹',
    'suiza': '🇨🇭', 'austria': '🇦🇹', 'grecia': '🇬🇷', 'turquia': '🇹🇷', 'kenia': '🇰🇪',
    'filipinas': '🇵🇭', 'macedonia del norte': '🇲🇰', 'nueva zelanda': '🇳🇿',
    'australia': '🇦🇺', 'luxemburgo': '🇱🇺', 'sudafrica': '🇿🇦', 'senegal': '🇸🇳',
    # ── medidos contra los 13 festivales del repo el 17 ago 2026 ──────────────
    # La tabla se escribía a mano y a demanda, así que le faltaba lo que ningún
    # festival anterior había traído: «Hungría» apareció con CineAutopsia y se
    # quedó sin bandera. En vez de añadir una, se midió TODO el repo y se cerró
    # el hueco entero. Los nombres en inglés entran porque los festivales
    # internacionales publican así (TIFF, Tribeca) y traducirlos en la línea de
    # salida sería inventar la palabra del festival.
    'hungria': '🇭🇺', 'palestina': '🇵🇸', 'honduras': '🇭🇳', 'taiwan': '🇹🇼',
    'qatar': '🇶🇦', 'bangladesh': '🇧🇩', 'corea del sur': '🇰🇷', 'corea': '🇰🇷',
    'sri lanka': '🇱🇰', 'malasia': '🇲🇾', 'eslovaquia': '🇸🇰', 'vietnam': '🇻🇳',
    'nigeria': '🇳🇬', 'puerto rico': '🇵🇷', 'rumania': '🇷🇴', 'rumania (romania)': '🇷🇴',
    'estonia': '🇪🇪', 'republica dominicana': '🇩🇴', 'rep. dominicana': '🇩🇴',
    'israel': '🇮🇱', 'tailandia': '🇹🇭', 'kosovo': '🇽🇰', 'bulgaria': '🇧🇬',
    'costa rica': '🇨🇷', 'georgia': '🇬🇪', 'guatemala': '🇬🇹', 'nicaragua': '🇳🇮',
    'el salvador': '🇸🇻', 'haiti': '🇭🇹', 'jamaica': '🇯🇲', 'marruecos': '🇲🇦',
    'egipto': '🇪🇬', 'tunez': '🇹🇳', 'argelia': '🇩🇿', 'libano': '🇱🇧',
    'siria': '🇸🇾', 'irak': '🇮🇶', 'afganistan': '🇦🇫', 'pakistan': '🇵🇰',
    'indonesia': '🇮🇩', 'singapur': '🇸🇬', 'camboya': '🇰🇭', 'nepal': '🇳🇵',
    'mongolia': '🇲🇳', 'ucrania': '🇺🇦', 'republica checa': '🇨🇿', 'chequia': '🇨🇿',
    'hungria (magyarorszag)': '🇭🇺', 'serbia': '🇷🇸', 'croacia': '🇭🇷',
    'eslovenia': '🇸🇮', 'bosnia y herzegovina': '🇧🇦', 'albania': '🇦🇱',
    'letonia': '🇱🇻', 'lituania': '🇱🇹', 'finlandia': '🇫🇮', 'islandia': '🇮🇸',
    'etiopia': '🇪🇹', 'ghana': '🇬🇭', 'mali': '🇲🇱', 'burkina faso': '🇧🇫',
    'ruanda': '🇷🇼', 'tanzania': '🇹🇿', 'uganda': '🇺🇬', 'mozambique': '🇲🇿',
    'angola': '🇦🇴', 'congo': '🇨🇬', 'republica democratica del congo': '🇨🇩',
    'costa de marfil': '🇨🇮', 'camerun': '🇨🇲', 'zimbabue': '🇿🇼', 'namibia': '🇳🇦',
    'botsuana': '🇧🇼', 'sudan': '🇸🇩', 'somalia': '🇸🇴', 'yemen': '🇾🇪',
    'arabia saudita': '🇸🇦', 'saudi arabia': '🇸🇦', 'turkiye': '🇹🇷', 'emiratos arabes unidos': '🇦🇪', 'jordania': '🇯🇴',
    # nombres en inglés, tal como los publican los festivales internacionales
    'united states': '🇺🇸', 'usa': '🇺🇸', 'eeuu': '🇺🇸', 'ee.uu.': '🇺🇸',
    'united kingdom': '🇬🇧', 'uk': '🇬🇧', 'inglaterra': '🇬🇧', 'england': '🇬🇧',
    'scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', 'france': '🇫🇷', 'spain': '🇪🇸', 'germany': '🇩🇪',
    'italy': '🇮🇹', 'norway': '🇳🇴', 'sweden': '🇸🇪', 'denmark': '🇩🇰',
    'ireland': '🇮🇪', 'netherlands': '🇳🇱', 'belgium': '🇧🇪', 'switzerland': '🇨🇭',
    'austria': '🇦🇹', 'poland': '🇵🇱', 'portugal': '🇵🇹', 'greece': '🇬🇷',
    'japan': '🇯🇵', 'south korea': '🇰🇷', 'korea': '🇰🇷', 'india': '🇮🇳',
    'brazil': '🇧🇷', 'mexico': '🇲🇽', 'chile': '🇨🇱', 'colombia': '🇨🇴',
    'argentina': '🇦🇷', 'peru': '🇵🇪', 'canada': '🇨🇦', 'australia': '🇦🇺',
    'new zealand': '🇳🇿', 'south africa': '🇿🇦', 'israel': '🇮🇱', 'turkey': '🇹🇷',
    'china': '🇨🇳', 'taiwan': '🇹🇼', 'hong kong': '🇭🇰', 'philippines': '🇵🇭',
    'thailand': '🇹🇭', 'vietnam': '🇻🇳', 'indonesia': '🇮🇩', 'malaysia': '🇲🇾',
    'ukraine': '🇺🇦', 'russia': '🇷🇺', 'czech republic': '🇨🇿', 'czechia': '🇨🇿',
    'hungary': '🇭🇺', 'romania': '🇷🇴', 'bulgaria': '🇧🇬', 'serbia': '🇷🇸',
    'croatia': '🇭🇷', 'slovenia': '🇸🇮', 'slovakia': '🇸🇰', 'estonia': '🇪🇪',
    'latvia': '🇱🇻', 'lithuania': '🇱🇹', 'finland': '🇫🇮', 'iceland': '🇮🇸',
    'egypt': '🇪🇬', 'morocco': '🇲🇦', 'tunisia': '🇹🇳', 'algeria': '🇩🇿',
    'nigeria': '🇳🇬', 'kenya': '🇰🇪', 'senegal': '🇸🇳', 'ethiopia': '🇪🇹',
    # Territorios de ultramar del Caribe francés. No son estados soberanos,
    # pero tienen bandera propia y los festivales los publican como país de
    # la obra — QAFF 2026 trae tres. Puerto Rico ya sentaba el criterio.
    'martinica': '🇲🇶', 'guadalupe': '🇬🇵', 'guayana francesa': '🇬🇫',
}

# ISO2, porque los catálogos y TMDB los publican así y un país escrito «CO» es
# el mismo país. Solo los que aparecen de verdad en el repo.
ISO2 = {'co': '🇨🇴', 'ar': '🇦🇷', 'br': '🇧🇷', 'cl': '🇨🇱', 'mx': '🇲🇽', 'pe': '🇵🇪',
        'us': '🇺🇸', 'gb': '🇬🇧', 'fr': '🇫🇷', 'es': '🇪🇸', 'de': '🇩🇪', 'it': '🇮🇹',
        'ca': '🇨🇦', 'pt': '🇵🇹', 'jp': '🇯🇵', 'cn': '🇨🇳', 'kr': '🇰🇷', 'in': '🇮🇳'}

# Abreviaturas y nombres a medias que los festivales publican tal cual.
ALIAS = {'rep dominicana': '🇩🇴', 'rd congo': '🇨🇩', 'guinea bissau': '🇬🇼',
         'republica democratica del congo': '🇨🇩'}


def banderas(pais):
    """País(es) → banderas, deduplicadas y en orden de aparición.

    Separa por coma, barra, « y » Y POR PARÉNTESIS: «España (Austria)» es una
    coproducción de dos países, y quedarse con uno pierde el otro — 84 casos
    medidos en el repo el 17 ago 2026. Un país que no se reconoce no inventa
    bandera: se omite, y el guardián [country-flags] lo cuenta."""
    out = []
    for p in re.split(r'[,/()]| y | - |—', pais or ''):
        k = norm(p)
        if not k:
            continue
        b = BANDERAS.get(k) or ALIAS.get(k) or (ISO2.get(k) if len(k) == 2 else None)
        if b:
            out.append(b)
    return ''.join(dict.fromkeys(out))


# ── procedencia ──────────────────────────────────────────────────────────────
def provenance(fuente, **extra):
    """El bloque _provenance de todo sidecar. `capturado` va SIEMPRE: sin fecha
    no se puede saber si un sidecar está viejo — así se escondió el bug de las
    48 salas de FICDEH."""
    return {'fuente': fuente,
            'capturado': datetime.date.today().isoformat(), **extra}


# ── acceso: la casilla que no se puede dejar en blanco ───────────────────────
# EL ESLABÓN QUE FALTABA. El formato intermedio ya tenía `acceso`, FICDEH lo
# capturaba de su web y FICMA lo declaraba en prosa — y aun así NINGÚN festival
# convertía eso en los campos que la app lee. CineAutopsia lo dejó vacío y nadie
# se enteró: 6 enlaces de TuBoleta estaban en la fuente y no llegaron al JSON.
# Aquí vive la traducción, una sola vez, con las frases reales que la escriben.
#
# Y una distinción que importa: NO SABER no es lo mismo que NO MIRAR. Un
# festival que aún no publicó precios se declara `desconocido` a propósito; lo
# que queda prohibido es el silencio.
DESCONOCIDO = 'desconocido'

_LIBRE = ('entrada libre', 'entrada gratuita', 'gratuita', 'gratuito', 'gratis',
          'ingreso libre', 'acceso libre', 'free admission', 'entrada franca')
_INSCRIPCION = ('inscripcion', 'inscribir', 'registro previo', 'cupo limitado',
                'previa inscripcion', 'formulario')


def acceso_campos(texto, url=''):
    """De la palabra del festival a los 4 campos que la app lee.

    Devuelve solo lo que la fuente AFIRMA — nunca rellena el hueco con una
    suposición. `ticketing_model` es del festival, no de la función, y se
    decide arriba: solo 'paid' | 'mixed' ([valor-inventado]).

    >>> acceso_campos('Entrada libre')            # Cinemateca de Bogotá
    {'is_free': True}
    >>> acceso_campos('', 'https://...tuboleta...')
    {'ticket_url': 'https://...tuboleta...'}
    """
    t = norm(texto or '')
    out = {}
    if url and url.startswith('http'):
        out['ticket_url'] = url
    if any(x in t for x in _LIBRE):
        out['is_free'] = True
    if any(x in t for x in _INSCRIPCION):
        out['requires_registration'] = True
    return out


def acceso_declarado(f):
    """¿Esta función del formato intermedio dice cómo se entra? El string vacío
    NO cuenta: es exactamente el hueco por el que se coló CineAutopsia."""
    return bool((f.get('acceso') or '').strip()) or bool(f.get('ticket_url'))


# ── el formato intermedio: cargar validando ──────────────────────────────────
def cargar_crudo(path):
    """Carga un sidecar del formato intermedio y FALLA si no lo cumple. Las
    herramientas genéricas solo aceptan este shape: mejor un error a la cara
    que una herramienta leyendo claves que no existen."""
    d = json.load(open(path, encoding='utf-8'))
    pr = d.get('_provenance') or {}
    assert pr.get('capturado'), f'{path}: _provenance.capturado es OBLIGATORIO'
    # `programas` es alias legítimo de `funciones`: un programa de cortos ES una
    # función —se entra una vez, se sienta una vez— y obligar a renombrarlo solo
    # para pasar por aquí sería una ceremonia sin dato detrás.
    fs = d.get('funciones') or d.get('programas')
    d['funciones'] = fs   # el resto del pipeline lee UNA clave, no dos
    assert isinstance(fs, list) and fs, f'{path}: falta la lista funciones[] (o programas[])'
    OBLIG = {'titulo', 'dia', 'hora', 'sede'}
    for i, f in enumerate(fs):
        faltan = OBLIG - set(f)
        assert not faltan, f'{path}: funciones[{i}] sin {sorted(faltan)}'
    # La casilla de acceso no puede quedar MUDA. Basta con que el festival lo
    # diga una vez para todas sus funciones (FICMA: «entrada libre a todo el
    # festival»), pero alguien tiene que decirlo. Si de verdad no se sabe, se
    # escribe lib.DESCONOCIDO — la ignorancia se declara, el silencio no vale.
    if not any(acceso_declarado(f) for f in fs):
        raise AssertionError(
            f'{path}: ninguna función dice cómo se entra. Llená `acceso` (o '
            f'`ticket_url`) al menos en una; si el festival no lo ha publicado, '
            f'poné lib.DESCONOCIDO a propósito.')
    return d


# ── el contrato, aplicado al escribir ────────────────────────────────────────
# `pipeline/contrato.json` declara el tipo de cada campo. Esta función lo APLICA
# en el último paso antes de publicar: es el sitio por donde pasa todo festival,
# y por tanto el único donde una corrección llega a todos.
#
# Por qué existe: FICDEH y FICMA —los dos festivales MÁS RECIENTES— emitían
# `year` como string mientras los otros diez lo emitían como número. Nadie lo
# vio nunca porque la app hace `String(f.year)` en las cuatro superficies donde
# lo pinta. Un dato puede estar mal tipado durante meses si la app es amable con
# él; el contrato no lo es, y ese es el punto.
#
# NO INVENTA: lo que no puede convertir lo deja como está y lo reporta, para que
# la decisión la tome una persona. Un `year: ''` no se vuelve 0 — se omite, que
# es lo que significa.
_CONTRATO = None


def contrato():
    global _CONTRATO
    if _CONTRATO is None:
        _CONTRATO = json.load(open(f'{os.path.dirname(os.path.abspath(__file__))}'
                                   '/contrato.json', encoding='utf-8'))
    return _CONTRATO


def normaliza(film, reporte=None):
    """Coacciona los tipos del contrato en UN film. Devuelve el film."""
    for k, spec in contrato()['campos'].items():
        if k not in film:
            continue
        v = film[k]
        if v is None or v == '':
            del film[k]                      # el campo vacío se OMITE, no se emite
            continue
        if spec.get('tipo') == 'number' and not isinstance(v, bool) and isinstance(v, str):
            if v.strip().isdigit():
                film[k] = int(v)
                if reporte is not None:
                    reporte[k] += 1
            elif reporte is not None:
                reporte[f'{k}!NO-CONVERTIBLE'] += 1
        if spec.get('tipo') == 'boolean' and isinstance(v, str):
            if v.lower() in ('true', 'false'):
                film[k] = (v.lower() == 'true')
                if reporte is not None:
                    reporte[k] += 1
    return film


# ── selftest ─────────────────────────────────────────────────────────────────
def _selftest():
    ok = [0]
    def t(nombre, got, want):
        assert got == want, f'{nombre}: {got!r} != {want!r}'
        ok[0] += 1
    # casos reales, cada uno resolvió (o causó) algo concreto
    t('norm tildes', norm('Akababuru: Expresión de asombro'), 'akababuru expresion de asombro')
    t('sinacento', sinacento('Dirección'), 'DIRECCION')
    t('slug', slug('¿Cómo limpiar un espejo?'), 'como-limpiar-un-espejo')
    t('hora24 pm', hora24('5:30 p.m.'), '17:30')
    t('hora24 12am', hora24('12:00 a.m.'), '00:00')
    t('hora24 12pm', hora24('12:00 p.m.'), '12:00')
    t('rango pm solo al final', rango_horario('8:00 - 5:00pm'), ('08:00', 540))
    t('rango explícito', rango_horario('9:00 am - 12:00 pm'), ('09:00', 180))
    t('rango sin fin', rango_horario('11:00 am'), ('11:00', None))
    t('director acentos', director_coincide('Michaël Dudok de Wit', ['Michael Dudok de Wit']), True)
    t('director romanizado', director_coincide('Gorõ Miyazaki', ['宮崎吾朗', 'Goro Miyazaki']), True)
    t('director distinto', director_coincide('Lina Rodríguez', ['Maider Oleaga']), False)
    t('director tokens cortos', director_coincide('Gala del Sol', ['Gala del Sol']), True)
    t('banderas coproducción con paréntesis', banderas('España (Austria)'), '🇪🇸🇦🇹')
    t('banderas ISO2', banderas('CO'), '🇨🇴')
    t('banderas con guion', banderas('Colombia - España'), '🇨🇴🇪🇸')
    t('banderas Hungría (la que faltaba)', banderas('Hungría'), '🇭🇺')
    t('banderas no inventa', banderas('Varios'), '')
    t('banderas no duplica', banderas('Colombia, Colombia'), '🇨🇴')
    # acceso — las frases REALES que escriben los festivales
    _rep = collections.Counter()
    t('normaliza year string→int', normaliza({'year': '1998'}, _rep)['year'], 1998)
    t('normaliza year vacío se OMITE', 'year' in normaliza({'year': ''}), False)
    t('normaliza year no numérico se respeta', normaliza({'year': 'circa 1970'}, _rep)['year'], 'circa 1970')
    t('normaliza is_free "true"→True', normaliza({'is_free': 'true'})['is_free'], True)
    t('normaliza no toca lo que ya está bien', normaliza({'year': 2026})['year'], 2026)
    t('acceso libre (Cinemateca)', acceso_campos('Entrada libre'), {'is_free': True})
    t('acceso gratuito (FINCA)', acceso_campos('Entrada gratuita. Por orden de llegada.'), {'is_free': True})
    t('acceso libre todo el fest (FICMA)', acceso_campos('Entrada libre a todo el festival'), {'is_free': True})
    t('acceso con inscripcion (FICDEH)', acceso_campos('Previa inscripción'), {'requires_registration': True})
    t('acceso con enlace', acceso_campos('', 'https://cinemateca.checkout.tuboleta.com/x'),
      {'ticket_url': 'https://cinemateca.checkout.tuboleta.com/x'})
    t('acceso desconocido no inventa', acceso_campos(DESCONOCIDO), {})
    t('reserva no es gratis', acceso_campos('Reserva por boletería online o presencial.'), {})
    t('declarado: vacío no cuenta', acceso_declarado({'acceso': '  '}), False)
    t('declarado: desconocido SÍ cuenta', acceso_declarado({'acceso': DESCONOCIDO}), True)
    t('ficha ok', ficha_verifica(
        {'director': 'Kogonada', 'anio': 2017, 'duracion_min': 104},
        {'credits': {'crew': [{'job': 'Director', 'name': 'Kogonada'}]},
         'release_date': '2017-08-04', 'runtime': 104}), True)
    t('ficha homónimo', ficha_verifica(          # Tribeca: título igual, otra peli
        {'director': 'Sepideh Farsi', 'anio': 2023, 'duracion_min': 100},
        {'credits': {'crew': [{'job': 'Director', 'name': 'Mario Nalpas'}]},
         'release_date': '1927-01-01', 'runtime': 86}), False)
    t('sede_sala tabla', sede_sala('Olimpia', {'Olimpia': ('Teatro los Fundadores', 'Sala Olimpia')}),
      ('Teatro los Fundadores', 'Sala Olimpia'))
    t('sede_sala passthrough', sede_sala('Batuta', {}), ('Batuta', ''))
    t('banderas dobles', banderas('Colombia, Canadá'), '🇨🇴🇨🇦')
    t('banderas dedup', banderas('Colombia / Colombia'), '🇨🇴')
    d = dias_config(['2026-08-10', '2026-08-11'])
    t('dias lbl', d['days'][0], {'k': '2026-08-10', 'd': 10, 'lbl': 'LUN'})
    t('dias long', d['dayLong']['2026-08-11'], 'Martes 11 de agosto')
    assert 'capturado' in provenance('x'); ok[0] += 1
    import tempfile, os as _os
    tf = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
    json.dump({'_provenance': provenance('test'),
               'funciones': [{'titulo': 'X', 'dia': '2026-09-09', 'hora': '10:00',
                              'sede': 'Y', 'acceso': 'Entrada libre'}]}, tf)
    tf.close()
    t('cargar_crudo ok', len(cargar_crudo(tf.name)['funciones']), 1)
    json.dump({'funciones': [{'titulo': 'X'}]}, open(tf.name, 'w'))
    try:
        cargar_crudo(tf.name); assert False, 'debió fallar sin capturado'
    except AssertionError as e:
        assert 'capturado' in str(e); ok[0] += 1
    # el crudo MUDO: cumple todo lo demás y no dice cómo se entra
    json.dump({'_provenance': provenance('test'),
               'funciones': [{'titulo': 'X', 'dia': '2026-09-09', 'hora': '10:00',
                              'sede': 'Y', 'acceso': ''}]}, open(tf.name, 'w'))
    try:
        cargar_crudo(tf.name); assert False, 'debió fallar mudo sobre el acceso'
    except AssertionError as e:
        assert 'cómo se entra' in str(e); ok[0] += 1
    _os.unlink(tf.name)
    print(f'✓ selftest: {ok[0]} casos')


if __name__ == '__main__':
    _selftest()
