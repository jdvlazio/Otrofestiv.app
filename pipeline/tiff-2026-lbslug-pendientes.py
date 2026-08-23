# -*- coding: utf-8 -*-
"""Los 5 títulos de TIFF que PODRÍAN tener Letterboxd y aún no lo tienen.

Todo lo demás de la lista de «62 sin lbSlug» no es un hueco: 20 son programas
de cortos (Letterboxd no tiene página de programa), 5 son charlas y 22 son
series de Primetime — y Letterboxd es SOLO cine. Ver docs/PIPELINE.md Fase 0·bis.

Estos 5 son estrenos 2026 sin ficha en TMDB al 17 ago. El slug sale del atajo
`letterboxd.com/tmdb/<id>`, así que sin TMDB no hay slug: o aparece su ficha
sola (lo normal según se acerca el festival) o se da de alta (Fase 3b).

    TMDB_API_KEY=… python3 pipeline/tiff-2026-lbslug-pendientes.py
    TMDB_API_KEY=… python3 pipeline/tiff-2026-lbslug-pendientes.py --aplicar
"""
import json, os, re, subprocess, sys, time, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAVE = os.environ.get('TMDB_API_KEY')
# título → director, para VERIFICAR. La lección Tribeca (134 pósters falsos) no
# se repite: sin director que coincida, no se acepta la ficha.
# Al 17 ago 2026 quedan DOS. Los otros tres se resolvieron esa noche:
#   London → london-2026 (director coincide)
#   Turtle Island Rap → turtle-island-rap (director coincide)
#   Re/Pair → re-pair (TMDB sin crew; verificado por duración + país + sinopsis)
#
# TRAMPA QUE COSTÓ LA PRIMERA PASADA: buscar con `&year=2026` los escondía. Una
# ficha recién creada en TMDB no tiene `release_date`, así que filtrar por año
# descarta justo los estrenos que estamos buscando. Se busca SIN año y se
# verifica después.
PENDIENTES = {
    'Pretenders': None,
    'The Hummingbird Paints Fragrant Songs': None,
}


def buscar(titulo):
    u = ('https://api.themoviedb.org/3/search/movie?api_key=' + CLAVE +
         '&query=' + urllib.parse.quote(titulo))   # SIN año: ver la nota de arriba
    r = subprocess.run(['curl', '-s', '--max-time', '25', u], capture_output=True)
    try:
        return (json.loads(r.stdout.decode()).get('results') or [])
    except Exception:
        return []


# NO es lib.slug (que convierte un título en slug): ésta PREGUNTA a Letterboxd
# por el suyo vía el atajo /tmdb/<id>. Lo cazó [lib-unica] en el acto.
def slug_letterboxd(tmdb_id):
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', f'https://letterboxd.com/tmdb/{tmdb_id}/'],
                       capture_output=True)
    m = re.search(r'letterboxd\.com/film/([^/]+)/', r.stdout.decode())
    return m.group(1) if m else None


def main():
    if not CLAVE:
        sys.exit('✗ falta $TMDB_API_KEY (vive en ~/.zshrc)')
    P = f'{REPO}/festivals/tiff-2026.json'
    d = json.load(open(P, encoding='utf-8'))
    dirs = {f['title']: f.get('director') for f in d['films']}
    hallados = {}
    for t, _ in PENDIENTES.items():
        res = buscar(t)
        esperado = dirs.get(t) or ''
        elegido = None
        for c in res[:3]:
            det = lib.tmdb_get(f"/movie/{c['id']}", CLAVE, append_to_response='credits')
            nombres = [x['name'] for x in (det.get('credits', {}).get('crew') or [])
                       if x.get('job') == 'Director']
            if not esperado or lib.director_coincide(esperado, nombres):
                elegido = c
                break
        if not elegido:
            print(f'  {t[:40]:42} sin ficha verificada ({len(res)} candidatos)')
            continue
        s = slug_letterboxd(elegido['id'])
        print(f'  {t[:40]:42} tmdb={elegido["id"]} → {s or "sin página en Letterboxd"}')
        if s:
            hallados[t] = (elegido['id'], s)
        time.sleep(.5)
    if '--aplicar' in sys.argv and hallados:
        n = 0
        for f in d['films']:
            if f['title'] in hallados and not f.get('lbSlug'):
                f['tmdb_id'], f['lbSlug'] = hallados[f['title']]
                n += 1
        json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'\n✓ {n} funciones actualizadas — correr después: python3 validate.py')


if __name__ == '__main__':
    main()
