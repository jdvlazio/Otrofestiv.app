#!/usr/bin/env python3
"""provinciadevelez-2026-crudo.py — el catálogo → crudo: 7 funciones (25 nov 2026).

Cada obra del catálogo trae su(s) función(es) con la lámina que lo dice; acá se
agrupan por día, hora y sede, en el orden de las láminas. Una función con una obra
es esa obra; con varias, un programa.

30 NOV (SENA, Vélez) FUERA: el afiche dice 1–6 dic; solo días oficiales (Juan, 24 nov).
TÍTULOS: el festival no nombra los programas: «A + B» / «A + N Obras» (precedente Under).
ACCESO: «¡Entrada libre a todos los escenarios!» (Df4hzKXkYiP, 18 nov; Df2AcYNEbXC, 17 nov).
DURACIÓN: ninguna franja; la del programa es la suma de las obras con duración conocida.
Las obras sin función se quedan en el catálogo (no se inventan).
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

CAT = f'{REPO}/festivals/staging/provinciadevelez-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/provinciadevelez-2026-crudo.json'
FB25 = 'https://www.facebook.com/festivaldecinebarbosa/posts/pfbid02fqEztN5KAMM1Ro3k4YYZ61BBVJwtd7myTLcnZyVFp8qtAkX3ygDGrYRBDc18297Ul'
IG = 'https://www.instagram.com/p/'
CORREO = 'correo del festival a hola@otrofestiv.app (4 láminas, sin texto)'
# (día, hora) → título, sección, post, fecha del post, obras en el orden de las láminas
FUNCIONES = {
    ('2026-12-01', '18:00'): ('La familia Bélier + El pescador (videoclip)', 'Franja Infantil', 'DfxyKI-S9LA', '2026-11-15', [
        'La familia Bélier', 'El pescador (videoclip)']),
    ('2026-12-02', '18:00'): ('Nueve jueves en Riachuelo + 3 Obras', 'Selección Oficial', FB25, '2026-11-25', [
        'Nueve jueves en Riachuelo', 'Sinfonía incompleta de oficios del Fonce', 'La Belleza', 'Pez azul']),
    ('2026-12-02', '19:00'): ('My Name Is Bill W. + De la tradición a la prohibición', 'Muestra Especial', 'Df2AcYNEbXC', '2026-11-17', [
        'My Name Is Bill W.', 'De la tradición a la prohibición']),
    ('2026-12-03', '18:00'): ('El fantástico Sr. Fox + Salvemos el agua', 'Franja Infantil', 'Df4hzKXkYiP', '2026-11-18', [
        'El fantástico Sr. Fox', 'Salvemos el agua']),
    ('2026-12-04', '18:00'): ('La imaginada', 'Muestra Especial', 'Df71yg2P6hF', '2026-11-19', ['La imaginada']),
    ('2026-12-04', '19:00'): ('Saint Juanito + 10 Obras', 'Selección Oficial', 'Df7ZYXrEaXh', '2026-11-19', [
        'Saint Juanito', 'El latir de la memoria', 'Paisaje / Niebla', 'Olvidar a Miriam', 'Limones',
        'Entre amigos', 'El pescador', 'El cuarto', 'Creation of a Unicorn', 'Anima Sola', 'Cicatrices']),
    ('2026-12-05', '18:00'): ('El dolor del vientre + 5 Obras', 'Selección Oficial', 'DgFiVrTEbh0', '2026-11-23', [
        'El dolor del vientre', 'Llantos del monte', 'Uma Uñjirinaka · Alto Milluni',
        'Un diálogo para sanar la Tierra', 'Escisión de la cigarra', 'El arte de inmortalizar mortales']),
    ('2026-12-05', '20:00'): ('Tres lunas nuevas', 'Muestra Central', CORREO, '2026-11-27', ['Tres lunas nuevas']),
    ('2026-12-06', '20:00'): ('Ayuno y cenizas', 'Muestra Central', CORREO, '2026-11-27', ['Ayuno y cenizas']),
}
# Eventos sin obra (correo del 27 nov): el conversatorio del 5 dic
EVENTOS = [{'titulo': 'Conversatorio: Realidad y destino', 'dia': '2026-12-05', 'hora': '19:30',
            'sede': 'Parque Emilio Ulloa', 'seccion': 'Conversatorios', 'tipo': 'evento',
            'event_kind': 'conversatorio', 'invitados': 'Rodrigo Dimaté y María Jimena Barreto'}]
INICIO, FIN = '2026-12-01', '2026-12-06'   # el afiche oficial
assert all(INICIO <= d <= FIN for d, _ in FUNCIONES), 'función fuera de los días oficiales'
CAMPOS = ('director', 'pais', 'anio', 'duracion_min', 'sinopsis', 'synopsis_en')


def obra(o):
    d = {'titulo': o['titulo'], **{k: o[k] for k in CAMPOS if o.get(k)}}
    if o.get('categoria') == 'Documental':
        d['genero'] = d['genre'] = 'Documental'
    return d


def main():
    cat = {o['titulo']: o for o in json.load(io.open(CAT, encoding='utf-8'))['obras']}
    # cobertura inversa: lo que el catálogo pone en cada función = lo transcrito aquí
    porf, sedes = {}, {}
    for o in cat.values():
        for f in o.get('funciones') or ([o['funcion']] if o.get('funcion') else []):
            k = (f['fecha'], f['hora'])
            porf.setdefault(k, set()).add(o['titulo'])
            assert sedes.setdefault(k, f['sede']) == f['sede'], k
    assert porf == {k: set(v[4]) for k, v in FUNCIONES.items()}, 'catálogo ≠ funciones'
    out = []
    for (dia, hora), (tit, sec, sc, fecha, obras) in FUNCIONES.items():
        f = {'titulo': tit, 'dia': dia, 'hora': hora, 'sede': sedes[dia, hora], 'seccion': sec,
             'acceso': 'Entrada libre',
             '_src': {'url': sc if sc.startswith(('http', 'correo')) else f'{IG}{sc}/', 'date': fecha, 'tipo': 'festival' if sc.startswith(('http', 'correo')) else 'festival-ig'}}
        os_ = [obra(cat[t]) for t in obras]
        if len(os_) == 1:
            f.update({k: v for k, v in os_[0].items() if k != 'titulo'})
        else:
            f['obras'] = os_
        out.append(f)
    for e in EVENTOS:
        out.append({**e, 'acceso': 'Entrada libre', '_src': {'url': CORREO, 'date': '2026-11-27', 'tipo': 'festival'}})
    out.sort(key=lambda f: (f['dia'], f['hora']))
    json.dump({'_provenance': provenance('IG @9_festcineprovinciadevelez (láminas) vía provinciadevelez-2026-catalogo.json'),
               'funciones': out}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} funciones → {OUT}')


if __name__ == '__main__':
    main()
