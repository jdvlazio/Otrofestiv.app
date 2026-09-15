# -*- coding: utf-8 -*-
"""Reconstruye festivals/ficma-2026.json con la programación de SEPTIEMBRE.

FICMA 17 se aplazó por el sismo del 10 ago y volvió del 19 al 26 de SEPTIEMBRE.
Lo publicado seguía siendo la parrilla de agosto bajo una banda de «aplazado»,
o sea 90 funciones de unas fechas que ya no existen.

POR QUÉ NO SE REMAPEA LO DE AGOSTO. Se comparó obra por obra: «El hogar fue
sepultado» pasó de mar 11 · 08:00 · All Cine a sáb 19 · 19:00 · Palogrande;
«Soñé su nombre» de mié 12 · 18:00 a sáb 19 · 14:00; «El príncipe de Nanawa» de
jue 13 · 07:30 · Los Fundadores a sáb 19 · 09:00 · Banrep. Cambian día, hora Y
sede, y además hay obras que en agosto no estaban. Un desplazamiento del
calendario habría sido barato; esto es una parrilla nueva.

QUÉ SE CONSERVA. El CATÁLOGO entero. Las fichas —póster, sinopsis, lbSlug,
género, país, año, duración, bandera— salen de lo ya publicado, que es donde
viven también las correcciones a mano. La obra es la misma; lo que cambió es
cuándo y dónde se ve.

QUÉ SE PIERDE, A PROPÓSITO. Las 81 funciones de agosto que el festival todavía
no ha vuelto a anunciar. No se reubican ni se adivinan: publicar una función en
una fecha que nadie declaró es peor que no publicarla. `publicar.py` lo va a
frenar y hay que pasarle --forzar: esa pérdida es el objetivo, no un accidente.

Lee   festivals/staging/ficma-2026-reprogramado.json      (la parrilla nueva)
      festivals/staging/ficma-2026-catalogo-agosto.json  (las 86 fichas, congeladas)
      festivals/staging/ficma-2026-venues-geo.json    (+ las 3 sedes nuevas)
Esc.  festivals/staging/ficma-2026-build.json         (lo publica publicar.py)
"""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CIUDAD = 'Manizales'

# El festival corre del 19 al 26 aunque hoy solo haya funciones en cinco de esos
# días. El rango es el que el festival declara en su web y en su bio; los días
# vacíos son la verdad —todavía no ha publicado esa parte— y no se recortan para
# que la parrilla se vea más llena de lo que está.
DIAS = [f'2026-09-{d}' for d in range(19, 27)]

# Nombre de sección TAL CUAL lo escribe el festival en cada post (regla
# permanente). Lo nuestro es solo el emoji, el inglés y el arquetipo —que no es
# etiqueta libre: es la clave del color y hay un gate que lo exige—.
SECCIONES = {
    'Función de apertura':      ('🎬 Función de apertura', 'Opening Film', 'Apertura / Gala', 1),
    'Función Inaugural':        ('✨ Función Inaugural', 'Inaugural Screening', 'Apertura / Gala', 2),
    'Estrenos Cine Colombiano': ('🇨🇴 Estrenos Cine Colombiano', 'Colombian Premieres', 'Competencia', 3),
    'Cine Colombiano':          ('🎞️ Cine Colombiano', 'Colombian Cinema', 'Muestra / País', 4),
    'Cortometrajes':            ('⚡ Cortometrajes', 'Short Films', 'Cortos / Programas', 5),
    'Cine Clásico Colombiano':  ('📽️ Cine Clásico Colombiano', 'Colombian Classics', 'Retrospectiva / Tributo', 6),
    'Talleres':                 ('🛠️ Talleres', 'Workshops', 'Charlas / Industria', 7),
}

# Sede del post → (clave canónica de venues, sala). La tabla es EXPLÍCITA, nunca
# heurística sobre el guion: es la lección más cara de FICDEH.
SEDES = {
    'Centro Cultural del Banco de la República':
        ('Centro Cultural del Banco de la República', ''),
    'Teatro Los Fundadores – Sala Olimpia':
        ('Teatro los Fundadores', 'Sala Olimpia'),
    'Casa de la Cultura de Palogrande – Calle externa':
        ('Casa de la Cultura de Palogrande', 'Calle externa'),
    'Confa de la 50 – Auditorio Hernando Aristizábal Botero':
        ('Confa de la 50', 'Auditorio Hernando Aristizábal Botero'),
    'Parque Ernesto Gutiérrez': ('Parque Ernesto Gutiérrez', ''),
    'Secretaría de Cultura de Palogrande': ('Casa de la Cultura de Palogrande', ''),
    'Hall Secretaría de la Mujer y Equidad de Género':
        ('Secretaría de la Mujer y Equidad de Género', 'Hall'),
}

# Las tres que agosto no tenía, ubicadas en Google Maps el 15 sep 2026 — cada una
# con ficha propia (/place/), no con el centro de un resultado de búsqueda. Para
# sedes de ciudades colombianas Maps manda sobre Nominatim.
GEO_NUEVAS = {
    'Centro Cultural del Banco de la República': {
        'lat': 5.0669562, 'lng': -75.5168109, '_prec': 'maps',
        '_nota': 'ficha propia en Google Maps; a ~700 m del Teatro los Fundadores'},
    'Casa de la Cultura de Palogrande': {
        'lat': 5.0575195, 'lng': -75.484585, '_prec': 'maps',
        '_nota': 'ficha «Casa de la cultura - Palogrande». El festival la nombra también «Secretaría de Cultura de Palogrande»: se unifican.'},
    'Confa de la 50': {
        'lat': 5.0625092, 'lng': -75.4989887, '_prec': 'maps',
        '_nota': 'ficha «Confa», Cra 25 Calle 50 esquina. El auditorio Hernando Aristizábal Botero está dentro.'},
}

# Conversatorio o presencia del director declarados en el post o en la web.
CON_QA = {'Soñé su nombre', 'Ayuno y cenizas', 'Que el cielo nos perdone',
          'El juego de la vida', 'El hogar fue sepultado en esa tierra que nunca pudimos encontrar'}


# el normalizador es el de lib.py: una sola casa para comparar títulos
norm = lib.norm


def main():
    rep = json.load(open(f'{ST}/ficma-2026-reprogramado.json', encoding='utf-8'))
    # La foto CONGELADA, no el JSON publicado: publicar encoge ese archivo a las
    # 11 funciones reanunciadas, y leerlo aquí haría que el segundo regenerado
    # saliera sin catálogo. Un paso que se estropea a sí mismo al usarlo.
    cat = json.load(open(f'{ST}/ficma-2026-catalogo-agosto.json', encoding='utf-8'))['obras']
    geo = json.load(open(f'{ST}/ficma-2026-venues-geo.json', encoding='utf-8'))

    # Catálogo: primero el propio FICMA publicado, y si la obra es nueva —las hay:
    # el festival reprogramó y además cambió la selección— se busca en el RESTO de
    # nuestros festivales. La coincidencia se propone por título y se CONFIRMA por
    # director: «Semillas» y «Solo» son títulos que dos obras distintas comparten
    # con facilidad, y lo que se hereda (póster, sinopsis, lbSlug) es justo lo que
    # un homónimo arruina.
    import glob
    ficha, ajenas = {}, {}
    for t, o in cat.items():
        ficha.setdefault(norm(t), o)
    for otro in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        if otro.endswith('ficma-2026.json'):
            continue
        try:
            d = json.load(open(otro, encoding='utf-8'))
        except Exception:
            continue
        for x in (d.get('films') or []):
            for o in [x] + list(x.get('film_list') or []):
                if o and o.get('title') and o.get('director'):
                    ajenas.setdefault(norm(o['title']), (os.path.basename(otro), o))

    def apellidos(d):
        return {w for w in norm(d).replace(',', ' ').split() if len(w) > 3}

    def heredar(titulo, director):
        k = norm(titulo)
        if k in ficha:
            return ficha[k], 'ficma-2026 (agosto)'
        if k in ajenas:
            fn, o = ajenas[k]
            if apellidos(director) & apellidos(o.get('director')):
                return o, fn
        return None, ''

    films, venues, sin_ficha = [], {}, []
    for fn in rep['funciones']:
        es_taller = fn.get('tipo') == 'taller'
        sec_src = 'Talleres' if es_taller else fn['seccion']
        sec = SECCIONES[sec_src][0]
        sede_src = fn['sede']
        if not sede_src:
            # «Franja con colegios» sin sede declarada. No se inventa: la función
            # no entra, y queda dicho. Entrará cuando el festival la publique.
            sin_ficha.append(f"{fn['titulo']} — SIN SEDE declarada, no se publica")
            continue
        clave_sede, sala = SEDES[sede_src]
        k = f'{clave_sede} - {CIUDAD}'
        if k not in venues:
            g = geo.get(clave_sede) or GEO_NUEVAS.get(clave_sede) or {}
            venues[k] = {'short': clave_sede, 'lat': g.get('lat'), 'lng': g.get('lng'),
                         'city': CIUDAD, 'address': g.get('address', '')}
            if g.get('_prec'):
                venues[k]['_prec'] = g['_prec']
            if g.get('_nota'):
                venues[k]['_nota'] = g['_nota']

        base, de_donde = heredar(fn['titulo'], fn.get('director', ''))
        if base is None and not es_taller:
            sin_ficha.append(fn['titulo'])
        b = dict(base or {})
        # Lo que el PROPIO festival publica sobre esta edición manda sobre la
        # ficha heredada: es su obra y su texto, y puede haber cambiado de corte.
        for k_, k2 in (('anio', 'year'), ('pais', 'country')):
            if fn.get(k_):
                b[k2] = fn[k_]
        if fn.get('duracion_min'):
            b['duration'] = f"{fn['duracion_min']} min"
        if fn.get('sinopsis'):
            # sinopsis del propio festival: es española y así se declara, que el
            # contrato exige el idioma y la app lo lee para no ofrecer traducción
            b['synopsis'], b['synopsis_lang'] = fn['sinopsis'], 'es'
        if fn.get('pais') and not b.get('flags'):
            b['flags'] = lib.banderas(fn['pais'])
        item = {
            'title': fn['titulo'],
            'director': fn.get('director') or fn.get('tallerista') or '',
            'year': b.get('year'), 'duration': b.get('duration'),
            'country': b.get('country', ''), 'flags': b.get('flags', ''),
            'section': sec, 'day': fn['dia'], 'time': fn['hora'],
            # índice del día en la grilla, que el contrato exige derivado de `day`
            'day_order': DIAS.index(fn['dia']),
            'venue': k, 'has_qa': fn['titulo'] in CON_QA,
            # «Todas las actividades son de acceso libre», dicho por el festival
            # en laficma.com. La casilla de acceso no puede quedar muda: lo pide
            # [boleteria-muda] y es de lo primero que mira quien va a ir.
            'is_free': True,
            '_src': f"{fn['_src']['url']} ({fn['_src']['date']})",
        }
        if de_donde and de_donde != 'ficma-2026 (agosto)':
            item['_ficha_heredada_de'] = de_donde
        if sala:
            item['sala'] = sala
        for campo in ('tmdb_id', 'genre', 'poster', 'posterSource', 'synopsis',
                      'synopsis_en', 'synopsis_lang', 'lbSlug', 'title_en'):
            if b.get(campo):
                item[campo] = b[campo]
        if es_taller:
            item['event_kind'] = 'taller'
            item['duration'] = item['duration'] or '180 min'
        films.append(item)

    films.sort(key=lambda f: (f['day'], f['time'], f['title']))
    secs = {v[0]: {'en': v[1], 'archetype': v[2], 'order': v[3]}
            for k, v in SECCIONES.items()
            if any(f['section'] == v[0] for f in films)}

    out = {
        '_provenance': {
            'programacion': 'laficma.com (/estrenosficma17/, /talleresficma17/) + Instagram '
                            '@cinemanizales_ficma, post a post — el festival NO ha publicado parrilla completa',
            'catalogo': 'heredado de festivals/ficma-2026.json (la edición de agosto): la obra es '
                        'la misma, solo cambió cuándo y dónde se ve',
            'sedes': 'las de agosto + 3 nuevas ubicadas en Google Maps el 15 sep 2026',
            'acceso': 'Todas las actividades son de acceso libre (declarado en laficma.com)',
            'capturado': '2026-09-15',
            'reprogramacion': 'aplazado el 10 ago por el sismo de Manizales; vuelve 19–26 SEP. '
                              'La parrilla de agosto NO se remapea (día, hora y sede cambian).',
        },
        'name': 'FICMA', 'shortName': 'FICMA',
        'fullName': 'Feria Internacional de Cine de Manizales',
        'city': CIUDAD, 'country': 'CO',
        'dates': '19–26 SEP', 'dates_en': 'SEP 19–26', 'year': 2026,
        'timezoneOffset': '-05:00', 'storageKey': 'ficma2026_',
        'festivalStartStr': f'{DIAS[0]}T00:00:00', 'festivalEndStr': f'{DIAS[-1]}T23:59:00',
        'prioLimit': 4,
        'ticketing_model': 'free',
        # Los dos pases del sábado 19 a las 19:00 en Palogrande son UNA función:
        # «Que el cielo nos perdone» (16 min) va antes de «El hogar fue sepultado»
        # (90 min), en la misma calle externa. El festival los anunció por
        # separado porque son dos posts, no dos entradas.
        'sharedSlotIsOneScreening': True,
        **lib.dias_config(DIAS, 'septiembre'),
        'sections': secs, 'venues': venues, 'films': films,
    }
    json.dump(out, open(f'{ST}/ficma-2026-build.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    dias_con = sorted({f['day'] for f in films})
    print(f'{len(films)} funciones · {len(venues)} sedes · {len(secs)} secciones')
    print(f'días declarados {len(DIAS)} ({DIAS[0]}…{DIAS[-1]}) · con función {len(dias_con)}: '
          + ', '.join(d[-2:] for d in dias_con))
    print(f'con póster {sum(1 for f in films if f.get("poster"))} · '
          f'con sinopsis {sum(1 for f in films if f.get("synopsis"))} · '
          f'con lbSlug {sum(1 for f in films if f.get("lbSlug"))}')
    if sin_ficha:
        print('sin ficha heredada o sin sede:')
        for s in sin_ficha:
            print('   ·', s)


if __name__ == '__main__':
    main()
