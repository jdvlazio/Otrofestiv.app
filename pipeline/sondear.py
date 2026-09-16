# -*- coding: utf-8 -*-
"""sondear.py <url|archivo> — la FORMA de una fuente, antes de escribir el parser.

Existe por una cuenta concreta: montando #NarrarElFuturo (15 sep 2026) reescribí
el mismo parser TRES veces, y las tres fallaron por suponer la forma de la
fuente en vez de mirarla. El regex del día aceptaba «Mié» y la página decía
«Martes». La ventana del <a> era de 120 caracteres y el markup mete 180. El
póster era «la primera imagen que diga poster» y la primera es un resto de
plantilla. Cada vez que miré primero, salió a la primera.

Esto no parsea nada: enseña. En diez segundos dice qué bloque se repite, qué
formas de línea hay, qué etiquetas se repiten y cuántos de cada cosa — que es
exactamente lo que hace falta ANTES de escribir la primera expresión regular.

    python3 pipeline/sondear.py https://…/programa/
    python3 pipeline/sondear.py fuentes/<fest>/pagina.html --bloque evento-card
"""
import collections, html, io, os, re, subprocess, sys

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Safari/605.1.15')


def bajar(origen):
    if os.path.exists(origen):
        return io.open(origen, encoding='utf-8', errors='replace').read()
    r = subprocess.run(['curl', '-sL', '--max-time', '45', '-A', UA, origen],
                       capture_output=True, text=True)
    return r.stdout


def lineas(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def forma(x):
    """La línea, con sus valores reemplazados por marcas: dos líneas con la
    misma forma son el mismo campo aunque digan cosas distintas."""
    s = re.sub(r'\d+', '#', x)
    s = re.sub(r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', 'Aa', s)
    s = re.sub(r'[a-záéíóúñ]+', 'aa', s)
    return re.sub(r'\s+', ' ', s)[:44]


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: python3 pipeline/sondear.py <url|archivo> [--bloque <clase>]')
    h = bajar(sys.argv[1])
    print(f'── {len(h):,} bytes\n')

    # 1 · clases que se repiten: candidatas a «el bloque que es una entrada»
    cls = collections.Counter()
    for m in re.finditer(r'class="([^"]+)"', h):
        for c in m.group(1).split():
            if not re.match(r'^(e-|elementor|wp-|has-|is-|css-)', c):
                cls[c] += 1
    rep = [(c, n) for c, n in cls.most_common(12) if n > 2]
    print('CLASES QUE SE REPITEN (candidatas a bloque):')
    for c, n in rep[:8]:
        print(f'   {n:>4}×  {c}')

    # 2 · si se pide un bloque, se trocea y se enseña UNA entrada entera
    if '--bloque' in sys.argv:
        b = sys.argv[sys.argv.index('--bloque') + 1]
        partes = re.split(rf'(?=<[^>]+class="[^"]*{re.escape(b)})', h)[1:]
        print(f'\nBLOQUES «{b}»: {len(partes)}')
        if partes:
            L = lineas(partes[0])
            print(f'   la PRIMERA entrada, línea por línea ({len(L)} líneas):')
            for i, x in enumerate(L[:18]):
                print(f'     [{i:>2}] {x[:78]}')
            # cuántas líneas tiene cada bloque: si varía mucho, no son uniformes
            tam = collections.Counter(len(lineas(p)) for p in partes)
            print(f'   tamaños de bloque: {dict(sorted(tam.items()))}')
        return

    # 3 · sin bloque: las formas de línea más frecuentes
    L = lineas(h)
    print(f'\n{len(L)} líneas · formas más frecuentes:')
    for f, n in collections.Counter(forma(x) for x in L).most_common(14):
        ej = next(x for x in L if forma(x) == f)
        print(f'   {n:>4}×  {f:<46} p.ej. «{ej[:38]}»')

    # 4 · etiquetas «Campo:» que la fuente usa
    et = collections.Counter(m.group(1) for m in re.finditer(r'^([A-ZÁÉÍÓÚ][\w áéíóúñ]{2,24}):\s*$', '\n'.join(L), re.M))
    if et:
        print('\nETIQUETAS de campo:')
        for e, n in et.most_common(12):
            print(f'   {n:>4}×  {e}')


if __name__ == '__main__':
    main()
