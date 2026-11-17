#!/usr/bin/env python3
"""aleste-2026-programa.py — la web oficial del festival (alestfestival.com/programa2026)
→ festivals/staging/aleste-2026-programa.json (sidecar que leen el catálogo y el crudo).

LA FUENTE (16 nov 2026, la detectó el vigía): una página por obra, 40, con
sección, título, título original, dirección, año, país, duración, sinopsis y
una línea por función:
    «Bogotá · Sábado 28 nov · 14:30 · Cinemateca de Bogotá – Sala 3 · Seguida de conversatorio con los realizadores»
Es el programa completo de las dos ciudades; antes de ella Bogotá eran 5
láminas de IG.

    python3 pipeline/aleste-2026-programa.py            # lee lo bajado
    python3 pipeline/aleste-2026-programa.py --bajar    # baja índice + 40 páginas
"""
import glob, html, io, json, os, re, subprocess, sys, unicodedata, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

URL = 'https://www.alestfestival.com/programa2026'
DIR = f'{REPO}/fuentes/aleste-2026/programa'
OUT = f'{REPO}/festivals/staging/aleste-2026-programa.json'
DIAS = {'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'}


def bajar():
    os.makedirs(DIR, exist_ok=True)
    idx = f'{DIR}/programa2026.html'
    subprocess.run(['curl', '-sL', '-A', 'Mozilla/5.0', URL, '-o', idx], check=True)
    urls = sorted(set(re.findall(r'href="(https://www\.alestfestival\.com/programa2026/[^"]+)"',
                                 open(idx, encoding='utf-8').read())))
    for u in urls:
        f = f'{DIR}/{urllib.parse.unquote(u.rsplit("/", 1)[1])}.html'
        subprocess.run(['curl', '-sL', '-A', 'Mozilla/5.0', u, '-o', f], check=True)
    print(f'✓ índice + {len(urls)} páginas → {os.path.relpath(DIR, REPO)}')


def lineas(path):
    s = io.open(path, encoding='utf-8').read()
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', s))
    ls = [unicodedata.normalize('NFC', re.sub(r'\s+', ' ', l.replace('\u200b', ''))).strip() for l in t.split('\n')]
    ls = [l for l in ls if l]
    i = ls.index('< Back')
    j = next(k for k in range(i, len(ls)) if ls[k] in ('ENTRADAS', 'Comparte esta película'))
    return ls[i + 1:j]


FUNC = re.compile(r'^(Medellín|Bogotá) · (\w+) (\d{1,2}) nov · (\d{1,2}:\d{2}) · ([^·]+?)(?: · (.+))?$')


def leer(path):
    """Las líneas de la ficha, en orden fijo: sección, título, título original,
    dirección, [año], país, «N min», sinopsis, funciones."""
    L = [l for l in lineas(path) if l != '.']   # 16 nov: la web cierra la ficha con un «.» suelto
    nom = os.path.basename(path)
    k = next(i for i, l in enumerate(L) if re.fullmatch(r'\d{1,3} min', l))
    cab = L[:k]
    if len(cab) == 6:
        sec, tit, orig, dire, anio, pais = cab
    elif len(cab) == 5:                       # los cortos de «Hecho en Colombia»: sin año
        (sec, tit, orig, dire, pais), anio = cab, None
    else:
        sys.exit(f'✗ {nom}: cabecera de {len(cab)} líneas: {cab}')
    # 16 nov: la línea de país pasó a «País, 2025. 103 min» (y el «N min» sigue aparte)
    pais = re.sub(r',\s*\d{4}\.\s*\d{1,3} min$', '', pais).strip()
    if anio is not None and not re.fullmatch(r'\d{4}', anio):
        sys.exit(f'✗ {nom}: año raro «{anio}»')
    funcs, sinopsis = [], []
    for l in L[k + 1:]:
        m = FUNC.match(l)
        if not m:
            if funcs:
                sys.exit(f'✗ {nom}: línea después de las funciones: «{l}»')
            sinopsis.append(l)
            continue
        ciudad, dsem, dia, hora, lugar, nota = m.groups()
        if dsem.lower() not in DIAS:
            sys.exit(f'✗ {nom}: día de semana raro «{dsem}»')
        sede, _, sala = (x.strip() for x in lugar.partition(' – '))
        funcs.append({'ciudad': ciudad, 'dia': f'2026-11-{int(dia):02d}', 'dia_semana': dsem,
                      'hora': f'{int(hora[:-3]):02d}{hora[-3:]}', 'sede': sede, 'sala': sala or None,
                      'nota': (nota or '').strip() or None})
    if not funcs:
        sys.exit(f'✗ {nom}: sin funciones')
    return {'pagina': nom[:-5], 'seccion': sec, 'titulo': tit, 'titulo_original': orig,
            'director': None if dire == 'Varios' else dire, 'anio': int(anio) if anio else None,
            'pais': pais, 'duracion_min': int(L[k].split()[0]), 'sinopsis': ' '.join(sinopsis),
            'funciones': funcs}


def main():
    if '--bajar' in sys.argv:
        bajar()
    pags = sorted(p for p in glob.glob(f'{DIR}/*.html') if not p.endswith('/programa2026.html'))
    obras = [leer(p) for p in pags]
    n = sum(len(o['funciones']) for o in obras)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(URL, metodo='una página por obra (curl), texto plano: sección, '
                                  'ficha y «Ciudad · Día · Hora · Sede – Sala · nota»'),
        'obras': obras}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(obras)} obras, {n} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
