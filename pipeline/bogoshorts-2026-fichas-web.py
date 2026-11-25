#!/usr/bin/env python3
"""bogoshorts-2026-fichas-web.py — la ficha de cada obra en la web del festival.

POR QUÉ (16 nov 2026). La web del festival (festival.bogoshorts.com/corto/<n>)
tiene una página por obra y muchas traen el PÓSTER OFICIAL. Ninguna fuente
obligatoria la nombraba y cinco tandas dieron obras por «sin afiche» que lo
tenían ahí; hoy es la fuente `pagina_del_festival` del registro de altas. Las
tandas la buscaban a mano, id por id, con un servidor lento (114 páginas no
respondieron en una pasada). Esto lo baja UNA vez, con reintentos, y deja el
índice título → página → póster.

    python3 pipeline/bogoshorts-2026-fichas-web.py --bajar [--desde 3800 --hasta 4700]
    python3 pipeline/bogoshorts-2026-fichas-web.py            # rearma el índice con lo bajado

Escribe fuentes/bogoshorts-2026/web-cortos/<n>.html y
festivals/staging/bogoshorts-2026-fichas-web.json:
  {"fichas": {"<n>": {"titulo", "url", "poster"?}}, "_faltan": [ids sin respuesta]}
"""
import glob, html, io, json, os, re, subprocess, sys, time, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = f'{REPO}/fuentes/bogoshorts-2026/web-cortos'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-fichas-web.json'
BASE = 'https://festival.bogoshorts.com/corto/'


def _arg(f, d):
    return int(sys.argv[sys.argv.index(f) + 1]) if f in sys.argv else d


def bajar(desde, hasta):
    os.makedirs(DIR, exist_ok=True)
    faltan = []
    for n in range(desde, hasta + 1):
        p = f'{DIR}/{n}.html'
        if os.path.exists(p) and os.path.getsize(p) > 2000:
            continue
        ok = False
        for intento in range(3):
            r = subprocess.run(['curl', '-sL', '--max-time', '60', '-A', 'Mozilla/5.0', '-o', p,
                                '-w', '%{http_code}', BASE + str(n)], capture_output=True, text=True)
            if r.stdout.strip() == '200' and os.path.getsize(p) > 2000:
                ok = True
                break
            time.sleep(2 * (intento + 1))
        if not ok:
            if os.path.exists(p):
                os.remove(p)
            faltan.append(n)
    return faltan


def leer(p):
    s = io.open(p, encoding='utf-8', errors='ignore').read()
    t = re.search(r'<title>(.*?)</title>', s, re.S)
    titulo = html.unescape(t.group(1)).split(' | ')[0].strip() if t else ''
    if not titulo or titulo.lower().startswith('bogoshorts'):
        return None
    pos = re.findall(r'(https://festival\.bogoshorts\.com/images/peliculas/[^"\']+\.(?:jpe?g|png|webp))', s, re.I)
    n = os.path.basename(p)[:-5]
    e = {'titulo': unicodedata.normalize('NFC', titulo), 'url': BASE + n}
    if pos:
        e['poster'] = pos[0]
    return n, e


def main():
    faltan = []
    if '--bajar' in sys.argv:
        faltan = bajar(_arg('--desde', 3800), _arg('--hasta', 4700))
    fichas = {}
    for p in sorted(glob.glob(f'{DIR}/*.html'), key=lambda x: int(os.path.basename(x)[:-5])):
        r = leer(p)
        if r:
            fichas[r[0]] = r[1]
    json.dump({'_provenance': {'fuente': BASE + '<n>', 'capturado': time.strftime('%Y-%m-%d'),
                               'metodo': 'curl con 3 reintentos; título del <title>, póster de /images/peliculas/'},
               'fichas': fichas, '_faltan': faltan},
              io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(fichas)} fichas ({sum(1 for e in fichas.values() if e.get("poster"))} con póster)'
          f'{f" · {len(faltan)} ids sin respuesta" if faltan else ""} → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
