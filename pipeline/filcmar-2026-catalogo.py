# -*- coding: utf-8 -*-
"""Catálogo de la Selección Oficial del 8° FILCMAR (Marinilla), desde IG.

Acá SÍ hay que leer las láminas: el pie solo dice «desliza para conocer la lista
completa». A cambio, la lámina trae la ficha entera —título, dirección, país (o
universidad) , año y duración—, que es más de lo que suele dar un festival.
Salidas:
  festivals/staging/filcmar-2026-seleccion-oficial.json            (este script)
  festivals/staging/filcmar-2026-seleccion-oficial-enriquecido.json (enriquecer_catalogo.py)
"""
import json, os, re

LAT = 'https://www.instagram.com/filcmar/p/DdSWXZoDT3a/'
UNI = 'https://www.instagram.com/filcmar/p/DczfyWVjjI6/'
TRA = 'https://www.instagram.com/filcmar/p/DdU6a5DjYji/'

# (titulo, director, pais_o_universidad, anio, duracion tal cual la lámina)
LATINO = [
 ('Lo demás es ruido', 'Nicolás Pereda', 'México', 2026, '70 min'),
 ('La corazonada', 'Diego Soto', 'Chile', 2025, '78 min'),
 ('Andariega', 'Raúl Soto', 'Colombia', 2025, '94 min'),
 ('El vuelo del moscardón', 'Emanuel Di Cunto, Rodrigo Medrano y Pablo Bochard', 'Argentina', 2025, '105 min'),
 ('Testimonio', 'Leonardo Amaral, Roberto Cotta', 'Brasil', 2026, '14 min'),
 ('Una vez un cuerpo', 'María Cristina Pérez', 'Colombia, Estados Unidos', 2025, '10 min'),
 ('Pude ver un fantasma desde mi ventana', 'Mayro Romero', 'Ecuador', 2025, '9 min'),
 ('Casi 30', 'Mila Aquilia, Bianca Oliveti', 'Argentina', 2026, '14 min'),
 ('Persépio', 'Felipe Bibian', 'Brasil', 2025, '18 min'),
 ('Lo que queda del mar', 'Camila Adaro Liloff', 'Argentina', 2026, '5 min'),
 ('El día interrumpido', 'María Villar', 'Argentina', 2025, '13 min'),
]
# Tercera competencia, anunciada el 15 SEP — el catálogo de las otras dos se
# había capturado el día antes. La encontró el issue de radar del festival
# (#903) el 16 SEP: cinco títulos que no teníamos.
#
# HDLT no lleva dirección: la lámina la acredita «Prod. Artefactum Suba», que es
# una PRODUCTORA. Va en `produccion`, no en `director` — un crédito que no es
# autoría no se convierte en autoría por caber en el campo.
TRASNOCHE = [
 ('HDLT', None, 'Artefactum Suba', 'Colombia', 2026, '18 min'),
 ('El cazador', 'Luciana Riso Soto, Manuel Villa', None, 'Colombia', 2026, '13 min'),
 ('Show de Ziggy: la maldición del Mariachi Bondage', 'Giorgio Ross', None, 'México', 2026, '10 min'),
 ('Merrimundi', 'Niles Atallah', None, 'Chile', 2025, '20 min'),
 ('Petra y el sol', 'Malu Furche, Stefania Malacchini', None, 'Chile', 2026, '10 min'),
]
UNIV = [
 ('The Raules', 'Hugo Chamorro', 'Politécnico Colombiano Jaime Isaza Cadavid', 2025, '1:19 min'),
 ('Desarraigo', 'Nicolas Patiño Hortua, Andrés Santiago Cely Orjuela', 'Politécnico Colombiano Jaime Isaza Cadavid', 2026, '15 min'),
 ('Para no volver', 'Tania Galvis', 'Universidad del Magdalena', 2026, '10:16 min'),
 ('Miguel Ángel, Federico, y el carro que pasó encima de las gafas', 'Juan David Rodriguez', 'Universidad Central de Bogotá', 2025, '13 min'),
 ('Agachar el rostro', 'Camilo Medina Noy', 'Pontificia Universidad Javeriana', 2025, '12:36 min'),
 ('El espejo de la vida', 'Simón Sánchez Plazas', 'Universidad Jorge Tadeo Lozano', 2025, '9:17 min'),
 ('La danza del caos', 'Valeria Preciado Romaña', 'Universidad de los Andes', 2025, '5:35 min'),
 ('La pecera', 'Angela Tatiana Fonseca Galvez', 'Academia de Artes de China', 2025, '7:42 min'),
 ('Reverb', 'María Elizabeth López', 'Universidad Nacional de Colombia', 2025, '1:55 min'),
 ('Chicha la chicharra', 'Sofia Alejandra Uzcátegui', 'Universidad Autónoma de Bucaramanga', 2025, '10 min'),
 ('HUSH', 'Santiago Franco', 'Universidad Jorge Tadeo Lozano', 2025, '13:35 min'),
 ('Sol de niebla', 'Maria José Ibarra, Florentino Vargas', 'Universidad Nacional de Colombia', 2026, '5:44 min'),
 ('Pudor ante el asalto de los ojos furtivos', 'Laura María Rodríguez', 'Pontificia Universidad Javeriana', 2025, '8:35 min'),
 ('El ocaso de los dioses', 'Juan Pablo Rendón', 'Instituto Tecnológico Metropolitano', 2025, '19:05 min'),
 ('Somnolítico', 'Abril Natalia Velásquez', 'Universidad Nacional de Colombia', 2026, '11 min'),
]

def minutos(d):
    """«10:16 min» es 10 min 16 s, NO 10 h 16. Se redondea al minuto y se deja
    la cadena original al lado: el que dude, que mire la lámina."""
    m = re.match(r'^(\d+):(\d+)\s*min$', d)
    if m:
        return int(m.group(1)) + (1 if int(m.group(2)) >= 30 else 0)
    return int(re.match(r'^(\d+)', d).group(1))

obras = []
for t, dr, donde, anio, dur in LATINO:
    obras.append({'titulo': t, 'director': dr, 'pais': donde, 'anio': anio,
                  'duracion_min': minutos(dur), 'duracion_lamina': dur,
                  'seccion': 'Competencia Latinoamericana',
                  '_src': {'url': LAT, 'date': '2026-09-14'}})
for t, dr, donde, anio, dur in UNIV:
    obras.append({'titulo': t, 'director': dr, 'universidad': donde, 'anio': anio,
                  'duracion_min': minutos(dur), 'duracion_lamina': dur,
                  'seccion': '6ª Competencia Universitaria',
                  '_src': {'url': UNI, 'date': '2026-09-06'}})

for t, dr, prod, donde, anio, dur in TRASNOCHE:
    o = {'titulo': t, 'director': dr, 'pais': donde, 'anio': anio,
         'duracion_min': minutos(dur), 'duracion_lamina': dur,
         'seccion': 'Competencia Espíritu Trasnoche',
         '_src': {'url': TRA, 'date': '2026-09-15'}}
    if prod:
        o['produccion'] = prod
    obras.append({k: v for k, v in o.items() if v is not None})

out = {
 '_provenance': {
   'fuente': 'Instagram del festival (@filcmar) — los tres carruseles de Selección Oficial',
   'capturado': '2026-09-15',
   'metodo': 'LECTURA DE LÁMINA, una por una, a resolución completa. El texto alternativo de Instagram vino VACÍO, así que la doble lectura de Jardín no era posible por ahí. Para Trasnoche (15 sep) sí la hubo: OCR del sistema (pipeline/ocr.py) MÁS lectura visual, y no coincidieron — el OCR leyó «HOLT» donde la lámina dice «HDLT», y puso la productora en el renglón de la dirección. Manda la vista. El pie no lista títulos («desliza para conocer la lista completa»).',
   'alcance': 'Las TRES competencias publicadas (Latinoamericana, Universitaria y Espíritu Trasnoche). NO hay funciones: ni día, ni hora, ni sede. El festival es del 9 al 13 de octubre.'},
 '_festival': {
   'nombre': 'Festival de Cine de Marinilla', 'sigla': 'FILCMAR', 'edicion': 8,
   'ciudad': 'Marinilla, Antioquia',
   'fechas': '9–13 de octubre de 2026',
   'organiza': 'Cinismo y Algo Más (@cinismoyalgomas) y Corarte Marinilla',
   'ig': 'https://www.instagram.com/filcmar/',
   'filmfreeway': 'https://filmfreeway.com/FestivaldeCinedeMarinilla-FILCMAR',
   'radar': 'SIN ISSUE — descubierto el 15 sep 2026, no estaba en el radar'},
 '_trampas': [
   'LA DURACIÓN DE LA COMPETENCIA UNIVERSITARIA VIENE EN mm:ss, no en minutos: «The Raules 1:19 min» es UN minuto con 19 segundos, no una hora y 19. Leerla como h:mm convierte un corto de un minuto en un largometraje. Se guarda `duracion_min` redondeado y `duracion_lamina` con la cadena original al lado.',
   'En la Competencia Universitaria la lámina pone la UNIVERSIDAD donde la Latinoamericana pone el PAÍS. No es el país de la obra: va en su propio campo.',
   'El texto alternativo de Instagram vino vacío en las 13 láminas: acá no hay red de seguridad por OCR, solo la lectura visual. Si algún título se relee y no coincide, manda una segunda lectura de la lámina.'],
 '_herencia': 'Cinco obras ya están enriquecidas en otros festivales nuestros: Andariega (siembrafest-2026), La corazonada y Para no volver (cinemancia-2026), Chicha la chicharra (siembrafest-2026). Verificar por director antes de heredar.',
 '_categorias': {
   'Competencia Latinoamericana': {'post': LAT, 'publicado': '2026-09-14', 'obras': len(LATINO)},
   '6ª Competencia Universitaria': {'post': UNI, 'publicado': '2026-09-06', 'obras': len(UNIV)}},
 'obras': obras}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = REPO + '/festivals/staging/filcmar-2026-seleccion-oficial.json'
json.dump(out, open(D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(obras)} obras ({len(LATINO)} latinoamericana + {len(UNIV)} universitaria)')
for o in obras[:3] + obras[11:13]:
    print(' ', o['titulo'], '·', o['duracion_lamina'], '→', o['duracion_min'], 'min')
