#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sello_fuente.py — el original de una sinopsis está, letra por letra, donde dice que está.

POR QUÉ (auditoría del 25 nov 2026): de 896 obras selladas, 118 citaban como fuente
del original una página que no lo trae; 63 decían «TMDB» y TMDB no tenía ese texto
en ese idioma (era una traducción nuestra). El sello lo firmaba un lector que decía
haberlo comprobado. Ahora lo comprueba la máquina antes de sellar.

QUÉ LEE, según la fuente citada (puede haber varias, separadas por « · »):
  · TMDB (themoviedb.org/movie/<id>): todas las traducciones, por la API (TMDB_API_KEY).
  · una URL: la página (o el PDF) tal como llega, sin etiquetas.
  · Instagram: la copia del vigía en Otrofestiv-fuentes/ig-vigia, o el embed público.
  · una ruta del repo o de Otrofestiv-fuentes (fuentes/…): el archivo.
Un «[…]» del original separa fragmentos: cada uno tiene que estar, en orden indiferente.
Mayúsculas, tildes compuestas, comillas y puntuación no cuentan; las palabras sí.

    comprobar({texto, idioma, fuente}, obra={titulos, directores, tmdb})
        → ('literal' | 'no está' | 'ilegible' | 'no vale', dónde)
ATADO A LA OBRA (revisión senior, 25 nov 2026): en un catálogo con todas las obras, la
sinopsis de otra pasaba. Ahora el texto vale si la fuente es de ESTA obra: TMDB con su
número, o su título o el apellido de quien la dirige cerca del texto. El propio almacén
(catalogo/, festivals/, pipeline/) no es fuente.
"""
import html
import json
import os
import re
import subprocess
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.expanduser('~/Developer/Otrofestiv-fuentes')
NAVEGADOR = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15'
# webs que no se dejan bajar (las arma JavaScript o bloquean): se lee la copia guardada
# del festival en Otrofestiv-fuentes/<carpeta>. Cuenta solo si UN archivo trae todo el texto
# y el título de la obra cerca: si no, pasaría la sinopsis de otra obra del mismo festival.
COPIAS = {'info.bogoshorts.com': 'bogoshorts-2026', 'bogoshorts.com': 'bogoshorts-2026', 'ficcifestival.com': 'ficci-65'}
_copias = {}
# Una página que dice «bloqueado» o pide sesión no se leyó: no puede probar que el texto
# no está (FilmAffinity devuelve Cloudflare; Facebook y YouTube, su portada).
BLOQUEO = ('attention required', 'you have been blocked', 'enable javascript', 'just a moment', 'captcha',
           'access denied', 'iniciar sesión', 'log in or sign up', 'inicia sesión para', 'before you continue')
DETRAS_DE_SESION = ('facebook.com', 'fb.watch', 'youtube.com', 'youtu.be', 'filmfreeway.com', 'eventive.org', 'vimeo.com')
CERCA = 3000            # caracteres entre el título y el texto, dentro de un archivo de la copia
PALABRAS = 4            # un fragmento más corto que esto casa en cualquier página
MINIMO = 400            # menos texto que esto no es una página leída (bloqueo, captcha, vacío)


def plano(t):
    t = unicodedata.normalize('NFKC', html.unescape(t or '')).replace('\xad', '')
    return re.sub(r'\W+', ' ', t).lower().strip()


CUBRE = 0.9             # los fragmentos que se buscan cubren al menos esto de las palabras del original


def fragmentos(texto):
    """Los trozos del original separados por «[…]», de PALABRAS o más. Si los que se
    descartan por cortos pesan más de 1 − CUBRE, ninguno ([]): un trozo genérico no
    puede cargar con un original inventado."""
    todos = [plano(x) for x in re.split(r'\[…\]|\[\.\.\.\]|\(…\)|\(\.\.\.\)', texto or '')]
    fr = [x for x in todos if len(x.split()) >= PALABRAS]
    n = sum(len(x.split()) for x in todos)
    return fr if n and sum(len(x.split()) for x in fr) >= CUBRE * n else []


class SinLeer(Exception):
    """No se pudo consultar la fuente (sin clave, sin red): no prueba nada, ni deja sellar a mano."""


def _de_html(t):
    t = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), t).replace('\\n', ' ')
    return re.sub(r'<[^>]+>', ' ', t)


def _pdf(b):
    return subprocess.run(['pdftotext', '-', '-'], input=b, capture_output=True, timeout=120).stdout.decode(errors='replace').replace('-\n', '')


_web = {}


def leer_web(u):
    """La página (o PDF) en texto; una vez por URL y corrida. '' si no se leyó."""
    if u not in _web:
        _web[u] = _bajar(u)
    return _web[u]


def _bajar(u):
    r = subprocess.run(['curl', '-sL', '--max-time', '240', '-A', NAVEGADOR, '-w', '\n%{http_code} %{url_effective}', u],
                       capture_output=True, timeout=300)
    b, _, cola = r.stdout.rpartition(b'\n')
    if r.returncode in (6, 7, 28, 35, 52, 56):     # sin red, sin respuesta, tiempo agotado
        raise SinLeer(f'curl {r.returncode} en {u}')
    codigo, _, final = cola.decode(errors='replace').partition(' ')
    # un error o una redirección a la portada no es la página citada: no se leyó
    if not codigo.startswith('2') or (re.sub(r'^https?://[^/]+', '', final).strip('/') == '' and re.sub(r'^https?://[^/]+', '', u).strip('/')):
        return ''
    return _pdf(b) if b[:4] == b'%PDF' else _de_html(b.decode(errors='replace'))


def _cadenas(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _cadenas(v)
    elif isinstance(x, list):
        for v in x:
            yield from _cadenas(v)


def leer_local(p):
    for q in (os.path.join(REPO, p), os.path.join(FUENTES, re.sub(r'^fuentes/', '', p))):
        q = os.path.realpath(q)
        if not q.startswith((os.path.realpath(REPO) + os.sep, os.path.realpath(FUENTES) + os.sep)):
            continue
        if os.path.isfile(q):
            with open(q, 'rb') as fh:
                b = fh.read()
            if q.lower().endswith('.json'):     # «río» no es «río»: el JSON se lee decodificado
                try:
                    return _de_html('\n'.join(_cadenas(json.loads(b.decode(errors='replace')))))
                except ValueError:
                    pass
            return _pdf(b) if b[:4] == b'%PDF' else _de_html(b.decode(errors='replace'))
    return ''


def leer_tmdb(i, clave):
    import urllib.request
    if not clave:
        raise SinLeer('falta TMDB_API_KEY')
    u = f'https://api.themoviedb.org/3/movie/{i}/translations'
    h = {'Authorization': 'Bearer ' + clave} if len(clave) > 40 else {}
    if not h:
        u += '?api_key=' + clave
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
            d = json.load(r)
    except Exception as e:
        if getattr(e, 'code', None) == 404:
            return [('', '')]           # el id no existe: se leyó, y el texto no está
        raise SinLeer(f'TMDB {i}: {e}')
    return [(t['iso_639_1'], t['data'].get('overview') or '') for t in d.get('translations') or []]


def leer_instagram(codigo):
    import glob
    for q in glob.glob(os.path.join(FUENTES, 'ig-vigia', f'*{codigo}*.json')) + glob.glob(os.path.join(FUENTES, '*', f'ig-{codigo}.json')):
        return leer_local(q)
    return leer_web(f'https://www.instagram.com/p/{codigo}/embed/captioned/')


def leer_copia(carpeta):
    """→ {archivo: texto plano} de la copia guardada."""
    import glob
    if carpeta not in _copias:
        out = {}
        for p in sorted(glob.glob(os.path.join(FUENTES, carpeta, '**', '*'), recursive=True)):
            if os.path.isfile(p) and p.endswith(('.pdf', '.html', '.htm', '.json', '.txt', '.csv')) and os.path.getsize(p) < 3e7:
                out[os.path.relpath(p, FUENTES)] = plano(leer_local(p))
        _copias[carpeta] = out
    return _copias[carpeta]


def _en(fr, t):
    """¿Todos los fragmentos, con borde de palabra, en el texto plano t?"""
    t = ' ' + t + ' '
    return bool(fr) and all(' ' + f + ' ' in t for f in fr)


# Un título de una sola palabra corriente («Ella», «Madre», «La») aparece suelto en cualquier
# sinopsis: no ata un texto a una obra. Uno de una palabra cuenta si es largo y raro.
CORRIENTES = set('''ella el la los las madre padre hijo hija casa mar agua tierra noche dia luz vida amor
fuego viento cielo sol luna rio ciudad pueblo campo calle camino viaje tiempo memoria cuerpo mujer hombre
nina nino hermana hermano familia sueño sueno silencio sombra raiz raices hogar regreso origen
mother father home love night water life light land house'''.split())


def apellido(nombre):
    """El apellido de una persona (la última palabra larga): el nombre de pila no ata."""
    p = plano(nombre)
    if any(x in p.split() for x in ('colectivo', 'varios', 'directores', 'directoras', 'taller', 'escuela', 'comunidad', 'grupo')):
        return ''                                   # un colectivo no tiene apellido: ancla el título
    ws = [w for w in p.split() if len(w) >= 4]
    return ws[-1] if ws else ''


def _titulo_ancla(t):
    p = plano(t)
    if len(p.split()) == 1 and (len(p) < 6 or p in CORRIENTES):
        return ''
    return p if len(p) >= 3 else ''


def anclas(obra):
    """Lo que dice que un texto es de ESTA obra: sus títulos (no los de una palabra corriente)
    y el apellido de quien la dirige."""
    out = {_titulo_ancla(t) for t in (obra.get('titulos') or [])}
    out |= {_titulo_ancla(t).replace(' ', '') for t in (obra.get('titulos') or [])}   # «Lez-Ama» / «LezAma»
    out |= {apellido(d) for d in obra.get('directores') or []}
    return {a for a in out if a}


_titulos = None


def titulos_del_almacen():
    """Los títulos de todas las obras (catalogo/obras), planos: para saber de quién es un texto
    en un catálogo de muchas."""
    global _titulos
    if _titulos is None:
        import glob
        out = set()
        for p in glob.glob(os.path.join(REPO, 'catalogo', 'obras', '*.json')):
            with open(p, encoding='utf-8') as fh:
                o = json.load(fh)
            for t in [o.get('titulo_original'), *(o.get('titulos') or [])]:
                if t and _titulo_ancla(t):
                    out.add(_titulo_ancla(t))
            out |= {apellido(d) for d in o.get('directores') or [] if apellido(d)}      # la dirección de otra obra compite
        _titulos = out
    return _titulos


def _cerca(fr, anc, t, ajenas=()):
    """El texto es de esta obra: dentro de CERCA del primer fragmento hay un ancla suya, y el
    título de obra MÁS CERCANO al texto es suyo, no el de otra del mismo catálogo."""
    if not anc or not _en(fr, t):
        return False
    t = ' ' + t + ' '
    i = t.find(' ' + fr[0] + ' ')
    fin = i + len(fr[0]) + 1

    def dist(a):
        k = t.rfind(' ' + a + ' ', max(0, i - CERCA), i + 1)
        j = t.find(' ' + a + ' ', fin, fin + CERCA)
        return min([i - k for k in [k] if k >= 0] + [j - fin for j in [j] if j >= 0] or [None]) if (k >= 0 or j >= 0) else None
    mia = [(d, -len(a)) for a in anc for d in [dist(a)] if d is not None]
    if not mia:
        return False
    # ante el empate gana el título más largo: «El abrazo de la serpiente» le gana a «El abrazo»
    otra = [(d, -len(a)) for a in set(ajenas) - set(anc) for d in [dist(a)] if d is not None]
    return not otra or min(mia) <= min(otra)


PROPIAS = ('catalogo/', 'festivals/', 'pipeline/')     # el almacén no prueba lo que dice el almacén


def comprobar(original, leer=None, obra=None):
    """→ (estado, dónde): 'literal', 'no está', 'ilegible' o 'no vale'.

    `obra` = {titulos, directores, tmdb}. El texto cuenta solo si está en la fuente Y la fuente
    es de esta obra: TMDB con el número de la obra, o una página donde aparece su título o el
    apellido de quien la dirige cerca del texto. Si el texto está pero nada lo ata a la obra,
    'ilegible' (lo dice una persona). Sin red o sin clave, SinLeer."""
    leer = leer or {'web': leer_web, 'local': leer_local, 'tmdb': lambda i: leer_tmdb(i, os.environ.get('TMDB_API_KEY') or ''),
                    'instagram': leer_instagram, 'copia': leer_copia}
    obra = obra if isinstance(obra, dict) else {'titulos': [obra] if obra else []}
    fr, fuente, visto, suelto = fragmentos(original.get('texto') or ''), original.get('fuente') or '', [], []
    if not fr:
        return 'no está', f'el original tiene menos de {PALABRAS} palabras seguidas'
    anc = anclas(obra)
    ajenas = obra.get('ajenas') if 'ajenas' in obra else titulos_del_almacen()
    if any(re.match(r'\s*' + p, x.strip()) for p in PROPIAS for x in fuente.split('·')):
        return 'no vale', 'la fuente es el propio almacén'
    for i in re.findall(r'themoviedb\.org/movie/(\d+)', fuente):
        if obra.get('tmdb') and str(obra['tmdb']) != i:
            visto.append(f'TMDB {i} no es la ficha de la obra ({obra["tmdb"]})')
            continue
        ts = leer['tmdb'](i)
        if ts:
            visto.append(f'TMDB {i}')
        # un original «es y en» trae un párrafo por idioma: cada párrafo, entero, en alguna traducción
        parrafos = [fragmentos(x) for x in re.split(r'\n\s*\n|\n', original.get('texto') or '') if fragmentos(x)]
        if parrafos and all(any(_en(q, plano(t)) for _, t in ts) for q in parrafos):
            if obra.get('tmdb'):
                return 'literal', f'TMDB {i}'
            suelto.append(f'TMDB {i}, sin número de TMDB en la obra para atarlo')

    def mirar(t, donde):
        p = plano(t)
        if _cerca(fr, anc, p, ajenas):
            return 'literal'
        if _en(fr, p):
            suelto.append(f'{donde}: el texto está, pero ni el título ni la dirección cerca')
    for u in re.findall(r'https?://[^\s·]+', fuente):
        u = u.rstrip('.,;:')
        if u.endswith(')') and u.count('(') < u.count(')'):
            u = u[:-1]
        if 'themoviedb.org' in u:
            continue
        m = re.search(r'instagram\.com/(?:p|reel)/([\w-]+)', u)
        dom = re.sub(r'^https?://(www\.)?([^/]+).*', r'\2', u)
        try:
            t = leer['instagram'](m[1]) if m else leer['web'](u)
        except SinLeer:
            if dom not in COPIAS:                # sin copia guardada, no hay con qué
                raise
            t = ''                               # la web no responde: se mira la copia
        if t and mirar(t, u):
            return 'literal', u
        # Instagram: el texto suele estar en una lámina (imagen) del carrusel, que esto no lee
        if len(plano(t)) >= MINIMO and not m and not any(b in plano(t)[:3000] for b in BLOQUEO) \
                and not any(d in u for d in DETRAS_DE_SESION):
            visto.append(u)
        if dom in COPIAS and 'copia' in leer:
            c = leer['copia'](COPIAS[dom])
            for archivo, x in sorted(c.items()):
                if _cerca(fr, anc, x, ajenas):
                    return 'literal', f'{u} (copia guardada: fuentes/{archivo})'
            if any(_en(fr, x) for x in c.values()):
                suelto.append(f'copia de {dom}: el texto está, pero ni el título ni la dirección cerca')
            elif c:
                visto.append(f'copia de {dom}')
    for p in re.findall(r'(?:^|\s)(fuentes/[^\s·,()]+)', fuente):
        t = leer['local'](p.rstrip('.'))
        if t and mirar(t, p):
            return 'literal', p
        if len(plano(t)) >= MINIMO:            # una imagen o un archivo vacío no se leyó
            visto.append(p)
    if suelto:
        return 'ilegible', ' · '.join(suelto)
    return ('no está', ' · '.join(visto)) if visto else ('ilegible', fuente[:120])


def autoprueba():
    """[] = la comprobación ve."""
    T = 'Una mujer vuelve a su pueblo, y encuentra un hotel. '
    pag = 'x ' * 300 + 'Mi título. ' + T + 'y ' * 300
    L = {'web': lambda u: pag if 'bien' in u else ('x ' * 300 if 'otra' in u else ''), 'local': lambda p: '',
         'tmdb': lambda i: [('en', 'A woman returns.')], 'instagram': lambda c: ''}
    o = {'texto': 'Una mujer vuelve a su pueblo y encuentra un hotel.', 'idioma': 'es'}
    ob = {'titulos': ['Mi título'], 'directores': ['Ana Restrepo'], 'tmdb': 1, 'ajenas': {'otra obra', 'la vecina'}}
    c = lambda fuente, leer=L, obra=ob, **k: comprobar(dict(o, fuente=fuente, **k), leer, obra)[0]
    mal = []
    if c('https://bien.co') != 'literal':
        mal.append('no ve el texto que está')
    if c('https://bien.co', dict(L, web=lambda u: 'x ' * 300 + 'Restrepo dirige. ' + T)) != 'literal':
        mal.append('no ata la obra por el apellido de quien la dirige')
    if c('https://bien.co', dict(L, web=lambda u: 'x ' * 300 + 'Otra obra. ' + T)) != 'ilegible':
        mal.append('acepta un texto que nada ata a esta obra (catálogo de varias)')
    if c('https://otra.co') != 'no está':
        mal.append('no ve que no está')
    if c('https://www.themoviedb.org/movie/1') != 'no está':
        mal.append('da por bueno lo que TMDB no tiene')
    if c('https://www.themoviedb.org/movie/1', dict(L, tmdb=lambda i: [('en', o['texto'])]), idioma='es y en') != 'literal':
        mal.append('no ve el texto en la ficha de TMDB de la obra')
    if c('https://www.themoviedb.org/movie/2', dict(L, tmdb=lambda i: [('en', o['texto'])])) == 'literal':
        mal.append('acepta la ficha de TMDB de otra obra')
    if c('catalogo/originales.json') != 'no vale' or c('https://bien.co · festivals/x.json') != 'no vale':
        mal.append('el almacén se prueba a sí mismo')
    if c('https://vacia.co') != 'ilegible':
        mal.append('llama «no está» a lo que no pudo leer')
    if c('https://bloqueo.co', dict(L, web=lambda u: 'Attention Required! ' + 'x ' * 400)) != 'ilegible':
        mal.append('toma una página de bloqueo por leída')
    if c('https://www.instagram.com/p/AbC/', dict(L, instagram=lambda q: 'x ' * 400)) != 'ilegible':
        mal.append('da por ausente lo que puede estar en una lámina')
    copia = dict(L, web=lambda u: '', copia=lambda q: {'a.html': plano('Otra obra ' + 'z ' * 900 + T), 'b.html': plano('Mi título. ' + T)})
    if c('https://info.bogoshorts.com/x', copia) != 'literal':
        mal.append('no lee la copia guardada')
    if c('https://info.bogoshorts.com/x', copia, {'titulos': ['Otra cosa'], 'ajenas': set()}) != 'ilegible':
        mal.append('acepta en la copia un texto lejos de la obra, o da «no está» si está con otro título')
    if c('https://info.bogoshorts.com/x', dict(copia, copia=lambda q: {'b.html': plano('Mi título. Nada que ver.')})) != 'no está':
        mal.append('no ve que el texto no está en la copia')
    if c('https://info.bogoshorts.com/x', dict(copia, copia=lambda q: {'b.html': plano('Evadir. ' + T)}), {'titulos': ['Eva'], 'ajenas': set()}) == 'literal':
        mal.append('casa el título a mitad de palabra')
    dos = 'Una mujer vuelve a su pueblo y encuentra un hotel.\n\nA woman goes back to her town and finds a hotel.'
    if c('https://www.themoviedb.org/movie/1', dict(L, tmdb=lambda i: [('es', o['texto']), ('en', 'A woman goes back to her town and finds a hotel.')]), texto=dos) != 'literal':
        mal.append('no admite un original con un párrafo por idioma')
    if c('https://www.themoviedb.org/movie/1', dict(L, tmdb=lambda i: [('es', o['texto'])]), texto=dos) == 'literal':
        mal.append('acepta un párrafo que TMDB no tiene')
    caida = dict(copia, web=lambda u: (_ for _ in ()).throw(SinLeer('curl 28')))
    if c('https://info.bogoshorts.com/x', caida) != 'literal':
        mal.append('si la web no responde, no mira la copia guardada')
    try:
        c('https://www.themoviedb.org/movie/1', dict(L, tmdb=lambda i: (_ for _ in ()).throw(SinLeer('x'))))
        mal.append('sin clave o sin red responde en vez de parar')
    except SinLeer:
        pass
    if c('https://bien.co', dict(L, web=lambda u: pag.replace('pueblo', 'pueblos')), texto='Una mujer vuelve a su pueblo') == 'literal':
        mal.append('casa a mitad de palabra')
    cat = 'x ' * 300 + 'Mi título. Dirección: Ana Restrepo. Otro texto. El mar quieto. Dirección: Ana López. ' + T
    if c('https://bien.co', dict(L, web=lambda u: cat), {**ob, 'ajenas': {'el mar quieto', 'lopez'}}) == 'literal':
        mal.append('el nombre de pila de la dirección ata la sinopsis de otra obra')
    if c('https://bien.co', dict(L, web=lambda u: 'x ' * 300 + 'Ella. ' + T), {'titulos': ['Ella'], 'ajenas': set()}) == 'literal':
        mal.append('un título de una palabra corriente ata cualquier texto')
    vecina = 'x ' * 300 + 'Mi título. Su texto propio aquí. La vecina. ' + T
    if c('https://bien.co', dict(L, web=lambda u: vecina)) == 'literal':
        mal.append('en un catálogo, da por suya la sinopsis de la obra vecina')
    if c('https://bien.co', dict(L, web=lambda u: 'x ' * 300 + 'El abrazo de la serpiente. ' + T), {'titulos': ['El abrazo'], 'ajenas': {'el abrazo de la serpiente'}}) == 'literal':
        mal.append('un título que contiene el propio no compite')
    if c('https://bien.co', texto='…') == 'literal':
        mal.append('acepta un original sin palabras')
    if c('https://bien.co', texto='Inventado […] vuelve a su pueblo […] raro') == 'literal':
        mal.append('sella un original inventado con un trozo genérico')
    if c('https://bien.co', texto='Una mujer vuelve a su pueblo […] y encuentra un hotel.') != 'literal':
        mal.append('no admite fragmentos')
    return mal
