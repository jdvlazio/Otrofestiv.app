#!/usr/bin/env python3
"""filcmar-2026-crudo.py — la programación del 8° Festival de Cine de Marinilla → crudo.

LA FUENTE es el carrusel de programación de @filcmar, `p/Dd-Wc29Dhkd` (1 oct
2026): 16 láminas — 0 la portada (las cuatro sedes), 1 la leyenda de íconos,
2–14 los días (vie 9 a mar 13) y 15 los patrocinios. El pie: «🎟️ Entrada
libre». La web del festival (cinismoyalgomas.com/filcmar) solo trae la
programación académica.

MANDA LA LECTURA A OJO —fuentes/filcmar-2026-ojos-programa.json— y la OCR de las
mismas láminas la confirma (fuentes/filcmar-2026-ocr-programa.json): toda palabra
de 4+ letras del título, del crédito y de la sede, y toda hora, en SU lámina; y
en sentido inverso, cada hora impresa con su actividad.

LA SECCIÓN la dice el ÍCONO de cada bloque (lámina 1, la leyenda), tal cual: así
«Lo que queda del mar» va en Competencia Latinoamericana aunque se proyecte en el
bloque de Cinescuela. Los encabezados de bloque del día mandan sobre la leyenda
donde difieren («6.º Competencia Universitaria», «Competencia Espíritu del
Trasnoche»), por decisión de Juan (1 oct 2026).

LO QUE QUEDA FUERA (Juan, 1 oct 2026), ver EXCLUIDOS: el Taller Cacharrero
Óptico (su formulario se cerraba el 28 sep), la evaluación de biblias del Mercado
MORA (industria) y la Fiesta FILCMAR.

LO QUE LAS LÁMINAS NO DICEN, y no se inventa: la duración de las actividades (el
hueco hasta la siguiente en la misma sede, con DURACION_POR_DEFECTO de tope, la
regla de Mamut, Itagüí y Girardota) y la de la ceremonia de premiación.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'filcmar-2026'
POST = 'Dd-Wc29Dhkd'
OJOS = f'{REPO}/fuentes/filcmar-2026-ojos-programa.json'
OCR = f'{REPO}/fuentes/filcmar-2026-ocr-programa.json'
CATALOGO = f'{REPO}/festivals/staging/filcmar-2026-seleccion-oficial.json'
OUT = f'{REPO}/festivals/staging/filcmar-2026-crudo.json'
DURACION_POR_DEFECTO = 90

EXCLUIDOS = {
    'Taller Cacharrero Óptico': 'inscripción previa y su formulario «debe ser diligenciado antes '
        'del lunes 28 de septiembre» (linktr.ee/filcmar); Juan, 1 oct',
    'Mercado MORA — Presentación y Evaluación de Biblias de Producción - programa Películas en Camino':
        'sesión de industria del mercado, no abierta al público; Juan, 1 oct',
    'Fiesta FILCMAR': 'fiesta en el Bar de Juaneto; queda fuera, 1 oct',
}

# ── LAS SEDES: lo que imprime la lámina → (sede, sala). La Casa Cultural y el
# Teatro Regional son dos edificios vecinos (Google Maps los ubica a 15 m); el
# Foso es una sala del Teatro Regional.
SEDES = {
    'Teatro Regional Valerio Antonio Jiménez': ('Teatro Regional Valerio Antonio Jiménez', None),
    'Foso Teatro Regional Valerio Antonio Jiménez': ('Teatro Regional Valerio Antonio Jiménez', 'Foso'),
    'Teatro Municipal Simona Duque': ('Teatro Municipal Simona Duque', None),
    'Parque Principal de Marinilla': ('Parque Principal de Marinilla', None),
    'punto de partida: parque principal': ('Parque Principal de Marinilla', None),
    'Galería San José - CBA Marinilla': ('Galería San José - CBA Marinilla', None),
    'Hall Casa Cultural Valerio Antonio Jiménez': ('Casa Cultural Valerio Antonio Jiménez', 'Hall'),
    'Salón Artes Plásticas, Casa Cultural Valerio Antonio Jiménez':
        ('Casa Cultural Valerio Antonio Jiménez', 'Salón Artes Plásticas'),
    'Capilla Casa Cultural Valerio Antonio Jiménez': ('Casa Cultural Valerio Antonio Jiménez', 'Capilla'),
    'Bar de Juaneto': ('Bar de Juaneto', None),
}

# ── LAS SECCIONES, por el ícono (lámina 1). Los nombres, tal cual.
SECCION = {
    'Competencia Universitaria': '6.º Competencia Universitaria',
    'Competencia Latinoamericana': 'Competencia Latinoamericana',
    'Espíritu del Trasnoche': 'Competencia Espíritu del Trasnoche',
    'Cinescuela': 'Cinescuela',
    'Viejos secretos del nuevo Oeste': 'Viejos secretos del nuevo Oeste',
    'Programación Académica': 'Programación Académica',
    'Programación MORA': 'Programación MORA',
    'Programación Cultural': 'Programación Cultural',
    # la ceremonia lleva un trofeo que no está en la leyenda
    'trofeo': 'Programación Cultural',
}

# ── LAS ACTIVIDADES que no son proyección: título → event_kind (palabras ya en
# el mapa de la app; ninguna nueva).
ACTIVIDAD = {
    'MAPISTAS Expo FILCMAR 8': 'evento',
    'Taller Escritura y Reescritura': 'taller',
    'Taller Juguetería Audiovisual': 'taller',
    'Tintico Charlado: Mercado MORA — Oriente como destino audiovisual': 'charla',
    'Tintico Charlado: Mercado MORA — El cine ¿es medio o es fin?': 'charla',
    'Tintico Charlado: Mercado MORA — Antioquia Film Friendly': 'charla',
    'Conversatorio: Secretos de chifonier': 'conversatorio',
    'Mercado MORA — Pitch público Películas en Camino MORA': 'evento',
    'Concierto Central: Edson Velandia': 'evento',
    'CAMINATA FOTOGRÁFICA': 'experiencia',
    'Ceremonia de premiación — Premiación MORA y Competencias': 'acto',
}
# La caja sostenida de la lámina no se publica (caja-sostenida): la palabra, en
# frase; MAPISTAS es el nombre propio de la expo y se queda.
TITULO = {'CAMINATA FOTOGRÁFICA': 'Caminata fotográfica',
          # el renglón de abajo va como texto: «premiación» dos veces en un título
          'Ceremonia de premiación — Premiación MORA y Competencias': 'Ceremonia de premiación'}

# LO QUE EL FESTIVAL DICE DE UNA ACTIVIDAD en su propio post, que la lámina no
# trae: frases del pie, literales y recortadas.
SINOPSIS = {
    'Taller Escritura y Reescritura':  # p/DdZWR0ulRvS
        'Del guion al montaje: taller de escritura y reescritura, en alianza con Centro Ático. '
        'Lo guía Juan C. López, editor y postproductor. En este taller exploraremos cómo la '
        'narrativa pasa del papel y se reescribe activamente durante la etapa de edición. '
        'Cupos limitados.',
    'Taller Juguetería Audiovisual':  # p/DdcQBaRFZqB
        'Un taller abierto a niños, jóvenes y adultos para acercarnos de forma práctica y '
        'divertida al principio didáctico y fascinante de la imagen en movimiento. La comunidad '
        'construirá sus propios juguetes ópticos y los pondrá a prueba para explorar cómo nace '
        'la ilusión que le da vida al cine. Lo guían Carolina del Castillo y Marcela Restrepo '
        '(Corporación Trama). Sin inscripción previa.',
    'Ceremonia de premiación — Premiación MORA y Competencias': 'Premiación MORA y Competencias.',
}

# LO QUE LA WEB DEL FESTIVAL DICE Y LA LÁMINA NO (cinismoyalgomas.com/filcmar/
# programacionacademica, leída el 2 oct): el taller de escritura va de 9:00 a.m. a
# 1:00 p.m., y la Juguetería es a las 2:00 p.m. —lo mismo que su post
# p/DdcQBaRFZqB—; la lámina de programación decía 1:30. Dos fuentes contra una,
# aprobado por Juan (2 oct).
DURACION_DE_OTRA_FUENTE = {'Taller Escritura y Reescritura': 240}
HORA_DE_OTRA_FUENTE = {('Taller Juguetería Audiovisual', '2026-10-11', '13:30'): '14:00'}

INSCRIPCION = {
    # linktr.ee/filcmar; inscripciones extendidas al 5 oct (p/Dd4ajjCz5Go)
    'Taller Escritura y Reescritura': 'https://docs.google.com/forms/d/e/1FAIpQLScPop2bHx6C7Mf7yzrjH7Q1lRP9EG_DXEmzve4oJzRQ_lEsOA/viewform',
}

# EL TÍTULO DE LA PROGRAMACIÓN y el del catálogo: la lámina de la Selección
# Oficial la presentó con su título original («Persépio», portugués); la
# programación la traduce. Se publica como la programación; el original va aparte.
TITULO_EN_CATALOGO = {'El pesebre': 'Persépio'}

# EL TÍTULO DE LA OBRA donde la lámina se aparta de cómo la obra se llama: las
# tres fuentes independientes coinciden (TMDB, IMDb y FilmAffinity, mirado el 2
# oct 2026) y Juan lo aprobó. Lo demás se publica como lo escribe el festival.
TITULO_OFICIAL = {
    'MU KI RA': 'Mu-Ki-Ra',
    'Si no ardemos cómo iluminar la noche': 'Si no ardemos, cómo iluminar la noche',
    # al festival se le cayó el «en» en las dos láminas
    'Una vez un cuerpo': 'Una vez en un cuerpo',
}
# EL TÍTULO DE UN CORTO DE PROGRAMA donde el festival mismo lo escribió después
# como TMDB: su post de Espíritu del Trasnoche (p/DeH5TQzFeHV, 4 oct) dice
# «Show de Ziggy: La maldición del mariachi bondage». Juan, 6 oct.
TITULO_OFICIAL_CORTO = {
    'Show de Ziggy: la maldición del Mariachi Bondage': 'Show de Ziggy: La maldición del mariachi bondage',
}

# LO QUE COMPLETAMOS NOSOTROS (Juan, 6 oct), con su porqué:
#   · el PAÍS de la Competencia Universitaria: la lámina pone la universidad
#     donde la Latinoamericana pone el país; las universidades colombianas dan
#     una producción colombiana. «La pecera» (Academia de Artes de China) queda
#     sin país;
#   · el de los tres cortos en 8 mm: «Grupo experimental cine Caldas», la lámina;
#   · la DIRECCIÓN de HDLT: «Colectivo Artefactum Suba», como la acreditan
#     Popayán («dirigido y producido por») y Honda («Dir.»); acá solo producía.
UNIVERSIDAD_COLOMBIANA = {
    'Politécnico Colombiano Jaime Isaza Cadavid', 'Universidad del Magdalena',
    'Universidad Central de Bogotá', 'Pontificia Universidad Javeriana',
    'Universidad Jorge Tadeo Lozano', 'Universidad de los Andes',
    'Universidad Nacional de Colombia', 'Universidad Autónoma de Bucaramanga',
    'Instituto Tecnológico Metropolitano',
}
PAIS_8MM = 'Colombia'
DIRECTOR_DECLARADO = {'HDLT': 'Colectivo Artefactum Suba'}

PAIS = {'Brazil': 'Brasil', 'Colombia / Estados Unidos': 'Colombia, Estados Unidos'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def hora_impresa(h):
    a, b = map(int, h.split(':'))
    suf = 'a m' if a < 12 else 'p m'
    a = a - 12 if a > 12 else a
    return f'{a} {b:02d} {suf}'


def dur(s):
    """«19:52min» → 20; «110min» → 110."""
    m = re.match(r'(\d+)(?::(\d+))?', s)
    return int(m.group(1)) + (1 if m.group(2) and int(m.group(2)) >= 30 else 0)


def verifica(ojos):
    cajas = json.load(io.open(OCR, encoding='utf-8'))
    texto = {int(k[:2]): plano(' '.join(v)) for k, v in cajas.items()}
    fallos = []
    for a in ojos:
        t, w = texto[a['lamina']], set(texto[a['lamina']].split())
        piezas = [a.get('titulo') or '', a.get('sede') or '', a.get('credito') or '']
        piezas += [o['titulo'] + ' ' + o['direccion'] for o in a.get('obras', [])]
        piezas += a.get('cortos', [])
        for p in piezas:
            faltan = [x for x in plano(p).replace(' o ', ' ').split()
                      if len(x) >= 4 and x not in w and x not in ('programa',)]
            if faltan:
                fallos.append(f'lámina {a["lamina"]}: la OCR no encuentra {faltan} de «{p}»')
        if hora_impresa(a['hora']) not in t:
            fallos.append(f'lámina {a["lamina"]}: la OCR no encuentra la hora {a["hora"]}')
    for k, v in cajas.items():
        n = int(k[:2])
        impresas = sum(1 for x in v if re.match(r'^\d{1,2}:\d{2}\s*[ap]\.?m', x.strip()))
        propias = sum(1 for a in ojos if a['lamina'] == n)
        if impresas != propias:
            fallos.append(f'lámina {n}: {impresas} horas impresas y {propias} actividades')
    return fallos


def obra(o, cat):
    t = o['titulo']
    c = cat.get(plano(TITULO_EN_CATALOGO.get(t, t)))
    r = {'titulo': TITULO_OFICIAL.get(t, t), 'director': o['direccion'], 'pais': PAIS.get(o['pais'], o['pais']),
         'anio': o['anio'], 'duracion_min': dur(o['duracion'])}
    if c:
        # el catálogo trae el crédito completo («Di Cunto, Medrano y Bochard»)
        r.update({k: c[k] for k in ('director', 'pais', 'anio', 'duracion_min') if c.get(k)})
    if t in TITULO_EN_CATALOGO:
        r['titulo_original'] = TITULO_EN_CATALOGO[t]
    return {k: v for k, v in r.items() if v}


def corto(t, cat):
    c = cat[plano(t)]
    r = {k: c[k] for k in ('titulo', 'director', 'pais', 'anio', 'duracion_min') if c.get(k)}
    r['titulo'] = TITULO_OFICIAL_CORTO.get(r['titulo'], r['titulo'])
    if not r.get('pais') and c.get('universidad') in UNIVERSIDAD_COLOMBIANA:
        r['pais'] = 'Colombia'
    if not r.get('director') and c['titulo'] in DIRECTOR_DECLARADO:
        r['director'] = DIRECTOR_DECLARADO[c['titulo']]
    return r


def duracion_sin_dato(funciones):
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede']
                     and g.get('sala') == f.get('sala') and mins(g['hora']) > mins(f['hora']))
        hueco = sig[0] - mins(f['hora']) if sig else None
        if hueco and hueco <= DURACION_POR_DEFECTO:
            f['duracion_min'] = hueco
            f['_duracion_de'] = 'el hueco hasta la siguiente actividad en la misma sede'
        else:
            f['duracion_min'] = DURACION_POR_DEFECTO
            f['_duracion_de'] = f'{DURACION_POR_DEFECTO} min declarados: la lámina no la da'


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['actividades']
    fallos = verifica(ojos)
    if fallos:
        sys.exit('✗ la transcripción y la OCR no coinciden:\n  · ' + '\n  · '.join(fallos))
    cat = {plano(o['titulo']): o for o in json.load(io.open(CATALOGO, encoding='utf-8'))['obras']}

    funciones, fuera = [], []
    for a in ojos:
        t = a.get('titulo')
        if t in EXCLUIDOS:
            fuera.append(f'{a["dia"]} {a["hora"]} {t}')
            continue
        if a['sede'] not in SEDES:
            sys.exit(f'✗ sede sin entrada en la tabla: {a["sede"]!r}')
        sede, sala = SEDES[a['sede']]
        base = {'dia': a['dia'], 'hora': a['hora'], 'sede': sede, **({'sala': sala} if sala else {}),
                'acceso': 'Entrada libre',
                '_src': {'url': f'https://www.instagram.com/p/{POST}/', 'date': '2026-10-01',
                         'lamina': a['lamina']}}
        if a.get('edad'):
            base['clasificacion'] = a['edad']
        if a.get('presencia'):
            base['has_qa'], base['qa_type'] = True, 'team'

        # (1) UN PROGRAMA con nombre: modelo A
        if a.get('cortos') or t == 'Cortoconcierto inaugural Antioquia Super Ochera':
            reg = {'titulo': t, **base, 'seccion': SECCION[a['icono']]}
            reg['obras'] = ([corto(x, cat) for x in a['cortos']] if a.get('cortos')
                            else [obra(o, cat) for o in a['obras']])
            if t.startswith('Cortoconcierto'):
                reg['obras'] = [{**o, 'pais': o.get('pais') or PAIS_8MM} for o in reg['obras']]
            reg['duracion_min'] = sum(o.get('duracion_min') or 0 for o in reg['obras'])
            if t.startswith('Cortoconcierto'):
                reg['premiere'] = 'Inauguración'
                reg['sinopsis'] = a['texto'].rstrip(':') + '.'
            funciones.append(reg)
            continue
        # (2) UNA ACTIVIDAD; con obras, ellas comparten su función (anclaje)
        if t in ACTIVIDAD:
            reg = {'titulo': TITULO.get(t, t), **base, 'seccion': SECCION[a['icono']],
                   'tipo': 'evento', 'event_kind': ACTIVIDAD[t]}
            # UNA CHARLA DEL MORA lleva su tema en el título («… — Oriente como
            # destino audiovisual») y quién la da en el renglón de abajo. Como
            # `invitados` las dos de la Comisión Fílmica quedaban con el mismo
            # texto ([sinopsis-duplicada]); juntas, con palabras de la lámina, no.
            if a.get('credito') and t.startswith('Tintico Charlado'):
                reg['sinopsis'] = f'{t.split(" — ", 1)[1].rstrip("?")}{"?" if t.endswith("?") else "."} {a["credito"]}.'
            elif a.get('credito'):
                reg['invitados'] = f'Invitados: {a["credito"]}.'
            if a.get('texto'):
                reg['sinopsis'] = a['texto'].rstrip('.') + '.'
            if t in SINOPSIS:
                reg['sinopsis'] = SINOPSIS[t]
            if t in DURACION_DE_OTRA_FUENTE:
                reg['duracion_min'] = DURACION_DE_OTRA_FUENTE[t]
            reg['hora'] = HORA_DE_OTRA_FUENTE.get((t, a['dia'], a['hora']), reg['hora'])
            if t in INSCRIPCION:
                reg['acceso'] = 'Entrada libre con inscripción previa'
                reg['registration_url'] = INSCRIPCION[t]
            if sum(1 for x in ojos if x.get('titulo') == t) > 1:
                reg['is_recurring'] = True
            funciones.append(reg)
        elif t not in (None, 'Cinescuela', 'Competencia Latinoamericana', 'Película de Clausura'):
            sys.exit(f'✗ bloque sin decidir: {t!r}')
        # (3) LAS OBRAS del bloque: cada una su función, en anclaje
        for o in a.get('obras', []):
            reg = {**obra(o, cat), **base, 'seccion': SECCION[o['icono'] or a['icono']]}
            if t == 'Película de Clausura':
                reg['premiere'] = 'Clausura'
            funciones.append(reg)

    duracion_sin_dato(funciones)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @filcmar — el carrusel de programación (16 láminas)',
            que_aporta='la programación entera: día, hora, lugar, sección y créditos',
            url=f'https://www.instagram.com/p/{POST}/',
            metodo='lectura a ojo lámina por lámina, confirmada con la OCR de las mismas '
                   'láminas, en los dos sentidos'),
        '_excluidas': {'funciones': fuera, 'por_que': EXCLUIDOS},
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} funciones ({len(funciones) - n_ev} proyecciones + {n_ev} '
          f'actividades) · {len({f["sede"] for f in funciones})} sedes · fuera: {len(fuera)} '
          f'→ {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
