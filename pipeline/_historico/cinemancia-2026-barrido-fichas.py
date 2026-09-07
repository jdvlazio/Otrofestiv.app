# -*- coding: utf-8 -*-
"""Ficha de Letterboxd de cada obra → `cinemancia-2026-fichas.json`.

POR QUÉ NO SE USA `enriquecer.py`. La herramienta genérica va TMDB → Letterboxd:
busca la obra en TMDB por título, la verifica, y del id verificado saca el
`lbSlug` por el atajo `letterboxd.com/tmdb/<id>`. Aquí el flujo se INVIERTE,
porque Cinemancia publica su propia lista en Letterboxd: el slug ya lo tenemos
y viene del festival, que es mejor evidencia que cualquier búsqueda. Así que
se va Letterboxd → TMDB, y la ficha de Letterboxd hace doble trabajo:

  1. da director, año y el id de TMDB de una sola petición, y
  2. VERIFICA el emparejamiento título-a-título que hizo la alineación de
     secuencias. Su lista está en inglés y la nuestra en idioma original, así
     que 28 de las 107 parejas se apoyaban solo en el orden. Un título
     traducido no es evidencia; el director sí. Esta pasada las convierte en
     confirmadas o en errores, sin zona gris.

El veredicto usa `lib.director_coincide` —tokens largos sin partículas— más
año ±1, que es el mismo candado de `ficha_verifica` adaptado a que Letterboxd
no publica duración en la ficha.

Escribe la procedencia por obra: de dónde salió el dato y con qué se verificó.
Sin eso no se puede auditar después sin re-correr todo.

Segunda mitad (sinopsis y póster desde TMDB con el id ya verificado): necesita
TMDB_API_KEY y vive en el paso siguiente del plan.
"""
import html, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUCE = f'{REPO}/festivals/staging/cinemancia-2026-lb.json'
OUT = f'{REPO}/festivals/staging/cinemancia-2026-fichas.json'


def ficha_lb(slug):
    """→ {director[], year, tmdb_id, title, title_original} desde la ficha."""
    s = lib.curl_get(f'https://letterboxd.com/film/{slug}/')
    if not s:
        return None
    dirs = []
    for d in re.findall(r'/director/([a-z0-9-]+)/', s):
        # el nombre legible está en el enlace; el slug es el respaldo
        m = re.search(r'/director/' + re.escape(d) + r'/"[^>]*>(?:<[^>]+>)*([^<]+)', s)
        n = html.unescape(m.group(1)).strip() if m else d.replace('-', ' ')
        if n and n not in dirs:
            dirs.append(n)
    y = re.search(r'/films/year/(\d{4})/', s)
    t = re.search(r'themoviedb\.org/movie/(\d+)', s)
    og = re.search(r'<meta property="og:title" content="([^"]+)"', s)
    orig = re.search(r"[’']s original title[^<]*<[^>]*>([^<]+)", s) \
        or re.search(r'<h2 class="originalname">([^<]+)', s)
    return {'director': dirs,
            'year': int(y.group(1)) if y else None,
            'tmdb_id': int(t.group(1)) if t else None,
            'title': html.unescape(re.sub(r'\s*\(\d{4}\)\s*$', '', og.group(1))).strip()
                     if og else None,
            'title_original': html.unescape(orig.group(1)).strip() if orig else None}


def main():
    obras = json.load(open(CRUCE, encoding='utf-8'))['obras']
    con_slug = [o for o in obras if o.get('lbSlug')]
    print(f'{len(con_slug)} obras con lbSlug · {len(obras) - len(con_slug)} sin él\n')

    out, ok, malas, sin_tmdb = [], 0, [], 0
    for i, o in enumerate(con_slug, 1):
        f = ficha_lb(o['lbSlug'])
        if not f:
            malas.append((o, 'ficha no descargada')); continue
        d_ok = lib.director_coincide(o['director'], f['director'])
        a_ok = not (o['year'] and f['year']) or abs(o['year'] - f['year']) <= 1
        veredicto = 'confirmada' if (d_ok and a_ok) else 'DISCREPA'
        if veredicto == 'confirmada':
            ok += 1
        else:
            malas.append((o, f'director={f["director"]} año={f["year"]}'))
        if not f['tmdb_id']:
            sin_tmdb += 1
        out.append({**o, 'lb_director': f['director'], 'lb_year': f['year'],
                    'tmdbId': f['tmdb_id'], 'title_en': f['title'] or o.get('title_en'),
                    'title_original_lb': f['title_original'],
                    '_verificacion': veredicto,
                    '_src': f'letterboxd.com/film/{o["lbSlug"]}/ — director y año de la ficha'})
        print(f'[{i:3}/{len(con_slug)}] {"OK " if veredicto=="confirmada" else "!! "}'
              f'{o["title"][:40]:42} {f["director"][:1] or ["?"]} {f["year"]}'
              f' tmdb={f["tmdb_id"] or "—"}', flush=True)
        time.sleep(0.7)                                   # cortesía con Letterboxd

    for o in obras:
        if not o.get('lbSlug'):
            out.append({**o, '_verificacion': 'sin letterboxd'})

    d = {'_provenance': lib.provenance(
            'ficha de cada obra en letterboxd.com (slug de la lista oficial del festival)',
            verificacion=('director (lib.director_coincide) + año ±1 contra el PDF oficial; '
                          'confirma o desmiente la alineación de secuencias del paso anterior'),
            pendiente='sinopsis y póster desde TMDB con el tmdbId ya verificado (requiere TMDB_API_KEY)'),
         'obras': out}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n{OUT.split("/")[-1]}  ·  confirmadas {ok}/{len(con_slug)} · '
          f'con id de TMDB {sum(1 for x in out if x.get("tmdbId"))} · sin id {sin_tmdb}')
    if malas:
        print(f'\nA REVISAR ({len(malas)}) — el emparejamiento no se sostiene:')
        for o, por in malas:
            print(f'   · {o["title"][:40]:42} PDF: {o["director"][:26]:28} {o["year"]}')
            print(f'     LB «{o.get("title_en") or o["lbSlug"]}» → {por}')


if __name__ == '__main__':
    main()
