# -*- coding: utf-8 -*-
"""Listado del PDF × lista de Letterboxd → `cinemancia-2026-lb.json`.

Cinemancia mantiene su propia lista en Letterboxd (letterboxd.com/cinemancia),
con una lista MAESTRA de la edición y una por sección. El `lbSlug` que sale de
ahí es el de ellos: no se infiere, que es la única forma de tenerlo bien.

EL PROBLEMA: la lista está en INGLÉS y el PDF en el idioma original, así que
emparejar por título falla en ~la mitad («Oublie pas le gruau» ↔ «Don't Forget
the Oatmeal»). Lo que sí se conserva es el ORDEN: la lista sigue el mismo
orden que el PDF, sección por sección.

LA SOLUCIÓN: alineación de secuencias (Needleman-Wunsch) sobre las dos listas,
con la similitud de títulos como puntaje y un pequeño bono por año compatible.
Las obras de título idéntico actúan de ancla y arrastran a las traducidas que
tienen alrededor. Un emparejamiento greedy por título NO sirve —se probó— y un
emparejamiento puramente posicional tampoco, porque el PDF tiene 2 obras que
no están en Letterboxd y a partir de ahí todo se corre.

LO QUE ESTE SCRIPT **NO** HACE: dar por buena la pareja. Emite `_conf` y las
que bajan de 0.5 quedan marcadas para verificación por DIRECTOR contra la
ficha de Letterboxd (`lib.ficha_verifica`), que es la doctrina desde Tribeca.
Un título traducido que «suena parecido» no es evidencia de nada.
"""
import difflib, html, json, os, re, subprocess, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTADO = f'{REPO}/festivals/staging/cinemancia-2026-listado.json'
OUT = f'{REPO}/festivals/staging/cinemancia-2026-lb.json'
LISTA = 'https://letterboxd.com/cinemancia/list/cinemancia-2026/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
GAP = -0.55           # penalización por hueco: calibrada para que las 2 obras
                      # ausentes de Letterboxd abran hueco y no arrastren pares
UMBRAL = 0.5          # por debajo → a verificar por director


# Era una copia literal de lib.norm(). Se importa: una sola definición.
import lib                                     # noqa: E402
norm = lib.norm


def bajar_lista():
    """→ [{slug, name, year}] en el orden en que Letterboxd los publica."""
    out, vistos = [], set()
    for p in range(1, 8):
        r = subprocess.run(['curl', '-sL', '-A', UA, f'{LISTA}page/{p}/'],
                           capture_output=True)
        s = r.stdout.decode('utf-8', 'replace')
        slugs = re.findall(r'data-item-slug="([^"]+)"', s) \
            or re.findall(r'data-film-slug="([^"]+)"', s)
        if not slugs:
            break
        nombres = dict(zip(slugs, re.findall(r'data-item-name="([^"]+)"', s)))
        for sl in slugs:
            if sl in vistos:
                continue
            vistos.add(sl)
            n = html.unescape(nombres.get(sl, ''))   # «Don&#039;t» → «Don't»
            m = re.search(r'\((\d{4})\)\s*$', n)
            out.append({'slug': sl,
                        'name': re.sub(r'\s*\(\d{4}\)\s*$', '', n).strip(),
                        'year': int(m.group(1)) if m else None})
    return out


def sim(o, x):
    """Similitud obra-PDF ↔ item-Letterboxd. Prueba también cada mitad de un
    título doble «Original / Traducción»."""
    cands = [norm(o['title'])] + [norm(t) for t in o['title'].split('/')]
    n = norm(x['name'])
    base = 1.0 if any(c == n for c in cands) else \
        max(difflib.SequenceMatcher(None, c, n).ratio() for c in cands)
    compatible = not (o['year'] and x['year'] and abs(o['year'] - x['year']) > 1)
    return base + (0.12 if compatible else 0.0)


def alinear(obras, lb):
    """Needleman-Wunsch: → {índice de obra: índice de lb}."""
    n, m = len(obras), len(lb)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    B = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0], B[i][0] = D[i - 1][0] + GAP, 'u'
    for j in range(1, m + 1):
        D[0][j], B[0][j] = D[0][j - 1] + GAP, 'l'
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i][j], B[i][j] = max((D[i-1][j-1] + sim(obras[i-1], lb[j-1]), 'd'),
                                   (D[i-1][j] + GAP, 'u'),
                                   (D[i][j-1] + GAP, 'l'))
    i, j, par, sobran = n, m, {}, []
    while i > 0 or j > 0:
        b = B[i][j]
        if b == 'd':
            par[i - 1] = j - 1; i -= 1; j -= 1
        elif b == 'u':
            i -= 1
        else:
            sobran.append(j - 1); j -= 1

    # Pasada final fuera del orden: la alineación es monótona a propósito, pero
    # Cinemancia coloca la película de CLAUSURA («Iluminaciones», Pablo Llorca
    # 2025) dentro de la sección Iluminaciones de su lista, no al principio.
    # Un título IDÉNTICO con año compatible es evidencia suficiente para cruzar
    # el orden; nada más lo es (un título traducido, no).
    libres = [i for i in range(n) if i not in par]
    for j2 in list(sobran):
        for i2 in libres:
            if i2 in par:
                continue
            if norm(obras[i2]['title']) == norm(lb[j2]['name']) and \
               not (obras[i2]['year'] and lb[j2]['year']
                    and abs(obras[i2]['year'] - lb[j2]['year']) > 1):
                par[i2] = j2; sobran.remove(j2); break
    return par, sorted(sobran)


def main():
    obras = json.load(open(LISTADO, encoding='utf-8'))['obras']
    lb = bajar_lista()
    par, sobran = alinear(obras, lb)

    filas, sin, dudosas = [], [], []
    for i, o in enumerate(obras):
        j = par.get(i)
        x = lb[j] if j is not None else None
        c = round(sim(o, x), 2) if x else 0.0
        fila = {'title': o['title'], 'section': o['section'], 'year': o['year'],
                'director': o['director'],
                'lbSlug': x['slug'] if x else None,
                'title_en': x['name'] if x else None,
                '_conf': c,
                '_verificar': bool(x) and c < UMBRAL}
        filas.append(fila)
        if not x:
            sin.append(o)
        elif c < UMBRAL:
            dudosas.append(fila)

    d = {'_provenance': lib.provenance(
            f'lista maestra de Letterboxd ({LISTA}) alineada contra el PDF oficial',
            metodo=('Needleman-Wunsch sobre el orden de ambas listas; la lista está en '
                    'inglés y el PDF en idioma original, así que el título solo no basta.'),
            pendiente=(f'{len(dudosas)} parejas con _conf<{UMBRAL} esperan verificación '
                       'por DIRECTOR contra la ficha de Letterboxd (doctrina Tribeca).')),
         'obras': filas}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{OUT.split("/")[-1]}  ·  PDF {len(obras)} · Letterboxd {len(lb)} · '
          f'emparejadas {len(obras) - len(sin)}')
    print(f'\nsin par en Letterboxd ({len(sin)}) — alta manual o resolver a mano:')
    for o in sin:
        print(f'   · {o["title"][:52]:54} {o["year"]}  [{o["section"][:32]}]')
    for j in sobran:
        print(f'   · en Letterboxd y no en el PDF: {lb[j]["name"][:48]} ({lb[j]["slug"]})')
    print(f'\npor verificar por director ({len(dudosas)}):')
    for f in dudosas:
        print(f'   {f["_conf"]:.2f}  {f["title"][:42]:44} → {f["title_en"][:40]}')


if __name__ == '__main__':
    main()
