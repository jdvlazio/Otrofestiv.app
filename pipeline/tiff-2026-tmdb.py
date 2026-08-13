# -*- coding: utf-8 -*-
"""Enriquece el catálogo de TIFF con TMDB, y de paso audita a Letterboxd.

En los festivales anteriores TMDB era el BUSCADOR: le dábamos un título y él
proponía candidatos que había que verificar (director + año/duración) para no
repetir el desastre de Tribeca. Aquí no busca nada: el `tmdb_id` ya lo declaró
Letterboxd en la ficha de cada obra.

Eso no elimina la verificación, la reorienta. Un id declarado también puede
estar mal —el mapeo de Letterboxd lo mantiene gente— así que se aplica el mismo
criterio de siempre, ahora como AUDITORÍA: si el director de TMDB no coincide
con el de Letterboxd, la obra sale marcada `discrepa` y se mira a mano. Nunca se
descarta sola: dos fuentes que no concuerdan es una pregunta, no un veredicto.

Los créditos se piden en `en-US` a propósito. En `es-CO` TMDB devuelve el nombre
del director transliterado al alfabeto de destino («蔡明亮», «Евгения
Арбугаева»), y entonces la comparación falla por motivos ortográficos y no de
identidad. La sinopsis, en cambio, sí se pide en español: es lo que se lee.

Sin sinopsis en español NO se cae a la inglesa aquí. Se reporta el hueco, y esa
decisión de copy es de Juan.
"""
import json, os, re, ssl, sys, time, unicodedata, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
KEY = os.environ.get('TMDB_API_KEY')
if not KEY:
    sys.exit('Falta $TMDB_API_KEY en el entorno (vive en ~/.zshrc).')
API = 'https://api.themoviedb.org/3'


def _contexto_ssl():
    """El Python de python.org en macOS no usa el llavero del sistema.

    Sin esto, TODA petición muere con CERTIFICATE_VERIFY_FAILED. Lo pagamos
    caro: la primera corrida se pasó una hora reintentando y durmiendo sin
    escribir una línea, porque el error de transporte se trataba como si fuera
    un fallo pasajero de la API.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _contexto_ssl()


def get(path, **params):
    """→ dict, o None si TMDB dice 404 (obra sin ficha, estado legítimo).

    Solo reintenta lo que puede mejorar solo: timeouts y 5xx. Un 401 o un fallo
    de certificado no mejoran esperando, así que abortan de una con el motivo a
    la vista. La regla: si nada va a funcionar nunca, hay que enterarse en la
    primera obra, no en la 259.
    """
    url = f'{API}{path}?api_key={KEY}&' + urllib.parse.urlencode(params)
    for intento in range(4):
        try:
            with urllib.request.urlopen(url, timeout=25, context=CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (401, 403):
                sys.exit(f'TMDB responde {e.code} — revisa $TMDB_API_KEY. Abortado.')
            if e.code < 500:
                return None
        except urllib.error.URLError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e.reason):
                sys.exit('SSL: falta el certificado raíz. Instala `certifi` '
                         '(pip3 install certifi) o corre "Install Certificates.command" '
                         'del instalador de Python. Abortado.')
        except Exception:
            pass
        time.sleep(1.5 * (intento + 1))
    return '__falla__'


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def director_coincide(a, b):
    """Comparación por token largo, con dos salvavidas que costaron una corrida.

    La versión ingenua —intersecar tokens de más de 3 letras tras pasar el
    nombre a ASCII— marcaba como discrepancia dos casos que no lo eran:

    1. Nombres de tokens cortos. «Sue Kim» contra «Sue Kim», idénticos, daban
       conjuntos vacíos y por tanto intersección vacía. Se marcaba una obra
       perfectamente sana.
    2. Alfabetos no latinos. «濱口竜介» se normaliza a nada, así que cualquier
       nombre CJK, árabe o tailandés chocaba contra su equivalente latino.

    De ahí el orden: primero igualdad normalizada, después el caso de conjunto
    vacío —donde no hay nada que intersecar y comparar cadenas es lo honesto—
    y solo al final la intersección de tokens.
    """
    na, nb = norm(a), norm(b)
    if na and na == nb:
        return True
    ta = {t for t in na.split() if len(t) > 3}
    tb = {t for t in nb.split() if len(t) > 3}
    if not ta or not tb:
        # Sin tokens largos en algún lado: o son nombres cortos, o uno de los
        # dos no es alfabeto latino. En ninguno de los dos casos la
        # intersección significa nada, así que aquí NO se decide.
        return None
    return bool(ta & tb)


def main():
    src = json.load(open(f'{ST}/tiff-2026-letterboxd.json', encoding='utf-8'))
    obras = src['obras']
    out, discrepan, sin_ficha, sin_sinopsis = [], [], [], []

    for i, o in enumerate(obras, 1):
        det = get(f'/movie/{o["tmdb_id"]}', language='es-CO', append_to_response='credits')
        if det == '__falla__':
            sys.exit(f'TMDB no responde tras 4 intentos en «{o["titulo_lb"]}». '
                     f'Abortado en la obra {i} para no producir 259 huecos falsos.')
        if not det:
            sin_ficha.append(o['titulo_lb'])
            print(f'[{i:3}/{len(obras)}] !!  {o["titulo_lb"][:44]:46} id {o["tmdb_id"]} sin ficha')
            continue
        dirs = [c['name'] for c in det.get('credits', {}).get('crew', [])
                if c.get('job') == 'Director']
        if not dirs:   # créditos en inglés: ver docstring
            en = get(f'/movie/{o["tmdb_id"]}', language='en-US', append_to_response='credits')
            dirs = [c['name'] for c in (en or {}).get('credits', {}).get('crew', [])
                    if c.get('job') == 'Director']

        lb_dirs = o.get('directores') or []

        def _veredicto(cands):
            """→ True/False/None. None = la comparación no puede decidir."""
            if not lb_dirs or not cands:
                return True          # hueco en una fuente: nada que auditar
            vs = [director_coincide(a, b) for a in lb_dirs for b in cands]
            if any(v is True for v in vs):
                return True
            return False if any(v is False for v in vs) else None

        concuerda = _veredicto(dirs)
        if concuerda is not True:
            # TMDB devuelve el nombre en su alfabeto original cuando se pide en
            # es-CO. Antes de acusar discrepancia se pregunta en en-US, que es
            # donde los nombres viven transliterados y comparables.
            en = get(f'/movie/{o["tmdb_id"]}', language='en-US',
                     append_to_response='credits')
            dirs_en = [c['name'] for c in (en or {}).get('credits', {}).get('crew', [])
                       if c.get('job') == 'Director'] if en != '__falla__' else []
            if dirs_en:
                dirs = dirs_en
                concuerda = _veredicto(dirs_en)
        # Indecidible no es discrepancia: se deja pasar y se anota aparte.
        indeciso = concuerda is None
        concuerda = concuerda is not False

        sin_es = not (det.get('overview') or '').strip()
        if sin_es:
            sin_sinopsis.append(o['titulo_lb'])

        reg = dict(o)
        reg.update({
            'titulo_original': det.get('original_title') or o['titulo'],
            'idioma_original': det.get('original_language'),
            'paises': [p['iso_3166_1'] for p in det.get('production_countries', [])],
            'generos': [g['name'] for g in det.get('genres', [])],
            'anio_tmdb': (det.get('release_date') or '')[:4] or None,
            'duracion_tmdb': det.get('runtime') or None,
            'sinopsis_es': (det.get('overview') or '').strip() or None,
            'poster_tmdb': det.get('poster_path'),
            'directores_tmdb': dirs,
            '_auditoria': ('sin_decidir' if indeciso else
                           'director✓' if concuerda else 'DISCREPA'),
        })
        out.append(reg)
        if not concuerda:
            discrepan.append({'titulo': o['titulo_lb'], 'tmdb_id': o['tmdb_id'],
                              'letterboxd': lb_dirs, 'tmdb': dirs})
        marca = 'OK ' if concuerda else '?? '
        print(f'[{i:3}/{len(obras)}] {marca}{o["titulo_lb"][:44]:46} '
              f'{"es" if not sin_es else "--"} {det.get("poster_path") and "post" or "----"}',
              flush=True)
        time.sleep(0.06)

    salida = f'{ST}/tiff-2026-tmdb.json'
    json.dump({'_provenance': provenance('api.themoviedb.org/3',
                                         metodo='tmdb_id declarado por Letterboxd'),
               '_metodo': 'tmdb_id declarado por Letterboxd; TMDB no busca, solo enriquece. '
                          'La comparación de director es AUDITORÍA del mapeo ajeno: discrepar '
                          'marca la obra para revisión a mano, no la descarta.',
               '_obras': len(out), '_discrepan': discrepan,
               '_sin_sinopsis_es': sin_sinopsis, '_sin_ficha_tmdb': sin_ficha,
               'obras': out}, open(salida, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    print(f'\n── {salida}')
    print(f'   obras {len(out)}/{len(obras)} · discrepan {len(discrepan)} · '
          f'sin sinopsis es {len(sin_sinopsis)} · sin póster '
          f'{sum(1 for x in out if not x["poster_tmdb"])}')
    for d in discrepan[:10]:
        print(f'   ?? {d["titulo"][:34]:36} LB {d["letterboxd"]} ≠ TMDB {d["tmdb"]}')


if __name__ == '__main__':
    main()
