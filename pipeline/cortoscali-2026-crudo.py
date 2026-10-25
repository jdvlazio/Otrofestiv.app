#!/usr/bin/env python3
"""cortoscali-2026-crudo.py — la parrilla de Cortos Cali 18 → crudo.

LA FUENTE es Instagram (@cortoscali; cortoscali.com no publica programación):
el carrusel «Programación» (p/De4VP9xkaMd, 24 oct, 17 láminas) y la
«Programación académica» (p/DerpBbZkeSs). Las láminas se transcribieron a ojo
a festivals/staging/cortoscali-2026-ojos.json; ig-lecturas.py las leyó cuatro
veces y cortoscali-2026-verificar.py cruza cada título, hora y dirección
contra esas lecturas.

DECISIONES (25 oct 2026):
  · cada lámina de selección es UNA función con 3–4 cortos (un programa). El
    festival no le pone nombre al bloque más allá de la sección, y la misma
    sección se repite el martes, jueves y viernes: el título es «<sección> —
    <día>», como Leviza;
  · la duración de los bloques no está publicada: se deduce del hueco hasta la
    función siguiente en la misma sala (60 min), y 60 si es la última del día;
    las masterclass, hueco con tope de 90;
  · el Lab de Guion (lun 26) es «solo seleccionados por convocatoria»: no se
    publica. La Muestra de Películas Ganadoras (sáb 31, Cinemateca La Tertulia)
    cae fuera de los días oficiales (27–30 oct): no se publica (duda a Juan);
  · ACCESO: «🎟 Entrada LIBRE» en el pie del post de programación.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'cortoscali-2026'
OJOS = f'{REPO}/festivals/staging/cortoscali-2026-ojos.json'
# LA DIRECCIÓN DECLARADA (25 oct 2026): la lámina manda, salvo una corrección
# escrita con su fuente y su porqué en -correcciones.json («direccion»). Los
# ojos se quedan verbatim; la lámina original viaja en `_director_lamina`.
CORR = f'{REPO}/festivals/staging/cortoscali-2026-correcciones.json'
DESTINO = f'{REPO}/festivals/staging/cortoscali-2026-crudo.json'
URL = 'https://www.instagram.com/p/De4VP9xkaMd/'
URL_ACAD = 'https://www.instagram.com/p/DerpBbZkeSs/'
SEDE = 'Auditorio Xepia UAO'
ACCESO = 'Entrada libre'
DIA = {'2026-10-27': 'Martes', '2026-10-28': 'Miércoles', '2026-10-29': 'Jueves', '2026-10-30': 'Viernes'}


def minutos(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def duraciones(funcs, tope):
    por_dia = {}
    for f in funcs:
        por_dia.setdefault(f['dia'], []).append(f)
    for fs in por_dia.values():
        fs.sort(key=lambda f: f['hora'])
        for i, f in enumerate(fs):
            if i + 1 < len(fs):
                f['duracion_min'] = min(tope, minutos(fs[i + 1]['hora']) - minutos(f['hora']))
                f['_duracion_de'] = 'hueco hasta la siguiente en la sala'
            else:
                f['duracion_min'] = 60
                f['_duracion_de'] = '60: lo último del día en la sala'


def main():
    ojos = json.load(open(OJOS, encoding='utf-8'))
    dirs = json.load(open(CORR, encoding='utf-8')).get('direccion', {})

    def obra(t, d, p):
        o = {'titulo': t, 'director': d, 'pais_respaldo': p}
        c = dirs.get(t)
        if c:
            if c['lamina'] != d:
                sys.exit(f'✗ corrección de dirección de {t!r}: la lámina ya no dice {c["lamina"]!r} sino {d!r}')
            o['director'], o['_director_lamina'] = c['director'], d
        return o
    bloques = []
    for b in ojos['bloques']:
        bloques.append({
            'titulo': f"{b['seccion']} — {DIA[b['dia']]}",
            'dia': b['dia'], 'hora': b['hora'], 'sede': SEDE, 'acceso': ACCESO,
            'seccion': b['seccion'],
            '_src': {'url': URL, 'lamina': b['lamina']},
            'obras': [obra(t, d, p) for t, d, p in b['obras']],
        })
    duraciones(bloques, 60)
    charlas = []
    for m in ojos['masterclass']:
        charlas.append({
            'titulo': m['titulo'], 'dia': m['dia'], 'hora': m['hora'], 'sede': SEDE,
            'acceso': ACCESO, 'tipo': 'evento', 'event_kind': 'masterclass',
            'seccion': 'Masterclass', 'invitados': m['invitado'],
            '_src': {'url': URL_ACAD, 'lamina': m['lamina']},
        })
    duraciones(charlas, 90)
    funcs = sorted(bloques + charlas, key=lambda f: (f['dia'], f['hora']))
    out = {'_provenance': provenance(
        'IG @cortoscali: «Programación» p/De4VP9xkaMd (24 oct) + «Programación académica» p/DerpBbZkeSs',
        que_aporta='día, hora, sala, sección y obras (título, dirección, país) de cada bloque',
        url=URL, metodo='transcripción a ojo lámina por lámina, cruzada con 4 lecturas OCR'),
        'funciones': funcs, '_fuera': ojos['fuera']}
    json.dump(out, open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n = sum(len(f.get('obras', [])) for f in funcs)
    print(f'✓ {DESTINO}: {len(funcs)} funciones, {n} obras')


if __name__ == '__main__':
    main()
