# -*- coding: utf-8 -*-
"""cobertura.py — ¿qué dice el PDF que nuestro modelo NO recoge?

LA COMPROBACIÓN QUE FALTABA. verifica.py comprueba una dirección: que todo lo
transcrito esté en la página que declara. Nada comprobaba la contraria, y por
ahí se perdió un dato entero: cada página de ficha lleva estampado el DÍA de su
proyección («16 SEPT.»), el extractor lo descartaba por decorativo, y así
concluimos que el Museo Nacional y la Universidad Nacional no tenían
programación. Le escribimos al festival preguntando por unos horarios que
estaban impresos en su propio PDF, y el director tuvo que señalárnoslo.

Una lectura doble que lee DOS VECES LO MISMO no es doble: es la misma lectura
repetida. Lo que hacía falta era mirar el documento entero y preguntar, línea a
línea, «¿de esto quién se hizo cargo?». Lo que no lo explique nadie sale aquí.

Tres preguntas, de la más floja a la más exigente:

  1. ¿Queda alguna línea con FORMA DE DATO —un sello de fecha, una hora, una
     duración— que nadie explique? Global sobre el documento entero.
  2. ¿Cada hora impresa en una parrilla está explicada por algo que el modelo
     coloca EN ESA PÁGINA? La global no basta: borrando del modelo la función de
     las 19:30 del día 15, seguía en verde porque «7:30 pm» sale en otras
     páginas. Una hora que se repite tapa a la que falta.
  3. Lo mismo con los días: una parrilla que anuncia «16 DE SEPTIEMBRE» y un
     modelo que en esa página no programa nada del 16.
  4. ¿Hay alguna página con fecha Y hora impresas que el modelo no toque? Las
     preguntas 2 y 3 solo miran páginas que el modelo ya reconoce, así que una
     página que desaparece entera se les escapa — y es el error original: dimos
     por no programados el Museo Nacional y la Universidad Nacional teniendo su
     fecha y su hora impresas.

LO QUE NO CUBRE, dicho aquí para que nadie lo dé por hecho: si de una parrilla se
cae UNA obra pero su franja horaria sigue en el modelo, la hora y el día se
siguen explicando y las tres preguntas dan verde. El título perdido aparece como
huérfana sin forma de dato, entre las ~900 líneas de sinopsis y biografías, que
es donde no se ve. Cerrar ese hueco pedía comprobar los títulos por página, y
medido daba 47 líneas de ruido —nombres de panelistas, títulos partidos en dos
renglones— que es como un aviso deja de leerse. Para esa dirección está
verifica.py, que comprueba cada obra transcrita contra su página.

Uso:
    python3 pipeline/qaff_pdf/cobertura.py            # solo el resumen
    python3 pipeline/qaff_pdf/cobertura.py --todo     # cada línea huérfana
"""
import os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limpia import paginas, limpia                                    # noqa: E402
import programa as pr                                                 # noqa: E402


def n(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())


# Lo que el PDF repite en cada página y no aporta dato: cabeceras, lomo,
# patrocinadores, mapa de orientación. Se declara AQUÍ, a la vista, en vez de
# filtrarse calladamente dentro de un extractor.
MUEBLE = [
    'programa qaff', 'quibdo africa film festival', 'edicion', 'septiembre 2026',
    'hora', 'fecha', 'sede', 'apertura', 'donde', 'programa', 'imperdibles',
    'networking', 'exposicion', 'performance artistica e musical', 'aliados',
    'un proyecto', 'socios', 'entrada', 'libre', 'moderadora', 'moderador',
    'te esperamos', 'nos vemos', 'cra', 'calle', 'carrera', 'bogota', 'sala',
    'auditorio', 'edificio', 'facultad', 'estudio', 'biografia',
]
# etiquetas de ficha: su VALOR ya viaja en el modelo
ETIQUETA = re.compile(r'^(Duraci|Tipo de Proyecto|Idioma|Pa[íi]s|A[ñn]o|Distribuci|'
                      r'Fecha de Finalizaci|Directora?e?s?|Guionista|Productor|Director de|'
                      r'Editor|De\s)', re.I)
# Una línea CON forma de dato es la que ES un dato, no la que lo menciona: un
# sello de fecha, una hora suelta, una duración. Un año dentro de una biografía
# («ganó el premio en 2012») no lo es, y tratarlo como tal ahogaría la señal —
# que es exactamente cómo un aviso deja de leerse.
DATO = re.compile(r'^\s*\d{1,2}\s*SEPT\.?\s*$'          # 16 SEPT.
                  r'|^\s*\d{1,2}:\d{2}\s*[-–]?\s*(\d{1,2}:\d{2})?\s*[APap]?\.?[Mm]?\.?\s*$'
                  r"|^\s*\d{1,3}\s*['’]\s*\d{0,2}\s*$")   # 19'54

# El PRELANZAMIENTO (5 SEP, Museo Nacional) queda fuera del festival por decisión
# de Juan, así que sus páginas no tienen que estar explicadas por el modelo.
FUERA = {'7', '8', '9', '10', '11', '12'}


def _hhmm(h):
    """'19:30' → '730', que es como queda tras n() la forma que imprime el PDF."""
    H, M = map(int, h.split(':'))
    return f'{H % 12 or 12}{M:02d}'


def _mas(h, mins):
    H, M = map(int, h.split(':'))
    t = H * 60 + M + mins
    return f'{t // 60 % 24:02d}:{t % 60:02d}'


def _formas(h):
    """Las formas en que una hora aparece IMPRESA: sola («7:30») y con meridiano
    («7:30 pm»). Las dos van, porque el PDF usa ambas y a veces con el meridiano
    equivocado —«10:00 - 12:00 AM» para una franja de mediodía—. Se generan am y
    pm sin decidir cuál es: aquí no se juzga la hora, se reconoce el texto."""
    b = _hhmm(h)
    return {b, b + 'am', b + 'pm'}


def _ventana(ini, fin):
    """La franja impresa como UNA línea: «3:00 - 5:00 pm». Que esto faltara es
    por lo que 40 de las 46 huérfanas eran horarios que el modelo sí tenía: se
    conocían las horas sueltas y no la línea que las junta."""
    b = _hhmm(ini) + _hhmm(fin)
    return {b, b + 'am', b + 'pm'}


def conocido():
    """Todo lo que el modelo SÍ explica: obras, sedes, salas, personas — y
    también los DÍAS, las HORAS y las FRANJAS, en las formas en que el PDF las
    imprime. Un comprobador que grita por todo no se lee, y uno que calla lo que
    no entiende es peor: por eso cada forma que se añade aquí se comprueba antes
    contra el modelo, una por una."""
    k = set()
    horas, dias = set(), set()
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        horas |= _formas(hora); dias.add(int(dia))
    for t, sede, sala, dia, ini, fin, tit, quien, pag in pr.ACTIVIDADES:
        horas |= _formas(ini); dias.add(int(dia))
        if fin:
            horas |= _formas(fin) | _ventana(ini, fin)
    for sede, dia, hora in pr.APERTURAS:
        horas |= _formas(hora); dias.add(int(dia))
    for (sede, dia, hora), (mins, pag) in pr.VENTANAS.items():
        horas |= _formas(hora) | _ventana(hora, _mas(hora, mins))
    k |= {n(x) for x in horas}
    k |= {n(f'{d} SEPT') for d in dias}
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        k |= {n(o) for o in obras}; k.add(n(sede)); k.add(n(sala or ''))
    for t, sede, sala, dia, ini, fin, tit, quien, pag in pr.ACTIVIDADES:
        k.add(n(tit)); k |= {n(x) for x in re.split(r'[·,]', quien)}
        for w in re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ'’-]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñ'’-]+)+", quien):
            k.add(n(w))
    for (s, d, h), (nom, sin) in pr.BLOQUES.items():
        k.add(n(nom)); k |= {n(x) for x in sin.split('.')}
    return {x for x in k if x}


# Una hora impresa en una parrilla se comprueba contra lo que el modelo sitúa EN
# ESA PÁGINA, no contra todo el modelo. La diferencia no es teórica: borrando del
# modelo la función de las 19:30 del día 15, la comprobación global seguía en
# verde porque «7:30 pm» aparece en otras páginas. Una hora que se repite tapa a
# la que falta, y lo que se pierde en un onboarding es justo eso: una función de
# un día, no un horario que no existe en ningún sitio.
HORA_SOLA = re.compile(r'^\s*\d{1,2}:\d{2}\s*[-–]?\s*(\d{1,2}:\d{2})?\s*[APap]?\.?[Mm]?\.?\s*$')


def por_pagina():
    """{página de parrilla → formas horarias que el modelo sitúa en ella}."""
    d = {}
    def add(pag, formas):
        d.setdefault(str(pag), set()).update(formas)
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        add(pag, _formas(hora))
    for (sede, dia, hora), (mins, pag) in pr.VENTANAS.items():
        add(pag, _formas(hora) | _ventana(hora, _mas(hora, mins)))
    for t, sede, sala, dia, ini, fin, tit, quien, pag in pr.ACTIVIDADES:
        add(pag, _formas(ini) | (_formas(fin) | _ventana(ini, fin) if fin else set()))
    return d


def horas_fuera_de_sitio():
    """Horas impresas en una parrilla que el modelo no coloca en esa página."""
    mod = por_pagina()
    # La apertura de sala es la misma todos los días y se imprime en cada página
    # de la sede; no se le puede pedir página propia.
    aper = {n(x) for s, di, h in pr.APERTURAS for x in _formas(h)}
    fuera = {}
    for pag, crudo in paginas().items():
        if pag in FUERA or str(pag) not in mod:
            continue
        conocidas = {n(x) for x in mod[str(pag)]} | aper
        for l in limpia(crudo):
            if HORA_SOLA.match(l) and n(l) not in conocidas:
                fuera.setdefault(pag, []).append(l)
    return fuera


SELLO = re.compile(r'^\s*\d{1,2}\s*SEPT\.?\s*$', re.I)


def paginas_mudas():
    """Páginas que llevan sello de fecha Y hora, y que el modelo no toca.

    El hueco que dejaban las otras dos preguntas: solo miran páginas que el
    modelo ya reconoce como parrilla, así que una página que desaparece ENTERA
    del modelo deja de ser mirada por nadie. Y ese es, exactamente, el error
    original: dimos por hecho que el Museo Nacional y la Universidad Nacional no
    tenían programación, cuando su fecha y su hora estaban impresas en sus
    páginas. Una página con fecha y hora es programación hasta que se demuestre
    lo contrario."""
    enmod = set()
    for f in pr.FUNCIONES:
        enmod.add(str(f[-1]))
    for k, (mins, pag) in pr.VENTANAS.items():
        enmod.add(str(pag))
    for a in pr.ACTIVIDADES:
        enmod.add(str(a[-1]))
    mudas = {}
    for pag, crudo in paginas().items():
        if pag in FUERA or str(pag) in enmod:
            continue
        ls = limpia(crudo)
        if any(SELLO.match(l) for l in ls) and any(re.match(r'^\s*\d{1,2}:\d{2}', l) for l in ls):
            mudas[pag] = [l for l in ls if SELLO.match(l) or re.match(r'^\s*\d{1,2}:\d{2}', l)][:4]
    return mudas


DIA_LARGO = re.compile(r'^\s*(\d{1,2})\s+DE\s+SEPTIEMBRE\s*$', re.I)


def dias_fuera_de_sitio():
    """Días impresos en una parrilla que el modelo no coloca en esa página.

    Es la misma pregunta que la de las horas, sobre el otro eje. Una parrilla que
    anuncia «16 DE SEPTIEMBRE» y un modelo que en esa página no pone nada del 16
    es un día de programación perdido — que es exactamente el tamaño del error
    que nos hizo escribirle al festival preguntando por horarios impresos en su
    propio PDF."""
    dias = {}
    def add(pag, dia):
        dias.setdefault(str(pag), set()).add(int(dia))
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        add(pag, dia)
    for (sede, dia, hora), (mins, pag) in pr.VENTANAS.items():
        add(pag, dia)
    for t, sede, sala, dia, ini, fin, tit, quien, pag in pr.ACTIVIDADES:
        add(pag, dia)
    # El campo FECHA de la cabecera NO es un encabezado de bloque: nombra el
    # rango de la página, y a veces solo su primer día (p45 dice «15» y programa
    # el 15 y el 16). Además el festival lo tiene MAL en la p51: dice «15» y sus
    # dos bloques son el 17 y el 18. Es un error de su documento, no del modelo,
    # así que se informa aparte en vez de bloquear — pero se informa, porque un
    # día equivocado en la cabecera es justo lo que confunde a quien transcribe.
    fuera, cabeceras = {}, {}
    for pag, crudo in paginas().items():
        if pag in FUERA or str(pag) not in dias:
            continue
        ls = limpia(crudo)
        for i, l in enumerate(ls):
            m = DIA_LARGO.match(l)
            if not m or int(m.group(1)) in dias[str(pag)]:
                continue
            es_campo = i and ls[i - 1].strip().upper().startswith('FECHA')
            (cabeceras if es_campo else fuera).setdefault(pag, []).append(l)
    if cabeceras:
        for pag in sorted(cabeceras, key=int):
            print(f'   · p{pag}: la cabecera FECHA dice {cabeceras[pag]} y la página '
                  f'programa {sorted(dias[str(pag)])} — error del PDF del festival')
    return fuera


def huerfanas():
    K = conocido()
    fuera = {}
    for pag, crudo in paginas().items():
        if pag in FUERA:
            continue
        for l in limpia(crudo):
            t = n(l)
            if not t or len(t) < 3:
                continue
            if t in K or any(t in x or x in t for x in K if len(x) > 6):
                continue
            if ETIQUETA.match(l) or any(m in t for m in (n(x) for x in MUEBLE)):
                continue
            # prosa: sinopsis y biografías, que el modelo guarda por obra
            if len(l.split()) > 9:
                continue
            fuera.setdefault(pag, []).append(l)
    return fuera


if __name__ == '__main__':
    fuera = huerfanas()
    desubicadas = horas_fuera_de_sitio()
    dias_mal = dias_fuera_de_sitio()
    mudas = paginas_mudas()
    con_dato = {p: [l for l in ls if DATO.search(l)] for p, ls in fuera.items()}
    con_dato = {p: ls for p, ls in con_dato.items() if ls}
    tot = sum(len(v) for v in fuera.values())
    ndato = sum(len(v) for v in con_dato.values())
    print(f'líneas del PDF que nadie explica: {tot} · de ellas con FORMA DE DATO '
          f'(fecha, hora o duración): {ndato}')
    if con_dato:
        print('\n⚠ estas llevan un dato dentro y no están en el modelo:')
        for p in sorted(con_dato, key=int):
            for l in con_dato[p]:
                print(f'   p{p:>3}  {l[:70]}')
    if desubicadas:
        print('\n⚠ horas impresas que el modelo NO coloca en esa página:')
        for p in sorted(desubicadas, key=int):
            for l in desubicadas[p]:
                print(f'   p{p:>3}  {l[:70]}')
    else:
        print(f'· las horas de las {len(por_pagina())} páginas de parrilla están '
              f'explicadas por el modelo EN SU PROPIA PÁGINA')
    if dias_mal:
        print('\n⚠ días anunciados en una parrilla que el modelo no programa ahí:')
        for p in sorted(dias_mal, key=int):
            for l in dias_mal[p]:
                print(f'   p{p:>3}  {l[:70]}')
    else:
        print('· cada día anunciado en una parrilla tiene programación del modelo '
              'en esa misma página')
    if mudas:
        print('\n⚠ páginas con fecha y hora impresas que el modelo no toca — '
              'programación entera sin recoger:')
        for p in sorted(mudas, key=int):
            print(f'   p{p:>3}  {" · ".join(mudas[p])}')
    else:
        print('· ninguna página con fecha y hora impresas se quedó fuera del modelo')
    if '--todo' in sys.argv:
        print('\nel resto de huérfanas:')
        for p in sorted(fuera, key=int):
            for l in fuera[p]:
                if not DATO.search(l):
                    print(f'   p{p:>3}  {l[:70]}')
    sys.exit(1 if (con_dato or desubicadas or dias_mal or mudas) else 0)
