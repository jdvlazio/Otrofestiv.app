# -*- coding: utf-8 -*-
"""Una ficha por obra desde narrarelfuturo.com/programa-2026/<slug>/.

LA FUENTE COMPLETA, y la encontré tarde. La página de programación enlaza una
ficha propia por obra —42— y ahí está lo que estuve buscando en los pies
truncados de Instagram: sinopsis entera, dirección, día, hora, sala, sede,
frase de acceso con su enlace, y el PÓSTER de la obra.

Se llega por el enlace «Ver Detalles» de cada tarjeta y por el título de cada
corto dentro de un programa; la ruta lleva el programa cuando la obra pertenece
a uno: `/programa-2026/cortos-·-aqua-ensayo-diversidad/refraccion/`.

POR QUÉ NO SE USA EL PIE DE INSTAGRAM PARA ESTO: el embed corta el pie a ~2.170
caracteres, a mitad de palabra. Leídas así, «El Futuro del Futuro» daba 5 obras
de 9 y «Narrar. Creer. Crecer» 2 de 10. La web no se corta.
"""
import io, json, os, re, subprocess, sys, time
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
BASE = 'https://narrarelfuturo.com/programa-2026/'
SALIDA = f'{ST}/narrarelfuturo-2026-obras.json'

MES = {'sep': '09'}
RE_FICHA = re.compile(r'^(?P<pais>[^·]+?)\s*·\s*(?P<anio>(?:19|20)\d\d)\s*·\s*(?P<dur>[^·]+?)\s*(?:·\s*(?P<gen>.+))?$')
RE_CUANDO = re.compile(r'(\d{1,2})\s+de\s+(Sep\w*)\.?\s+(\d{1,2}):(\d{2})\s*([ap])m', re.I)
SEDES = ('Cinemateca de Bogotá', 'Universidad Jorge Tadeo Lozano', 'Cinemateca Fontanar del Río')


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    import html as _h
    t = _h.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def minutos(s):
    m = re.match(r'^(\d+)\s*h\s*(\d+)?\s*min', s.strip())
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    m = re.match(r'^(\d+)\s*min', s.strip())
    return int(m.group(1)) if m else None


def bajar(url, nombre):
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
        time.sleep(0.25)
    return io.open(p, encoding='utf-8', errors='replace').read()


def parse(ruta, h):
    L = texto(h)
    partes = [unquote(x) for x in ruta.strip('/').split('/')]
    d = {'_src': BASE + ruta, '_slug': partes[-1]}
    if len(partes) > 1:
        d['programa'] = partes[0].replace('cortos ·', '').replace('cortos-·-', '').strip(' -·')
    # el título es la línea ANTES de la ficha «País · Año · Duración · Género»
    for k, x in enumerate(L):
        m = RE_FICHA.match(x)
        if m and minutos(m.group('dur')) is not None and k:
            d['titulo'] = L[k - 1]
            d.update({'pais': m.group('pais').strip(), 'anio': int(m.group('anio')),
                      'duracion_min': minutos(m.group('dur')),
                      'genero': (m.group('gen') or '').strip()})
            break
    for k, x in enumerate(L):
        if x == 'Dir.' and k + 1 < len(L):
            d.setdefault('director', L[k + 1])
        mc = RE_CUANDO.search(x)
        if mc and not d.get('dia'):
            hh = int(mc.group(3)) % 12 + (12 if mc.group(5).lower() == 'p' else 0)
            d['dia'] = f"2026-{MES.get(mc.group(2)[:3].lower(),'09')}-{int(mc.group(1)):02d}"
            d['hora'] = f'{hh:02d}:{mc.group(4)}'
        if re.match(r'^\*?\s*Entrada', x, re.I):
            d.setdefault('acceso', x.lstrip('*').strip())
        if re.match(r'^(Sala|Hemiciclo|Aula|Laboratorio)\b', x):
            d.setdefault('sala', x.rstrip(',').strip())
        for s in SEDES:
            if s in x:
                d.setdefault('sede', s)
    largos = [x for x in L if len(x) > 160 and 'Festival de Cine & Nuevos Medios es un punto' not in x]
    if largos:
        d['sinopsis'] = largos[0]
    ims = [u for u in dict.fromkeys(re.findall(
        r'(https://narrarelfuturo\.com/wp-content/uploads/[^"\s]+?\.(?:jpg|jpeg|png|webp))', h, re.I))
        if not re.search(r'-\d+x\d+\.', u) and 'Mesa-de-trabajo' not in u]
    poster = [u for u in ims if 'poster' in u.lower()]
    if poster:
        d['poster'] = poster[0]
    if ims:
        d['imagenes'] = ims[:5]
    m = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).){0,600}?Inscrib', h, re.S | re.I)
    if m:
        d['registration_url'] = re.sub(r'^http://', 'https://', m.group(1))
    m = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).){0,600}?(?:boleta|Compra)', h, re.S | re.I)
    if m:
        d['ticket_url'] = re.sub(r'^http://', 'https://', m.group(1))
    d.setdefault('acceso', 'Entrada gratis con inscripción' if d.get('registration_url')
                 else ('Boletería' if d.get('ticket_url') else lib.DESCONOCIDO))
    return d


def main():
    idx = bajar(BASE, 'programa-2026.html')
    rutas = sorted(set(re.findall(r'href="https://narrarelfuturo\.com/programa-2026/([^"#?]+/)"', idx)))
    out = []
    for r in rutas:
        nombre = 'obra-' + re.sub(r'[^A-Za-z0-9]+', '-', unquote(r).strip('/'))[:70] + '.html'
        out.append(parse(r, bajar(BASE + r, nombre)))

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        BASE + '<slug>/',
        metodo='una ficha por obra, enlazadas desde el programa; la ruta lleva el programa cuando la obra pertenece a uno',
        nota='el pie de Instagram se corta a ~2.170 caracteres y daba 5 obras de 9; la web no se corta'),
        '_obras': len(out), 'obras': out},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(out)} obras')
    campos = ('titulo', 'director', 'sinopsis', 'poster', 'dia', 'hora', 'sede', 'acceso', 'genero')
    for c in campos:
        n = sum(1 for o in out if o.get(c))
        print(f'   {c:<12} {n:>3}/{len(out)}')
    sin = [o['_slug'] for o in out if not o.get('titulo')]
    if sin:
        print('   ⚠ sin título:', sin[:6])


if __name__ == '__main__':
    main()
