#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ig.py <volcado.json> [--fest <id>] — Instagram como fuente de verdad.

POR QUÉ. Es donde más festivales publican antes que en su web, y donde a veces
publican lo ÚNICO: en #NarrarElFuturo, los seis conversatorios de la franja de
la Tadeo y el encuentro con las directoras de la inaugural no estaban en ninguna
otra parte. Extraerlo mal no es perder un adorno, es publicar un programa falso.

LAS TRES MITADES DEL PROBLEMA, medidas el 16 sep 2026:

  1. DESCUBRIR. Sin sesión el perfil enseña ~10 posts: el muro corta el scroll y
     el bloque «More posts» devuelve los mismos. CON sesión, 155.
  2. EL PIE. Sin sesión llega cortado a ~2170 caracteres —en el embed, en la
     página y en su `og:description`—. CON sesión viaja entero en
     `<meta name="description">`, que se puede pedir con un fetch por post.
  3. LA LÁMINA. La mitad del dato está PINTADO: título, dirección, país, año,
     sede, hora, el sello de sección. El pie no lo repite.

(1) y (2) viven en el navegador, que es donde hay sesión; (3) es de este script.
Por eso el reparto: el navegador VUELCA, este script LEE. El volcado se guarda
en fuentes/, así que el paso es re-corrible sin volver a pedirle nada a
Instagram — que además es lo prudente.

EL VOLCADO se hace en el navegador, con sesión abierta, así (el snippet vive
aquí para que no haya que redescubrirlo):

    // 1 · descubrir: scrollear el perfil recogiendo enlaces
    const v=new Set(); const r=()=>document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]')
      .forEach(a=>v.add(a.getAttribute('href'))); r();
    for(let i=0;i<12;i++){ scrollTo(0,document.body.scrollHeight);
      await new Promise(s=>setTimeout(s,1400)); r(); }
    // 2 · pie entero, un fetch por post (en tandas de ~12: el puente corta a 45s)
    const dec=s=>s.replace(/&#x([0-9a-f]+);/gi,(_,h)=>String.fromCodePoint(parseInt(h,16)));
    for (const href of v) { const h=await (await fetch(href,{credentials:'include'})).text();
      const pie=dec((h.match(/<meta name="description" content="([^"]*)"/)||[])[1]||'');
      const fecha=(pie.match(/on (\w+ \d{1,2}, \d{4})/)||[])[1]||null;
      /* … acumular {shortcode, fecha, pie} … */ }

LAS LÁMINAS NO VAN EN EL VOLCADO: el HTML que sirve la sesión no trae sus URLs
(`display_url` no aparece), y no hacen falta — el EMBED las da sin sesión, que
es lo que ya hace pipeline/ig_carrusel.py. Cada mitad por donde es más barata:
el pie por el navegador, la lámina por el embed.

EL VOLCADO SE VERSIONA en festivals/staging/<id>-ig-volcado.json, no en
fuentes/ (que está fuera del repo): es material de fuente que costó una sesión
abierta, y sin él este paso no se puede re-correr en otra máquina.

Lee   festivals/staging/<id>-ig-volcado.json  (el volcado del navegador)
      y, si existe, <id>-crudo.json (para cruzar)
Esc.  festivals/staging/<id>-ig-corpus.json   — pie + texto de cada lámina
      fuentes/ig/<shortcode>/NN.jpg           — las láminas, cacheadas

El nombre del sidecar es `-ig-corpus` a propósito: el parser del festival puede
seguir escribiendo su propio `-ig.json`, y así cada archivo conserva un solo
escritor ([sidecar-dos-escritores]).
"""
import io, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance
from ocr import leer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/ig'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
RE_HORA = re.compile(r'(\d{1,2}):(\d{2})\s*(?:a|p)\.?\s*m', re.I)


def urls_laminas(sc):
    """Las URLs de las láminas, vía el embed público (no necesita sesión)."""
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     'ig_carrusel.py'), sc],
                       capture_output=True, text=True)
    linea = (r.stdout or '').strip().split('\n')[0]
    if not linea.startswith('{'):
        return []
    return [l['url'] for l in json.loads(linea).get('laminas', []) if not l.get('video')]


def bajar_laminas(sc, urls):
    """Las imágenes del post, en fuentes/ig/<shortcode>/. Devuelve rutas."""
    d = f'{CACHE}/{sc}'
    os.makedirs(d, exist_ok=True)
    out = []
    for i, u in enumerate(urls):
        p = f'{d}/{i:02d}.jpg'
        if not os.path.exists(p) or os.path.getsize(p) < 5000:
            subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, u, '-o', p])
            time.sleep(0.2)
        if os.path.exists(p) and os.path.getsize(p) > 5000:
            out.append(p)
    return out


def horas(texto):
    return {f'{int(h) % 12 + (12 if "p" in m.group(0).lower() else 0):02d}:{mm}'
            for m in RE_HORA.finditer(texto) for h, mm in [m.groups()]}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    volcado = json.load(io.open(sys.argv[1], encoding='utf-8'))
    posts = volcado if isinstance(volcado, list) else volcado.get('posts', [])
    fest = None
    if '--fest' in sys.argv:
        fest = sys.argv[sys.argv.index('--fest') + 1]

    salida, total_lam = [], 0
    for p in posts:
        sc = p.get('shortcode') or p.get('code')
        rutas = bajar_laminas(sc, p.get('imagenes') or urls_laminas(sc))
        texto = leer(rutas)
        total_lam += len(rutas)
        salida.append({
            'shortcode': sc,
            'fecha': p.get('fecha'),
            'url': f'https://www.instagram.com/p/{sc}/',
            'pie': p.get('pie') or '',
            'laminas': [{'archivo': os.path.relpath(r, REPO), 'texto': texto.get(r, [])}
                        for r in rutas],
        })

    if fest:
        os.makedirs(ST, exist_ok=True)
        io.open(f'{ST}/{fest}-ig-corpus.json', 'w', encoding='utf-8').write(
            json.dumps({'_provenance': provenance(
                'instagram.com — perfil recorrido en el navegador CON SESIÓN; pie entero de '
                '<meta name="description"> y láminas leídas con el OCR del sistema',
                posts=len(salida), laminas=total_lam),
                'posts': salida}, ensure_ascii=False, indent=1) + '\n')
    print(f'── ig: {len(salida)} posts · {total_lam} láminas leídas'
          + (f' → {fest}-ig-corpus.json' if fest else ''))

    # CRUCE con el crudo, que es para lo que sirve tener el corpus: una hora
    # pintada o escrita que la parrilla no tiene es una función que nos falta —
    # o un cambio que el festival anunció solo por aquí.
    crudo_p = f'{ST}/{fest}-crudo.json' if fest else None
    if crudo_p and os.path.exists(crudo_p):
        crudo = json.load(io.open(crudo_p, encoding='utf-8'))
        nuestras = {f.get('hora') for f in crudo['funciones']}
        sueltas = {}
        for e in salida:
            t = e['pie'] + '\n' + '\n'.join(x for l in e['laminas'] for x in l['texto'])
            for h in horas(t) - nuestras:
                sueltas.setdefault(h, []).append(e['shortcode'])
        if sueltas:
            print('   horas anunciadas que la parrilla NO tiene:')
            for h, cs in sorted(sueltas.items()):
                print(f'      {h}  ← {", ".join(cs[:4])}')
        else:
            print('   ✓ toda hora anunciada en Instagram existe en la parrilla')


if __name__ == '__main__':
    main()
