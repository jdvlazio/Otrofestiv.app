#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-crudo.py — la parrilla y las obras, en el formato intermedio.

JUNTA LAS TRES FUENTES ya verificadas:
  · `-parrilla.json`   — los 53 bloques con día, hora, fin y sede (del PDF).
  · `-obras-pdf.json`  — las 92 obras con su programa y sinopsis en español.
  · `-obras-web.json`  — las 81 fichas de la web: sinopsis en inglés, afiche,
    Instagram, y la duración de las que el PDF dejó sin ella.

CADA BLOQUE CON NOMBRE DE PROGRAMA ES UNA FUNCIÓN, no seis: el festival le puso
nombre al conjunto («Nuevas Miradas: UMBRALES») y agrupó sus fichas debajo, así
que va como programa de cortos con su lista de obras. Los largos y las
ceremonias van sueltos, que es como el propio PDF los nombra.

════════════════════════════════════════════════════════════════════════════
«UN POETA» VA CON 120 MINUTOS, no con los 123 de TMDB: el festival y
FilmAffinity coinciden en 120 y son dos fuentes contra una (Juan, 19 sep 2026).
Sigue sin caber en su casilla de 105, que es lo que importa para el horario.

LA DURACIÓN QUE SE PUBLICA ES LA REAL, NO LA DIBUJADA. Regla de Juan, 19 sep
2026, y vale para todo festival: cuando las obras de un bloque suman más de lo
que mide su casilla en la retícula, MANDA LA SUMA.

Los festivales dibujan la parrilla en casillas redondas y no siempre cuadran
los minutos: «Territorios RAÍCES» ocupa una casilla de 60 minutos y sus cuatro
obras suman 79. Si publicáramos los 60, la app diría que termina a las 12:45 y
alguien pondría algo a las 13:00 sin ver el choque — que es exactamente el
trabajo que la app existe para hacer. Publicar de menos no es prudente: es
esconder un conflicto real.

Queda `_duracion_dibujada` con lo que decía la casilla, para poder explicarlo.
════════════════════════════════════════════════════════════════════════════

Esc.  festivals/staging/villadelcine-2026-crudo.json
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OUT = f'{ST}/villadelcine-2026-crudo.json'
PLAN = f'{REPO}/pipeline/villadelcine-2026.plan.json'

# Bloques que NO son proyección: ceremonias, laboratorios, charlas y entrevistas.
# El rótulo con que el festival los nombra manda; acá solo se dice de qué tipo
# son para que la app no los trate como una película.
#
# La sección va con su nombre LIMPIO: el emoji lo pone el plan, que es su dueño
# único. Escribirlo acá dejaba «🎉 Eventos Especiales» sin pareja en el mapa de
# secciones y el ensamblador —con razón— se negaba a adivinar.
# El TERCER valor es el `event_kind`, y es el que de verdad importa: el
# ensamblador deriva `type:'event'` de él y no de `tipo`. Sin ponerlo, las 24
# actividades salían publicadas como PELÍCULAS —ceremonias y talleres en el
# planificador como si fueran proyecciones, y la cobertura de pósters contando
# el Claquetazo—. Los valores son los del vocabulario que ya usa la app
# ([event-kind-conocido] los vigila), no inventados.
ACTIVIDAD = [
    (r'dirigir el tiempo', 'taller', 'Ruta Académica', 'masterclass'),
    (r'gente que hace cine|trazos|restauraci[oó]n', 'charla', 'Ruta Académica', 'charla'),
    (r'club de pitch|estaci[oó]n ig', 'taller', 'Ruta Académica', 'encuentro'),
    (r'ruta acad[eé]mica|claquetazo|del collage|transformaci',
     'taller', 'Ruta Académica', 'taller'),
    (r'comunicaciones|entre\s*vistas', 'charla', 'Comunicaciones', 'charla'),
    (r'ceremonia unquy|apertura', 'evento', 'Eventos Especiales', 'apertura'),
    (r'tamsa|premiaci[oó]n|clausura', 'evento', 'Eventos Especiales', 'awards'),
    (r'reconocimiento|tributo', 'evento', 'Eventos Especiales', 'encuentro'),
    (r'muestra especial: *festival de cine|eureka', 'evento', 'Eventos Especiales',
     'experiencia'),
]


# SIN SECCIÓN EN NINGUNA FUENTE. «El fósil mágico» está en la retícula del
# sábado y en ningún otro lado: no tiene página de ficha en el PDF, ni página
# en la web, ni figura en la Selección Oficial de Instagram. El festival la
# programó sin catalogarla, así que la sección no existe y no se deduce.
#
# Se publica —está anunciada, con día, hora y sede— dentro de la secuencia de
# cierre de Casa San Pedro, que es donde cae: a las 15:45, entre el CLAQUETAZO
# y el tributo a Aquileo Venganza. Es un SUPUESTO nuestro, va marcado como tal
# y está en la lista de preguntas al festival.
# EL NOMBRE DE UNA ACTIVIDAD SALE DE SU FICHA, NO DE LA CELDA. La celda de la
# retícula amontona el rótulo de la franja, el nombre y el formato («Ruta
# Académica CineCamino DEL COLLAGE AL PÓSTER Creación de Afiches Para Cine
# Taller EUREKA»). Las páginas 51–60 del PDF traen la ficha de cada actividad
# con su nombre propio, que es como el festival la llama.
#
# La caja se escribe a mano por la misma razón que los títulos de obra: el PDF
# los imprime en mayúscula sostenida y ninguna regla automática sabe dónde va
# un nombre propio.
NOMBRE_ACTIVIDAD = [
    ('club de pitch',        'Club de Pitch — Encuentro Work in Progress'),
    ('estaci',               'Estación Igüaque'),
    ('del collage',          'Taller Eureka — Del collage al póster'),
    ('gente que hace cine',  'Gente que hace cine'),
    ('dirigir el tiempo',    'Dirigir el tiempo'),
    ('transformaci',         'Maquillaje: transformaciones del tiempo'),
    ('trazos',               'Trazos — Charla con realizadores'),
    ('restauraci',           'Proceso de restauración de La paga y Aquileo Venganza'),
    ('podcast',              'Universos expandidos con el podcast'),
    ('claquetazo - inicio',  'Claquetazo — Laboratorio de creación (inicio)'),
    ('claquetazo - cierre',  'Claquetazo — Laboratorio de creación (cierre)'),
    ('claquetazo',           'Claquetazo — Laboratorio de creación'),
    ('entre vistas',         'Entre-Vistas — Entrevistas a seleccionados'),
    ('eureka',               'Muestra especial: Festival de Cine Eureka'),
    ('ceremonia unquy',      'Ceremonia UNQUY de apertura y Cine Concierto Caminos Sonoros'),
    ('tamsa',                'Ceremonia TAMSA — Premiación y clausura'),
    ('tributo aquileo',      'Tributo a Aquileo Venganza — Joyce Ventura'),
    ('reconocimiento',       'Reconocimiento a Mabel Teresa Velosa'),
]

# La caja de los nombres de PROGRAMA, que el PDF imprime en mayúscula.
CAJA_PROGRAMA = {
    'BOYACÁ EN LOS CAMPOS': 'Boyacá en los campos',
    'X-PLORA CINE': 'X-Plora Cine',
}

SIN_SECCION = {}

# NO SE PUBLICA, por decisión de Juan (19 sep 2026). «El fósil mágico» aparece
# en la retícula del sábado y EN NINGUNA OTRA PARTE: sin ficha en el PDF, sin
# página en la web, sin entrada en la Selección Oficial de Instagram. No tiene
# sección, ni país, ni duración propia, ni sinopsis. Publicar una función así
# obliga a inventarle la sección para que la app pueda agruparla, y eso es
# precisamente lo que no hacemos. Queda fuera hasta que el festival la
# catalogue, y la pregunta está en la lista.
NO_PUBLICAR = {
    'el fosil magico': 'solo está en la retícula: sin ficha, sin sección y sin país '
                       'en ninguna de las cuatro fuentes. Preguntado al festival.',
}


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def tipo_de(texto):
    t = norm(texto)
    for pat, tipo, seccion, kind in ACTIVIDAD:
        if re.search(pat, t):
            return tipo, seccion, kind
    return '', '', ''


def main():
    par = json.load(open(f'{ST}/villadelcine-2026-parrilla.json', encoding='utf-8'))
    pdf = json.load(open(f'{ST}/villadelcine-2026-obras-pdf.json', encoding='utf-8'))['obras']
    web = json.load(open(f'{ST}/villadelcine-2026-obras-web.json', encoding='utf-8'))['obras']
    plan = json.load(open(PLAN, encoding='utf-8'))['festival']
    sedes, acceso = plan['sedes'], plan['acceso_por_defecto']

    # la web, por título normalizado, para rellenar duración y sinopsis en inglés
    porweb = {}
    for o in web:
        porweb[norm(o['titulo'])] = o
    ALIAS = {'tormenta en llamas': 'a burning turret', 'enemigo en el espejo': 'enemy in the mirror',
             'con la mano arriba': 'with the hand up', 'sun coffe': 'sun coffee',
             'lens': 'lens ai short film'}

    def de_web(t):
        k = norm(t)
        return porweb.get(k) or porweb.get(norm(ALIAS.get(k, ''))) or {}

    # LA CUARTA FUENTE, que estaba extraída y sin usar: los reels de Selección
    # Oficial dicen en QUÉ CATEGORÍA compite cada corto («Mejor Cortometraje
    # YoungFilm»). No es el género ni la sección: es el premio al que aspira, y
    # el festival lo anuncia obra por obra.
    ig = {}
    ig_p = f'{ST}/villadelcine-2026-seleccion-oficial.json'
    if os.path.exists(ig_p):
        for o in json.load(open(ig_p, encoding='utf-8'))['obras']:
            ig[norm(o['titulo'])] = o

    # EL AFICHE DEL FESTIVAL. El ensamblador genérico lee `poster` de cada
    # obra, así que el sidecar de pósters se aplica aquí: TMDB cubre 15 de 111
    # y el resto los publica el festival en la página de cada obra.
    pos = {}
    pos_p = f'{ST}/villadelcine-2026-posters.json'
    if os.path.exists(pos_p):
        for t, v in json.load(open(pos_p, encoding='utf-8'))['posters'].items():
            pos[norm(t)] = v

    # TMDB, para el hueco que ni el PDF ni la web llenan
    tm = {}
    enr_p = f'{ST}/villadelcine-2026-enriquecido.json'
    if os.path.exists(enr_p):
        for o in json.load(open(enr_p, encoding='utf-8')).get('obras', []):
            tm[norm(o['titulo'])] = o

    def ficha(o):
        """Los datos de una obra, de la fuente que los tenga. ORDEN: el PDF
        oficial primero, después la web del festival, después TMDB. Nunca se
        mezcla dentro de un campo: cada uno viene entero de una fuente."""
        k = norm(o['titulo'])
        w, t, i = de_web(o['titulo']), tm.get(k, {}), ig.get(k, {})
        return {
            'duracion_min': o.get('duracion_min') or w.get('duracion_min')
                            or t.get('duracion_tmdb'),
            'pais': o.get('pais') or w.get('pais') or t.get('pais_tmdb') or '',
            'genero': o.get('genero') or t.get('genero') or '',
            'anio': o.get('anio') or w.get('anio') or t.get('anio_tmdb'),
            'sinopsis': o.get('sinopsis') or t.get('synopsis_es') or '',
            'sinopsis_en': w.get('sinopsis_en') or t.get('synopsis_en') or '',
            **({'categoria': i['categoria']} if i.get('categoria') else {}),
            **({'tmdb_id': t['tmdb_id']} if t.get('tmdb_id') else {}),
            **({'poster': t['poster_path'], 'posterSource': 'tmdb'}
               if t.get('poster_path') else
               {'poster': pos[k]['poster'], 'posterSource': 'oficial'}
               if k in pos else {}),
            **({'lbSlug': t['lbSlug']} if t.get('lbSlug') else {}),
        }

    # las obras, agrupadas por programa
    porprog = {}
    for o in pdf:
        k = norm(o['programa']) or norm(o['seccion'])
        porprog.setdefault(k, []).append(o)

    funciones, avisos = [], []
    for b in sorted(par['bloques'], key=lambda b: (b['dia'], b['hora'], b['sede'])):
        texto = ' '.join(b['lineas'])
        sede_cruda = b['sede']
        if sede_cruda not in sedes:
            avisos.append(f'sede sin tabla: «{sede_cruda}»')
            continue
        fuera = next((v for k, v in NO_PUBLICAR.items() if k in norm(texto)), '')
        if fuera:
            avisos.append(f'{b["dia"][-2:]} {b["hora"]} «{texto[:34]}» NO se publica: {fuera}')
            continue
        sede, sala = sedes[sede_cruda]
        tipo, sec_act, kind = tipo_de(texto)

        # ¿UNA OBRA O UN PROGRAMA? Primero lo primero: si la celda nombra una
        # obra concreta —«ARENAS, Dir. John Bolívar Acosta»— es UNA función,
        # y el nombre del programa que aparece debajo es solo su sección. Al
        # revés, buscando antes el programa, la inauguración del miércoles se
        # llevaba las cuatro obras de BOYACÁ EN LOS CAMPOS y pasaba de 15 a 49
        # minutos: el festival proyecta ahí un corto, no el programa entero.
        m = re.match(r'^\s*(.+?)[,.]?\s*Dir[.,]', texto, re.I)
        obras, clave, solo_web = [], '', {}
        if m:
            t = norm(m.group(1))
            obras = [o for o in pdf if norm(o['titulo']) == t] \
                or [o for o in pdf if t and t in norm(o['titulo'])]
            obras = obras[:1]
            # ARENAS abre el miércoles y NO tiene página de ficha en el PDF; su
            # ficha está en la web. Que el programa no la imprima no la convierte
            # en el programa entero.
            if not obras and de_web(m.group(1)):
                solo_web = de_web(m.group(1))
        # una obra nombrada dentro de la celda, aunque no lleve «Dir.»: así se
        # anuncian los dos largos de Rumbo a los Macondo, con su metraje al lado.
        if not obras and not solo_web:
            sueltas = [o for o in pdf
                       if len(norm(o['titulo'])) > 6 and norm(o['titulo']) in norm(texto)]
            obras = sueltas[:1]
        if not obras and not solo_web:
            clave = next((k for k in porprog
                          if k and len(k) > 3 and k in norm(texto)), '')
            obras = porprog.get(clave, []) if clave else []

        titulo = (solo_web['titulo'] if solo_web
                  else obras[0]['titulo'] if len(obras) == 1 and not clave
                  else (obras[0]['programa'] or obras[0]['seccion']) if obras
                  else re.sub(r'\s*/\s*', ' ', texto).strip())
        titulo = CAJA_PROGRAMA.get(titulo, titulo)
        if tipo or not obras:
            nt = norm(texto)
            for pat, nombre in NOMBRE_ACTIVIDAD:
                if pat in nt:
                    titulo = nombre
                    break
        seccion = (obras[0]['seccion'] if obras else sec_act) or sec_act
        if solo_web:
            # la sección la dice la propia celda («Nuevas Miradas: RESISTENCIAS»)
            ms = re.search(r'(Nuevas Miradas|Territorios|Narrativas Divergentes|'
                           r'Lenguajes Emergentes|Programación Infantil|Industria)', texto)
            seccion = ms.group(1) if ms else seccion
        es_programa = bool(clave) and len(obras) > 1

        # ── LA DURACIÓN REAL MANDA ───────────────────────────────────────────
        suma = (solo_web.get('duracion_min') or 0) if solo_web else sum(
            ficha(o)['duracion_min'] or 0 for o in obras)
        # el metraje que la propia celda imprime («… 2:03:00»), si lo trae
        mm = re.search(r'\b(\d):(\d{2}):(\d{2})\b', texto)
        if mm and not obras:
            suma = max(suma, int(mm.group(1)) * 60 + int(mm.group(2)))
        sin_dur = [o['titulo'] for o in obras if not ficha(o)['duracion_min']]
        # DOS DURACIONES DISTINTAS, y confundirlas cuesta caro en los dos
        # sentidos. La que se PUBLICA es el máximo entre la casilla y el
        # contenido: si el contenido se pasa, publicar la casilla esconde un
        # conflicto real (la regla de Juan); y si el contenido es más corto,
        # publicar solo la obra deja reservar algo mientras la sala sigue
        # ocupada —«Mucho Gusto» son 5 minutos en una casilla de 15—.
        #
        # La de la OBRA va aparte, en `duracion_obra`: es la que sirve para
        # VERIFICAR contra TMDB, que compara con ±3 minutos de margen. Con la
        # casilla, «Llueve sobre Babel» (113 min en una casilla de 120) no
        # verificaba y se quedaba sin ficha y sin póster.
        dur = max(b['duracion_min'], suma) if suma else b['duracion_min']
        if suma > b['duracion_min']:
            avisos.append(f'{b["dia"][-2:]} {b["hora"]} «{titulo[:34]}»: la casilla mide '
                          f'{b["duracion_min"]} min y sus obras suman {suma} — se publica '
                          f'{suma}, que es lo que de verdad dura')

        reg = {
            'titulo': titulo, 'dia': b['dia'], 'hora': b['hora'], 'sede': sede,
            **({'sala': sala} if sala else {}),
            'duracion_min': dur,
            **({'_duracion_dibujada': b['duracion_min']} if dur != b['duracion_min'] else {}),
            **({'duracion_obra': suma} if suma and not es_programa
               and suma != dur else {}),
            **({'_obras_sin_duracion': sin_dur} if sin_dur else {}),
            'seccion': seccion,
            'is_free': acceso['is_free'],
            'acceso': 'Entrada libre',
            '_acceso_por_defecto': True,
            '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                            f'p{b["pagina"]}', 'date': '2026-09-19'},
        }
        if tipo:
            reg['tipo'] = tipo
            reg['event_kind'] = kind
        if es_programa:
            reg['is_cortos'] = True
            reg['film_list'] = [{'titulo': o['titulo'], 'director': o['director'],
                                 **{k: v for k, v in ficha(o).items() if v},
                                 **({'formato': o['formato']} if o.get('formato') else {})}
                                for o in obras]
        elif solo_web:
            reg.update({
                'director': solo_web.get('director', ''),
                'pais': solo_web.get('pais', ''),
                **({'sinopsis_en': solo_web['sinopsis_en']}
                   if solo_web.get('sinopsis_en') else {}),
                '_sin_ficha_en_el_pdf': True,
            })
        elif obras:
            o = obras[0]
            reg.update({'director': o['director'],
                        **{k: v for k, v in ficha(o).items()
                           if v and k != 'duracion_min'}})
        # UNA ACTIVIDAD NO HEREDA LA FICHA DE LA OBRA QUE NOMBRA, y esto va
        # AL FINAL a propósito: la primera vez lo puse antes de las ramas de
        # arriba, que volvían a ponerle los campos, y el validador siguió
        # cazando la contaminación. El tributo a Aquileo Venganza, la charla
        # sobre su restauración y la película son tres cosas distintas; las
        # tres acababan con la misma sinopsis porque la celda menciona el
        # título.
        if tipo:
            for k in ('sinopsis', 'sinopsis_en', 'pais', 'genero', 'anio',
                      'tmdb_id', 'lbSlug', 'poster', 'posterSource', 'director',
                      'categoria'):
                reg.pop(k, None)
        funciones.append(reg)

    json.dump({'_provenance': provenance(
        'PROGRAMACIÓN «Caminos del tiempo» 2026 (PDF) + las fichas de obra de '
        'villadelcine.com',
        que_aporta='las funciones del festival con día, hora, sede, sala, sección y '
                   'la lista de obras de cada programa de cortos',
        url='https://villadelcine.com/wp-content/uploads/2026/09/'
            'Programacion-caminos-del-tiempo-2026_compressed.pdf',
        metodo='la duración publicada es la REAL: cuando las obras suman más que la '
               'casilla dibujada, manda la suma (regla de Juan, 19 sep 2026)'),
        'funciones': funciones}, open(OUT, 'w', encoding='utf-8'),
        ensure_ascii=False, indent=1)

    lib.cargar_crudo(OUT)          # el contrato, a la cara si algo falta
    prog = sum(1 for f in funciones if f.get('is_cortos'))
    act = sum(1 for f in funciones if f.get('tipo'))
    estirados = sum(1 for f in funciones if '_duracion_dibujada' in f)
    print(f'{len(funciones)} funciones · {prog} programas de cortos · {act} actividades '
          f'· {estirados} con duración real mayor que la dibujada → '
          f'{os.path.basename(OUT)}')
    for a in avisos:
        print('   ·', a)


if __name__ == '__main__':
    main()
