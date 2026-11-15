#!/usr/bin/env python3
"""fuentes_descubrir.py — el inventario de TODO lo que un festival publicó.

POR QUÉ (12 nov 2026). Villa de Leyva subió su programa completo en un PDF de la
home el 11 nov y nadie lo vio en un día: el vigía comparaba los PDF que ya
conocía, no buscaba los nuevos. FICFUSA tenía sus nueve formularios de
inscripción en el Linktree de la bio de Instagram y el onboarding nunca lo
abrió. Las dos fallas son la misma: mirábamos lo conocido, no lo publicado.

QUÉ HACE. Recorre las RAÍCES del festival (la web, el link de la bio de IG, el
Facebook) y las páginas internas que enlazan (hasta 2 saltos, 60 páginas), y
anota cada cosa que puede traer programación: PDF, formularios, Linktree,
Drive, imágenes de programación y páginas de programa/agenda. Lo guarda en
festivals/staging/<fid>-fuentes.json. Lo que aparece por primera vez entra como
`sin-revisar`; una persona (o el vigía) lo pasa a `usada` o `descartada` con su
porqué. [inventario-fuentes] (validate.py) frena si queda algo sin revisar en
un festival vivo; publicar.py frena si el inventario tiene más de 24 h.

USO
  python3 pipeline/fuentes_descubrir.py <fid>              # recorre y actualiza
  python3 pipeline/fuentes_descubrir.py --vivos            # todos los festivales en curso o por venir
  python3 pipeline/fuentes_descubrir.py <fid> --raiz web=https://... --raiz bio=https://linktr.ee/x
  python3 pipeline/fuentes_descubrir.py <fid> --marcar <url|prefijo> usada|descartada "porqué"
Sale con código 3 si hay algo sin revisar (el vigía lo usa como hallazgo).
"""
import datetime
import html
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
MAX_PAGINAS, MAX_SALTOS = 60, 2
RAICES = ('web', 'bio', 'facebook', 'instagram', 'drive')   # + sufijo _2, _3… si hay varias
PROGRAMA = re.compile(r'program|agenda|horario|parrilla|cartelera|calendario|schedule|funcion|proyeccion|selecci', re.I)
IMAGEN_PROGRAMA = re.compile(r'program|agenda|horario|parrilla|cartelera|calendario', re.I)
NO_SEGUIR = re.compile(r'\.(jpe?g|png|gif|webp|svg|css|js|ico|mp4|zip|woff2?)(\?|$)|/wp-json/|/feed/?$|/tag/|/author/|#', re.I)


def ruta(fid):
    return os.path.join(REPO, 'festivals', 'staging', f'{fid}-fuentes.json')


def ahora():
    return (datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M')


def bajar(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'es-CO,es;q=0.9'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tipo = r.headers.get('Content-Type', '')
        if 'html' not in tipo and 'json' not in tipo:
            return r.geturl(), tipo, ''
        return r.geturl(), tipo, r.read(3_000_000).decode('utf-8', 'replace')


def enlaces(base, texto):
    out = set()
    for m in re.finditer(r'''(?:href|src|data-src|content)\s*=\s*["']([^"'<>\s]+)["']''', texto, re.I):
        u = html.unescape(m.group(1)).strip()
        if u.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
            continue
        if m.group(0).lower().startswith('content') and not u.startswith('http'):
            continue
        out.add(urllib.parse.urljoin(base, u))
    # URLs sueltas en JSON embebido (Wix, Linktree, Next.js): "https:\/\/..."
    for m in re.finditer(r'https?:\\?/\\?/[^"\'<>\s\\]+(?:\\/[^"\'<>\s\\]*)*', texto):
        out.add(m.group(0).replace('\\/', '/'))
    return out


def clasificar(u):
    p = urllib.parse.urlparse(u)
    h, path = p.netloc.lower(), p.path.lower()
    if path.endswith('.pdf') or '/_files/ugd/' in path and path.endswith('.pdf'):
        return 'pdf'
    if 'forms.gle' in h or ('docs.google.com' in h and re.search(r'/forms/(d/e/|d/)[A-Za-z0-9_-]{15,}', path)):
        return 'formulario'
    if 'docs.google.com' in h or 'drive.google.com' in h:
        return 'drive' if re.search(r'/(d|folders)/[A-Za-z0-9_-]{15,}', path) else None
    if h.removeprefix('www.') in ('linktr.ee', 'beacons.ai', 'linkin.bio', 'bio.link', 'campsite.bio', 'lnk.bio') \
            and re.fullmatch(r'/[^/]+/?', path) and not path.startswith(('/s/', '/blog', '/features', '/tools')):
        return 'bio'
    if re.search(r'\.(jpe?g|png|webp)$', path) and IMAGEN_PROGRAMA.search(path) \
            and not re.search(r'-\d{2,4}x\d{2,4}\.\w+$', path):
        return 'imagen-programa'
    if any(x in h for x in ('tuboleta', 'eticket', 'taquilla', 'boleteria', 'passline', 'eventbrite', 'cinecolombia', 'cinemark', 'procinal')):
        return 'boleteria'
    return None


def normal(u):
    p = urllib.parse.urlparse(u)
    q = '' if clasificar(u) in ('pdf', 'imagen-programa', 'formulario', 'drive') else p.query
    q = '&'.join(x for x in q.split('&') if x and not x.startswith(('fbclid', 'utm_', 'usp=', 'g_ep')))
    return urllib.parse.urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip('/') or '/', '', q, ''))


def de_otro_anio(u, anio):
    """Un enlace que solo nombra años anteriores es archivo de ediciones pasadas."""
    anios = set(re.findall(r'(?<!\d)(20[12]\d)(?!\d)', urllib.parse.urlparse(u).path))
    return bool(anios) and str(anio) not in anios and all(int(a) < anio for a in anios)


def recorrer(raices, anio):
    vistos, cosas, errores = set(), {}, []
    hosts = {urllib.parse.urlparse(u).netloc.lower().removeprefix('www.') for k, u in raices.items()
             if k.startswith('web') and u}
    cola = [(u, 0, re.sub(r'_\d+$', '', k)) for k, u in raices.items()
            if u and not k.startswith(('_', 'instagram')) and u.startswith('http')]
    for k, u in raices.items():   # una raíz que ya es fuente (Drive, formulario) entra al inventario tal cual
        if isinstance(u, str) and u.startswith('http') and clasificar(normal(u)) not in (None, 'bio'):
            cosas.setdefault(normal(u), {'tipo': clasificar(normal(u)), 'visto_en': f'raíz {k}'})
    while cola and len(vistos) < MAX_PAGINAS:
        u, salto, desde = cola.pop(0)
        if u in vistos:
            continue
        vistos.add(u)
        try:
            final, tipo, texto = bajar(u)
        except Exception as e:
            errores.append(f'{u}: {str(e)[:80]}')
            continue
        if not texto or 'google.com' in urllib.parse.urlparse(final).netloc:
            continue   # Drive y Forms no se recorren: su contenido lo pinta JS (se revisa a mano / en el navegador)
        for e in enlaces(final, texto):
            try:
                n = normal(e)
                k = clasificar(n)
            except ValueError:
                continue
            host = urllib.parse.urlparse(n).netloc.lower().removeprefix('www.')
            if de_otro_anio(n, anio):
                continue
            if k == 'bio' and desde == 'bio':
                continue   # un Linktree enlaza a otros perfiles: no son del festival
            if k:
                cosas.setdefault(n, {'tipo': k, 'visto_en': final})
                if k == 'bio' and salto < MAX_SALTOS:
                    cola.append((n, salto + 1, 'bio'))
            elif host in hosts and salto < MAX_SALTOS and not NO_SEGUIR.search(n):
                if PROGRAMA.search(urllib.parse.urlparse(n).path):
                    cosas.setdefault(n, {'tipo': 'pagina-programa', 'visto_en': final})
                cola.append((n, salto + 1, desde))
    return cosas, errores, len(vistos)


def cargar(fid):
    p = ruta(fid)
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return {'_provenance': {'fuente': 'pipeline/fuentes_descubrir.py', 'capturado': None},
            'raices': {}, 'items': {}}


def guardar(fid, d):
    io.open(ruta(fid), 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')


def vivos():
    cfg = open(os.path.join(REPO, 'src', 'config.js'), encoding='utf-8').read()
    hoy = (datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(hours=5)).date().isoformat()
    return sorted(re.sub(r'([a-z]+)(\d+)$', r'\1-\2', f)
                  for f, end in re.findall(r"'([a-z0-9]+)':\s*\{.*?festivalEndStr:\s*'(\d{4}-\d{2}-\d{2})", cfg, re.S)
                  if end >= hoy)


def descubrir(fid):
    d = cargar(fid)
    if not any(k.startswith(('web', 'bio', '_sin_web')) for k in d['raices']):
        print(f'✗ {fid}: sin raíces — darlas con --raiz web=… --raiz bio=… (o _sin_web/_sin_bio con su porqué)')
        return 1
    cosas, errores, n = recorrer(d['raices'], int(re.search(r'(20\d\d)$', fid).group(1)))
    t = ahora()
    nuevos = []
    for u, c in sorted(cosas.items()):
        it = d['items'].get(u)
        if it:
            it['ultima_vez'] = t
        else:
            d['items'][u] = {**c, 'primera_vez': t, 'ultima_vez': t, 'estado': 'sin-revisar'}
            nuevos.append(u)
    d['_provenance']['capturado'] = t
    d['_provenance']['paginas_leidas'] = n
    d['_provenance']['errores'] = errores[:10]
    guardar(fid, d)
    pend = [u for u, i in d['items'].items() if i['estado'] == 'sin-revisar']
    print(f'{"⚠" if pend else "✓"} {fid}: {n} páginas · {len(d["items"])} fuentes · {len(nuevos)} nuevas · {len(pend)} sin revisar')
    for u in pend:
        print(f'   · [{d["items"][u]["tipo"]}] {u}')
    for e in errores[:3]:
        print(f'   ✗ no se pudo leer {e}')
    return 3 if pend else 0


def problemas(d, horas=None, ahora_co=None):
    """Lo que le falta a un inventario para dar por buena la obtención de fuentes.
    Dueña única de la regla: la usan [inventario-fuentes] (validate.py, sin
    `horas`) y publicar.py (con `horas`=24: un inventario viejo no prueba nada)."""
    out = []
    r = d.get('raices') or {}
    if not any(k.startswith(('web', 'bio', '_sin_web')) for k in r):
        out.append('sin raíces: falta la web o el link de la bio (o _sin_web con su porqué)')
    if not any(k.startswith(('bio', '_sin_bio')) for k in r):
        out.append('falta el link de la bio de Instagram (o _sin_bio con su porqué): ahí suelen estar Linktree y formularios')
    pend = [u for u, i in (d.get('items') or {}).items() if i.get('estado') == 'sin-revisar']
    if pend:
        out.append(f'{len(pend)} fuente(s) sin revisar, p. ej. {pend[0]}')
    if horas:
        cap = (d.get('_provenance') or {}).get('capturado')
        ya = ahora_co or datetime.datetime.strptime(ahora(), '%Y-%m-%dT%H:%M')
        if not cap or (ya - datetime.datetime.strptime(cap, '%Y-%m-%dT%H:%M')).total_seconds() > horas * 3600:
            out.append(f'el recorrido tiene más de {horas} h ({cap}): correr pipeline/fuentes_descubrir.py')
    return out


def autoprueba():
    t = datetime.datetime(2026, 11, 12, 12, 0)
    bien = {'_provenance': {'capturado': '2026-11-12T08:00'}, 'raices': {'web': 'https://x', 'bio': 'https://y'},
            'items': {'https://x/a.pdf': {'estado': 'usada'}}}
    ciegos = []
    if problemas(bien, 24, t):
        ciegos.append('bien')
    for nombre, cebo in (('pendiente', {**bien, 'items': {'https://x/b.pdf': {'estado': 'sin-revisar'}}}),
                         ('sin bio', {**bien, 'raices': {'web': 'https://x'}}),
                         ('viejo', {**bien, '_provenance': {'capturado': '2026-11-10T08:00'}})):
        if not problemas(cebo, 24, t):
            ciegos.append(nombre)
    return ciegos


def main(a):
    if not a or a[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    if a[0] == '--vivos':
        return max([descubrir(f) for f in vivos()] or [0])
    fid = a[0]
    if '--marcar' in a:
        i = a.index('--marcar')
        pref, estado, porque = a[i + 1], a[i + 2], a[i + 3]
        if estado not in ('usada', 'descartada') or not porque.strip():
            sys.exit('✗ estado: usada|descartada, y un porqué')
        d = cargar(fid)
        hits = [u for u in d['items'] if u == pref or u.startswith(pref)]
        if not hits:
            sys.exit(f'✗ nada empieza con {pref}')
        for u in hits:
            d['items'][u].update(estado=estado, _por_que=porque, revisado=ahora())
        guardar(fid, d)
        print(f'✓ {len(hits)} marcada(s) {estado}')
        return 0
    d = cargar(fid)
    for i, x in enumerate(a):
        if x == '--raiz':
            k, v = a[i + 1].split('=', 1)
            if re.sub(r'_\d+$', '', k) not in RAICES and not k.startswith('_sin_'):
                sys.exit(f'✗ raíz {k}: una de {RAICES} o _sin_<raíz>')
            d['raices'][k] = v
    guardar(fid, d)
    return descubrir(fid)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
