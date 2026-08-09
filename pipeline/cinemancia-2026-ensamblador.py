# -*- coding: utf-8 -*-
"""Los cuatro sidecars → `festivals/staging/cinemancia-2026-build.json`.

ENTRADAS, y quién manda sobre qué:

  · listado (PDF oficial) — la LISTA de obras y su sección. Manda en título,
    director, país, año y duración. Es la única fuente completa: 109 obras.
  · web (fichas del festival) — manda en SINOPSIS (es la del festival, no una
    traducción) y es la ÚNICA fuente de programación: día, hora, sede, sala.
  · tmdb — rellena la sinopsis que la web no publica, y aporta póster.
  · lb — lbSlug y title_en.

REGLA DE PRECEDENCIA para la sinopsis: web > TMDB. La del festival describe la
obra como ellos la programan; la de TMDB es genérica. Nunca se traduce: sin
sinopsis en español el campo va vacío y se le pide al festival.

films[] ES UNA LISTA DE FUNCIONES, no de obras: una obra con dos pases produce
dos entradas. Las 53 obras que aún no tienen horario NO entran —no se puede
inventar día ni sede— y salen listadas en el reporte.

SEDE Y SALA: la web las publica pegadas («Centro Colombo Americano - Sede
centro - Sala 1») y con el mismo lugar escrito de varias formas. La tabla SEDES
de abajo es EXPLÍCITA y no un regex, que es la lección más cara de FICDEH: ahí
la misma «Sala 2» escrita de dos maneras partió tres funciones reales en seis.
Con 14 textos distintos que son 11 sedes, aquí habría pasado igual:

    «Biblioteca Comfama Bello - Centro»            ┐ la misma
    «Biblioteca Comfama Bello Centro»              ┘
    «Centro Colombo Americano - Sede centro - Sala 2»  ┐ la misma
    «Colombo Americano - Sede centro - Sala 2»         ┘

Toda entrada nueva que no esté en la tabla DETIENE el ensamblado: es preferible
un error a la cara que una sede duplicada en silencio.
"""
import json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OUT = f'{ST}/cinemancia-2026-build.json'
CIUDAD_DEF = 'Valle de Aburrá'
DIAS = [f'2026-09-{d:02d}' for d in range(3, 13)]        # 3–12 SEP, sexta edición

# texto de la web → (sede canónica, sala). Explícita a propósito: ver el
# docstring. La sala vacía significa «la sede no distingue salas».
SEDES = {
    'Antimateria Libros y Café':                    ('Antimateria Libros y Café', ''),
    'Biblioteca Comfama Bello - Centro':            ('Biblioteca Comfama Bello Centro', ''),
    'Biblioteca Comfama Bello Centro':              ('Biblioteca Comfama Bello Centro', ''),
    'Casa Municipal de la Cultura':                 ('Casa Municipal de la Cultura', ''),
    'Casa Museo Otraparte':                         ('Casa Museo Otraparte', ''),
    'Centro Colombo Americano - Sede centro - Sala 1': ('Centro Colombo Americano - Sede centro', 'Sala 1'),
    'Centro Colombo Americano - Sede centro - Sala 2': ('Centro Colombo Americano - Sede centro', 'Sala 2'),
    'Colombo Americano - Sede centro - Sala 2':     ('Centro Colombo Americano - Sede centro', 'Sala 2'),
    'Cine MAMM':                                    ('Cine MAMM', ''),
    'Cineprox Las Américas':                        ('Cineprox Las Américas', ''),
    'ITM – Facultad de Artes y Humanidades (Sede La Floresta)':
                                                    ('ITM - Facultad de Artes y Humanidades', ''),
    'La Capilla del Claustro Comfama':              ('La Capilla del Claustro Comfama', ''),
    'Teatro Caribe':                                ('Teatro Caribe', ''),
    'Terko':                                        ('Terko', ''),
}
MES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
       'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11,
       'diciembre': 12}

# Sección del PDF → (emoji, arquetipo, etiqueta EN). Aprobado por Juan el 9 ago
# 2026. El nombre ES va VERBATIM del festival (regla «secciones tal cual»);
# nuestra capa es solo el emoji, el arquetipo —que decide el color— y el EN.
#
# Las cinco primeras heredan emoji y arquetipo de Cinemancia 2025, que ya está
# en SECTION_ARCHETYPES: así el festival no cambia de color entre ediciones.
# Incluida una decisión de 2025 que se respeta a propósito: «Iluminaciones» va
# como Perspectivas / Miradas y no como Retrospectiva, aunque en 2026 sea la
# sección de restauraciones.
#
# El orden es el del PDF, que es la curaduría del festival.
SECCIONES = [
    ('Función inaugural',                    '⭐',  'Apertura / Gala',         'Opening Film'),
    ('Función de clausura',                  '🎬',  'Clausura',                'Closing Film'),
    ('Competencia central',                  '🏆',  'Competencia',             'Main Competition'),
    ('Competencia de cortometrajes',         '🎞️',  'Competencia',             'Short Film Competition'),
    ('Programa 1. El espesor de las formas', '🔺',  'Cortos / Programas',      'Programme 1. The Thickness of Forms'),
    ('Programa 2. Teoremas sobre la mirada', '👁️',  'Cortos / Programas',      'Programme 2. Theorems on the Gaze'),
    ('Competencia Nuevas voces',             '🌱',  'Competencia',             'New Voices Competition'),
    ('Proyecciones especiales',              '✨',  'Especiales / Eventos',    'Special Screenings'),
    ('Iluminaciones',                        '💡',  'Perspectivas / Miradas',  'Illuminations'),
    ('Alquimia de la luz. El cine de Luciana Decker', '⚗️', 'Retrospectiva / Tributo',
     'Alchemy of Light. The Cinema of Luciana Decker'),
    ('Carta blanca',                         '🃏',  'Perspectivas / Miradas',  'Carte Blanche'),
    ('La primavera llega para los que esperan. El cine de José Luis Torres Leiva', '🌷',
     'Retrospectiva / Tributo', 'Spring Comes for Those Who Wait. The Cinema of José Luis Torres Leiva'),
    ('Febril incisión. El cine de Thomas Fürhapter', '🌡️', 'Retrospectiva / Tributo',
     'Feverish Incision. The Cinema of Thomas Fürhapter'),
    ('Sick and Dirty. Curaduría de Michael Koresky', '🖤', 'Perspectivas / Miradas',
     'Sick and Dirty. Curated by Michael Koresky'),
    ('La sutil materia. Sergio Navarro',     '📼',  'Retrospectiva / Tributo', 'The Subtle Matter. Sergio Navarro'),
    ('Historia(s) del cine: Argentina. Curaduría de José Miccio', '🇦🇷', 'Muestra / País',
     'Histoire(s) of Cinema: Argentina. Curated by José Miccio'),
]
# Única excepción a «tal cual», decidida por Juan el 9 ago 2026: el PDF de este
# año escribe dos secciones en minúscula que en 2025 iban en Title Case. Se
# muestran como en 2025 —«se ve mucho más título de sección»— y de paso vuelven
# a ser exactamente la misma clave del mapa, o sea herencia real y no una
# entrada nueva. El PDF sigue siendo la fuente: esto es solo cómo se rotula.
ROTULO = {
    'Competencia Nuevas voces': 'Competencia Nuevas Voces',
    'Proyecciones especiales':  'Proyecciones Especiales',
}
SEC = {s: (f'{e} {ROTULO.get(s, s)}', a, en, ROTULO.get(s, s))
       for s, e, a, en in SECCIONES}


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def carga(nombre):
    return json.load(open(f'{ST}/cinemancia-2026-{nombre}.json', encoding='utf-8'))['obras']


def fecha_iso(txt):
    """«Jueves 10 de septiembre» → 2026-09-10. El día de la semana que trae la
    ficha se VERIFICA contra el calendario: es lo que probó que las fechas son
    de 2026 y no de la edición anterior (en 2025 el 10 de septiembre era
    miércoles). Si no cuadra, se detiene."""
    import datetime
    m = re.search(r'(\w+)\s+(\d{1,2})\s+de\s+(\w+)', txt, re.U)
    if not m:
        return None, f'fecha ilegible: {txt!r}'
    dsem, dia, mes = m.group(1), int(m.group(2)), m.group(3).lower()
    if mes not in MES:
        return None, f'mes desconocido: {txt!r}'
    f = datetime.date(2026, MES[mes], dia)
    esperado = ['lunes', 'martes', 'miercoles', 'jueves',
                'viernes', 'sabado', 'domingo'][f.weekday()]
    if norm(dsem) != esperado:
        return None, f'{txt!r}: en 2026 el {dia}/{MES[mes]} es {esperado}'
    return f.isoformat(), None


def main():
    listado, web, tmdb, lb = (carga(x) for x in ('listado', 'web', 'tmdb', 'lb'))
    T = {norm(o['title']): o for o in tmdb}
    L = {norm(o['title']): o for o in lb}

    # ficha web ↔ obra del PDF: por título, probando cada mitad de «A / B»
    W = {}
    for o in web:
        W[norm(o['title_web'])] = o
    def ficha(t):
        cands = [norm(t)] + [norm(x.strip()) for x in t.split('/')]
        for c in cands:
            if c in W:
                return W[c]
        # Respaldo por título contenido, con dos candados. Sin ellos, la obra
        # que se llama «O» —una sola letra— casaba dentro de «medellin yo te
        # saludo» y esa ficha quedaba asignada a dos obras distintas, con dos
        # funciones fantasma. Se exige longitud mínima y límite de palabra.
        for c in cands:
            if len(c) < 10:
                continue
            for k, v in W.items():
                if re.search(rf'\b{re.escape(c)}\b', k) or re.search(rf'\b{re.escape(k)}\b', c):
                    return v
        return None

    films, sin_horario, errores = [], [], []
    venues, secciones, usada = {}, {}, {}
    for o in listado:
        t = T.get(norm(o['title']), {})
        l = L.get(norm(o['title']), {})
        w = ficha(o['title'])
        if o['section'] not in SEC:
            errores.append(f'sección sin arquetipo: {o["section"]!r}'); continue
        clave_sec, _arq, _en, _rot = SEC[o['section']]
        secciones.setdefault(clave_sec, 0)

        # sinopsis: la del festival manda; TMDB rellena. Nunca se traduce.
        sin_es = (w or {}).get('synopsis_web') or t.get('synopsis') or ''
        fuente_sin = ('web del festival' if (w or {}).get('synopsis_web')
                      else ('TMDB' if t.get('synopsis') else ''))

        base = {
            'title': o['title'], 'title_en': l.get('title_en') or t.get('title_en') or '',
            'director': o['director'], 'year': str(o['year'] or ''),
            'duration': f'{o["duration"]} min' if o['duration'] else '',
            'country': o['country'], 'flags': lib.banderas(o['country']),
            'section': clave_sec,
            'synopsis': sin_es, 'synopsis_lang': 'es' if sin_es else '',
            'synopsis_en': t.get('synopsis_en') or '',
            'poster': f'https://image.tmdb.org/t/p/w500{t["poster_tmdb"]}'
                      if t.get('poster_tmdb') else '',
            'posterSource': 'tmdb' if t.get('poster_tmdb') else '',
            'lbSlug': l.get('lbSlug') or '', 'tmdbId': t.get('tmdbId') or None,
            # entrada libre con preinscripción en toda la edición (anuncio oficial)
            'is_free': True, 'requires_registration': True,
            'is_cortos': False, 'film_list': [],
            '_src': ('PDF oficial del listado'
                     + (f'; sinopsis de {fuente_sin}' if fuente_sin else '; SIN sinopsis')),
        }
        if not w or not w['horarios']:
            sin_horario.append(o)
            continue
        # Una ficha pertenece a UNA obra. Si dos obras reclaman la misma, el
        # emparejamiento está mal y las funciones se duplicarían en silencio
        # — pasó con la obra «O», que casaba dentro de otro título.
        if w['slug'] in usada:
            errores.append(f'ficha «{w["slug"]}» reclamada por «{usada[w["slug"]]}» '
                           f'y por «{o["title"]}»')
            continue
        usada[w['slug']] = o['title']
        for h in w['horarios']:
            dia, err = fecha_iso(h['dia_txt'])
            if err:
                errores.append(err); continue
            if h['sede_txt'] not in SEDES:
                errores.append(f'sede fuera de la tabla: {h["sede_txt"]!r}'); continue
            sede, sala = SEDES[h['sede_txt']]
            clave = f'{sede} - {h["ciudad"]}'
            venues.setdefault(clave, {'short': sede, 'city': h['ciudad'],
                                      'lat': None, 'lng': None, 'address': ''})
            films.append({**base, 'day': dia, 'time': h['hora'],
                          'day_order': DIAS.index(dia), 'venue': clave,
                          'sala': sala})
            secciones[clave_sec] += 1

    if errores:
        print('ERRORES — el ensamblado se detiene:')
        for e in sorted(set(errores)):
            print(f'   ✗ {e}')
        sys.exit(1)

    d = {'id': 'cinemancia2026', 'name': 'Cinemancia 2026',
         'city': CIUDAD_DEF, 'country': 'CO', 'year': 2026,
         'timezoneOffset': '-05:00',
         'dates': '3–12 SEP', 'dates_en': 'SEP 3–12',
         'storageKey': 'cinemancia2026_',
         # Cinemancia programa varias obras en UNA función: 89 filas son 41
         # proyecciones reales, y el propio festival anuncia 77 proyecciones
         # para 109 obras. La evidencia de que el agrupamiento es real y no un
         # artefacto: de los 21 bloques con más de una obra, NINGUNO mezcla
         # secciones, y las secciones grandes se parten en programas parejos
         # (Nuevas voces = 2 programas de 5, cada uno repetido en dos ciudades).
         # El loader ancla por día|hora|sede|sala: no rivalizan entre sí, la
         # sala se ocupa por la suma y el Q&A cuenta una sola vez.
         'sharedSlotIsOneScreening': True,
         'festivalStartStr': '2026-09-03T00:00:00',
         'festivalEndStr': '2026-09-12T23:59:00',
         **lib.dias_config(DIAS, 'septiembre'),
         '_provenance': lib.provenance(
             'PDF oficial (obras y secciones) + fichas de la web (sinopsis y horarios) + TMDB',
             precedencia='sinopsis: web del festival > TMDB; nunca traducida',
             pendiente=f'{len(sin_horario)} obras sin horario publicado'),
         'sections': {SEC[s][0]: {'oficial': SEC[s][3], 'en': SEC[s][2],
                                  'archetype': SEC[s][1], 'order': i + 1}
                      for i, (s, *_ ) in enumerate(SECCIONES)},
         'venues': venues, 'films': films}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{OUT.split("/")[-1]}  ·  {len(films)} funciones de '
          f'{len(listado) - len(sin_horario)} obras · {len(venues)} sedes')
    print(f'   sinopsis: {sum(1 for f in films if f["synopsis"])}/{len(films)} funciones · '
          f'póster: {sum(1 for f in films if f["poster"])}/{len(films)}')
    print(f'\n   {len(sin_horario)} obras SIN horario publicado (no entran):')
    import collections
    for s, n in collections.Counter(o['section'] for o in sin_horario).most_common():
        print(f'      {n:3}  {s}')
    print('\n   secciones CON funciones (falta arquetipo y emoji, decisión de Juan):')
    for s, n in secciones.items():
        if n:
            print(f'      {n:3}  {s}')


if __name__ == '__main__':
    main()
