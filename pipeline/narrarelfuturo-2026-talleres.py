# -*- coding: utf-8 -*-
"""narrarelfuturo.com/talleres-2026/<slug>/ → la franja académica, con imágenes.

La página índice enlaza una ficha por taller y cada ficha trae día, rango
horario, sede, tallerista con su país, duración, cupos y descripción — más el
RETRATO del tallerista en wp-content/uploads.

Las fichas NO son uniformes: unas rotulan «Tallerista:» y ponen el nombre en la
línea siguiente, otras lo escriben inline; el día llega como «Jueves 17 de
Septiembre», «17 de Sep» o «Viernes 18 de Sep». Por eso el parser es tolerante
y, lo que no puede llenar, LO DECLARA al final en vez de adivinarlo: una hora
inventada en una franja académica se ve igual de bien que una real.

La imagen se guarda en su forma ORIGINAL, sin la variante «-1024x476» que
WordPress genera: el encuadre de pósters parte del archivo original (POSTERS.md
§3) y encadenar recortes sobre recortes acumula deformación.
"""
import io, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
INDICE = 'https://narrarelfuturo.com/talleres-2026/'
SALIDA = f'{ST}/narrarelfuturo-2026-talleres.json'

MES = {'sep': '09', 'septiembre': '09'}
RE_DIA = re.compile(r'(?:(?:Lun|Mar|Mié|Mie|Jue|Vie|Sáb|Sab|Dom)[a-zé]*\s+)?(\d{1,2})\s+de\s+(Sep\w*)', re.I)
# El separador del rango NO es siempre « a »: «Desde el Terreno» escribe
# «9:00am - 1:00pm» con guion, y por exigir « a » ese taller se cayó entero del
# festival — una actividad real perdida por un carácter. Se aceptan « a », guion,
# raya y «hasta».
RE_RANGO = re.compile(
    r'(\d{1,2}):(\d{2})\s*([ap])?m?\s*(?:a|-|–|—|hasta)\s*(\d{1,2})(?::(\d{2}))?\s*([apm])', re.I)
# La fuente nombra el mismo lugar de varias formas y cada variante partiría las
# funciones: «UTADEO» es la Tadeo, y «Taller de la Imagen» es una SALA dentro de
# la Cinemateca. Tabla explícita, nunca heurística — la lección de FICDEH.
SEDES = {
    'Taller de la Imagen': ('Cinemateca de Bogotá', 'Taller de la Imagen'),
    # Misma casa, otro nombre: cinco fichas escriben «Taller de Creación
    # Audiovisual» donde otras cinco dicen «Taller de la Imagen». Las diez
    # nombran además «Cinemateca de Bogotá», que es la sede. Sin esta entrada la
    # sala se perdía en la mitad de los talleres.
    'Taller de Creación Audiovisual': ('Cinemateca de Bogotá', 'Taller de Creación Audiovisual'),
    'Cinemateca de Bogotá': ('Cinemateca de Bogotá', ''),
    'Universidad Jorge Tadeo Lozano': ('Universidad Jorge Tadeo Lozano', ''),
    'UTADEO': ('Universidad Jorge Tadeo Lozano', ''),
}


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    import html as _h
    t = _h.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def bajar(url, nombre):
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 5000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
        time.sleep(0.3)
    return io.open(p, encoding='utf-8', errors='replace').read()


# ERRATA DEL SITIO, corregida con evidencia y declarada aquí: la ficha del
# taller escribe «Resonacia Cromática», y el MISMO sitio escribe «Resonancia
# Cromática» en la ficha de «Sueño Viscoso 194» —de esa misma gente— y su
# Instagram es @resonanciacromatica. Es una letra caída, no otro nombre. Se
# corrige porque es el nombre propio de quien dicta el taller; queda dicho para
# avisarle al festival.
CORRECCION_NOMBRE = {'Resonacia Cromática': 'Resonancia Cromática'}


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


def h24(hh, mm, ap):
    # «12m» es MEDIODÍA (meridiano), como lo escribe la ficha del taller de
    # podcast: «10:00am a 12m». Tratarlo como «12 sin am/pm» daba 00:00, el fin
    # quedaba antes del inicio y el taller salía sin duración.
    if (ap or '').lower() == 'm' and int(hh) == 12:
        return '12:00'
    h = int(hh) % 12 + (12 if (ap or '').lower().startswith('p') else 0)
    return f'{h:02d}:{mm or "00"}'


def parse(slug, h):
    L = texto(h)
    d = {'_slug': slug, '_src': f'{INDICE}{slug}/', 'tipo': 'taller'}
    d['titulo'] = re.sub(r'\s*-\s*#NarrarElFuturo\s*$', '', L[0]).strip()
    for k, x in enumerate(L):
        if re.match(r'^Tallerista[s]?:$', x) and k + 1 < len(L):
            d.setdefault('tallerista', L[k + 1])
        m = re.match(r'^Tallerista[s]?:\s*(.+)$', x)
        if m and m.group(1).strip():
            # el país viene pegado entre paréntesis en la misma línea
            # («Tallerista: María Isabel Cevallos (Ecuador)»); separarlo es lo que
            # hace que la bandera exista.
            _v = m.group(1).strip()
            _mp = re.match(r'^(.+?)\s*\(([^)]{3,40})\)\s*\.?$', _v)
            if _mp:
                d.setdefault('tallerista', _mp.group(1).strip())
                d.setdefault('pais', _mp.group(2).strip())
            else:
                d.setdefault('tallerista', _v)
        if re.fullmatch(r'\(([^)]+)\)', x) and not d.get('pais'):
            d['pais'] = x.strip('()')
        if re.match(r'^Participantes:?$', x) and k + 1 < len(L):
            d.setdefault('cupos', L[k + 1])
        m = re.match(r'^\.?\s*Participantes:\s*(\d+)', x)
        if m:
            d.setdefault('cupos', m.group(1))
        md = RE_DIA.search(x)
        if md and not d.get('dia'):
            d['dia'] = f"2026-{MES.get(md.group(2)[:3].lower(),'09')}-{int(md.group(1)):02d}"
        # «Primera sesión: … / Segunda sesión: …»: el taller tiene DOS sesiones
        # el mismo día. Se toma la primera como hora y se declara la otra, en vez
        # de publicar el taller sin duración como hacía antes.
        if re.match(r'^Segunda sesi', x, re.I):
            d['_segunda_sesion'] = x
        mr = RE_RANGO.search(x)
        # SEGUNDA SESIÓN el mismo día: el taller de podcast va «10:00am a 12m» y
        # «Segunda sesión: 2:00pm a 6:00pm». Antes se guardaba solo el rótulo y
        # el bloque de la tarde se perdía en silencio; ahora es una sesión más,
        # que el crudo publica como su propia actividad.
        if mr and d.get('hora') and not d.get('sesion2'):
            h2 = h24(mr.group(1), mr.group(2), mr.group(3) or mr.group(6))
            f2 = h24(mr.group(4), mr.group(5), mr.group(6))
            i2 = int(h2[:2]) * 60 + int(h2[3:])
            e2 = int(f2[:2]) * 60 + int(f2[3:])
            d['sesion2'] = {'hora': h2, 'duracion_min': (e2 - i2) if e2 > i2 else None, '_rango': x}
        if mr and not d.get('hora'):
            d['hora'] = h24(mr.group(1), mr.group(2), mr.group(3) or mr.group(6))
            fin = h24(mr.group(4), mr.group(5), mr.group(6))
            ini = int(d['hora'][:2]) * 60 + int(d['hora'][3:])
            f2 = int(fin[:2]) * 60 + int(fin[3:])
            if f2 > ini:
                d['duracion_min'] = f2 - ini
            d['_rango'] = x
        for variante, (sede, sala) in SEDES.items():
            if variante in x:
                d.setdefault('sede', sede)
                if sala:
                    d.setdefault('sala', sala)
                break
        # tallerista en la forma «Con NOMBRE» / «(País)», que es como lo
        # escriben siete de las once fichas: sin el rótulo «Tallerista:».
        if x == 'Con' and k + 1 < len(L) and not d.get('tallerista'):
            d['tallerista'] = L[k + 1]
            if k + 2 < len(L) and re.fullmatch(r'\(([^)]+)\)\.?', L[k + 2]):
                d.setdefault('pais', L[k + 2].strip('().'))
        # «Con Nombre (País)» en UNA línea: «Señales Líquidas» lo escribe así y
        # mi regla de dos líneas lo dejaba sin tallerista.
        # «Con Resonacia Cromática -» y los nombres en el RENGLÓN SIGUIENTE: así
        # acredita el festival al único taller dictado por un colectivo, y mis
        # dos reglas (una línea, o «Con» solo) lo dejaban sin tallerista.
        mcol = re.match(r'^Con\s+(.{3,60}?)\s*[-–—]\s*$', x)
        if mcol and not d.get('tallerista') and k + 1 < len(L):
            _col = CORRECCION_NOMBRE.get(mcol.group(1).strip(), mcol.group(1).strip())
            d['tallerista'] = f'{_col} — {L[k + 1].strip()}'
            if k + 2 < len(L) and re.fullmatch(r'\(([^)]+)\)\.?', L[k + 2]):
                d.setdefault('pais', L[k + 2].strip('().'))
        m2 = re.match(r'^Con\s+(.{3,90}?)\s*\(([^)]{3,40})\)\s*\.?$', x)
        if m2 and not d.get('tallerista'):
            d['tallerista'], _p = m2.group(1).strip(), m2.group(2).strip()
            d.setdefault('pais', _p)
    largos = [x for x in L if len(x) > 140]
    if largos:
        d['sinopsis'] = largos[0]
    # retrato del tallerista, de las imágenes del contenido (ver imagenes())
    ims = imagenes(h)
    if ims:
        d['imagen'] = ims[0]
        d['_imagenes'] = ims[:4]
    # EL ANCLA NO ES EL TEXTO DEL ENLACE. Buscar un <a> cuyo texto diga
    # «Inscrib» no encontraba NADA en los doce talleres: la ficha escribe
    # «INSCRIPCIÓN AQUÍ» FUERA del <a> y dentro pone la URL pelada
    # («bit.ly/TalleresNEF2026»). Resultado: doce talleres publicados sin su
    # formulario y con acceso «desconocido», teniéndolo la fuente en la cara.
    # Es la misma familia del bug que se llevó los seis enlaces de TuBoleta de
    # CineAutopsia. Ahora se busca el rótulo y se toma el primer href que venga
    # detrás, y también se acepta el <a> que sí se nombre a sí mismo.
    m = re.search(r'Inscrip\w*|Inscrib\w*', h, re.I)
    if m:
        m2 = re.search(r'href="([^"]+)"', h[m.end():m.end() + 600])
        if m2:
            d['registration_url'] = re.sub(r'^http://', 'https://', m2.group(1))
    if not d.get('registration_url'):
        m3 = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).)*?Inscrib', h, re.S | re.I)
        if m3:
            d['registration_url'] = re.sub(r'^http://', 'https://', m3.group(1))
    d['acceso'] = ('Entrada gratis con inscripción' if d.get('registration_url')
                   else ('Entrada libre' if re.search(r'Entrada libre', h, re.I) else lib.DESCONOCIDO))
    return d


def del_indice(idx):
    """tallerista y país desde el ÍNDICE, que los escribe «Con Nombre (País)».
    Siete de las once fichas no rotulan «Tallerista:» y el nombre queda suelto en
    el cuerpo; el índice sí es regular. Se cruza por el enlace de cada ficha, no
    por parecido de títulos."""
    m = {}
    for b in re.split(r'(?=<a[^>]+href="https://narrarelfuturo\.com/talleres-2026/)', idx)[1:]:
        u = re.match(r'<a[^>]+href="(https://narrarelfuturo\.com/talleres-2026/[^"#?]+)"', b)
        if not u:
            continue
        t = texto(b[:4000])
        for k, x in enumerate(t):
            mm = re.match(r'^Con\s+(.+?)\s*$', x)
            if mm and k + 1 < len(t) and re.fullmatch(r'\(([^)]+)\)\.?', t[k + 1]):
                m[u.group(1).rstrip('/').split('/')[-1]] = (
                    mm.group(1).strip(), t[k + 1].strip('().'))
                break
    return m


def main():
    idx = bajar(INDICE, 'talleres-indice.html')
    nombres = del_indice(idx)
    # El href de «Narrativas Virales» termina en «/?»: excluir «?» del patrón
    # excluía el taller entero. Se captura la ruta y se corta lo que siga al «?».
    # Lo cazó una extracción independiente que contó 12 talleres donde yo tenía 11.
    urls = sorted(set(re.sub(r'\?.*$', '', u) for u in
                      re.findall(r'href="(https://narrarelfuturo\.com/talleres-2026/[^"#]+)"', idx)))
    out = []
    for u in urls:
        slug = u.rstrip('/').split('/')[-1]
        d = parse(slug, bajar(u, f'taller-{slug}.html'))
        if slug in nombres and not d.get('tallerista'):
            d['tallerista'], d['_tallerista_src'] = nombres[slug][0], 'índice de talleres'
            d.setdefault('pais', nombres[slug][1])
        out.append(d)
    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        INDICE, metodo='una ficha por taller, enlazadas desde el índice',
        nota='fichas NO uniformes: el rótulo del tallerista y la forma del día cambian entre ellas'),
        '_talleres': len(out), 'talleres': out},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(out)} talleres')
    for d in out:
        print(f"  {d.get('dia','   ?      ')} {d.get('hora','  ?  ')}  {d['titulo'][:34]:36} "
              f"{(d.get('tallerista') or '—')[:24]:26} {(d.get('sala') or d.get('sede') or '—')[:20]:22} "
              f"{'img' if d.get('imagen') else '—'}")
    faltan = {k: [d['_slug'][:26] for d in out if not d.get(k)]
              for k in ('dia', 'hora', 'tallerista', 'sede', 'imagen')}
    for k, v in faltan.items():
        if v:
            print(f'  ⚠ sin {k}: {v}')


if __name__ == '__main__':
    main()
