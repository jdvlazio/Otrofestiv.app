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
import json, re, subprocess, time, unicodedata, datetime

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
        if {x for x in a if len(x) > 4} & {x for x in b if len(x) > 4}:
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
    'rusia': '🇷🇺', 'polonia': '🇵🇱', 'dinamarca': '🇩🇰', 'suecia': '🇸🇪', 'noruega': '🇳🇴',
    'irlanda': '🇮🇪', 'belgica': '🇧🇪', 'paises bajos': '🇳🇱', 'portugal': '🇵🇹',
    'suiza': '🇨🇭', 'austria': '🇦🇹', 'grecia': '🇬🇷', 'turquia': '🇹🇷', 'kenia': '🇰🇪',
    'filipinas': '🇵🇭', 'macedonia del norte': '🇲🇰', 'nueva zelanda': '🇳🇿',
    'australia': '🇦🇺', 'luxemburgo': '🇱🇺', 'sudafrica': '🇿🇦', 'senegal': '🇸🇳',
}

def banderas(pais):
    out = [BANDERAS[k] for p in re.split(r'[,/]| y ', pais or '')
           if (k := norm(p)) in BANDERAS]
    return ''.join(dict.fromkeys(out))


# ── procedencia ──────────────────────────────────────────────────────────────
def provenance(fuente, **extra):
    """El bloque _provenance de todo sidecar. `capturado` va SIEMPRE: sin fecha
    no se puede saber si un sidecar está viejo — así se escondió el bug de las
    48 salas de FICDEH."""
    return {'fuente': fuente,
            'capturado': datetime.date.today().isoformat(), **extra}


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
    print(f'✓ selftest: {ok[0]} casos')


if __name__ == '__main__':
    _selftest()
