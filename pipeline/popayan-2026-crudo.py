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
  · el SÁBADO 10 y el DOMINGO 11 no aparecen, aunque el festival dura hasta
    el 11: no se inventan; los 10 cortos de la sección Infantil del catálogo
    quedan sin función (se listan al final);
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
URL = 'https://festicinepopayan.com/fest2026/programacion2026/'
FUENTE = f'{REPO}/fuentes/{FID}/programacion2026.json'
CATALOGO = f'{REPO}/festivals/staging/popayan-2026-catalogo.json'
DESTINO = f'{REPO}/festivals/staging/popayan-2026-crudo.json'

DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) (\d{1,2}) de octubre$')
SLOT = re.compile(r'^(.+?) / (\d{1,2})(?::(\d{2}))?\s*(am|pm)$', re.I)
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
}

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
ACTIVIDADES = {'Apertura del Festival': 'apertura', 'Conversatorio': 'conversatorio'}
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
    return [x.strip() for x in t.split('\n') if x.strip()], d['modified']


def hora(h, m, ap):
    h = int(h) % 12 + (12 if ap.lower() == 'pm' else 0)
    return f'{h:02d}:{m or "00"}'


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
            i += 2
            if i < len(L) and L[i] == 'Películas':
                i += 1
                while i < len(L) and not SLOT.match(L[i]) and not DIA.match(L[i]):
                    tit = L[i]
                    i += 1
                    if tit.startswith(RELLENO):          # el relleno de la plantilla
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
    fallos, funciones, vistos, usadas = [], [], set(), set()
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
        r = {'titulo': b['titulo'], 'dia': b['dia'], 'hora': b['hora'], 'sede': sede, 'acceso': ACCESO,
             '_src': {'url': URL, 'date': modificada[:10]}}
        if sala:
            r['sala'] = sala
        if b['titulo'] in ACTIVIDADES:
            r.update({'tipo': 'evento', 'event_kind': ACTIVIDADES[b['titulo']], 'seccion': SECCION_ACTIVIDADES})
            funciones.append(r)
            continue
        seccion = BLOQUE.sub('', b['titulo']).strip()
        r['seccion'] = seccion
        obras = []
        for o in b['obras']:
            cat_t, pub_t = ALIAS.get(o['titulo'], (o['titulo'], None))
            c = idx.get(plano(cat_t))
            d = director(o['credito'])
            m = MINUTOS.search(o['credito'])
            if not c and o['titulo'] in SOLO_PARRILLA:
                obras.append({'titulo': o['titulo'], 'director': d,
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
                          'duracion_min': dur or c.get('duracion_min'), 'sinopsis': c.get('sinopsis')})
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
    horas_impresas = [x for x in crudo_L if re.search(r'\d{1,2}(:\d{2})?\s*[ap]\.?\s*m\.?\s*$', x, re.I)]
    repetidos = len(bloques) - len(vistos)
    if len(horas_impresas) - repetidos != len(funciones):
        fallos.append(f'{len(horas_impresas)} renglones con hora ({repetidos} repetidos) y {len(funciones)} funciones')
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
        if not f.get('obras') and f.get('tipo') != 'evento':
            f['poster'] = '/assets/popayan-2026/muestra-de-cortos-internacionales.jpg'
            f['posterSource'] = 'oficial'
    sin_funcion = [o['titulo'] for o in cat if plano(o['titulo']) not in usadas]
    out = {'_provenance': provenance(
        'festicinepopayan.com, página de programación 2026 (wp-json, id 13120)',
        que_aporta='día, hora, sede y obras de cada bloque; el resto de la ficha, del catálogo',
        url=URL, metodo='wp-json + parser de renglones; cruce con el catálogo por título y dirección'),
        '_sin_funcion': {'porque': 'la página no trae el sábado 10 ni el domingo 11', 'obras': sin_funcion},
        'funciones': funciones}
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    n_obras = sum(len(f.get('obras', [])) for f in funciones)
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("tipo") == "evento")} actividades) · '
          f'{n_obras} obras en programa · {len(sin_funcion)} del catálogo sin función → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
