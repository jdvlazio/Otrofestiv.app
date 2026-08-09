# -*- coding: utf-8 -*-
"""Segunda pasada sobre las obras que la verificación rechazó.

Las 12 dudosas no fallan por la misma razón, y solo una parte es real:

  · Créditos en otro alfabeto — «La colina de las amapolas» sí está en TMDB,
    pero su director figura como 宮崎吾朗. Comparado contra «Gorõ Miyazaki» no
    cruza nunca. Se piden los créditos en inglés, que vienen romanizados.
  · El título de búsqueda no es el del PDF — «La Sirena (The Siren)» lleva el
    internacional entre paréntesis, y «Nina y los cuentos del Erizo» es la
    traducción de «Nina et le secret du hérisson». Se prueban variantes.
  · El OCR estropeó el título — «Maya, donne-moin titre» por «Maya, donne-moi
    un titre». Se corrigen a mano, con tabla explícita y auditable.

Lo que quede fuera después de esto es un estreno que TMDB no tiene, y ahí la
respuesta no es forzar el match: es dar la obra de alta o dejarla sin ficha.
"""
import json, os, re, subprocess, unicodedata, time

S = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ['TMDB_API_KEY']
API = 'https://api.themoviedb.org/3'

# Títulos que el OCR leyó mal. Leídos del PDF y corregidos a mano.
OCR_FIX = {
    'Maya, donne-moin titre': 'Maya, donne-moi un titre',
}

# Títulos que el FESTIVAL rebautizó. No es un error del OCR ni de TMDB: el
# programa dice «Nina y los cuentos del Erizo» y la película se distribuye
# como «Nina et le secret du hérisson». Buscar por el original la encuentra.
# Se declara a mano y verificado a ojo — nunca se infiere una traducción.
ALIAS = {
    'Nina y los cuentos del Erizo': 'Nina et le secret du hérisson',
}


def get(path, **params):
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
    return set(re.sub(r'[^a-z0-9 ]', ' ', s).split()) - {'de', 'la', 'del', 'y', 'van', 'der', 'le'}


def dir_ok(esperado, nombres):
    a = norm(esperado)
    for n in nombres:
        b = norm(n)
        if {x for x in a if len(x) > 4} & {x for x in b if len(x) > 4}:
            return True
    return False


def variantes(titulo):
    """Formas alternativas de buscar el mismo título."""
    v = [OCR_FIX.get(titulo, titulo)]
    if titulo in ALIAS: v.insert(0, ALIAS[titulo])
    m = re.match(r'^(.+?)\s*\((.+)\)\s*$', v[0])       # «La Sirena (The Siren)»
    if m:
        v += [m.group(2).strip(), m.group(1).strip()]
    return list(dict.fromkeys(v))


def main():
    d = json.load(open(f'{S}/ficma-tmdb.json', encoding='utf-8'))
    ok, quedan = d['verificadas'], []

    for x in d['dudosas']:
        p, elegido = x['pdf'], None
        for q in variantes(x['titulo']):
            # sin `year` y en inglés: el filtro de año descartaba candidatos
            # buenos con fecha de estreno distinta a la del festival, y los
            # créditos en inglés vienen romanizados.
            for lang in ('en-US', 'es-ES'):
                for c in get('/search/movie', query=q, language=lang,
                             include_adult='false').get('results', [])[:6]:
                    det = get(f"/movie/{c['id']}", language='es-ES', append_to_response='credits')
                    det_en = get(f"/movie/{c['id']}", language='en-US', append_to_response='credits')
                    dirs = [pp['name'] for det_ in (det, det_en)
                            for pp in det_.get('credits', {}).get('crew', []) if pp.get('job') == 'Director']
                    anio_t = int((det.get('release_date') or '0000')[:4] or 0)
                    dur_t = det.get('runtime') or 0
                    a_ok = p['anio'] and abs(anio_t - p['anio']) <= 1
                    r_ok = p['duracion_min'] and dur_t and abs(dur_t - p['duracion_min']) <= 3
                    if dir_ok(p['director'], dirs) and (a_ok or r_ok):
                        elegido = {'tmdb_id': c['id'], 'titulo_original': det.get('original_title'),
                                   'poster_path': det.get('poster_path'),
                                   'synopsis_es': det.get('overview') or '',
                                   'synopsis_en': det_en.get('overview') or '',
                                   'generos': [g['name'] for g in det.get('genres', [])],
                                   'anio_tmdb': anio_t, 'duracion_tmdb': dur_t, 'director_tmdb': dirs,
                                   '_verificado': f"repesca · director✓ {'año✓' if a_ok else ''} {'duración✓' if r_ok else ''}".strip(),
                                   '_busqueda': q}
                        break
                if elegido: break
            if elegido: break
        if elegido:
            ok[x['titulo']] = {**elegido, 'pdf': p}
            print(f'  RECUPERADA  {x["titulo"][:46]:48} ← «{elegido["_busqueda"]}»')
        else:
            quedan.append({**x, 'motivo': 'no está en TMDB (verificado con título original, '
                                          'variantes y créditos romanizados)'})
            print(f'  sin ficha   {x["titulo"][:46]:48} {p["director"][:22]} · {p["anio"]}')

    json.dump({**d, 'verificadas': ok, 'dudosas': quedan},
              open(f'{S}/ficma-tmdb.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nverificadas {len(ok)} · sin ficha en TMDB {len(quedan)}')
    print(f'con póster {sum(1 for v in ok.values() if v["poster_path"])} · '
          f'sin sinopsis ES {sum(1 for v in ok.values() if not v["synopsis_es"])}')


if __name__ == '__main__':
    main()
