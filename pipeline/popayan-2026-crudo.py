#!/usr/bin/env python3
"""popayan-2026-crudo.py — la parrilla del 17 Festival de Cine Corto de Popayán → crudo.

LA FUENTE es la página de programación de la web del festival,
festicinepopayan.com/fest2026/programacion2026/ (id 13120), leída por su
`wp-json` (mod_security rechaza la consulta por slug: se pide por id). Se
publicó el 28 sep y se retocó el 29 sep 02:21 GMT; la portada todavía no la
enlaza. La trae, por día, bloques de la forma

    Teatro Bolívar / 7:30 pm
    Selección Oficial Documental (primer bloque)
    Películas
    <título>
    dirigido por … y producido por …. Documental. 8 minutos. <lugar de rodaje>.

Cada bloque es UNA función con varias obras (un programa). La ficha de cada
obra —año, sinopsis, ficha de TMDB— sale del catálogo del pre-onboarding
(popayan-2026-catalogo.py, 77 obras), que se cruza aquí por título Y
dirección: un bloque que nombra una obra que el catálogo no tiene, o con otra
dirección, detiene el crudo.

LO QUE LA PÁGINA TRAE A MEDIO ARMAR (radar #573, 29 sep), y cómo se trata:
  · el DOMINGO 11 no aparece, aunque el festival dura hasta el 11: no se
    inventa; lo del catálogo que no tiene función se lista al final;
  · la «Muestra de Cortos Internacionales» (vie 3 p. m.) tiene el encabezado
    «Películas» sin obras: se publica la función, sin obras;
  · la primera obra del bloque Experimental tiene como título el texto de
    relleno de la plantilla («Lorem ipsum…») y debajo «(El Experimento)»: el
    catálogo la registra con ese título y esa dirección (Paola Michaels);
  · el par «4:30 pm Conversatorio / 5:00 pm Selección Oficial Afro» del
    miércoles sale DOS veces seguidas: se toma una;
  · la duración de los CONVERSATORIOS, la APERTURA y la MUESTRA INTERNACIONAL
    no está publicada, y el plan la necesita ([activity-duration]): se deduce
    del hueco hasta lo siguiente en la MISMA sede ese día, con tope de 90 min,
    y 60 si es lo último del día (la regla de las charlas de BIFF);
  · la MUESTRA INTERNACIONAL, sin obras, lleva el AFICHE OFICIAL del festival
    (p/DdCljrXoEzp): no hay afiche de sus obras, y el del festival manda sobre
    cualquiera nuestro (jerarquía del póster).
  · el ACCESO: la página no lo dice → ACCESO (ver abajo).
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

FID = 'popayan-2026'
# desde el 6 oct la página es OTRA (id 12543, slug programacion-2026): la 13120 da 404
URL = 'https://festicinepopayan.com/fest2026/programacion-2026/'
FUENTE = f'{REPO}/fuentes/{FID}/programacion2026.json'
CATALOGO = f'{REPO}/festivals/staging/popayan-2026-catalogo.json'
DESTINO = f'{REPO}/festivals/staging/popayan-2026-crudo.json'

# (\s+: el sábado del 30 sep sale «Sábado 10  de octubre», con doble espacio)
DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+(\d{1,2})\s+de\s+octubre$')
# «Teatro Bolívar / 7:30 pm» y, desde el 30 sep, también un RANGO: «/ 9 am – 1
# pm» (los talleres) o «/ 9 am – 1 pm y 2 a 5 pm» (el de MAMPO): el fin es la
# última hora del renglón
SLOT = re.compile(r'^(.+?) / (\d{1,2})(?::(\d{2}))?\s*(am|pm)((?:\s*[–-]\s*|\s+y\s+|\s+a\s+|\d|:|\s*[ap]m)*)$', re.I)
HORA_EN = re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', re.I)
# LA VERSIÓN DEL 30 SEP (modificada 00:12 GMT) agrega el viernes y el sábado en
# el Centro Comercial Terra Plaza con OTRA forma: la sede sola en un renglón y
# debajo cada actividad con su hora delante («3:00 pm Apertura muestra …»)
HORA_DELANTE = re.compile(r'^(\d{1,2}):(\d{2})\s*(am|pm)\s+(.+)$', re.I)
CREDITO = re.compile(r'^(?:.*?\s)?dirigid[oa]s?\s*(?:y producid[oa]s?\s*)?por\s', re.I)
# «dirigido por A y producido por B» / «dirigido y producido por A» — la
# DIRECCIÓN es lo que va antes de « y producido» o, en el segundo caso, el
# mismo nombre
DIR_Y_PROD = re.compile(r'dirigid[oa]s?\s*y\s*producid[oa]s?\s*por\s+(.+?)\.\s', re.I)
DIR_SOLO = re.compile(r'dirigid[oa]s?\s*por\s+(.+?)(?:\s+y\s+[Pp]roducid[oa]s?\s+por\s|\.\s)', re.I)
MINUTOS = re.compile(r'(\d+)\s*minutos')
RELLENO = 'Lorem ipsum'

# LAS SEDES: el nombre que imprime la página, tal cual; la sala aparte
SEDES = {
    'Teatro Bolívar': ('Teatro Bolívar', ''),
    'Auditorio Maya Facultad de Artes Unicauca': ('Facultad de Artes Unicauca', 'Auditorio Maya'),
    # las cuatro que trae la versión del 30 sep
    'Museo de Arte Moderno de Popayán MAMPO': ('Museo de Arte Moderno de Popayán MAMPO', ''),
    'Casa Taller Sirirí': ('Casa Taller Sirirí', ''),
    'Mikuna Casa Cultural': ('Mikuna Casa Cultural', ''),
    # 8 oct: la misma sede con su barrio pegado (jueves 8, «Cine Corto al barrio»)
    'Mikuna Casa Cultural. Barrio el Tunel Bajo': ('Mikuna Casa Cultural', ''),
    'Centro Comercial Terra Plaza – Pantalla gigante': ('Centro Comercial Terra Plaza', 'Pantalla gigante'),
}
# LO QUE ES SOLO PARA INSCRITOS: los talleres y el CineCorto Lab («solo
# inscritos y aceptados»). La convocatoria ya cerró y el público no puede ir:
# no se publican, como los talleres de Mamut (decisión de Juan). Quedan
# anotados en el crudo, en `_fuera`, con su día y hora.
SOLO_INSCRITOS = re.compile(r'\(\s*s[oó]lo inscritos y aceptados\s*\)', re.I)

# EL ACCESO. La página no lo dice. El afiche oficial del festival sí:
# «teatro Bolívar · entrada libre» (IG @cinecortofest p/DdCljrXoEzp, mirado el
# 29 sep). Se declara a nivel festival y se repite en cada función.
ACCESO = 'Entrada libre'

# LA SECCIÓN de cada bloque: el nombre del bloque sin «(primer bloque)» /
# «segundo bloque». Es el nombre que imprime la parrilla, en caja de título, y
# no el del catálogo («SELECCIÓN OFICIAL CORTOMETRAJE AFRO», mayúscula sostenida).
BLOQUE = re.compile(r'\s*\(?(primer|segundo)\s+bloque\)?\s*$', re.I)
# EL CATÁLOGO nombra «ANIMADO» lo que la parrilla llama «Animación»: misma sección
SECCION_CATALOGO = {
    'Selección Oficial Documental': 'SELECCIÓN OFICIAL CORTOMETRAJE DOCUMENTAL',
    'Selección Oficial Cauca': 'SELECCIÓN OFICIAL CORTOMETRAJE CAUCA',
    'Selección Oficial Experimental': 'SELECCIÓN OFICIAL CORTOMETRAJE EXPERIMENTAL',
    'Selección Oficial Indígena': 'SELECCIÓN OFICIAL CORTOMETRAJE INDÍGENA',
    'Selección Oficial Afro': 'SELECCIÓN OFICIAL CORTOMETRAJE AFRO',
    'Selección Oficial Animación': 'SELECCIÓN OFICIAL CORTOMETRAJE ANIMADO',
    'Selección Oficial Comunitario': 'SELECCIÓN OFICIAL CORTOMETRAJE COMUNITARIO',
    'Selección Oficial Ficción': 'SELECCIÓN OFICIAL CORTOMETRAJE FICCIÓN',
}
# TÍTULOS QUE LA PARRILLA Y LA SELECCIÓN OFICIAL ESCRIBEN DISTINTO (misma
# dirección, misma sección). parrilla → (título en el catálogo, título que se publica)
#   · «Akababuru»: la parrilla lo abrevia; la Selección da el título entero.
#   · «Ley de Origen y Espiritualidad»: la Selección del 28 sep la llamaba
#     «Vivenciando lo Hilos de Vida…»; el festival la corrigió el 29 sep (03:28
#     UTC) al título de la parrilla y de cinecorto.co. Ya no necesita alias.
ALIAS = {
    'Akababuru': ('Akababuru: Expresión de asombro', 'Akababuru: Expresión de asombro'),
}
# OBRAS QUE LA PARRILLA TRAE Y LA SELECCIÓN OFICIAL NO: se publican con lo que
# dice la parrilla (título, dirección, duración) y el enriquecido les busca ficha.
#   · «Amor en los tiempos de como sea que se llame el presente»: 10.ª obra del
#     bloque de Animación; la Selección lista 9.
SOLO_PARRILLA = {'Amor en los tiempos de como sea que se llame el presente'}
# EL PAÍS. La parrilla da el LUGAR DE RODAJE («Lisboa, Portugal»), no el país
# de producción, y el catálogo tampoco lo trae: salían todas con el globo. El
# reglamento sí lo dice para toda la Selección Oficial: «cortometrajes
# realizados en Colombia o por colombianos en el exterior». Va como país de
# RESPALDO: el ensamblador lo usa solo donde TMDB no da uno, que así las
# coproducciones («France, Colombia», «Colombia, Portugal») se respetan. Las
# 29 fichas de TMDB que ya lo tienen incluyen todas a Colombia (29 sep).
PAIS_SELECCION = 'Colombia'
# LA SINOPSIS QUE LA FUENTE TRAE ROTA, con su prueba. La ficha de «Legado» en
# cinecorto.co (post 15569) empieza «na serie documental que viaja…»: se comió
# la primera letra. Se repone (Juan, 1 oct 2026); el resto, literal.
SINOPSIS_ERRATA = {'Legado': ('na serie documental', 'Una serie documental')}
ACTIVIDADES = {'Apertura del Festival': 'apertura', 'Conversatorio': 'conversatorio',
               # Terra Plaza (30 sep): la apertura de la muestra con la banda, y
               # la grabación del videopodcast
               'Apertura muestra Banda de la Academia Militar General Tomás Cipriano de Mosquera': 'apertura',
               'Vodcast en Vivo': 'evento',
               # 6 oct: la premiación, viernes 9 en el Teatro Bolívar
               'Ceremonia de premiación': 'acto'}
# EL BLOQUE QUE LA PÁGINA DEJA SIN NOMBRE (6 oct): «Casa Taller Sirirí / 6:30
# pm» y debajo, directo, las obras. En la versión del 30 sep esa misma sede a
# esa misma hora era «CineCorto en el Barrio» (jueves 8); la del 6 oct lo pasa
# al sábado 10 y se come el título. Se le pone el del 30 sep, anotado.
TITULO_SIN_NOMBRE = {('2026-10-10', '18:30', 'Casa Taller Sirirí'): 'CineCorto en el Barrio'}
# LOS BLOQUES QUE MEZCLAN SECCIONES (30 sep): su sección es el nombre del
# programa, sin el verbo
SECCION_DE_BLOQUE = {'Proyección Cine Corto Familiar': 'Cine Corto Familiar'}
SECCION_ACTIVIDADES = 'Actividades'


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def lineas():
    d = json.load(io.open(FUENTE, encoding='utf-8'))
    t = html.unescape(re.sub(r'<[^>]+>', '\n', d['content']['rendered']))
    # el ESPACIO DURO: «Teatro Bolívar /\xa03:30 pm» (jueves) no casaba con « / »
    # y el bloque Comunitario entero se perdía sin error
    t = t.replace('\xa0', ' ')
    L = [x.strip() for x in t.split('\n') if x.strip()]
    return normalizar(L), d['modified']


def normalizar(L):
    """Las formas que trajo la versión del 30 sep, llevadas a la de siempre
    («<sede> / <hora>» + título). Cada una, con el renglón que la trajo:
      · «6: 30 pm» (espacio tras los dos puntos, jueves en el barrio);
      · «Teatro Bolívar» + «/ 9 am – 1 pm» (la sede y la hora en dos renglones);
      · «Peliculas» sin tilde (sábado);
      · «(Sólo inscritos y aceptados)» solo en su renglón: va con su título;
      · «Color piel dirigido» + «por Fidel…»: el título y el crédito, partidos
        por la mitad del crédito;
      · la sede sola y debajo «3:00 pm <actividad>» (Terra Plaza)."""
    L = [re.sub(r'(\d):\s+(\d{2})\s*(am|pm)', r'\1:\2 \3', x, flags=re.I) for x in L]
    L = ['Películas' if x == 'Peliculas' else x for x in L]
    out, sede = [], None
    i = 0
    while i < len(L):
        x = L[i]
        nxt = L[i + 1] if i + 1 < len(L) else ''
        # 6 oct: la sede y DEBAJO la hora sola, sin la barra («Teatro Bolívar» + «3 pm»)
        if x in SEDES and re.fullmatch(r'\d{1,2}(:\d{2})?\s*(am|pm)', nxt, re.I):
            out.append(f'{x} / {nxt}')
            sede = None
            i += 2
            continue
        # 8 oct: la sede, la barra sola y la hora, en TRES renglones
        # («Mikuna Casa Cultural. Barrio el Tunel Bajo» + «/» + «6:30 pm»)
        nxt2 = L[i + 2] if i + 2 < len(L) else ''
        if x in SEDES and nxt == '/' and re.fullmatch(r'\d{1,2}(:\d{2})?\s*(am|pm)', nxt2, re.I):
            out.append(f'{x} / {nxt2}')
            sede = None
            i += 3
            continue
        if x in SEDES and nxt.startswith('/ '):
            out.append(f'{x} {nxt}')
            sede = None
            i += 2
            continue
        # LA VERSIÓN DEL 6 OCT parte el nombre del bloque: «Selección Oficial
        # Cauca» + «(primer bloque)»; y la primera obra de Experimental viene
        # entre paréntesis: «(El Experimento)» + su crédito
        if re.fullmatch(r'\(?(primer|segundo)\s+bloque\)?', x, re.I) and out:
            out[-1] = f'{out[-1]} {x}'
            i += 1
            continue
        m_par = re.fullmatch(r'\((.+)\)', x)
        if m_par and re.match(r'^dirigid', nxt, re.I):
            out.append(m_par.group(1))
            i += 1
            continue
        if SOLO_INSCRITOS.fullmatch(x) and out:
            out[-1] = f'{out[-1]} {x}'
            i += 1
            continue
        if re.search(r'\sdirigid[oa]s?$', x) and nxt.lower().startswith('por '):
            tit, _ = re.split(r'\s(?=dirigid[oa]s?$)', x)
            out += [tit, f'{x[len(tit):].strip()} {nxt}']
            i += 2
            continue
        if x in SEDES:
            sede = x
            i += 1
            continue
        m = HORA_DELANTE.match(x)
        if sede and m:
            out += [f'{sede} / {m.group(1)}:{m.group(2)} {m.group(3)}', m.group(4)]
            i += 1
            continue
        if DIA.match(x) or SLOT.match(x):
            sede = None
        out.append(x)
        i += 1
    return out


def hora(h, m, ap):
    h = int(h) % 12 + (12 if ap.lower() == 'pm' else 0)
    return f'{h:02d}:{m or "00"}'


def _sinopsis(c):
    s = c.get('sinopsis')
    e = SINOPSIS_ERRATA.get(c.get('titulo'))
    if s and e and s.startswith(e[0]):
        s = e[1] + s[len(e[0]):]
    return s


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def director(credito):
    m = DIR_Y_PROD.search(credito + ' ')
    if m:
        return m.group(1).strip()
    m = DIR_SOLO.search(credito + ' ')
    return m.group(1).strip() if m else ''


def leer():
    """La página → bloques [{dia, hora, sede_pdf, titulo, obras:[{titulo, credito}]}]."""
    L, modificada = lineas()
    bloques, dia, i = [], None, 0
    while i < len(L):
        x = L[i]
        m = DIA.match(x)
        if m:
            dia = f'2026-10-{int(m.group(2)):02d}'
            i += 1
            continue
        m = SLOT.match(x)
        if m:
            b = {'dia': dia, 'hora': hora(m.group(2), m.group(3), m.group(4)), 'sede_pdf': m.group(1).strip(),
                 'titulo': L[i + 1].rstrip('.').strip(), 'obras': []}
            fin = HORA_EN.findall(m.group(5) or '')
            if fin:
                b['hora_fin'] = hora(*fin[-1])
            i += 2
            sin_nombre = TITULO_SIN_NOMBRE.get((b['dia'], b['hora'], b['sede_pdf']))
            if sin_nombre:
                b['titulo'], b['_titulo_declarado'] = sin_nombre, True
                i -= 1
            # la descripción de una actividad («Grabación de Video Podcast con…»)
            if i < len(L) and b['titulo'] in ACTIVIDADES and not SLOT.match(L[i]) and not DIA.match(L[i]) \
                    and L[i] != 'Películas' and not L[i].startswith('Selección Oficial'):
                b['descripcion'] = L[i]
                i += 1
            # «Películas» encabezaba las obras hasta el 30 sep; el 6 oct ya no
            # está: una obra es un renglón seguido de su crédito
            if i < len(L) and L[i] == 'Películas':
                i += 1
            if True:
                while i < len(L) and not SLOT.match(L[i]) and not DIA.match(L[i]):
                    tit = L[i]
                    i += 1
                    if tit.startswith(RELLENO):          # el relleno de la plantilla
                        continue
                    # «Conversatorio con realizadores» cierra el bloque (6 oct)
                    if tit == 'Conversatorio con realizadores':
                        b['qa'] = True
                        continue
                    nx = L[i] if i < len(L) else ''
                    # UN BLOQUE SIN HORA PROPIA (6 oct): «Apertura del Festival» y
                    # debajo «Selección Oficial Documental (primer bloque)» con sus
                    # obras, todo bajo el mismo «7:00 pm» (el 30 sep era 7:30). Es
                    # otro bloque en la misma franja.
                    if tit.startswith('Selección Oficial') and not CREDITO.match(nx):
                        bloques.append(b)
                        b = {'dia': b['dia'], 'hora': b['hora'], 'sede_pdf': b['sede_pdf'],
                             'titulo': tit, 'obras': [], '_sin_hora_propia': True}
                        continue
                    if not CREDITO.match(nx) and not re.search(r'\sdirigid', nx):
                        # un renglón sin crédito detrás no es una obra: es la
                        # descripción de una actividad («Con el Apoyo de Origen Lab»)
                        if not b['obras']:
                            b['descripcion'] = f"{b.get('descripcion', '')} {tit}".strip()
                        continue
                    # EL CRÉDITO puede venir partido: el título se come el comienzo
                    # («… que se llame el» / «presente dirigido por…») o el crédito
                    # sigue en otro renglón («… Álvaro Ruiz Velasco» / «.» / «7 minutos…»)
                    if CREDITO.match(tit) is None and i < len(L) and CREDITO.match(L[i]) and \
                            not re.match(r'^dirigid', L[i], re.I):
                        pre, cred = re.split(r'\s(?=dirigid)', L[i], maxsplit=1)
                        tit, cr = f'{tit} {pre}', cred
                        i += 1
                    else:
                        cr = L[i] if i < len(L) else ''
                        i += 1
                    while i < len(L) and not MINUTOS.search(cr) and not SLOT.match(L[i]) and not DIA.match(L[i]):
                        cr = f'{cr} {L[i]}'
                        i += 1
                    b['obras'].append({'titulo': tit.strip(), 'credito': re.sub(r'\s+\.\s*', '. ', cr).strip()})
            bloques.append(b)
            continue
        i += 1
    return bloques, modificada


def main():
    bloques, modificada = leer()
    cat = json.load(io.open(CATALOGO, encoding='utf-8'))['obras']
    idx = {plano(o['titulo']): o for o in cat}
    fallos, funciones, vistos, usadas, fuera = [], [], set(), set(), []
    # el par del miércoles sale dos veces: la PRIMERA copia de Afro no trae
    # obras y la segunda sí → de cada repetido se toma la copia con más obras
    mejor = {}
    for b in bloques:
        k = (b['dia'], b['hora'], b['sede_pdf'], b['titulo'])
        if k not in mejor or len(b['obras']) > len(mejor[k]['obras']):
            mejor[k] = b
    for b in bloques:
        k = (b['dia'], b['hora'], b['sede_pdf'], b['titulo'])
        if k in vistos or mejor[k] is not b:
            continue
        vistos.add(k)
        if b['sede_pdf'] not in SEDES:
            fallos.append(f'sede sin entrada: {b["sede_pdf"]!r}')
            continue
        sede, sala = SEDES[b['sede_pdf']]
        if SOLO_INSCRITOS.search(b['titulo']):
            fuera.append({'titulo': b['titulo'], 'dia': b['dia'], 'hora': b['hora'], 'sede': sede,
                          'porque': 'solo inscritos y aceptados: no se publica'})
            continue
        r = {'titulo': b['titulo'], 'dia': b['dia'], 'hora': b['hora'], 'sede': sede, 'acceso': ACCESO,
             '_src': {'url': URL, 'date': modificada[:10]}}
        if sala:
            r['sala'] = sala
        if b.get('hora_fin'):
            r['duracion_min'] = mins(b['hora_fin']) - mins(b['hora'])
        if b.get('qa'):
            r['has_qa'], r['qa_type'] = True, 'team'
        # «Conversatorio Autorepresentación y cosmovisiones…» (6 oct): un
        # conversatorio con nombre propio
        kind = ACTIVIDADES.get(b['titulo']) or ('conversatorio' if b['titulo'].startswith('Conversatorio ') else None)
        if kind:
            r.update({'tipo': 'evento', 'event_kind': kind, 'seccion': SECCION_ACTIVIDADES})
            if b.get('descripcion'):
                r['sinopsis'] = b['descripcion']
            funciones.append(r)
            continue
        seccion = SECCION_DE_BLOQUE.get(b['titulo']) or BLOQUE.sub('', b['titulo']).strip()
        r['seccion'] = seccion
        obras = []
        for o in b['obras']:
            cat_t, pub_t = ALIAS.get(o['titulo'], (o['titulo'], None))
            c = idx.get(plano(cat_t))
            d = director(o['credito'])
            m = MINUTOS.search(o['credito'])
            if not c and o['titulo'] in SOLO_PARRILLA:
                obras.append({'titulo': o['titulo'], 'director': d, 'pais_respaldo': PAIS_SELECCION,
                              'duracion_min': int(m.group(1)) if m else None, '_solo_parrilla': True})
                continue
            if not c:
                fallos.append(f'«{o["titulo"]}» ({b["titulo"]}): no está en el catálogo')
                continue
            if not (set(plano(d).split()) & set(plano(c['director']).split())):
                fallos.append(f'«{o["titulo"]}»: la parrilla dice {d!r}, el catálogo {c["director"]!r}')
            if SECCION_CATALOGO.get(seccion) and c.get('seccion_fuente') != SECCION_CATALOGO[seccion]:
                fallos.append(f'«{o["titulo"]}»: en la parrilla va en {seccion!r}, el catálogo la tiene en '
                              f'{c.get("seccion_fuente")!r}')
            dur = int(m.group(1)) if m else None
            # LA DURACIÓN, comparada entre fuentes (regla de Juan): la parrilla
            # contra la ficha de cinecorto.co. Manda la parrilla —es la del
            # festival para ESTA función— y la diferencia queda a la vista.
            if dur and c.get('duracion_min') and abs(dur - c['duracion_min']) > 1:
                print(f'  ⚠ duración de «{c["titulo"]}»: parrilla {dur} · cinecorto.co {c["duracion_min"]}')
            usadas.add(plano(c['titulo']))
            obras.append({'titulo': pub_t or c['titulo'], 'director': c['director'], 'anio': c.get('anio'),
                          'pais_respaldo': PAIS_SELECCION,
                          'duracion_min': dur or c.get('duracion_min'), 'sinopsis': _sinopsis(c)})
        if obras:
            r['obras'] = [{k2: v for k2, v in o.items() if v not in (None, '')} for o in obras]
            r['duracion_min'] = sum(o['duracion_min'] or 0 for o in obras)
        funciones.append(r)
    # COBERTURA INVERSA, con un patrón PROPIO y más flojo que el del lector: todo
    # renglón que termina en una hora. La primera versión reusaba SLOT y se
    # aprobaba sola: el renglón con espacio duro no casaba en ninguno de los dos
    # y el bloque Comunitario faltaba con el chequeo en verde.
    L, _ = lineas()
    crudo_L = [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', json.load(io.open(
        FUENTE, encoding='utf-8'))['content']['rendered'])).split('\n') if x.strip()]
    # (desde el 30 sep, también el renglón que EMPIEZA con la hora: Terra Plaza)
    horas_impresas = [x for x in crudo_L if re.search(r'\d{1,2}(:\s*\d{2})?\s*[ap]\.?\s*m\.?\s*$', x, re.I)
                      or re.match(r'^\d{1,2}:\d{2}\s*[ap]\.?\s*m\.?\s', x, re.I)]
    repetidos = len(bloques) - len(vistos)
    # el bloque que comparte la hora de otro no imprime la suya (ver leer())
    sin_hora = sum(1 for b in bloques if b.get('_sin_hora_propia'))
    if len(horas_impresas) - repetidos + sin_hora != len(funciones) + len(fuera):
        fallos.append(f'{len(horas_impresas)} renglones con hora ({repetidos} repetidos) y '
                      f'{len(funciones)} funciones + {len(fuera)} fuera')
    if sum(len(f.get('obras', [])) for f in funciones) != sum(1 for x in crudo_L if re.match(r'^(.*\s)?dirigid', x, re.I)):
        fallos.append('las obras del crudo no son tantas como los créditos «dirigido…» de la página')
    if fallos:
        sys.exit('✗ la parrilla y el catálogo no coinciden:\n  · ' + '\n  · '.join(fallos))
    # LA DURACIÓN DEDUCIDA (ver el docstring)
    for f in funciones:
        if f.get('duracion_min'):
            continue
        ini = int(f['hora'][:2]) * 60 + int(f['hora'][3:])
        sig = sorted(int(g['hora'][:2]) * 60 + int(g['hora'][3:]) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and g['hora'] > f['hora'])
        f['duracion_min'] = min(sig[0] - ini, 90) if sig else 60
        f['_duracion_de'] = ('el hueco hasta la siguiente en la misma sede, con tope de 90' if sig
                             else '60: lo último del día en su sede')
        if not f.get('obras') and f.get('tipo') != 'evento':
            f['poster'] = '/assets/popayan-2026/muestra-de-cortos-internacionales.jpg'
            f['posterSource'] = 'oficial'
    # DOS BLOQUES DISTINTOS NO PUEDEN LLAMARSE IGUAL ([programa-mismo-titulo]):
    # la app identifica la obra por el título y enseñaría los cortos del primero
    # en todos. La versión del 30 sep trae cinco «Proyección Cine Corto
    # Familiar» y dos «CineCorto en el Barrio», cada uno con otros cortos. Como
    # en Jardín («… · Parte 1», «· Parte 2»): el orden en el festival; y si dos
    # van a la MISMA hora, la sede, que es lo único que los distingue.
    por_titulo = {}
    for f in funciones:
        if f.get('obras'):
            por_titulo.setdefault(f['titulo'], []).append(f)
    for t, fs in por_titulo.items():
        if len({tuple(o['titulo'] for o in f['obras']) for f in fs}) < 2:
            continue
        fs.sort(key=lambda f: (f['dia'], f['hora'], f['sede']))
        a_la_vez = len({(f['dia'], f['hora']) for f in fs}) < len(fs)
        for n, f in enumerate(fs, 1):
            f['titulo'] = f'{t} · {f["sede"]}' if a_la_vez else f'{t} · Parte {n}'
    sin_funcion = [o['titulo'] for o in cat if plano(o['titulo']) not in usadas]
    out = {'_provenance': provenance(
        'festicinepopayan.com, página de programación 2026 (wp-json, id 12543)',
        que_aporta='día, hora, sede y obras de cada bloque; el resto de la ficha, del catálogo',
        url=URL, metodo='wp-json + parser de renglones; cruce con el catálogo por título y dirección'),
        '_sin_funcion': {'porque': 'obras del catálogo que la parrilla del 6 oct no programa', 'obras': sin_funcion},
        '_fuera': fuera,
        'funciones': funciones}
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    n_obras = sum(len(f.get('obras', [])) for f in funciones)
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("tipo") == "evento")} actividades) · '
          f'{len(fuera)} solo para inscritos, fuera · '
          f'{n_obras} obras en programa · {len(sin_funcion)} del catálogo sin función → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
