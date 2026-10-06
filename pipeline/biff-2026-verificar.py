#!/usr/bin/env python3
"""biff-2026-verificar.py — lo que se va a publicar, contra las fuentes del festival.

El crudo ya cruza las fichas del PDF con la tabla por días. Esto mira el OTRO
extremo: el BUILD —lo que llega a la app— contra dos lecturas independientes:

  · la tabla «Programación por días»: toda fila está en el build con su día,
    hora y título, y el build no publica ninguna función que no esté en ella;
  · la agenda de la Cinemateca de Bogotá: toda función suya que el festival
    también publica está en el build con la MISMA sala;
  · toda sede tiene su pin verificado a mano.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'biff-2026'
CIUDAD = 'Bogotá'
D = f'{REPO}/fuentes/biff-2026'
# lo que la Cinemateca no trae y el festival sí, mirado
CINEMATECA_NO_TRAE = {('2026-10-11', '14:00', 'hermanas'): 'aún no publicada en la agenda (la grilla la confirma a las 14:00)',
                      ('2026-10-10', '16:00', 'no quiero ser un hombre'): 'al aire libre, en la Calle Museo'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    tabla = json.load(io.open(f'{D}/por-dias.json', encoding='utf-8'))['funciones']
    cin = json.load(io.open(f'{D}/cinemateca/funciones.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    crudo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-crudo.json', encoding='utf-8'))['funciones']
    # el título del build puede ser el de la Cinemateca o, en las charlas, el
    # abreviado: se compara por el título que imprime el PDF, que el crudo guarda
    pdf_de = {}
    for f in crudo:
        pdf_de[(f['dia'], f['hora'], plano(f['titulo']))] = plano(f.get('titulo_pdf') or f['titulo'])
    pub = {}
    for f in build['films']:
        k = (f['day'], f['time'], plano(f['title']))
        pub[(k[0], k[1], pdf_de.get(k, k[2]))] = f
    fallos = []
    tab = {(t['dia'], t['hora'].zfill(5), plano(t['titulo'])) for t in tabla}
    # LOS PANELES DE INDUSTRIA (6 oct) no están en el PDF: los trae
    # biff.co/eventos_Paneles.php. Se releen por su cuenta, del texto plano y con
    # otro corte —cada «OCTUBRE, <día> <n> - <hora>» hasta la siguiente—, y el
    # build los lleva por el título de la web, que el crudo guarda en `titulo_web`
    import html as _h
    web = _h.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '',
                      io.open(f'{D}/eventos_Paneles.html', encoding='utf-8', errors='replace').read(), flags=re.S)))
    web = re.sub(r'\s+', ' ', web)
    cortes = list(re.finditer(r'OCTUBRE, \w+ (\d{1,2}) - (\d{1,2}):(\d{2}) ([ap])\.m\.', web))
    paneles = set()
    for n, m in enumerate(cortes):
        tramo = web[m.end():cortes[n + 1].start() if n + 1 < len(cortes) else len(web)]
        t = re.search(r'\bPanel (.+?)(?= [A-ZÁÉÍÓÚ¿][a-záéíóú])', tramo)
        dia = f'2026-10-{int(m.group(1)):02d}'
        if dia < '2026-10-08':        # antes del festival: fuera, como en el crudo
            continue
        h = f'{int(m.group(2)) % 12 + (12 if m.group(4) == "p" else 0):02d}:{m.group(3)}'
        paneles.add((dia, h))
    web_de = {(f['dia'], f['hora'], plano(f['titulo'])): (f['dia'], f['hora']) for f in crudo if f.get('titulo_web')}
    en_build = {web_de[k] for k in pub if k in web_de}
    for k in paneles - en_build:
        fallos.append(f'panel en biff.co y NO en el build: {k}')
    for k in en_build - paneles:
        fallos.append(f'panel en el build y NO en biff.co: {k}')
    tab |= {k for k in pub if k in web_de and web_de[k] in paneles}
    for k in tab:
        if k not in pub:
            fallos.append(f'en la tabla y NO en el build: {k}')
    for k in pub:
        if k not in tab:
            fallos.append(f'en el build y NO en la tabla: {k}')
    for c in cin:
        k = (c[0], c[1], c[2])
        f = pub.get(k) or next((v for kk, v in pub.items() if kk[:2] == k[:2] and plano(v['title']) == c[2]), None)
        if not f:
            fallos.append(f'en la Cinemateca y NO en el build: {k}')
        elif plano(f.get('sala')) != plano(c[4]):
            fallos.append(f'{k}: sala {c[4]!r} en la Cinemateca, {f.get("sala")!r} en el build')
    en_cin = {(c[0], c[1], c[2]) for c in cin}
    for k, f in pub.items():
        if f['venue'].startswith('Cinemateca') and f.get('sala') not in (None, '', 'Calle Museo') \
                and (k[0], k[1], plano(f['title'])) not in en_cin and f.get('type') != 'event' \
                and (k[0], k[1], plano(f['title'])) not in CINEMATECA_NO_TRAE and 'muestra' not in k[2]:
            fallos.append(f'en la Cinemateca del build y NO en su agenda: {k}')
    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None and not g.get('_todo'):
            fallos.append(f'sede {v!r} sin pin y sin pendiente escrito')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')
    if fallos:
        sys.exit('✗ el build no coincide con las fuentes:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ las {len(tab)} funciones de la tabla por días están en el build y el build no publica '
          f'ninguna más · las {len(cin)} de la Cinemateca, con su sala · {len(build["venues"])} sedes '
          f'con pin verificado a mano')


if __name__ == '__main__':
    main()
