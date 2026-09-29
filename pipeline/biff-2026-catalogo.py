#!/usr/bin/env python3
"""biff-2026-catalogo.py — las fichas de películas del PDF oficial del BIFF 12 → catálogo.

LA FUENTE es el PDF de programación que el festival cuelga en su web
(biff.co/documentos/Programacion_BIFF_12_DIGITAL.pdf, 26 sep 2026, InDesign con
texto). Las fichas van en las páginas 9–25 del PDF —el índice impreso numera
distinto: su «6 Películas» es la página 8 del archivo—. Cada ficha trae:

    TÍTULO                                     (sección, a la derecha)
    2026 | Colombia, Canadá | Drama | 102 min. | Español, Emberá
    Dirección: Juan Andrés ARANGO
    sinopsis…
    Dom. 11 - 19:30 | Cinemateca - Sala Capital      ← a la IZQUIERDA
    Mar. 13 - 17:00 | Av. Chile - Sala 4

LA DIAGRAMACIÓN VA A DOS COLUMNAS y ningún orden de lectura sirve: con
`-layout` las funciones quedan en la misma línea que la sinopsis, y sin él el
título a veces sale DESPUÉS de sus datos. Se lee con COORDENADAS
(`pdftotext -bbox-layout`): la columna de la ficha empieza en x≈141, la de las
funciones en x≈31, y cada función pertenece a la ficha cuyo título está
inmediatamente ENCIMA en la misma página.

Las funciones de las fichas son la CUARTA lectura de la parrilla: la tabla
«Programación por días», la grilla «por salas» y la agenda de la Cinemateca son
las otras tres. Acá solo se anotan; el cruce es del crudo.
"""
import html
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

PDF = f'{REPO}/fuentes/biff-2026/Programacion_BIFF_12_DIGITAL.pdf'
DESTINO = f'{REPO}/festivals/staging/biff-2026-catalogo.json'
PAGINAS = (9, 27)
# Dos páginas con su propia sección y sin rótulo de ficha: los cine conciertos
# (dos películas silentes con música en vivo) y la muestra de cortometrajes BIFF
# BANG, que es UN PROGRAMA de 8 cortos proyectado 7 veces (una por día, en sedes
# distintas). En esa página las funciones son del PROGRAMA, no del corto que les
# quede encima.
SECCION_DE_PAGINA = {26: 'Cine Conciertos', 27: 'Muestra de cortometrajes BIFF Bang'}
PAGINA_PROGRAMA = 27
SECCIONES = ['Película de inauguración', 'Colombia viva', 'Espíritu joven', 'Masters',
             'Fantasmas del pasado', 'Clases de lucha', 'Relatos mutantes',
             'Retrospectiva Rei Pictures', 'Retro. Rei Pictures', 'BIFF Kids']
FUNCION = re.compile(r'^(Lun|Mar|Mié|Jue|Vie|Sáb|Dom)\. (\d{1,2}) - (\d{1,2}:\d{2}) \| (.+)$')
META = re.compile(r'^(\d{4}) \| (.+)$')
X_FICHA = 130


def lineas():
    out = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(PAGINAS[0]), '-l', str(PAGINAS[1]),
                          PDF, '-'], capture_output=True, text=True).stdout
    paginas = re.findall(r'<page [^>]*>(.*?)</page>', out, re.S)
    res = []
    for n, p in enumerate(paginas, PAGINAS[0]):
        for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" '
                             r'yMax="([\d.]+)">(.*?)</line>', p, re.S):
            words = re.findall(r'<word[^>]*>(.*?)</word>', m.group(5))
            res.append({'pag': n, 'x': float(m.group(1)), 'y': float(m.group(2)),
                        't': html.unescape(' '.join(words)).strip()})
    return res


def es_titulo(l, siguiente):
    return (l['x'] >= X_FICHA and l['t'] == l['t'].upper() and re.search(r'[A-ZÁÉÍÓÚÑ]', l['t'])
            and siguiente is not None and META.match(siguiente['t']))


def nombre(s):
    """«Juan Andrés ARANGO» → «Juan Andrés Arango»: el PDF pone los apellidos en
    versalitas; la caja de un nombre propio no es un dato."""
    return ' '.join(w.capitalize() if w.isupper() and len(w) > 1 else w for w in s.split())


def plano(s):
    import unicodedata
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# LA CAJA DEL TÍTULO. El PDF imprime todos los títulos en MAYÚSCULAS; la agenda
# de la Cinemateca (48 fichas del BIFF, fuentes/biff-2026/cinemateca/) los trae
# en caja de título. Donde la obra está allá, se toma esa caja; donde no,
# queda la del PDF y se decide al montar.
def cajas_cinemateca():
    p = f'{REPO}/fuentes/biff-2026/cinemateca/biff-nodos.json'
    if not os.path.exists(p):
        return {}
    return {plano(v['titulo']): v['titulo'] for v in json.load(io.open(p, encoding='utf-8')).values()}


MENORES = {'a', 'al', 'de', 'del', 'el', 'en', 'la', 'las', 'los', 'para', 'por', 'un', 'una', 'y', 'o',
           'e', 'the', 'of', 'and', 'in', 'on', 'to', 'for'}


def caja_titulo(t):
    """«NO QUIERO SER UN HOMBRE» → «No Quiero Ser un Hombre»: la caja de título
    que usa la Cinemateca para las otras 48 (y la que prefiere Juan), para los
    13 títulos que solo están en el PDF, que los imprime en mayúsculas."""
    out = []
    for i, w in enumerate(t.lower().split()):
        out.append(w if (i and w in MENORES) else w[:1].upper() + w[1:])
    return ' '.join(out)


def main():
    CAJA = cajas_cinemateca()
    L = lineas()
    obras, seccion_pag = [], {}
    programa_funciones = []
    por_pag = {}
    for l in L:
        por_pag.setdefault(l['pag'], []).append(l)
    seccion = None
    for pag in sorted(por_pag):
        ls = sorted(por_pag[pag], key=lambda l: (l['y'], l['x']))
        col = [l for l in ls if l['x'] >= X_FICHA]
        # la sección que rotula la página (o la ficha): la última vista manda
        titulos = []
        for i, l in enumerate(col):
            if l['t'] in SECCIONES:
                continue
            sig = next((c for c in col[i + 1:] if c['t'] not in SECCIONES), None)
            if es_titulo(l, sig):
                # EL TÍTULO EN DOS RENGLONES («BORRACHOS MIENTRAS ESCUCHAMOS» /
                # «LAS GOTAS CAER»): el renglón de encima, en mayúsculas y pegado,
                # es la primera mitad
                ant = col[i - 1] if i else None
                if (ant and ant['t'] == ant['t'].upper() and re.search(r'[A-Z]', ant['t'])
                        and 0 < l['y'] - ant['y'] < 12 and not any(a is ant for _, a in titulos)):
                    l = {**l, 't': ant['t'] + ' ' + l['t'], 'y': ant['y']}
                titulos.append((i, l))
        for k, (i, l) in enumerate(titulos):
            y0 = l['y']
            y1 = titulos[k + 1][1]['y'] if k + 1 < len(titulos) else 10 ** 6
            # la sección: el rótulo más cercano ANTES del título siguiente y
            # a la altura de este (a la derecha del título o en la página)
            for s in ls:
                if s['t'] in SECCIONES and s['y'] < y1 - 20:
                    if s['y'] <= y0 + 20 or not titulos[:k]:
                        seccion = s['t']
            bloque = [c for c in col if y0 < c['y'] < y1 and c['t'] not in SECCIONES]
            # el SEGUNDO RENGLÓN de un título partido («LAS GOTAS CAER») cae
            # dentro del bloque: se salta hasta la línea de metadatos, o su
            # texto se tomaba por el país («2026»)
            while bloque and not META.match(bloque[0]['t']) and bloque[0]['t'] == bloque[0]['t'].upper():
                bloque = bloque[1:]
            meta = META.match(bloque[0]['t']) if bloque else None
            partes = [p.strip() for p in meta.group(2).split('|')] if meta else []
            if pag in SECCION_DE_PAGINA:
                seccion = SECCION_DE_PAGINA[pag]
            o = {'titulo': CAJA.get(plano(l['t'])) or caja_titulo(l['t']), 'titulo_pdf': l['t'], 'seccion': 'Retrospectiva Rei Pictures'
                 if seccion == 'Retro. Rei Pictures' else seccion,
                 '_src': {'pdf': os.path.basename(PDF), 'pagina': pag}}
            if meta:
                o['anio'] = int(meta.group(1))
            j = 1
            # la línea de metadatos puede partirse en dos («… | Drama histórico |»
            # / «125 min. | Francés, Neerlandés»)
            while j < len(bloque) and not bloque[j]['t'].startswith('Dirección'):
                partes += [p.strip() for p in bloque[j]['t'].split('|')]
                j += 1
            partes = [p for p in partes if p]
            dur = next((p for p in partes if re.match(r'^\d+ min\.?$', p)), None)
            if dur:
                o['duracion_min'] = int(re.match(r'\d+', dur).group())
                idx = partes.index(dur)
                o['pais'] = partes[0] if partes else ''
                o['genero'] = ' | '.join(partes[1:idx])
                o['idioma'] = ', '.join(partes[idx + 1:])
            k0 = next((n for n, c in enumerate(bloque) if c['t'].startswith('Dirección:')), None)
            d = bloque[k0]['t'] if k0 is not None else ''
            # LA DIRECCIÓN PARTIDA: un renglón que termina en coma sigue en el
            # siguiente («Dirección: Tobias NÖLLE,» / «Loran BONNARDOT
            # (Co-Dirección)»); sin esto el segundo nombre se iba a la sinopsis
            while k0 is not None and d.rstrip().endswith(',') and k0 + 1 < len(bloque):
                k0 += 1
                d += ' ' + bloque[k0]['t']
            o['director'] = nombre(re.sub(r'\s*\(Co-?Direcci[oó]n\)', '', d.replace('Dirección:', '')).strip())
            if k0 is not None:
                sin = ' '.join(c['t'] for c in bloque[k0 + 1:])
                o['sinopsis'] = re.sub(r'(\w)- (\w)', r'\1\2', sin).strip()
            if pag == PAGINA_PROGRAMA:
                o['programa'] = SECCION_DE_PAGINA[pag]
                o['funciones_ficha'] = []
            else:
                funciones = [f for f in ls if f['x'] < X_FICHA and y0 < f['y'] < y1 and FUNCION.match(f['t'])]
                o['funciones_ficha'] = [f['t'] for f in funciones]
            obras.append(o)
        if pag == PAGINA_PROGRAMA:
            programa_funciones = [f['t'] for f in ls if f['x'] < X_FICHA and FUNCION.match(f['t'])]
    json.dump({'_provenance': provenance(
        'PDF oficial del BIFF 12 (Programacion_BIFF_12_DIGITAL.pdf, 26 sep 2026)',
        que_aporta='las fichas: sección, año, país, género, duración, idiomas, dirección, '
                   'sinopsis y las funciones que cada ficha anota',
        url='https://biff.co/documentos/Programacion_BIFF_12_DIGITAL.pdf',
        metodo='pdftotext -bbox-layout: columnas por coordenada, cada función a la ficha '
               'cuyo título está encima'),
        'obras': obras,
        'programas': {SECCION_DE_PAGINA[PAGINA_PROGRAMA]: {
            'obras': [o['titulo_pdf'] for o in obras if o.get('programa')],
            'funciones_ficha': programa_funciones}}}, io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    por_sec = {}
    for o in obras:
        por_sec[o['seccion']] = por_sec.get(o['seccion'], 0) + 1
    print(f'✓ {len(obras)} obras · {sum(len(o["funciones_ficha"]) for o in obras)} funciones '
          f'anotadas en las fichas → {os.path.relpath(DESTINO, REPO)}')
    for s, n in por_sec.items():
        print(f'   {n:2}  {s}')


if __name__ == '__main__':
    main()
