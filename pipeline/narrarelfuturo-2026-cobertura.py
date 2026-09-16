#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""narrarelfuturo-2026-cobertura.py — el SITIO ENTERO contra lo que extrajimos.

POR QUÉ. Revisé la web del festival más de siete veces —menú, parrilla, fichas—
y en cada pasada aparecía algo nuevo: primero los talleres, después las fichas
de obra, después el og:image, después las charlas. El error no era de lectura
sino de MÉTODO: estaba mirando las páginas a las que la parrilla enlaza, y la
parrilla de un festival no es el programa del festival. Una web publica su
índice completo —/wp-sitemap.xml— y ese índice es una lista CERRADA contra la
que se puede verificar. Verificar lo transcrito no verifica lo descartado
(docs: cobertura inversa por página).

QUÉ HACE. Trae todas las páginas del sitio, se queda con las modificadas en
2026 —el resto es archivo de ediciones anteriores— y comprueba que cada una
está cubierta por algún sidecar nuestro, o declarada aquí abajo con su motivo.
Falla si aparece una página 2026 que nadie mira. No extrae nada: vigila.

Lee   https://narrarelfuturo.com/page-sitemap.xml
      festivals/staging/narrarelfuturo-2026-{obras,talleres,charlas}.json
"""
import io, json, os, re, subprocess, sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
SITEMAP = 'https://narrarelfuturo.com/page-sitemap.xml'

# Páginas de 2026 que NO son actividad, con el motivo. Cada línea es una
# decisión, no un descarte silencioso: si mañana alguna pasa a serlo, se ve.
FUERA = {
    r'^/$': 'portada',
    r'^/home/?$|^/home-parallax/?$': 'plantillas del tema',
    r'^/nef/?$': 'quiénes somos',
    r'^/programa2026/?$': 'teaser: «la programación se revela muy pronto»',
    r'^/programa-2026/?$': 'índice de la parrilla (lo lee -web.py)',
    r'^/talleres-2026/?$': 'índice de talleres (lo lee -talleres.py)',
    r'^/charlas-2026/?$': 'índice de charlas (lo lee -charlas.py)',
    r'^/programa-2026/(cortos|vr-2026)[^/]*/?$': 'carpeta de programa: sin texto propio, solo el título',
    r'^/invitados': 'fichas de PERSONAS, no de actividades (talleristas, panelistas y tutores del NewMediaLab)',
    r'^/hackathonvr360/?$': ('laboratorio de 20 seleccionados: convocatoria cerrada el 8 sep, sede que '
                             'los participantes reciben por correo. Su día 4 —estreno de los cortos VR360 '
                             'el sábado 19 en la Cinemateca— SÍ es público, pero el festival no publica '
                             'hora y la agenda de la Cinemateca no lo lista (se revisaron sus 46 nodos '
                             'de la ventana). Sin hora no entra: el formato intermedio no la inventa.'),
    r'^/elements/': 'páginas de demostración del tema',
    r'^/secciones/': 'cartelera de ediciones pasadas (obras de 2022–2024)',
}


def bajar(url, nombre):
    p = f'{REPO}/fuentes/narrarelfuturo-2026/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 500:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, url, '-o', p], check=True)
    return io.open(p, encoding='utf-8', errors='replace').read()


def cubiertas():
    """Las URLs que algún sidecar nuestro dice haber leído."""
    out = set()
    for n, clave in (('obras', 'obras'), ('talleres', None), ('charlas', 'charlas')):
        p = f'{ST}/narrarelfuturo-2026-{n}.json'
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding='utf-8'))
        filas = d if isinstance(d, list) else (d.get(clave or n) or [])
        for f in filas:
            if f.get('_src'):
                out.add(unquote(f['_src']).rstrip('/'))
    return out


def main():
    x = bajar(SITEMAP, 'page-sitemap.xml')
    urls = [(unquote(u), m) for u, m in
            re.findall(r'<url>\s*<loc>([^<]+)</loc>\s*(?:<lastmod>([^<]*)</lastmod>)?', x)]
    de2026 = [(u, m) for u, m in urls if (m or '').startswith('2026')]
    cub = cubiertas()
    huerfanas, declaradas = [], 0
    for u, _ in de2026:
        if u.rstrip('/') in cub:
            continue
        ruta = '/' + u.split('narrarelfuturo.com/', 1)[-1]
        if any(re.search(p, ruta) for p in FUERA):
            declaradas += 1
            continue
        huerfanas.append(ruta)
    print(f'── cobertura del sitio · {len(urls)} páginas, {len(de2026)} tocadas en 2026')
    print(f'   leídas por un sidecar: {len(de2026) - declaradas - len(huerfanas)}')
    print(f'   fuera, declaradas:     {declaradas}')
    if huerfanas:
        print(f'   ✗ SIN MIRAR ({len(huerfanas)}): una página de 2026 que nadie lee')
        for r in huerfanas:
            print('      ', r)
        sys.exit(1)
    print('   ✓ ninguna página de 2026 queda sin mirar')


if __name__ == '__main__':
    main()
