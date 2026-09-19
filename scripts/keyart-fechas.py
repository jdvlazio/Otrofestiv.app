#!/usr/bin/env python3
"""keyart-fechas.py — qué FECHAS lleva impreso cada afiche del splash.

POR QUÉ EXISTE (18 sep 2026). FICMA se aplazó por un sismo y volvió de agosto a
septiembre. El afiche del splash siguió diciendo «10 AL 17 DE AGOSTO» durante
ocho días — y yo afirmé, sin abrir ni un archivo, que el festival no había
publicado uno nuevo. Sí lo había publicado: estaba en su web como og:image desde
el 10 de septiembre. Lo cazó Juan, no el repo.

Un afiche que anuncia un mes que ya no es el del festival es la peor forma de
mentir: se lee antes que nada y nadie lo revisa porque «es del festival».

QUÉ HACE. Lee con OCR (Vision, macOS) cada keyArt declarado en FESTIVAL_CONFIG y
guarda los MESES y AÑOS que encuentra impresos. El guardián [keyart-fechas] de
validate.py compara eso contra las fechas que el festival declara, y no necesita
ni OCR ni red: lee este archivo. Es el patrón de siempre —una tabla generada y
un guardián que la lee— porque dos copias del mismo hecho divergen.

QUÉ NO HACE. No decide. Un afiche sin fechas impresas es normal y se registra
como tal; lo que el guardián persigue es el afiche que dice un mes EQUIVOCADO.

    python3 scripts/keyart-fechas.py            # regenera assets/keyart/FECHAS.json
    python3 scripts/keyart-fechas.py --ver      # además imprime lo leído
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
OUT = f'{REPO}/assets/keyart/FECHAS.json'

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
# El OCR de un afiche mezcla idiomas: varios llevan el mes en inglés.
MESES_EN = {'january': 'enero', 'february': 'febrero', 'march': 'marzo',
            'april': 'abril', 'may': 'mayo', 'june': 'junio', 'july': 'julio',
            'august': 'agosto', 'september': 'septiembre', 'october': 'octubre',
            'november': 'noviembre', 'december': 'diciembre'}


def sinacento(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                   if unicodedata.category(c) != 'Mn')


def keyarts():
    """{id de festival: ruta del keyArt} desde FESTIVAL_CONFIG."""
    cfg = open(f'{REPO}/src/config.js', encoding='utf-8').read()
    out = {}
    for m in re.finditer(r"'([a-z0-9]+)':\s*\{(.*?)\n  \},", cfg, re.S):
        k = re.search(r"keyArt:'([^']+)'", m.group(2))
        if k:
            out[m.group(1)] = k.group(1)
    return out


def main():
    from ocr import leer
    rutas, de_quien = [], {}
    for fid, rel in sorted(keyarts().items()):
        p = REPO + rel
        if os.path.exists(p):
            rutas.append(p)
            de_quien.setdefault(p, []).append(fid)
        else:
            print(f'⚠ {fid}: no existe {rel}', file=sys.stderr)

    leido = leer(rutas)
    reg = {}
    for p in rutas:
        texto = ' '.join(leido.get(p, []))
        plano = sinacento(texto)
        for en, es in MESES_EN.items():
            plano = plano.replace(en, es)
        meses = [m for m in MESES if m in plano]
        anios = sorted(set(re.findall(r'\b(20\d{2})\b', plano)))
        reg[os.path.basename(p)] = {
            'festivales': sorted(de_quien[p]),
            'meses': meses, 'anios': anios,
            'texto': re.sub(r'\s+', ' ', texto)[:300],
        }
        if '--ver' in sys.argv:
            print(f'{os.path.basename(p):34} meses={meses or "—"} años={anios or "—"}')

    json.dump({'_doc': [
        'Lo que cada afiche del splash lleva IMPRESO, leído con OCR (Vision).',
        'Lo genera scripts/keyart-fechas.py; lo vigila [keyart-fechas] en',
        'validate.py, que compara estos meses contra las fechas que el festival',
        'declara en FESTIVAL_CONFIG. No editar a mano.',
        '',
        'Un afiche sin fechas impresas es normal: meses vacíos = nada que',
        'contradecir. El caso que persigue el guardián es el afiche que anuncia',
        'un mes que ya no es el del festival (FICMA, sep 2026: el afiche decía',
        'AGOSTO ocho días después de que el festival se moviera a septiembre).'],
        'afiches': reg},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con = sum(1 for v in reg.values() if v['meses'])
    print(f'{len(reg)} afiches leídos · {con} con mes impreso → '
          f'{os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
