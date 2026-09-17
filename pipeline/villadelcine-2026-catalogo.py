# -*- coding: utf-8 -*-
"""Catálogo de la Selección Oficial del 12° Festival Villa del Cine, desde IG.

A diferencia de Jardín, acá NO hace falta leer las láminas: el festival escribe
título y dirección EN EL PIE de cada reel, uno por categoría. La lámina es la
pieza gráfica; el dato está en el texto. Se transcribe verbatim —incluidas sus
erratas, que van al mapa de correcciones, no a la transcripción—.
Salida: festivals/staging/villadelcine-2026-seleccion-oficial.json

NO hay enriquecido: el pie del festival da título y dirección pero NI AÑO NI
DURACIÓN, y sin uno de los dos el candado de enriquecer.py no puede abrirse.
Las láminas tampoco los traen (se miraron: son solo fotogramas).
"""
import json, os
BASE = 'https://www.instagram.com/festivalvilladelcine/reel/'
CATS = [
 ('Mejor Cortometraje YoungFilm', 'Dc9eZuGzzNZ', '2026-09-06', [
   ('Withch and Frog', 'Anastasia Provotorova'),
   ('Tiro Libre', 'Inti Deus'),
   ('Sun Coffee', 'Zoé Filloux'),
   ('La Silla', 'Clara García'),
   ('Far', 'We Are Central Asia Collective')]),
 ('Mejor Cortometraje Escolar', 'Dc_mqC_qsDc', '2026-09-07', [
   ('Sua y Sie: Guardianes de la vida', 'Johanna Cortés'),
   ('Solo', 'Agustina Lecaros'),
   ('Manos Rojas', 'Julián Monroy'),
   ('La Presencia de Blanco', 'Néstor Javier Serpa'),
   ('In Between', 'Carlos Andrés Paniagua')]),
 ('Mejor Cortometraje IA', 'DdCfLeDBJeP', '2026-09-08', [
   ('Prompt Zero', 'Tomás Etter Gómez'),
   ('Catatumbo: House of Thunder, Memory, and Dignity', 'Jhonattan Sarmiento'),
   ('Lens', 'Eduardo Rodriguez'),
   ('They Call It Sausage', 'Timm Osterhold'),
   ('Life is a Chessboard; Every Move is Final', 'Wang Zhi-Zhong')]),
 ('Mejor Cortometraje con Celular', 'DdEvchbu11S', '2026-09-09', [
   ('No se fía, ni aunque lloren', 'Natalia Hernández Sánchez'),
   ('La Última Historia', 'Eberto Manotas y Mauro Andrade'),
   ('A body without a horse?', 'Lara Fuke'),
   ('Maleza', 'Nicolle Estrada Díaz y Marcela Palacio Montoya'),
   ('Ventajas y desventaja de soñar despierto', 'Lorena López')]),
 ('Mejor Cortometraje Vertical', 'DdH9DfzO7_M', '2026-09-10', [
   ('Ánima de Marea', 'Laury T. Herrera'),
   ('Nahuales', 'Alejandro Cervantes'),
   ('Behind the Door', 'Leonardo Valenti'),
   ('4 Minutes', 'Rogerio Troiani'),
   ('Shorts', 'Daniel Baena Pacheco')]),
 ('Mejor VR', 'DdJ5KDGq9Fn', '2026-09-11', [
   ('Floppy the Robot – El último contacto', 'Jacobo Rendón'),
   ('Human', 'Debora Bergamini'),
   ('Protecting Our Territory', 'Christopher Boulton')]),
 ('Mejor Videoclip', 'DdMnxg-pWMZ', '2026-09-12', [
   ('Después de tanto amor', 'Mercedes Oviedo'),
   ('Mucho gusto', 'Cintia Obando'),
   ('A pesar de mí', 'Thomas Mejía Lozano'),
   ('Benditos los viejos', 'Camilo Duque Zuluaga y Santiago Rubio López'),
   ('Aguapanela', 'Juan José Narváez')]),
 ('Mejor Cortometraje Apasionado', 'DdPCDPLqNx8', '2026-09-13', [
   ('Vía Crucis', 'Juan Lucas Neira'),
   ('1 paseo por la ciudad', 'Sara Coello Coello y Alejandro Acuña Sevilla'),
   ('La Sombrilla de Mamá', 'Mateo Forero'),
   ('Grief', 'Nicolas Patiño Hortua y Andrés Santiago Cely Orjuela'),
   ('Lost Fragments of a Seizure', 'Michael Martinez')]),
 ('International Universities', 'DdRpOgSqBkz', '2026-09-15', [
   ('Beyond the End', 'Sara Sangiorgio'),
   ('I Don’t Know What to Do', 'Akshita Tyagi, Leyla Belarbi y Lia Macruz'),
   ('Final Act', 'Babi Astolfi y Lisa Soares'),
   ('TV Entreaberta', 'Mateus Compart'),
   ('Memorias del Alba', 'Aldair Acosta')]),
 # Las dos que faltaban: el festival las publicó el 16 y el 17 de septiembre,
 # a una semana del arranque. Con estas son ONCE categorías, no nueve.
 ('Cortometraje Nacional', 'DdUN3Zoqwl4', '2026-09-16', [
   ('Tuktu, Padre Maíz', 'Mauricio Prieto Muriel'),
   ('Sukua', 'Omar Ospina Giraldo'),
   # La misma obra que FICMA proyecta el sáb 19 en Manizales: circula por los
   # dos festivales, y por eso su ficha se hereda sola cuando haya parrilla.
   ('Que el cielo nos perdone', 'Andrés Buitrago'),
   ('No es el Fin del Mundo', 'Sebastián Florez'),
   ('La Independencia', 'Jhon Agudelo')]),
 ('Mejor Corto Internacional', 'DdWyHp1q4MG', '2026-09-17', [
   ('Autokar', 'Sylwia Szkiłądź'),
   ('Le Jeune Sofiane', 'Fabien Ara'),
   ('Una Torreta en Llamas', 'Humberto Flores'),
   ('On Hold', 'Krishna Kumar Shukla'),
   ('Alivios', 'Juan Manuel Gonzalez Fernandez')]),
]

# EL TÍTULO QUE EL FESTIVAL ESCRIBIÓ MAL. «Withch» no es una grafía: es una
# errata del pie. La obra se llama «Witch and Frog» —así la registra su propia
# directora, Anastasia Provotorova, en TMDB (1772239)— y con la errata no la
# encuentra nadie, ni nosotros ni quien la busque en la app.
TITULO_OFICIAL = {'Withch and Frog': 'Witch and Frog'}

# El festival escribe algunos apellidos en VERSALES («Sylwia SZKIŁĄDŹ»), que es
# una convención de créditos, no la forma del nombre. Se escribe como se escribe
# un nombre; queda dicho acá para que no parezca una transcripción descuidada.
VERSALES = {'Sylwia Szkiłądź': 'la fuente lo escribe «Sylwia SZKIŁĄDŹ»'}

obras = []
cats = {}
for nombre, sc, fecha, lista in CATS:
    cats[nombre] = {'reel': BASE + sc + '/', 'publicado': fecha, 'obras': len(lista)}
    for t, d in lista:
        o = {'titulo': TITULO_OFICIAL.get(t, t), 'director': d,
             'seccion': 'Selección Oficial', 'categoria': nombre,
             '_src': {'url': BASE + sc + '/', 'date': fecha}}
        if t in TITULO_OFICIAL:
            o['_titulo_publicado'] = t
        obras.append(o)

out = {
 '_provenance': {
   'fuente': 'Instagram del festival (@festivalvilladelcine) — los once reels de Selección Oficial, uno por categoría',
   'capturado': '2026-09-17',
   'metodo': 'TRANSCRIPCIÓN DEL PIE, no lectura de lámina: este festival escribe «🎬 Título – Dir. Nombre» en el texto del post. El pie se leyó por el embed, entero, sin truncar. No hizo falta la doble lectura que sí exigió Jardín.',
   'alcance': 'SOLO la Selección Oficial en competencia. NO hay una sola función con día, hora ni sede: a 6 días del arranque el festival no ha publicado parrilla.',
   'versales': VERSALES,
   'titulo_corregido': TITULO_OFICIAL},
 '_festival': {
   'nombre': 'Festival Villa del Cine', 'edicion': 12,
   'ciudad': 'Villa de Leyva, Boyacá',
   'fechas': '23–26 de septiembre de 2026',
   'concepto': 'Caminos del Tiempo',
   'web': 'https://villadelcine.com/',
   'ig': 'https://www.instagram.com/festivalvilladelcine/',
   'radar': '#570'},
 '_trampas': [
   'La página «Selección Oficial 2026» de villadelcine.com apunta a /festival-2024-2/ y su CONTENIDO es de 2024: encabezado nuevo sobre documento viejo. No sirve como fuente y lista categorías que no son las de esta edición.',
   'El radar contó 7 categorías el 13 sep y son 8 a esa fecha: se le pasó «Mejor VR» (3 obras, 11 sep). Al contar categorías de este festival hay que enumerar los reels, no fiarse del acumulado anterior. Volvió a pasar: el 16 y el 17 aparecieron dos categorías más (Cortometraje Nacional y Mejor Corto Internacional). Mientras el festival siga publicando, este catálogo se re-cuenta cada día.',
   'El botón PROGRAMACIÓN de villadelcine.com enlaza un PDF de 2023 (Programafvdc23_compressed-1.pdf). Es la TERCERA capa de contenido viejo bajo encabezado nuevo, con la selección de 2024 y las fechas de 2026. Ninguna corrida debe transcribirlo.',
   'Hay categorías que NO son cine proyectable en sala de la manera habitual: «Mejor VR» (3 obras) y «Mejor Cortometraje Vertical» (5). Antes de montar hay que preguntar cómo se exhiben.',
   'CLAQUETAZO es un laboratorio de creación (3 equipos, filminutos), no una sección de la selección: no entra al catálogo.'],
 '_categorias': cats,
 'obras': obras}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = REPO + '/festivals/staging/villadelcine-2026-seleccion-oficial.json'
json.dump(out, open(D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(obras)} obras · {len(cats)} categorías → {D.split("/")[-1]}')
