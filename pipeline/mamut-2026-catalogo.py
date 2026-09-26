#!/usr/bin/env python3
"""mamut-2026-catalogo.py — la Selección Oficial de Mamut 11 → catálogo.

PRE-ONBOARDING (26 sep 2026, radar #964). Mamut, el festival de memoria
audiovisual de Medellín (5–11 oct), publicó sus 16 cortometrajes seleccionados
y todavía no la parrilla. Igual que FILCMAR y Fantasmagoría, no hay crudo sino
catálogo.

LA FUENTE son las LÁMINAS del carrusel `p/DdufDCkgX6-` (25 sep), no su pie. El
pie da título, dirección y país; las láminas dan además AÑO y DURACIÓN —sin
ellos el candado de TMDB no puede verificar nada— y separan las dos
selecciones, Cortos Internacionales y Cortos Nacionales. Donde los dos
difieren, manda la lámina: el pie firma «Belleza letal · Colectivo» y la lámina
nombra a las doce personas que la dirigen.

TRES LECTURAS, igual que Itagüí:
  1. la transcripción A OJO de las dos láminas, fuentes/mamut-2026-ojos.json:
     es lo que se publica;
  2. el OCR de las mismas láminas (pipeline/ocr.swift): cada obra tiene que
     aparecer con su año y su duración;
  3. el PIE del post, que es otra transcripción del propio festival: cada obra
     tiene que estar con su país.
Si una lectura no confirma a la otra, el paso falla. Las diferencias ya
entendidas van en DIFERENCIAS, cada una con su porqué.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'mamut-2026'
POST = 'DdufDCkgX6-'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
OJOS = f'{REPO}/fuentes/{FID}-ojos.json'
DESTINO = f'{REPO}/festivals/staging/{FID}-catalogo.json'
ESPERADAS = {'Selección Cortos Internacionales': 8, 'Selección Cortos Nacionales': 8}

# lo que el PIE escribe distinto y ya está mirado
DIFERENCIAS = {
    'Belleza letal': 'el pie la firma «Colectivo»; la lámina nombra a las doce '
                     'personas que la dirigen, y manda la lámina',
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def ocr(n):
    r = subprocess.run(['swift', f'{REPO}/pipeline/ocr.swift', f'{LAMINAS}/{n:02d}.jpg'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ el OCR de la lámina {n} falló: {r.stderr[:200]}')
    return json.loads(r.stdout)['lineas']


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['obras']
    cuenta = {}
    for o in ojos:
        cuenta[o['seccion']] = cuenta.get(o['seccion'], 0) + 1
    if cuenta != ESPERADAS:
        sys.exit(f'✗ por sección: {cuenta}, se esperaba {ESPERADAS}')

    # 2 · el OCR: el título, y en la línea (o líneas) de crédito que lo siguen,
    #     «· Año · N min.»
    fallos, sin_titulo = [], []
    lectura = {n: ocr(n) for n in sorted({o['lamina'] for o in ojos})}
    for o in ojos:
        lin = lectura[o['lamina']]
        i = next((k for k, l in enumerate(lin) if plano(l) == plano(o['titulo'])), None)
        if i is not None:
            credito = ' '.join(lin[i + 1:i + 5])
        else:
            # EL OCR SE SALTA UNA LÍNEA DE TÍTULO a veces —pasó con «Una
            # habitación en Bangkok»: leyó el crédito de debajo y no el título—.
            # No se afloja: la obra se busca por la línea de SU dirección y el
            # año y la duración se siguen verificando igual.
            j = next((k for k, l in enumerate(lin)
                      if plano(o['director'].split(',')[0].split(' y ')[0]) in plano(l)), None)
            if j is None:
                fallos.append(f'«{o["titulo"]}»: el OCR no encuentra ni el título ni su '
                              f'dirección en la lámina {o["lamina"]}')
                continue
            credito = ' '.join(lin[j:j + 4])
            sin_titulo.append(o['titulo'])
        credito = credito[:credito.find('min') + 3] if 'min' in credito else credito
        if not re.search(rf'\b{o["anio"]}\b\D+{o["duracion_min"]}\s*m', credito):
            fallos.append(f'«{o["titulo"]}»: el OCR no confirma {o["anio"]} · {o["duracion_min"]} min '
                          f'(lee: {credito[-60:]!r})')

    # 3 · el pie: «Título · Dirección · País» por obra
    pie = json.loads(open(f'{LAMINAS}/post.jsonl', encoding='utf-8').readline())['caption']
    filas = {}
    for linea in pie.split('\n'):
        partes = [p.strip() for p in linea.split('·')]
        if len(partes) == 3:
            filas[plano(partes[0])] = partes
    for o in ojos:
        f = filas.get(plano(o['titulo']))
        if not f:
            fallos.append(f'«{o["titulo"]}»: no está en el pie')
            continue
        if plano(f[2]) != plano(o['pais']):
            fallos.append(f'«{o["titulo"]}»: país {o["pais"]!r} en la lámina, {f[2]!r} en el pie')
        if plano(f[1]) != plano(o['director']) and o['titulo'] not in DIFERENCIAS:
            fallos.append(f'«{o["titulo"]}»: dirección {o["director"]!r} en la lámina, {f[1]!r} en el pie')
    if len(filas) != len(ojos):
        fallos.append(f'el pie lista {len(filas)} obras y las láminas {len(ojos)}')
    if fallos:
        sys.exit('✗ las lecturas no coinciden:\n  · ' + '\n  · '.join(fallos))

    obras = [{k: v for k, v in o.items() if k != 'lamina'} for o in ojos]
    json.dump({'_provenance': provenance(
        f'IG @mamut_festival p/{POST} (25 sep 2026): las láminas 1 y 2 leídas a ojo, '
        'confirmadas por el OCR de las mismas láminas y por el pie del post'),
        'obras': obras}, open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras · las tres lecturas coinciden '
          f'({len(DIFERENCIAS)} diferencia explicada) → {os.path.relpath(DESTINO, REPO)}')
    if sin_titulo:
        print('   el OCR no leyó el título de ' + ' · '.join(sin_titulo) +
              ' — confirmada por su línea de dirección, año y duración')
    for s, n in cuenta.items():
        print(f'   {n:2}  {s}')


if __name__ == '__main__':
    main()
