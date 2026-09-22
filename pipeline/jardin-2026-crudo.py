#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-crudo.py — lo que el 11° Festival de Cine de Jardín SÍ fechó.

A CUATRO DÍAS DEL FESTIVAL HAY UNA SOLA FUNCIÓN CON DÍA, HORA Y SEDE: la
inaugural. El catálogo tiene 37 obras con ficha completa desde el 15 de
septiembre y ninguna otra tiene cuándo ni dónde. Este paso NO rellena ese hueco:
publica la que existe y deja las otras 36 contadas, con su razón, en
`_sin_funcion`. Sin día, hora y sede no se publica una función — la regla es
vieja y es de las que no se negocian.

DE DÓNDE SALE CADA CAMPO. Del catálogo de la web sale la ficha de la obra
(país, idioma, género, duración, sinopsis, año, dirección), porque está escrita
a máquina por el festival. De la lámina de Instagram salen el día, la hora, la
sede y el «Estreno mundial» — que la web no publica en ninguna parte. Donde las
dos hablan y no coinciden manda la web, y la discrepancia va declarada en
`jardin-2026-contraste.py`, no resuelta en silencio aquí.

LA CASILLA DE ACCESO LA DECIDIÓ JUAN, y por eso la palabra la pone el PLAN y no
este script. Ninguna fuente del festival dice en esta edición si se entra
gratis: lo dice un tercero en Instagram y lo decía la página de la primera
edición, de 2016. Juan lo zanjó el 20 sep —«Entrada libre, siempre. A todas las
funciones»— y en `acceso_por_defecto._por_que` queda escrito que la decisión es
suya, no un dato que hayamos leído. Si el festival lo desmiente se cambia allí,
en un sitio, y se re-corre.

Lee   festivals/staging/jardin-2026-catalogo.json
      festivals/staging/jardin-2026-ig.json
      festivals/staging/jardin-2026-posters.json
Esc.  festivals/staging/jardin-2026-crudo.json
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PLAN = f'{REPO}/pipeline/jardin-2026.plan.json'
CAT = f'{ST}/jardin-2026-catalogo.json'
IG = f'{ST}/jardin-2026-ig.json'
PARR = f'{ST}/jardin-2026-parrilla.json'

# EL NOMBRE DE LA SEDE EN LA PARRILLA Y EN EL PLAN. La retícula imprime «Casa
# de la cultura» y el plan la declara «Casa de la Cultura»; son la misma y el
# geocodificador solo conoce la del plan.
# DONDE LA PARRILLA GANA A LA FICHA, declarado en el verificador a tres bandas:
# «Alma provinciana» es silente y dura distinto según la velocidad de la copia
# (111 a 16 fps, 93 a 19) y la parrilla anuncia la que se proyecta; «La marcha
# del hambre» son 94 según OjoAgua, su productora, y 92 según Proimágenes.
DURA_PARRILLA = {'almaprovinciana', 'lamarchadelhambre'}

# LA MISMA SINOPSIS EN DOS OBRAS DISTINTAS, y el error es del festival: sus
# páginas de «Relatos del camino» y «Un aparato para detectar fantasmas»
# publican palabra por palabra el mismo texto —«Un director de casting regresa
# a la ladera de la ciudad…»—. Comprobado en las dos URL el 21 sep.
#
# No se adivina cuál es cuál: se publican SIN sinopsis las dos. Poner el mismo
# texto en dos obras es peor que no ponerlo, y elegir a ojo sería inventar.
# Preguntado al festival.
# CALEIDOSCOPIO ES LA COMPETENCIA **NACIONAL** DE CORTOMETRAJES, y el
# festival lo escribe así en su propio logotipo: los 22 cortos son colombianos
# por definición de la sección. Sus fichas no imprimen país —la web solo lo
# pone en 15 de 37 obras— y salían sin bandera, que es lo que Juan preguntó de
# «Una sola golondrina» (22 sep).
#
# No es adivinar por el nombre del director ni por la ciudad: es la regla de
# admisión de la sección, publicada por el festival. Queda declarado aquí y
# no disperso en 22 sitios.
PAIS_POR_SECCION = {
    'CALEIDOSCOPIO': ('Colombia',
        'la sección es la «Competencia NACIONAL de cortometrajes» —así la '
        'rotula el festival en su logotipo y en la parrilla—: entrar en ella '
        'es ser colombiana.'),
}

SINOPSIS_EN_DISPUTA = {'relatos del camino', 'un aparato para detectar fantasmas'}

SEDE_PLAN = {
    'Casa de la cultura': 'Casa de la Cultura',
    'Coliseo municipal': 'Coliseo Municipal',
    'Placa deportiva Barrio Simón Bolívar': 'Placa deportiva Simón Bolívar',
    'Teatro municipal de Jardín - Café Tinta y Tinto Piso 2': 'Teatro Municipal de Jardín',
}
SALA = {'Teatro municipal de Jardín - Café Tinta y Tinto Piso 2': 'Café Tinta y Tinto, piso 2'}

# QUÉ ES CADA COSA QUE NO ES UNA OBRA. La parrilla mezcla proyecciones con
# paneles, charlas, muestras y actos, y el `event_kind` que publicamos tiene
# que salir del enum que la app sabe pintar (_kindMapES) o la card muestra el
# genérico «EVENTO» —lo vigila [event-kind-conocido]—.
#
# PENDIENTE DE JUAN: esto es vocabulario y se ve en la tarjeta. Mi lectura es
# que un «Panel» con ponentes y moderador es un FORO, y que la lección
# inaugural y la presentación del libro de Víctor Gaviria son CHARLAS. Las
# «Muestras» NO llevan kind: son proyecciones de un bloque de obras, aunque no
# sepamos cuáles; publicarlas como evento las sacaría del planificador.
ACTIVIDAD = [
    (r'^acto inaugural',            'apertura'),
    (r'^acto de clausura',          'clausura'),
    (r'^acto de premiaci|^premiaci', 'encuentro'),
    (r'^lecci[óo]n inaugural|^origen y conceptualizaci', 'charla'),
    (r'^panel:|^[áa]gora:',         'foro'),
    (r'^charla:',                   'charla'),
    (r'^presentaci[óo]n del libro', 'charla'),
]
POS = f'{ST}/jardin-2026-posters.json'
OUT = f'{ST}/jardin-2026-crudo.json'

# La ficha de la obra, de la web al formato intermedio. Solo renombra: si un
# campo hubiera que TRADUCIRLO, no iría aquí — iría discutido y declarado.
DE_LA_WEB = {'pais': 'pais', 'idioma': 'idioma', 'genero': 'genero',
             'duracion_min': 'duracion_min', 'sinopsis': 'sinopsis',
             'anio': 'anio', 'director': 'director', 'clasificacion': 'rating'}

# POR QUÉ CADA GRUPO DE OBRAS SE QUEDA FUERA. La clave es la sección tal como
# la escribe el catálogo; un grupo sin entrada hace fallar el paso.
SIN_FUNCION_OK = {
    'Muestra Central': 'con la parrilla completa del 21 sep quedan DOS obras '
        'fichadas en la web que no aparecen en ninguna lámina: «Nuestra tierra» '
        '(Lucrecia Martel) —que el propio festival anunció en el post de Muestra '
        'Central Parte I— y «Ubuntu: La métrica de los afectos». No es que no '
        'tengan día: es que la programación publicada no las incluye. '
        'Preguntado al festival.',
}


def genero_de(w):
    """El género de un corto de CALEIDOSCOPIO.

    La ficha de un largo imprime «Género: Documental / musical / ambiental». La
    de un corto no tiene esa línea: imprime la palabra suelta —«Documental»,
    «Ficción», «Experimental»— justo bajo el título, en el mismo sitio de la
    maqueta, y el raspador la guarda como `categoria` porque además es el eje
    por el que el festival parte la competencia. Es la misma palabra del mismo
    festival en el mismo lugar: se publica como género. No se traduce ni se
    completa — un corto sin esa línea se queda sin género."""
    if not w.get('genero') and w.get('categoria'):
        return {'genero': w['categoria']}
    return {}


def poster_de(w, pos):
    """El afiche YA BAJADO por `jardin-2026-posters.py`, servido por nosotros.

    Nunca la URL remota: un archivo en assets/ que ningún JSON nombra es un
    huérfano que el CI caza, y publicar la URL de image.tmdb.org además se
    salta el encuadre, que solo trabaja sobre archivos locales. Es la lección
    que costó los 16 pósters sueltos de Villa del Cine."""
    e = pos.get(norm(w['titulo']))
    return {'poster': e['poster'], 'posterSource': e['posterSource']} if e else {}


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    ig = json.load(open(IG, encoding='utf-8'))
    pos = {}
    if os.path.exists(POS):
        pos = {norm(x['title']): x
               for x in json.load(open(POS, encoding='utf-8'))['films']}
    acc = json.load(open(PLAN, encoding='utf-8'))['festival']['acceso_por_defecto']
    palabra = 'Entrada libre' if acc.get('is_free') is True else str(acc.get('is_free'))
    web = {norm(o['titulo']): o for o in cat['obras']}

    parr = json.load(open(PARR, encoding='utf-8'))
    funciones, usadas = [], set()
    for f in parr['funciones'] + [t for t in parr['talleres']
                                  if not t.get('_no_se_publica')]:
        tit = f.get('titulo') or ''
        sede_cruda = f.get('sede') or f.get('lugar') or ''
        reg = {'titulo': tit, 'dia': f['dia'], 'hora': f['hora'],
               'sede': SEDE_PLAN.get(sede_cruda, sede_cruda),
               'acceso': palabra,
               '_src': {'url': 'https://www.instagram.com/p/DdkY5ejlraV/',
                        'date': '2026-09-21'}}
        if SALA.get(sede_cruda):
            reg['sala'] = SALA[sede_cruda]
        if f.get('rotulo'):
            reg['_rotulo'] = f['rotulo']

        # UN BLOQUE DE CALEIDOSCOPIO ES UN PROGRAMA. La lámina lista sus cortos
        # con director y metraje, y cada uno tiene ficha en el catálogo: se
        # publica como programa con su lista, no como una función opaca.
        # UNA CASILLA DE DOS PELÍCULAS es un programa: dos obras en una
        # sesión, con un solo conversatorio. La primera («Tres Mujeres
        # guerreras») no tiene ficha en la web y la segunda («Ubuntu») sí; cada
        # una toma la mejor fuente. Sin esto, el crudo publicaba solo la
        # primera y «Ubuntu» se caía —lo vio Juan—.
        if f.get('obras') and len(f['obras']) > 1:
            reg['seccion'] = 'Muestra Central'
            reg['is_cortos'] = True
            reg['duracion_min'] = f['duracion_min']
            reg['film_list'] = []
            for ob in f['obras']:
                w2 = web.get(norm(ob['titulo']))
                it = {'titulo': (w2 or ob)['titulo'],
                      'director': (w2 or {}).get('director') or ob.get('director'),
                      'duracion_min': (w2 or {}).get('duracion_min') or ob.get('duracion_min')}
                if w2:
                    for orig, dest in DE_LA_WEB.items():
                        if w2.get(orig):
                            it[dest] = w2[orig]
                    it.update(genero_de(w2)); it.update(poster_de(w2, pos))
                    usadas.add(norm(ob['titulo']))
                else:
                    for c in ('pais', 'anio', 'genero'):
                        if ob.get(c):
                            it[c if c != 'genero' else 'genero'] = ob[c]
                    it['_sin_ficha_en_la_web'] = True
                reg['film_list'].append(it)
            # EL TÍTULO NOMBRA A LAS DOS. El festival no le pone nombre al
            # bloque, y titularlo con la primera escondía la segunda en la
            # tarjeta — lo caza [titulo-programa-incompleto].
            reg['titulo'] = ' + '.join(it['titulo'] for it in reg['film_list'])
            funciones.append(reg)
            continue

        if f.get('cortos'):
            reg['seccion'] = 'CALEIDOSCOPIO'
            reg['is_cortos'] = True
            reg['duracion_min'] = f['duracion_min']
            reg['film_list'] = []
            for c in f['cortos']:
                w = web.get(norm(c['titulo']))
                if not w:
                    sys.exit(f'✗ el corto «{c["titulo"]}» no tiene ficha en el '
                             f'catálogo — mirar antes de publicarlo a medias')
                usadas.add(norm(c['titulo']))
                it = {'titulo': w['titulo'], 'director': w.get('director') or c['director'],
                      'duracion_min': w.get('duracion_min') or c['duracion_min']}
                for orig, dest in DE_LA_WEB.items():
                    if w.get(orig):
                        it[dest] = w[orig]
                if norm(w['titulo']) in {norm(x) for x in SINOPSIS_EN_DISPUTA}:
                    it.pop('sinopsis', None)
                    it['_sinopsis_en_disputa'] = ('la web del festival publica el '
                        'mismo texto en esta obra y en la otra; se omite hasta que '
                        'lo aclaren')
                it.update(genero_de(w))
                it.update(poster_de(w, pos))
                _ps = PAIS_POR_SECCION.get(w.get('seccion'))
                if _ps and not it.get('pais'):
                    it['pais'] = _ps[0]
                    it['_pais_fuente'] = _ps[1]
                reg['film_list'].append(it)
            funciones.append(reg)
            continue

        # UN CINE FORO ES UNA PROYECCIÓN, no otra cosa. Clasificarlo como
        # evento le quitaba a «Volver» su ficha, su sinopsis y su afiche, y la
        # dejaba en la lista de obras sin función aunque el sábado se proyecta
        # a las 16:30. El prefijo se retira y la obra se busca por su nombre.
        mcf = re.match(r'^Cine foro:\s*(.+)$', tit, re.I)
        if mcf and web.get(norm(mcf.group(1))):
            tit = mcf.group(1).strip()
            reg['titulo'] = tit
            reg['_formato'] = 'Cine foro'

        # UNA ACTIVIDAD, y el festival la nombra
        kind = next((k for pat, k in ACTIVIDAD if re.search(pat, tit, re.I)
                     or re.search(pat, f.get('rotulo') or '', re.I)), '')
        w = web.get(norm(tit))
        if kind and not w:
            reg['tipo'] = 'evento'
            reg['event_kind'] = kind
            reg['duracion_min'] = f.get('duracion_min') or 60
            reg['seccion'] = 'Muestra Central'
            funciones.append(reg)
            continue
        if f.get('lugar'):                     # taller
            reg['tipo'] = 'evento'
            reg['event_kind'] = 'taller'
            # SE LLEVA, NO SE PLANIFICA. «Intervención artística · Crea tu
            # propia serigrafía» son cuatro horas de puertas abiertas en la
            # Casa de la Cultura mientras ahí mismo se proyecta: no es una
            # función a la que se llega a una hora. `info` la deja en el
            # programa sin meterla en el cruce de horarios.
            if re.match(r'^Intervenci[óo]n art[íi]stica', tit, re.I):
                reg['info'] = True
            reg['duracion_min'] = f.get('duracion_min') or 120  # el default solo si la lámina no da el fin
            reg['seccion'] = 'Muestra Central'
            # QUIÉN LO ORGANIZA VA EN LA DESCRIPCIÓN, no en un campo interno.
            # La lámina lo rotula —«Organiza: Defensoría del pueblo»,
            # «Tallerista: Diego León Zapata»— y yo lo guardaba en `_credito`,
            # que empieza por guion bajo y por tanto NO SE PUBLICA: en la
            # tarjeta el taller salía sin una línea. Lo vio Juan (22 sep).
            #
            # La sinopsis se arma con lo que el festival escribió y nada más:
            # el subtítulo cuando lo hay —«(Taller ELO - Espacios Libres de
            # Odio)», «Crea tu propia serigrafía»— y el crédito con su rótulo.
            _sub = (f.get('subtitulo') or '').strip()
            _cred = ('Organiza: ' + f['organiza'] if f.get('organiza')
                     else 'Tallerista: ' + f['tallerista'] if f.get('tallerista')
                     else '')
            _desc = '. '.join(x.strip(' .') for x in (_sub, _cred) if x)
            if _desc:
                reg['sinopsis'] = _desc + '.'
            funciones.append(reg)
            continue

        if not w:
            # una proyección SIN ficha en el catálogo: se publica con lo que la
            # parrilla imprime, que trae país, año, duración y género
            reg['seccion'] = 'Muestra Central'
            reg['duracion_min'] = f.get('duracion_min') or 90
            for c in ('director', 'pais', 'anio', 'genero'):
                if f.get(c):
                    reg[c] = f[c]
            # EL AFICHE TAMBIÉN PARA ÉSTAS. El paso de afiches ya las cubre
            # —su espina incluye lo que solo está en la parrilla— pero acá no
            # se le preguntaba, así que el cartel de «La casa del trueno» que
            # guarda la Cinemateca se bajaba y no llegaba a publicarse.
            reg.update(poster_de({'titulo': tit}, pos))
            reg['_sin_ficha_en_la_web'] = True
            funciones.append(reg)
            continue

        usadas.add(norm(tit))
        reg['titulo'] = w['titulo']
        reg['seccion'] = w['seccion']
        for orig, dest in DE_LA_WEB.items():
            if w.get(orig):
                reg[dest] = w[orig]
        reg.update(genero_de(w))
        reg.update(poster_de(w, pos))
        if f.get('_estreno') or (f.get('_extra') or '').lower().startswith('estreno'):
            reg['premiere'] = 'Estreno mundial'
        # LA DURACIÓN: manda la ficha, salvo donde la propia ficha explica que
        # la parrilla tiene razón (ver jardin-2026-verificar-parrilla.py).
        reg['duracion_min'] = (f['duracion_min'] if norm(tit) in DURA_PARRILLA
                               else w.get('duracion_min') or f.get('duracion_min'))
        funciones.append(reg)

    sin, fallos = {}, []
    for o in cat['obras']:
        if norm(o['titulo']) in usadas:
            continue
        sin.setdefault(o['seccion'], []).append(o['titulo'])
    for sec in sin:
        if sec not in SIN_FUNCION_OK:
            fallos.append(f'{len(sin[sec])} obra(s) de «{sec}» sin función y sin '
                          f'entrada en SIN_FUNCION_OK')

    json.dump({'_provenance': provenance(
        'festicinejardin.com (la ficha de cada obra) + las láminas de Instagram '
        'de @festicinejardin (día, hora, sede y el estreno)',
        que_aporta='la única función que el festival ha fechado, con la ficha '
                   'completa de su obra',
        url='https://festicinejardin.com/',
        metodo='las dos superficies del festival, contrastadas campo a campo en '
               'jardin-2026-contraste.py. Donde discrepan manda la web, que '
               'está escrita a máquina, y la discrepancia queda declarada',
        alcance=f'{len(funciones)} función de las {len(cat["obras"])} obras del '
                f'catálogo — el resto no tiene día, hora ni sede'),
        'funciones': funciones,
        '_talleres_fuera': [
            {'titulo': t['titulo'], '_por_que': t['_no_se_publica']}
            for t in parr['talleres'] if t.get('_no_se_publica')],
        '_sin_funcion': {sec: {'n': len(ts), '_por_que': SIN_FUNCION_OK.get(sec, ''),
                               'obras': sorted(ts)}
                         for sec, ts in sorted(sin.items())},
        '_sedes_publicadas_sin_funcion': [
            s for s in ig['sedes'] if s not in {f['sede'] for f in funciones}]},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{len(funciones)} función · {sum(len(v) for v in sin.values())} obras '
          f'del catálogo esperando parrilla → {OUT.split("/")[-1]}')
    for f in funciones:
        print(f'  {f["dia"][-2:]} {f["hora"]} {f["duracion_min"]:>4}m  '
              f'{f["titulo"][:40]:42} {f["sede"]}')
    for sec, ts in sorted(sin.items()):
        print(f'  · {len(ts):2} de «{sec}» sin función')
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for x in fallos:
            print('   ✗', x)
        sys.exit(1)


if __name__ == '__main__':
    main()
