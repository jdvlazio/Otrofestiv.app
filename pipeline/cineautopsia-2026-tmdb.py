# -*- coding: utf-8 -*-
"""Enriquece las 45 obras de CineAutopsia con TMDB, y de ahí el lbSlug.

EXPECTATIVA BAJA A PROPÓSITO. Es cine experimental de circuito de festival:
cortos de 4 a 30 minutos, muchos de 2025 y 2026, de 18 países. Ese es
exactamente el perfil que peor cubren TMDB y Letterboxd —lo medimos en
SiembraFest: un tercio— así que aquí el resultado que importa no es «cuántas
encontramos» sino «cuántas encontramos SIN inventar ninguna».

EL CANDADO ES EL DE SIEMPRE, y aquí aprieta más que nunca: se busca por título
y solo se acepta el candidato si el DIRECTOR coincide. Títulos como «Ocno»,
«XYZ», «Decaer» o «Chaika» tienen homónimos garantizados; sin verificación
traeríamos la película equivocada, que es peor que no traer nada (lección
Tribeca: 134 pósters falsos).

El lbSlug sale del atajo `letterboxd.com/tmdb/<id>` — Letterboxd responde con
SU propio mapeo, así que el slug no lo inferimos nosotros. Sin tmdb_id
verificado no se pide slug.
"""
import json, os, re, ssl, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
KEY = os.environ.get('TMDB_API_KEY')
if not KEY:
    sys.exit('Falta $TMDB_API_KEY (vive en ~/.zshrc).')
API = 'https://api.themoviedb.org/3'

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()


def get(path, **params):
    """Un fallo que no puede mejorar solo ABORTA en la primera obra, no en la 45.
    La lección del enriquecedor de TIFF: una hora reintentando SSL sin escribir."""
    url = f'{API}{path}?api_key={KEY}&' + urllib.parse.urlencode(params)
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25, context=CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code in (401, 403): sys.exit(f'TMDB {e.code} — revisá $TMDB_API_KEY.')
            if e.code < 500: return None
        except urllib.error.URLError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e.reason):
                sys.exit('SSL: falta el certificado raíz. pip3 install certifi.')
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


<<<<<<< HEAD
def norm(s):
=======
# [lib-unica] renombrada desde `norm` el 17 ago 2026.
# Conserva el ordinal («12ª» → «12a»); `lib.norm` lo colapsa a «12».
def norm_ordinales(s):
>>>>>>> origin/main
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def mismo_director(a, b):
<<<<<<< HEAD
    ta = {t for t in norm(a).split() if len(t) > 3}
    tb = {t for t in norm(b).split() if len(t) > 3}
    if not ta or not tb:
        return norm(a) == norm(b)      # nombres cortos: comparación completa
=======
    ta = {t for t in norm_ordinales(a).split() if len(t) > 3}
    tb = {t for t in norm_ordinales(b).split() if len(t) > 3}
    if not ta or not tb:
        return norm_ordinales(a) == norm_ordinales(b)      # nombres cortos: comparación completa
>>>>>>> origin/main
    return bool(ta & tb)


def lbslug(tmdb_id):
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'], capture_output=True)
    m = re.match(r'https://letterboxd\.com/film/([^/]+)/?$', r.stdout.decode().strip())
    return m.group(1) if m else None


def main():
    src = json.load(open(f'{ST}/cineautopsia-2026-cinemateca.json', encoding='utf-8'))
    obras = [dict(o, _programa=p['programa']) for p in src['programas'] for o in p['obras']]

    ok, sin, dudosas = [], [], []
    for i, o in enumerate(obras, 1):
        # el título puede venir doble: «Original / Traducción»
        cands = [t.strip() for t in re.split(r'\s+/\s+|\s+\|\s+', o['titulo']) if t.strip()]
        elegido = None
        for t in cands:
            for params in ({'query': t, 'year': o['anio']}, {'query': t}):
                res = (get('/search/movie', language='es-CO', include_adult='false', **params) or {}).get('results') or []
                for c in res[:5]:
                    det = get(f"/movie/{c['id']}", language='es-CO', append_to_response='credits')
                    if not det: continue
                    dirs = [x['name'] for x in det.get('credits', {}).get('crew', []) if x.get('job') == 'Director']
                    if any(mismo_director(o['director'], d) for d in dirs):
                        elegido = det; break
                if elegido: break
            if elegido: break

        if not elegido:
            sin.append(o['titulo'])
            print(f'[{i:2}/{len(obras)}] —   {o["titulo"][:44]:46} {o["director"][:24]}', flush=True)
            continue

        slug = lbslug(elegido['id'])
        ok.append({**o, 'tmdb_id': elegido['id'],
                   'titulo_original': elegido.get('original_title'),
                   'sinopsis': (elegido.get('overview') or '').strip() or None,
                   'poster_tmdb': elegido.get('poster_path'),
                   'lbSlug': slug,
                   '_verificado': 'director✓'})
        print(f'[{i:2}/{len(obras)}] OK  {o["titulo"][:44]:46} tmdb {elegido["id"]} '
              f'{"·poster" if elegido.get("poster_path") else ""}{"·lb" if slug else ""}', flush=True)
        time.sleep(0.2)

    salida = f'{ST}/cineautopsia-2026-tmdb.json'
    json.dump({'_provenance': provenance('api.themoviedb.org/3 + letterboxd.com/tmdb/<id>',
                                         metodo='busqueda por titulo, ACEPTADA solo si el director coincide'),
               '_obras': len(obras), '_encontradas': len(ok), '_sin_match': sin,
               'obras': ok}, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n── {salida}')
    print(f'   {len(ok)}/{len(obras)} verificadas · con póster '
          f'{sum(1 for x in ok if x["poster_tmdb"])} · con lbSlug {sum(1 for x in ok if x["lbSlug"])} '
          f'· con sinopsis {sum(1 for x in ok if x["sinopsis"])}')


if __name__ == '__main__':
    main()
