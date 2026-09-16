# -*- coding: utf-8 -*-
"""narrarelfuturo.com/talleres-2026/<slug>/ → la franja académica, con imágenes.

La página índice enlaza una ficha por taller y cada ficha trae día, rango
horario, sede, tallerista con su país, duración, cupos y descripción — más el
RETRATO del tallerista en wp-content/uploads.

Las fichas NO son uniformes: unas rotulan «Tallerista:» y ponen el nombre en la
línea siguiente, otras lo escriben inline; el día llega como «Jueves 17 de
Septiembre», «17 de Sep» o «Viernes 18 de Sep». Por eso el parser es tolerante
y, lo que no puede llenar, LO DECLARA al final en vez de adivinarlo: una hora
inventada en una franja académica se ve igual de bien que una real.

La imagen se guarda en su forma ORIGINAL, sin la variante «-1024x476» que
WordPress genera: el encuadre de pósters parte del archivo original (POSTERS.md
§3) y encadenar recortes sobre recortes acumula deformación.
"""
import io, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
INDICE = 'https://narrarelfuturo.com/talleres-2026/'
SALIDA = f'{ST}/narrarelfuturo-2026-talleres.json'

MES = {'sep': '09', 'septiembre': '09'}
RE_DIA = re.compile(r'(?:(?:Lun|Mar|Mié|Mie|Jue|Vie|Sáb|Sab|Dom)[a-zé]*\s+)?(\d{1,2})\s+de\s+(Sep\w*)', re.I)
RE_RANGO = re.compile(r'(\d{1,2}):(\d{2})\s*([ap])?m?\s*a\s*(\d{1,2})(?::(\d{2}))?\s*([apm])', re.I)
# La fuente nombra el mismo lugar de varias formas y cada variante partiría las
# funciones: «UTADEO» es la Tadeo, y «Taller de la Imagen» es una SALA dentro de
# la Cinemateca. Tabla explícita, nunca heurística — la lección de FICDEH.
SEDES = {
    'Taller de la Imagen': ('Cinemateca de Bogotá', 'Taller de la Imagen'),
    # Misma casa, otro nombre: cinco fichas escriben «Taller de Creación
    # Audiovisual» donde otras cinco dicen «Taller de la Imagen». Las diez
    # nombran además «Cinemateca de Bogotá», que es la sede. Sin esta entrada la
    # sala se perdía en la mitad de los talleres.
    'Taller de Creación Audiovisual': ('Cinemateca de Bogotá', 'Taller de Creación Audiovisual'),
    'Cinemateca de Bogotá': ('Cinemateca de Bogotá', ''),
    'Universidad Jorge Tadeo Lozano': ('Universidad Jorge Tadeo Lozano', ''),
    'UTADEO': ('Universidad Jorge Tadeo Lozano', ''),
}


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    import html as _h
    t = _h.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def bajar(url, nombre):
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 5000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
        time.sleep(0.3)
    return io.open(p, encoding='utf-8', errors='replace').read()


def h24(hh, mm, ap):
    h = int(hh) % 12 + (12 if (ap or '').lower().startswith('p') else 0)
    return f'{h:02d}:{mm or "00"}'


def parse(slug, h):
    L = texto(h)
    d = {'_slug': slug, '_src': f'{INDICE}{slug}/', 'tipo': 'taller'}
    d['titulo'] = re.sub(r'\s*-\s*#NarrarElFuturo\s*$', '', L[0]).strip()
    for k, x in enumerate(L):
        if re.match(r'^Tallerista[s]?:$', x) and k + 1 < len(L):
            d.setdefault('tallerista', L[k + 1])
        m = re.match(r'^Tallerista[s]?:\s*(.+)$', x)
        if m and m.group(1).strip():
            d.setdefault('tallerista', m.group(1).strip())
        if re.fullmatch(r'\(([^)]+)\)', x) and not d.get('pais'):
            d['pais'] = x.strip('()')
        if re.match(r'^Participantes:?$', x) and k + 1 < len(L):
            d.setdefault('cupos', L[k + 1])
        m = re.match(r'^\.?\s*Participantes:\s*(\d+)', x)
        if m:
            d.setdefault('cupos', m.group(1))
        md = RE_DIA.search(x)
        if md and not d.get('dia'):
            d['dia'] = f"2026-{MES.get(md.group(2)[:3].lower(),'09')}-{int(md.group(1)):02d}"
        mr = RE_RANGO.search(x)
        if mr and not d.get('hora'):
            d['hora'] = h24(mr.group(1), mr.group(2), mr.group(3) or mr.group(6))
            fin = h24(mr.group(4), mr.group(5), mr.group(6))
            ini = int(d['hora'][:2]) * 60 + int(d['hora'][3:])
            f2 = int(fin[:2]) * 60 + int(fin[3:])
            if f2 > ini:
                d['duracion_min'] = f2 - ini
            d['_rango'] = x
        for variante, (sede, sala) in SEDES.items():
            if variante in x:
                d.setdefault('sede', sede)
                if sala:
                    d.setdefault('sala', sala)
                break
        # tallerista en la forma «Con NOMBRE» / «(País)», que es como lo
        # escriben siete de las once fichas: sin el rótulo «Tallerista:».
        if x == 'Con' and k + 1 < len(L) and not d.get('tallerista'):
            d['tallerista'] = L[k + 1]
            if k + 2 < len(L) and re.fullmatch(r'\(([^)]+)\)\.?', L[k + 2]):
                d.setdefault('pais', L[k + 2].strip('().'))
    largos = [x for x in L if len(x) > 140]
    if largos:
        d['sinopsis'] = largos[0]
    # retrato del tallerista: original, sin la variante de tamaño de WordPress
    ims = [u for u in dict.fromkeys(
        re.findall(r'(https://narrarelfuturo\.com/wp-content/uploads/[^"\s]+?\.(?:jpg|jpeg|png|webp))', h, re.I))
        if not re.search(r'-\d+x\d+\.', u) and 'Mesa-de-trabajo' not in u]
    if ims:
        d['imagen'] = ims[0]
        d['_imagenes'] = ims[:4]
    m = re.search(r'href="([^"]+)"[^>]*>(?:(?!</a>).)*?Inscrib', h, re.S | re.I)
    if m:
        d['registration_url'] = re.sub(r'^http://', 'https://', m.group(1))
    d['acceso'] = ('Entrada gratis con inscripción' if d.get('registration_url')
                   else ('Entrada libre' if re.search(r'Entrada libre', h, re.I) else lib.DESCONOCIDO))
    return d


def del_indice(idx):
    """tallerista y país desde el ÍNDICE, que los escribe «Con Nombre (País)».
    Siete de las once fichas no rotulan «Tallerista:» y el nombre queda suelto en
    el cuerpo; el índice sí es regular. Se cruza por el enlace de cada ficha, no
    por parecido de títulos."""
    m = {}
    for b in re.split(r'(?=<a[^>]+href="https://narrarelfuturo\.com/talleres-2026/)', idx)[1:]:
        u = re.match(r'<a[^>]+href="(https://narrarelfuturo\.com/talleres-2026/[^"#?]+)"', b)
        if not u:
            continue
        t = texto(b[:4000])
        for k, x in enumerate(t):
            mm = re.match(r'^Con\s+(.+?)\s*$', x)
            if mm and k + 1 < len(t) and re.fullmatch(r'\(([^)]+)\)\.?', t[k + 1]):
                m[u.group(1).rstrip('/').split('/')[-1]] = (
                    mm.group(1).strip(), t[k + 1].strip('().'))
                break
    return m


def main():
    idx = bajar(INDICE, 'talleres-indice.html')
    nombres = del_indice(idx)
    urls = sorted(set(re.findall(r'href="(https://narrarelfuturo\.com/talleres-2026/[^"#?]+)"', idx)))
    out = []
    for u in urls:
        slug = u.rstrip('/').split('/')[-1]
        d = parse(slug, bajar(u, f'taller-{slug}.html'))
        if slug in nombres and not d.get('tallerista'):
            d['tallerista'], d['_tallerista_src'] = nombres[slug][0], 'índice de talleres'
            d.setdefault('pais', nombres[slug][1])
        out.append(d)
    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        INDICE, metodo='una ficha por taller, enlazadas desde el índice',
        nota='fichas NO uniformes: el rótulo del tallerista y la forma del día cambian entre ellas'),
        '_talleres': len(out), 'talleres': out},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(out)} talleres')
    for d in out:
        print(f"  {d.get('dia','   ?      ')} {d.get('hora','  ?  ')}  {d['titulo'][:34]:36} "
              f"{(d.get('tallerista') or '—')[:24]:26} {(d.get('sala') or d.get('sede') or '—')[:20]:22} "
              f"{'img' if d.get('imagen') else '—'}")
    faltan = {k: [d['_slug'][:26] for d in out if not d.get(k)]
              for k in ('dia', 'hora', 'tallerista', 'sede', 'imagen')}
    for k, v in faltan.items():
        if v:
            print(f'  ⚠ sin {k}: {v}')


if __name__ == '__main__':
    main()
