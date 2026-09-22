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


# QUIÉN MANDA CUANDO LAS DOS FUENTES DISCREPAN. La regla, y no se decide obra
# por obra: la FICHA DE LA WEB manda para los datos de la OBRA —año, director,
# duración—, porque es la ficha completa y la parrilla es un resumen que además
# trunca (imprime «Pablo Andrés Muñoz» donde la ficha dice «Pablo Andrés Muñoz
# Castrillón»). La PARRILLA manda para día, hora y sede, que es lo único que
# la web no publica.
#
# Las diferencias que quedan abajo están EXPLICADAS: dejan de ser un fallo
# porque se sabe por qué existen, no porque se hayan silenciado. Cualquier otra
# pone el verificador en rojo.
EXPLICADAS = {
    ('alma provinciana', 'duracion'):
        'LA PARRILLA GANA ACÁ, y lo dice la propia ficha del festival: «111 '
        'minutos en la ficha de Proimágenes y la Fundación Patrimonio Fílmico. '
        'Algunas versiones restauradas/catálogos consignan otras duraciones, '
        'debido a la velocidad de proyección de las copias». Es una película '
        'SILENTE de 1926: a 16 fotogramas por segundo dura 111 y a 19 dura 93. '
        'La parrilla anuncia la copia que se va a proyectar, y lo que el '
        'planificador necesita es cuánto ocupa la sala. Se publica 93.',
    ('cuando las aguas se juntan', 'anio'):
        'la ficha dice «Año: 2023» sin ambigüedad y la parrilla imprime 1923: '
        'errata del impreso en un dígito. Se publica 2023.',
    ('la marcha del hambre', 'duracion'):
        'LA PARRILLA GANA, y otra vez lo dice la propia ficha: «Duración: 92 '
        'min. según Proimágenes / 94 min. según OjoAgua». OjoAgua Cine es LA '
        'PRODUCTORA de la película, así que los 94 de la parrilla son la cifra '
        'de quien la hizo y los 92 los del registro. Se publica 94.',
    ('la creciente', 'director'):
        'la parrilla trunca el apellido; la ficha dice «Pablo Andrés Muñoz '
        'Castrillón». Manda la ficha.',
    ('cuando las montanas tiemblan', 'director'):
        'son los mismos dos nombres con distinto separador («,» contra «y»). '
        'Manda la ficha.',
}


def clave_titulo(s):
    """El título sin acentos, espacios ni puntuación. No se llama `norm`: ésa
    es de lib.py y hace otra cosa —deja los espacios—, y dos funciones con el
    mismo nombre y distinto comportamiento es exactamente lo que [lib-unica]
    existe para impedir."""
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
    # EL MISMO parser incluye sus retoques: si esta lectura se saltara uno,
    # la diferencia que saldría sería contra el camino, no contra la imagen.
    return P.propaga_episodio(fun)


def clave(f):
    return (f['dia'], f['hora'], clave_titulo(f['sede']), clave_titulo(f.get('titulo')))


def titulos(fs):
    """Todo título que la lectura produce, al nivel que sea."""
    out = set()
    for f in fs:
        out.add(clave_titulo(f.get('titulo')))
        for it in (f.get('cortos') or []) + (f.get('obras') or []):
            out.add(clave_titulo(it.get('titulo')))
    return out - {''}


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

    # D · LA EVIDENCIA CRUDA CONTRA LO PARSEADO, que es la única lectura de
    #     verdad independiente. A y B pasan por el MISMO parser: si el parser
    #     tira una película, las dos la tiran igual y coinciden — «las tres
    #     lecturas dicen lo mismo» mientras «Ubuntu: La métrica de los afectos»
    #     no existía en el festival. Lo vio Juan, no este archivo.
    #
    #     Acá se cuenta la evidencia que el OCR deja sin pasar por el parser:
    #     cada línea «País, año, NN min, género» es UNA obra proyectada, la
    #     imprima el festival sola en su casilla o debajo de otra. Si el parser
    #     produce menos obras que fichas hay en las láminas, se perdió algo.
    crudo = P.ocr(sorted(f'{P.LAMINAS}/{n}' for n in os.listdir(P.LAMINAS)
                         if n.endswith('.jpg')))
    fichas_ocr = 0
    for k, ls in crudo.items():
        if any(c['t'].strip() == 'TALLERES' for c in ls if c['y'] < 0.075):
            continue
        if not P.dia_de(ls):
            continue
        fichas_ocr += sum(1 for c in ls
                          if c['x'] >= P.COL_FICHA and P.RE_FICHA.match(c['t'].strip()))
    obras_parseadas = sum(
        1 for f in A
        for _ in (f.get('obras') or [None]) if f.get('obras') or f.get('anio'))
    print(f'D · fichas «País, año, min, género» en el OCR: {fichas_ocr} · '
          f'obras con ficha en lo parseado: {obras_parseadas}')
    if obras_parseadas < fichas_ocr:
        fallos.append(f'el OCR ve {fichas_ocr} fichas de obra en las láminas y el '
                      f'parser produce {obras_parseadas}: se perdieron '
                      f'{fichas_ocr - obras_parseadas}')

    # C · contra el catálogo de la web
    cat = json.load(open(f'{ST}/jardin-2026-catalogo.json', encoding='utf-8'))['obras']
    por_tit = {clave_titulo(o['titulo']): o for o in cat}
    cruzadas, choques, explicadas = 0, [], []
    for f in A:
        o = por_tit.get(clave_titulo(f.get('titulo')))
        if not o:
            continue
        cruzadas += 1
        k = re.sub(r'[^a-z ]', '', unicodedata.normalize('NFD', f['titulo'].lower())
                   .encode('ascii', 'ignore').decode()).strip()
        def anota(campo, texto):
            if (k, campo) in EXPLICADAS:
                explicadas.append(f'{texto} — {EXPLICADAS[(k, campo)][:96]}…')
            else:
                choques.append(texto)
        if f.get('duracion_min') and o.get('duracion_min') \
                and abs(f['duracion_min'] - o['duracion_min']) > 1:
            anota('duracion', f'«{f["titulo"][:26]}» dura {f["duracion_min"]} en la '
                              f'parrilla y {o["duracion_min"]} en la web')
        if f.get('director') and o.get('director') \
                and clave_titulo(f['director']) != clave_titulo(o['director']):
            anota('director', f'«{f["titulo"][:26]}»: dir. {f["director"][:22]} en la '
                              f'parrilla y {o["director"][:22]} en la web')
        if f.get('anio') and o.get('anio') and f['anio'] != o['anio']:
            anota('anio', f'«{f["titulo"][:26]}»: año {f["anio"]} en la parrilla '
                          f'y {o["anio"]} en la web')
    print(f'C · contra el catálogo web: {cruzadas} de {len(A)} funciones cruzan '
          f'con una de las {len(cat)} fichas')
    # …Y EN EL OTRO SENTIDO, que es el que faltaba: toda obra del catálogo
    # tiene que aparecer en alguna función —suelta, dentro de un programa de
    # Caleidoscopio o dentro de una casilla de dos películas— o estar declarada
    # en el crudo como sin función. Sin esta mitad, «Ubuntu» se cayó del
    # festival y el verificador imprimió un ✓.
    # El denominador se compara contra lo que SE PUBLICA, no contra la parrilla
    # cruda: el crudo le quita el prefijo a «Cine foro: Volver» —un cine foro es
    # una proyección— y con la parrilla a secas «Volver» salía como perdida.
    vistos, declaradas = titulos(A), set()
    _cr = f'{ST}/jardin-2026-crudo.json'
    if os.path.exists(_cr):
        _c = json.load(open(_cr, encoding='utf-8'))
        vistos |= titulos(_c['funciones'])
        vistos |= {clave_titulo(it.get('titulo'))
                   for f in _c['funciones'] for it in (f.get('film_list') or [])}
        declaradas = {clave_titulo(t) for v in (_c.get('_sin_funcion') or {}).values()
                      for t in v['obras']}
    perdidas = [o['titulo'] for o in cat
                if clave_titulo(o['titulo']) not in vistos | declaradas]
    if perdidas:
        fallos.append('obra(s) del catálogo que no aparecen en ninguna función ni '
                      'están declaradas: ' + ', '.join(f'«{t}»' for t in perdidas[:6]))
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

    for x in sorted(set(explicadas)):
        print(f'   · diferencia EXPLICADA: {x}')
    fallos = sorted(set(fallos))      # una obra que se proyecta 3 veces choca 3 veces
    if fallos:
        for x in fallos:
            print(f'   ✗ {x}')
        print(f'\n✗ {len(fallos)} diferencia(s) sin explicar')
        sys.exit(1)
    print('\n✓ las tres lecturas dicen lo mismo')


if __name__ == '__main__':
    main()
