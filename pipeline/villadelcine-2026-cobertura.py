#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-cobertura.py — las 67 páginas del PDF contra lo que extrajimos.

POR QUÉ NO BASTA EL VERIFICADOR (19 sep 2026). `villadelcine-2026-verificar.py`
revisa la RETÍCULA: que las celdas estén, no se monten y duren un múltiplo de
15. Pero la retícula son 10 de 67 páginas. Las 39 de ficha, las 10 de ruta
académica y las 8 de portada y créditos no las revisaba nadie, y una obra que
no extrajimos no deja hueco: deja una ficha vacía que nadie echa de menos.

QUÉ HACE: COBERTURA INVERSA, PÁGINA POR PÁGINA. Recorre las 67 y, por cada
línea de texto, exige que esté en una de estas tres cajas:

  · EXTRAÍDA — aparece en algún registro de `villadelcine-2026-parrilla.json`
    (un bloque de la retícula, el texto de una ficha o el de la academia).
  · ADORNO — es cromo de la plantilla: el logotipo, el lema, los créditos, los
    patrocinadores. Declarado en ADORNO, con su razón.
  · SIN CLASIFICAR — y entonces el paso FALLA, porque es contenido que el
    festival publicó y nosotros no leímos.

Verificar lo transcrito no verifica lo descartado, y contar en total es flojo:
una página que se repite tapa a la que falta. Por eso el recuento es POR
PÁGINA y el informe dice cuál.

    python3 pipeline/villadelcine-2026-cobertura.py          # informe + fallo
    python3 pipeline/villadelcine-2026-cobertura.py --todo   # además, lo cubierto
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAR = f'{REPO}/festivals/staging/villadelcine-2026-parrilla.json'
WEB = f'{REPO}/festivals/staging/villadelcine-2026-obras-web.json'
PAGINAS = 67

# CROMO DE LA PLANTILLA. Está en casi todas las páginas y no es programación.
# Cada patrón dice qué es; no se amplía para callar un aviso sin mirarlo.
ADORNO = [
    (r'^12$|^FESTIVAL$|^VILLA$|^DEL CINE$', 'el logotipo, partido en líneas'),
    (r'^caminos$|^del$|^tiempo$|^del tiempo$', 'el lema de la edición'),
    (r'^Septiembre$|^\d{1,2}\s+(MIÉRCOLES|JUEVES|VIERNES|SÁBADO|MAÑANA|TARDE|NOCHE|TARDE/NOCHE)$',
     'la fecha de la cabecera de la retícula'),
    (r'^(MIÉRCOLES|JUEVES|VIERNES|SÁBADO)$|^(MAÑANA|TARDE|NOCHE|TARDE/NOCHE)$',
     'la franja del día'),
    (r'^Lugar$|^Hora$', 'los rótulos de los ejes de la tabla'),
    (r'^\d{1,2}:\d{2}\s*.?\.?m\.?$', 'las horas de la columna izquierda'),
    (r'^23 - 26 Septiembre 2026$', 'las fechas de la portada'),
    (r'^(Patrocinadores|Aliados Estratégicos|Aliados de la Villa|'
     r'Medios de Comunicación|Restaurantes|Hospedajes|MAPA VILLA DEL CINE|'
     r'NUESTRO CREW|CRÉDITOS)$', 'los títulos de las páginas de cierre'),
]
# Las páginas que son enteramente cromo: portada, patrocinadores, créditos,
# mapa y contraportada. Se declaran por número, y el paso comprueba que de
# verdad no traigan nada que parezca programación.
PAGS_SIN_PROGRAMA = {1, 61, 62, 63, 64, 65, 66, 67}
# En esas páginas todo es texto libre (nombres del equipo, marcas). Lo que se
# vigila es que no aparezca una HORA o una FECHA, que sería programación
# escondida entre los créditos.
# LA MISMA OBRA CON DOS TÍTULOS. La web la nombra en inglés y el PDF en
# español (o al revés), así que el cruce las da por ausentes. Cada par está
# comprobado en el texto del PDF; lo que queda fuera de esta tabla es una obra
# que el programa de verdad no menciona, y eso se le pregunta al festival.
ALIAS = {
    'A Burning Turret': 'TORMENTA EN LLAMAS — mismo director (Humberto Flores), mismo '
                        'país (México), misma duración (22:12 / 0:22:00) y la misma '
                        'sinopsis traducida. Tres campos, no una corazonada',
    'Enemy in the Mirror': 'ENEMIGO EN EL ESPEJO',
    'With the Hand Up': 'CON LA MANO ARRIBA',
    'SUN COFFEE': 'SUN COFFE (así, con una efe, en el PDF)',
    'LENS - AI Short Film': 'LENS',
    'Sabor a mi (Acústico/ BoleroJazz)  Tatiana Jáuregui & Husil':
        'SABOR A MI (ACÚSTICO / BOLERO JAZZ) — la web le añade los intérpretes',
    'Cine Concierto Villa del Cine 2021':
        'es la página de la edición de 2021, no una obra de esta',
}

RE_PROGRAMA = re.compile(r'\d{1,2}:\d{2}\s*[ap]\.?\s*m|'
                         r'\b(2[3-6])\s+de\s+septiembre\b', re.I)


def es_adorno(t):
    for pat, por_que in ADORNO:
        if re.match(pat, t.strip()):
            return por_que
    return ''


def main():
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        'vp', f'{REPO}/pipeline/villadelcine-2026-programa-pdf.py')
    vp = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(vp)

    d = json.load(open(PAR, encoding='utf-8'))
    # todo lo que extrajimos, normalizado, por página de origen
    extraido = {}
    for b in d['bloques']:
        for t in b['lineas']:
            extraido.setdefault(norm(t), set()).add(b['pagina'])
        # el NOMBRE DE LA SEDE se extrae compuesto («Museo Casa Antonio Nariño
        # Salón principal 1er piso») a partir de tres líneas apiladas. Cada una
        # por separado también está extraída, aunque no aparezca así.
        for parte in b['sede'].split():
            extraido.setdefault(norm(parte), set()).add(b['pagina'])
        for n in range(1, 5):
            ps = b['sede'].split()
            for i in range(len(ps) - n + 1):
                extraido.setdefault(norm(' '.join(ps[i:i + n])), set()).add(b['pagina'])
    for f in d['fichas']:
        for t in f['texto'].split('\n') + [f['cabecera']]:
            extraido.setdefault(norm(t), set()).add(f['pagina'])
        # la cabecera de la ficha («NUEVAS MIRADAS TRÁNSITO») también se compone
        # de líneas sueltas que el logotipo parte: cada trozo está extraído.
        ps = f['cabecera'].split()
        for n in range(1, len(ps) + 1):
            for i in range(len(ps) - n + 1):
                extraido.setdefault(norm(' '.join(ps[i:i + n])), set()).add(f['pagina'])
    for a in d['academica']:
        for t in a['texto'].split('\n'):
            extraido.setdefault(norm(t), set()).add(a['pagina'])

    filas, sueltas_total = [], []
    for pag in range(1, PAGINAS + 1):
        ls = vp.lineas(pag, pag)
        n = cub = ado = 0
        sueltas = []
        for _, _, _, _, _, t in ls:
            if not t.strip():
                continue
            n += 1
            if norm(t) in extraido:
                cub += 1
            elif es_adorno(t):
                ado += 1
            elif pag in PAGS_SIN_PROGRAMA and not RE_PROGRAMA.search(t):
                ado += 1
            else:
                sueltas.append(t)
        filas.append((pag, n, cub, ado, len(sueltas)))
        for t in sueltas:
            sueltas_total.append(f'p{pag}: «{t[:60]}»')

    print(f'villadelcine-2026 · cobertura del PDF, {PAGINAS} páginas')
    print(f"{'pág':>4} {'líneas':>7} {'extraído':>9} {'adorno':>7} {'sin clasificar':>15}")
    for pag, n, cub, ado, s in filas:
        marca = '  ✗' if s else ''
        if s or '--todo' in sys.argv:
            print(f'{pag:>4} {n:>7} {cub:>9} {ado:>7} {s:>15}{marca}')
    tot = sum(f[1] for f in filas)
    print(f"{'TOT':>4} {tot:>7} {sum(f[2] for f in filas):>9} "
          f"{sum(f[3] for f in filas):>7} {sum(f[4] for f in filas):>15}")

    # el otro lado: las obras de la web que el PDF no nombra, y al revés
    if os.path.exists(WEB):
        web = json.load(open(WEB, encoding='utf-8'))['obras']
        # contra TODO el PDF, no solo las fichas: «ARENAS» no tiene página de
        # ficha pero sí está en la retícula del miércoles.
        texto_pdf = norm(' '.join(
            [f['texto'] + ' ' + f['cabecera'] for f in d['fichas']]
            + [a['texto'] for a in d['academica']]
            + [' '.join(b['lineas']) for b in d['bloques']]))
        # el título completo no sirve como llave: el PDF escribe «SABOR A MI
        # (ACÚSTICO / BOLERO JAZZ)» y la web «Sabor a mi (Acústico/ BoleroJazz)
        # Tatiana Jáuregui & Husil». Se cruza por las tres primeras palabras
        # con letra, que es lo que ninguna de las dos versiones cambia.
        # POR PALABRAS, NO POR CADENA. Quitar las palabras cortas del título y
        # buscarlo entero en el texto no funciona: «La presencia de blanco» se
        # convertía en «presencia blanco», que no está en «la presencia de
        # blanco». Se comprueba que TODAS las palabras largas del título estén
        # en el PDF, que es lo que sobrevive a que cada fuente lo escriba a su
        # manera.
        palabras_pdf = set(texto_pdf.split())

        def falta(t):
            ps = {w for w in norm(t).split() if len(w) > 3}
            return bool(ps) and not ps <= palabras_pdf

        faltan = [o['titulo'] for o in web
                  if falta(o['titulo']) and o['titulo'] not in ALIAS]
        print(f'\nobras de la web ({len(web)}) que el PDF no nombra: {len(faltan)} '
              f'(+{len(ALIAS)} que sí están, con otro título — ver ALIAS)')
        for t in faltan[:14]:
            print('   ·', t)
        if len(faltan) > 14:
            print(f'   … y {len(faltan) - 14} más')

    if sueltas_total:
        print(f'\n✗ {len(sueltas_total)} línea(s) SIN CLASIFICAR — son del festival y '
              f'no las leímos:')
        for s in sueltas_total[:30]:
            print('   ✗', s)
        if len(sueltas_total) > 30:
            print(f'   … y {len(sueltas_total) - 30} más')
        sys.exit(1)
    print('\n✓ las 67 páginas: cada línea, o extraída, o declarada adorno')


if __name__ == '__main__':
    main()
