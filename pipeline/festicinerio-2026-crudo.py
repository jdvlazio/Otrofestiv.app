#!/usr/bin/env python3
"""festicinerio-2026-crudo.py — la programación de FESTICINERIO V → crudo.

LA FUENTE es el carrusel oficial p/DfXJjeBm1w7 (5 nov 2026, 8 láminas): 01–06 son
la parrilla 8–13 nov en el Teatro Cuesta; 07, la charla del sábado 14. El catálogo
del pre-onboarding (p/DfVZajiG5qG) dice QUÉ obras hay en cada programa: cada franja
de cortos se llama como una de sus 11 categorías, y las 48 obras entran.

DOS LECTURAS: la tabla de abajo, a ojo lámina por lámina, y Vision (ocr.py): cada
hora y cada palabra del título tienen que estar en SU lámina, o el paso falla.

DÍAS OFICIALES (regla de Juan, 8 oct): la portada dice 8 al 13. La charla del
sábado 14 queda en `_fuera`.
ACCESO: el pie dice «entrada libre». DURACIÓN de un programa: el hueco hasta la
franja siguiente de la misma sala.
FILMINUTO: seis franjas sin lista de obras publicada. Se publican sin obras.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance  # noqa: E402
from ocr import leer  # noqa: E402

POST = 'DfXJjeBm1w7'
IG = f'{REPO}/fuentes/ig/{POST}'
CATALOGO = f'{REPO}/festivals/staging/festicinerio-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/festicinerio-2026-crudo.json'
URL = f'https://www.instagram.com/p/{POST}/'
SEDE = 'Teatro Cuesta'
LARGO, FILMI = 'Largometrajes', 'Filminuto'
# título en la parrilla → categoría del catálogo, cuando difieren
CATEGORIA = {'Animación Nacional': 'Animación', 'Ficción Nacional': 'Ficción'}

# lámina, día, [(hora, título, sección; None = la sección es el título del programa)]
PARRILLA = [
    ('01', '2026-11-08', [('17:00', 'Animación Internacional', None), ('17:30', 'Animación Nacional', None),
                          ('18:10', 'Documental', None), ('19:20', FILMI, FILMI), ('19:30', 'Andariega', LARGO)]),
    ('02', '2026-11-09', [('17:00', 'Videoclip', None), ('17:20', 'Ficción Internacional', None),
                          ('18:00', FILMI, FILMI), ('18:10', 'En Bajo de 4 Puntas', LARGO), ('19:00', 'Diòba', LARGO)]),
    ('03', '2026-11-10', [('17:00', 'Experimental', None), ('18:30', FILMI, FILMI), ('18:40', 'Paristopia', LARGO)]),
    ('04', '2026-11-11', [('17:00', 'Selección Riosucio', None), ('17:30', 'Panorama Regional', None),
                          ('18:20', FILMI, FILMI), ('18:40', 'Simplicity of Chaos', LARGO)]),
    ('05', '2026-11-12', [('17:00', 'Ficción Nacional', None), ('19:00', FILMI, FILMI),
                          ('19:20', 'La Creciente', 'Largometraje Invitado')]),
    ('06', '2026-11-13', [('17:00', 'Historias de Carnaval Internacional', None), ('19:00', FILMI, FILMI),
                          ('19:20', 'Sangre Invisible', 'Cortometraje Invitado'), ('20:00', 'Conversatorio', 'Conversatorio')]),
]
CREDITOS = {
    'La Creciente': {'director': 'Pablo Andrés Muñoz Castrillón',
                     '_creditos_por_que': 'único largo colombiano de 2026 con ese título (TMDB 1779631), publicado en Jardín 2026'},
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).strip()


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def rotulo(h):
    a, b = int(h[:2]) % 12 or 12, h[3:]
    return [f'{a} {b}'] if b != '00' else [f'{a}pm', f'{a} pm', f'{a}am']


def main():
    cat = json.load(io.open(CATALOGO, encoding='utf-8'))['obras']
    por_cat, por_tit = {}, {norm(o['titulo']): o for o in cat}
    for o in cat:
        por_cat.setdefault(o['categoria'], []).append(o)
    rutas = {n: f'{IG}/{n}.jpg' for n, _, _ in PARRILLA}
    lec = leer(list(rutas.values()))
    funcs, fallos, usadas = [], [], set()
    for n, dia, lista in PARRILLA:
        txt = plano(' '.join(lec.get(rutas[n], [])))
        for i, (hora, titulo, seccion) in enumerate(lista):
            if not any(r in txt for r in rotulo(hora)):
                fallos.append(f'{dia} {hora}: la hora no se lee en la lámina {n}')
            for p in re.findall(r'\w{4,}', plano(titulo)):
                if p not in txt:
                    fallos.append(f'{titulo}: «{p}» no se lee en la lámina {n}')
            f = {'titulo': titulo, 'dia': dia, 'hora': hora, 'sede': SEDE, 'sala': '', 'acceso': 'Entrada libre',
                 'seccion': seccion or titulo, '_src': {'url': URL, 'lamina': f'{n}.jpg', 'date': '2026-11-05'}}
            sig = lista[i + 1][0] if i + 1 < len(lista) else None
            if seccion is None or seccion == FILMI:
                if sig:
                    f['duracion_min'], f['_duracion_de'] = mins(sig) - mins(hora), 'hueco hasta la franja siguiente'
            if seccion is None:
                c = CATEGORIA.get(titulo, titulo)
                f['obras'] = [{k: o[k] for k in ('titulo', 'director', 'pais') if o.get(k)} for o in por_cat[c]]
                usadas.add(c)
            elif seccion == LARGO:
                o = por_tit[norm(titulo)]
                f['titulo'], f['director'] = o['titulo'], o['director']
                usadas.add(LARGO)
            elif seccion == 'Conversatorio':
                f.update(tipo='evento', event_kind='conversatorio')
            f.update(CREDITOS.get(titulo, {}))
            funcs.append(f)
    sueltas = set(por_cat) - usadas
    if sueltas:
        fallos.append(f'categorías sin función: {sorted(sueltas)}')
    largos = {norm(f['titulo']) for f in funcs if f['seccion'] == LARGO}
    faltan = {norm(o['titulo']) for o in por_cat[LARGO]} - largos
    if faltan:
        fallos.append(f'largos sin función: {sorted(faltan)}')
    n_obras = sum(len(f.get('obras') or []) for f in funcs) + len(largos)
    if n_obras != 48:
        fallos.append(f'{n_obras} obras del catálogo en la parrilla, se esperaban 48')
    if fallos:
        sys.exit('✗ la tabla y el OCR no coinciden:\n  · ' + '\n  · '.join(fallos))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('IG @festicinerio, carrusel de la programación (5 nov 2026)',
                                  que_aporta='día, hora y sala de todo el festival', url=URL,
                                  metodo='lectura a ojo de las láminas, confirmada por Vision'),
        '_acceso': {'estado': 'Entrada libre', 'revisado': '2026-11-05', 'fuentes': [URL],
                    '_por_que': 'el pie dice «entrada libre»'},
        '_fuera': [{'titulo': 'Si hay alguien vivo, grite o haga ruido', 'dia': '2026-11-14', 'hora': '09:00',
          'sede': 'Biblioteca Otto Morales B.', 'lamina': '07',
          '_por_que': 'charla de Álvaro Cardona, fuera de las fechas oficiales 8–13 nov (regla de Juan, 8 oct)'}], 'funciones': funcs}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funcs)} funciones, {n_obras} obras del catálogo → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
