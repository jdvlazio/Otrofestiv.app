#!/usr/bin/env python3
"""miradas-2026-catalogo.py — la selección de Miradas Medellín 2026 (Festival de
cine y artes audiovisuales, Medellín, 3–8 nov 2026). PRE-ONBOARDING.

LAS FUENTES: tres carruseles de @cinematecademedellin, leídos sin sesión por el
embed público (pipeline/ig_sin_sesion.py + ig.bajar_laminas → fuentes/ig/<sc>/):
  · DefnwMYDHVV (14 oct) — Largometrajes iberoamericanos: una lámina por obra con
    dirección, año, país, género, duración, idioma, sinopsis y sus funciones.
  · DeiGFLoIKqz (15 oct) — Cortometrajes iberoamericanos: igual.
  · DeX03IEDKSe (11 oct) — Cine hecho en Medellín: título + dirección, sin más.
Las iberoamericanas se leen por OCR (pipeline/ocr.py): el texto va en orden. Las
de Medellín están diagramadas en dos columnas que el OCR cruza: se TRANSCRIBEN a
ojo (HECHO_EN_MEDELLIN, abajo), lámina por lámina.

Las funciones que traen las láminas se guardan en `funciones_lamina` de cada
obra, verbatim, para el crudo que llegará con la parrilla completa.

Escribe festivals/staging/miradas-2026-catalogo.json
"""
import glob, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
import ocr  # noqa: E402

OUT = f'{REPO}/festivals/staging/miradas-2026-catalogo.json'
POSTS = {'DefnwMYDHVV': 'Largometrajes iberoamericanos', 'DeiGFLoIKqz': 'Cortometrajes iberoamericanos'}
URL = 'https://www.instagram.com/p/{}/'
DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) \d+ de noviembre')
FICHA = re.compile(r'^Dir(?:s|a|\.ª|ª)?[.:]?\s*(.+)$')

# Transcripción a ojo de DeX03IEDKSe, láminas 02–08 (16 oct 2026). La lámina dice
# «Dir.» o «Dir.ª»; se guarda el nombre tal cual lo pinta el festival.
HECHO_EN_MEDELLIN = [
    (2, 'Largometrajes', 'La pesadilla del siervo', 'Manuel Villa Machado'),
    (2, 'Largometrajes', 'Uno vuelve siempre', 'Camilo Ríos'),
    (2, 'Largometrajes', 'Chapecó, el último sobreviviente', 'Edison Vanegas Álvarez'),
    (3, 'Cortometrajes', 'Madres de nacimiento', 'Gloria Isabel Gómez Ceballos'),
    (3, 'Cortometrajes', 'Refracción', 'Isabella Palacio Mesa'),
    (3, 'Cortometrajes', 'La mona', 'Laura Gutiérrez'),
    (3, 'Cortometrajes', 'De Saúl', 'Santiago Gomxz'),
    (4, 'Cortometrajes', 'La danza de los ángeles', 'Juan Restrepo Molina'),
    (4, 'Cortometrajes', 'La escucha, la razón', 'Juan David Bolívar Araque'),
    (4, 'Cortometrajes', 'Luis Antonio', 'Juan José Arias Gil'),
    (5, 'Cortometrajes', 'Mal de tierra', 'Camila Caballero Guzmán'),
    (5, 'Cortometrajes', 'La muerte nos declaró adultos', 'Luisa María Charry Valencia'),
    (5, 'Cortometrajes', 'Kof kof', 'Juan David Cardona Arboleda'),
    (6, 'Cine comunitario', 'Éther, somos todo', 'Fabián Cataño Torres'),
    (6, 'Cine comunitario', 'El teléfono morado', 'Taller de Cine Corporación Mi Comuna'),
    (6, 'Cine comunitario', 'Paralelo', 'Tania Díaz, Elsy Galeano'),
    (6, 'Cine comunitario', 'Oro molido #2', 'Juan David Medrano'),
    # Fe de erratas del pie del post: «El proyecto "El paradero", de la selección
    # Cine comunitario, es realizado por Semillero Colectivo Cinestrato» (la
    # lámina 07 decía «Taller de Cine Corporación Mi Comuna»).
    (7, 'Cine comunitario', 'El paradero', 'Semillero Colectivo Cinestrato'),
    (7, 'Cine comunitario', 'Mamá Chila raíz y corazón de la comunidad', 'Dir. Colectiva'),
    (7, 'Cine comunitario', 'Chico de barrio (videoclip animado)', 'Juan David Echavarría Urrego'),
    (8, 'Cine expandido', 'Todas las cosas que algún día se desvanecieron', 'Carlos Eduardo Castaño Correa'),
    (8, 'Cine expandido', 'Vórtice nebular', 'Diego Alberto Pérez Osorno'),
    (8, 'Cine expandido', 'El sueño de Sedna', 'Felipe López'),
    (8, 'Cine expandido', 'Sosiego al atardecer', 'Jose Luis Ruiz Peláez'),
]


# Lo que el OCR leyó mal, mirado en la lámina (16 oct 2026)
OCR_A_OJO = {'lan de la Rosa': 'Ian de la Rosa'}


def frase(t):
    """PROPUESTA de caja (las láminas van en mayúscula sostenida); el publicado
    lo da la ficha de TMDB o se confirma con Juan (caja-sostenida)."""
    t = t.lower()
    return re.sub(r'^(\W*)(\w)', lambda m: m.group(1) + m.group(2).upper(), t)


def ibero(sc, seccion):
    fs = sorted(glob.glob(f'{REPO}/fuentes/ig/{sc}/[0-9][0-9].jpg'))
    if not fs:
        sys.exit(f'✗ faltan las láminas de {sc}: python3 -c "import ig; ig.bajar_laminas(...)"')
    obras = []
    for f, lineas in ocr.leer(fs).items():
        ls = [x.strip() for x in lineas]
        i = next((k for k, x in enumerate(ls) if FICHA.match(x)), None)
        if i is None:
            continue                       # portada, cierre o logos
        titulo = ls[i - 1]
        ficha = ls[i]
        j = i + 1
        while j < len(ls) and not ls[j][:1].islower() and '•' in ls[j]:
            ficha += ' ' + ls[j]
            j += 1
        sinopsis, funciones = [], []
        for x in ls[j:]:
            if x.startswith('Medellín') or x.startswith('Mědellín'):
                break
            if DIA.match(x) or (funciones and not x.startswith('Funciones') and not DIA.match(x) and len(x) < 40 and x[:1].islower()):
                if DIA.match(x):
                    funciones.append(x)
                else:
                    funciones[-1] += ' ' + x
            elif x.startswith('Funciones con presencia'):
                pass
            elif not funciones:
                sinopsis.append(x)
        partes = [p.strip() for p in re.split(r'\s*•\s*', FICHA.match(ficha).group(1))]
        anio = re.search(r'\b(20\d\d)\b', ficha)
        dur = re.search(r'(\d+)\s*min', ' '.join(ls[i:i + 3]))
        obras.append({'titulo': frase(titulo), 'titulo_lamina': titulo,
                      'anio': int(anio.group(1)) if anio else None,
                      'duracion_min': int(dur.group(1)) if dur else None, 'seccion': seccion, 'ficha_lamina': ficha,
                      'director': OCR_A_OJO.get(partes[0], partes[0]), 'partes': partes[1:],
                      'sinopsis_es': ' '.join(sinopsis),
                      'con_presencia': any('presencia' in x for x in ls),
                      'funciones_lamina': funciones,
                      '_src': {'url': URL.format(sc), 'lamina': int(os.path.basename(f)[:2]), 'date': '2026-10-16'}})
    return obras


def main():
    obras = []
    for sc, sec in POSTS.items():
        obras += ibero(sc, sec)
    for lam, sec, tit, dire in HECHO_EN_MEDELLIN:
        obras.append({'titulo': tit, 'seccion': 'Cine hecho en Medellín · ' + sec, 'director': dire,
                      '_src': {'url': URL.format('DeX03IEDKSe'), 'lamina': lam, 'date': '2026-10-16'}})
    json.dump({'_provenance': provenance('@cinematecademedellin (3 carruseles, embed sin sesión)',
                                         metodo='OCR de láminas (iberoamericanas) + transcripción a ojo (Hecho en Medellín)'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
