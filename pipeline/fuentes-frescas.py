#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""fuentes-frescas.py <fest-id> — ¿la fuente cambió después de que la leímos?

POR QUÉ EXISTE (18 sep 2026). La página de talleres de FICMA cambió a las 16:05
del día anterior al arranque: la masterclass de Andrés Buitrago pasó de la mañana
a las 4 de la tarde. Nuestra captura era de dos días antes y el parser la leía de
la caché, así que no se enteró nadie. Estuvimos a punto de preguntarle al
festival por una hora que ya había corregido.

Un sidecar guarda `capturado`. El servidor sabe cuándo cambió la página. Nadie
comparaba las dos cosas, y esa comparación es barata.

CÓMO. Por cada sidecar del festival saca las URL de su `_provenance` y busca la
fecha de modificación de cada una:

  · SITEMAP primero. En WordPress —que es lo que usa casi todo festival— el
    sitemap trae `<lastmod>` por página, al minuto, y es lo que de verdad se
    actualiza cuando editan. Es la señal que descubrió el cambio de FICMA.
  · Si no hay sitemap, `Last-Modified` de una petición HEAD.
  · Lo que no se puede fechar se DICE. Instagram no publica fecha de
    modificación de un post y el silencio no puede parecer un «no cambió»:
    esas fuentes salen listadas como «no verificable», que es distinto de
    «verificada».

Sale con 1 si alguna fuente es más nueva que nuestra lectura. Eso no significa
que el dato esté mal: significa que hay que volver a leer antes de publicar.

    python3 pipeline/fuentes-frescas.py ficma-2026
"""
import datetime, email.utils, glob, json, os, re, subprocess, sys, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
# Dominios que no publican fecha de modificación por recurso. No se adivina.
SIN_FECHA = ('instagram.com', 'linktr.ee', 'drive.google.com', 'forms.gle',
             'docs.google.com', 'themoviedb.org', 'letterboxd.com')


def _curl(url, head=False):
    cmd = ['curl', '-sS', '-L', '--max-time', '40', '-A', UA]
    cmd += ['-I'] if head else []
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def sitemap(origen):
    """{url: fecha} del sitemap del sitio, si lo tiene."""
    out = {}
    for ruta in ('/sitemap_index.xml', '/sitemap.xml', '/wp-sitemap.xml'):
        x = _curl(origen + ruta)
        if '<sitemapindex' in x:
            for sub in re.findall(r'<loc>([^<]+)</loc>', x):
                y = _curl(sub.strip())
                for m in re.finditer(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', y, re.S):
                    out[m.group(1).strip().rstrip('/')] = m.group(2).strip()[:10]
        elif '<urlset' in x:
            for m in re.finditer(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', x, re.S):
                out[m.group(1).strip().rstrip('/')] = m.group(2).strip()[:10]
        if out:
            break
    return out


def last_modified(url):
    h = _curl(url, head=True)
    m = re.search(r'(?im)^last-modified:\s*(.+)$', h)
    if not m:
        return ''
    try:
        return email.utils.parsedate_to_datetime(m.group(1).strip()).date().isoformat()
    except Exception:
        return ''


def urls_de(prov):
    """Todas las URL que menciona un bloque de procedencia, en orden."""
    return list(dict.fromkeys(re.findall(r'https?://[^\s,;)"\'<>]+',
                                         json.dumps(prov, ensure_ascii=False))))


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: python3 pipeline/fuentes-frescas.py <fest-id>')
    fid = sys.argv[1]
    sidecars = sorted(glob.glob(f'{ST}/{fid}-*.json'))
    if not sidecars:
        sys.exit(f'no hay sidecars de {fid} en festivals/staging/')

    mapas, viejas, sin_fecha, frescas, sin_url = {}, [], [], 0, []
    for p in sidecars:
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        prov = d.get('_provenance')
        if not isinstance(prov, dict) or not prov.get('capturado'):
            continue
        base = os.path.basename(p)
        if prov.get('congelado'):
            continue                      # declarado: no se re-lee a propósito
        cap = prov['capturado'][:10]
        us = [u for u in urls_de(prov)]
        if not us:
            sin_url.append(base)
            continue
        for u in us:
            host = urllib.parse.urlparse(u).netloc
            if any(s in host for s in SIN_FECHA):
                sin_fecha.append(f'{base} ← {host}')
                continue
            origen = f'{urllib.parse.urlparse(u).scheme}://{host}'
            if origen not in mapas:
                mapas[origen] = sitemap(origen)
            mod = mapas[origen].get(u.rstrip('/')) or last_modified(u)
            if not mod:
                sin_fecha.append(f'{base} ← {u[:60]} (el servidor no da fecha)')
                continue
            if mod > cap:
                viejas.append(f'{base}: leído el {cap} y la fuente cambió el {mod} '
                              f'→ {u[:70]}')
            else:
                frescas += 1

    print(f'{fid}: {frescas} fuente(s) verificadas al día · {len(viejas)} vencida(s) · '
          f'{len(sin_fecha)} no verificable(s)')
    for s in dict.fromkeys(sin_fecha):
        print('   · no verificable:', s)
    for s in sin_url:
        print('   · sin URL en su procedencia:', s)
    if viejas:
        print('\n✗ hay que volver a leer antes de publicar:')
        for v in viejas:
            print('   ✗', v)
        sys.exit(1)
    print('\n✓ ninguna fuente fechable cambió después de que la leímos')


if __name__ == '__main__':
    main()
