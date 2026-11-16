#!/usr/bin/env python3
"""cineparalapaz-2026-verificar.py — segunda y tercera lectura del crudo.

El crudo se escribió a ojo desde las láminas de p/DfzeOb2lq6q. Aquí cada
función se busca en SU lámina con dos motores de OCR que no comparten camino
(Vision, A y al doble, y Tesseract; fuentes/ig/DfzeOb2lq6q-lecturas.json, de
ig-lecturas.py): la hora y el título (o cada obra del bloque) tienen que
leerse en los dos. Si uno no lo lee, frena con lo que faltó.

    python3 pipeline/ig-lecturas.py DfzeOb2lq6q --salida fuentes/ig/DfzeOb2lq6q-lecturas.json
    python3 pipeline/cineparalapaz-2026-verificar.py
"""
import importlib.util, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUDO = f'{REPO}/festivals/staging/cineparalapaz-2026-crudo.json'
LECT = f'{REPO}/fuentes/ig/DfzeOb2lq6q-lecturas.json'
spec = importlib.util.spec_from_file_location('igl', f'{REPO}/pipeline/ig-lecturas.py')
igl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(igl)

# cómo la lámina escribe el título cuando el crudo lo normalizó
EN_LAMINA = {'Selección Oficial': None,                       # los bloques: se verifican sus obras
             'LA + Taller: Autorretrato como una herramienta para la salud menstrual': 'Autorretrato como una herramienta',
             'Cierre musical · Concierto andino: Yananty y Runa Taky': 'Yananty y Runa Taky',
             'Samay Punlla · Conmemoración a las almas': 'Conmemoración a las almas',
             'Refugiar el Gesto': 'Refugiar el gesto',
             'Conversatorio "La Propia Inopia"': 'La Propia Inopia'}


# lo que un motor no lee y la lámina sí dice: mirado a ojo, con su porqué
MIRADO = {('01.jpg', '09:00', 'Tesseract'): 'la franja «09:00 am – 11:00 am» va sobre banda naranja y Tesseract '
                                           'no la lee; Vision sí, y a ojo es inequívoca (16 nov)'}


def h12(h):
    """«15:00» → «03:00 pm»: así imprime la lámina."""
    hh, mm = map(int, h.split(':'))
    return f'{(hh - 1) % 12 + 1:02d}:{mm:02d} {"am" if hh < 12 else "pm"}'


def main():
    lect = json.load(io.open(LECT, encoding='utf-8'))['DfzeOb2lq6q']['lecturas']
    malos, n = [], 0
    for f in json.load(io.open(CRUDO, encoding='utf-8'))['funciones']:
        lam = f['_src']['lamina']
        textos = [EN_LAMINA.get(o['titulo'], o['titulo']) for o in f.get('obras') or []] or \
                 [EN_LAMINA.get(f['titulo'], f['titulo'])]
        textos = [t for t in textos if t]
        vis = '\n'.join(lect.get(k, {}).get(lam, '') for k in ('A·vision', 'C·al-doble'))
        tes = lect.get('T·tesseract', {}).get(lam, '')
        for motor, txt in (('Vision', vis), ('Tesseract', tes)):
            horas = igl.tokens(txt)['horas']
            if f['hora'] not in horas and h12(f['hora']) not in txt.lower() and (lam, f['hora'], motor) not in MIRADO:
                malos.append(f'{lam} {f["hora"]} «{f["titulo"]}»: {motor} no lee la hora')
            for t in textos:
                if not igl.lee(txt, t):
                    malos.append(f'{lam} {f["hora"]} «{t}»: {motor} no lo lee')
        n += 1
    if malos:
        print('\n'.join('✗ ' + m for m in malos))
        sys.exit(f'✗ {len(malos)} lectura(s) que no coinciden en {n} funciones: mirar la lámina')
    print(f'✓ {n} funciones: hora y títulos leídos por Vision y por Tesseract en su lámina')


if __name__ == '__main__':
    main()
