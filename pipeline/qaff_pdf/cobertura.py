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


def _h12(h):
    """'19:30' → las formas en que el programa la imprime."""
    H, M = map(int, h.split(':'))
    return {f'{H % 12 or 12}:{M:02d}'}


def conocido():
    """Todo lo que el modelo SÍ explica: obras, sedes, salas, personas — y
    también las HORAS y los DÍAS, que la primera versión no miraba y por eso
    marcaba como huérfana cada hora impresa del programa. Un comprobador que
    grita por todo no se lee."""
    k = set()
    horas, dias = set(), set()
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        horas |= _h12(hora); dias.add(int(dia))
    for t, sede, sala, dia, ini, fin, tit, quien, pag in pr.ACTIVIDADES:
        horas |= _h12(ini); dias.add(int(dia))
        if fin: horas |= _h12(fin)
    for sede, dia, hora in pr.APERTURAS:
        horas |= _h12(hora); dias.add(int(dia))
    # la ventana impresa de cada franja: «10:00 - 1:00 pm»
    for (sede, dia, hora), (mins, pag) in pr.VENTANAS.items():
        horas |= _h12(hora)
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
    if '--todo' in sys.argv:
        print('\nel resto de huérfanas:')
        for p in sorted(fuera, key=int):
            for l in fuera[p]:
                if not DATO.search(l):
                    print(f'   p{p:>3}  {l[:70]}')
    sys.exit(1 if con_dato else 0)
