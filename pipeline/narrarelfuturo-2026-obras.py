# -*- coding: utf-8 -*-
"""Una ficha por obra desde narrarelfuturo.com/programa-2026/<slug>/.

LA FUENTE COMPLETA, y la encontré tarde. La página de programación enlaza una
ficha propia por obra —42— y ahí está lo que estuve buscando en los pies
truncados de Instagram: sinopsis entera, dirección, día, hora, sala, sede,
frase de acceso con su enlace, y el PÓSTER de la obra.

Se llega por el enlace «Ver Detalles» de cada tarjeta y por el título de cada
corto dentro de un programa; la ruta lleva el programa cuando la obra pertenece
a uno: `/programa-2026/cortos-·-aqua-ensayo-diversidad/refraccion/`.

POR QUÉ NO SE USA EL PIE DE INSTAGRAM PARA ESTO: el embed corta el pie a ~2.170
caracteres, a mitad de palabra. Leídas así, «El Futuro del Futuro» daba 5 obras
de 9 y «Narrar. Creer. Crecer» 2 de 10. La web no se corta.
"""
import io, json, os, re, subprocess, sys, time, unicodedata
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
BASE = 'https://narrarelfuturo.com/programa-2026/'
SALIDA = f'{ST}/narrarelfuturo-2026-obras.json'

MES = {'sep': '09'}
RE_FICHA = re.compile(r'^(?P<pais>[^·]+?)\s*·\s*(?P<anio>(?:19|20)\d\d)\s*·\s*(?P<dur>[^·]+?)\s*(?:·\s*(?P<gen>.+))?$')
RE_CUANDO = re.compile(r'(\d{1,2})\s+de\s+(Sep\w*)\.?\s+(\d{1,2}):(\d{2})\s*([ap])m', re.I)
SEDES = ('Cinemateca de Bogotá', 'Universidad Jorge Tadeo Lozano', 'Cinemateca Fontanar del Río')


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    import html as _h
    t = _h.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def imagenes(h):
    """Las imágenes DEL CONTENIDO de la ficha, en su forma original.

    NO vale barrer el HTML entero buscando URLs de /uploads/: eso recoge
    también el <meta property="og:image">, que es la imagen para COMPARTIR EN
    REDES —siempre 16:9, a veces de otra persona («iliana.jpg» en la ficha de un
    taller que dictan Camila Lozano y Andrés Fernández)—. Once de los doce
    talleres publicaban esa en vez del retrato del tallerista, que estaba en el
    contenido, en vertical, dos párrafos más abajo. El <img> del contenido es el
    único que la página pone para que se vea.

    Se devuelve la forma ORIGINAL: WordPress escribe el src con la variante de
    tamaño («-836x1024») y la original es la que no la lleva.
    """
    out = []
    for m in re.finditer(r'<img[^>]+src="(https://narrarelfuturo\.com/wp-content/uploads/[^"]+)"', h, re.I):
        u = re.sub(r'-\d+x\d+(\.\w+)$', r'\1', m.group(1))
        # chrome del sitio: perfil, logos y la cabecera de plantilla
        if re.search(r'cropped-|_perfil|perfil\.|logo|favicon|icon|Mesa-de-trabajo', u, re.I):
            continue
        out.append(u)
    return list(dict.fromkeys(out))


def minutos(s):
    m = re.match(r'^(\d+)\s*h\s*(\d+)?\s*min', s.strip())
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    m = re.match(r'^(\d+)\s*min', s.strip())
    return int(m.group(1)) if m else None


def bajar(url, nombre):
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
        time.sleep(0.25)
    return io.open(p, encoding='utf-8', errors='replace').read()


def parse(ruta, h):
    L = texto(h)
    partes = [unquote(x) for x in ruta.strip('/').split('/')]
    d = {'_src': BASE + ruta, '_slug': partes[-1]}
    if len(partes) > 1:
        d['programa'] = partes[0].replace('cortos ·', '').replace('cortos-·-', '').strip(' -·')
    # EL TÍTULO SALE DEL <title> DE LA PÁGINA, no de la línea anterior a la
    # ficha técnica. Esa línea es a veces el SUBTÍTULO: en la inaugural dice
    # «Película inaugural», así que la obra se guardaba con ese nombre, no
    # cruzaba con «Soñé su nombre» y perdía su sinopsis en la fusión. El <title>
    # es el nombre de la obra y no depende de la maquetación.
    titulo_pagina = re.sub(r'\s*-\s*#NarrarElFuturo\s*$', '', L[0]).strip() if L else ''
    for k, x in enumerate(L):
        m = RE_FICHA.match(x)
        if m and minutos(m.group('dur')) is not None and k:
            d['titulo'] = titulo_pagina or L[k - 1]
            d.update({'pais': m.group('pais').strip(), 'anio': int(m.group('anio')),
                      'duracion_min': minutos(m.group('dur')),
                      'genero': (m.group('gen') or '').strip()})
            break
    # sin línea de ficha técnica igual hay obra: el título del <title> vale.
    # Pasa en dos piezas de VR, que no publican país/año/duración.
    d.setdefault('titulo', titulo_pagina)
    for k, x in enumerate(L):
        if x == 'Dir.' and k + 1 < len(L):
            d.setdefault('director', L[k + 1])
        mc = RE_CUANDO.search(x)
        if mc and not d.get('dia'):
            hh = int(mc.group(3)) % 12 + (12 if mc.group(5).lower() == 'p' else 0)
            d['dia'] = f"2026-{MES.get(mc.group(2)[:3].lower(),'09')}-{int(mc.group(1)):02d}"
            d['hora'] = f'{hh:02d}:{mc.group(4)}'
        if re.match(r'^\*?\s*Entrada', x, re.I):
            d.setdefault('acceso', x.lstrip('*').strip())
        if re.match(r'^(Sala|Hemiciclo|Aula|Laboratorio)\b', x):
            d.setdefault('sala', x.rstrip(',').strip())
        for s in SEDES:
            if s in x:
                d.setdefault('sede', s)
    # LA SINOPSIS ES ESTRUCTURAL, NO UN UMBRAL DE LARGO. Es el párrafo que va
    # entre la línea de acceso (o la sede) y el pie institucional «El Festival de
    # Cine & Nuevos Medios es un punto…». Con umbral de 160 se perdían «Malignant
    # / Catatonic» (120) y «How things are between us» (131); con 100 se perdía
    # «Marta Trend» (48): «Él siempre vuelve a Buenos Aires. Ella también.» Una
    # sinopsis puede ser una frase. Todo umbral que uno elige es una hipótesis
    # sobre la fuente, y ésta la desmintió tres veces.
    PIE = 'Festival de Cine & Nuevos Medios es un punto'
    fin = next((k for k, x in enumerate(L) if PIE in x), len(L))
    # El ANCLA es la SEDE, no el acceso. En las fichas de Fontanar sede y acceso
    # van en un renglón («Cinemateca Fontanar del Río , entrada gratis…») ANTES
    # de la sinopsis; en las de la Tadeo la sede va en dos («Hemiciclo» / «,
    # Universidad Jorge Tadeo Lozano…») y el acceso («INSCRIPCIÓN AQUÍ» +
    # bit.ly) va DESPUÉS. Anclar en el acceso se comía 6 sinopsis de la Tadeo.
    ini = 0
    for k in range(min(fin, len(L)) - 1, -1, -1):
        if re.match(r'^(Sala|Hemiciclo|Laboratorio|Cinemateca|Universidad)\b', L[k]) \
           or re.match(r'^, (Cinemateca|Universidad)', L[k]):
            ini = k + 1
            break
    cuerpo = [x for x in L[ini:fin]
              if not re.match(r'^(Ver Detalles|Inscribirse|INSCRIPCI|Compra|Cargando|\*|Dir\.|bit\.ly|https?://)', x)
              and not re.match(r'^, ', x) and '#NarrarElFuturo' not in x
              and not re.search(r'\b(entrada (gratis|libre)|hasta completar (el )?aforo|boleta)\b', x, re.I)
              and not RE_FICHA.match(x) and not RE_CUANDO.search(x)
              and len(x) > 20]
    if cuerpo:
        d['sinopsis'] = ' '.join(cuerpo)
        # ERRATA DEL SITIO, con evidencia: la ficha de «Fail» trae pegado el 2º
        # párrafo de la sinopsis de «Chaika» («Los paisajes, trémulos y
        # borrosos…»), que existe tal cual en la ficha de Chaika. Se corta ahí y
        # se deja constancia; no se reescribe nada más.
        _c = d['sinopsis'].find('Los paisajes, trémulos y borrosos')
        if _c > 0 and (d.get('titulo') or '').strip().lower() == 'fail':
            d['sinopsis'] = d['sinopsis'][:_c].rstrip()
            d['_sinopsis_nota'] = 'la web pega a continuación el 2º párrafo de la sinopsis de Chaika; se cortó'

    ims = imagenes(h)   # solo el contenido de la ficha, nunca el og:image
    # EL PÓSTER: dos señales, y ninguna alcanza sola. Lo midió una revisión
    # independiente que extrajo las 42 fichas sin ver este código:
    #   · exigir «poster» EN EL NOMBRE pierde 7 afiches reales
    #     («1_ColombiaEmbrujoVerdeEsmeralda-1.jpg» no lleva la palabra)
    #   · exigir que el NOMBRE COINCIDA con el título pierde otros 8
    #     («PosterQQB1-1-1.jpg», «7059170c3d-poster.webp»)
    #   · y coincidir por título solo puede traer un FOTOGRAMA: en «Después del
    #     frío» el archivo que lleva el título es un frame y el afiche es
    #     «POSTER-DDF-1-1-1.jpg», que no lo lleva.
    # Por eso: vale cualquiera de las dos señales, y cuando las dos existen
    # MANDA la que dice «poster». `LATTICE-poster-1.jpg` se descarta siempre:
    # está en todas las fichas, es un resto de la plantilla del sitio.
    # La clave se PLANCHA a ascii ANTES de quitar lo no alfanumérico. Quitarlo
    # primero borra la ñ y las tildes —«Niños» → «nios»— mientras el nombre del
    # archivo las transcribe («2_Ninos-de-Donbass-…»), así que la obra se
    # quedaba sin su póster. Lo mismo valía para cualquier título con acento.
    _t = unicodedata.normalize('NFD', (d.get('titulo') or '').lower())
    _t = _t.encode('ascii', 'ignore').decode()
    clave = re.sub(r'[^a-z0-9]+', '', _t)[:8]
    # …salvo en LATTICE, donde ese archivo ES su afiche legítimo. Excluirlo
    # siempre dejaba sin póster justo a la obra dueña de la imagen.
    cand = [u for u in ims if 'LATTICE-poster' not in u or clave.startswith('lattice')]
    def archivo(u):
        x = unicodedata.normalize('NFD', u.rsplit('/', 1)[-1].lower())
        return re.sub(r'[^a-z0-9]+', '', x.encode('ascii', 'ignore').decode())
    con_palabra = [u for u in cand if 'poster' in u.lower() or 'afiche' in u.lower()]
    con_titulo = [u for u in cand if clave and clave[:6] in archivo(u)]
    ambas = [u for u in con_palabra if u in con_titulo]
    elegido = (ambas or con_palabra or con_titulo)
    if elegido:
        d['poster'] = elegido[0]
        d['_poster_regla'] = ('nombre + palabra' if ambas else
                              ('palabra «poster»' if con_palabra else 'nombre de la obra'))
    if ims:
        d['imagenes'] = ims[:5]
    m = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).){0,600}?Inscrib', h, re.S | re.I)
    if m:
        d['registration_url'] = re.sub(r'^http://', 'https://', m.group(1))
    m = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).){0,600}?(?:boleta|Compra)', h, re.S | re.I)
    if m:
        d['ticket_url'] = re.sub(r'^http://', 'https://', m.group(1))
    d.setdefault('acceso', 'Entrada gratis con inscripción' if d.get('registration_url')
                 else ('Boletería' if d.get('ticket_url') else lib.DESCONOCIDO))
    return d


def main():
    idx = bajar(BASE, 'programa-2026.html')
    rutas = sorted(set(re.findall(r'href="https://narrarelfuturo\.com/programa-2026/([^"#?]+/)"', idx)))
    out = []
    for r in rutas:
        nombre = 'obra-' + re.sub(r'[^A-Za-z0-9]+', '-', unquote(r).strip('/'))[:70] + '.html'
        out.append(parse(r, bajar(BASE + r, nombre)))

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        BASE + '<slug>/',
        metodo='una ficha por obra, enlazadas desde el programa; la ruta lleva el programa cuando la obra pertenece a uno',
        nota='el pie de Instagram se corta a ~2.170 caracteres y daba 5 obras de 9; la web no se corta'),
        '_obras': len(out), 'obras': out},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(out)} obras')
    campos = ('titulo', 'director', 'sinopsis', 'poster', 'dia', 'hora', 'sede', 'acceso', 'genero')
    for c in campos:
        n = sum(1 for o in out if o.get(c))
        print(f'   {c:<12} {n:>3}/{len(out)}')
    sin = [o['_slug'] for o in out if not o.get('titulo')]
    if sin:
        print('   ⚠ sin título:', sin[:6])


if __name__ == '__main__':
    main()
