# -*- coding: utf-8 -*-
"""El PDF oficial de SASAIMA → funciones del crudo.

Hermano de siembrafest-2026-villeta.py y con su misma disciplina: BLOQUES es la
transcripción hecha LEYENDO cada página como imagen, y `verificar()` la comprueba
contra la capa de texto del PDF —título, sede, sección, hora y día—. Si el
festival reimprime, falla.

Sasaima programa OBRAS DISTINTAS a las de Villeta: de sus 28, ninguna se repite
en el otro municipio. Y trae dos que no están en la Selección Oficial, las dos de
archivo: «Madre» (1924, la más antigua que proyecta el festival) y «Tres cuentos
colombianos - Tiempos de sequía» (1963), coherente con que la Fundación
Patrimonio Fílmico Colombiano sea aliada.

    python3 pipeline/siembrafest-2026-sasaima.py --escribir
"""
import json, os, re, sys, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance                                    # noqa: E402

TEXTO = f'{REPO}/festivals/staging/siembrafest-2026-sasaima-texto.json'
SALIDA = f'{REPO}/festivals/staging/siembrafest-2026-sasaima-crudo.json'

ACCESO = 'Entrada libre'      # instagram.com/p/Dc4AhaFwFOg — cubre TODO el festival

# El PDF numera los días desde el 9 de septiembre (día 1 = miércoles 9).
DIA1 = datetime.date(2026, 9, 9)

# ── ERRATA DEL FESTIVAL ──────────────────────────────────────────────────────
# La página 7 encabeza «Día 10 · LUNES · 14/9». El día 10 de un festival que
# arranca el 9 es el VIERNES 18, y el 14/9 ya tiene su propio bloque como «Día 6»
# en la página 2. Repitieron la línea del día 6.
#
# Lo que lo cierra no es la aritmética sino una imposibilidad: si el 14/9 fuera
# correcto, habría DOS programas distintos a las 18:00 en la misma sede (Rotonda
# Tienda Museo del Café) el mismo día. Se toma el NÚMERO de día, que además cuadra
# con que el festival anuncie 9–18 y con que Sasaima cierre el 18.
ERRATA_DIA = {10: 'el PDF encabeza «Lunes 14/9», que es el día 6 y ya tiene bloque propio'}


def fecha(n):
    return (DIA1 + datetime.timedelta(days=n - 1)).isoformat()


# (día, hora, hora_fin, sede, tipo, sección, [(título, director, año, min)], página)
BLOQUES = [
 (6, '18:00', '20:00', 'Rotonda Tienda Museo del Café', 'exhibicion', 'Amores & Desamores', [
    ('Tres cuentos colombianos - Tiempos de sequía', 'Julio Luzardo', 1963, 28),
    ('Soñé su nombre', 'Ángela Carabalí', 2025, 86)], 2),

 (7, '08:00', '10:00', 'Escuela Rural Santa Ana', 'exhibicion', 'Ojo Pelao', [
    ('En el mar', 'Alfred Robinson', 2024, 7),
    ('Emechiche, el renacer de los cabeciblancos', 'Juan Camilo González', 2025, 11),
    ('Chicha la chicharra', 'Sofía Alejandra Uzcátegui León', 2025, 10),
    ('Daniel', 'Armando Velásquez', 2025, 12),
    ('Zizuma, nuestra casa de agua y nubes', 'Fátima Correa', 2026, 12)], 2),

 (7, '10:00', '12:00', 'Escuela Rural Santa Ana', 'exhibicion', 'Ojo Pelao', [
    ('Cantos al juego de "Bolar"', 'Iván Sierra', 2025, 8),
    ('La gran hazaña', 'Luber Yesid Zúñiga Ordóñez', 2024, 15),
    ('Extinta', 'Yesid Soacha', 2024, 7),
    ('La pecera', 'Ángela Tatiana Fonseca Gálvez', 2025, 8),
    ('Un pájaro más', 'Julián Gómez Reyes', 2026, 17)], 3),

 (8, '07:00', '08:30', 'IED Rural San Bernardo', 'exhibicion', 'Amores & Desamores', [
    ('Take It Off', 'Sergio Tovar Uribe', 2025, 10),
    ('Carola', 'Violeta Barrios Ramírez', 2025, 11),
    ('Desarraigo', 'Nicolás Patiño H. & Santiago Cely O.', 2026, 15),
    ('Gladiolos', 'Mónica Juanita Hernández Duquino', 2024, 15),
    ('Idilio', 'Luz Rincón Barahona', 2024, 18)], 4),

 (8, '08:30', '09:45', 'IED Rural San Bernardo', 'exhibicion', 'Ojo Pelao', [
    ('Cantos al juego de "Bolar"', 'Iván Sierra', 2025, 8),
    ('La gran hazaña', 'Luber Yesid Zúñiga Ordóñez', 2024, 15),
    ('Extinta', 'Yesid Soacha', 2024, 7),
    ('La pecera', 'Ángela Tatiana Fonseca Gálvez', 2025, 8),
    ('Un pájaro más', 'Julián Gómez Reyes', 2026, 17)], 4),

 (8, '10:15', '11:30', 'IED Rural San Bernardo', 'exhibicion', 'Estampas', [
    ('Donde nace el nombre', 'Juan Vanegas', 2025, 27),
    ('Camino al Chicamocha', 'Frank Alexander Rodríguez Rojas', 2024, 15),
    ('Sinfonía incompleta de oficios del Fonce', 'Nelson Omar Silva Sánchez', 2024, 16)], 5),

 (8, '18:00', '20:00', 'Salón Comunal Vda. San Bernardo', 'exhibicion', 'Buenos, Malos y Feos', [
    ('Entre 2 aguas', 'Carlos Gabriel Vergara M.', 2025, 93)], 5),

 (9, '10:00', '12:00', 'IED San Nicolás', 'exhibicion', 'Buenos, Malos y Feos', [
    ('Catatumbo: Casa del trueno, memoria y dignidad', 'Jhonattan Sarmiento', 2025, 8),
    ('6 de diciembre', 'Nelson Rodríguez Tequia', 2026, 30),
    ('Relatos del camino', 'Daniel Prieto Muriel', 2025, 12),
    ('La Europa', 'Jorge Pérez Aldana', 2025, 22)], 6),

 (9, '18:00', '20:00', 'Vereda Ilo Alto', 'exhibicion', 'Buenos, Malos y Feos', [
    ('El huaquero', 'Harold De Vasten', 2026, 94)], 6),

 (10, '10:00', '12:00', 'IED San Nicolás', 'exhibicion', 'Así es Cundinamarca', [
    ('Xie. Defensa de la vida', 'Adriana Bernal-Mor y Paola Zuluaga P.', 2025, 70)], 7),

 (10, '18:00', '20:00', 'Rotonda Tienda Museo del Café', 'exhibicion', 'Buenos, Malos y Feos', [
    ('Madre', 'Samuel Velasquez', 1924, 17),
    ('El huaquero', 'Harold De Vasten', 2026, 94)], 7),
]


def verificar():
    """Cada dato transcrito de la imagen, contra la capa de texto de su página."""
    P = json.load(open(TEXTO, encoding='utf-8'))['paginas']
    fallos = []
    for dia, ini, fin, sede, tipo, sec, obras, pag in BLOQUES:
        pl = P.get(str(pag), '')
        t = norm(pl)
        for tit, *_ in obras:
            if norm(tit.split(':')[0].split(' - ')[0]) not in t:
                fallos.append(f'p{pag}: «{tit}» no está en la página')
        for quien, q in (('sede', sede), ('sección', sec)):
            if norm(q.split()[0]) not in t:
                fallos.append(f'p{pag}: la {quien} «{q}» no aparece')
        h12 = f'{int(ini[:2]) % 12 or 12}:{ini[3:]}'
        if h12 not in pl:
            fallos.append(f'p{pag}: la hora {ini} ({h12}) no está impresa')
        # el DÍA se comprueba por su NÚMERO, que es lo que el PDF acierta; la
        # fecha del día 10 está mal impresa y por eso no se compara contra ella
        if f'Día {dia}' not in pl and f'Día         {dia}' not in pl:
            fallos.append(f'p{pag}: no aparece «Día {dia}»')
    return fallos


def crudo():
    funcs = []
    for dia, ini, fin, sede, tipo, sec, obras, pag in BLOQUES:
        f = {'dia': fecha(dia), 'hora': ini, 'hora_fin': fin,
             'sede': sede, 'seccion': sec, 'acceso': ACCESO,
             'titulo': ' + '.join(o[0] for o in obras),
             '_src': f'PDF oficial de la programación de Sasaima, p{pag}',
             'obras': [{'titulo': t, 'director': d, 'anio': a,
                        'duracion_min': m, 'seccion': sec} for t, d, a, m in obras]}
        if dia in ERRATA_DIA:
            f['_errata_impresa'] = ERRATA_DIA[dia]
        funcs.append(f)
    funcs.sort(key=lambda x: (x['dia'], x['hora'], x['sede']))
    return {'_provenance': provenance(
              'PDF oficial de la programación de Sasaima — '
              'siembrafest.com/descargas/programacion_11sf_sasaima.pdf',
              metodo='doble lectura: capa de texto del PDF (no OCR) + lectura visual de cada '
                     'página; verificar() cruza título, sede, sección, hora y número de día',
              ojo='el PDF encabeza el día 10 como «Lunes 14/9» y es el VIERNES 18 — ver '
                  'ERRATA_DIA en el generador'),
            'funciones': funcs}


if __name__ == '__main__':
    fallos = verificar()
    print(f'  verificar(): {len(fallos)} fallos')
    for x in fallos:
        print('   ·', x)
    d = crudo()
    obras = {o['titulo'] for f in d['funciones'] for o in f['obras']}
    print(f'  {len(d["funciones"])} funciones · {len(obras)} obras distintas · '
          f'{len({f["sede"] for f in d["funciones"]})} sedes')
    if '--escribir' in sys.argv:
        if fallos:
            sys.exit('  ✗ no se escribe con fallos de verificación')
        json.dump(d, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  → {SALIDA}')
