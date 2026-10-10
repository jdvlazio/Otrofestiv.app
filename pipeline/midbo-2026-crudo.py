#!/usr/bin/env python3
"""midbo-2026-crudo.py — la 28 Muestra Internacional Documental de Bogotá → crudo.

LA FUENTE es la web del festival (midbo.co, WordPress). No hay grilla general:
la programación vive en la ficha de cada obra (`/peliculas/<slug>/`), en su
bloque «Funciones»:

    1 de noviembre / 19:30 H
    Sala Capital, Cinemateca de Bogotá
    Estreno en Colombia · *Con presencia del director · Adquiere tus entradas …

La lista de obras sale de la API (`/wp-json/wp/v2/pelicula`, 120) y cada una
trae su `seccion` de la taxonomía (`/wp-json/wp/v2/seccion`): la categoría
MADRE es la sección publicada («Competencia Nacional de Cortometraje
Documental») y la HIJA, si la hay, es el programa («Programa 1: Pasaje entre
mundos: duelo y memoria»): sus obras se proyectan juntas, y en la app son un
programa con sus obras.

LA VENTANA son las fechas oficiales, 28 oct–4 nov (regla de Juan, 8 oct): lo de
antes o después (las itinerancias de diciembre) queda fuera, anotado.
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
from lib import provenance  # noqa: E402

FID = 'midbo-2026'
DIR = f'{REPO}/fuentes/{FID}'
OUT = f'{REPO}/festivals/staging/midbo-2026-crudo.json'
# las FECHAS OFICIALES son las del afiche de la 28 MIDBO («27 de octubre al 4 de
# noviembre de 2026», @midbo_doc p/DeSf11QJ-Mp); el radar decía 28
DESDE, HASTA = '2026-10-27', '2026-11-04'
MES = {'octubre': 10, 'noviembre': 11, 'diciembre': 12}
FECHA = re.compile(r'^(\d{1,2}) de (octubre|noviembre|diciembre) / (\d{1,2}):(\d{2}) H$')
NOTA = re.compile(r'^(Adquiere tus entradas|Entrada libre.*|Estreno .*|\*Con presencia .*|MIDBO en Regiones|'
                  r'Duración total.*|Esta proyección hace parte .*|Función \d+:.*|\(.*\))$', re.I)

# LAS SEDES: lo que imprime la ficha → (sede, sala, ciudad)
SEDES = {
    'Sala Capital, Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Sala Capital', 'Bogotá'),
    'Sala 2, Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Sala 2', 'Bogotá'),
    'Sala 3, Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Sala 3', 'Bogotá'),
    'Sala 2 - Sala 3 - Sala Capital, Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Salas 2, 3 y Capital', 'Bogotá'),
    'Alianza Francesa': ('Alianza Francesa', '', 'Bogotá'),
    'Centro de Memoria, Paz y Reconciliación': ('Centro de Memoria, Paz y Reconciliación', '', 'Bogotá'),
    'Aula 1, Centro de Memoria, Paz y Reconciliación': ('Centro de Memoria, Paz y Reconciliación', 'Aula 1', 'Bogotá'),
    'Potocine, Ciudad Bolívar': ('Potocine', '', 'Bogotá'),
    'Auditorio Caldas, Universidad Central': ('Universidad Central', 'Auditorio Caldas', 'Bogotá'),
    'Canterbury Café, Kennedy': ('Canterbury Café', '', 'Bogotá'),
    'Auditorio Virginia Guitérrez, Posgrados de Ciencias Humanas, Universidad Nacional de Colombia, Bogotá':
        ('Universidad Nacional de Colombia', 'Auditorio Virginia Gutiérrez', 'Bogotá'),
    'Auditorio Salmona, Centro Cultural Gabriel García Márquez': ('Centro Cultural Gabriel García Márquez', 'Auditorio Salmona', 'Bogotá'),
    'Cinemateca del Caribe, Barranquilla': ('Cinemateca del Caribe', '', 'Barranquilla'),
    'UniNorte, Barranquilla': ('Universidad del Norte', '', 'Barranquilla'),
    'Sala Langosta Azul, Universidad del Magdalena, Santa Marta': ('Universidad del Magdalena', 'Sala Langosta Azul', 'Santa Marta'),
    'Cine club Cine 40 de Minca, Santa Marta': ('Cine club Cine 40', '', 'Minca'),
    'Cinemateca La Tertulia, Cali': ('Cinemateca La Tertulia', '', 'Cali'),
    'MAMM, El Poblado, Medellín': ('Museo de Arte Moderno de Medellín - MAMM', '', 'Medellín'),
    'Universidad de Antioquia, Paraninfo, sala de cine': ('Universidad de Antioquia', 'Paraninfo', 'Medellín'),
}
# LO QUE NO ES PARA EL PÚBLICO: dentro de cárceles y colegios (como en FICPA y Popayán)
SEDE_FUERA = {
    'Centro Penitenciario La Picota': 'función dentro de un centro penitenciario («MIDBO va a las cárceles»)',
    'Colegio Alejandro Obregón': 'función dentro de un colegio («MIDBO va a los colegios»)',
    'Colegio Manuelita Sáenz': 'función dentro de un colegio («MIDBO va a los colegios»)',
    'Auditorio Caldas, Servicio Forjar Restaurativo Arborizadora Baja, Ciudad Bolívar':
        'función dentro de un servicio de justicia restaurativa juvenil',
}


# ── EL SEMINARIO PENSAR LO REAL «Lenguajes sonoros» (página /encuentro-pensar-lo-
# real/seminario/): programación por día, «Lugar: …» y renglones «9:00 a.m. a
# 10:30 a.m. – Master Class: La escucha en el cine directo» con sus invitados
# debajo. Lo que no es actividad (registro, presentación) no se publica; la
# proyección comentada ya es función de su obra; el martes 27 cae fuera.
SEMINARIO = f'{DIR}/paginas/seminario.html'
SECCION_SEMINARIO = 'Encuentro Pensar lo Real'
KIND_SEM = {'master class': 'masterclass', 'mesa redonda': 'conversatorio', 'diálogo': 'dialogo',
            'charla': 'charla', 'lanzamiento': 'evento'}
SEDE_SEM = {'Sala Capital, Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Sala Capital'),
            'Sala Capital Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Sala Capital'),
            'Alianza Francesa, Sede Centro': ('Alianza Francesa', 'Sede Centro'),
            'Alianza Francesa': ('Alianza Francesa', '')}
DIA_SEM = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) (\d{1,2}) de (octubre|noviembre)$')
RENGLON = re.compile(r'^(\d{1,2})(?::(\d{2}))?\s*(a\.?\s*m\.?|p\.?\s*m\.?|m\.?)?\s*a\s+(\d{1,2})(?::(\d{2}))?\s*'
                     r'(a\.?\s*m\.?|p\.?\s*m\.?|m\.?)?\s*[–-]\s*(.+)$', re.I)


def _h24(h, m, ap):
    h = int(h); ap = (ap or '').lower().replace(' ', '').replace('.', '')
    # «2:30 m. a 4:00 p.m» (charla del 28): la página escribe «m.» por p. m.; una
    # hora de 1 a 7 sin «a. m.» en un seminario que abre a las 8 es de la tarde
    if (ap.startswith('p') or (ap in ('m', '') and 1 <= h <= 7)) and h < 12:
        h += 12
    return f'{h:02d}:{int(m or 0):02d}'


def seminario():
    L = lineas(SEMINARIO)
    L = L[L.index('Programación') + 1:]
    out, fuera, dia, lugar, i = [], [], None, None, 0
    while i < len(L) and not L[i].startswith('©'):
        x = re.sub(r'\[[a-z]\]', '', L[i]).strip()
        m = DIA_SEM.match(x)
        if m:
            dia = f'2026-{MES[m.group(3)]:02d}-{int(m.group(2)):02d}'
        elif x.startswith('Lugar:'):
            lugar = x.split(':', 1)[1].strip()
        else:
            r = RENGLON.match(x)
            if r:
                ini, fin = _h24(r.group(1), r.group(2), r.group(3)), _h24(r.group(4), r.group(5), r.group(6))
                act = r.group(7).strip()
                inv = []
                j = i + 1
                while j < len(L) and re.match(r'^(Invitad[oaex]s?|Modera)\s*:', L[j]):
                    inv.append(re.sub(r'\[[a-z]\]', '', L[j]).strip())
                    j += 1
                kind = next((v for k, v in KIND_SEM.items() if act.lower().startswith(k)), None)
                if not (DESDE <= dia <= HASTA):
                    fuera.append(f'{dia} {ini} {act[:50]}: fuera del 27 oct–4 nov oficial')
                elif kind is None:
                    fuera.append(f'{dia} {ini} {act[:50]}: no es una actividad del público (registro, presentación o proyección ya publicada)')
                else:
                    sede, sala = SEDE_SEM[lugar]
                    out.append({'titulo': act, 'dia': dia, 'hora': ini, 'sede': sede, **({'sala': sala} if sala else {}),
                                'ciudad': 'Bogotá', 'tipo': 'evento', 'event_kind': kind, 'seccion': SECCION_SEMINARIO,
                                'duracion_min': (int(fin[:2]) * 60 + int(fin[3:])) - (int(ini[:2]) * 60 + int(ini[3:])),
                                'acceso': 'desconocido',
                                **({'invitados': ' · '.join(inv) + '.'} if inv else {}),
                                '_src': {'url': 'https://midbo.co/encuentro-pensar-lo-real/seminario/', 'date': '2026-10-10'}})
                i = j
                continue
        i += 1
    return out, fuera


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def lineas(p):
    s = io.open(p, encoding='utf-8', errors='ignore').read()
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', s, flags=re.S)
    return [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', s)).split('\n') if x.strip()]


def bloques(p):
    """El bloque «Funciones» del HTML: cada <li> (cuándo, dónde) y el párrafo de
    observaciones (`funciones-obs`) que vale para TODAS las funciones de la obra:
    «Entrada libre», «Adquiere tus entradas», «Estreno en…», «*Con presencia…»."""
    s = io.open(p, encoding='utf-8', errors='ignore').read()
    i = s.find('funciones-lista')
    if i < 0:
        return []
    seg = s[i:s.find('</div>', s.find('funciones-obs', i) if 'funciones-obs' in s[i:i + 20000] else i)]
    t = lambda r: html.unescape(re.sub(r'<[^>]+>', ' ', r)).strip()
    obs_m = re.search(r'class="funciones-obs">(.*?)</p>', s[i:i + 20000], re.S)
    obs = [re.sub(r'\s+', ' ', t(x)) for x in re.split(r'<br\s*/?>', obs_m.group(1))] if obs_m else []
    obs = [x for x in obs if x]
    cta = re.search(r'class="link-cta" href="([^"]+)"', s[i:i + 20000])
    if cta:
        obs.append('TICKET ' + html.unescape(cta.group(1)))
    # «Función 1: proyección conjunta …» / «Función 2: proyección programa …»: cada
    # tramo de las observaciones es de SU función (la N-ésima de la lista); lo que
    # va antes del primer «Función N:» vale para todas
    tramos, comun, cur = {}, [], None
    for x in obs:
        m = re.match(r'^Función (\d+):\s*(.*)$', x)
        if m:
            cur = int(m.group(1)) - 1
            tramos.setdefault(cur, []).append(m.group(2))
        elif cur is None or x.startswith('TICKET '):
            comun.append(x)
        else:
            tramos[cur].append(x)
    out = []
    for n, li in enumerate(re.findall(r'<li>(.*?)</li>', seg, re.S)):
        c = re.search(r'f-cuando">(.*?)</span>', li, re.S); d = re.search(r'f-donde">(.*?)</span>', li, re.S)
        if c and d:
            out.append(([re.sub(r'\s+', ' ', t(c.group(1))), re.sub(r'\s+', ' ', t(d.group(1)))],
                        comun + tramos.get(n, [])))
    return out


def ficha(L, BLOQUES):
    k = L.index('Sinopsis') if 'Sinopsis' in L else None
    if k is None:
        k = L.index('Funciones') if 'Funciones' in L else None
    d = {}
    if 'Sinopsis' in L:
        fin = next((j for j in range(k + 1, len(L)) if L[j] in ('Reseña', 'Trailer', 'Funciones')), k + 2)
        d['sinopsis'] = ' '.join(L[k + 1:fin])
    dur = next((j for j in range(len(L)) if re.fullmatch(r'\d+ min', L[j])), None)
    if dur:
        d['duracion_min'] = int(L[dur].split()[0])
        d['director'], d['pais'] = L[dur - 3], L[dur - 2]
        if re.fullmatch(r'(19|20)\d{2}', L[dur - 1]):
            d['anio'] = int(L[dur - 1])
    fun = []
    for li, obs in BLOQUES:
        m = FECHA.match(li[0])
        if m:
            fun.append({'dia': f'2026-{MES[m.group(2)]:02d}-{int(m.group(1)):02d}',
                        'hora': f'{int(m.group(3)):02d}:{m.group(4)}', 'lugar': li[1], 'notas': obs})
    d['funciones'] = fun
    return d


def main():
    obras = json.load(io.open(f'{DIR}/pelicula-1.json', encoding='utf-8')) + \
        json.load(io.open(f'{DIR}/pelicula-2.json', encoding='utf-8'))
    S = {s['id']: s for s in json.load(io.open(f'{DIR}/seccion.json', encoding='utf-8'))}
    fuera, slots = [], {}
    for o in obras:
        titulo = html.unescape(o['title']['rendered']).strip()
        secs = [S[i] for i in o.get('seccion') or [] if i in S]
        hija = next((s for s in secs if s['parent']), None)
        # «Inauguración y clausura» es una SEGUNDA sección de dos obras de competencia:
        # la sección publicada es la competencia, y la función lleva el rótulo
        gala = any(s['name'] == 'Inauguración y clausura' for s in secs)
        madre = S[hija['parent']] if hija else next((s for s in secs if not s['parent']
                                                     and s['name'] != 'Inauguración y clausura'), None)
        _p = f'{DIR}/fichas/{o["slug"]}.html'
        d = ficha(lineas(_p), bloques(_p))
        for f in d['funciones']:
            if not (DESDE <= f['dia'] <= HASTA):
                fuera.append(f'{f["dia"]} {f["hora"]} {titulo[:50]}: fuera del 27 oct–4 nov oficial ({f["lugar"]})')
                continue
            if f['lugar'] in SEDE_FUERA:
                fuera.append(f'{f["dia"]} {f["hora"]} {titulo[:50]}: {SEDE_FUERA[f["lugar"]]}')
                continue
            if f['lugar'] not in SEDES:
                sys.exit(f'✗ sede sin entrada en la tabla: {f["lugar"]!r} ({titulo})')
            sede, sala, ciudad = SEDES[f['lugar']]
            # UN PROGRAMA, UNA FUNCIÓN: la ficha de cada corto puede dar SU hora de
            # inicio dentro del programa («Tanto trabajo por hacer»: 18:30 y 19:00,
            # el segundo al terminar el primero). Se agrupa por programa, día y sala,
            # y la función arranca con el primero.
            conjunta = any('proyección conjunta' in n.lower() for n in f['notas'])
            k = (f['dia'], f['lugar'], html.unescape(hija['name'])) if hija and not conjunta else (f['dia'], f['hora'], f['lugar'])
            s = slots.setdefault(k, {'obras': [], 'notas': set(), 'programa': None, 'hora': f['hora'],
                                     'sede': sede, 'sala': sala, 'ciudad': ciudad})
            s['hora'] = min(s['hora'], f['hora'])
            s['gala'] = gala
            s['obras'].append({'titulo': titulo, 'url': o['link'], 'madre': madre['name'] if madre else None,
                               **{c: d[c] for c in ('director', 'pais', 'anio', 'duracion_min', 'sinopsis') if d.get(c)}})
            s['notas'].update(f['notas'])
            if hija and not conjunta:
                s['programa'] = html.unescape(hija['name'])
    funciones = []
    for k, s in sorted(slots.items(), key=lambda kv: (kv[0][0], kv[1]['hora'])):
        dia, hora = k[0], s['hora']
        notas = s['notas']
        base = {'dia': dia, 'hora': hora, 'sede': s['sede'], **({'sala': s['sala']} if s['sala'] else {}),
                'ciudad': s['ciudad'],
                **({'ticket_url': next(n[7:] for n in notas if n.startswith('TICKET '))}
                   if any(n.startswith('TICKET ') for n in notas) else {}),
                'acceso': 'Boletería en TuBoleta' if any(n.startswith('TICKET ') for n in notas) else
                          ('Entrada libre' if any('entrada libre' in n.lower() for n in notas) else 'desconocido'),
                '_src': {'url': s['obras'][0]['url'], 'date': '2026-10-10'}}
        if any('con presencia' in n.lower() for n in notas):
            base['has_qa'], base['qa_type'] = True, 'team'
        est = next((re.search(r'Estreno en [A-ZÁÉÍÓÚ][\wáéíóú]+', n).group() for n in notas if re.search(r'Estreno en [A-ZÁÉÍÓÚ]', n)), None)
        if est:
            base['premiere'] = est
        if s.get('gala'):
            # la obra de inauguración es la que va en la noche del 28 en las tres salas;
            # la de clausura, la del 4 (las dos de «Inauguración y clausura»)
            base['premiere'] = 'Inauguración' if dia == '2026-10-28' else ('Clausura' if dia == HASTA else base.get('premiere'))
        # sin sección en la API («Cuando cierro los ojos»): palabra nuestra, como en Mamut
        madre = html.unescape(s['obras'][0]['madre'] or 'Proyecciones')
        if len(s['obras']) > 1 or s['programa']:
            # sin programa nombrado: si todas las obras son de la MISMA sección, el
            # bloque se llama como ella («Foco Santiago Álvarez»); si no, se nombran
            madres = {x['madre'] for x in s['obras']}
            titulo = s['programa'] or (html.unescape(madres.pop()) if len(madres) == 1 and None not in madres
                                       else ' + '.join(x['titulo'] for x in s['obras']))
            dt = next((re.search(r"Duración total[^0-9]*(\d+)'", n) for n in notas if re.search(r"Duración total[^0-9]*\d+'", n)), None)
            reg = {'titulo': titulo, **base, 'seccion': madre,
                   'obras': [{k: v for k, v in x.items() if k in ('titulo', 'director', 'pais', 'anio', 'duracion_min', 'sinopsis')}
                             for x in s['obras']],
                   'duracion_min': int(dt.group(1)) if dt else sum(x.get('duracion_min') or 0 for x in s['obras']) or None}
        else:
            x = s['obras'][0]
            reg = {**base, 'seccion': madre,
                   **{k: v for k, v in x.items() if k in ('titulo', 'director', 'pais', 'anio', 'duracion_min', 'sinopsis')}}
        funciones.append({k: v for k, v in reg.items() if v not in (None, '')})
    # DOS BLOQUES CON EL NOMBRE DE SU SECCIÓN y obras distintas (las dos funciones
    # del Homenaje a Pablo Mora): cada uno se nombra por sus obras, o la app
    # mostraría la lista de uno en el otro ([programa-mismo-titulo])
    _vistos = {}
    for f in funciones:
        if f.get('obras'):
            _vistos.setdefault(f['titulo'], set()).add(tuple(o['titulo'] for o in f['obras']))
    for f in funciones:
        if f.get('obras') and len(_vistos[f['titulo']]) > 1 and not f['titulo'].startswith('Programa'):
            f['titulo'] = ' + '.join(o['titulo'] for o in f['obras'])
    # COMILLAS RECTAS en el título ([title-normalization])
    for f in funciones:
        f['titulo'] = f['titulo'].replace('’', "'").replace('‘', "'")
        for o in f.get('obras') or []:
            o['titulo'] = o['titulo'].replace('’', "'").replace('‘', "'")
    sem, sem_fuera = seminario()
    funciones += sem
    fuera += sem_fuera
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('midbo.co — ficha de cada obra (bloque «Funciones») + API pelicula/seccion',
                                  url='https://midbo.co/', metodo='120 fichas; sección = categoría madre, programa = hija'),
        '_excluidas': fuera, 'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones · {sum(len(f.get("obras") or [1]) for f in funciones)} obras-función · '
          f'{len({(f["sede"], f["ciudad"]) for f in funciones})} sedes · {len(fuera)} fuera → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
