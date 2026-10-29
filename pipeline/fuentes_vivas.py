# -*- coding: utf-8 -*-
"""fuentes_vivas.py — las fuentes de un festival que CAMBIAN, bajadas por comando
y con su edad a la vista (20 oct 2026, aprobado por Juan).

POR QUÉ. Un festival vigente tiene varias fuentes (la página, la API, el PDF)
y solo algunas tenían comando para bajarse. Las demás quedaban viejas en
silencio y el pipeline comparaba contra ellas: FICCALI verificó contra la
página del 6 oct y la API del 18 hasta que alguien las bajó a mano con curl;
Fantasmagoría re-armó con la cartelera v2 cuando la vigente era la v26. La
fecha del archivo no sirve para medir la edad (copiar entre carpetas la
reescribe), así que cada descarga deja su hora en un registro propio.

EL PLAN las declara (pipeline/<fid>.plan.json):

    "fuentes_vivas": [
      {"archivo": "fuentes/<fid>/programacion.json", "url": "https://…/wp-json/wp/v2/<tipo>",
       "como": "wp-json"},                       # todas las páginas, y cuenta == X-WP-Total
      {"archivo": "fuentes/<fid>/pagina.html", "url": "https://…/programacion/",
       "como": "pagina", "debe_contener": "texto que tiene que estar"},
      {"archivo": "fuentes/<fid>/x.json", "cmd": "python3 pipeline/<fid>-x.py --bajar"}
    ]

USO
    python3 pipeline/correr.py <fid> --bajar   # baja todas y corre el plan
    python3 pipeline/fuentes_vivas.py <fid>    # solo bajar
    python3 pipeline/fuentes_vivas.py <fid> --edad

REGLA. Mientras el festival está vigente (desde 2 días antes hasta su fin), una
fuente viva sin registro o con más de `max_horas` (24 por defecto) FRENA a
correr.py y a publicar-datos.py, con el comando para refrescarla.
"""
import datetime, hashlib, json, os, subprocess, sys, tempfile, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
MAX_HORAS = 24


class FuenteMala(Exception):
    pass


def declaradas(fid):
    p = os.path.join(REPO, 'pipeline', f'{fid}.plan.json')
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding='utf-8')).get('fuentes_vivas') or []


def _registro_p(fid):
    return os.path.join(REPO, 'fuentes', fid, '_bajadas.json')


def registro(fid):
    p = _registro_p(fid)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def _anotar(fid, archivo, contenido, como):
    r = registro(fid)
    r[archivo] = {'cuando': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
                  'bytes': len(contenido), 'sha12': hashlib.sha256(contenido).hexdigest()[:12], 'como': como}
    os.makedirs(os.path.dirname(_registro_p(fid)), exist_ok=True)
    json.dump(r, open(_registro_p(fid), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read(), res.headers


def _escribir(ruta, contenido):
    """Atómico: si algo falla a mitad, queda la versión anterior entera."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta))
    with os.fdopen(fd, 'wb') as f:
        f.write(contenido)
    os.replace(tmp, ruta)


def bajar_una(fid, f):
    """Baja UNA fuente y la verifica antes de reemplazar la anterior. Un 200 no
    prueba nada (hay sitios que contestan 200 a todo): se mira el contenido."""
    ruta = os.path.join(REPO, f['archivo'])
    if f.get('cmd'):
        r = subprocess.run(f['cmd'], shell=True, cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(ruta):
            raise FuenteMala(f'{f["archivo"]}: «{f["cmd"]}» falló ({(r.stderr or r.stdout).strip()[-200:]})')
        contenido = open(ruta, 'rb').read()
    elif f.get('como') == 'wp-json':
        todo, pag, total = [], 1, None
        while True:
            sep = '&' if '?' in f['url'] else '?'
            cuerpo, h = _get(f'{f["url"]}{sep}per_page=100&page={pag}')
            if 'json' not in (h.get('Content-Type') or ''):
                raise FuenteMala(f'{f["archivo"]}: la API no devolvió JSON (página {pag})')
            lote = json.loads(cuerpo)
            if not isinstance(lote, list):
                raise FuenteMala(f'{f["archivo"]}: la API no devolvió una lista')
            todo += lote
            total = int(h.get('X-WP-Total') or len(todo))
            if pag >= int(h.get('X-WP-TotalPages') or 1):
                break
            pag += 1
        if len(todo) != total or not todo:
            raise FuenteMala(f'{f["archivo"]}: bajé {len(todo)} de {total} — no se reemplaza')
        contenido = json.dumps(todo, ensure_ascii=False, indent=1).encode()
        _escribir(ruta, contenido)
    else:   # pagina
        contenido, h = _get(f['url'])
        if 'html' not in (h.get('Content-Type') or '') or len(contenido) < 2000:
            raise FuenteMala(f'{f["archivo"]}: no parece la página ({h.get("Content-Type")}, {len(contenido)} bytes)')
        if f.get('debe_contener') and f['debe_contener'].encode() not in contenido:
            raise FuenteMala(f'{f["archivo"]}: la página no contiene «{f["debe_contener"]}» — no se reemplaza')
        _escribir(ruta, contenido)
    _anotar(fid, f['archivo'], contenido, f.get('como') or 'cmd')
    return len(contenido)


def bajar(fid):
    fs = declaradas(fid)
    if not fs:
        print(f'  · {fid}: el plan no declara fuentes_vivas')
        return
    malas = []
    for f in fs:
        try:
            n = bajar_una(fid, f)
            print(f'  ✓ {f["archivo"]} ({n:,} bytes)')
        except Exception as e:
            malas.append(str(e))
            print(f'  ✗ {e}')
    if malas:
        raise FuenteMala(f'{len(malas)} fuente(s) no se pudieron bajar — quedan las anteriores')


def vencidas(fid, ahora=None):
    """[(archivo, horas | None)] de las fuentes vivas sin registro o con más de su
    max_horas. None = nunca bajada por este comando (cuenta como vencida)."""
    ahora = ahora or datetime.datetime.now().astimezone()
    reg, malas = registro(fid), []
    for f in declaradas(fid):
        e = reg.get(f['archivo'])
        if not e:
            malas.append((f['archivo'], None)); continue
        h = (ahora - datetime.datetime.fromisoformat(e['cuando'])).total_seconds() / 3600
        if h > f.get('max_horas', MAX_HORAS):
            malas.append((f['archivo'], round(h)))
    return malas


def vigente(fid, hoy=None):
    """¿El festival está vigente (de 2 días antes a su fin)? Lee las fechas de su
    ficha con el mismo script que publica la ficha. Sin ficha: no vigente."""
    import re
    cfg = re.sub(r'-(\d+)$', r'\1', fid)          # ficcali-2026 → ficcali2026
    r = subprocess.run(['node', 'scripts/ficha-de.mjs', cfg], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        return False
    fi = json.loads(r.stdout)
    try:
        ini = datetime.date.fromisoformat(fi['festivalStartStr'][:10]) - datetime.timedelta(days=2)
        fin = datetime.date.fromisoformat(fi['festivalEndStr'][:10])
    except (KeyError, ValueError):
        return False
    hoy = hoy or datetime.date.today()
    return ini <= hoy <= fin


def frenar_si_vencidas(fid, comando):
    """El freno común de correr.py y publicar-datos.py. Devuelve None o el mensaje."""
    if not declaradas(fid) or not vigente(fid):
        return None
    v = vencidas(fid)
    if not v:
        return None
    lineas = '\n'.join(f'    {a}: {"nunca bajada con el comando" if h is None else f"hace {h} h"}' for a, h in v)
    return (f'✗ {fid} está VIGENTE y {len(v)} fuente(s) viva(s) están vencidas:\n{lineas}\n'
            f'  El pipeline compararía contra datos viejos sin avisar. Refrescalas:\n'
            f'    {comando}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    _fid = sys.argv[1]
    if '--edad' in sys.argv:
        _reg = registro(_fid)
        for _f in declaradas(_fid):
            _e = _reg.get(_f['archivo'])
            print(f'  {_f["archivo"]:60} {(_e or {}).get("cuando", "nunca bajada")}')
        sys.exit(0)
    try:
        bajar(_fid)
    except FuenteMala as _e:
        sys.exit(f'✗ {_e}')
