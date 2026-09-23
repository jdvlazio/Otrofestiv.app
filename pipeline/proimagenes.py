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
import urllib.parse

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
    # EL AFICHE EN SU TAMAÑO, NO EN MINIATURA. La ficha referencia la misma
    # imagen en varios recortes —130×110, 270×400— y además el ORIGINAL, que
    # es el mismo nombre con las medidas vacías: `..._imagen__.jpg`. El de
    # «Mi abuelo, mi papá y yo» mide 760×1104 ahí y 270×392 en la miniatura,
    # que cae por debajo del suelo de [poster-mirado] y encima se amplía a
    # 780 de ancho inventando píxeles. Se pide el original y la miniatura
    # queda de respaldo.
    afiche = (re.search(r'(photos/[0-9_]+__imagen__\.jpg)', t)
              or re.search(r'(photos/[0-9_]+__imagen_270_400\.jpg)', t))
    return {'id': idp, 'directores': dirs,
            'genero': _campo(t, 'G[ée]nero'), 'duracion': _campo(t, 'Duraci[oó]n'),
            'anio': _campo(t, 'A[ñn]o'), 'sinopsis': sin,
            'afiche': (BASE + '/' + afiche.group(1)) if afiche else ''}


ARTICULO = re.compile(r'^(el|la|los|las|un|una|unos|unas)\s+', re.I)


def variantes(titulo):
    """El título entero; lo que va antes del punto o los dos puntos; y lo mismo
    sin el artículo inicial.

    El buscador es LITERAL, en los dos sentidos:
      · «Xie. defensa de la vida» devuelve CERO y «Xie» devuelve su ficha
        (id 3243, con las dos directoras exactas);
      · «La estancia» devuelve CERO y «Estancia» devuelve la suya (id 3121,
        Andrés Carmona Rivera, 85 minutos — la duración que imprime Itagüí).
        Proimágenes cataloga sin artículo y el festival lo rotula con él, así
        que la película estaba registrada y salía «sin ficha». Medido el 23 sep.
    """
    t = titulo.strip()
    out = []
    for x in (t, re.split(r'[.:]', t)[0].strip()):
        for y in (x, ARTICULO.sub('', x).strip()):
            if len(y) >= 3 and y not in out:
                out.append(y)
    return out


def _q(s):
    """La consulta, percent-encoded en LATIN-1, que es lo que el buscador habla.

    TERCERA trampa del sitio, medida el 23 sep: «Mi abuelo, mi papá y yo»
    devuelve CERO con la tilde en UTF-8 y con la tilde cruda, y devuelve su
    ficha (id 280, con afiche) codificada en latin-1. Los títulos sin tilde dan
    lo mismo en las tres. Es el mismo error de esta mañana en TMDB: escapar la
    URL a mano en vez de dejárselo a urllib.
    """
    return urllib.parse.quote(s.encode('latin-1', 'ignore'), safe='')


def busca(titulo):
    """Ids candidatos. Se piden los DOS catálogos: largos (nt=1) y cortos (nt=3)."""
    ids = []
    for q in variantes(titulo):
        for nt in (1, 3):
            t = baja(BUSCAR.format(nt=nt, q=_q(q)))
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
    # LO QUE TMDB VERIFICÓ MANDA... salvo el afiche que no tiene.
    # «Mi abuelo, mi papá y yo» está en TMDB (327480) con país, año y
    # sinopsis y su ficha NO tiene imagen (`poster_path: null`), así que
    # salió sin afiche aunque Proimágenes sí lo publica. Una obra
    # verificada por TMDB vuelve a consultarse SOLO si le falta el afiche, y
    # de la segunda fuente se toma Únicamente eso: los campos verificados no
    # se pisan nunca.
    solo_afiche = {norm(o['titulo']) for o in obras
                   if o.get('tmdb_id') and not o.get('poster')}
    ya = {norm(o['titulo']) for o in obras
          if o.get('tmdb_id') and norm(o['titulo']) not in solo_afiche}

    pend, vistos = [], set()
    for f in crudo['funciones']:
        t = f.get('titulo') or ''
        if f.get('tipo') == 'evento' or norm(t) in ya or norm(t) in vistos:
            continue
        vistos.add(norm(t))
        if f.get('director'):        # sin director no hay candado: no se busca
            pend.append(f)

    print(f'{len(pend)} obra(s) a buscar en Proimágenes ({len(solo_afiche)} solo por el afiche)')
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
        if norm(t) in solo_afiche:
            # verificada por TMDB: SOLO se le añade el afiche que le faltaba,
            # sobre su propia entrada. Ni un campo más, y ninguno encima.
            if not o.get('poster'):
                print(f'[{i:2}/{len(pend)}] —   {t[:44]:46} '
                      'proimagenes tampoco publica su afiche')
                continue
            for x in obras:
                if norm(x['titulo']) == norm(t):
                    x['poster'], x['posterSource'] = o['poster'], o['posterSource']
                    x['_afiche_de'] = f'proimagenes {hit["id"]} (TMDB no tiene imagen)'
            print(f'[{i:2}/{len(pend)}] OK  {t[:44]:46} '
                  f'proimagenes {hit["id"]}  solo el afiche')
            continue
        if norm(t) in solo_afiche:
            # verificada por TMDB: SOLO se le añade el afiche que le faltaba,
            # sobre su propia entrada. Ni un campo más, y ninguno encima.
            if not o.get('poster'):
                print(f'[{i:2}/{len(pend)}] —   {t[:44]:46} '
                      'proimagenes tampoco publica su afiche')
                continue
            for x in obras:
                if norm(x['titulo']) == norm(t):
                    x['poster'] = o['poster']
                    x['posterSource'] = o['posterSource']
                    x['_afiche_de'] = f'proimagenes {hit["id"]}: TMDB verificó la ficha y no tiene imagen'
            print(f'[{i:2}/{len(pend)}] OK  {t[:44]:46} '
                  f'proimagenes {hit["id"]}  solo el afiche')
            continue
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
