#!/usr/bin/env python3
"""under-2026-verificar.py — segunda y tercera lectura del crudo.

El crudo se escribió a ojo desde las cuadros del reel p/Df0rYtRxmgp. Aquí cada
función se busca en SU lámina con dos motores de OCR que no comparten camino
(Vision, A y al doble, y Tesseract; fuentes/ig/Df0rYtRxmgp-lecturas.json, de
ig-lecturas.py): la hora y el título (o cada obra del bloque) tienen que
leerse en los dos. Si uno no lo lee, frena con lo que faltó.

    python3 pipeline/ig-lecturas.py Df0rYtRxmgp --salida fuentes/ig/Df0rYtRxmgp-lecturas.json
    python3 pipeline/under-2026-verificar.py
"""
import importlib.util, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUDO = f'{REPO}/festivals/staging/under-2026-crudo.json'
LECT = f'{REPO}/fuentes/ig/Df0rYtRxmgp-lecturas.json'
spec = importlib.util.spec_from_file_location('igl', f'{REPO}/pipeline/ig-lecturas.py')
igl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(igl)

# cómo la lámina escribe el título cuando el crudo lo normalizó
EN_LAMINA = {'Fiesta Under · El Vikingo Selektor': 'El Vikingo',
             'Orígenes de los lenguajes audiovisuales experimentales y laboratorio de creación': 'laboratorio de creaci',
             'Hacerlo Sin Permiso. Laboratorio de Apropiación': 'Hacerlo Sin Permiso',
             'Función sorpresa': 'sorpresa'}


# lo que un motor no lee y la lámina sí dice: mirado a ojo, con su porqué
MIRADO = {
    ('01.jpg', '20:00', 'Tesseract'): 'la textura grunge del cuadro (manchas y grietas) rompe a Tesseract: lee «8:00 PM» como basura; Vision sí, y a ojo es inequívoca (17 nov)',
    ('03.jpg', '17:00', 'Tesseract'): 'la textura grunge del cuadro (manchas y grietas) rompe a Tesseract: no lee «5:00 pm | verdever»; Vision sí y a ojo es clara (17 nov)',
    ('02.jpg', 'Duelo', 'Tesseract'): 'la textura grunge del cuadro (manchas y grietas) rompe a Tesseract: lee «puelo»; Vision lee «Duelo» y a ojo es clara (17 nov)',
    ('04.jpg', 'El Vikingo', 'Tesseract'): 'texto blanco sobre foto: Tesseract no lo lee; Vision sí (17 nov)',
    ('06.jpg', 'Fata Morgana', 'Tesseract'): 'la textura grunge del cuadro (manchas y grietas) rompe a Tesseract: Vision lee «Fala Morgana», a ojo «Fata Morgana» (17 nov)',
    ('07.jpg', 'Hacerlo Sin Permiso', 'Tesseract'): 'la textura grunge del cuadro (manchas y grietas) rompe a Tesseract: una grieta cruza «Sin»; Vision lo lee y a ojo es claro (17 nov)',
}


def h12(h):
    """«15:00» → «03:00 pm»: así imprime la lámina."""
    hh, mm = map(int, h.split(':'))
    return f'{(hh - 1) % 12 + 1:02d}:{mm:02d} {"am" if hh < 12 else "pm"}'


def main():
    lect = json.load(io.open(LECT, encoding='utf-8'))['Df0rYtRxmgp']['lecturas']
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
                if not igl.lee(txt, t) and (lam, t, motor) not in MIRADO:
                    malos.append(f'{lam} {f["hora"]} «{t}»: {motor} no lo lee')
        n += 1
    if malos:
        print('\n'.join('✗ ' + m for m in malos))
        sys.exit(f'✗ {len(malos)} lectura(s) que no coinciden en {n} funciones: mirar la lámina')
    print(f'✓ {n} funciones: hora y títulos leídos por Vision y por Tesseract en su lámina')


if __name__ == '__main__':
    main()
