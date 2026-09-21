#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-posters.py — el afiche que el propio festival publica.

POR QUÉ EXISTE. `enriquecer.py --posters` trae los de TMDB, y para un festival
de cortos eso cubre poquísimo: casi ninguna de estas obras tiene ficha. Pero el
festival SÍ publica imágenes por obra en su web, y las tenemos extraídas desde
el primer día en `-obras-web.json`.

════════════════════════════════════════════════════════════════════════════
UN STILL NO ES UN AFICHE, y confundirlos salió caro (21 sep 2026, lo vio Juan
en la app ya publicada). La galería de la ficha mezcla el afiche con FOTOS DE
RODAJE, y este script tomaba la primera y la marcaba `oficial` SIN MIRAR LA
IMAGEN. `encuadrar-posters.py` estira a 780×1170 todo lo que no sea
`editorial`, así que 67 fotogramas apaisados salieron a producción deformados
entre un 62% y un 74%: «Amor a primera vista» (2560×1349), «Quimera»
(2048×1152), «Benditos los Viejos» (1920×759).

Los nombres de archivo lo decían y nadie los leyó: `Timeline_4_01_16_57_01`,
`Screenshot_129`, `Captura-de-pantalla-2026-07-31`, `witch_and_frog.still3_`.
De las 81 URLs, solo TRES llevan «poster» en el nombre.

LA REGLA (Juan): para estos stills se usa NUESTRO PÓSTER. Y nuestro póster no
se pone: se deja el hueco. Una obra sin `poster` cae al paso 8 de
`getFilmPoster` y la app construye el generativo tipográfico. Poner el
fotograma como `editorial` sería la otra opción —la vista lo encuadraría a
16:9 sin deformarlo— pero un fotograma de rodaje no identifica la obra, y la
jerarquía de la casa dice que la Escalera entra donde íbamos a inventar un
afiche.

POR ESO ESTE PASO MIDE. Solo entra la imagen VERTICAL, que es la forma de un
afiche. Lo apaisado y lo cuadrado se descartan con su medida escrita.
════════════════════════════════════════════════════════════════════════════

QUÉ HACE. Baja el afiche de cada obra a `assets/villadelcine-2026/<slug>.jpg` y
escribe el sidecar que el ensamblador lee. Respeta lo que TMDB ya trajo: si una
obra tiene ficha verificada, su póster manda —es el original y suele estar
mejor—; el del festival entra donde no hay otro.

NO TOCA LO YA BAJADO (write-once): los assets pasan después por
`encuadrar-posters.py`, y volver a bajarlos desharía ese trabajo.

Lee   festivals/staging/villadelcine-2026-obras-web.json
Esc.  festivals/staging/villadelcine-2026-posters.json + assets/villadelcine-2026/
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/villadelcine-2026'
OUT = f'{ST}/villadelcine-2026-posters.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')


# Un afiche es VERTICAL. El rango cubre desde el 2:3 canónico (0,667) hasta el
# 4:5 que usan algunos festivales, con holgura. Medido sobre las 81 de este
# festival: 11 caen aquí y son afiches de verdad; 67 son fotogramas apaisados
# (r de 1,78 a 2,53) y 3 son cuadradas.
R_MIN, R_MAX = 0.55, 0.85
# …Y SE ABRE (Juan, 21 sep 2026: «necesito solución urgente a los posters. Usa
# la página»). La ventana estrecha dejaba fuera afiches de verdad que la página
# publica: los 9:16 de «Tiro Libre» (385×800) y «Protecting Our Territory 360»
# (400×800), el 1354×2560 de «Cuadrilleros» y las carátulas cuadradas de
# «Prompt Zero», «Floppy» y «Sabor a mí». Entra todo lo que NO es apaisado;
# `encuadrar-posters.py` ya no estira más del 16% —recorta al centro—, así que
# abrir la ventana no vuelve a deformar nada. Lo apaisado sigue fuera: eso sí
# es un fotograma.
R_MIN, R_MAX = 0.44, 1.06

# UN VIDEOCLIP NO TIENE AFICHE 2:3, TIENE CARÁTULA 16:9, y descartarla por
# apaisada es aplicarle la regla de otro formato. La categoría de la página lo
# dice en su encabezado: «MEJOR VIDEOCLIP NACIONAL». Estas entran como
# `editorial`, que es el carril que YA existe para el 16:9 y que
# `encuadrar-posters.py` respeta sin llevarlo al lienzo 2:3 (docs/POSTERS.md
# §4) — así que no se deforma nada.
#
# No es una excepción inventada para salvar dos archivos: es la diferencia
# entre «esta imagen no identifica la obra» (un fotograma de rodaje, que es lo
# que la regla de Juan manda descartar) y «esta imagen ES la portada que
# publicó su autor, en la proporción de su formato».
CATEGORIA_16_9 = 'videoclip'


def forma(ruta):
    """(ancho, alto) de la imagen ya bajada. (0, 0) si no se puede leer."""
    try:
        from PIL import Image
        return Image.open(ruta).size
    except Exception:
        return (0, 0)


def _slug_afiche(t):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', norm(t))).strip('-')[:60]


SELECCION = 'https://villadelcine.com/festival-2024-2/'


def de_seleccion():
    """[(categoría, título, url)] de la página de SELECCIÓN OFICIAL.

    AQUÍ ESTÁN LOS AFICHES, y no en la página de cada obra. La ficha de una
    obra tiene una galería de FOTOS DE RODAJE; la de Selección Oficial tiene
    una tarjeta por obra con su afiche de fondo. Los nombres de archivo lo
    dicen: `poster-quimera-…`, `APVU-POSTER_FINAL-…`, `AFICHE-MI-TESORO-V1-…`.

    Se ven RECORTADOS en la web porque la tarjeta usa `background-size:cover`
    sobre el archivo entero —es recorte de CSS, no del archivo—: pedido
    directo, «Quimera» llega en 1587×2245 completo. Lo vio Juan (21 sep 2026)
    y es lo que llevó de 10 afiches a 72.

    Y SE LEE LA CATEGORÍA, que es el <h5> que encabeza cada fila (Juan, 21 sep
    2026: «Mucho gusto es Mejor Videclip Nacional, no leíste bien»). La
    categoría dice QUÉ FORMA es la correcta para esa tarjeta: un VIDEOCLIP
    trae carátula 16:9 y no es un fotograma robado; un CORTOMETRAJE VERTICAL
    trae un afiche 9:16 y no es un error de medida. Una sola ventana de
    proporción para las 86 no puede distinguirlos.
    """
    r = subprocess.run(['curl', '-sSL', '--max-time', '60', '-A', UA, SELECCION],
                       capture_output=True)
    h = r.stdout.decode('utf-8', 'replace')
    import html as _html, bisect
    heads = [(m.start(), _html.unescape(m.group(1)).strip())
             for m in re.finditer(r'<h[1-6][^>]*class="elementor-heading-title'
                                  r'[^"]*"[^>]*>([^<]{3,70})</h[1-6]>', h)]
    offs = [o for o, _ in heads]
    tarjetas = []
    for m in re.finditer(r'background-image:\s*url\((https://villadelcine\.com/'
                         r'wp-content/uploads/2026/[^)]+)\)', h):
        seg = h[m.end():m.end() + 3000]
        t = re.findall(r'class="ue_title[^"]*"[^>]*>([^<]{2,90})<', seg)
        if not t:
            continue
        i = bisect.bisect_right(offs, m.start()) - 1
        tarjetas.append((heads[i][1] if i >= 0 else '',
                         _html.unescape(t[0]).strip(), m.group(1)))
    if len(tarjetas) < 80:
        sys.exit(f'✗ la página de Selección Oficial devolvió {len(tarjetas)} '
                 f'tarjetas: esperábamos 86. ¿Cambió la maqueta?')
    return tarjetas


def clave(t):
    """La forma del título con la que se cruzan las dos fuentes.

    LA PÁGINA Y EL PDF NO ESCRIBEN EL MISMO TÍTULO, y con `norm()` a secas seis
    afiches que SÍ estaban se daban por ausentes: «Cuadrileros, orgullo y
    legado» contra «Cuadrileros orgullo y legado» (la coma), «Momentos en
    movimiento…» contra «…Colombia.» (el punto final) y «Sabor a mí (acústico /
    bolero jazz)» contra «Sabor a mi (Acústico/ BoleroJazz)  Tatiana Jáuregui &
    Husil» (la página le añade los intérpretes y junta dos palabras).

    Así que se compara SIN PUNTUACIÓN NI ESPACIOS: lo que queda es la cadena de
    letras, que es lo que de verdad coincide. El cruce por prefijo —abajo— se
    apoya en esta misma forma.
    """
    return re.sub(r'[^a-z0-9]+', '', norm(t))


def main():
    web = json.load(open(f'{ST}/villadelcine-2026-obras-web.json',
                         encoding='utf-8'))['obras']
    # LA PÁGINA DE SELECCIÓN OFICIAL ES LA ESPINA, NO LA LISTA DE FICHAS.
    #
    # Este bucle recorría `obras-web.json` —las obras que tienen PÁGINA DE
    # FICHA en la web— y consultaba la página de Selección Oficial solo para
    # ellas. Seis obras del festival no tienen ficha propia, así que su tarjeta
    # NUNCA se miraba aunque estuviera ahí: «Korebaju Pai Rekocho» (566×800),
    # «The Guanentá Symphony» (540×800) y «Momentos en Movimiento» (595×842)
    # son afiches verticales de verdad, dentro de la ventana, y se publicaron
    # con el generativo nuestro. Lo vio Juan el 21 sep 2026 mirando la fila de
    # RAÍCES en la propia página: «En villadelcine.com están todos, no?».
    #
    # Ahora las obras SON la unión de las dos fuentes de catálogo (las fichas
    # de la web y las del PDF), y la tarjeta se busca para todas.
    pdf = json.load(open(f'{ST}/villadelcine-2026-obras-pdf.json',
                         encoding='utf-8'))['obras']
    vistas, obras = set(), []
    # EL PDF VA PRIMERO: el crudo busca el afiche por el título del PDF, así
    # que la clave del sidecar tiene que ser esa y no la larga de la web.
    galeria = {clave(o['titulo']): o['afiches'] for o in web}
    for o in ([{'titulo': o['titulo'], 'afiches': galeria.get(clave(o['titulo']), [])}
               for o in pdf] + web):
        k = clave(o['titulo'])
        # la misma obra con el título largo de la web y el corto del PDF
        # («Sabor a mi … Tatiana Jáuregui & Husil» / «Sabor a mí (acústico …)»)
        # es UNA obra: bajaba dos veces y dejaba un asset huérfano.
        if not k or any(k.startswith(v) or v.startswith(k)
                        for v in vistas if min(len(k), len(v)) >= 12):
            continue
        vistas.add(k)
        obras.append(o)
    # El afiche por título, de la página de Selección Oficial. Sustituye a la
    # galería de la ficha, que son fotos de rodaje.
    sel, cat = {}, {}
    for c, t, u in de_seleccion():
        sel.setdefault(clave(t), u)
        cat.setdefault(clave(t), c)

    def tarjeta(t):
        """(url, categoría) de la tarjeta de esta obra, o (None, '')."""
        k = clave(t)
        if k in sel:
            return sel[k], cat[k]
        # la página le añade cosas al título («… Tatiana Jáuregui & Husil»):
        # vale el prefijo, y solo si es INEQUÍVOCO —una sola tarjeta empieza
        # así—, que es lo que impide que «Sierra» se lleve la de otra.
        if len(k) >= 12:
            c = [x for x in sel if x.startswith(k)]
            if len(c) == 1:
                return sel[c[0]], cat[c[0]]
        return None, ''
    enr_p = f'{ST}/villadelcine-2026-enriquecido.json'
    con_tmdb = set()
    if os.path.exists(enr_p):
        # `poster_path` Y `poster`: el enricher escribe el PATH de TMDB
        # («/abc.jpg»), no una URL, y mirando solo `poster` este conjunto
        # salía VACÍO — con lo cual el paso bajaba el still de la web ENCIMA
        # del afiche de TMDB, que comparten nombre de archivo. Se vio el 21
        # sep: 17 obras con ficha verificada y «0 los trae TMDB».
        _e = json.load(open(enr_p, encoding='utf-8'))
        con_tmdb = {norm(o['titulo']) for o in _e.get('obras', [])
                    if o.get('poster') or o.get('poster_path')}

    os.makedirs(ASSETS, exist_ok=True)
    mapa, bajados, ya, sin, descartados = {}, 0, 0, [], []
    for o in obras:
        url_sel, categoria = tarjeta(o['titulo'])
        if not url_sel and not o['afiches']:
            sin.append(o['titulo'])
            continue
        if norm(o['titulo']) in con_tmdb:
            continue                       # el de TMDB manda: es el original
        # EL AFICHE DE SELECCIÓN OFICIAL MANDA. La galería de la ficha es el
        # último recurso, y casi siempre la descarta la medida por apaisada.
        url = url_sel or o['afiches'][0]
        dest = f'{ASSETS}/{_slug_afiche(o["titulo"])}.jpg'
        # SE MIDE EL ORIGINAL, SIEMPRE, Y NO LO QUE HAY EN assets/.
        #
        # La primera versión de esta comprobación medía el archivo del destino,
        # y el destino puede ser un estirado de una corrida anterior: 780×1170
        # pasa el examen de «¿es vertical?» con nota. Así volvieron a entrar
        # tres que la medida ya había descartado, entre ellas «Le Jeune
        # Sofiane», cuyo archivo se llama literalmente `3-banner_…` y mide
        # 1920×798. Un verificador que se mira a sí mismo no verifica nada.
        #
        # Por eso se baja SIEMPRE a un temporal, se mide ahí, y solo entonces
        # se decide. El write-once se conserva donde importa: si el afiche ya
        # está en assets/ no se pisa —porque ya pasó por encuadrar-posters—,
        # pero la decisión de si vale se toma con el original en la mano.
        import tempfile
        tmp = tempfile.mktemp(suffix='.img')
        r = subprocess.run(['curl', '-sSL', '--max-time', '45', '-A', UA,
                            '-o', tmp, url], capture_output=True)
        if r.returncode or not os.path.exists(tmp) or os.path.getsize(tmp) < 4000:
            sin.append(f'{o["titulo"]} (no se pudo bajar)')
            if os.path.exists(tmp):
                os.remove(tmp)
            continue
        w, h = forma(tmp)
        # La carátula 16:9 de un VIDEOCLIP no se mide con la regla del afiche:
        # entra por el carril `editorial`, que nadie estira. Solo cuenta si la
        # imagen es de verdad apaisada —un videoclip con afiche vertical es un
        # afiche vertical y sigue el camino normal—.
        es_16_9 = bool(h) and CATEGORIA_16_9 in norm(categoria) and w / h > R_MAX
        if not h or not (es_16_9 or R_MIN <= w / h <= R_MAX):
            descartados.append((o['titulo'], w, h, round(w / h, 2) if h else 0,
                                url.split('/')[-1]))
            os.remove(tmp)
            if os.path.exists(dest):
                os.remove(dest)      # sin huérfanos en assets/
            continue
        if os.path.exists(dest) and os.path.getsize(dest) > 4000:
            os.remove(tmp)
            ya += 1
        else:
            # LA WEB LOS SIRVE EN WEBP aunque el enlace diga otra cosa, y
            # `encuadrar-posters` —que usa sips— no puede reescribir un webp
            # con nombre .jpg. Se convierte al mover, que es donde cuesta una
            # línea y no un arreglo aguas abajo.
            try:
                from PIL import Image
                Image.open(tmp).convert('RGB').save(dest, 'JPEG', quality=90)
            except Exception as e:
                sin.append(f'{o["titulo"]} (no se pudo convertir: {str(e)[:40]})')
                os.remove(tmp)
                continue
            os.remove(tmp)
            bajados += 1
        mapa[o['titulo']] = {'poster': f'/assets/villadelcine-2026/{os.path.basename(dest)}',
                             'posterSource': 'editorial' if es_16_9 else 'oficial',
                             '_url': url, '_medida_original': f'{w}x{h}',
                             **({'_categoria': categoria} if categoria else {})}

    json.dump({'_provenance': provenance(
        'villadelcine.com — el afiche que el festival publica en la página de cada obra',
        que_aporta='el póster de las obras que no tienen ficha en TMDB, que en un '
                   'festival de cortos son casi todas',
        url='https://villadelcine.com/festival-2024-2/',
        metodo='write-once: lo ya bajado no se vuelve a pedir, porque después pasa '
               'por encuadrar-posters.py y re-bajarlo desharía el encuadre'),
        'posters': mapa,
        '_descartados_por_forma': [
            {'titulo': t, 'medida': f'{w}x{h}', 'r': r, 'archivo': f,
             '_por_que': 'apaisada o cuadrada: es un fotograma, no un afiche. '
                         'La obra se publica sin póster y la app le pone el '
                         'generativo nuestro.'}
            for t, w, h, r, f in sorted(descartados, key=lambda x: -x[3])]},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(mapa)} afiches del festival · {bajados} bajados ahora · {ya} ya estaban '
          f'· {len(con_tmdb)} los trae TMDB → {os.path.basename(OUT)}')
    if descartados:
        print(f'   {len(descartados)} descartadas por NO SER VERTICALES '
              f'(fotogramas): la obra va con el póster generativo nuestro')
        for t, w, h, r, f in sorted(descartados, key=lambda x: -x[3])[:8]:
            print(f'      {t[:30]:32} {w}x{h} r={r}  {f[:40]}')
    if sin:
        print(f'   sin afiche ({len(sin)}): ' + ', '.join(x[:26] for x in sin[:6]))


if __name__ == '__main__':
    main()
