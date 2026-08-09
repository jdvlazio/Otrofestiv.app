# -*- coding: utf-8 -*-
"""Cruza el catálogo de FICMA contra TMDB — VERIFICANDO, no adivinando.

El PDF publica director, año y duración de cada obra. Eso convierte el
emparejamiento en verificación y es lo que evita el desastre de Tribeca (134
pósters de películas equivocadas por casar solo por título: hay homónimos,
remakes y el mismo nombre en tres idiomas).

Regla de aceptación: el candidato entra SOLO si el director coincide y además
coincide el año (±1) o la duración (±3 min). Todo lo demás va a `dudosos`
para revisión humana — nunca se acepta a medias ni se elige "el más popular".
"""
import json, os, re, subprocess, unicodedata, time

S = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ['TMDB_API_KEY']
API = 'https://api.themoviedb.org/3'


def get(path, **params):
    q = '&'.join(f'{k}={subprocess.list2cmdline([str(v)])}' for k, v in params.items())
    url = f'{API}{path}?api_key={KEY}&' + '&'.join(
        f'{k}=' + str(v).replace(' ', '%20').replace('&', '%26') for k, v in params.items())
    for _ in range(3):
        r = subprocess.run(['curl', '-s', '--max-time', '25', url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except Exception:
                pass
        time.sleep(0.8)
    return {}


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]', ' ', s).split()


def director_coincide(esperado, obtenido):
    """Compara por APELLIDOS. El PDF escribe «Michaël Dudok de Wit» y TMDB
    «Michael Dudok de Wit»; y con varios directores basta que uno cruce."""
    a = set(norm(esperado)) - {'de', 'la', 'del', 'y', 'van', 'der'}
    b = set(norm(obtenido)) - {'de', 'la', 'del', 'y', 'van', 'der'}
    return bool(a & b) and len(a & b) >= min(2, len(a), len(b)) or bool(
        {x for x in a if len(x) > 4} & {x for x in b if len(x) > 4})


def main():
    crudo = json.load(open(f'{S}/ficma-crudo.json', encoding='utf-8'))
    obras = {}
    for f in crudo['funciones']:
        obras.setdefault(f['titulo'], f)

    ok, dudosos = {}, []
    for i, (titulo, f) in enumerate(sorted(obras.items()), 1):
        cands = []
        for params in ({'query': titulo, 'year': f['anio']}, {'query': titulo}):
            res = get('/search/movie', language='es-ES', include_adult='false', **params)
            cands += res.get('results', [])[:5]
            if cands:
                break
        elegido, motivo = None, 'sin candidatos en TMDB'
        for c in cands[:6]:
            det = get(f"/movie/{c['id']}", language='es-ES', append_to_response='credits')
            dirs = [p['name'] for p in det.get('credits', {}).get('crew', []) if p.get('job') == 'Director']
            anio_t = int((det.get('release_date') or '0000')[:4] or 0)
            dur_t = det.get('runtime') or 0
            d_ok = any(director_coincide(f['director'], n) for n in dirs)
            a_ok = f['anio'] and abs(anio_t - f['anio']) <= 1
            r_ok = f['duracion_min'] and dur_t and abs(dur_t - f['duracion_min']) <= 3
            if d_ok and (a_ok or r_ok):
                en = get(f"/movie/{c['id']}", language='en-US')
                elegido = {'tmdb_id': c['id'], 'titulo_original': det.get('original_title'),
                           'poster_path': det.get('poster_path'),
                           'synopsis_es': det.get('overview') or '',
                           'synopsis_en': en.get('overview') or '',
                           'generos': [g['name'] for g in det.get('genres', [])],
                           'anio_tmdb': anio_t, 'duracion_tmdb': dur_t, 'director_tmdb': dirs,
                           '_verificado': f"director✓ {'año✓' if a_ok else ''} {'duración✓' if r_ok else ''}".strip()}
                break
            motivo = f'mejor candidato «{c.get("title")}» ({anio_t}, {dur_t}min, {", ".join(dirs) or "sin director"}) no verifica'
        if elegido:
            ok[titulo] = {**elegido, 'pdf': {k: f[k] for k in ('director', 'pais', 'anio', 'duracion_min')}}
        else:
            dudosos.append({'titulo': titulo, 'pdf': {k: f[k] for k in ('director', 'pais', 'anio', 'duracion_min')},
                            'motivo': motivo})
        print(f'[{i:2}/{len(obras)}] {"OK " if elegido else "?? "} {titulo[:52]}', flush=True)

    json.dump({'_metodo': 'verificación por director + (año ±1 o duración ±3 min); sin match no se adivina',
               'verificadas': ok, 'dudosas': dudosos},
              open(f'{S}/ficma-tmdb.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con_sin_es = sum(1 for v in ok.values() if not v['synopsis_es'])
    print(f'\n{len(obras)} obras · verificadas {len(ok)} · dudosas {len(dudosos)}')
    print(f'con póster {sum(1 for v in ok.values() if v["poster_path"])} · '
          f'sin sinopsis ES {con_sin_es} · sin sinopsis EN {sum(1 for v in ok.values() if not v["synopsis_en"])}')


if __name__ == '__main__':
    main()
