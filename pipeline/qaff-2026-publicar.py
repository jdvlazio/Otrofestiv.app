# -*- coding: utf-8 -*-
"""Staged → `festivals/qaff-2026.json`. NO publica nada.

EL NOMBRE ENGAÑA, así que conviene decirlo aquí: esto no pone el festival en
producción. Es solo la transformación staging → festivals/, filtrando las
claves de trabajo. Para que QAFF sea visible hacen falta además la entrada en
FESTIVAL_CONFIG (sin ella el archivo es inerte: el splash se construye desde el
config, no desde los JSON) y el merge de la rama a main.

POR QUÉ SE CORRE ANTES DE PUBLICAR: `tools/audit.html` —el gate de revisión
film por film— lee `../festivals/<id>.json`, no el staging. Sin este paso, Juan
no puede hacer su revisión.

    python3 -m http.server 8765
    http://localhost:8765/tools/audit.html?fest=qaff-2026

CONSERVAR y por qué cada una:
  · `_src`        procedencia, obligatoria — el gate [sin-procedencia] la exige
                  por film. Se PODA a lo necesario: el id del evento de Boom y
                  el id de TMDB. Los `stills` (hasta 3 URLs de wixstatic por
                  film) son material de trabajo y engordan el archivo sin que
                  nadie los lea en runtime.
  · `_inherited`  procedencia POR CAMPO: qué dato salió del catálogo y cuál del
                  desc del evento. Es lo que permite auditar sin re-correr.
  · `_pendiente`  dato que la fuente no publica, marcado como tal.
  · `_nota`       sede a <60 m de otra ya revisada a mano. El guardián
                  [sedes-apiladas] la lee AQUÍ, en el publicado: si se filtra,
                  la nota no puede existir y el aviso no hay forma de cerrarlo.
                  Costó una tarde descubrirlo en FICDEH.

DESCARTAR:
  · `_src_titulo`   cómo se normalizó el título. Interesante en la rama, ruido
                    en producción; queda en el staging.
  · `_programada`   marca interna del ensamblado.
  · `_poster_provisional`, `_geocode_nota`, `_contact`, `_obras_sin_funcion`,
    `_etapa`        material de trabajo.
"""
import json, os, sys, collections, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f'{REPO}/festivals/staging/qaff-2026.json'
OUT = f'{REPO}/festivals/qaff-2026.json'

CONSERVAR = {'_src', '_inherited', '_pendiente', '_nota'}
SRC_UTIL = ('boom_event_id', 'tmdb_id')      # del _src, solo esto sobrevive


def _sinacento(s):
    """Título reducido a letras y dígitos, sin tildes ni mayúsculas.

    La PUNTUACIÓN también se cae, y no es un detalle: «Amazonas: Cocinas
    Indígenas…» contra «Amazonas Cocinas Indigenas…» son el mismo título —uno
    perdió las tildes Y los dos puntos—, pero comparando solo tildes salían
    distintos y el original se copiaba a title_en como si fuera inglés."""
    t = ''.join(c for c in unicodedata.normalize('NFKD', s or '')
                if not unicodedata.combining(c)).lower()
    return ''.join(c for c in t if c.isalnum())


def limpio(d):
    return {k: v for k, v in d.items() if not k.startswith('_') or k in CONSERVAR}


def poda_src(f):
    s = f.get('_src')
    if isinstance(s, dict):
        f['_src'] = {k: s[k] for k in SRC_UTIL if s.get(k)} or {'origen': 'calendario Boom del festival'}
    return f


def main():
    d = json.load(open(SRC, encoding='utf-8'))
    out = {k: v for k, v in d.items()
           if k not in ('films', 'venues', 'sections') and not k.startswith('_')}
    out['_provenance'] = d.get('_provenance', {})
    out['sections'] = {k: limpio(v) for k, v in d['sections'].items()}
    # `short` es el nombre que se PINTA; la clave lleva la ciudad pegada para
    # desambiguar sedes homónimas entre ciudades. El ensamblador de QAFF copiaba
    # la clave entera, así que la agenda leería «Biblioteca Departamental -
    # Quibdó» donde debe decir «Biblioteca Departamental». Misma regla que el
    # ensamblador genérico (ensamblar.py:251) y que ya siguen FICDEH y FINCA.
    out['venues'] = {}
    for k, v in d['venues'].items():
        v = limpio(v)
        if v.get('short') == k and ' - ' in k:
            v['short'] = k.rsplit(' - ', 1)[0]
        out['venues'][k] = v
    out['films'] = [poda_src(limpio(f)) for f in d['films']]

    # ── SOLO QUIBDÓ (decisión de Juan, 23 ago 2026) ───────────────────────────
    # El festival programa 14 funciones en Bogotá —Cinemateca y Museo Nacional—
    # en paralelo a Quibdó. El 11 ago se decidió incluirlas porque caían dentro
    # de la ventana oficial; el 23 ago Juan lo revierte: QAFF es en Quibdó.
    #
    # Cuesta 7 títulos que NO se proyectan en Quibdó y por tanto desaparecen del
    # catálogo: Iniciación en la Octava Dimensión, LAUNDRY (Uhlanjululo), Of Mud
    # and Blood, The Travelers, Wrong Generation y los dos Diálogo Improbable
    # —que se llevan su sección entera—. Queda constancia aquí porque el dato
    # existe en la fuente y la app no lo va a mostrar: es una omisión decidida,
    # no una que se nos escapó.
    _bog = {k for k, v in d['venues'].items() if v.get('city') != 'Quibdó'}
    out['films'] = [f for f in out['films'] if f['venue'] not in _bog]
    out['venues'] = {k: v for k, v in out['venues'].items() if k not in _bog}
    # NFC ANTES de tocar títulos. Las tablas de abajo buscan por clave exacta y
    # «Soñé su nombre» llegaba en NFD (n+tilde combinante): se ve idéntico, no
    # casa con nada, y la corrección se caía sin error ni síntoma. lib.normaliza
    # también lo hace, pero corre al final — demasiado tarde para estas tablas.
    for f in out['films']:
        for k, v in list(f.items()):
            if isinstance(v, str):
                f[k] = unicodedata.normalize('NFC', v)

    # ── TÍTULO: el original manda, el inglés va en title_en ───────────────────
    # (decisión de Juan, 23 ago 2026)
    #
    # QAFF venía al revés que los otros nueve festivales: el inglés en `title`
    # y el original en `title_orig`, un campo que nadie lee y que el contrato no
    # declara. `title_en` SÍ está declarado, lo leen cinco sitios de src/, y
    # filmDisplayTitle() ya sabe pintar «inglés arriba, original debajo» cuando
    # la interfaz está en inglés. FICDEH tiene 171 así; QAFF tenía UNO —«El
    # Capitán Anthony» → «Captain Anthony»—, que es el caso hecho bien.
    #
    # El inglés lo pusimos nosotros, tomándolo de la página de Selección
    # Oficial: el CALENDARIO del propio festival publica RELATOS DE LA
    # GUAJIRITA, CAIDA LIBRE, LA TINAJA, REFUGIAR EL GESTO y POSESAS.
    #
    # Dos casos, no uno:
    #   · mismo título mal escrito (Carabali→Carabalí) → se corrige `title` y
    #     NO se inventa un title_en: «Carabali» no es un título en inglés.
    #   · traducción de verdad (Free Fall / Caída Libre) → el original a
    #     `title`, el inglés a `title_en`.
    # La frontera es comparar sin tildes ni mayúsculas: si coinciden, es
    # ortografía; si no, son dos títulos.
    EN_LIMPIO = {  # el inglés venía pegado al original entre corchetes
        'POSESAS [Possessed]': 'Possessed',
    }

    # Dos obras que la regla de arriba NO podía ver, porque nunca tuvieron
    # title_orig: nadie leyó su afiche, así que no había con qué comparar.
    # Aparecieron cruzando el lbSlug —verificado— contra el título: un slug en
    # inglés sobre un título en español dice que falta un title_en, y uno que no
    # casa con ninguno de los dos dice que alguno está mal escrito.
    #   · «Mi viche todo el dia» → TMDB da «Mi viche todo el día» como original
    #     y Letterboxd (my-daily-viche) «My Daily Viche» como inglés.
    #   · «Soñé su nombre» ya estaba bien; solo le faltaba el inglés, que
    #     confirman Letterboxd (i-dreamed-his-name) y TMDB.
    A_MANO = {
        'Mi viche todo el dia': ('Mi viche todo el día', 'My Daily Viche'),
        'Soñé su nombre':       ('Soñé su nombre',       'I Dreamed His Name'),
    }
    for f in out['films']:
        if f['title'] in A_MANO:
            f['title'], f['title_en'] = A_MANO[f['title']]
    for f in out['films']:
        orig = f.pop('title_orig', None)
        if not orig or orig == f['title']:
            continue
        if _sinacento(orig) == _sinacento(f['title']):
            f['title'] = orig                      # solo ortografía
        else:
            f['title_en'] = EN_LIMPIO.get(f['title'], f['title'])
            f['title'] = orig

    _usadas = {f.get('section') for f in out['films']}
    out['sections'] = {k: v for k, v in out['sections'].items() if k in _usadas}

    # El contrato, aplicado en el ÚLTIMO paso: lib.normaliza es el dueño del
    # tipo de cada campo. QAFF emitía `year` como string en las 61 funciones,
    # igual que FICDEH y FICMA antes que él, y por el mismo motivo: la app hace
    # String(f.year) y nunca se quejó.
    # `flags` es DERIVADO: no existe en ninguna fuente, se calcula del país.
    # Las 55 banderas se arreglaron el 23 ago a mano SOBRE el publicado, porque
    # este ensamblador —a diferencia del genérico, que lo hace en ensamblar.py:138—
    # nunca las derivó. Re-correr el publicador las borraba en silencio. Derivarlas
    # aquí hace que la corrida sea idempotente y reproduzca lo ya commiteado.
    rep = collections.Counter()
    for f in out['films']:
        for o in [f] + list(f.get('film_list') or []):
            if not o.get('flags'):
                b = lib.banderas(o.get('country') or '')
                if b:
                    o['flags'] = b
                    rep['flags←country'] += 1
            lib.normaliza(o, rep)

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              separators=(',', ':'))

    sin_src = [f['title'] for f in out['films'] if not f.get('_src')]
    priv = collections.Counter(k for f in out['films'] for k in f if k.startswith('_'))
    print(f'{OUT.split("/")[-1]}  {os.path.getsize(OUT)//1024} KB')
    print(f'   films {len(out["films"])} · sedes {len(out["venues"])} · secciones {len(out["sections"])}')
    print(f'   claves privadas conservadas: {dict(priv)}')
    print(f'   contrato aplicado: {dict(rep) or "nada que coaccionar"}')
    print(f'   films sin _src: {len(sin_src)}' + (f'  ⚠️ {sin_src[:4]}' if sin_src else ' ✅'))
    ciudades = sorted({v['city'] for v in out['venues'].values()})
    print(f'   ciudades: {", ".join(ciudades)}')
    print(f'\n   NO está publicado. Para verlo: python3 -m http.server 8765')
    print(f'   → http://localhost:8765/tools/audit.html?fest=qaff-2026')
    print(f'   Falta la entrada en FESTIVAL_CONFIG y el merge para que sea visible en la app.')
    if sin_src:
        sys.exit(1)


if __name__ == '__main__':
    main()
