# -*- coding: utf-8 -*-
"""Lee la parrilla oficial de Cinemancia 2026 desde el PDF del festival.

La parrilla es POSICIONAL: la FILA es la sede (rótulo a la izquierda, x~46) y
cada celda es una función — hora arriba, título debajo en el mismo x, duración
a la derecha en la misma línea de la hora. Extraer el texto plano aplasta las
columnas y mezcla funciones de sedes distintas; por eso se lee con coordenadas.
"""
import json, re, sys
import pypdf

HORA = re.compile(r'^(\d{1,2}):\s?(\d{2})\s*(?:([ap])\.?\s?m\.?)?\s*$', re.I)
# Dos celdas de la parrilla escriben la hora SIN a.m./p.m. («4:30», págs. 3 y 12).
# No se adivina: la parrilla corre cronológica de izquierda a derecha y las dos
# caen en x~413, la columna de media tarde. Además el festival no programa nada
# entre la 1 y las 9 de la mañana —lo más temprano son las 9:00 a.m., y esas SÍ
# llevan sufijo—. Se marcan con _hora_inferida para poder auditarlas.
DUR  = re.compile(r'^(\d{1,3})\s*[’\']$')
DIA  = re.compile(r'^(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)$', re.I)
X_SEDE = 100          # a la izquierda de esto vive el rótulo de sede
# Todo rótulo de sede TERMINA en su municipio. Es lo que distingue una sede de
# otra cosa escrita en el margen: el sábado 12 la parrilla ocupa la mitad de
# arriba y debajo empieza otra sección («Conversaciones»), cuyo encabezado caía
# en la misma columna y se leía como una sede más.
# Encabezados de las secciones de DETALLE que van debajo de la parrilla en
# algunas páginas. La parrilla termina donde empieza la primera de ellas: sin
# ese corte, el sábado 12 producía una función fantasma cuyo «título» era el
# rótulo de sede que la sección de detalle repite en su cuerpo.
SECCION = re.compile(r'^(Conversaciones|Debate|Encuentro|Seminario|Foro)\b', re.I)
MUNICIPIOS = re.compile(r'^(Medell[íi]n|Itag[üu][íi]|Envigado|Bello|Caldas|Copacabana|'
                        r'Sabaneta|La Estrella|Girardota|Barbosa)\.?$', re.I)
ANCHO_CELDA = 72      # ancho útil de una celda, medido en la página

def fragmentos(page):
    """Fragmentos POSICIONADOS. Algunas páginas emiten además un fragmento
    gigante con el texto entero de la página en x~0: no es un rótulo, es el
    volcado. Se cuela como «sede» y deja la página sin filas (pasó con sábado 5
    y domingo 6). Se descarta por lo que es: multilínea y desmesurado."""
    out = []
    page.extract_text(visitor_text=lambda t, cm, tm, fd, fs:
                      out.append((round(tm[4], 1), round(tm[5], 1), t))
                      if t.strip() else None)
    return [(x, y, t.strip()) for x, y, t in out
            if t.strip() and '\n' not in t.strip() and len(t.strip()) < 120]

def bloques_sede(items):
    """Rótulos de sede agrupados por cercanía vertical → [(y_top, texto)]."""
    lin = sorted([i for i in items if i[0] < X_SEDE and not DIA.match(i[2])
                  and not i[2].isdigit()], key=lambda i: -i[1])
    bloques, actual = [], []
    for x, y, t in lin:
        if actual and abs(actual[-1][1] - y) > 9:
            bloques.append(actual); actual = []
        actual.append((x, y, t))
    if actual: bloques.append(actual)
    bloques = [b for b in bloques if MUNICIPIOS.match(b[-1][2].strip())]
    return [(b[0][1], ' - '.join(t for _, _, t in b)) for b in bloques]

def bandas(sedes):
    """(techo, piso, nombre) por sede. Una función pertenece a la fila cuya
    banda la contiene, y su TÍTULO no puede bajar del piso: sin ese límite cada
    celda se tragaba la fila de la sede siguiente."""
    out = []
    for i, (ys, nom) in enumerate(sedes):
        techo = ys + 9 if i == 0 else (sedes[i-1][0] + ys) / 2
        piso  = (ys + sedes[i+1][0]) / 2 if i + 1 < len(sedes) else -1e9
        out.append((techo, piso, nom))
    return out


def sede_de(y, sedes):
    """La sede cuya banda contiene y. La banda arranca un poco ARRIBA del
    rótulo: la primera función de la fila se pinta por encima del texto."""
    for i, (ys, nom) in enumerate(sedes):
        techo = ys + 9 if i == 0 else (sedes[i-1][0] + ys) / 2
        piso  = (ys + sedes[i+1][0]) / 2 if i + 1 < len(sedes) else -1e9
        if piso < y <= techo: return nom
    return sedes[-1][1] if sedes else None

def parsea_pagina(page):
    items = fragmentos(page)
    if not items: return None, []
    corte = min([y for x, y, t in items if x < X_SEDE and SECCION.match(t)] or [-1e9])
    if corte > -1e9:
        items = [(x, y, t) for x, y, t in items if y > corte]
    sedes = bloques_sede(items)
    dia = next((t for x, y, t in items if DIA.match(t)), None)
    num = next((t for x, y, t in items if x < 25 and t.isdigit()), None)
    celdas = sorted([(x, y, t) for x, y, t in items if x >= X_SEDE], key=lambda i: (-i[1], i[0]))
    horas = [(x, y, t) for x, y, t in celdas if HORA.match(t)]
    # Dentro de una FILA el eje X es el tiempo: las funciones de una misma sede
    # se pintan de izquierda a derecha. Por eso el borde derecho de una celda no
    # es un ancho fijo —eso hacía que «Macho Dancer» se comiera la función
    # siguiente— sino el x de la celda que viene DESPUÉS en su misma fila.
    bs = bandas(sedes)
    def banda_de(y):
        for techo, piso, nom in bs:
            if piso < y <= techo: return (techo, piso, nom)
        return bs[-1] if bs else (1e9, -1e9, None)
    por_sede = {}
    for hx, hy, ht in horas:
        por_sede.setdefault(banda_de(hy)[2], []).append(hx)
    funciones = []
    for hx, hy, ht in horas:
        m = HORA.match(ht)
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or '').lower()
        inferida = not ap
        if inferida: ap = 'p' if 1 <= h <= 9 else 'a'
        if ap == 'p' and h != 12: h += 12
        if ap == 'a' and h == 12: h = 0
        _techo, _piso, sede = banda_de(hy)
        derechas = sorted(x for x in por_sede.get(sede, []) if x > hx + 6)
        x_fin = derechas[0] - 6 if derechas else 1e9
        cuerpo, dur = [], None
        for x2, y2, t2 in celdas:
            if not (hx - 6 <= x2 < x_fin): continue
            if DUR.match(t2) and abs(y2 - hy) < 4:
                if dur is None: dur = int(DUR.match(t2).group(1))
                continue
            if DUR.match(t2): continue          # duración de otra celda, no es título
            if _piso < y2 < hy - 2 and not HORA.match(t2): cuerpo.append((y2, x2, t2))
        titulo = ' '.join(t for y2, x2, t in sorted(cuerpo, key=lambda i: (-i[0], i[1])))
        funciones.append({'dia_num': num, 'dia_semana': dia, 'hora': f'{h:02d}:{mi:02d}',
                          'titulo_crudo': re.sub(r'\s+', ' ', titulo).strip(),
                          'duracion_min': dur, 'sede_crudo': sede,
                          **({'_hora_inferida': True} if inferida else {}),
                          '_x': hx, '_y': hy})
    return dia, funciones

def main(pdf):
    r = pypdf.PdfReader(pdf)
    todo = []
    for i, p in enumerate(r.pages):
        dia, fs = parsea_pagina(p)
        # Solo las páginas de PARRILLA. Las de detalle (Conversaciones, Debate,
        # Encuentro) describen una actividad en prosa y no tienen filas de sede:
        # leerlas como rejilla producía «sedes» que eran un trozo de párrafo.
        # Su texto sirve para las descripciones, no para el horario.
        if not dia:
            continue
        for f in fs: f['_pagina'] = i + 1
        todo += fs
    return todo

if __name__ == '__main__':
    fs = main(sys.argv[1] if len(sys.argv) > 1 else 'cinemancia-programacion.pdf')
    json.dump(fs, open('cinemancia-parrilla.json', 'w'), ensure_ascii=False, indent=1)
    print('funciones leídas:', len(fs))
