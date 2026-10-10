#!/usr/bin/env python3
"""ficpa-2026-crudo.py — la programación del 22 FICPA (Pasto, 13–17 oct 2026) → crudo.

LA FUENTE es la página «Programación oficial 2026» de ficcpa.co (WP, slug
`programacion2026`, modificada el 9 oct 2026), bajada por la API de WordPress
a fuentes/ficpa-2026/programacion2026.json. Es HTML estructurado, una tarjeta
por actividad:

    <div class="ficpa-programacion-dia" id="programacion-13">
      <div class="ficpa-funcion" data-categoria=… data-entrada=… data-sede=…>
        hora (y hora de fin) · <h3>título</h3> · <p>Dirección / Responsable: …
        · Duración: N min · Procedencia: …</p> · etiqueta · lugar · entrada

y al final la PROGRAMACIÓN ALTERNA, agrupada por sede (`ficpa-alt-grupo`): las
funciones en universidades, colegios y municipios de Nariño, con el día escrito
(«JUE 15») y las obras en el renglón de abajo («Título — Director; …»).

LOS PROGRAMAS. La página no los anida: pone una tarjeta-encabezado sin crédito
(«CORTOS INTERNACIONALES», 6:00 p. m.) y debajo, a la MISMA hora y con la misma
etiqueta, una tarjeta por obra. Eso se lee como un programa con sus obras. Un
encabezado con una sola obra debajo es esa obra (el «LARGOMETRAJE COLOMBIANO DE
FICCIÓN» de El Huaquero). El encabezado del seminario y el de la gala nariñense
no agrupan: sus tarjetas son ponencias y una película con otra etiqueta, que se
publican solas.

LA SECCIÓN es la de la Selección Oficial (página `seleccionados2026`): «Ecos del
Mundo» y «Latidos del Cine Colombiano» (Selección Sol de los Pastos), «Cámaras
de Barniz» y «Churo Cósmico». Las actividades van en «Academia» o «Industria»,
los dos nombres del menú del sitio.

LO QUE NO SE INVENTA: la duración de los cortos sin «Duración» (la completa
TMDB o queda vacía) y la de las actividades sin hora de fin (DURACION_POR_DEFECTO).
"""
import html
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import banderas, provenance  # noqa: E402

FID = 'ficpa-2026'
DIR = f'{REPO}/fuentes/{FID}'
FUENTE = f'{DIR}/programacion2026.json'
SELECCION = f'{DIR}/seleccionados2026.json'
INAUGURAL = f'{DIR}/pelicula-inagural26.json'
OUT = f'{REPO}/festivals/staging/ficpa-2026-crudo.json'
URL = 'https://www.ficpa.co/programacion2026/'
DURACION_POR_DEFECTO = 90
DIA_DE = {'13': '2026-10-13', '14': '2026-10-14', '15': '2026-10-15', '16': '2026-10-16', '17': '2026-10-17'}

# ── LO QUE QUEDA FUERA. La regla de Mamut y Popayán: lo que el público no puede
# ver no se publica. Cada línea, con su porqué.
FUERA_CATEGORIA = {
    'Film in Progress': 'solo para proyectos participantes previamente inscritos (lo dice la tarjeta)',
    'Función privada': '«Con invitación de la producción»',
    'Networking': '«Cóctel de cortesía para acreditados» / «Con acreditación»',
}
FUERA_TITULO = {
    'ENCUENTRO DEL SECTOR AUDIOVISUAL NARIÑENSE':
        '«Espacio para personas nariñenses vinculadas al sector»: no es para el público',
}
# Pitch de Films in Progress del viernes: la tarjeta dice «Entrada libre», se queda
FUERA_EXCEPTO = {'FILMS IN PROGRESS – Pitch de proyectos participantes'}
# PROGRAMACIÓN ALTERNA: grupos de sede que quedan fuera (decisión pendiente de Juan,
# 10 oct 2026: propuesta = colegios fuera, municipios dentro)
ALTERNA_FUERA = {
    'I.E. Luis Eduardo Mora Osejo': 'funciones dentro de un colegio, para sus estudiantes',
    'I.E. San Juan Bosco': 'funciones y taller dentro de un colegio',
    'Chachagüí · I.E. Chachagüí': 'taller dentro de un colegio',
    'Yacuanquer · I.E. de Concentración de Desarrollo Rural': 'taller dentro de un colegio',
    'La Florida · I.E. de la Inmaculada de Robles': 'taller dentro de un colegio',
    'Centro Comercial Único · Cinemas Royal Films PELICULA EN ALIANZA FUERA DE LA PROGRAMACIÓN OFICIAL':
        'el festival la declara «fuera de la programación oficial»',
}

# ── LOS TÍTULOS. La tarjeta mete en el título lo que es nota de la función
# («– Con presencia del director», «largometraje colombiano documental»). El
# título publicado es el de la obra, tal como lo escribe la Selección Oficial
# en frase; la presencia del equipo va como has_qa.
TITULO = {
    # errata del festival: el corto de Sandra Rengifo es «AtmoSphaira» (IMDb
    # nm5653494 y CineAutopsia 2026); corregido con OK de Juan, 10 oct
    'AtmaSphaira': 'AtmoSphaira',
    'Película Inaugural: Lactar': 'Lactar',
    'Cautivo – Con presencia del productor Alfredo Brito': 'Cautivo',
    'Corrientes del Amazonas, largometraje colombiano documental – en presencia del director': 'Corrientes del Amazonas',
    'Allá, Cartas al Corazón, largometraje internacional documental – en presencia del director con presencia de FICTEQ': 'Allá, cartas al corazón',
    'Sierra, el álbum mortuorio – Con presencia del director': 'Sierra: el álbum mortuorio',
    'Achikanain – Con presencia del director': 'Achikanain',
    '“Pacto de libertad” – Película nariñense de ficción. Con presencia del director': 'Pacto de libertad',
    'FUNCIÓN DE CLAUSURA CORTO CON AUDIODESCRIPCIÓN Y LENGUAJE DE SEÑAS: BUSCANDO A PAPÁ. Dir. Mauro Andrade. Apoya: Smartfilms Colombia': 'Buscando a papá',
    'Conversatorio especial con la directora y periodista María Jimena Duzán. Proyección “Después del Frío” Largo Col Doc':
        'Conversatorio con María Jimena Duzán y proyección de «Después del frío»',
    'Apertura exposición de fotogramas “Nariño Como Locación Cinematográfica” y “Vitrina de servicios audiovisuales”. Exposición extendida hasta el viernes 16 de octubre de 2026':
        'Apertura de la exposición «Nariño como locación cinematográfica» y «Vitrina de servicios audiovisuales»',
    'CEREMONIA DE PREMIACIÓN Y CLAUSURA': 'Ceremonia de premiación y clausura',
    'FILMS IN PROGRESS – Pitch de proyectos participantes': 'Films in Progress: pitch de proyectos participantes',
    'Taller Nuestro Talento: “Galeras 2037. Del plano al mundo jugable (AAA aplicados al cine)”':
        'Taller Nuestro Talento «Galeras 2037. Del plano al mundo jugable (AAA aplicados al cine)»',
}
QA = re.compile(r'(?i)presencia del (director|productor)')
# encabezados de programa: el título del programa, en frase
PROGRAMA = {
    'CORTOS INTERNACIONALES': 'Cortos internacionales',
    'CORTOS COLOMBIANOS DE FICCIÓN Y DOCUMENTAL': 'Cortos colombianos de ficción y documental',
    'VIDEOCLIPS NARIÑENSES – Duración total 30 min': 'Videoclips nariñenses',
    'CORTOMETRAJE NARIÑENSE': 'Cortometraje nariñense',
}
# encabezados que NO agrupan (sus tarjetas se publican solas)
ENCABEZADO_SOLO = {'SEMINARIO CINE EN MIL PALABRAS – PONENCIAS', 'GALA DE CINE NARIÑENSE',
                   'LARGOMETRAJE COLOMBIANO DE FICCIÓN'}

# ── LAS ACTIVIDADES: etiqueta de la tarjeta → event_kind (palabra del festival)
KIND = {'Master Class': 'masterclass', 'Conversatorio': 'conversatorio', 'Exposición': 'apertura',
        'Taller': 'taller', 'Seminario': 'seminario', 'Ponencia': 'ponencia', 'Foro': 'foro',
        'Encuentro': 'encuentro', 'Film in Progress': 'evento', 'Clausura': 'acto', 'Cine foro': 'foro'}
INDUSTRIA = {'Film in Progress', 'Encuentro'}
SECCION_ACADEMIA, SECCION_INDUSTRIA, SECCION_CLAUSURA = 'Academia', 'Industria', 'Clausura'
# LA PROGRAMACIÓN ALTERNA que no es de la Selección va con el nombre que le da el
# sitio; los programas temáticos de Churo Cósmico (identidades, sociedad y
# libertades, trabajo, animación) son de su sección aunque lleven un corto colegial
SECCION_ALTERNA = 'Programación alterna'
CHURO = re.compile(r'(?i)churo|identidades|sociedad y libertades|trabajo, econom|^animaci')
# la Selección: subtítulo de la página → sección publicada
GRUPO_SECCION = {'ECOS DEL MUNDO': 'Ecos del Mundo', 'LATIDOS DEL CINE COLOMBIANO': 'Latidos del Cine Colombiano',
                 'SELECCIÓN CÁMARAS DE BARNIZ – CINE NARIÑENSE': 'Cámaras de Barniz',
                 'SELECCIÓN CHURO CÓSMICO – SECCIÓN TEMÁTICA': 'Churo Cósmico'}

# ── LAS SEDES: lo que imprime la tarjeta → (sede, sala, ciudad)
SEDES = {
    'Casa de la Cultura': ('Casa de la Cultura', '', 'Pasto'),
    'Universidad Mariana, Auditorio Jesús de Nazareth': ('Universidad Mariana', 'Auditorio Jesús de Nazareth', 'Pasto'),
    'Universidad Mariana, Auditorio San José': ('Universidad Mariana', 'Auditorio San José', 'Pasto'),
    'Universidad CESMAG, Auditorio Santa Clara': ('Universidad CESMAG', 'Auditorio Santa Clara', 'Pasto'),
    'Cinemas Valle de Atriz, sala 2': ('Cinemas Valle de Atriz', 'Sala 2', 'Pasto'),
    'Banco de la República, Sala Múltiple': ('Banco de la República', 'Sala Múltiple', 'Pasto'),
    'Banco de la República, Sala Emi': ('Banco de la República', 'Sala Emi', 'Pasto'),
    'Banco de la República, Sala de apoyo': ('Banco de la República', 'Sala de Apoyo', 'Pasto'),
    'Banco de la República, Sala de Apoyo': ('Banco de la República', 'Sala de Apoyo', 'Pasto'),
    'Banco de la República, Sala Apoyo': ('Banco de la República', 'Sala de Apoyo', 'Pasto'),
    'Teatro Colombia': ('Teatro Colombia', '', 'Pasto'),
    'Casa Paramo': ('Casa Páramo', '', 'Pasto'),
    # programación alterna: el título del grupo
    'Universidad de Nariño · Sede Torobajo · Sala de Proyecciones Biblioteca': ('Universidad de Nariño, Sede Torobajo', 'Sala de Proyecciones Biblioteca', 'Pasto'),
    'Universidad Cooperativa de Colombia · Torobajo · Sala de Audiencias': ('Universidad Cooperativa de Colombia, Torobajo', 'Sala de Audiencias', 'Pasto'),
    'Universidad CESMAG · Salón de Teatro': ('Universidad CESMAG', 'Salón de Teatro', 'Pasto'),
    'Casa Páramo Cine Club': ('Casa Páramo', '', 'Pasto'),
    'Universidad Mariana · Sala Audiovisual Pedro Schumacher': ('Universidad Mariana', 'Sala Audiovisual Pedro Schumacher', 'Pasto'),
    'Fundación Universitaria San Martín · Sede Mijitayo': ('Fundación Universitaria San Martín, Sede Mijitayo', '', 'Pasto'),
    'Corregimiento Jamondino · Salón Comunal El Rosario': ('Salón Comunal El Rosario, Jamondino', '', 'Pasto'),
    'Chachagüí': ('Chachagüí', '', 'Chachagüí'),
    'Yacuanquer · Parque Principal': ('Parque Principal de Yacuanquer', '', 'Yacuanquer'),
    'La Florida · Parque Principal': ('Parque Principal de La Florida', '', 'La Florida'),
}
# la tarjeta abrevia el título que la Selección da completo
ALIAS_SELECCION = {'Tierra Palestina': 'TIERRA PALESTINA. CAMBIO GLOBAL'}
DIA_ALT = re.compile(r'(LUN|MAR|MIÉ|JUE|VIE|SÁB)\s+(\d{1,2})')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def txt(r):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', r or ''))).strip()


def hora_ampm(h):
    m = re.match(r'(\d{1,2}):(\d{2})\s*([ap])m', h.strip().lower())
    if not m:
        return None
    hh = int(m.group(1)) % 12 + (12 if m.group(3) == 'p' else 0)
    return f'{hh:02d}:{m.group(2)}'


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def frase(s):
    """CAJA SOSTENIDA → frase (caja-sostenida): primera letra en mayúscula."""
    if s.isupper():
        s = s.lower()
        return s[:1].upper() + s[1:]
    return s


def seleccion():
    """Título normalizado → {seccion, director, pais} de la Selección Oficial."""
    c = json.load(io.open(SELECCION, encoding='utf-8'))[0]['content']['rendered']
    L = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', c)).split('\n') if x.strip()]
    out, sec, i = {}, None, 0
    while i < len(L):
        x = L[i]
        if x in GRUPO_SECCION:
            sec = GRUPO_SECCION[x]
        elif x.startswith('▸ '):
            t = x[2:].strip()
            d = {'seccion': sec, 'titulo_seleccion': t}
            j = i + 1
            while j < len(L) and not L[j].startswith('▸ ') and L[j] not in GRUPO_SECCION and j < i + 7:
                if L[j] == 'Dirección:' and j + 1 < len(L):
                    d['director'] = L[j + 1]
                if L[j].startswith('País/Ciudad') and j + 1 < len(L):
                    d['pais'] = L[j + 1]
                j += 1
            out.setdefault(plano(t), d)      # una obra en dos secciones: la primera
        i += 1
    return out


def credito(ps):
    d = {}
    for p in ps:
        m = re.search(r'Dirección / Responsable:\s*([^·]+)', p)
        if m:
            d['director'] = m.group(1).strip()
        m = re.search(r'Duración:\s*(\d+)\s*min', p)
        if m:
            d['duracion_min'] = int(m.group(1))
        m = re.search(r'Procedencia:\s*(.+)$', p)
        if m:
            d['procedencia'] = m.group(1).strip()
    return d


def tarjetas():
    c = json.load(io.open(FUENTE, encoding='utf-8'))[0]['content']['rendered']
    oficial, alterna = [], []
    partes = re.split(r'<div class="ficpa-programacion ficpa-programacion-dia" id="programacion-([^"]+)">', c)
    for i in range(1, len(partes), 2):
        cuerpo = partes[i + 1].split('class="ficpa-alt-grupo"')[0]
        for f in cuerpo.split('<div class="ficpa-funcion"')[1:]:
            a = dict(re.findall(r'data-(\w+)="([^"]*)"', f.split('>')[0]))
            h = re.search(r'class="ficpa-hora">([^<]*)(?:<span class="ficpa-hora-fin">([^<]*))?', f)
            oficial.append({'dia': DIA_DE[partes[i]], 'hora': hora_ampm(h.group(1)),
                            'fin': hora_ampm(h.group(2) or '') if h.group(2) else None,
                            'titulo': txt(re.search(r'<h3>(.*?)</h3>', f, re.S).group(1)),
                            'ps': [txt(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', f, re.S)],
                            'categoria': html.unescape(a.get('categoria', '')),
                            'sede': txt((re.search(r'ficpa-nombre-lugar">(.*?)</strong>', f, re.S) or [None, ''])[1]),
                            'entrada': txt((re.search(r'ficpa-boleteria">(.*?)</span>', f, re.S) or [None, ''])[1])})
    k = c.find('class="ficpa-alt-grupo"')
    for g in c[k:].split('class="ficpa-alt-grupo"')[1:]:
        grupo = txt(re.search(r'ficpa-alt-sede-titulo">(.*?)</h3>', g, re.S).group(1))
        for f in g.split('<div class="ficpa-funcion-alterna"')[1:]:
            a = dict(re.findall(r'data-(\w+)="([^"]*)"', f.split('>')[0]))
            dtxt = txt(re.search(r'ficpa-alt-dia">(.*?)</div>', f, re.S).group(1))
            htxt = txt(re.search(r'ficpa-alt-hora">(.*?)</div>', f, re.S).group(1))
            hs = re.findall(r'\d{1,2}:\d{2}\s*[ap]m', htxt)
            for d in DIA_ALT.findall(dtxt) or [('', x) for x in re.findall(r'\b(1[3-7])\b', dtxt)]:
                alterna.append({'dia': DIA_DE[d[1]], 'hora': hora_ampm(hs[0]), 'fin': hora_ampm(hs[1]) if len(hs) > 1 else None,
                                'titulo': txt(re.search(r'<h3>(.*?)</h3>', f, re.S).group(1)),
                                'ps': [txt(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', f, re.S)],
                                'categoria': html.unescape(a.get('categoria', '')), 'grupo': grupo})
    return oficial, alterna


def obras_de_renglon(p):
    """«Título — Director; Título — Director (País). Duración: 38 min.» → obras."""
    p = re.sub(r'\s*Duración( total)?:\s*\d+\s*min\.?.*$', '', p).strip().rstrip('.')
    out = []
    for parte in re.split(r';\s*', p):
        m = re.match(r'(.+?)\s+—\s+(.+?)(?:\s+\(([^)]+)\))?$', parte.strip())
        if m:
            out.append({'titulo': m.group(1).strip(), 'director': m.group(2).strip(),
                        **({'pais': m.group(3)} if m.group(3) else {})})
    return out


def main():
    sel = seleccion()
    oficial, alterna = tarjetas()
    funciones, fuera = [], []

    def base(t, sede_txt):
        if sede_txt not in SEDES:
            sys.exit(f'✗ sede sin entrada en la tabla: {sede_txt!r}')
        sede, sala, ciudad = SEDES[sede_txt]
        return {'dia': t['dia'], 'hora': t['hora'], 'sede': sede, **({'sala': sala} if sala else {}),
                'ciudad': ciudad, '_src': {'url': URL, 'date': '2026-10-09'}}

    def obra_reg(t, titulo):
        o = sel.get(plano(titulo)) or {}
        cr = credito(t['ps'])
        r = {'titulo': titulo, 'director': cr.get('director') or o.get('director'),
             'pais': o.get('pais') or cr.get('procedencia')}
        if cr.get('duracion_min'):
            r['duracion_min'] = cr['duracion_min']
        return r, o.get('seccion')

    i = 0
    while i < len(oficial):
        t = oficial[i]
        cat, tit = t['categoria'], t['titulo']
        if tit not in FUERA_EXCEPTO and (cat in FUERA_CATEGORIA or tit in FUERA_TITULO):
            fuera.append(f'{t["dia"]} {t["hora"]} {tit[:60]}: {FUERA_CATEGORIA.get(cat) or FUERA_TITULO[tit]}')
            i += 1
            continue
        hijos = []
        if not t['ps'] or tit in PROGRAMA or tit in ENCABEZADO_SOLO:
            j = i + 1
            while j < len(oficial) and oficial[j]['dia'] == t['dia'] and oficial[j]['hora'] == t['hora'] \
                    and oficial[j]['categoria'] == cat and oficial[j]['ps']:
                hijos.append(oficial[j])
                j += 1
        if tit in ENCABEZADO_SOLO:
            fuera.append(f'{t["dia"]} {t["hora"]} {tit}: encabezado de bloque (sus tarjetas se publican solas)')
            i += 1
            continue
        if tit in PROGRAMA:
            reg = {'titulo': PROGRAMA[tit], **base(t, t['sede']), 'acceso': t['entrada'] or 'Entrada libre'}
            obras, secs = [], []
            for h in hijos:
                o, s = obra_reg(h, TITULO.get(h['titulo'], h['titulo']))
                if QA.search(h['titulo']):
                    reg['has_qa'], reg['qa_type'] = True, 'team'
                obras.append(o)
                secs.append(s)
            reg['obras'] = obras
            reg['seccion'] = next((s for s in secs if s), 'Latidos del Cine Colombiano')
            m = re.search(r'Duración total (\d+) min', tit)
            dur = sum(o.get('duracion_min') or 0 for o in obras)
            reg['duracion_min'] = int(m.group(1)) if m else (dur or None)
            funciones.append(reg)
            i = j
            continue
        if tit.startswith('Película Inaugural: Lactar'):
            tit = 'Película Inaugural: Lactar'      # el h3 trae pegado el homenaje y la nota de ingreso
        titulo = TITULO.get(tit, frase(tit) if tit.isupper() else tit)
        reg = {**base(t, t['sede']), 'acceso': t['entrada'] or 'Entrada libre'}
        if tit.startswith('FUNCIÓN DE CLAUSURA'):
            cat = 'Corto de clausura'                # es un corto (5 min), no un acto
        if cat == 'Exposición':
            # UNA EXPOSICIÓN SE VISITA, no se reserva (regla de MAPISTAS, 9 oct):
            # info:true. La tarjeta da la apertura (13 oct, 3 p. m.) y dice
            # «extendida hasta el viernes 16», sin horario de los otros días.
            reg['info'] = True
        if cat in KIND:
            reg.update(titulo=titulo, tipo='evento', event_kind=KIND[cat],
                       seccion=SECCION_INDUSTRIA if cat in INDUSTRIA else
                       (SECCION_CLAUSURA if cat == 'Clausura' else SECCION_ACADEMIA))
            cr = credito(t['ps'])
            if cr.get('director'):
                reg['invitados'] = f'A cargo de {cr["director"]}' + (f' ({cr["procedencia"]})' if cr.get('procedencia') else '') + '.'
            if cr.get('duracion_min'):
                reg['duracion_min'] = cr['duracion_min']
            # el evento con UNA obra adentro: el ensamblador lo titularía con la obra
            # y se perdería el conversatorio; la obra va en la descripción
            if 'Después del Frío' in tit:
                reg['sinopsis'] = 'Proyección de «Después del frío» (María Jimena Duzán, largometraje colombiano documental) y conversatorio con su directora.'
        else:
            o, s = obra_reg(t, titulo)
            reg.update(o)
            reg['seccion'] = SECCION_CLAUSURA if cat == 'Corto de clausura' else (
                s or ('Ecos del Mundo' if cat == 'Cortometrajes internacionales' else 'Latidos del Cine Colombiano'))
            if cat == 'Gala inaugural':
                reg['premiere'] = 'Inauguración'
            if tit.startswith('FUNCIÓN DE CLAUSURA'):
                reg['premiere'] = 'Clausura'
                reg['accesibilidad'] = 'Con audiodescripción y lengua de señas'
        if QA.search(tit):
            reg['has_qa'], reg['qa_type'] = True, 'team'
        if t['fin'] and not reg.get('duracion_min'):
            reg['duracion_min'] = mins(t['fin']) - mins(t['hora'])
        funciones.append(reg)
        i += 1

    # ── la programación alterna
    for t in alterna:
        if t['grupo'] in ALTERNA_FUERA:
            fuera.append(f'{t["dia"]} {t["hora"]} {t["titulo"][:50]} ({t["grupo"][:40]}): {ALTERNA_FUERA[t["grupo"]]}')
            continue
        reg = {**base(t, t['grupo']), 'acceso': 'Entrada libre'}
        reg['_src']['programacion'] = 'alterna'
        cat, tit = t['categoria'], t['titulo']
        p = ' '.join(t['ps'])
        obras = obras_de_renglon(p)
        if cat in ('Taller', 'Cine foro') and not obras:
            reg.update(titulo=tit, tipo='evento', event_kind=KIND.get(cat, 'evento'), seccion=SECCION_ACADEMIA)
        elif len(obras) >= 2 or cat in ('Cortometrajes', 'Animación'):
            secs = [sel[plano(o['titulo'])]['seccion'] for o in obras if plano(o['titulo']) in sel]
            reg.update(titulo=tit, obras=obras,
                       seccion='Churo Cósmico' if CHURO.search(tit) else
                       (max(set(secs), key=secs.count) if secs else SECCION_ALTERNA))
            m = re.search(r'Duración( total)?:\s*(\d+)\s*min', p)
            if m:
                reg['duracion_min'] = int(m.group(2))
            if not obras:
                reg['sinopsis'] = p.rstrip('.') + '.'
        else:
            # una película: «Largometraje … — Director. Procedencia: X. Duración: N min.»
            o = sel.get(plano(ALIAS_SELECCION.get(tit, tit))) or {}
            m = re.search(r'—\s*([^.]+)\.', p)
            reg.update(titulo=frase(tit), seccion=o.get('seccion') or SECCION_ALTERNA,
                       director=o.get('director') or (m.group(1).strip() if m else None), pais=o.get('pais'))
            d = re.search(r'Duración:\s*(\d+)\s*min', p)
            if d:
                reg['duracion_min'] = int(d.group(1))
            if cat == 'Cine foro':
                reg.update(titulo=tit, tipo='evento', event_kind='foro', seccion=SECCION_ACADEMIA,
                           sinopsis='Proyección de «Homo Plastic» (Julio Pérez del Campo, 71 min) y foro con Roberto Ramírez Espitia (México).')
                reg.pop('director', None); reg.pop('pais', None)
        if t['fin'] and not reg.get('duracion_min'):
            reg['duracion_min'] = mins(t['fin']) - mins(t['hora'])
        funciones.append({k: v for k, v in reg.items() if v not in (None, '')})

    # sinopsis oficial de la inaugural
    ina = json.load(io.open(INAUGURAL, encoding='utf-8'))[0]['content']['rendered']
    L = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', ina)).split('\n') if x.strip()]
    if 'SINOPSIS' in L:
        for f in funciones:
            if f.get('titulo') == 'Lactar':
                f['sinopsis'] = L[L.index('SINOPSIS') + 1]
    # LA DURACIÓN QUE NADIE DA: el hueco hasta la siguiente en la misma sede (la
    # regla de Mamut, Itagüí y Girardota), con DURACION_POR_DEFECTO de tope
    for f in funciones:
        if f.get('duracion_min') or f.get('tipo') == 'evento':
            continue
        sig = sorted(mins(g['hora']) for g in funciones if g['dia'] == f['dia'] and g['sede'] == f['sede']
                     and mins(g['hora']) > mins(f['hora']))
        hueco = sig[0] - mins(f['hora']) if sig else None
        f['duracion_min'] = hueco if hueco and hueco <= DURACION_POR_DEFECTO else DURACION_POR_DEFECTO
        f['_duracion_de'] = ('el hueco hasta la siguiente función en la misma sede' if hueco and hueco <= DURACION_POR_DEFECTO
                             else f'{DURACION_POR_DEFECTO} min declarados: la tarjeta no la da')
    for f in funciones:
        if not f.get('duracion_min') and f.get('tipo') == 'evento':
            f['duracion_min'] = DURACION_POR_DEFECTO
            f['_duracion_de'] = f'{DURACION_POR_DEFECTO} min declarados: la tarjeta no da hora de fin'
    # EL PAÍS. La tarjeta y la Selección dan PROCEDENCIA: un país («España,
    # Etiopía») o, para el cine colombiano, el municipio o el departamento
    # («Cali», «Valle del Cauca», «Guachucal, Cumbal - Nariño»). Lo que no es un
    # país reconocible es Colombia: el lugar no es el país y salía con globo.
    def pais(v):
        return v if (v and banderas(v)) else ('Colombia' if v else v)
    for f in funciones:
        for o in [f] + list(f.get('obras') or []):
            if o.get('pais'):
                o['pais'] = pais(o['pais'])
            # erratas del festival declaradas en TITULO, también dentro de un programa
            if o.get('titulo') in ('AtmaSphaira',):
                o['titulo'] = TITULO[o['titulo']]
        # COMILLAS RECTAS en el título ([title-normalization])
        f['titulo'] = f['titulo'].translate(str.maketrans({'“': '"', '”': '"', '«': '"', '»': '"'}))
    funciones = [{k: v for k, v in f.items() if v not in (None, '')} for f in funciones]
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('ficpa.co — Programación oficial 2026 (WP programacion2026) + Selección Oficial',
                                  url=URL, metodo='HTML estructurado de la página, tarjeta por tarjeta; '
                                                  'la sección y el crédito, de la página de seleccionados'),
        '_excluidas': fuera, 'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} funciones ({len(funciones) - n_ev} proyecciones + {n_ev} actividades) · '
          f'{len({f["sede"] for f in funciones})} sedes · {len(fuera)} fuera → {os.path.relpath(OUT, REPO)}')
    for x in fuera:
        print('   fuera ·', x)


if __name__ == '__main__':
    main()
