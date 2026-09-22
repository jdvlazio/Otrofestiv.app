#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-verificar-parrilla.py — la parrilla, leída TRES veces.

POR QUÉ (Juan, 21 sep 2026: «¿hiciste doble o triple verificación?»). La
parrilla del festival existe SOLO como imágenes: 14 láminas de un carrusel de
Instagram. Una sola lectura de una imagen no se puede auditar —si el OCR se
come una línea, nadie se entera— y ya pasó dos veces hoy: un taller se quedó
con el día, el lugar y la hora del taller siguiente, y dos rótulos («ESTRENO»,
«ACTO DE CLAUSURA») se publicaron como si fueran el título de la obra. Las dos
las cacé mirando la lámina con los ojos, que no es un método.

LAS TRES LECTURAS, y por qué son independientes de verdad:

  A · OCR de Vision a resolución nativa. Es la que usa el parser.

  B · OCR de Vision sobre la lámina al DOBLE, con el mismo parser. Mismo motor
      pero otra ENTRADA: el reconocedor decide distinto sobre texto pequeño, y
      la letra chica de esta parrilla —los «Ponentes:», las notas de
      conversatorio— es justo donde falla. Si A y B coinciden en las 58
      funciones, la lectura no depende del tamaño; si difieren, la diferencia
      se nombra.

  C · EL CATÁLOGO DE LA WEB, que es otra superficie del mismo festival y la
      única independiente de la imagen: 37 fichas con director, año y duración
      publicadas en festicinejardin.com. Toda obra de la parrilla que esté en
      el catálogo tiene que coincidir. Aquí es donde se ven los años imposibles
      que la lámina imprime.

Falla con código ≠ 0 si queda una diferencia SIN EXPLICAR. Un ✓ que se imprime
al lado de un aviso no es un ✓ —la lección del verificador de Villa del Cine—.
"""
import json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'parr', f'{REPO}/pipeline/jardin-2026-parrilla.py')
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

ST = f'{REPO}/festivals/staging'
DOBLE = f'{REPO}/fuentes/ig/{P.POST}-x2'


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '', s)


def al_doble():
    """Las mismas láminas, al 200%. Se cachean: el OCR es lo caro."""
    from PIL import Image
    os.makedirs(DOBLE, exist_ok=True)
    out = []
    for n in sorted(os.listdir(P.LAMINAS)):
        if not n.endswith('.jpg'):
            continue
        dst = f'{DOBLE}/{n}'
        if not os.path.exists(dst):
            im = Image.open(f'{P.LAMINAS}/{n}')
            im.resize((im.width * 2, im.height * 2), Image.LANCZOS).save(dst, quality=95)
        out.append(dst)
    return out


def lee(rutas):
    """Corre el MISMO parser sobre un juego de láminas."""
    crudo = P.ocr(rutas)
    fun = []
    for ruta in rutas:
        k = os.path.basename(ruta)
        ls = crudo.get(k) or crudo.get(ruta) or []
        if any(c['t'].strip() == 'TALLERES' for c in ls if c['y'] < 0.075):
            continue
        dia = P.dia_de(ls)
        if not dia:
            continue
        hay = any(c['x'] >= P.COL_FICHA and c['y'] > 0.075 for c in ls)
        fs = P.filas(ls, dia)[0] if hay else P.una_columna(ls, dia)
        for f in fs:
            f.pop('_y', None)
            f.update(P.ficha(f))
            f.pop('ficha', None)
            fun.append(f)
    return fun


def clave(f):
    return (f['dia'], f['hora'], norm(f['sede']), norm(f.get('titulo')))


def main():
    A = json.load(open(f'{ST}/jardin-2026-parrilla.json', encoding='utf-8'))['funciones']
    print(f'A · OCR nativo: {len(A)} funciones')
    B = lee(al_doble())
    print(f'B · OCR al doble: {len(B)} funciones')

    ka, kb = {clave(f) for f in A}, {clave(f) for f in B}
    solo_a, solo_b = sorted(ka - kb), sorted(kb - ka)
    fallos = []
    if solo_a or solo_b:
        for k in solo_a[:8]:
            fallos.append(f'solo en la lectura NATIVA: {k[0]} {k[1]} {k[2][:20]} «{k[3][:26]}»')
        for k in solo_b[:8]:
            fallos.append(f'solo en la lectura AL DOBLE: {k[0]} {k[1]} {k[2][:20]} «{k[3][:26]}»')
    else:
        print(f'   ✓ las dos lecturas coinciden en las {len(ka)} funciones')

    # C · contra el catálogo de la web
    cat = json.load(open(f'{ST}/jardin-2026-catalogo.json', encoding='utf-8'))['obras']
    por_tit = {norm(o['titulo']): o for o in cat}
    cruzadas, choques = 0, []
    for f in A:
        o = por_tit.get(norm(f.get('titulo')))
        if not o:
            continue
        cruzadas += 1
        if f.get('duracion_min') and o.get('duracion_min') \
                and abs(f['duracion_min'] - o['duracion_min']) > 1:
            choques.append(f'«{f["titulo"][:26]}» dura {f["duracion_min"]} en la '
                           f'parrilla y {o["duracion_min"]} en la web')
        if f.get('director') and o.get('director') \
                and norm(f['director']) != norm(o['director']):
            choques.append(f'«{f["titulo"][:26]}»: dir. {f["director"][:22]} en la '
                           f'parrilla y {o["director"][:22]} en la web')
        if f.get('anio') and o.get('anio') and f['anio'] != o['anio']:
            choques.append(f'«{f["titulo"][:26]}»: año {f["anio"]} en la parrilla '
                           f'y {o["anio"]} en la web')
    print(f'C · contra el catálogo web: {cruzadas} de {len(A)} funciones cruzan '
          f'con una de las {len(cat)} fichas')
    fallos += choques

    # EL AÑO LO ARBITRA LA WEB, NO MI CORAZONADA. La primera versión marcaba
    # «año fuera de rango» cualquier película anterior a 2000 que no pareciera
    # de Cine memoria, y cantó dos falsas: «Romero» (1989) y «Cuando las
    # montañas tiemblan» (1983) son viejas de verdad y el festival las
    # programa a propósito. Un año solo es sospechoso si OTRA fuente lo
    # desmiente, y eso ya lo mira el cruce C.
    #
    # LA HORA SE JUZGA POR LA SECUENCIA, no por el reloj. Marqué «hora
    # improbable» las 23:00 del sábado y la lámina las imprime: el sábado va
    # 9:30 → 10:00 → 11:00 → 13:00 → 15:00 → 16:00 → 16:30 → 19:00 → 22:00 →
    # 23:00, estrictamente creciente. Lo que SÍ delata un día o una hora mal
    # leídos es que la parrilla retroceda: está maquetada en orden.
    orden = []
    for lam in sorted({f['_lamina'] for f in A if f.get('_lamina')}):
        hs = [f['hora'] for f in A if f.get('_lamina') == lam]
        if hs != sorted(hs):
            orden.append(f'{lam}: las horas no van en orden ({" ".join(hs)})')
    fallos += orden

    fallos = sorted(set(fallos))      # una obra que se proyecta 3 veces choca 3 veces
    if fallos:
        for x in fallos:
            print(f'   ✗ {x}')
        print(f'\n✗ {len(fallos)} diferencia(s) sin explicar')
        sys.exit(1)
    print('\n✓ las tres lecturas dicen lo mismo')


if __name__ == '__main__':
    main()
