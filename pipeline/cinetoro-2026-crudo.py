#!/usr/bin/env python3
"""cinetoro-2026-crudo.py — la parrilla de CINETORO 2026 → crudo.

LAS FUENTES (cinetoro.org, bajadas a fuentes/cinetoro-2026/ por `correr.py
--bajar`, declaradas en `fuentes_vivas`):
  · programacion-2026-2.html — LA PARRILLA. Cada actividad es un bloque
        <título…> / <rótulo> / Fecha: … / Lugar: … / Hora: … / <acceso>
    con un botón «programa» que apunta a un ancla de programas-2.
  · programas-2.html — LOS PROGRAMAS: cada ancla (#traducir, #Especies…) trae
    el nombre, el texto curatorial y sus obras como «Título | Dirección» +
    «Año | País | Categoría».
  · festivals/staging/cinetoro-2026-catalogo.json — el catálogo del
    pre-onboarding (las 4 páginas de la selección): CÓMO es cada obra.

QUIÉN MANDA EN QUÉ (PROTOCOLO §2·ter, la fusión):
  · la tarjeta del programa (programas-2) decide QUÉ obras tiene cada programa;
  · la ficha del catálogo completa CÓMO es cada una (dirección, país, año,
    duración, sinopsis). Donde la tarjeta escribe distinto que la ficha, manda
    la ficha y la diferencia queda en DIFERENCIAS (para el reporte a Juan);
  · las obras que NO están en el catálogo (Cinetoro al aula, retrospectiva de
    invitadas) entran con lo que dice la tarjeta.

CRITERIO DE JUAN (31 oct 2026): solo los días oficiales, 10–15 nov — Roldanillo
(10 nov, Museo Rayo) y Toro (11–15 nov, en veredas y corregimientos por el
terremoto). Fuera, con su porqué en `_fuera`: Bogotá, Cali (incluido el
lanzamiento del 7 nov: no es día oficial, Juan 31 oct), Palmira, el Laboratorio Hibridaciones
(«Solo para participantes aceptados») y el taller exclusivo Univalle.

ACCESO: Roldanillo «ENTRADA LIBRE» por actividad; Toro, la frase de la sección
«Toda la programación es ENTRADA LIBRE, excepto los talleres, que requieren
inscripción previa»; los talleres, «Inscripción previa» con su enlace
(ficcali.com/cine-expandido-2026/#talleres); el lanzamiento, «EVENTO CON
BOLETERÍA» (sin enlace de compra publicado).

COBERTURA INVERSA: todo bloque «Fecha:» de la parrilla tiene que estar en
LECTURA o en DESCARTADOS_JUAN; si la web suma uno, el script frena.

Escribe festivals/staging/cinetoro-2026-crudo.json
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance  # noqa: E402

SRC = f'{REPO}/fuentes/cinetoro-2026'
CATALOGO = f'{REPO}/festivals/staging/cinetoro-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/cinetoro-2026-crudo.json'
URL_PARRILLA = 'https://cinetoro.org/programacion-2026-2/'
URL_PROGRAMAS = 'https://cinetoro.org/programas-2/'
TALLERES = 'https://ficcali.com/cine-expandido-2026/#talleres'
LIBRE = 'Entrada libre'
# «Toda la programación es ENTRADA LIBRE, excepto los talleres, que requieren
# inscripción previa»: la excepción es la inscripción, no un precio. Sin aviso de
# pago es libre (regla de Juan, 13 oct 2026).
LIBRE_INSCRIPCION = 'Entrada libre con inscripción previa'

SEL, AULA, ACAD, ESP = 'Selección Oficial', 'Cinetoro al Aula', 'Programación Académica', 'Especial'

# ── LA LECTURA DE LA PARRILLA: los bloques que entran ───────────────────────────────────────────────
# clave = la línea de título TAL CUAL en la parrilla (con la que se encuentra el
# bloque). `titulo` = el que se publica: el nombre del festival, en caja de
# oración cuando la web lo grita (las secciones y programas los pone en Título
# ensamblar.py con caja.py). `ancla` = el programa de programas-2 cuyas obras
# lleva. `sesiones` = días/horas cuando el bloque trae más de uno.
LECTURA = {
    'Panel: archivos, fabulaciones y resistencias con Azul Aizemberg, Cristina Hadwa y Martha Hincapie. Modera Laura Alhach': dict(
        titulo='Panel: archivos, fabulaciones y resistencias', seccion=ACAD, tipo='evento',
        event_kind='evento', invitados='Azul Aizemberg, Cristina Hadwa y Martha Hincapie. Modera Laura Alhach',
        ancla_texto='invitadas'),
    'Traducir lo propio': dict(
        # el Programa No 1 es UNA sola obra (un mediometraje de 60 min): se
        # publica como la obra, no como un programa de un elemento
        titulo='Traducir lo propio (o el síntoma de recordar)', seccion=SEL, ancla='traducir', una_obra=True),
    'Postales y mapas de límites convergentes. Música y animación en vivo. Colectivo CINETORO': dict(
        titulo='Postales y mapas de límites convergentes', seccion=ESP, tipo='evento',
        event_kind='evento', invitados='Música y animación en vivo. Colectivo CINETORO'),
    'Toda tierra anhela el sol / Programa especial de animación': dict(
        titulo='Toda tierra anhela el sol', seccion=AULA, ancla='tierra'),
    'Especies de espacios': dict(titulo='Especies de espacios', seccion=SEL, ancla='Especies'),
    'CINETORO AL AULA / Huellas de una generación pasada': dict(
        titulo='Huellas de una generación pasada', seccion=AULA, ancla='Huellas',
        _nota='la parrilla dice «09:00 a 13:00 (Dos funciones)» sin la hora de cada una: '
              'se publica UNA función a las 09:00 con la franja entera'),
    'TALLER NICOLE ANTEBI: Moviendo montañas': dict(
        titulo='Taller Nicole Antebi: Moviendo montañas', seccion=ACAD, tipo='evento', event_kind='taller',
        acceso=LIBRE_INSCRIPCION, registration_url=TALLERES,
        sesiones=[('2026-11-12', '09:00', '13:00'), ('2026-11-13', '09:00', '13:00')]),
    'Cartografías de un cuerpo en movimiento': dict(
        titulo='Cartografías de un cuerpo en movimiento', seccion=SEL, ancla='cartografia'),
    'Cuerdas cruzadas': dict(
        titulo='Intermedio musical: Cuerdas cruzadas', seccion=ESP, tipo='evento', event_kind='evento',
        invitados='Jerónimo Saldarriaga'),
    'Apariencia de un mundo indeseado o una realidad absoluta': dict(
        titulo='Apariencia de un mundo indeseado o una realidad absoluta', seccion=SEL, ancla='apariencia'),
    'TALLER archivo con el centro de memoria toro POR LAURA ALHACH': dict(
        titulo='Taller archivo con el Centro de Memoria Toro', seccion=ACAD, tipo='evento',
        event_kind='taller', invitados='Laura Alhach', acceso=LIBRE_INSCRIPCION, registration_url=TALLERES,
        sesiones=[('2026-11-13', '15:00', '18:00'), ('2026-11-14', '09:00', '12:00')]),
    'Territorios infinitos en territorios finitos': dict(
        # el botón de la parrilla apunta a edicion-2025/programas-2/#infinitos
        # (enlace viejo); el ancla vive en programas-2 de 2026
        titulo='Territorios infinitos en territorios finitos', seccion=SEL, ancla='infinitos'),
    'Vestigios de un sueño inalcanzado': dict(
        titulo='Vestigios de un sueño inalcanzado', seccion=SEL, ancla='vestigios'),
    'Performance: Vendrán otros mares: Vendrán otras bárbaras a través de los mares (Cristina Hadwa y Laura Alhach)': dict(
        titulo='Performance: Vendrán otros mares: Vendrán otras bárbaras a través de los mares',
        seccion=ESP, tipo='evento', event_kind='evento', invitados='Cristina Hadwa y Laura Alhach'),
    'Bajo una lluvia ajena': dict(
        titulo='Bajo una lluvia ajena', seccion=ESP, director='Martha Hincapie',
        _nota='«Largo invitado» en la parrilla'),
    'El azul del horizonte': dict(titulo='El azul del horizonte', seccion=SEL, ancla='azul'),
    'PRENDER LA LUZ': dict(titulo='Prender la luz', seccion=SEL, ancla='luz'),
    'Mapping geografías en transformación por el colectivo AZMA': dict(
        titulo='Mapping geografías en transformación', seccion=ESP, tipo='evento', event_kind='evento',
        invitados='Colectivo AZMA', _nota='«CINETORO EXPANDIDO»'),
    'MUESTRA DE RESULTADOS TALLERES NICOLE ANTEBI Y MAIA GATTÁS': dict(
        titulo='Muestra de resultados talleres Nicole Antebi y Maia Gattás', seccion=ESP, tipo='evento',
        event_kind='evento', _nota='«CINETORO EXPANDIDO»'),
    'Líneas imaginarias': dict(titulo='Líneas imaginarias', seccion=SEL, ancla='lineas'),
    'PREMIACIÓN – MUESTRA DE PROCESOS Y CIERRE': dict(
        titulo='Premiación – muestra de procesos y cierre', seccion=ESP, tipo='evento', event_kind='clausura',
        duracion_min=120, _duracion_de='hueco hasta el karaoke (22:30), misma sede'),
    # sin hora de fin en la parrilla y última del día: se entra y se sale (`info`)
    'KARAOKE HÍBRIDO': dict(titulo='Karaoke híbrido', seccion=ESP, tipo='evento', event_kind='evento', info=True),
}

# ── LOS BLOQUES QUE NO ENTRAN (criterio de Juan, 31 oct 2026) ──────────────────────────
DESCARTADOS_JUAN = {
    'Lanzamiento CINETORO EXPERIMENTAL 19 / Límites Convergentes': 'Cali (7 nov), fuera de los días oficiales 10–15 nov (Juan, 31 oct)',
    'Lanzamiento CINETORO EN BOGOTÁ – INVITADA MAIA GATTÁS': 'Bogotá (15 oct, ya ocurrió)',
    'MASTER CLASS NICOLE ANTEBI: Hago cosas que se mueven, se repiten y, a veces, sostienen.': 'Bogotá (5 nov)',
    'SEMINARIO FICCALI Maia Gattás / ALIANZA FICCALI – YAWA – ERMITAÑAS': 'Cali, fuera de los días oficiales (20 oct, ya ocurrió)',
    'TALLER DE CINE ATMOSFÉRICO Maia Gattás CALI / ALIANZA FICCALI – YAWA – ERMITAÑAS': 'Cali, fuera de los días oficiales (21–23 oct, ya ocurrió)',
    'MASTER CLASS Azul Aizemberg: Profanaciones, resistencias y fabulaciones (Contra)usos de archivo en EL cine': 'Cali, fuera de los días oficiales (6 nov)',
    'Taller de animación Nicole Antebi: Postales infinitas': '«Evento exclusivo Univalle» (Cali, 9–11 nov)',
    'Taller AZMA / Creación de Contenido Inmersivo para Domo': 'Cali (YAWA, 9–11 nov): fuera del criterio de Juan',
    'HABITAR EL ARCHIVO': 'Palmira (6 nov)',
    'LABORATORIO HIBRIDACIONES': '«Solo para participantes aceptados»',
}

# La tarjeta del programa escribe distinto que la ficha del catálogo: estas
# son la MISMA obra (mismo programa, misma dirección o mismo país). Lo demás
# casa por título normalizado.
ALIAS = {
    'wild yeasts': 'Wild Yeast',
    'muchas muchas gracias thanks so so much': 'Muchas, muchas gracias',
}
# Obras fuera del catálogo que la tarjeta escribe en mayúscula sostenida: caja
# de oración (como «catalogo_titulo» en -correcciones.json); las palabras, del festival.
CAJA = {
    'LA TAQUIGRAFISTA': 'La taquigrafista',
    'LAS PICAPIEDRERAS': 'Las picapiedreras',
    '100 VISTAS PARCIALMENTE OSCURECIDAS': '100 vistas parcialmente oscurecidas',
    'PUBLIC DOMAIN REVIEW ANIMATED INTERVENTION': 'Public Domain Review Animated Intervention',
    'FOUR PERCENT': 'Four Percent',
    'SUSURROS': 'Susurros',
    'LA BARAJA DE MIRIAM': 'La baraja de Miriam',
}


def texto(fragmento):
    s = re.sub(r'(?s)<(script|style).*?</\1>', '', fragmento)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'</(p|div|h\d|li|tr|td|a|span)>', '\n', s)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    return [re.sub(r'\s+', ' ', l).strip() for l in s.split('\n') if l.strip()]


def minutos(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def dur(h0, h1):
    d = minutos(h1) - minutos(h0)
    return d if d > 0 else d + 24 * 60          # «22:00 a 00:00»


def fecha(s):
    m = re.search(r'(\d{1,2})\s*/\s*(\d{2})\s*/\s*(\d{4})', s)
    return f'{m.group(3)}-{m.group(2)}-{int(m.group(1)):02d}'


def horas(s):
    hs = re.findall(r'(\d{2}:\d{2})', s)
    return hs[0], (hs[1] if len(hs) > 1 else None)


# ── programas-2: ancla → (texto, obras) ──────────────────────────────────────
# Las anclas del HTML no sirven para cortar (id="lineas" aparece tres veces, en
# secciones que no son la suya): se corta por el NOMBRE de cada programa, que
# es la línea que la página escribe en mayúsculas, y se le asigna su ancla.
NOMBRES = {
    'Huellas de una generación pasada': 'Huellas',
    'Toda tierra anhela el sol': 'tierra',
    'TRADUCIR LO PROPIO (Programa inaugural)': 'traducir',
    'ESPECIES DE ESPACIOS': 'Especies',
    'CARTOGRAFÍAS DE UN CUERPO EN MOVIMIENTO': 'cartografia',
    'APARIENCIA DE UN MUNDO INDESEADO O UNA REALIDAD ABSOLUTA': 'apariencia',
    'TERRITORIOS INFINITOS EN TERRITORIOS FINITOS': 'infinitos',
    'VESTIGIOS DE UN SUEÑO INALCANZADO': 'vestigios',
    'EL AZUL DEL HORIZONTE': 'azul',
    'PRENDER LA LUZ': 'luz',
    'LÍNEAS IMAGINARIAS': 'lineas',
    'HABITAR EL ARCHIVO': 'habitar',
    'LÍMITES CONVERGENTES- CALI': 'LIMITES',
    'ARCHIVOS, FABULACIONES Y RESISTENCIAS': 'invitadas',
}


def programas():
    s = io.open(f'{SRC}/programas-2.html', encoding='utf-8').read()
    ls = texto(s[s.find('<body'):])
    ls = ls[max(k for k, l in enumerate(ls) if l == 'Programas'):]
    cortes = [(k, NOMBRES[l]) for k, l in enumerate(ls) if l in NOMBRES]
    falta = set(NOMBRES.values()) - {a for _, a in cortes}
    if falta or len(cortes) != len(NOMBRES):
        sys.exit(f'✗ programas-2: no se hallaron {sorted(falta)} (o hay nombres repetidos)')
    out = {}
    for n, (k0, ancla) in enumerate(cortes):
        k1 = cortes[n + 1][0] if n + 1 < len(cortes) else len(ls)
        obras, prosa, k = [], [], k0 + 1
        while k < k1:
            l = ls[k]
            if '|' in l and k + 1 < k1 and 'categor' in ls[k + 1].lower():
                t, d = [x.strip() for x in l.split('|')[:2]]
                meta = [x.strip() for x in ls[k + 1].split('|')]
                anio = next((int(x) for x in meta if re.fullmatch(r'20\d\d', x)), None)
                pais = next((x for x in meta if x and not re.fullmatch(r'0?2?\d{2,3}', x)
                             and not x.lower().startswith('categor')), None)
                obras.append({'titulo': t, 'director': d, 'anio': anio, 'pais_tarjeta': pais})
                k += 2
                continue
            if not obras and len(l) > 140:
                prosa.append(l)
            k += 1
        out[ancla] = {'texto': '\n\n'.join(prosa), 'obras': obras}
    return out


# ── la parrilla: título → bloque ─────────────────────────────────────────────
def parrilla():
    s = io.open(f'{SRC}/programacion-2026-2.html', encoding='utf-8').read()
    ls = texto(s[s.find('BOGOT'):])
    bloques = {}
    for i, l in enumerate(ls):
        if not l.startswith('Fecha:'):
            continue
        cab = ls[max(0, i - 6):i]
        lugar = next(x for x in ls[i:i + 3] if x.startswith('Lugar:'))[6:].strip()
        hora = next(x for x in ls[i:i + 4] if x.startswith('Hora:'))[5:].strip()
        tras = ls[i + 3:i + 6]
        bloques[i] = {'cab': cab, 'fecha': l[6:].strip(), 'lugar': lugar, 'hora': hora, 'tras': tras}
    return bloques


def bloque_de(bloques, clave):
    hits = [b for b in bloques.values() if clave in b['cab']]
    if len(hits) != 1:
        sys.exit(f'✗ «{clave}»: {len(hits)} bloques en la parrilla (se esperaba 1)')
    return hits[0]


LUGARES = {
    'CCMI': 'CCMI',
    'Museo Rayo': 'Museo Rayo',
    'Coliseo Corregimiento de San Francisco': 'Coliseo Corregimiento de San Francisco',
    'Mambo House, San Antonio': 'Mambo House',
    'Hotel Miracruz': 'Hotel Miracruz',
    'Polideportivo (San Antonio)': 'Polideportivo San Antonio',
    # el intermedio va ENTRE los programas 3 y 4, que son en el Polideportivo
    # (19:00–20:00 y 21:00–22:00): se publica ahí (inferido, se pregunta)
    'Mambo House / Polideportivo (San Antonio)': 'Polideportivo San Antonio',
    'Por confirmar': 'Por confirmar',
    'Coliseo: Institución Educativa Fray José Joaquín Escobar': 'Coliseo Institución Educativa Fray José Joaquín Escobar',
    'Vereda de Patio bonito': 'Vereda Patio Bonito',
    'POR DEFINIR': 'Por definir',
    'Rosalia´s Garden': "Rosalia's Garden",
}


def main():
    cat = {norm(o['titulo']): o for o in json.load(io.open(CATALOGO, encoding='utf-8'))['obras']}
    progs = programas()
    bloques = parrilla()
    # cobertura inversa: cada bloque de la parrilla, dentro o fuera
    claves = list(LECTURA) + list(DESCARTADOS_JUAN)
    for b in bloques.values():
        if not any(c in b['cab'] for c in claves):
            sys.exit(f'✗ bloque de la parrilla sin decidir: {b["cab"][-3:]} {b["fecha"]}')
    for c in DESCARTADOS_JUAN:
        bloque_de(bloques, c)

    difs, usadas, funcs = [], set(), []

    def obra(o):
        k = norm(o['titulo'])
        c = cat.get(norm(ALIAS.get(k, o['titulo'])))
        if not c and o['titulo'].startswith('maps of'):
            c = cat.get(norm('Maps of Wilderness'))
        if not c:
            # fuera del catálogo (Cinetoro al aula, retrospectiva de invitadas):
            # lo que dice la tarjeta
            x = {'titulo': CAJA.get(o['titulo'], o['titulo']), 'director': o['director']}
            if o['anio']:
                x['anio'] = o['anio']
            if o['pais_tarjeta']:
                x['pais'] = o['pais_tarjeta']
            return x
        usadas.add(c['titulo'])
        for campo, a, b in (('título', o['titulo'], c['titulo']), ('dirección', o['director'], c['director'])):
            if norm(a) != norm(b):
                difs.append(f'{c["titulo"]}: {campo} tarjeta «{a}» / ficha «{b}»')
        x = {'titulo': c['titulo'], 'director': c['director'], 'pais': c['pais'], 'anio': c['anio']}
        if c.get('duracion_min'):
            x['duracion_min'] = c['duracion_min']
        if c.get('sinopsis'):
            x['sinopsis'] = c['sinopsis'].replace('\n', ' ')
        return x

    for clave, a in LECTURA.items():
        b = bloque_de(bloques, clave)
        lugar = b['lugar']
        if lugar not in LUGARES:
            sys.exit(f'✗ «{clave}»: sede «{lugar}» sin entrada en LUGARES')
        sede = LUGARES[lugar]
        dia0 = fecha(b['fecha'])
        if a.get('acceso'):
            acceso = a['acceso']
        elif sede == 'CCMI':
            acceso = 'Evento con boletería'
        else:
            # Roldanillo lo dice por actividad; Toro, una vez para toda la sección
            acceso = LIBRE
        sesiones = a.get('sesiones') or [(dia0, *horas(b['hora']))]
        for (dia, h0, h1) in sesiones:
            f = {'titulo': a['titulo'], 'dia': dia, 'hora': h0, 'sede': sede, 'sala': '',
                 'seccion': a['seccion'], 'acceso': acceso,
                 '_src': {'url': URL_PARRILLA, 'bloque': clave, 'fecha': b['fecha'], 'lugar': lugar,
                          'hora': b['hora']}}
            if 'is_free' in a:
                f['is_free'] = a['is_free']
            if a.get('registration_url'):
                f['registration_url'] = a['registration_url']
            for k in ('tipo', 'event_kind', 'invitados', 'director', '_nota', 'info'):
                if a.get(k):
                    f[k] = a[k]
            if len(sesiones) > 1:
                f['is_recurring'] = True
            if a.get('duracion_min'):
                f['duracion_min'], f['_duracion_de'] = a['duracion_min'], a['_duracion_de']
            if h1:
                f['duracion_min'] = dur(h0, h1)
                f['_duracion_de'] = 'la franja «Hora:» de la parrilla'
            if a.get('ancla_texto'):
                f['sinopsis'] = progs[a['ancla_texto']]['texto']
                f['_src']['programa'] = f'{URL_PROGRAMAS}#{a["ancla_texto"]}'
            if a.get('ancla'):
                p = progs[a['ancla']]
                f['_src']['programa'] = f'{URL_PROGRAMAS}#{a["ancla"]}'
                obs = [obra(o) for o in p['obras']]
                if a.get('una_obra'):
                    assert len(obs) == 1, a['titulo']
                    o = obs[0]
                    f.update({k: v for k, v in o.items() if k != 'titulo'})
                    f['titulo'] = o['titulo']
                    f['duracion_min'] = o.get('duracion_min') or f.get('duracion_min')
                    f['_duracion_de'] = 'la ficha del catálogo'
                else:
                    f['obras'] = obs
                    if p['texto']:
                        f['sinopsis'] = p['texto']
            funcs.append(f)

    funcs.sort(key=lambda f: (f['dia'], f['hora']))
    no_usadas = sorted(set(o['titulo'] for o in cat.values()) - usadas)
    d = {'_provenance': provenance('cinetoro.org — programacion-2026-2 (parrilla) + programas-2 (obras de cada '
                                   'programa) + el catálogo del pre-onboarding (fichas)'),
         'funciones': funcs,
         '_fuera': DESCARTADOS_JUAN,
         '_catalogo_sin_funcion': no_usadas,
         '_diferencias_tarjeta_ficha': difs}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    n_obras = sum(len(f.get('obras') or []) for f in funcs)
    print(f'✓ {len(funcs)} funciones, {n_obras} obras en programas → {os.path.relpath(OUT, REPO)}')
    print(f'  del catálogo sin función: {no_usadas}')
    for x in difs:
        print(f'  ≠ {x}')


if __name__ == '__main__':
    main()
