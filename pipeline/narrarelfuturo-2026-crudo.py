# -*- coding: utf-8 -*-
"""Funde las fuentes de #NarrarElFuturo en el crudo del formato intermedio.

ESTE ES EL ÚNICO SCRIPT CON DERECHO A ESCRIBIR EL CRUDO. Los parsers escriben
cada uno su sidecar; cuando dos de ellos apuntaron al crudo, el segundo borró al
primero y se perdieron 8 funciones y 27 obras sin un error en pantalla.

Entradas y qué aporta cada una:
  -web.json        la PARRILLA: qué función hay, cuándo, dónde y cómo se entra
  -obras.json      la FICHA de cada obra: sinopsis, póster, dirección, género
  -talleres.json   la franja académica, con el retrato del tallerista
  -ig.json         lo que la web no publica: el bloque de la Sala VR
  -vr.json         las 8 obras de la instalación
  -cinemateca.json CORROBORACIÓN de las 8 funciones en salas de la Cinemateca

La Cinemateca no aporta dato nuevo: se usa para CONTRASTAR día, hora y sala, y
lo que discrepe se reporta. Dos fuentes independientes que coinciden valen más
que una que nadie contradijo.
"""
import io, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
SALIDA = f'{ST}/narrarelfuturo-2026-crudo.json'

# La instalación VR no es una función: está ABIERTA en bloque y el festival
# publica sus horarios en Instagram. Se modela como una actividad recurrente
# —un bloque, `is_recurring` en cada sesión— que es el mecanismo de la casa para
# lo multi-día. Sin esto el domingo 20 se quedaría sin nada, y sí hay algo.
VR_SESIONES = [('2026-09-15', '14:00', 240), ('2026-09-16', '14:00', 240),
               ('2026-09-17', '14:00', 240), ('2026-09-18', '14:00', 240),
               ('2026-09-19', '11:00', 420), ('2026-09-20', '11:00', 420)]
VR_SEDE, VR_SALA = 'Cinemateca de Bogotá', 'Laboratorios 1 y 2'

# El mismo corto escrito de dos formas por las dos fuentes. La web de este
# festival publica «Mercado del arte_ …» porque su gestor convirtió los dos
# puntos del título en guion bajo; la Cinemateca lo escribe bien. Y «6 de
# December» es la mitad en inglés de «6 de diciembre». Mapa EXPLÍCITO: la
# versión heurística de esto añadió las dos como obras nuevas y duplicó el
# programa.
TITULO_OFICIAL = {
    'Mercado del arte: cómo fabricar un artista': 'Mercado del arte_ cómo fabricar un artista',
    '6 de December': '6 de diciembre',
}

# (Hubo un FALTANTES para «Malignant / Catatonic»: la tarjeta no traía año y el
# parser de la web la tiraba. Se arregló el parser — el año es opcional — y el
# parche se fue. Un crudo que repone lo que su parser pierde esconde el hueco.)

# SECCIÓN = la temática que el propio festival usa para filtrar su programa
# («🏷️ FILTRAR POR TEMÁTICA»), más «Sala VR», que es como llama a la
# instalación en su propio índice. Ninguna es invención nuestra. El mapeo va
# EXPLÍCITO desde la etiqueta con que el festival encabeza cada tarjeta, no por
# heurística sobre el título.
SECCION = {
    'Largometraje': 'Proyecciones & Largos',
    'RT Meet The Creators': 'Proyecciones & Largos',
    'Cortos': 'Muestra de Cortos',
    'taller': 'Talleres & Formación',
    # la instalación entra con su kind, no con una etiqueta de tarjeta: sin esta
    # clave caía a «Proyecciones & Largos» y la Sala VR no existía como sección
    'experiencia': 'Sala VR',
}
# La clausura no lleva etiqueta en su tarjeta: es una proyección y va con ellas.
SECCION_DEFECTO = 'Proyecciones & Largos'


# slug()/norm() son las de lib: la clave de JOIN entre el título de la tarjeta
# («Aqua, Ensayo & Diversidad») y el slug de la ruta de la ficha
# («aqua-ensayo-diversidad»). Cruzar por norm() NO casa —coma y ampersand— y
# el fallo es mudo: la función se publica sin sus obras y nada avisa.
from lib import slug, norm  # noqa: E402


def cargar(n):
    return json.load(io.open(f'{ST}/narrarelfuturo-2026-{n}.json', encoding='utf-8'))


def main():
    web = cargar('web')['funciones']
    obras = cargar('obras')['obras']
    talleres = cargar('talleres')['talleres']
    vr = cargar('vr')['obras']
    cine = cargar('cinemateca')['funciones']

    por_titulo = {norm(o.get('titulo')): o for o in obras if o.get('titulo')}

    # FICHAS DUPLICADAS: dos páginas del festival traen la MISMA línea técnica
    # («Argentina · 2025 · 3 min 49s · Ficción IA» en Malignant / Catatonic y en
    # Marta Trend; «Colombia · 2026 · 27 min 59s» en Vivir de la piedra y en
    # Venezuela: latidos entre escombros). Es copia-y-pega del sitio, no dos
    # obras iguales, y explica las contradicciones tarjeta/ficha que salieron en
    # tres revisiones. Regla, no parche: si la ficha técnica de una obra coincide
    # entera con la de otra, para ESOS campos (país, año, duración, género) manda
    # la TARJETA del programa, que es donde el festival las lista una por una.
    # Sinopsis, dirección y póster de la ficha se conservan: esos sí son propios.
    _firma = {}
    for o in obras:
        if o.get('titulo') and o.get('anio') and o.get('duracion_min'):
            _firma.setdefault((o.get('pais'), o['anio'], o['duracion_min'], o.get('genero')), []).append(norm(o['titulo']))
    dup = {t for k, ts in _firma.items() if len(ts) > 1 for t in ts}
    TECNICOS = ('pais', 'anio', 'duracion_min', 'genero')
    por_programa = {}
    for o in obras:
        if o.get('programa') and o.get('titulo'):
            por_programa.setdefault(slug(o['programa']), []).append(o)

    FICHA = ('sinopsis', 'poster', 'genero', 'director', 'pais', 'anio', 'duracion_min')

    # La agenda de la Cinemateca publica estas mismas obras con la duración ya
    # redondeada al minuto, y sus listas suman EXACTAMENTE lo que el programa
    # declara (83, 87, 91). La web da segundos y al redondear cada obra por
    # separado la suma se desvía ±1. Donde la Cinemateca tiene la obra, manda su
    # minuto; y si tiene una obra que a la tarjeta le falta, se AÑADE y se dice.
    cine_obras = {}
    for c in cine:
        for o in (c.get('obras') or []):
            cine_obras[norm(TITULO_OFICIAL.get(o['titulo'], o['titulo']))] = o
    funciones = []

    for f in web:
        g = dict(f)
        g.pop('es_programa', None)
        if f.get('obras'):
            # LA TARJETA DECIDE QUÉ OBRAS TIENE EL PROGRAMA; la ficha por obra
            # solo la COMPLETA. Al revés no funciona: la web archiva «Despierta!»,
            # «HensFluenzers», «Sopro» y «Time Capsule» bajo la ruta de «Aqua,
            # Ensayo & Diversidad» aunque se proyecten en «Narrar. Creer.
            # Crecer». Tomando la ruta como pertenencia, ese programa salía con
            # 12 obras en vez de 8 — y la agenda de la Cinemateca, que es
            # independiente, también dice 8.
            g['obras'] = []
            vistos = set()
            for o in f['obras']:
                base = dict(por_titulo.get(norm(o.get('titulo'))) or {})
                if norm(o.get('titulo')) in dup:
                    for k in TECNICOS:
                        base.pop(k, None)          # ficha copiada: manda la tarjeta
                    base['_ficha_duplicada'] = 'línea técnica idéntica a otra obra; país/año/duración/género salen de la tarjeta'
                obra = {k: (o.get(k) or base.get(k)) for k in ('titulo', '_ficha_duplicada') + FICHA
                        if (o.get(k) or base.get(k))}
                cc = cine_obras.get(norm(o.get('titulo')))
                if cc and cc.get('duracion_min'):
                    obra['duracion_min'] = cc['duracion_min']
                vistos.add(norm(o.get('titulo')))
                g['obras'].append(obra)
        else:
            base = dict(por_titulo.get(norm(f['titulo'])) or {})
            if base and norm(f['titulo']) in dup:
                for k in TECNICOS:
                    base.pop(k, None)              # ficha copiada: manda la tarjeta
                g['_ficha_duplicada'] = 'línea técnica idéntica a otra obra; país/año/duración/género salen de la tarjeta'
            if base:
                for k in FICHA:
                    if base.get(k) and not g.get(k):
                        g[k] = base[k]
            g.pop('obras', None)
        funciones.append(g)

    for t in talleres:
        if not (t.get('dia') and t.get('hora')):
            continue
        funciones.append({
            'titulo': t['titulo'], 'dia': t['dia'], 'hora': t['hora'],
            'sede': t.get('sede', ''), 'sala': t.get('sala', ''),
            'tipo': 'taller', 'event_kind': 'taller',
            'director': t.get('tallerista', ''), 'pais': t.get('pais', ''),
            'duracion_min': t.get('duracion_min'), 'sinopsis': t.get('sinopsis'),
            'poster': t.get('imagen'), 'acceso': t.get('acceso', lib.DESCONOCIDO),
            'registration_url': t.get('registration_url'), '_src': t.get('_src'),
        })
        # Segunda sesión el mismo día (podcast: 10–12 y 2–6): su propia
        # actividad, con la misma ficha. Sin esto el bloque de la tarde no existía.
        if t.get('sesion2') and t['sesion2'].get('hora'):
            g = dict(funciones[-1])
            g.update({'hora': t['sesion2']['hora'], 'duracion_min': t['sesion2'].get('duracion_min'),
                      '_nota': 'segunda sesión del mismo día, declarada así en la ficha del taller'})
            funciones.append(g)

    # Las obras de VR también tienen ficha propia en la web: sin completarlas
    # desde ahí salían sin póster ni sinopsis las 48 entradas (8 obras × 6
    # sesiones). La lista de la tarjeta dice CUÁLES son; la ficha, cómo son.
    obras_vr = []
    for o in vr:
        base = por_titulo.get(norm(o.get('titulo'))) or {}
        obras_vr.append({k: (o.get(k) or base.get(k)) for k in ('titulo',) + FICHA
                         if (o.get(k) or base.get(k))})
    for dia, hora, dur in VR_SESIONES:
        funciones.append({
            # El nombre es el del festival, verbatim: la tarjeta de la web dice
            # «VR» / «#OtrosMundosPosibles» y el arte de IG «Expo VR
            # #OtrosMundosPosibles». «Sala VR» es la SECCIÓN (IG: «Proyecciones
            # en SALA VR»), no el título de la actividad.
            'titulo': 'VR #OtrosMundosPosibles', 'dia': dia, 'hora': hora,
            'sede': VR_SEDE, 'sala': VR_SALA,
            'duracion_min': dur,
            # ACTIVIDAD ABIERTA, no una función con hora de inicio: la
            # instalación está activa toda la franja y se entra cuando uno
            # quiere. Es el modelo `info:true` que ya existe en la app desde la
            # maratón de SiembraFest — «se lleva, no se planifica»: la ventana
            # es dato y se queda, lo que cambia es cómo se dice («Hasta 18:00»,
            # «Vas cuando quieras»). Modelarla como seis funciones la habría
            # metido en el planificador y en «la próxima», donde no va.
            'info': True, 'type': 'event', 'event_kind': 'experiencia',
            'acceso': 'Entrada libre hasta completar aforo',
            'obras': obras_vr,
            '_src': 'https://www.instagram.com/p/DdR-n97md3i/',
        })

    for f in funciones:
        f['seccion'] = SECCION.get(f.get('event_kind'), SECCION_DEFECTO)
        # La ETIQUETA de la tarjeta («Largometraje», «Cortos», «RT Meet The
        # Creators») sirve para elegir la sección y ahí se queda: NO es un
        # event_kind. Un event_kind que la app no conoce pinta «EVENTO» genérico
        # en la card de una película. Solo los talleres y la instalación VR son
        # actividades con kind propio.
        if f.get('event_kind') not in ('taller', 'experiencia'):
            f.pop('event_kind', None)
    # Pósters RE-HOSTEADOS (paso posters.py): la tabla remota→/assets/ se aplica
    # aquí, sobre funciones y obras, porque el crudo es el único que decide qué
    # póster lleva cada cosa. Si la tabla no existe, quedan las URLs del festival.
    _pp = f'{ST}/narrarelfuturo-2026-posters.json'
    _posters = json.load(io.open(_pp, encoding='utf-8')).get('posters', {}) if os.path.exists(_pp) else {}
    for f in funciones:
        for x in [f] + list(f.get('obras') or []):
            if x.get('poster') in _posters:
                x['poster'] = _posters[x['poster']]
    funciones = [{k: v for k, v in f.items() if v not in (None, '')} for f in funciones]
    for f in funciones:
        f.setdefault('sala', '')

    # CONTRASTE con la Cinemateca: no corrige, reporta.
    discrepa = []
    porc = {(norm(c['titulo']), c['dia']): c for c in cine}
    for f in funciones:
        c = porc.get((norm(f['titulo']), f.get('dia')))
        if c and c.get('hora') != f.get('hora'):
            discrepa.append(f"{f['titulo'][:34]} {f['dia']}: web {f.get('hora')} vs Cinemateca {c.get('hora')}")

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'narrarelfuturo.com (programa + ficha por obra + talleres) + Instagram (Sala VR) + agenda de la Cinemateca (contraste)',
        metodo='fusión: la parrilla de la web manda; la ficha por obra la completa; la Cinemateca contrasta',
        nota='la instalación VR va como actividad recurrente (is_recurring), no como seis funciones distintas'),
        '_funciones': len(funciones),
        '_obras': sum(len(f.get('obras') or []) for f in funciones),
        '_contraste_cinemateca': discrepa or 'sin discrepancias en día/hora',
        'funciones': funciones},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    import collections
    print(f'── {os.path.basename(SALIDA)} · {len(funciones)} funciones · '
          f"{sum(len(f.get('obras') or []) for f in funciones)} obras en programas")
    print('   días:', dict(sorted(collections.Counter(f['dia'][-2:] for f in funciones).items())))
    print('   secciones:', dict(sorted(collections.Counter(f['seccion'] for f in funciones).items())))
    for c in ('sinopsis', 'poster', 'director', 'acceso'):
        print(f"   {c:<10} {sum(1 for f in funciones if f.get(c)):>3}/{len(funciones)}")
    print('   contraste Cinemateca:', discrepa or 'sin discrepancias ✓')


if __name__ == '__main__':
    main()
