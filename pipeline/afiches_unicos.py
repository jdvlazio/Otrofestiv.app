#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""afiches_unicos.py — UN afiche por obra, y cuándo uno nuevo lo reemplaza.

POR QUÉ EXISTE (23 nov 2026, Juan): «el afiche de una película debería ser uno
solo». Medido ese día: 271 obras con más de un afiche entre festivales, 761
imágenes; 133 eran la misma imagen repetida. El afiche es de la OBRA: se elige
una vez y queda en catalogo/decisiones.json (campo `afiche`), que
catalogo_construir.py respeta siempre.

QUÉ SE COMPARA: la IMAGEN, no la etiqueta (`posterSource` miente: tarjetas de
sección de SiembraFest decían «oficial», y había fotogramas marcados igual).
La comparación tolera recortes de hasta 13 % por lado.

  misma imagen   ≥ 0,97   el mismo diseño; puede variar tamaño o recorte
  otra versión   ≥ 0,80   idioma, laureles, créditos o encuadre: no decide solo
  otro diseño    < 0,80

EL CRITERIO PARA REEMPLAZAR el afiche del almacén cuando llega uno nuevo:
  · lo nuevo no es afiche (tarjeta, apaisado, editorial) → se MANTIENE;
  · lo que hay no es afiche y lo nuevo sí               → se REEMPLAZA;
  · misma imagen y la nueva es más completa, o igual de completa y claramente
    más grande (≥ 1,3×, hasta 1000 px)                  → se REEMPLAZA;
  · misma imagen y nada mejora                          → se MANTIENE;
  · otra versión u otro diseño                          → se REVISA: la campaña
    de una obra cambia con su distribución, y eso lo mira una persona.
Lo ya comparado queda en `vistas` de la decisión y no se vuelve a preguntar.
Una elección hecha a mano por Juan nunca se reemplaza sola: se revisa.

    python3 pipeline/afiches_unicos.py --revisar [<festival>]   # no escribe
    python3 pipeline/afiches_unicos.py --registrar <clases.json>
"""
import itertools
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISMA, VERSION = 0.97, 0.80
_M = (0, .04, .08, .13)
PESO = {'tmdb': 0, 'oficial': 1, 'custom': 2, 'editorial': 3}


def abrir(ruta):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 150_000_000
    im = Image.open(ruta)
    w, h = im.size
    im.draft('L', (200, 300))
    im = im.convert('L')
    im.thumbnail((200, 300))
    return {'im': im, 'w': w, 'h': h}


def _recortes(im):
    import numpy as np
    from PIL import Image
    W, H = im.size
    out = []
    for l, t, r, b in itertools.product(_M, repeat=4):
        g = np.asarray(im.resize((24, 36), Image.BILINEAR, box=(l * W, t * H, W - r * W, H - b * H)), float)
        out.append((g - g.mean()) / (g.std() + 1e-6))
    return np.stack(out)


def similitud(a, b):
    """(parecido, cuánto más completa es `a`). a y b, de abrir()."""
    import numpy as np
    for x in (a, b):
        if 'rec' not in x:
            x['rec'] = _recortes(x['im'])
    ka = float(np.tensordot(a['rec'], b['rec'][0], 2).max()) / 864   # b cabe dentro de a
    kb = float(np.tensordot(b['rec'], a['rec'][0], 2).max()) / 864
    return max(ka, kb), ka - kb


def es_afiche(x, fuente='', tarjeta=False):
    return not tarjeta and fuente != 'editorial' and x['w'] / x['h'] <= .95


def decidir(actual, nuevo, a_mano=False):
    """'mantener' | 'reemplazar' | 'revisar'. Cada lado: {x: abrir(), fuente, tarjeta}."""
    va = es_afiche(actual['x'], actual.get('fuente'), actual.get('tarjeta'))
    vn = es_afiche(nuevo['x'], nuevo.get('fuente'), nuevo.get('tarjeta'))
    if not vn:
        return 'mantener'
    if not va:
        return 'revisar' if a_mano else 'reemplazar'
    k, completa = similitud(nuevo['x'], actual['x'])
    if k < MISMA:
        return 'revisar'
    ancho = lambda y: min(min(y['w'], y['h']), 1000)
    mejor = completa > .012 or (completa > -.012 and ancho(nuevo['x']) >= 1.3 * ancho(actual['x']))
    if not mejor:
        return 'mantener'
    return 'revisar' if a_mano else 'reemplazar'


def veredicto(fuente, x=None):
    """El veredicto del catálogo para el afiche elegido."""
    if fuente == 'editorial' or (x and x['w'] / x['h'] > .95):
        return 'fotograma'
    return 'oficial-festival' if fuente == 'custom' else 'oficial'


def _ruta(u):
    """El archivo local de un póster publicado, o None (lo remoto no se baja acá)."""
    p = REPO + str(u) if str(u).startswith('/assets/') else None
    return p if p and os.path.exists(p) else None


def revisar(solo=None):
    """Pósters publicados que no son el del almacén → [(acción, obra, festival, publicado, almacén)]."""
    import glob
    import json
    import sys
    sys.path.insert(0, os.path.join(REPO, 'pipeline'))
    import catalogo
    from afiche_criterio import es_tarjeta_de_texto
    obs = catalogo.obras()
    dec = {d['work_id']: d for d in catalogo.decisiones() if d['campo'] == 'afiche'}
    cache, out, vistos = {}, [], set()

    def lado(u, fuente):
        r = _ruta(u)
        if not r:
            return None
        if r not in cache:
            cache[r] = abrir(r)
        return {'x': cache[r], 'fuente': fuente, 'tarjeta': es_tarjeta_de_texto(r)}

    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        d = json.load(open(p, encoding='utf-8'))
        if (solo and fid != solo) or not isinstance(d, dict):
            continue
        for f in d.get('films', []):
            for o in (f.get('film_list') or [f]):
                w, u = o.get('work_id'), o.get('poster')
                e = dec.get(w)
                if not e or not u or u == e['valor']['archivo'] or u in (e.get('vistas') or []) or (w, u) in vistos:
                    continue
                vistos.add((w, u))
                a = lado(e['valor']['archivo'], 'editorial' if e['valor']['veredicto'] == 'fotograma' else '')
                n = lado(u, o.get('posterSource') or '')
                acc = decidir(a, n, a_mano=e.get('a_mano', False)) if a and n else 'revisar'
                out.append((acc, obs.get(w, {}).get('titulo_original', o.get('title')), fid, u, e['valor']['archivo']))
    return out


def registrar(ruta):
    """Las elecciones aprobadas (salida de la comparación) → catalogo/decisiones.json."""
    import io
    import json
    import sys
    sys.path.insert(0, os.path.join(REPO, 'pipeline'))
    import catalogo
    decs = catalogo.decisiones()
    ya = {d['work_id'] for d in decs if d['campo'] == 'afiche'}
    n = 0
    for e in json.load(io.open(ruta, encoding='utf-8')):
        if e['work_id'] in ya:
            continue
        decs.append({'work_id': e['work_id'], 'campo': 'afiche', 'valor': e['valor'], 'motivo': e['motivo'],
                     'fecha': e['fecha'], 'quien': e['quien'], 'vistas': e.get('vistas') or []})
        n += 1
    io.open(os.path.join(catalogo.DIR, 'decisiones.json'), 'w', encoding='utf-8').write(
        json.dumps(decs, ensure_ascii=False, indent=1))
    return n


if __name__ == '__main__':
    import sys
    from collections import Counter
    if '--registrar' in sys.argv:
        print(registrar(sys.argv[sys.argv.index('--registrar') + 1]), 'decisiones de afiche registradas')
    elif '--revisar' in sys.argv:
        xs = revisar(next((a for a in sys.argv[1:] if not a.startswith('--')), None))
        for x in xs:
            if x[0] != 'mantener':
                print(f'{x[0]:10} «{x[1]}» · {x[2]}: {x[3]}  (almacén: {x[4]})')
        print(dict(Counter(x[0] for x in xs)))
    else:
        sys.exit(__doc__)
