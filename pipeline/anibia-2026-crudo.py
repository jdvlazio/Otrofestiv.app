#!/usr/bin/env python3
"""anibia-2026-crudo.py — la programación de ANIBIA 2026 (Bogotá, 20 oct–1 nov)
→ crudo (función base) + afirmaciones (docs/FUNCION.md).

LA FUENTE PRINCIPAL es la programación oficial en PDF (Linktree; el mismo
diseño que el carrusel de IG DeQG0NPGy2f, 13 láminas, cruzado por
pipeline/ig-lecturas.py). Da día, hora, sede, acceso y edad, y se transcribe A
MANO abajo (FUNCIONES): es la función base, con su ancla (sede, día, hora).

LA SALA (Cinemateca de Bogotá: agenda/11, 80 y 112, y las fichas ?sede=11)
AFIRMA lo que el PDF no trae o contradice, en festivals/staging/
anibia-2026-afirmaciones.json:
  · `sala` de cada función del Centro (la agenda);
  · `entrada: boleta` + `ticket_url` (TuBoleta: UN link de compra por ficha)
    en las del Centro salvo la inaugural, que es entrada libre;
  · Fontanar del Río, 31 oct: la agenda dice 14:00 y el PDF 16:00. DECISIÓN
    DE JUAN (21 oct): la sala manda en hora y, ante una hora contradictoria, va
    la más temprana → afirmación `juan`, escrita a mano (ver abajo).
El script FRENA si una función de la Cinemateca no está en su agenda a la hora
del PDF (salvo la contradicción declarada).

LAS OBRAS de cada programa salen del catálogo (anibia-2026-catalogo.json, las
fichas de la Cinemateca), en su orden.

LO QUE NO SE PUBLICA (`_fuera`): el taller Anibia-ASIFA, «Evento para aliados»
y sin sede en el PDF. El Reel / WIP Day sí tiene sede: va, con entrada por
invitación («Evento para aliados»).

LA DECISIÓN DE JUAN (hora de Fontanar) vive escrita a mano en -afirmaciones.json
(tipo juan): el script la conserva, no la genera.

Escribe festivals/staging/anibia-2026-crudo.json y -afirmaciones.json
"""
import datetime, html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance, DESCONOCIDO  # noqa: E402

SRC = f'{REPO}/fuentes/anibia-2026'
CAT = f'{REPO}/festivals/staging/anibia-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/anibia-2026-crudo.json'
AFI = f'{REPO}/festivals/staging/anibia-2026-afirmaciones.json'
PDF = 'https://drive.google.com/uc?export=download&id=1oWVSdLh8OtO65UAX8pybuF2hhdnflkOK'
FICHA = 'https://cinematecadebogota.gov.co/node/peliculas/{}?sede={}'
HOY = '2026-10-21'

CIN, FON, CEFE = 'Cinemateca de Bogotá', 'Cinemateca Fontanar del Río', 'CEFE Chapinero'
NAL = 'Universidad Nacional, Edificio 303 (NEA)'
TADB, TAD4 = 'Universidad Jorge Tadeo Lozano, Ed. Biblioteca', 'Universidad Jorge Tadeo Lozano, Módulo 4'
# Una sede, la Javeriana; el edificio es la sala (como la UNAL 303). El detalle
# (Hall entrada admin. Facultad de Artes / Auditorio piso 5) va en la _nota de venues-geo.
JAV = ATI = 'Pontificia Universidad Javeriana'
LIBRE = 'Entrada libre / hasta completa aforo'
AGENDA_DE = {CIN: 11, FON: 80, CEFE: 112}     # la sede → su agenda en cinematecadebogota.gov.co
E = 'evento'

# (día, hora, título VERBATIM del PDF, sección, sede, sala del PDF, acceso del PDF,
#  edad, nodo de la Cinemateca, extra)
FUNCIONES = [
    ('2026-10-20', '15:00', 'Las orejas no tienen párpados', 'Cine Concierto & Panel', TADB, 'Auditorio Fabio Lozano',
     'Entrada libre / Hasta completa aforo', None, None,
     {'tipo': E, 'event_kind': 'cineconcierto', 'duracion_min': 120, '_duracion_de': '120 min declarados: el PDF no la da',
      'sinopsis': 'Un espacio dedicado a explorar el universo sonoro en el audiovisual y la animación. En alianza '
                  'entre el Festival Eureka, el Festival Anibia y la Universidad Jorge Tadeo Lozano.'}),
    ('2026-10-21', '19:00', 'El hijo de puta (O filho da puta)', 'Surgentes', CIN, '',
     'Entrada libre / hasta completa aforo. Entrega de boletería una hora antes de la función', 15, 3590,
     {'obra': 'El hijo de puta (O filho da puta)', 'premiere': 'Inauguración'}),
    ('2026-10-22', '16:00', 'Surgentes - Animage', 'Surgentes', CIN, '', DESCONOCIDO, 12, 3591, {'programa': 'Surgentes - Animage'}),
    ('2026-10-22', '17:00', 'Surgentes - Con extremos', 'Surgentes', CIN, '', DESCONOCIDO, 12, 3592, {'programa': 'Surgentes - Con extremos'}),
    ('2026-10-22', '17:30', 'Mukira', 'Todxs a Bordo', CEFE, '', LIBRE, 12, 3513,
     {'obra': 'Mukira', 'premiere': 'Estreno nacional', 'has_qa': True, 'qa_type': 'team'}),
    ('2026-10-22', '19:30', 'Conexión - Foco Pez Dorado', 'Conexión', CIN, '', DESCONOCIDO, 12, 3593,
     {'programa': 'Conexión - Foco Pez Dorado', 'has_qa': True, 'qa_type': 'team'}),
    ('2026-10-23', '16:00', 'Con acento nacional - Procesos de formación - Programa 1', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3594,
     {'programa': 'Con acento nacional - Procesos de formación - Programa 1'}),
    ('2026-10-23', '17:00', 'Con acento nacional - Profesional - Programa 1', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3595,
     {'programa': 'Con acento nacional - Profesional - Programa 1'}),
    ('2026-10-23', '19:30', 'Surgentes - Miyu', 'Surgentes', CIN, '', DESCONOCIDO, 12, 3596, {'programa': 'Surgentes - Miyu'}),
    ('2026-10-24', '14:00', 'Surgentes - Animage', 'Surgentes', CIN, '', DESCONOCIDO, 12, 3591, {'programa': 'Surgentes - Animage'}),
    ('2026-10-24', '15:30', 'Costa a costa - Lo mejor de Annecy 2026', 'Costa a Costa', CIN, '', DESCONOCIDO, 12, 3692,
     {'programa': 'Costa a costa - Lo mejor de Annecy 2026'}),
    ('2026-10-24', '16:00', 'Costa a costa', 'Costa a Costa', CIN, '', DESCONOCIDO, 12, 3616, {'programa': 'Costa a costa'}),
    ('2026-10-24', '17:30', 'Con acento nacional - Procesos de formación - Programa 2', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3617,
     {'programa': 'Con acento nacional - Procesos de formación - Programa 2'}),
    ('2026-10-24', '20:00', 'Con acento nacional - Profesional - Programa 2', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3618,
     {'programa': 'Con acento nacional - Profesional - Programa 2'}),
    ('2026-10-25', '14:00', 'Costa a costa', 'Costa a Costa', CIN, '', DESCONOCIDO, 12, 3616, {'programa': 'Costa a costa'}),
    ('2026-10-25', '16:00', 'Con acento nacional - Profesional - Programa 1', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3595,
     {'programa': 'Con acento nacional - Profesional - Programa 1'}),
    ('2026-10-25', '17:30', 'Con acento nacional - Profesional - Programa 2', 'Con Acento Nacional', CIN, '', DESCONOCIDO, 12, 3618,
     {'programa': 'Con acento nacional - Profesional - Programa 2'}),
    ('2026-10-25', '19:30', 'Costa a costa - Lo mejor de Annecy 2026', 'Costa a Costa', CIN, '', DESCONOCIDO, 12, 3692,
     {'programa': 'Costa a costa - Lo mejor de Annecy 2026'}),
    # 27 oct: la lámina pone la sede UNA vez, bajo «Entrega de reconocimientos»;
    # se lee como sede de los tres bloques (el bloque es «Con acento nacional /
    # Procesos de formación» con sus tres horas)
    ('2026-10-27', '14:00', 'Con acento nacional - Procesos de formación - Programa 1', 'Con Acento Nacional', TAD4,
     'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None, {'programa': 'Con acento nacional - Procesos de formación - Programa 1'}),
    ('2026-10-27', '15:30', 'Con acento nacional - Procesos de formación - Programa 2', 'Con Acento Nacional', TAD4,
     'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None, {'programa': 'Con acento nacional - Procesos de formación - Programa 2'}),
    ('2026-10-27', '17:30', 'Entrega de reconocimientos', 'Con Acento Nacional', TAD4, 'Aula Máxima Luís Cordoba Mariño', LIBRE, None, None,
     {'tipo': E, 'event_kind': 'awards', 'duracion_min': 60, '_duracion_de': '60 min declarados: el PDF no la da',
      'sinopsis': 'Con acento nacional · Procesos de formación. Módulo 4, planta baja, entrada calle 23.'}),
    ('2026-10-27', '18:30', 'Surgentes - Animage', 'Surgentes', NAL, 'Cinemateca Sala Alterna UNAL', LIBRE, None, None,
     {'programa': 'Surgentes - Animage'}),
    ('2026-10-28', '13:00', 'Reel / WIP Day', 'Día Internacional de la Animación', NAL, 'Bloque A, Aula Múltiple 105',
     'Evento para aliados', None, None,
     {'tipo': E, 'event_kind': 'encuentro', 'duracion_min': 240, '_duracion_de': '1:00 a 5:00 p. m., del PDF',
      'sinopsis': 'Profesionales y estudios observan los reels y proyectos en progreso (wips) de artistas noveles.'}),
    ('2026-10-28', '17:00', 'Caballo Loco Studio: Crear antes de animar', 'Charla', NAL, 'Bloque C, Auditorio 422', LIBRE, None, None,
     {'tipo': E, 'event_kind': 'charla', 'duracion_min': 90, '_duracion_de': '90 min declarados: el PDF no la da'}),
    ('2026-10-30', '16:00', 'Mi papá el camión', 'Conexión de Largo Aliento', ATI, 'Ed. Ático', LIBRE, None, None,
     {'tipo': E, 'event_kind': 'conversatorio', 'duracion_min': 120, '_duracion_de': '120 min: hasta el siguiente, a las 18:00',
      'sinopsis': 'Pez Dorado. Un espacio para conversar sobre el proceso creativo, las historias y los detalles detrás '
                  'del inicio de la producción de un largometraje.'}),
    ('2026-10-30', '18:00', 'Desechable', 'Conexión de Largo Aliento', ATI, 'Ed. Ático', LIBRE, None, None,
     {'tipo': E, 'event_kind': 'conversatorio', 'duracion_min': 90, '_duracion_de': '90 min declarados: el PDF no la da',
      'sinopsis': 'Nocroma. Un espacio para conversar sobre el proceso creativo, las historias y los detalles detrás '
                  'del inicio de la producción de un largometraje.'}),
    ('2026-10-31', '16:00', 'Surgentes - Animage', 'Surgentes', FON, '', LIBRE, 12, 3579, {'programa': 'Surgentes - Animage'}),
    ('2026-11-01', '14:00', 'Surgentes - Con extremos', 'Surgentes', FON, '', LIBRE, 12, None, {'programa': 'Surgentes - Con extremos'}),
]
# La exposición: 22 oct–13 nov, 8:00–17:00; el PDF la lista en cada día de
# programación desde el 22 (no el 26 ni el 29). Se recorre, no se reserva → info.
EXPO = ('Una vez en un cuerpo: Habitar la imagen', JAV, 'Ed. Gerardo Arango',
        ['2026-10-22', '2026-10-23', '2026-10-24', '2026-10-25', '2026-10-27', '2026-10-28',
         '2026-10-30', '2026-10-31', '2026-11-01'])

TB = 'https://cinemateca.checkout.tuboleta.com/selection/event/date?productId='
# La ficha 3596 (Miyu) publica …183952: un dígito menos, y TuBoleta responde
# «Error Page». La serie de las demás fichas (…523 a …532) deja libre …528, que
# TuBoleta titula «Cinemateca de Bogotá - Centro Sala 3 | 23.10.2026 - 19:30 |
# Surgentes - Miyu» (comprobado el 21 oct 2026).
TB_CORREGIDO = {3596: TB + '10230581839528'}


def tuboleta(n):
    if n in TB_CORREGIDO:
        return TB_CORREGIDO[n]
    p = f'{SRC}/fichas/s11-{n}.html'
    L = sorted(set(re.findall(re.escape(TB) + r'(\d{14})', open(p, encoding='utf-8').read())))
    if len(L) != 1:
        sys.exit(f'✗ ficha {n}: {len(L)} links de TuBoleta')
    return TB + L[0]


def agenda():
    """{(nodo, día, hora): sala} de las agendas de la Cinemateca."""
    out = {}
    meses = {'Octubre': '10', 'Noviembre': '11', 'Diciembre': '12'}
    for s in AGENDA_DE.values():
        d = open(f'{SRC}/agenda-{s}.html', encoding='utf-8').read()
        for it in d.split('views-view-responsive-grid__item-inner')[1:]:
            n = re.search(r'peliculas/(\d+)', it)
            sala = re.search(r"funcion-sala'>([^<]*)", it)
            f = re.search(r"funcion-fecha'>(\w+) (\d+)", it)
            h = re.search(r"funcion-hora'>(\d+):(\d+) (am|pm)", it)
            if n and f and h:
                hh = int(h[1]) % 12 + (12 if h[3] == 'pm' else 0)
                out[(int(n[1]), f'2026-{meses[f[1]]}-{int(f[2]):02d}', f'{hh:02d}:{h[2]}')] = html.unescape(sala[1]).strip()
    return out


def afirmacion(sede, dia, hora, casilla, valor, fuente, evidencia, **extra):
    return {'ancla': {'sede': f'{sede} - Bogotá', 'dia': dia, 'hora': hora}, 'fuente': fuente,
            'casilla': casilla, 'valor': valor, 'evidencia': evidencia, **extra}


def obra(o):
    r = {k: o[k] for k in ('titulo', 'director', 'anio', 'pais', 'duracion_min', 'sinopsis') if o.get(k)}
    # «…de nuestro país: violencia y lucha…» (Relatos del Camino): el guardián
    # [sinopsis-pura] lo lee como metadata pegada («País:»). No se pasa: la obra
    # se queda con la sinopsis que ya publicamos de ella (FICPA).
    if re.search(r'Pa[ií]s(?:es)?\s*:', r.get('sinopsis') or '', re.I):
        r.pop('sinopsis')
    return r


def main():
    ag = agenda()
    cat = json.load(open(CAT, encoding='utf-8'))['obras']
    por_prog, por_tit = {}, {o['titulo']: o for o in cat}
    for o in cat:
        por_prog.setdefault(o['programa'], []).append(o)

    # Lo que NO regenera este script se conserva del archivo: las decisiones de
    # Juan (tipo juan, escritas a mano en -afirmaciones.json) y la sala de una
    # función que ya pasó, que la agenda deja de listar (la dio el día del montaje)
    previas = json.load(open(AFI, encoding='utf-8'))['afirmaciones'] if os.path.exists(AFI) else []
    juan = [a for a in previas if a['fuente']['tipo'] == 'juan']
    hora_juan = {(a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora']): a['valor'] for a in juan if a['casilla'] == 'time'}
    hoy = datetime.date.today().isoformat()
    funciones, afs, fallos = [], list(juan), []
    for dia, hora, tit, sec, sede, sala, acceso, edad, nodo, x in FUNCIONES:
        f = {'titulo': tit, 'dia': dia, 'hora': hora, 'sede': sede, 'acceso': acceso, 'seccion': sec,
             '_src': {'url': PDF, 'date': HOY}}
        if sala:
            f['sala'] = sala
        if edad:
            f['clasificacion'] = f'Mayores de {edad} años'
        x = dict(x)
        if 'programa' in x:
            L = por_prog.get(x.pop('programa'))
            if not L:
                fallos.append(f'{tit}: el programa no está en el catálogo')
                continue
            f['obras'] = [obra(o) for o in L]
        if 'obra' in x:
            f.update({k: v for k, v in obra(por_tit[x.pop('obra')]).items() if k != 'titulo'})
        f.update(x)
        funciones.append(f)
        if not nodo:
            continue
        url = FICHA.format(nodo, AGENDA_DE[sede])
        fu = {'tipo': 'sala', 'url': url, 'fecha': HOY}
        anc = (f'{sede} - Bogotá', dia, hora)
        h_sala = hora_juan.get(anc, hora)
        k = (nodo, dia, h_sala)
        if k not in ag:
            # la agenda solo lista lo que no ha pasado: una función de hoy o
            # anterior que ya salió conserva lo que la agenda afirmó antes
            viejas = [a for a in previas if a['fuente']['tipo'] == 'sala'
                      and (a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora']) == anc]
            if dia <= hoy and viejas:
                afs += viejas
                continue
            fallos.append(f'{dia} {hora} {tit}: no está en la agenda de la Cinemateca')
            continue
        if sede == CIN:
            afs.append(afirmacion(sede, dia, hora, 'sala', ag[k], fu, f'{tit} · Cinemateca de Bogotá Centro · {dia} {hora} · {ag[k]}'))
            if nodo != 3590:
                ev = f'{tit} · {dia} {hora} · link de TuBoleta de la ficha'
                if nodo in TB_CORREGIDO:
                    ev += (' (la ficha trae …183952, un dígito menos, y TuBoleta da «Error Page»; …528 es el que '
                           'TuBoleta titula «Surgentes - Miyu», 23.10.2026 19:30)')
                afs.append(afirmacion(sede, dia, hora, 'entrada', 'boleta', fu, ev))
                afs.append(afirmacion(sede, dia, hora, 'ticket_url', tuboleta(nodo), fu, ev))
    tit, sede, sala, dias = EXPO
    for d in dias:
        funciones.append({'titulo': tit, 'dia': d, 'hora': '08:00', 'sede': sede, 'sala': sala,
                          'acceso': 'Entrada libre', 'seccion': 'Exposición', 'tipo': E, 'event_kind': 'evento',
                          'is_recurring': True, 'info': True, 'duracion_min': 540,
                          '_duracion_de': '8:00 a. m. a 5:00 p. m., del PDF',
                          'sinopsis': 'Exposición del 22 de octubre al 13 de noviembre, de 8:00 a. m. a 5:00 p. m.',
                          '_src': {'url': PDF, 'date': HOY}})
    if fallos:
        sys.exit('✗ la programación no cuadra:\n  · ' + '\n  · '.join(fallos))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('programación oficial de Anibia 2026 (PDF del Linktree = carrusel IG DeQG0NPGy2f)', url=PDF,
                                  metodo='PDF transcrito a mano; obras de cada programa desde el catálogo (fichas de la Cinemateca)'),
        '_fuera': ['Taller Anibia-ASIFA «Un arból que . . .» (21–23 oct, 9:00–12:00): «Evento para aliados» y '
                   'el PDF no da sede (la sede es obligatoria)'],
        'funciones': funciones}, ensure_ascii=False, indent=1))
    io.open(AFI, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('agenda y fichas de la Cinemateca de Bogotá (sala, TuBoleta) + decisión de Juan (hora de Fontanar)',
                                  metodo='una afirmación por casilla, con su fuente (docs/FUNCION.md)'),
        'afirmaciones': afs}, ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("obras"))} programas) · '
          f'{len(afs)} afirmaciones ({len(juan)} de Juan) · 1 fuera')


if __name__ == '__main__':
    main()
