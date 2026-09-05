# -*- coding: utf-8 -*-
"""Fichas de cinemanciafestival.com → `cinemancia-2026-web.json`.

HALLAZGO QUE JUSTIFICA ESTE PASO (9 ago 2026). Se escribió para rescatar las 21
sinopsis que TMDB no tiene y la web del festival sí. Al inspeccionar la ficha
apareció algo bastante más grande: **la programación YA ESTÁ PUBLICADA**, obra
por obra, en un bloque «Horarios» con fecha, hora, teatro, ciudad y sala. El
anuncio de prensa dice que horarios y sedes salen «en los próximos días», y es
verdad que no hay una página de programación general — pero el dato existe,
repartido en las fichas. Sin esto habríamos esperado semanas de gusto.

QUÉ SE EXTRAE, y cómo se distingue cada cosa sin adivinar:

  · SINOPSIS — el párrafo que sigue al rótulo «<h2>Sinopsis</h2>». La ficha
    mezcla sinopsis y biografías del director en párrafos con el MISMO formato
    (mismo widget de Elementor, misma clase), así que separarlos por la prosa
    sería frágil: se hace por el rótulo, que es estructura y no estilo.
  · HORARIOS — filas del bloque «Horarios»: «Jueves 10 de septiembre | 4:00
    p.m.» + teatro + ciudad. El teatro trae la sala pegada con guiones
    («Centro Colombo Americano - Sede centro - Sala 1») y NO se parte aquí:
    partir sede y sala es trabajo del ensamblador, con su tabla de sedes. La
    lección de FICDEH es que la sala inventada parte funciones reales en dos.
  · FICHA TÉCNICA — los rótulos «Año:», «Duración:», «País:», «Idioma:»,
    «Producción:», «Guion:», «Fotografía:», «Montaje:», «Sonido:», «Música:»,
    «Elenco:». El valor va inmediatamente después del rótulo.

NO SE INVENTA NADA: lo que la ficha no publica queda vacío, y la obra que no
tiene ficha (53 de las 109) no aparece en este sidecar.

El índice de fichas se re-descubre en cada corrida barriendo /peliculas/ y
filtrando por el badge «Edición 2026» (`<span class="pcTag">`), porque el
archivo mezcla las seis ediciones: 447 fichas en total, 56 de esta.
"""
import html, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/cinemancia-2026-web.json'
BASE = 'https://cinemanciafestival.com'
BADGE = 'Edición 2026'
CAMPOS = ['Año', 'Duración', 'País', 'Idioma', 'Dirección', 'Producción', 'Guion',
          'Fotografía', 'Montaje', 'Sonido', 'Música', 'Elenco']
CARD = re.compile(r'<article class="pcItem".*?</article>', re.S)
# Las seis del anuncio oficial. Lista CERRADA a propósito: es lo que permite
# saber dónde termina el nombre de la sede en una fila de horarios.
CIUDADES = {'Medellín', 'Envigado', 'Caldas', 'Itagüí', 'Copacabana', 'Bello'}
desconocidas = []


def limpia(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()


def indice():
    """→ [slug] de las fichas con badge «Edición 2026». El archivo mezcla las
    seis ediciones, así que sin el filtro entran 447 en vez de 56."""
    slugs, pagina = [], 1
    while pagina <= 30:
        s = lib.curl_get(f'{BASE}/peliculas/page/{pagina}/', min_bytes=20000)
        if not s:
            break
        hay = False
        for c in CARD.findall(s):
            hay = True
            t = re.search(r'<span class="pcTag">(.*?)</span>', c, re.S)
            u = re.search(r'href="https?://cinemanciafestival\.com/pelicula/([^"/]+)', c)
            if u and t and limpia(t.group(1)) == BADGE and u.group(1) not in slugs:
                slugs.append(u.group(1))
        if not hay:
            break
        pagina += 1
    return slugs


def tras_rotulo(s, rotulo, largo=900):
    """Texto que sigue a un <h2>rótulo</h2>. Es la única forma fiable de
    separar la sinopsis de las biografías: mismo widget, distinto rótulo."""
    m = re.search(r'>\s*' + re.escape(rotulo) + r'\s*<', s)
    if not m:
        return ''
    seg = s[m.end():m.end() + largo * 6]
    for p in re.findall(r'<p[^>]*>(.*?)</p>', seg, re.S):
        t = limpia(p)
        if len(t) > 40 and 'elementor' not in t:
            return t[:2000]
    return ''


def horarios(s):
    """→ [{dia_txt, hora, sede_txt, ciudad}] del bloque «Horarios»."""
    m = re.search(r'>\s*Horarios\s*<', s)
    if not m:
        return []
    seg = s[m.end():m.end() + 9000]
    seg = re.split(r'>\s*(?:Galer[íi]a|Sinopsis|Reflexi[óo]n)\s*<', seg)[0]
    seg = re.sub(r'</(p|div|h[1-6]|li|td|tr|span)>', '\n', seg)
    lineas = [limpia(x) for x in re.sub(r'<[^>]+>', ' ', seg).split('\n')]
    lineas = [x for x in lineas if x and 'Fecha/Hora' not in x]
    out, i = [], 0
    FH = re.compile(r'^(.+?)\s*\|\s*(\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?)$', re.I)
    while i < len(lineas):
        f = FH.match(lineas[i])
        if not f:
            i += 1
            continue
        # La fila NO tiene un número fijo de líneas: casi siempre es
        # sede + ciudad, pero cuando la sala va aparte son sede + sala +
        # ciudad («Colombo Americano - Sede centro» / «Sala 2» / «Medellín»).
        # Asumir 3 líneas metía «Sala 2» en el campo ciudad. Se leen líneas
        # hasta dar con una CIUDAD conocida: la lista es cerrada y sale del
        # anuncio del festival, así que una ciudad nueva se ve en el reporte
        # en vez de colarse como sede.
        partes, j = [], i + 1
        while j < len(lineas) and lineas[j] not in CIUDADES and j - i <= 3:
            partes.append(lineas[j]); j += 1
        if j < len(lineas) and lineas[j] in CIUDADES and partes:
            out.append({'dia_txt': f.group(1).strip(),
                        'hora': lib.hora24(f.group(2)),
                        # sede y sala quedan en un solo texto, con el mismo
                        # separador que ya usa la web; partirlas es del ensamblador
                        'sede_txt': ' - '.join(partes),
                        'ciudad': lineas[j]})
            i = j + 1
        else:
            desconocidas.append((f.group(1).strip(), partes, lineas[j] if j < len(lineas) else '?'))
            i += 1
    return out


def tecnica(s):
    d = {}
    for c in CAMPOS:
        m = re.search(r'>\s*' + re.escape(c) + r':\s*<', s)
        if not m:
            continue
        seg = re.sub(r'<[^>]+>', '\n', s[m.end():m.end() + 900])
        vals = [limpia(x) for x in seg.split('\n')]
        vals = [x for x in vals if x and not x.endswith(':')]
        if vals:
            d[c] = vals[0][:300]
    return d


def main():
    slugs = indice()
    print(f'fichas con badge «{BADGE}»: {len(slugs)}\n')
    obras, con_sin, con_hor = [], 0, 0
    for i, sl in enumerate(slugs, 1):
        s = lib.curl_get(f'{BASE}/pelicula/{sl}/', min_bytes=20000)
        if not s:
            print(f'[{i:3}] ?? {sl} — no descargó'); continue
        s = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', ' ', s, flags=re.S)
        t = re.search(r'<title>(.*?)\s*-\s*Cinemancia', s, re.S)
        sinop = tras_rotulo(s, 'Sinopsis')
        hor = horarios(s)
        obras.append({'slug': sl,
                      'title_web': html.unescape(t.group(1)).strip() if t else sl,
                      'synopsis_web': sinop,
                      'reflexion': tras_rotulo(s, 'Reflexión'),
                      'horarios': hor,
                      'tecnica': tecnica(s),
                      '_src': f'{BASE}/pelicula/{sl}/'})
        con_sin += bool(sinop); con_hor += bool(hor)
        print(f'[{i:3}/{len(slugs)}] {sl[:44]:46} sinopsis{"✓" if sinop else "·"} '
              f'funciones {len(hor)}', flush=True)
        time.sleep(0.6)

    d = {'_provenance': lib.provenance(
            f'fichas de {BASE}/pelicula/<slug>/ (índice filtrado por badge «{BADGE}»)',
            hallazgo=('la programación SÍ está publicada, obra por obra, en el bloque '
                      '«Horarios» de cada ficha: fecha, hora, teatro, ciudad y sala. No '
                      'hay página de programación general, pero el dato existe.'),
            nota='sede y sala vienen pegadas en un solo texto; partirlas es del ensamblador'),
         'obras': obras}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    funciones = sum(len(o['horarios']) for o in obras)
    print(f'\n{OUT.split("/")[-1]}  ·  {len(obras)} fichas · con sinopsis {con_sin} · '
          f'con horarios {con_hor} · {funciones} funciones')
    if desconocidas:
        print(f'\n   ⚠ filas de horario sin ciudad conocida ({len(desconocidas)}):')
        for d_, partes, c in desconocidas[:10]:
            print(f'      · {d_} · {partes} · «{c}»')
    ciudades = sorted({h['ciudad'] for o in obras for h in o['horarios']})
    print(f'   ciudades: {", ".join(ciudades)}')
    dias = sorted({h['dia_txt'] for o in obras for h in o['horarios']})
    print(f'   días distintos: {len(dias)}')


if __name__ == '__main__':
    main()
