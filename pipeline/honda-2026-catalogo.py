# -*- coding: utf-8 -*-
"""Catálogo de la selección oficial del 4.º Festival Latinoamericano de Cine de Honda, desde IG.

PRE-ONBOARDING (2 oct 2026, radar #978). El festival (8–11 oct) publicó su
selección «por convocatoria» en el carrusel p/Dd9_hgrFFA2 (1 oct), en dos
franjas: «A Rodar por el Río y la Región» (lámina 4) y «Río de Fantasmagorías y
Símbolos» (láminas 5 y 6). La lámina trae SOLO título y dirección: ni país, ni
año, ni duración, ni día, hora o sede. Las láminas 0–3 son la carta a los
seleccionados y la 7, los aliados.

LECTURA a ojo de las tres láminas, confirmada por la OCR del sistema
(fuentes/honda-2026-ocr-seleccion.json): toda palabra de 4+ letras de cada
título y cada crédito está en SU lámina (ver verifica()).

LO QUE SE COPIA TAL CUAL aunque parezca errata (se pregunta, no se corrige):
«Guadianes de la Fiesta», «Juan Jóse Cañon Romero», «Ána María Cepeda».
Salidas:
  festivals/staging/honda-2026-seleccion-oficial.json             (este script)
  festivals/staging/honda-2026-seleccion-oficial-enriquecido.json (enriquecer_catalogo.py)
"""
import io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POST = 'https://www.instagram.com/p/Dd9_hgrFFA2/'
OCR = f'{REPO}/fuentes/honda-2026-ocr-seleccion.json'

RIO = 'A Rodar por el Río y la Región'
FAN = 'Río de Fantasmagorías y Símbolos'
# (lámina, franja, título, dirección) — tal cual la lámina
OBRAS = [
 (4, RIO, 'Cauce Vivo', 'Tania Lorena Real'),
 (4, RIO, 'Un Río que Reclama su Memoria', 'Gabriela Galindo'),
 (4, RIO, 'Selva Nublada: Un viaje al corazón del bosque de niebla', 'Viviana Sánchez Prada'),
 (4, RIO, 'Un Futuro Enterrado en el Pasado', 'Daniel Bustos Echeverry'),
 (4, RIO, 'Guadianes de la Fiesta', 'Juan Jóse Cañon Romero'),
 (4, RIO, 'El cronista de Ibagué', 'Juan Jóse Cañon Romero'),
 (4, RIO, 'La Gran Hazaña', 'Luber Yesid Zúñiga Ordóñez'),
 (4, RIO, 'Muerto Parado', 'Andrés Mora, Diego Bohorquez'),
 (5, FAN, 'Los Lobo', 'Saaed Garcia Perez'),
 (5, FAN, '40X40 La Medida de la Barbarie', 'Gabriela Galindo'),
 (5, FAN, 'La Profecía de la Abuela Yuraq Jukú', 'Mujeres Territorio de Paz - Jessica Alejandra Trujillo Londoño'),
 (5, FAN, 'O Macaco no Fim do Arco-Íris', 'Tom Kenji, Lucas Tavares'),
 (5, FAN, 'Espíritus del Bosque', 'Juan Sebastián Arévalo Rojas'),
 (5, FAN, 'Toma 10', 'Ángel Campaña y Juan Arias'),
 (5, FAN, 'Hippomane Mancinella', 'Ricardo Muñoz Izquierdo'),
 (5, FAN, 'Arañas cazando abejas', 'Carlos Armando Castillo Martínez'),
 (6, FAN, 'HDLT', 'Colectivo Artefactum Suba'),
 (6, FAN, 'La Gallina Saraviada', 'Ingrid Paola Bonilla Rodríguez'),
 (6, FAN, 'CHAIKA', 'Mujeres Territorio de Paz - Jessica Alejandra Trujillo Londoño'),
 (6, FAN, 'Orígenes', 'Daniel Rodríguez Gaitán'),
 (6, FAN, 'Tierra Encima', 'Sebastián Duque R.'),
 (6, FAN, 'Tejiendo Almas', 'Ána María Cepeda'),
 (6, FAN, 'Ay de mi', 'Yamyle Ramírez'),
]


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def verifica():
    cajas = json.load(io.open(OCR, encoding='utf-8'))
    w = {int(k[:2]): set(plano(' '.join(v)).split()) for k, v in cajas.items()}
    fallos = [f'lámina {l}: la OCR no encuentra {x!r} de «{t}» / «{d}»'
              for l, _, t, d in OBRAS for x in plano(t + ' ' + d).split()
              if len(x) >= 4 and x not in w[l]]
    # cobertura inversa: cada «Dir.» impreso tiene su obra
    for l in (4, 5, 6):
        impresos = sum(1 for x in cajas[f'{l:02d}.jpg'] if x.startswith('Dir.'))
        propios = sum(1 for o in OBRAS if o[0] == l)
        if impresos != propios:
            fallos.append(f'lámina {l}: {impresos} créditos impresos y {propios} obras')
    return fallos


fallos = verifica()
if fallos:
    sys.exit('✗ la transcripción y la OCR no coinciden:\n  · ' + '\n  · '.join(fallos))

obras = [{'titulo': t, 'director': d, 'seccion': f, '_src': {'url': POST, 'date': '2026-10-01', 'lamina': l}}
         for l, f, t, d in OBRAS]
out = {
 '_provenance': {
   'fuente': 'Instagram del festival (@cinelathondafest) — el carrusel de la selección oficial por convocatoria',
   'capturado': '2026-10-02',
   'metodo': 'lectura a ojo de las láminas 4–6, confirmada por la OCR del sistema en los dos sentidos',
   'alcance': 'Las dos franjas por convocatoria. Solo título y dirección. NO hay funciones: ni día, ni hora, ni sede.'},
 '_festival': {
   'nombre': 'Festival Latinoamericano de Cine de Honda', 'edicion': 4,
   'lema': 'Río de Fantasmagorías y Símbolos', 'ciudad': 'Honda, Tolima',
   'fechas': '8–11 de octubre de 2026', 'ig': 'https://www.instagram.com/cinelathondafest/',
   'radar': 978},
 '_trampas': [
   'La lámina copia tal cual lo que parecen erratas: «Guadianes de la Fiesta», «Juan Jóse Cañon Romero», «Ána María Cepeda». Se preguntan, no se corrigen.',
   '«Mujeres Territorio de Paz - Jessica Alejandra Trujillo Londoño» firma DOS obras (La Profecía de la Abuela Yuraq Jukú y CHAIKA): colectivo + directora.',
   'HDLT es la misma obra de FILCMAR y Fantasmagoría (Artefactum Suba).'],
 '_categorias': {RIO: sum(1 for o in OBRAS if o[1] == RIO), FAN: sum(1 for o in OBRAS if o[1] == FAN)},
 'obras': obras}
D = REPO + '/festivals/staging/honda-2026-seleccion-oficial.json'
io.open(D, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print(f'✓ {len(obras)} obras ({out["_categorias"][RIO]} + {out["_categorias"][FAN]}) → {os.path.relpath(D, REPO)}')
