#!/usr/bin/env python3
"""fantasmagoria-2026-crudo.py — la parrilla de Fantasmagoría 8 → crudo.

LA FUENTE es la noticia «Ya puedes empezar a programarte para Fantasmagoría
2026» de la web del festival (wp-json post 6481, modificada el 28 sep 22:03
UTC), que el festival llama «adelanto de la Programación» y avisa «sujeta a
cambios». Va día por día (pestañas «Miércoles 14…» a «Domingo 25…»), con
bloques de la forma

    6:40pm || Selección Oficial de Largometrajes:
    El Despertar
    (Terror / Colombia, 2026, 96´) de Jaime Osorio Marquez, Federico Durán y …
    Cineprox – Las Américas (Sala 3) / Votación del Público / Entrada con Boleta

La primera línea da la HORA y el RÓTULO (la sección o la muestra); la del
paréntesis, género / país, año, duración y dirección; la última, la SEDE y,
separados por «/», los sellos y el ACCESO. Lo que va entre la ficha y la sede
(«Conversatorio con …») es texto del festival sobre la función.

Las obras de las siete selecciones ya están en el catálogo del pre-onboarding
(fantasmagoria-2026-catalogo.py, 47 obras): se cruzan por título. Las demás
—retrospectivas, muestras, aniversarios— se publican con la ficha que imprime
la propia parrilla y las enriquece la cascada de TMDB.

LO QUE NO SE INVENTA:
  · las 3 charlas virtuales por Twitch NO se montan: no tienen sede física y
    la app no tiene todavía cómo mostrar una actividad en línea (decisión
    pendiente de Juan);
  · «Por confirmar» (Motherwitch del vie 23) → acceso DESCONOCIDO;
  · la duración de las ACTIVIDADES no se publica: hueco hasta la siguiente en
    la misma sede ese día, tope 90 min, 60 si es la última (regla de BIFF);
  · qué cortos van en cada función de cortos: se toma la selección del catálogo
    que la función nombra, y solo cuando la nombra sin ambigüedad.
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
from lib import DESCONOCIDO, provenance  # noqa: E402

FUENTE = f'{REPO}/fuentes/fantasmagoria-2026/programacion.json'
URL = 'https://festivalfantasmagoriamedellin.com/noticias/ya-puedes-empezar-a-programarte-para-fantasmagoria-2026/'
CATALOGO = f'{REPO}/festivals/staging/fantasmagoria-2026-catalogo.json'
DESTINO = f'{REPO}/festivals/staging/fantasmagoria-2026-crudo.json'
# la SEGUNDA fuente oficial: la página de largometrajes (fantasmagoria-2026-largos.py)
LARGOS = f'{REPO}/festivals/staging/fantasmagoria-2026-largos.json'

DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) (\d{1,2}) de octubre$', re.I)
HEAD = re.compile(r'^(\d{1,2}):(\d{2})\s*(am|pm)\s*(?:\|\|)?\s*(.*)$', re.I)
FICHA = re.compile(r'^\((.*)\)\s*de\s+(.+?)\s*$')
ACCESO_RE = re.compile(r'entrada|acceso|confirmar|p[uú]blico dirigido|\$', re.I)

# LAS SEDES: el nombre que imprime la parrilla (escrito de varias formas) →
# (sede publicada, sala). La sala va aparte, como pide el contrato.
SEDES = {
    'COMFAMA – La Capilla': ('Comfama San Ignacio', 'La Capilla'),
    'COMFAMA – San Ignacio': ('Comfama San Ignacio', ''),
    'COMFAMA – Mediateca': ('Comfama San Ignacio', 'Mediateca'),
    'COMFAMA – Otraparte': ('Comfama Otraparte', ''),
    'Centro Colombo Americano': ('Centro Colombo Americano', ''),
    'Centro Colombo Americano – Sala 1': ('Centro Colombo Americano', 'Sala 1'),
    'Centro Colombo Americano – Sala 2': ('Centro Colombo Americano', 'Sala 2'),
    'Centro Colombo Americano – Sala X': ('Centro Colombo Americano', 'Sala X'),
    'Centro Colombo Americano – Sala x': ('Centro Colombo Americano', 'Sala X'),
    'Cineprox – Las Américas (Sala 3)': ('Cineprox Las Américas', 'Sala 3'),
    'Cineprox . Las Américas (Sala 3)': ('Cineprox Las Américas', 'Sala 3'),
    'Cineprox. Las Américas (Sala 3)': ('Cineprox Las Américas', 'Sala 3'),
    'Museo de Arte Moderno de Medellín': ('Museo de Arte Moderno de Medellín - MAMM', ''),
    'Museo de Arte de Moderno de Medellín': ('Museo de Arte Moderno de Medellín - MAMM', ''),
    'Planetario de Medellín – Auditorio': ('Planetario de Medellín', 'Auditorio'),
    'Cámara de Comercio – Auditorio': ('Cámara de Comercio de Medellín', 'Auditorio'),
    'Centro de Desarrollo Cultural de Moravia': ('Centro de Desarrollo Cultural de Moravia', ''),
    'Estación Metrocable del Metro – Andalucía': ('Estación Metrocable Andalucía', ''),
    'Parque Biblioteca Belén': ('Parque Biblioteca Belén', ''),
    'Parque Biblioteca Belén – Auditorio': ('Parque Biblioteca Belén', 'Auditorio'),
    'Parque de los Deseos': ('Parque de los Deseos', ''),
    'Universidad Luis Amigó – Auditorio Santa Rita': ('Universidad Católica Luis Amigó', 'Auditorio Santa Rita'),
    'Universidad Luis Amigó – Sala de tecnolgía': ('Universidad Católica Luis Amigó', 'Sala de tecnología'),
    'Universidad Nacional – Auditorio Gerardo Molina': ('Universidad Nacional', 'Auditorio Gerardo Molina'),
    'Universidad Nacional – Plaza de la Biblioteca': ('Universidad Nacional', 'Plaza de la Biblioteca'),
    'Universidad Nacional – Plazoleta de la Luz': ('Universidad Nacional', 'Plazoleta de la Luz'),
    'Universidad de Antioquia – Paraninfo UdeA': ('Paraninfo Universidad de Antioquia', ''),
    'La Pascasia': ('La Pascasia', ''),
    'Librería La Pascasia': ('La Pascasia', ''),
    'Librería Antimateria': ('Librería Antimateria', ''),
    'La Grieta': ('La Grieta', ''),
    'La Comarca': ('La Comarca', ''),
    'Draco Hobby': ('Draco Hobby', ''),
    'Silencio': ('Silencio', ''),
    'Nueva Villa de Aburrá': ('Nueva Villa de Aburrá', ''),
}
VIRTUAL = re.compile(r'twitch', re.I)

# EL ACCESO, con las palabras de la parrilla. «Entrada con Boleta» = «funciones
# con cobro especial en Colombo Americano, CineProx y MAMM» (nota de la noticia).
def acceso(txt):
    t = txt.lower()
    if 'confirmar' in t:
        return DESCONOCIDO
    if 'público dirigido' in t or 'publico dirigido' in t:
        return 'Ingreso únicamente con invitación'          # «Público dirigido de la Universidad»
    if 'libre con boleta' in t:
        return 'Entrada libre con boleta (en orden de llegada hasta completar aforo)'
    if 'libre' in t:
        return 'Entrada libre'
    if 'boleta' in t:
        return 'Con boleta'
    m = re.search(r'([\d.]+)\s*\$', txt)
    if m:
        return f'Con costo: {m.group(1)} $ (materiales incluidos)'
    return DESCONOCIDO

# LAS FUNCIONES DE CORTOS → la selección del catálogo que nombran (título
# normalizado del rótulo o de la línea). Solo las que lo dicen sin ambigüedad.
CORTOS = [
    (re.compile(r'cortometrajes? de animaci', re.I), 'Selección de Cortometrajes Animados'),
    (re.compile(r'selecci[oó]n oficial de cortometrajes colombianos', re.I), 'Selección de Cortometrajes Colombianos'),
    (re.compile(r'cortometrajes? latinoamericanos', re.I), 'Selección Latinoamericana de Cortometrajes'),
    (re.compile(r'^selección oficial de cortometrajes(\s*\+|\s*$)', re.I), 'Selección Oficial Cortometrajes'),
]
# LAS ACTIVIDADES CUYO NOMBRE NO ES LA LÍNEA SIGUIENTE (mirado bloque por
# bloque): el nombre es el rótulo y la línea es su descripción. (día, hora) →
# (título, event_kind o None si es una función de cortos sin lista, sección)
ACTIVIDAD = {
    ('2026-10-16', '18:00'): ('Torneos TCG: One Piece y Pokemón TCG', 'torneo', 'Actividades'),
    ('2026-10-16', '18:30'): ('Grabación en vivo del podcast Gente que hace cine «Colombia es Fantástica»', 'encuentro', 'Colombia es Fantástica'),
    ('2026-10-16', '22:00'): ('Fiesta Gótico Tropical', 'fiesta', 'Actividades'),
    ('2026-10-17', '15:00'): ('Muestra Fantasmagoritos: Cortometrajes infantiles', None, 'Muestra Fantasmagoritos'),
    ('2026-10-17', '16:00'): ('Iris de Cristal', None, 'Muestra especial'),
    ('2026-10-17', '19:00'): ('Expediente Fantasmagoría – Contacto', 'evento', 'Expediente Fantasmagoría'),
    ('2026-10-17', '22:00'): ('Noche de Librerías: Lectura de Cuentos de Terror', 'evento', 'Noche de Librerías'),
    ('2026-10-18', '19:00'): ('Selección Oficial de Cortometrajes Colombianos', None, 'Selección de Cortometrajes Colombianos'),
    ('2026-10-20', '14:00'): ('Conversatorio con Cristian Ponce', 'conversatorio', 'Retrospectiva Cristian Ponce'),
    ('2026-10-21', '14:00'): ('Fantascátedra – Muestra Cortometrajes universitarios de Medellín', None, 'Jornada Fantasmeet'),
    ('2026-10-21', '15:30'): ('Presentaciones de productoras/colectivos y Made in Medellín', 'encuentro', 'Jornada Fantasmeet'),
    ('2026-10-21', '18:00', 'Cámara de Comercio de Medellín'): ('De Cinema Zombie a Zinema Zombie', 'conversatorio', 'Jornada Fantasmeet'),
    ('2026-10-22', '18:00', 'Centro Colombo Americano'): ('Función Grindhouse: Selección Oficial de Cortometrajes', None, 'Selección Oficial Cortometrajes'),
    ('2026-10-22', '18:00', 'La Comarca'): ('Jornada Juegos de Mesa Fantastable', 'evento', 'Jornada Juegos de Mesa Fantastable'),
    ('2026-10-22', '18:00', 'Universidad Nacional'): ('Club de la Medianoche: Club de lectura', 'evento', 'Club de la Medianoche'),
    ('2026-10-23', '17:00'): ('Muestra Catalana: Cortometrajes C-Trencada', None, 'Muestra Catalana'),
    ('2026-10-23', '21:30'): ('Fiesta Fantasmagoría: Brujas, Espectros y Otros Fantasmas', 'fiesta', 'Actividades'),
    ('2026-10-24', '18:30'): ('Selección Oficial de Cortometrajes', None, 'Selección Oficial Cortometrajes'),
    ('2026-10-24', '19:00'): ('Cortometrajes colombianos que miran al cielo', None, 'Colombia es Fantástica'),
    ('2026-10-25', '17:00'): ('Evento de Clausura: Premiación y Presentación musical', 'clausura', 'Evento de Clausura'),
}
# solo palabras que la app ya conoce ([event-kind-conocido]); lectura, juegos y
# podcast no tienen entrada todavía: van como «evento» (copy de Juan)
KIND = [('charla', 'charla'), ('conversatorio', 'conversatorio'), ('taller', 'taller'), ('torneo', 'torneo'),
        ('fiesta', 'fiesta')]


# LA SECCIÓN que se publica: el PRIMER rótulo de la función, tal cual, sin el
# «+ …» que la combina con otra muestra ni los adornos («(Tema Central)»,
# «– charla», el punto final). La parrilla escribe la misma de varias formas;
# se unifica la caja con la forma más frecuente.
CAJA_SECCION = {'muestra asiatica el oriente es rojo': 'Muestra Asiática El Oriente Es Rojo',
                'colombia es fantastica': 'Colombia es Fantástica'}


def seccion_publicada(rot):
    s = re.split(r'\s*\+\s*', rot)[0]
    s = re.sub(r'\s*\((tema central)\)', '', s, flags=re.I)
    s = re.sub(r'\s*[–-]\s*(charla|conversatorio)?\s*$', '', s, flags=re.I)
    s = s.rstrip(' .:–-').strip()
    return CAJA_SECCION.get(plano(s), s)


# EL AÑO Y LA DURACIÓN salen de la ficha de cada largo en la página de
# largometrajes, no de la parrilla, que es un horario. Difieren en dos (29 sep):
# «Vida» (parrilla 2018 y «xxx´»; ficha 2016 y 64’, y Retina Latina también da
# 2016) y «Hammer» (parrilla 2025; ficha y página de la edición, 2024).


def recta(s):
    return (s or '').replace('’', "'").replace('‘', "'").replace('«', '"').replace('»', '"').replace('“', '"').replace('”', '"')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def lineas():
    d = json.load(io.open(FUENTE, encoding='utf-8'))
    t = html.unescape(re.sub(r'<[^>]+>', '\n', d['content']['rendered'])).replace('\xa0', ' ')
    return [x.strip() for x in t.split('\n') if x.strip() and not x.strip().startswith('[')], d['modified']


def hora(h, m, ap):
    h = int(h) % 12 + (12 if ap.lower() == 'pm' else 0)
    return f'{h:02d}:{m}'


def _es_pais(x):
    from lib import banderas
    return bool(banderas(x.strip()))


def ficha(txt):
    """«Terror / Colombia, 2026, 96´» · «Canadá, 2026, 90’» · «Documental, España, 70´»."""
    partes = [p.strip() for p in re.split(r'\s*/\s*', txt)]
    resto = partes[-1]
    genero = partes[0] if len(partes) > 1 else ''
    m = re.search(r'(\d+)\s*[´’\']', resto)
    dur = int(m.group(1)) if m else None
    a = re.search(r'\b(19|20)\d{2}\b', resto)
    anio = int(a.group()) if a else None
    pais = re.sub(r',?\s*\b(19|20)\d{2}\b.*$', '', resto)
    pais = re.sub(r',?\s*\d+\s*[´’\'].*$', '', pais).strip(' ,')
    # EL PAÍS es lo que tiene bandera; lo demás es género. Sin «/» la parrilla
    # mezcla los dos («Animación, musical, Colombia y España») y a veces pone
    # otra cosa («Julián Duque, Colombia»: el director)
    bits = [b.strip() for b in re.split(r',|\s+y\s+', pais) if b.strip()]
    paises = [b for b in bits if _es_pais(b)]
    otros = [b for b in bits if not _es_pais(b)]
    if len(partes) == 1 and otros and not genero:
        genero = ', '.join(o for o in otros if o.lower() not in ('julián duque',))
    if genero and _es_pais(genero):           # «(Inglaterra / Inglaterra…)»
        genero = ''
    return genero, ', '.join(paises), anio, dur


def main():
    L, modificada = lineas()
    cat = json.load(io.open(CATALOGO, encoding='utf-8'))['obras']
    idx = {plano(o['titulo']): o for o in cat}
    idx.update({plano(o.get('titulo_en') or ''): o for o in cat if o.get('titulo_en')})
    largos = json.load(io.open(LARGOS, encoding='utf-8'))['peliculas']
    lidx = {plano(k): v for k, v in largos.items()}
    por_seccion = {}
    for o in cat:
        por_seccion.setdefault(o['seccion'], []).append(o)

    bloques, dia = [], None
    for x in L:
        m = DIA.match(x)
        if m:
            dia = f'2026-10-{int(m.group(2)):02d}'
            continue
        m = HEAD.match(x)
        if m and dia:
            bloques.append({'dia': dia, 'hora': hora(*m.groups()[:3]), 'rotulo': m.group(4).strip(), 'L': []})
            continue
        if bloques and dia:
            if x.startswith('Más información sobre la edición'):
                dia = None
                continue
            bloques[-1]['L'].append(x)

    fallos, funciones, virtuales = [], [], []
    for b in bloques:
        cuerpo = b['L']
        # la línea de SEDE: la última con «/»; si no hay (la inaugural), la última
        iv = max((i for i, y in enumerate(cuerpo) if '/' in y and ACCESO_RE.search(y)), default=None)
        if iv is None:
            iv = len(cuerpo) - 1
            sede_txt, sellos = cuerpo[iv], [y for y in cuerpo if ACCESO_RE.search(y)]
        else:
            partes = [p.strip() for p in cuerpo[iv].split('/')]
            sede_txt, sellos = partes[0], partes[1:]
        if VIRTUAL.search(sede_txt):
            virtuales.append(f'{b["dia"]} {b["hora"]} {b["rotulo"]}')
            continue
        if sede_txt not in SEDES:
            fallos.append(f'{b["dia"]} {b["hora"]}: sede sin entrada en la tabla: {sede_txt!r}')
            continue
        sede, sala = SEDES[sede_txt]
        texto = cuerpo[:iv]
        rot = b['rotulo'].rstrip(':').strip()
        ifi = next((i for i, y in enumerate(texto) if FICHA.match(y)), None)
        r = {'dia': b['dia'], 'hora': b['hora'], 'sede': sede,
             'acceso': acceso(' / '.join(sellos)) if sellos else DESCONOCIDO,
             '_src': {'url': URL, 'date': modificada[:10]}}
        if sala:
            r['sala'] = sala
        sello = ' '.join(sellos).lower()
        if 'presencia' in sello or 'q&a' in ' '.join(cuerpo).lower():
            r['has_qa'], r['qa_type'] = True, 'team'
        if ifi is not None:
            m = FICHA.match(texto[ifi])
            genero, pais, anio, dur = ficha(m.group(1))
            director = re.sub(r'\s*\+.*$', '', m.group(2)).rstrip('.').strip()
            titulo = texto[ifi - 1] if ifi > 0 else rot.split(':')[-1].strip()
            if ifi == 0 and ':' in b['rotulo']:
                rot = b['rotulo'].split(':')[0].strip()
            titulo = re.sub(r'^Película:\s*', '', titulo).strip()
            pt = plano(titulo)
            c = idx.get(pt) or next((o for k, o in idx.items() if k and (
                k.startswith(pt + ' ') or pt.endswith(k) or k.endswith(pt))), None)
            r.update({'titulo': c['titulo'] if c else titulo, 'director': director,
                      'pais': re.sub(r'\s+e\s+', ', ', (c or {}).get('pais') or pais),
                      'anio': anio, 'duracion_min': dur, 'genero': genero.split(',')[0].strip() or None,
                      'seccion': c['seccion'] if c else rot})
            extra = [y for y in texto[ifi + 1:]] + ([m.group(2).split('+', 1)[1].strip()] if '+' in m.group(2) else [])
            if extra:
                r['invitados'] = ' '.join(extra).strip()
        elif (b['dia'], b['hora'], sede) in ACTIVIDAD or (b['dia'], b['hora']) in ACTIVIDAD:
            t_, k_, sec_ = ACTIVIDAD.get((b['dia'], b['hora'], sede)) or ACTIVIDAD[(b['dia'], b['hora'])]
            linea = ' '.join(texto).strip(' –-')
            r.update({'titulo': t_, 'seccion': sec_})
            if k_:
                r.update({'tipo': 'evento', 'event_kind': k_})
            desc = re.sub(r'^\+\s*', '', linea).strip()
            if desc and plano(desc) not in plano(t_):
                r['sinopsis'] = desc if desc.endswith('.') else desc + '.'
            prog = sec_ if sec_ in por_seccion else None     # la sección del catálogo que la función nombra
            if not k_ and prog:
                r['obras'] = [{'titulo': o['titulo'], 'director': o.get('director'), 'pais': o.get('pais'),
                               'anio': o.get('anio'), 'duracion_min': o.get('duracion_min')}
                              for o in por_seccion[prog]]
                r['duracion_min'] = sum(o.get('duracion_min') or 0 for o in por_seccion[prog])
        else:
            linea = ' '.join(texto).strip(' –-')
            titulo = linea or rot
            prog = next((sec for rx, sec in CORTOS if rx.search(rot) or rx.search(linea)), None)
            if prog and prog in por_seccion:
                r.update({'titulo': (titulo if linea else rot).rstrip('.').strip(), 'seccion': prog,
                          'obras': [{'titulo': o['titulo'], 'director': o.get('director'), 'pais': o.get('pais'),
                                     'anio': o.get('anio'), 'duracion_min': o.get('duracion_min')}
                                    for o in por_seccion[prog]]})
                r['duracion_min'] = sum(o.get('duracion_min') or 0 for o in por_seccion[prog])
            else:
                kind = next((k for w, k in KIND if w in (rot + ' ' + linea).lower()), 'evento')
                es_cortos = 'cortometraje' in (rot + ' ' + linea).lower()
                r.update({'titulo': titulo, 'seccion': rot})
                if not es_cortos:
                    r.update({'tipo': 'evento', 'event_kind': kind})
        if 'inaugural' in b['rotulo'].lower():
            r['premiere'] = 'Inauguración'
        if 'clausura' in b['rotulo'].lower() and r.get('tipo') != 'evento':
            r['premiere'] = 'Clausura'
        # LA SINOPSIS y el ESTRENO de la página de largometrajes (texto del festival)
        lg = lidx.get(plano(r['titulo'])) or next((v for k, v in lidx.items() if k.startswith(plano(r['titulo']) + ' ')), None)
        if lg and r.get('director'):
            for k in ('anio', 'duracion_min'):
                if lg.get(k):
                    r[k] = lg[k]
            if lg.get('sinopsis') and not r.get('sinopsis'):
                r['sinopsis'] = lg['sinopsis']
            if lg.get('estreno') and not r.get('premiere'):
                r['premiere'] = lg['estreno'][:1].upper() + lg['estreno'][1:].lower()
        if r.get('seccion'):
            r['seccion'] = seccion_publicada(r['seccion'])
        # comillas rectas en los títulos ([title-normalization]) y el punto final fuera
        r['titulo'] = recta(r['titulo']).rstrip('.').strip()
        for o in r.get('obras') or []:
            o['titulo'] = recta(o['titulo'])
            if o.get('pais'):
                o['pais'] = re.sub(r'\s+e\s+', ', ', o['pais'])
        funciones.append({k: v for k, v in r.items() if v not in (None, '')})

    # DURACIÓN DEDUCIDA de lo que no la publica (actividades y cortos sin lista)
    for f in funciones:
        if f.get('duracion_min') or f.get('director'):      # una película sin duración la completa TMDB
            continue
        ini = int(f['hora'][:2]) * 60 + int(f['hora'][3:])
        sig = sorted(int(g['hora'][:2]) * 60 + int(g['hora'][3:]) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and g.get('sala') == f.get('sala')
                     and g['hora'] > f['hora'])
        f['duracion_min'] = min(sig[0] - ini, 90) if sig else 60

    # COBERTURA INVERSA con un patrón propio: toda hora impresa es una función o virtual
    impresas = [x for x in L if re.match(r'^\d{1,2}:\d{2}\s*[ap]m', x, re.I)]
    if len(impresas) != len(funciones) + len(virtuales) + len(fallos):
        fallos.append(f'{len(impresas)} horas impresas y {len(funciones)} funciones + {len(virtuales)} virtuales')
    if fallos:
        sys.exit('✗ la parrilla no cuadra:\n  · ' + '\n  · '.join(fallos))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('festivalfantasmagoriamedellin.com, noticia de programación (wp-json post 6481)',
                                  url=URL, metodo='bloques por hora, ficha entre paréntesis, sede y acceso tras «/»'),
        '_virtuales_fuera': virtuales, 'funciones': funciones}, ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("tipo") == "evento")} actividades, '
          f'{sum(1 for f in funciones if f.get("obras"))} programas de cortos) · {len(virtuales)} virtuales fuera '
          f'· {len({f["sede"] for f in funciones})} sedes → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
