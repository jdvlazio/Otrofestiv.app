#!/usr/bin/env python3
"""biff-2026-pordias.py — la tabla «Programación por días» del PDF oficial → funciones.

Páginas 44–50 del PDF (el índice impreso dice 42). Columnas fijas:

    Sede (x≈31)   Sala (x≈94–116)   Hora (x≈140)   Película (x≈167)   Sección (íconos)

La SEDE y la SALA van escritas UNA vez, centradas a la altura de su grupo de
filas; la hora y la película, una por fila (el título puede partirse en dos
renglones). Cada fila se asigna a la sala y a la sede cuya etiqueta está más
cerca en vertical, dentro de su día. Es una deducción por posición, y por eso
este paso NO es la parrilla: es una de las lecturas que el crudo cruza contra
las funciones que anota cada ficha (sede y sala escritas en cada función), la
grilla «por salas» y la agenda de la Cinemateca.
"""
import html
import io
import json
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/biff-2026/Programacion_BIFF_12_DIGITAL.pdf'
DESTINO = f'{REPO}/fuentes/biff-2026/por-dias.json'
PAGINAS = (44, 50)
DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) (\d{1,2}) de octubre$')
HORA = re.compile(r'^\d{1,2}:\d{2}$')
SALA = re.compile(r'^(SALA .+|AUDITORIO .+|TEATRO|AULA .+|PLAZOLETA.*|TEATRO ESTUDIO)$')


def lineas():
    out = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(PAGINAS[0]), '-l', str(PAGINAS[1]),
                          PDF, '-'], capture_output=True, text=True).stdout
    res = []
    for n, p in enumerate(re.findall(r'<page [^>]*>(.*?)</page>', out, re.S), PAGINAS[0]):
        for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" '
                             r'yMax="([\d.]+)">(.*?)</line>', p, re.S):
            w = re.findall(r'<word[^>]*>(.*?)</word>', m.group(5))
            res.append({'pag': n, 'x': float(m.group(1)), 'y': float(m.group(2)),
                        'x2': float(m.group(3)), 't': html.unescape(' '.join(w)).strip()})
    return res


def main():
    L = lineas()
    filas = []
    for pag in sorted({l['pag'] for l in L}):
        ls = sorted([l for l in L if l['pag'] == pag], key=lambda l: (l['y'], l['x']))
        dias = [(l['y'], l) for l in ls if l['x'] < 60 and DIA.match(l['t'])]
        for k, (y0, dl) in enumerate(dias):
            y1 = dias[k + 1][0] if k + 1 < len(dias) else 10 ** 6
            dia = f'2026-10-{int(DIA.match(dl["t"]).group(2)):02d}'
            bloque = [l for l in ls if y0 < l['y'] < y1 and not l['t'].startswith(('Sede', 'Sala', 'Hora'))]
            horas = [l for l in bloque if 135 <= l['x'] <= 145 and HORA.match(l['t'])]
            titulos = [l for l in bloque if 160 <= l['x'] <= 175]
            salas = [l for l in bloque if 85 <= l['x'] < 135 and not HORA.match(l['t'])]
            # la sede puede ocupar varios renglones («CINE COLOMBIA» / «MULTIPLEX»
            # / «AVENIDA CHILE»): renglones pegados en x<85 se juntan
            sedes, cur = [], None
            for l in [l for l in bloque if l['x'] < 85 and not DIA.match(l['t'])]:
                if cur and l['y'] - cur['y2'] < 4:
                    cur['t'] += ' ' + l['t']; cur['y2'] = l['y']; cur['yc'] = (cur['y'] + l['y']) / 2
                else:
                    cur = {'t': l['t'], 'y': l['y'], 'y2': l['y'], 'yc': l['y']}; sedes.append(cur)
            # CADA RENGLÓN DE TÍTULO VA A SU HORA MÁS CERCANA. Un título en dos
            # renglones queda CENTRADO en su fila: el primero está por ENCIMA de
            # la hora («6 MESES EN EL EDIFICIO» a y=199,5 con su hora a 202,5), y
            # asignar «desde la hora hacia abajo» lo pegaba a la fila anterior.
            de_hora = {id(h): [] for h in horas}
            for t in titulos:
                if horas:
                    de_hora[id(min(horas, key=lambda h: abs(h['y'] - t['y'])))].append(t)
            for h in horas:
                partes = de_hora[id(h)]
                titulo = ' '.join(t['t'] for t in sorted(partes, key=lambda t: t['y']))
                yc = sum(t['y'] for t in partes) / len(partes) if partes else h['y']
                sala = min(salas, key=lambda s: abs(s['y'] - yc))['t'] if salas else ''
                sede = min(sedes, key=lambda s: abs(s['yc'] - yc))['t'] if sedes else ''
                filas.append({'dia': dia, 'hora': h['t'], 'titulo': titulo, 'sede': sede,
                              'sala': sala, 'pag': pag, 'y': round(yc, 1)})
    json.dump({'_fuente': 'PDF oficial BIFF 12, «Programación por días» (págs. 44–50), por coordenadas',
               'funciones': filas}, io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(filas)} funciones leídas de la tabla por días → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
