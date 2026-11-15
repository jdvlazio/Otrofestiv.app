#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""altas.py <fid> — el REGISTRO de altas: por cada obra sin ficha, qué se miró,
dónde, cuándo y qué se decidió (15 nov 2026).

POR QUÉ EXISTE. En BOGOSHORTS una investigación «rigurosa» la hicieron ayudantes
que dijeron cumplir y no revisaron las fuentes de afiche; una ficha se declaró a
mano en `fichas`, un afiche se recortó a mano, un título del catálogo venía en
NFD y no casaba. Juan (15 nov): las decisiones «¿tiene ficha en TMDB? ¿tiene
afiche original? ¿se da de alta?» pasan SIEMPRE por el pipeline y por
guardianes, no por el criterio libre de quien la haga.

EL REGISTRO. festivals/staging/<fid>-altas.json:
    {"obras": {"<título NFC>": {
        "titulo", "director", "estado": ficha_existente | alta_posible |
                                        afiche_chico | sin_afiche | alta_hecha,
        "tmdb_id"?, "afiche"?: {url, fuente, archivo, px, ratio, recorte, veredicto_criterio},
        "fuentes": {<clave>: {url, fecha, resultado} | {na: true, por_que, fecha}}}}}
Una fuente sin `url` (ni N/A con `por_que`) cuenta como NO revisada. La lista de
fuentes obligatorias vive SOLO acá: FUENTES_OBLIGATORIAS.

    python3 pipeline/altas.py <fid> --sondar                  # TMDB automático → registro
    python3 pipeline/altas.py <fid> --pendientes              # qué falta mirar a mano
    python3 pipeline/altas.py <fid> --fuente <título> <clave> <url> [--resultado TXT]
    python3 pipeline/altas.py <fid> --na <título> <clave> --por-que TXT
    python3 pipeline/altas.py <fid> --sin-afiche <título> --por-que TXT
    python3 pipeline/altas.py <fid> --preparar <título> --url URL --origen TXT
    python3 pipeline/altas.py <fid> --registrar-alta <título> <tmdb_id>

Guardianes: [alta-sin-evidencia], [ficha-sin-registro], [titulo-nfc] (validate.py);
deuda congelada en pipeline/altas-deuda.json (solo baja).
"""
import datetime, glob, json, os, re, sys, unicodedata, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEUDA = os.path.join(REPO, 'pipeline', 'altas-deuda.json')
sys.path.insert(0, os.path.join(REPO, 'pipeline'))

# LA lista. Agregar una fuente aquí la vuelve obligatoria para todo festival.
FUENTES_OBLIGATORIAS = (
    'tmdb_titulo',               # search/movie por el título del festival (con y sin año)
    'tmdb_alternos',             # sin acentos, sin subtítulo, título original/inglés
    'tmdb_director',             # search/person + movie_credits/tv_credits de cada director
    'imdb',
    'letterboxd',
    'web_director_o_productora',
    'distribuidora_o_agencia',
    'plataformas_festivales',    # Short Film Depot / FilmFreeway / Festhome
    'festivales_previos',
    'organismo_nacional',        # Proimágenes, INCAA, IMCINE…
    'busqueda_imagenes',
)
FUENTES_VIDEOCLIP = ('canal_oficial_artista',)
ESTADOS = ('ficha_existente', 'alta_posible', 'afiche_chico', 'sin_afiche', 'alta_hecha')
CON_FICHA = ('ficha_existente', 'alta_hecha')
RATIO = (0.66, 0.71)             # ancho/alto aceptado para el póster
MIN_PX = (500, 750)              # mínimo de TMDB para un póster


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def plano(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


def hoy():
    return datetime.date.today().isoformat()


def _st(raiz):
    return os.path.join(raiz, 'festivals', 'staging')


def ruta_registro(fid, raiz=REPO):
    return os.path.join(_st(raiz), f'{fid}-altas.json')


def leer_registro(fid, raiz=REPO):
    p = ruta_registro(fid, raiz)
    d = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    d.setdefault('obras', {})
    d['obras'] = {nfc(t): v for t, v in d['obras'].items()}
    return d


def escribir_registro(fid, reg, raiz=REPO):
    import lib
    reg['_provenance'] = lib.provenance('pipeline/altas.py (TMDB + fuentes revisadas a mano, una por una)')
    reg['_nota'] = ('registro de altas: por obra sin ficha, las fuentes revisadas y la decisión. '
                    'Se escribe con pipeline/altas.py, no a mano.')
    json.dump(reg, open(ruta_registro(fid, raiz), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _leer(p):
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def correcciones(fid, raiz=REPO):
    return _leer(os.path.join(_st(raiz), f'{fid}-correcciones.json'))


def sin_ficha(fid, raiz=REPO):
    """Títulos (NFC) sin ficha según el enriquecido, menos los que ya tienen una
    ficha declarada en `fichas` (la próxima corrida los casa)."""
    s = set()
    for n in (f'{fid}-catalogo-enriquecido.json', f'{fid}-enriquecido.json'):
        s |= {nfc(t) for t in (_leer(os.path.join(_st(raiz), n)).get('sin_ficha') or [])}
    dec = {plano(t) for t in (correcciones(fid, raiz).get('fichas') or {})}
    return sorted(t for t in s if plano(t) not in dec)


def obra_catalogo(fid, titulo, raiz=REPO):
    """Lo que el catálogo (o el crudo) sabe de la obra, por título plano."""
    k = plano(titulo)
    for n in (f'{fid}-catalogo.json',):
        for o in _leer(os.path.join(_st(raiz), n)).get('obras') or []:
            if plano(o.get('titulo')) == k:
                return o
    return {'titulo': titulo}


_ARTISTA = re.compile(r'\(([^)]*[^\d\s)][^)]*)\)\s*$')


def es_videoclip(titulo, obra=None):
    """Por el catálogo (género/sección/formato dice videoclip) o por el título
    con el artista entre paréntesis: «Canción (Artista)»."""
    obra = obra or {}
    if any('videoclip' in plano(str(obra.get(c) or '')).replace(' ', '')
           for c in ('genero', 'seccion', 'formato', 'categoria', 'tipo')):
        return True
    return bool(_ARTISTA.search(titulo or ''))


def obligatorias(titulo, obra=None):
    return FUENTES_OBLIGATORIAS + (FUENTES_VIDEOCLIP if es_videoclip(titulo, obra) else ())


def revisada(f):
    """Una fuente cuenta si tiene URL, o si es N/A con su porqué."""
    f = f or {}
    return bool(str(f.get('url') or '').strip()) or bool(f.get('na') and str(f.get('por_que') or '').strip())


def faltantes(e, titulo, obra=None):
    """Lo que le falta a una entrada del registro para estar COMPLETA."""
    e = e or {}
    est = e.get('estado')
    if est not in ESTADOS:
        out = ['estado']
    else:
        out = []
    if est in CON_FICHA:
        return out if e.get('tmdb_id') else out + ['tmdb_id']
    out += [k for k in obligatorias(titulo, obra) if not revisada((e.get('fuentes') or {}).get(k))]
    if est in ('alta_posible', 'afiche_chico'):
        a = e.get('afiche') or {}
        if not (a.get('url') and a.get('fuente') and a.get('ratio')):
            out.append('afiche')
        elif est == 'alta_posible' and (a.get('veredicto_criterio') or
                                        not RATIO[0] <= a['ratio'] <= RATIO[1]):
            out.append('afiche (no pasa el criterio)')
    return out


def pendientes(fid, raiz=REPO):
    """{título: [lo que falta]} de cada obra sin ficha cuya entrada no está completa."""
    reg = leer_registro(fid, raiz)['obras']
    out = {}
    for t in sin_ficha(fid, raiz):
        f = faltantes(reg.get(t), t, obra_catalogo(fid, t, raiz))
        if f:
            out[t] = f
    return out


# ── TMDB ────────────────────────────────────────────────────────────────────
def _tmdb(path, **params):
    """Punto único de red (los tests lo reemplazan)."""
    import lib
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')
    return lib.tmdb_get(path, key, **params) or {}


def _url_busqueda(q, anio=None):
    return ('https://www.themoviedb.org/search/movie?query=' + urllib.parse.quote(q)
            + (f'%20y%3A{anio}' if anio else ''))


def _int(v):
    m = re.search(r'\d+', str(v or ''))
    return int(m.group()) if m else None


def _verifica(obra, mid):
    """Candado de verificar-antes-de-alta / lib.ficha_verifica: director ✓ Y
    (año ±1 O duración ±3). → det o None."""
    import lib
    det = _tmdb(f'/movie/{mid}', language='en-US', append_to_response='credits')
    if not det:
        return None
    o = {'director': obra.get('director') or '', 'anio': _int(obra.get('anio')),
         'duracion_min': _int(obra.get('duracion_min'))}
    return det if (o['director'] and lib.ficha_verifica(o, det)) else None


def variantes(titulo, obra=None):
    obra = obra or {}
    v = []
    for q in (titulo, plano(titulo), re.split(r'\s*[:–—]\s*|\s+-\s+', titulo)[0],
              re.sub(r'\s*[\(\[].*?[\)\]]\s*', ' ', titulo).strip(),
              obra.get('titulo_original'), obra.get('title_en'), obra.get('titulo_en')):
        if q and q.strip() and q not in v:
            v.append(q.strip())
    return v


def sondar_obra(titulo, obra):
    """→ (fuentes, tmdb_id | None, por_que). Escribe tmdb_titulo, tmdb_alternos,
    tmdb_director e imdb (si el catálogo trae el id)."""
    import lib
    fuentes, anio = {}, _int(obra.get('anio'))
    hallada = [None, None]

    def probar(cands, via):
        for c in cands[:6]:
            if hallada[0]:
                return
            if _verifica(obra, c['id']):
                hallada[:] = [c['id'], f'{via}: TMDB {c["id"]} «{c.get("title") or c.get("name")}» — director ✓ y año/duración ✓']

    vs = variantes(titulo, obra)
    for clave, qs in (('tmdb_titulo', vs[:1]), ('tmdb_alternos', vs[1:])):
        vistos = []
        for q in qs:
            for extra in ({}, {'primary_release_year': anio} if anio else None):
                if extra is None:
                    continue
                res = _tmdb('/search/movie', query=q, include_adult='false', **extra).get('results') or []
                vistos.append(f'«{q}»{" " + str(anio) if extra else ""}: {len(res)} resultado(s)')
                probar(res, clave)
        if qs:
            fuentes[clave] = {'url': _url_busqueda(qs[0], anio), 'fecha': hoy(),
                              'resultado': '; '.join(vistos) + (f' → {hallada[1]}' if hallada[0] else ' → ninguna verifica')}
        else:
            fuentes[clave] = {'na': True, 'por_que': 'el título no tiene variantes (sin acentos, subtítulo ni título original)', 'fecha': hoy()}

    dirs = [p.strip() for p in re.split(r',|\s+y\s+|\s*&\s*|/', obra.get('director') or '') if len(p.strip()) >= 4]
    urls, res_d = [], []
    for nombre in dirs:
        ps = [p for p in (_tmdb('/search/person', query=nombre).get('results') or [])[:3]
              if lib.director_coincide(nombre, [p.get('name', '')])]
        if not ps:
            res_d.append(f'{nombre}: sin perfil en TMDB')
            urls.append('https://www.themoviedb.org/search/person?query=' + urllib.parse.quote(nombre))
        for p in ps:
            urls.append(f'https://www.themoviedb.org/person/{p["id"]}')
            obras_p = []
            for cr in ('movie_credits', 'tv_credits'):
                obras_p += [m for m in (_tmdb(f'/person/{p["id"]}/{cr}').get('crew') or [])
                            if m.get('job') == 'Director']
            res_d.append(f'{p.get("name")} ({p["id"]}): dirige {len(obras_p)}')
            cerca = [m for m in obras_p if plano(m.get('title') or m.get('name')) in {plano(x) for x in vs}
                     or any(plano(x) and plano(x) in plano(m.get('title') or m.get('name') or '') for x in vs)]
            probar([m for m in cerca if m.get('title')], 'tmdb_director')
    if dirs:
        fuentes['tmdb_director'] = {'url': ' '.join(urls), 'fecha': hoy(),
                                    'resultado': '; '.join(res_d) + (f' → {hallada[1]}' if hallada[0] else '')}

    imdb = obra.get('imdb') or obra.get('imdb_id')
    if imdb and re.match(r'tt\d+', str(imdb)):
        r = _tmdb(f'/find/{imdb}', external_source='imdb_id').get('movie_results') or []
        probar(r, 'imdb')
        fuentes['imdb'] = {'url': f'https://www.imdb.com/title/{imdb}/', 'fecha': hoy(),
                           'resultado': f'/find: {len(r)} ficha(s) TMDB' + (f' → {hallada[1]}' if hallada[0] else '')}
    return fuentes, hallada[0], hallada[1]


def _escribir_ficha(fid, titulo, tmdb_id, por_que, raiz):
    """La ficha en <fid>-correcciones.json `fichas`, con referencia al registro."""
    p = os.path.join(_st(raiz), f'{fid}-correcciones.json')
    c = _leer(p)
    fichas = c.setdefault('fichas', {})
    if any(plano(t) == plano(titulo) for t in fichas):
        return False
    fichas[titulo] = {'tmdb': int(tmdb_id), '_fuente': f'https://www.themoviedb.org/movie/{tmdb_id}',
                      '_por_que': por_que, '_registro': f'{fid}-altas.json'}
    json.dump(c, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return True


def sondar(fid, raiz=REPO):
    reg = leer_registro(fid, raiz)
    n_ex = 0
    for t in sin_ficha(fid, raiz):
        e = reg['obras'].setdefault(t, {'titulo': t})
        if e.get('estado') in CON_FICHA:
            continue
        obra = obra_catalogo(fid, t, raiz)
        e['director'] = obra.get('director') or e.get('director') or ''
        fu, mid, por_que = sondar_obra(t, obra)
        e.setdefault('fuentes', {}).update(fu)
        if mid:
            e.update(estado='ficha_existente', tmdb_id=mid)
            _escribir_ficha(fid, t, mid, f'altas.py --sondar: {por_que}', raiz)
            n_ex += 1
    escribir_registro(fid, reg, raiz)
    return n_ex


def _entrada(reg, titulo):
    t = nfc(titulo)
    for k in reg['obras']:
        if plano(k) == plano(t):
            return reg['obras'][k]
    return reg['obras'].setdefault(t, {'titulo': t})


def anotar_fuente(fid, titulo, clave, url=None, resultado='', por_que=None, raiz=REPO):
    if clave not in FUENTES_OBLIGATORIAS + FUENTES_VIDEOCLIP:
        sys.exit(f'clave desconocida: {clave} (las de FUENTES_OBLIGATORIAS)')
    reg = leer_registro(fid, raiz)
    e = _entrada(reg, titulo)
    if por_que is not None:
        if not por_que.strip():
            sys.exit('N/A sin porqué no cuenta')
        f = {'na': True, 'por_que': por_que, 'fecha': hoy()}
    else:
        if not re.match(r'https?://', url or ''):
            sys.exit('la fuente necesita una URL http(s)')
        f = {'url': url, 'fecha': hoy(), 'resultado': resultado}
    e.setdefault('fuentes', {})[clave] = f
    escribir_registro(fid, reg, raiz)


def marcar_sin_afiche(fid, titulo, por_que, raiz=REPO):
    reg = leer_registro(fid, raiz)
    e = _entrada(reg, titulo)
    e.update(estado='sin_afiche', por_que_sin_afiche=por_que)
    escribir_registro(fid, reg, raiz)


def _descargar(url, destino):
    if os.path.exists(url):
        import shutil
        shutil.copy(url, destino)
        return
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=40) as r, open(destino, 'wb') as f:
        f.write(r.read())


def encuadrar(origen, destino, objetivo=2 / 3):
    """JPG con ancho/alto dentro de RATIO; si no lo está, RECORTE CENTRADO a
    `objetivo`. → (px, ratio, recorte | None)."""
    from PIL import Image
    im = Image.open(origen).convert('RGB')
    w, h = im.size
    r, recorte = w / h, None
    if not RATIO[0] <= r <= RATIO[1]:
        if r > RATIO[1]:
            nw = round(h * objetivo)
            x = (w - nw) // 2
            box = (x, 0, x + nw, h)
        else:
            nh = round(w / objetivo)
            y = (h - nh) // 2
            box = (0, y, w, y + nh)
        im = im.crop(box)
        recorte = {'de': [w, h], 'caja': list(box), 'centrado': True, 'objetivo': round(objetivo, 4)}
    im.save(destino, 'JPEG', quality=90)
    return [im.width, im.height], round(im.width / im.height, 4), recorte


def preparar(fid, titulo, url, fuente, raiz=REPO):
    """Afiche → fuentes/<fid>/altas/, por afiche_criterio, JPG y proporción;
    título NFC; JSON para los helpers del skill tmdb-alta (wiz/personas/alta)."""
    import lib
    from afiche_criterio import veredicto
    reg = leer_registro(fid, raiz)
    e = _entrada(reg, titulo)
    t = nfc(e.get('titulo') or titulo)
    if e.get('estado') in CON_FICHA:
        sys.exit(f'«{t}» ya tiene ficha ({e.get("estado")} {e.get("tmdb_id")})')
    obra = obra_catalogo(fid, t, raiz)
    d = os.path.join(raiz, 'fuentes', fid, 'altas')
    os.makedirs(d, exist_ok=True)
    s = lib.slug(t)
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or '.img'
    orig = os.path.join(d, f'{s}-original{ext}')
    _descargar(url, orig)
    jpg = os.path.join(d, f'{s}.jpg')
    px, ratio, recorte = encuadrar(orig, jpg)
    v = veredicto(jpg)
    e['titulo'] = t
    e['afiche'] = {'url': url, 'fuente': fuente, 'archivo': os.path.relpath(jpg, raiz), 'px': px,
                   'ratio': ratio, 'recorte': recorte, 'veredicto_criterio': v, 'fecha': hoy()}
    if v:
        e['estado'] = 'sin_afiche'
    elif px[0] < MIN_PX[0] or px[1] < MIN_PX[1]:
        e['estado'] = 'afiche_chico'
    else:
        e['estado'] = 'alta_posible'
    dirs = [p.strip() for p in re.split(r',|\s+y\s+|\s*&\s*|/', obra.get('director') or e.get('director') or '') if p.strip()]
    salida = {
        'titulo': t, 'estado': e['estado'], 'poster': os.path.relpath(jpg, raiz),
        'wiz': {'title': t, 'synopsis': (obra.get('sinopsis_en') or obra.get('synopsis_en')
                                         or obra.get('sinopsis') or '')[:1000],
                'runtime': _int(obra.get('duracion_min')) or ''},
        'personas': {n: 'Director' for n in dirs},
        'alta': {'countries': [x for x in re.split(r'[,/]\s*', str(obra.get('pais') or '')) if x],
                 'crew': [['Director', n, ''] for n in dirs],
                 'rel': ([{'anio': _int(obra.get('anio')), 'tipo': 1, 'nota': fid}] if obra.get('anio') else [])},
    }
    json.dump(salida, open(os.path.join(d, f'{s}.tmdb.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    escribir_registro(fid, reg, raiz)
    return salida


def registrar_alta(fid, titulo, tmdb_id, raiz=REPO):
    reg = leer_registro(fid, raiz)
    e = _entrada(reg, titulo)
    if e.get('estado') not in ('alta_posible', 'afiche_chico', 'sin_afiche'):
        sys.exit(f'«{titulo}» no está para alta (estado {e.get("estado")}): primero --preparar')
    e.update(estado='alta_hecha', tmdb_id=int(tmdb_id), alta_fecha=hoy())
    _escribir_ficha(fid, e['titulo'], tmdb_id,
                    f'alta en TMDB hecha por nosotros el {hoy()} (registro {fid}-altas.json)', raiz)
    escribir_registro(fid, reg, raiz)


# ── guardianes (validate.py) ─────────────────────────────────────────────────
def por_salir(raiz=REPO):
    import preonboarding
    out = []
    for p in sorted(glob.glob(os.path.join(_st(raiz), '*-catalogo.json'))):
        fid = os.path.basename(p)[:-len('-catalogo.json')]
        if os.path.exists(os.path.join(raiz, 'pipeline', f'{fid}.plan.json')) \
                and preonboarding._publicadas(fid, raiz) is None:
            out.append(fid)
    return out


def medir_sin_evidencia(raiz=REPO):
    return {fid: sorted(pendientes(fid, raiz)) for fid in por_salir(raiz)}


def fichas_sin_registro(raiz=REPO):
    """{fid: [títulos en `fichas` sin entrada ficha_existente/alta_hecha en el registro]}"""
    out = {}
    for p in sorted(glob.glob(os.path.join(_st(raiz), '*-correcciones.json'))):
        fid = os.path.basename(p)[:-len('-correcciones.json')]
        reg = {plano(t): e for t, e in leer_registro(fid, raiz)['obras'].items()}
        malas = [t for t, v in (_leer(p).get('fichas') or {}).items()
                 if not ((reg.get(plano(t)) or {}).get('estado') in CON_FICHA
                         and str((reg.get(plano(t)) or {}).get('tmdb_id')) == str((v or {}).get('tmdb')))]
        if malas:
            out[fid] = malas
    return out


def titulos_no_nfc(raiz=REPO):
    """[(archivo, título)] de crudos y catálogos de staging con título no NFC."""
    out = []

    def walk(x, p):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ('titulo', 'title') and isinstance(v, str) and nfc(v) != v:
                    out.append((os.path.basename(p), v))
                walk(v, p)
        elif isinstance(x, list):
            for v in x:
                walk(v, p)
    for p in sorted(glob.glob(os.path.join(_st(raiz), '*crudo*.json'))
                    + glob.glob(os.path.join(_st(raiz), '*-catalogo*.json'))
                    + glob.glob(os.path.join(_st(raiz), '*-altas.json'))):
        try:
            walk(_leer(p), p)
        except ValueError:
            pass
    return out


def deuda(raiz=REPO):
    p = os.path.join(raiz, 'pipeline', 'altas-deuda.json')
    d = _leer(p)
    for k in ('alta_sin_evidencia', 'fichas_sin_registro', 'titulos_no_nfc'):
        d.setdefault(k, {} if k != 'titulos_no_nfc' else [])
    return d


def verificar(raiz=REPO):
    """→ {guardián: [problemas]} por ENCIMA de la deuda congelada."""
    dd = deuda(raiz)
    m = medir_sin_evidencia(raiz)
    sin_ev = [f'{f}: {len(v)} sin evidencia completa (deuda {dd["alta_sin_evidencia"].get(f, 0)}; p. ej. {", ".join(v[:3])})'
              for f, v in m.items() if len(v) > dd['alta_sin_evidencia'].get(f, 0)]
    fs = []
    for f, v in fichas_sin_registro(raiz).items():
        congeladas = {plano(t) for t in dd['fichas_sin_registro'].get(f, [])}
        fs += [f'{f}: «{t}»' for t in v if plano(t) not in congeladas]
    cong = {(a, b) for a, b in dd['titulos_no_nfc']}
    nn = [f'{a}: «{b}»' for a, b in titulos_no_nfc(raiz) if (a, b) not in cong]
    return {'alta-sin-evidencia': sin_ev, 'ficha-sin-registro': fs, 'titulo-nfc': nn}


def congelar(raiz=REPO):
    """Escribe la deuda inicial (o la baja: nunca la sube)."""
    p = os.path.join(raiz, 'pipeline', 'altas-deuda.json')
    previa = _leer(p)
    m = {f: len(v) for f, v in medir_sin_evidencia(raiz).items() if v}
    fs = fichas_sin_registro(raiz)
    nn = [list(x) for x in titulos_no_nfc(raiz)]
    if previa:
        pa = previa.get('alta_sin_evidencia', {})
        m = {f: min(n, pa.get(f, 0)) for f, n in m.items() if min(n, pa.get(f, 0))}
        pf = previa.get('fichas_sin_registro', {})
        fs = {f: [t for t in v if t in pf.get(f, [])] for f, v in fs.items()}
        fs = {f: v for f, v in fs.items() if v}
        pn = [list(x) for x in previa.get('titulos_no_nfc', [])]
        nn = [x for x in nn if x in pn]
    json.dump({'_nota': 'deuda de los guardianes del registro de altas (pipeline/altas.py); solo baja: '
                        'python3 pipeline/altas.py --bajar-deuda',
               'alta_sin_evidencia': m, 'fichas_sin_registro': fs, 'titulos_no_nfc': nn},
              open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def _arg(flag, n=1):
    i = sys.argv.index(flag)
    v = sys.argv[i + 1:i + 1 + n]
    if len(v) < n:
        sys.exit(f'{flag}: faltan argumentos')
    return v if n > 1 else v[0]


def main():
    if '--bajar-deuda' in sys.argv:
        congelar()
        print('✓ deuda bajada (pipeline/altas-deuda.json)')
        return
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    fid = sys.argv[1]
    a = sys.argv
    if '--sondar' in a:
        n = sondar(fid)
        print(f'✓ {fid}: {len(sin_ficha(fid))} sin ficha sondeadas · {n} con ficha existente (escritas en `fichas`)')
    if '--fuente' in a:
        t, k, u = _arg('--fuente', 3)
        anotar_fuente(fid, t, k, url=u, resultado=_arg('--resultado') if '--resultado' in a else '')
    if '--na' in a:
        t, k = _arg('--na', 2)
        anotar_fuente(fid, t, k, por_que=_arg('--por-que') if '--por-que' in a else '')
    if '--sin-afiche' in a:
        marcar_sin_afiche(fid, _arg('--sin-afiche'), _arg('--por-que'))
    if '--preparar' in a:
        print(json.dumps(preparar(fid, _arg('--preparar'), _arg('--url'), _arg('--origen')),
                         ensure_ascii=False, indent=1))
    if '--registrar-alta' in a:
        t, i = _arg('--registrar-alta', 2)
        registrar_alta(fid, t, i)
        print(f'✓ alta_hecha y ficha escrita en {fid}-correcciones.json')
    if '--pendientes' in a:
        p = pendientes(fid)
        for t, f in p.items():
            print(f'{t}\n    falta: {", ".join(f)}')
        print(f'— {len(p)} obra(s) con evidencia incompleta de {len(sin_ficha(fid))} sin ficha')


if __name__ == '__main__':
    main()
