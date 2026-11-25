#!/usr/bin/env python3
"""bogoshorts-2026-afiches.py — afiches oficiales de las obras que TMDB no tiene.

Dos fuentes, las dos ya identificadas:
  1. el registro de altas (bogoshorts-2026-altas.json): el afiche que pasó por
     `altas.py --preparar` (archivo en fuentes/bogoshorts-2026/altas/);
  2. la ficha de la obra en festival.bogoshorts.com (bogoshorts-2026-fichas-web.json),
     solo si la página nombra a la dirección de la obra (un homónimo de otra edición no
     entra) y el archivo dice póster/afiche y es vertical (los «Fotograma» no entran).
MIRADOS: lo que no es un afiche se lista en NO (a ojo, 23 nov 2026).

Escribe festivals/staging/bogoshorts-2026-afiches.json, que lee enriquecer.py.
"""
import json, os, re, subprocess, sys, unicodedata
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
ST = f'{REPO}/festivals/staging/bogoshorts-2026'
DIR = f'{REPO}/fuentes/bogoshorts-2026/afiches-web'
NO = {}
# la web titula la ficha en español o con el artista delante (misma obra: dirección y programa)
ALIAS = {'Idols': '4205', 'Cold Coffee': '4195', 'Cvijeće': '4249', 'On naît seul, on meurt seul': '4326',
         'The Waiting Palm': '4238', 'Savia (Alfilera)': '4344', 'Kupljena sjecanja': '4313',
         'Nothing Here is Lost': '4364', 'Raj’in': '4381', 'When the Flowers Bloom': '4380',
         'Berzingue (Crache)': '4345', 'The Beat (Matías Aguayo)': '4347', 'Cocodrilo (Dillom)': '4346',
         'Argentina Is Daing (Marttein)': '4348', 'Oui (Balming Tiger)': '4349', 'Běi Huí Guī Xiàn': '4259'}


def n(t):
    t = unicodedata.normalize('NFKD', (t or '').lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in t if not unicodedata.combining(c)))


def main():
    from PIL import Image
    os.makedirs(DIR, exist_ok=True)
    altas = json.load(open(f'{ST}-altas.json', encoding='utf-8'))['obras']
    web = json.load(open(f'{ST}-fichas-web.json', encoding='utf-8'))['fichas']
    cortos = json.load(open(f'{ST}-cortos.json', encoding='utf-8'))['programas']
    enr = {o['titulo']: o for o in json.load(open(f'{ST}-enriquecido.json', encoding='utf-8'))['obras']}
    ix = {}
    for k, v in web.items():
        ix.setdefault(n(v['titulo']), []).append((k, v))
    out, notas = {}, []
    # el afiche de TMDB, entero: su fondo negro liso se tomaba por marco y el encuadre cortaba el título por los lados
    # (mirado a ojo, 23 nov 2026). Declarado = no se recorta
    p = 'fuentes/bogoshorts-2026/afiches-web/fantasy-land-tmdb.jpg'
    if os.path.exists(f'{REPO}/{p}'):
        out['Fantasy Land'] = {'archivo': p, 'sobre_tmdb': True, 'url': 'https://image.tmdb.org/t/p/w780/5bCC7cYdBmm9gTkyx6QqxZA6t6T.jpg',
                               'fuente': 'afiche oficial de la ficha de TMDB 1840640 (acredita a Aitana Ahrens), sin el recorte del encuadre'}
    for t, x in json.load(open(f'{REPO}/festivals/staging/bogoshorts-2026-afiches-hallados.json', encoding='utf-8'))['afiches'].items():
        if os.path.exists(f"{REPO}/{x['archivo']}"):
            out[t] = {'archivo': x['archivo'], 'sobre_tmdb': True, 'url': x['url'], 'fuente': f"afiche oficial de la obra ({x['pagina']})"}
    for obras in cortos.values():
        for o in obras:
            t = o['titulo']
            if t in out or t in NO or (enr.get(t) or {}).get('poster_path'):
                continue
            a = (altas.get(t) or {}).get('afiche') or {}
            if a.get('archivo') and os.path.exists(f"{REPO}/{a['archivo']}"):
                # el recorte le cortó el título: el original se estira a 2:3 (proporción TMDB)
                if t == 'Ni aquí, ni allá':
                    a['archivo'] = a['archivo'].replace('.jpg', '-original.jpg')
                out[t] = {'archivo': a['archivo'], 'fuente': a['fuente'], 'url': a['url']}
                continue
            ap = [n(w) for x in re.split(r',| y ', o.get('director') or '') if x.strip() for w in x.split()[-2:] if len(w) > 2]
            for k, v in [c for x in [t] + o.get('titulos_alt', []) for c in ix.get(n(x), [])] + \
                    ([(ALIAS[t], web[ALIAS[t]])] if t in ALIAS else []):
                if not v.get('poster'):
                    continue
                pag = n(open(f'{REPO}/fuentes/bogoshorts-2026/web-cortos/{k}.html', encoding='utf-8', errors='ignore').read())
                if not any(x and x in pag for x in ap):
                    notas.append(f'{t}: corto/{k} no nombra a {o.get("director")}')
                    continue
                if re.search(r'fotograma|still', v['poster'], re.I):
                    notas.append(f'{t}: corto/{k} trae un fotograma, no un afiche')
                    continue
                p = f'{DIR}/{k}.{v["poster"].rsplit(".", 1)[-1].lower()}'
                if not os.path.exists(p) and '--bajar' in sys.argv:
                    subprocess.run(['curl', '-sfL', '--max-time', '90', '-o', p, v['poster']])
                if not os.path.exists(p):
                    notas.append(f'{t}: no bajó {v["poster"]}')
                    continue
                try:
                    im = Image.open(p)
                    im.load()
                except OSError:
                    notas.append(f'{t}: {os.path.basename(p)} bajó incompleto')
                    continue
                w, h = im.size
                if not 0.55 <= w / h <= 0.8:
                    notas.append(f'{t}: {w}×{h} no es vertical 2:3')
                    continue
                out[t] = {'archivo': os.path.relpath(os.path.realpath(p), os.path.realpath(REPO)) if not p.startswith(REPO) else p[len(REPO) + 1:],
                          'fuente': f'póster oficial de la ficha de la obra en la web del festival ({v["url"]}), {w}×{h}', 'url': v['poster']}
                break
    json.dump({'_provenance': provenance('https://festival.bogoshorts.com/corto/<n>', metodo='póster de la ficha de la obra en la web del festival y afiches del registro de altas; solo donde TMDB no tiene'),
               'afiches': out}, open(f'{ST}-afiches.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(out)} afiches declarados')
    for x in notas:
        print('  ·', x)


if __name__ == '__main__':
    main()
