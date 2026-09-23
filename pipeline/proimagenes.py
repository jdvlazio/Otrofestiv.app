#!/usr/bin/env python3
"""proimagenes.py <fest-id> [--posters] — la SEGUNDA fuente, para cine colombiano.

POR QUÉ EXISTE (23 sep 2026). TMDB no tiene el cine colombiano reciente. Itagüí
programó cuatro películas que no están ahí —«El último caso», «La estancia»,
«Clave de amor», «ARENAS»— y salieron sin país, sin año, sin sinopsis y sin
afiche, con la app diciendo que no se sabe nada de ellas. Proimágenes Colombia
es la base de datos oficial del cine colombiano y sí las registra.

CÓMO. Corre DESPUÉS de enriquecer.py y solo mira lo que TMDB no verificó: el
sidecar del enriquecido se completa, nunca se pisa. Lo que TMDB verificó manda.

EL MISMO CANDADO: el director tiene que casar (`director_coincide`, la de TMDB).
No es opcional — el buscador de Proimágenes es LAXO y busca también dentro de la
sinopsis: «ARENAS» devuelve «Camilo, el cura guerrillero», y «Habitante» dieciocho
títulos que no son. Sin el candado, colgaríamos homónimos, que es la lección
Tribeca.

DOS TRAMPAS MEDIDAS, las dos de este sitio:
  · el buscador NO responde a `buscar=`; el campo es `txtbuscar` con `mode` y
    `nt`. Con el parámetro equivocado devuelve la portada y cero resultados, que
    se lee igual que «no está».
  · la ficha imprime sus rótulos en MAYÚSCULAS por CSS, pero el HTML dice
    `<h3>Director:</h3>`. Buscar lo que se ve en pantalla no encuentra nada.

Esc.  completa festivals/staging/<id>-enriquecido.json
"""
import html
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import director_coincide, norm, slug, provenance  # noqa: E402

BASE = 'https://www.proimagenescolombia.com'
BUSCAR = (BASE + '/secciones/cine_colombiano/peliculas_colombianas/'
          'resultados_peliculas.php?mode=filtros&nt={nt}&genero=&estreno=&etapa='
          '&pais=&convo=&txtbuscar={q}')
FICHA = (BASE + '/secciones/cine_colombiano/peliculas_colombianas/'
         'pelicula_plantilla.php?id_pelicula={id}')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131 Safari/537.36'


def baja(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, url],
                           capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode('utf-8', 'replace')
        time.sleep(1)
    return ''


def _campo(t, rotulo):
    m = re.search(rf'<h3>{rotulo}[^<]*</h3>\s*<p>(.*?)</p>', t, re.S | re.I)
    return html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else ''


def ficha(idp):
    """La ficha, parseada. Los rótulos van en minúscula en el HTML."""
    t = baja(FICHA.format(id=idp))
    if not t:
        return None
    dirs = [html.unescape(x) for x in re.findall(
        r'id="listElencodir".*?</li>', t, re.S)[:1]
        for x in re.findall(r'<h4>([^<]+)</h4>', x)]
    sin = ''
    m = re.search(r'Sinopsis</h[23]>(.*?)</div>', t, re.S | re.I)
    if m:
        sin = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1)))
        sin = re.sub(r'\s{2,}', ' ', sin).strip()
    afiche = re.search(r'(photos/[0-9_]+__imagen_270_400\.jpg)', t)
    return {'id': idp, 'directores': dirs,
            'genero': _campo(t, 'G[ée]nero'), 'duracion': _campo(t, 'Duraci[oó]n'),
            'anio': _campo(t, 'A[ñn]o'), 'sinopsis': sin,
            'afiche': (BASE + '/' + afiche.group(1)) if afiche else ''}


def variantes(titulo):
    """El título entero y, si lleva punto o dos puntos, lo que va antes.

    El buscador es literal: «Xie. defensa de la vida» devuelve CERO y «Xie»
    devuelve su ficha (id 3243, con las dos directoras exactas). Medido el 23 sep.
    """
    t = titulo.strip()
    out = [t]
    corte = re.split(r'[.:]', t)[0].strip()
    if corte and corte != t and len(corte) >= 3:
        out.append(corte)
    return out


def busca(titulo):
    """Ids candidatos. Se piden los DOS catálogos: largos (nt=1) y cortos (nt=3)."""
    ids = []
    for q in variantes(titulo):
        for nt in (1, 3):
            t = baja(BUSCAR.format(nt=nt, q=re.sub(r'\s+', '%20', q)))
            ids += re.findall(r'id_pelicula=(\d+)', t)
    vistos, out = set(), []
    for i in ids:
        if i not in vistos:
            vistos.add(i); out.append(i)
    return out[:8]


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: python3 pipeline/proimagenes.py <fest-id> [--posters]')
    fid, posters = sys.argv[1], '--posters' in sys.argv
    crudo = json.load(open(f'{REPO}/festivals/staging/{fid}-crudo.json', encoding='utf-8'))
    ep = f'{REPO}/festivals/staging/{fid}-enriquecido.json'
    enr = json.load(open(ep, encoding='utf-8'))
    obras = enr.get('obras') or []
    ya = {norm(o['titulo']) for o in obras if o.get('tmdb_id')}

    pend, vistos = [], set()
    for f in crudo['funciones']:
        t = f.get('titulo') or ''
        if f.get('tipo') == 'evento' or norm(t) in ya or norm(t) in vistos:
            continue
        vistos.add(norm(t))
        if f.get('director'):        # sin director no hay candado: no se busca
            pend.append(f)

    print(f'{len(pend)} obra(s) sin ficha de TMDB y CON director — se buscan en Proimágenes')
    nuevas, n_post = [], 0
    for i, f in enumerate(pend, 1):
        t = f['titulo']
        hit = None
        for idp in busca(t):
            d = ficha(idp)
            if not d:
                continue
            if director_coincide(f['director'], d['directores']):
                hit = d
                break
        if not hit:
            print(f'[{i:2}/{len(pend)}] —   {t[:44]:46} sin ficha que case por director')
            continue
        o = {'titulo': t, 'pais': 'Colombia', '_fuente': 'proimagenes',
             '_proimagenes_id': hit['id'],
             '_verificado': f'director: {", ".join(hit["directores"])}'}
        if hit['anio'].isdigit():
            o['anio'] = int(hit['anio'])
        m = re.search(r'(\d{1,3})', hit['duracion'])
        if m:
            o['duracion_min'] = int(m.group(1))
        if hit['genero']:
            o['genero'] = hit['genero'].split('/')[0].strip()
        if hit['sinopsis']:
            o['sinopsis'] = hit['sinopsis'][:1200]
        if posters and hit['afiche']:
            os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
            dest = f'{REPO}/assets/{fid}/{slug(t)}.jpg'
            if not (os.path.exists(dest) and os.path.getsize(dest) > 5000):
                subprocess.run(['curl', '-sL', '--max-time', '30', '-A', UA,
                                '-o', dest, hit['afiche']])
            if os.path.exists(dest) and os.path.getsize(dest) > 5000:
                o['poster'] = f'/assets/{fid}/{slug(t)}.jpg'
                o['posterSource'] = 'oficial'
                n_post += 1
        nuevas.append(o)
        print(f'[{i:2}/{len(pend)}] OK  {t[:44]:46} proimagenes {hit["id"]}'
              f'{"  afiche" if o.get("poster") else ""}')

    obras += nuevas
    enr['obras'] = obras
    enr.setdefault('_fuentes', []).append(provenance(
        'proimagenescolombia.com — la base oficial del cine colombiano',
        que_aporta='país, año, duración, género, sinopsis y afiche de las obras '
                   'que TMDB no registra',
        metodo='búsqueda por título en los catálogos de largos y cortos, y el '
               'MISMO candado del director que TMDB: el buscador es laxo y '
               'también mira dentro de la sinopsis'))
    io.open(ep, 'w', encoding='utf-8').write(
        json.dumps(enr, ensure_ascii=False, indent=1) + '\n')
    print(f'\n{len(nuevas)} obra(s) recuperadas · {n_post} con afiche → {ep}')


if __name__ == '__main__':
    main()
