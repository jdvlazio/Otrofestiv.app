#!/usr/bin/env python3
"""afiches-ajenos.py — el veredicto de cada afiche que un festival toma de OTRO.

El enriquecido reusa el afiche de una obra ya publicada en otro festival nuestro.
Así llegaron nueve tarjetas de sección de SiembraFest a FILCMAR, Fantasmagoría,
Girardota y Popayán (auditoría del 7 oct 2026). Saber si una imagen ajena es una
tarjeta de festival exige LEERLA (OCR del sistema, solo macOS), y la CI no puede:
por eso el veredicto se calcula aquí y se versiona en assets/AFICHES-AJENOS.json,
con la huella del archivo. El guardián [afiche-es-afiche] exige que todo afiche
ajeno publicado tenga veredicto, con su huella vigente, y que sea «afiche».

    python3 scripts/afiches-ajenos.py          # recalcula y escribe el registro
"""
import glob
import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
from afiche_criterio import veredicto  # noqa: E402
from ocr import leer  # noqa: E402

DESTINO = f'{REPO}/assets/AFICHES-AJENOS.json'


def ajenos():
    """{ruta web: [festivales que la usan sin ser su carpeta]}"""
    out = {}
    for g in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(g)[:-5]
        try:
            films = json.load(open(g, encoding='utf-8')).get('films') or []
        except Exception:
            continue
        for f in films:
            for x in (f.get('film_list') or [f]):
                p = str(x.get('poster') or '')
                if not p.startswith('/assets/'):
                    continue
                carpeta = p.split('/')[2]
                if fid == carpeta or fid.startswith(carpeta) or carpeta.startswith(fid):
                    continue
                out.setdefault(p, set()).add(fid)
    return out


def huella(ruta):
    return hashlib.sha1(open(ruta, 'rb').read()).hexdigest()


def main():
    A = ajenos()
    rutas = [REPO + p for p in A if os.path.exists(REPO + p)]
    ocr = leer(rutas)
    reg = {}
    for p, usos in sorted(A.items()):
        r = REPO + p
        if not os.path.exists(r):
            continue
        m = veredicto(r, ' '.join(ocr.get(r, [])), ajena=True)
        reg[p] = {'sha1': huella(r), 'veredicto': 'afiche' if m is None else m, 'usado_en': sorted(usos)}
    json.dump({'_provenance': {'genera': 'scripts/afiches-ajenos.py', 'criterio': 'pipeline/afiche_criterio.py',
                               'regla': 'un afiche ajeno se publica solo con veredicto «afiche» y huella vigente'},
               'afiches': reg}, open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    malos = {p: v for p, v in reg.items() if v['veredicto'] != 'afiche'}
    print(f'✓ {len(reg)} afiches ajenos · {len(malos)} rechazados → {os.path.relpath(DESTINO, REPO)}')
    for p, v in malos.items():
        print(f'   ✗ {p} ({", ".join(v["usado_en"])}): {v["veredicto"]}')


if __name__ == '__main__':
    main()
