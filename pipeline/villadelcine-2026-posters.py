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


def forma(ruta):
    """(ancho, alto) de la imagen ya bajada. (0, 0) si no se puede leer."""
    try:
        from PIL import Image
        return Image.open(ruta).size
    except Exception:
        return (0, 0)


def _slug_afiche(t):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', norm(t))).strip('-')[:60]


def main():
    web = json.load(open(f'{ST}/villadelcine-2026-obras-web.json',
                         encoding='utf-8'))['obras']
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
    for o in web:
        if not o['afiches']:
            sin.append(o['titulo'])
            continue
        if norm(o['titulo']) in con_tmdb:
            continue                       # el de TMDB manda: es el original
        url = o['afiches'][0]
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
        if not h or not (R_MIN <= w / h <= R_MAX):
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
                             'posterSource': 'oficial', '_url': url,
                             '_medida_original': f'{w}x{h}'}

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
