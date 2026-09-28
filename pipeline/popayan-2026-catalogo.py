#!/usr/bin/env python3
"""popayan-2026-catalogo.py — la Selección Oficial del 17 Festival de Cine Corto de Popayán → catálogo.

PRE-ONBOARDING (28 sep 2026, radar #573). El festival (5–11 oct) publicó su
Selección Oficial y todavía no la parrilla: la página `/programacion-2/` existe
desde hoy, pero solo trae los encabezados de dos días. Como Mamut: catálogo sin
crudo. Regla de Juan del mismo día: con cada festival se enriquecen los títulos
apenas se publiquen, y quedan pendientes solo horarios y lugares.

DOS FUENTES DEL PROPIO FESTIVAL, con papeles distintos:

  1. LA LISTA: festicinepopayan.com/fest2026/seleccion-oficial-2026/, leída por
     su `wp-json` (el HTML renderizado es el mismo contenido con más ruido).
     Da SECCIÓN, TÍTULO y el renglón «dirigido por … y producido por …».
     Las secciones son pestañas: el contenido trae los encabezados de a tres
     y DESPUÉS los tres párrafos, en el mismo orden. Se emparejan por orden y
     el conteo por sección se exige contra ESPERADAS.
  2. LA FICHA: cinecorto.co, su catálogo del cortometraje colombiano (lo
     enlaza el X del festival). Da AÑO y DURACIÓN —sin ellos el candado de TMDB
     no puede verificar nada—, además de categoría y sinopsis. Una ficha se
     acepta solo si su DIRECCIÓN casa con la de la lista: un título igual con
     otra dirección es otra obra.

Tres de las secciones se cruzan además contra los posts de IG @cinecortofest
(26–28 sep), que las publicaron por separado: Documental 11 (p/Ddw8j7eFjLn),
Comunitario 5 (p/DdwbC17FkJH), Experimental 10 (p/DdzNIGeloJ1).

LO QUE NO SE PUBLICA TODAVÍA. Los nombres de sección salen de la web en
mayúscula sostenida («SELECCIÓN OFICIAL CORTOMETRAJE AFRO»). Se guardan tal
cual en `seccion_fuente`; el nombre que se publica lo elige Juan al montar
(regla de caja sostenida). Sin afiches: cinecorto.co trae fotogramas, y un
fotograma no es un afiche.
"""
import html
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'popayan-2026'
SELECCION = 'https://festicinepopayan.com/wp-json/wp/v2/pages?slug=seleccion-oficial-2026&_fields=content,modified'
CINECORTO = 'https://cinecorto.co/wp-json/wp/v2'
CACHE = f'{REPO}/fuentes/{FID}'
DESTINO = f'{REPO}/festivals/staging/{FID}-catalogo.json'

ESPERADAS = {
    'SELECCIÓN OFICIAL CORTOMETRAJE AFRO': 6,
    'SELECCIÓN OFICIAL CORTOMETRAJE ANIMADO': 9,
    'SELECCIÓN OFICIAL CORTOMETRAJE COMUNITARIO': 5,     # = IG p/DdwbC17FkJH
    'SELECCIÓN OFICIAL CORTOMETRAJE DOCUMENTAL': 11,     # = IG p/Ddw8j7eFjLn
    'SELECCIÓN OFICIAL CORTOMETRAJE EXPERIMENTAL': 10,   # = IG p/DdzNIGeloJ1
    'SELECCIÓN OFICIAL CORTOMETRAJE INDÍGENA': 4,
    'SELECCIÓN OFICIAL CORTOMETRAJE INFANTIL': 10,
    'SELECCIÓN OFICIAL CORTOMETRAJE FICCIÓN': 12,
    'SELECCIÓN OFICIAL CORTOMETRAJE CAUCA': 10,
}

# DOS OBRAS EN UN RENGLÓN. En Ficción el `<br>` entre «Las piedras del río» y
# «Los Huyentes» falta, y el crédito de la primera sigue sin corte en el título
# de la segunda («…producido por Wilson Arango.Los Huyentes dirigido por…»).
# Tabla y no regla: partir por «.» + mayúscula rompería «Studio national des
# arts contemporains» o cualquier crédito con iniciales.
PEGADAS = {
    'Las piedras del río': ('producido por Wilson Arango.', 'Los Huyentes'),
}

# cinecorto.co no siempre tiene la obra, o la tiene con el título escrito de
# otra forma: la búsqueda se hace por título y se confirma por dirección.
BUSQUEDA = {}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def get_json(url, cache):
    p = f'{CACHE}/{cache}'
    if os.path.exists(p):
        return json.load(io.open(p, encoding='utf-8'))
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 Otrofestiv'})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, io.open(p, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(0.4)
    return d


def texto(h):
    return html.unescape(re.sub(r'<[^>]+>', '', h)).strip()


def credito(rest):
    """«dirigido por A y producido por B» / «dirigido y producido por A»."""
    r = rest.strip().rstrip('.').strip()
    m = re.match(r'dirigido y producido por (.+)$', r, re.I)
    if m:
        return m.group(1).strip(), m.group(1).strip()
    m = re.match(r'dirigido por (.+?)(?: y [Pp]roducido por (.+))?$', r)
    if m:
        return m.group(1).strip(), (m.group(2) or '').strip()
    sys.exit(f'✗ crédito sin forma conocida: {rest!r}')


def lista():
    c = get_json(SELECCION, 'seleccion-oficial-2026.json')[0]['content']['rendered']
    pend, out = [], []
    for h, p in re.findall(r'<h4[^>]*>(.*?)</h4>|<p[^>]*>(.*?)</p>', c, re.S):
        if h:
            pend.append(texto(h))
            continue
        if not p.strip():
            continue
        sec = pend.pop(0)
        for it in re.split(r'<br\s*/?>', p):
            m = re.match(r'\s*<strong>(.*?)</strong>(.*)', it, re.S)
            if not m:
                if texto(it):
                    sys.exit(f'✗ renglón sin título en negrita en {sec}: {texto(it)!r}')
                continue
            titulo, rest = texto(m.group(1)), texto(m.group(2))
            if titulo in PEGADAS:
                corte, segundo = PEGADAS[titulo]
                i = rest.index(corte) + len(corte)
                out.append((sec, titulo, rest[:i]))
                assert rest[i:].startswith(segundo), rest[i:]
                out.append((sec, segundo, rest[i + len(segundo):]))
                continue
            out.append((sec, titulo, rest))
    if pend:
        sys.exit(f'✗ encabezados sin párrafo: {pend}')
    return out


def campo(t, nombre):
    m = re.search(rf'\n{nombre}\s*\n\s*([^\n]*)', t)
    return m.group(1).strip() if m else ''


def ficha_cinecorto(titulo, director):
    q = BUSQUEDA.get(titulo, titulo)
    res = get_json(f'{CINECORTO}/search?search={urllib.parse.quote(q)}&subtype=post&per_page=10',
                   f'cinecorto/busca-{plano(q).replace(" ", "-")[:60]}.json')
    dirs = set(plano(director).replace(' y ', ' ').split())
    for r in res:
        if plano(html.unescape(r['title'])) != plano(titulo):
            continue
        post = get_json(f'{CINECORTO}/posts/{r["id"]}?_fields=content,link',
                        f'cinecorto/post-{r["id"]}.json')
        # sin <script>: algunas fichas traen el JSON-LD de SEO dentro del
        # contenido, y era el «párrafo largo» que se tomaba por sinopsis
        cuerpo = re.sub(r'<script.*?</script>', '', post['content']['rendered'], flags=re.S)
        t = '\n' + re.sub(r'\n\s*\n+', '\n', html.unescape(re.sub(r'<[^>]+>', '\n', cuerpo)))
        # la etiqueta cambia de ficha en ficha: «Dirección», «Director»,
        # «Directora»… («Mañanitas» dice «Director» y se perdía)
        d_cc = campo(t, '(?:Dirección|Directora?e?s?|Dirigid[oa] por)')
        # LA LLAVE ES LA DIRECCIÓN: al menos dos palabras del nombre (o la única
        # que haya) en común. Un título igual con otra dirección es otra obra.
        comunes = dirs & set(plano(d_cc).split())
        if len(comunes) < min(2, len(dirs)):
            continue
        anio = campo(t, 'Año')
        # «7», «7 min», «17:32 min»: se toman los minutos enteros. Los segundos
        # sobran para el candado, que tolera ±3.
        m = re.match(r'(\d+)', campo(t, 'Duración'))
        dur = m.group(1) if m else ''
        # LA SINOPSIS: los párrafos largos antes de «Selecciones y premios».
        # Varias fichas la dan en los dos idiomas y no siempre en el mismo orden
        # («Una vez en un cuerpo» abre con la inglesa): cada párrafo va al idioma
        # que más palabras funcionales tiene.
        sinopsis = sinopsis_en = ''
        for linea in t.split('Selecciones y premios')[0].split('\n'):
            linea = linea.strip()
            if len(linea) < 120:
                continue
            w = f' {plano(linea)} '
            es = sum(w.count(f' {x} ') for x in ('el', 'la', 'de', 'que', 'y', 'en', 'los', 'su', 'una'))
            en = sum(w.count(f' {x} ') for x in ('the', 'and', 'of', 'to', 'her', 'his', 'is', 'with', 'a'))
            if es >= en and not sinopsis:
                sinopsis = linea
            elif en > es and not sinopsis_en:
                sinopsis_en = linea
        return {'url': post['link'], 'direccion': d_cc,
                'anio': int(anio[:4]) if anio[:4].isdigit() else None,
                'duracion_min': int(dur) if dur.isdigit() else None,
                'categoria': campo(t, 'Categoría'), 'sinopsis': sinopsis,
                'sinopsis_en': sinopsis_en}
    return None


def main():
    filas = lista()
    cuenta = {}
    for sec, *_ in filas:
        cuenta[sec] = cuenta.get(sec, 0) + 1
    if cuenta != ESPERADAS:
        sys.exit(f'✗ por sección: {cuenta}\n  se esperaba {ESPERADAS}')

    obras, sin_ficha = [], []
    for sec, titulo, rest in filas:
        director, produccion = credito(rest)
        o = {'titulo': titulo, 'director': director, 'seccion_fuente': sec,
             '_src': {'url': 'https://festicinepopayan.com/fest2026/seleccion-oficial-2026/',
                      'date': '2026-09-28'}}
        if produccion:
            o['produccion'] = produccion
        cc = ficha_cinecorto(titulo, director)
        if cc:
            for k in ('anio', 'duracion_min'):
                if cc[k]:
                    o[k] = cc[k]
            for k in ('sinopsis', 'sinopsis_en'):
                if cc[k]:
                    o[k] = cc[k]
            o['_ficha'] = {'url': cc['url'], 'categoria': cc['categoria'],
                           'direccion': cc['direccion']}
        else:
            sin_ficha.append(titulo)
        obras.append(o)

    json.dump({'_provenance': provenance(
        'festicinepopayan.com (Selección Oficial 2026, vía wp-json) + cinecorto.co '
        '(ficha de cada corto, confirmada por dirección)',
        que_aporta='sección, título y crédito (la web); año, duración y sinopsis (cinecorto.co)',
        url='https://festicinepopayan.com/fest2026/seleccion-oficial-2026/',
        metodo='la lista emparejada pestaña por pestaña y contada contra ESPERADAS; '
               'la ficha aceptada solo si su dirección casa'),
        'obras': obras, 'sin_ficha_cinecorto': sin_ficha},
        io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con = len(obras) - len(sin_ficha)
    print(f'✓ {len(obras)} obras en {len(cuenta)} secciones · {con} con ficha de '
          f'cinecorto.co (año/duración) → {os.path.relpath(DESTINO, REPO)}')
    for s, n in cuenta.items():
        print(f'   {n:2}  {s}')
    if sin_ficha:
        print(f'   sin ficha en cinecorto.co ({len(sin_ficha)}): ' + ' · '.join(sin_ficha))


if __name__ == '__main__':
    main()
