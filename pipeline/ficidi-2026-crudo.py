#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficidi-2026-crudo.py — el Calendario de programación del IV FICIDI → crudo.

JERARQUÍA DE FUENTES (declarada):
  1. fuentes/ficidi-2026/Calendario_IV_FICIDI_2026.pdf — el calendario que el
     festival ENVIÓ (29 oct 2026). Manda en días, sedes, horas, qué obras van en
     cada función, su orden, el país y el título (texto seleccionable,
     `pdftotext -layout`).
  2. Las láminas de Instagram de la programación (DfA_GjWkT_g: día 1, 2:00 p. m.;
     DfDlyoFEdJD: inaugural), leídas con pipeline/ocr.py y mirando la imagen:
     dan la DURACIÓN y la dirección de esas 17 obras (el PDF no da duraciones).
  3. El catálogo de la Selección Oficial (ficidi-2026-catalogo.json, pre-
     onboarding de las grillas de IG): dirección y país de las demás.
  4. TMDB verificada (ficidi-2026-catalogo-enriquecido.json y, de una corrida
     anterior, ficidi-2026-enriquecido.json): la duración de las obras que la
     lámina no da. Si falta, la obra va SIN duración.

LAS REGLAS:
  · cada bloque del PDF es UNA función con sus obras (`obras`). El festival no
    nombra los bloques salvo dos («La memoria revelada», «Revelar(se)»); el
    título de los demás es el rótulo del PDF tal cual («Día 1 · Primera
    función»). Propuesta, a confirmar con Juan.
  · cada obra del PDF TIENE que cruzar con el catálogo (por título normalizado o
    por la tabla ALIAS de abajo); si no, el paso falla.
  · el título publicado es el del PDF, salvo mayúscula sostenida (AR-DOR, NO):
    ahí va la caja del catálogo.
  · la duración del bloque: el 3 nov la da el PDF (2:00–6:00 p. m.); los demás,
    la SUMA de sus obras; si a alguna le falta, la suma es parcial y se declara
    en `_duracion_de`. 29 oct 2026, Juan: «Publica con la estimada» → a cada
    obra sin duración se le suma el PROMEDIO de las obras con duración del
    festival, y queda declarado ESTIMADA hasta que el festival dé la hora de fin.
  · acceso: «La entrada es completamente GRATIS.» (PDF, pág. 5) → todas.
"""
import io

FIN_FESTIVAL = {'18:00': '21:00', '09:00': '12:00'}
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'ficidi-2026'
PDF = f'{REPO}/fuentes/{FID}/Calendario_IV_FICIDI_2026.pdf'
CAT = f'{REPO}/festivals/staging/{FID}-catalogo.json'
CATENR = f'{REPO}/festivals/staging/{FID}-catalogo-enriquecido.json'
DESTINO = f'{REPO}/festivals/staging/ficidi-2026-crudo.json'
ENR = f'{REPO}/festivals/staging/{FID}-enriquecido.json'
ACCESO = 'Entrada libre'   # «La entrada es completamente GRATIS.»

DIAS = {'MARTES 3': '2026-11-03', 'MIÉRCOLES 4': '2026-11-04', 'JUEVES 5': '2026-11-05',
        'VIERNES 6': '2026-11-06', 'SÁBADO 7': '2026-11-07'}
# la sede como la escribe el PDF (sin la dirección) → sede canónica + sala
SEDES = [
    ('Sala CIMU · Aduana de Barranquilla', 'Aduana de Barranquilla', 'Sala CIMU'),
    ('Universidad Simón Bolívar', 'Universidad Simón Bolívar, sede 1', 'Salón del Mirador de la Bandera (azotea)'),
    ('Alianza Francesa de Barranquilla', 'Alianza Francesa de Barranquilla', ''),
    ('Maloca Cultural', 'La Maloca Cultural', ''),
    ('Universidad de la Costa', 'Universidad de la Costa – CUC', 'Bloque 11, piso 3 · Sala de Conferencias'),
    ('Auditorio EDA Fabrica de Cultura', 'La Fábrica de Cultura', 'Auditorio EDA'),
]
# título del PDF → título del catálogo, donde no coinciden normalizados
ALIAS = {
    '621km': '621 km',
    '1 año y un mes en Colombiamaricx': '1 año y un mez en Colombiamaricx',   # «mez»: errata de la lectura de IG
}
# LÁMINAS DE IG (dirección y minutos pintados), mirados uno por uno el 29 oct.
# «(28)» y «(11)»: así, entre paréntesis, en Exilio y Travas sobrevivientes; las
# otras 15 dicen «N MIN». Travas: TMDB da 11 → el paréntesis son minutos.
LAMINA = {
    'Exilio': ('DfA_GjWkT_g/01', 'Ander Parra', 28),
    'Muñecas de porcelana': ('DfA_GjWkT_g/02', 'Antonio José López Gómez', 8),
    'Aquí donde soy': ('DfA_GjWkT_g/03', 'Daniel Braga Alonso', 22),
    'Ius del tiempo': ('DfA_GjWkT_g/04', 'Roberto F. Canuto, Xiaoxi Xu', 25),
    'Inés': ('DfA_GjWkT_g/05', 'José Antonio Gutiérrez Moreno', 11),
    'Onades': ('DfA_GjWkT_g/06', 'Andoni Martínez', 15),
    'Todos los nombres empiezan con M': ('DfA_GjWkT_g/07', 'Carla Scolari', 19),
    'Verdulera': ('DfA_GjWkT_g/08', 'Jose Barbado', 5),
    'Travas sobrevivientes': ('DfDlyoFEdJD/02', 'Valeria Meneguzzi, Cristian Gonzalez', 11),
    'Transitar lo marica negro': ('DfDlyoFEdJD/03', 'May Romero Quiñones', 6),
    'Yo soy yo': ('DfDlyoFEdJD/04', 'Norberto Díaz', 22),
    'Maricones': ('DfDlyoFEdJD/05', 'Maria Paz Ruiz Gonzalez', 14),
    'Solo Natalie': ('DfDlyoFEdJD/06', 'Natalie Ramón Ramírez', 13),
    'Reina de polvo y luz': ('DfDlyoFEdJD/07', 'José Luis Ostos Molina', 16),
    'Más allá de la corona': ('DfDlyoFEdJD/08', 'Juan David Mesa Buitrago', 15),
    'Miradas Trans-Parentes': ('DfDlyoFEdJD/09', 'Efra', 3),
    'Made to Shine': ('DfDlyoFEdJD/10', 'Mariana Gutiérrez Zapata', 8),
}
PAIS = {'BRASIL': 'Brasil', 'ARGENTINA': 'Argentina', 'COLOMBIA': 'Colombia', 'ESPAÑA': 'España',
        'REINO UNIDO': 'Reino Unido', 'ITALIA': 'Italia', 'CHILE': 'Chile'}


def plano(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


def mins(h):
    return int(h[:2]) * 60 + int(h[3:5])


def h24(s):
    m = re.match(r'(\d{1,2}):(\d\d)\s*([ap])\.\s*m\.', s)
    h = int(m.group(1)) % 12 + (12 if m.group(3) == 'p' else 0)
    return f'{h:02d}:{m.group(2)}'


def texto():
    t = subprocess.run(['pdftotext', '-layout', PDF, '-'], capture_output=True, text=True, check=True).stdout
    t = re.sub(r'^.*FICIDI 2026 • LA MEMORIA REVELADA\s*$', '', t, flags=re.M)   # pie de página
    return t


def bloques(t):
    """[(cabecera, línea de sede, cuerpo)] por cada «DÍA N DE NOVIEMBRE | rótulo»."""
    cab = list(re.finditer(r'^\s+(LUNES|MARTES|MIÉRCOLES|JUEVES|VIERNES|SÁBADO) (\d+) DE NOVIEMBRE\s+\|\s*(.+?)\s*$\n\s*(.+?)\s*$',
                           t, re.M))
    fin = t.index('PARA DISFRUTAR EL FICIDI')
    out = []
    for i, m in enumerate(cab):
        cuerpo = t[m.end(): cab[i + 1].start() if i + 1 < len(cab) else fin]
        out.append((f'{m.group(1)} {m.group(2)}', m.group(3), m.group(4), cuerpo))
    return out


def obras_de(cuerpo):
    # una obra: «NN Título · PAÍS — sinopsis», que puede seguir en la línea de abajo
    lineas, cur = [], None
    for ln in cuerpo.splitlines():
        if re.match(r'^\d\d ', ln):
            cur = ln.strip()
            lineas.append(cur)
        elif cur is not None and ln.strip():
            lineas[-1] += ' ' + ln.strip()
        elif not ln.strip():
            cur = None
    out = []
    for ln in lineas:
        m = re.match(r'^(\d\d) (.+?) · (.+?) — (.+)$', ln)
        if not m:
            sys.exit(f'✗ línea de obra sin forma: {ln!r}')
        out.append({'n': int(m.group(1)), 'titulo': m.group(2).strip(), 'marca': m.group(3).strip(),
                    'sinopsis': m.group(4).strip()})
    return out


def main():
    cat = json.load(io.open(CAT, encoding='utf-8'))['obras']
    por_t = {plano(o['titulo']): o for o in cat}
    enr = {plano(o['titulo']): o for o in json.load(io.open(CATENR, encoding='utf-8'))['obras']}
    # y las fichas que encontró enriquecer.py sobre las obras de las funciones
    # (corrida anterior): solo su duración verificada, si el catálogo no la tiene
    if os.path.exists(ENR):
        for t, e in json.load(io.open(ENR, encoding='utf-8'))['verificadas'].items():
            for k in {plano(t)} | {plano(c) for c in ALIAS.values() if plano(ALIAS.get(t, '')) == plano(c)}:
                if e.get('duracion_tmdb') and not (enr.get(k) or {}).get('duracion_tmdb'):
                    enr[k] = e
    t = texto()
    funciones, usadas, avisos = [], set(), []
    for dia_k, rotulo, sede_ln, cuerpo in bloques(t):
        m = re.search(r'•\s*(\d{1,2}:\d\d\s*[ap]\.\s*m\.)(?:\s*–\s*(\d{1,2}:\d\d\s*[ap]\.\s*m\.))?', sede_ln)
        hora = h24(m.group(1))
        hasta = h24(m.group(2)) if m.group(2) else None
        sede = next((s for s in SEDES if sede_ln.startswith(s[0])), None)
        if not sede:
            sys.exit(f'✗ sede sin tabla: {sede_ln!r}')
        obras = obras_de(cuerpo)
        if [o['n'] for o in obras] != list(range(1, len(obras) + 1)):
            sys.exit(f'✗ {dia_k}: numeración rota {[o["n"] for o in obras]}')
        lista = []
        for o in obras:
            c = por_t.get(plano(ALIAS.get(o['titulo'], o['titulo'])))
            if not c:
                sys.exit(f'✗ obra del PDF sin catálogo: {o["titulo"]!r}')
            usadas.add(c['titulo'])
            tit = c['titulo'] if o['titulo'].isupper() else o['titulo']   # caja sostenida
            lam = LAMINA.get(o['titulo'])
            e = enr.get(plano(c['titulo'])) or enr.get(plano(tit)) or {}
            dur, dur_de = None, None
            if lam:
                dur, dur_de = lam[2], f'lámina IG {lam[0]}'
                if e.get('duracion_tmdb') and abs(e['duracion_tmdb'] - lam[2]) > 1:
                    avisos.append(f'{tit}: lámina {lam[2]} min, TMDB {e["duracion_tmdb"]} — manda la lámina')
            elif e.get('duracion_tmdb'):
                dur, dur_de = e['duracion_tmdb'], f'TMDB {e["tmdb_id"]}'
            pais = PAIS.get(o['marca'].upper(), c.get('pais'))
            r = {'titulo': tit, 'director': lam[1] if lam else c.get('director'), 'pais': pais,
                 'duracion_min': dur, 'sinopsis': o['sinopsis'],
                 '_src': {'pdf': f'{os.path.basename(PDF)} · {dia_k} nov, obra {o["n"]:02d}',
                          'duracion': dur_de, 'catalogo': c['titulo']}}
            if lam and lam[1] != c.get('director'):
                avisos.append(f'{tit}: dirección lámina «{lam[1]}» / catálogo «{c.get("director")}» — manda la lámina')
            if o['marca'] not in PAIS and o['marca'].upper() not in PAIS:
                r['_src']['pais'] = f'el PDF dice «{o["marca"]}»; país del catálogo'
            lista.append({k: v for k, v in r.items() if v not in (None, '')})
        # título y descripción de la función
        intro = re.split(r'^\d\d ', cuerpo, maxsplit=1, flags=re.M)[0]
        intro = ' '.join(intro.split())
        f = {'dia': DIAS[dia_k], 'hora': hora, 'sede': sede[1], 'acceso': ACCESO,
             'seccion': 'Selección Oficial', 'is_programa': True, 'obras': lista,
             '_src': {'pdf': os.path.basename(PDF), 'cabecera': f'{dia_k} DE NOVIEMBRE | {rotulo}',
                      'sede': sede_ln}}
        if sede[2]:
            f['sala'] = sede[2]
        if rotulo == 'Proyección especial':
            f['titulo'], f['seccion'] = 'Proyección especial', 'Proyección especial'
            f['sinopsis'] = 'Siete cortometrajes.'
        elif 'Inauguración' in rotulo:
            f['titulo'], f['premiere'] = 'La memoria revelada', 'Inauguración'
            f['sinopsis'] = re.sub(r'^FUNCIÓN INAUGURAL · LA MEMORIA REVELADA ', '', intro)
            f['has_qa'], f['qa_type'] = True, 'guests'     # conversatorio con invitados
        elif 'REVELAR(SE)' in rotulo:
            f['titulo'] = 'Revelar(se)'
            f['sinopsis'] = intro.replace('T onnie', 'Tonnie')
            f['has_qa'], f['qa_type'] = True, 'team'       # conversatorios con equipo y director
        else:
            f['titulo'] = rotulo
        # 29 oct 2026, respuesta del festival a Juan: «Las que son a las 6:00 PM
        # son hasta las 9:00 PM. El de las 9:00 AM son hasta las 12:00 PM»
        if not hasta and hora in FIN_FESTIVAL:
            f['duracion_min'] = mins(FIN_FESTIVAL[hora]) - mins(hora)
            f['_duracion_de'] = f'el festival a Juan (29 oct): hasta las {FIN_FESTIVAL[hora]}'
        elif hasta:
            f['duracion_min'] = mins(hasta) - mins(hora)
            f['_duracion_de'] = 'el PDF: 2:00 p. m. – 6:00 p. m.'
        else:
            ds = [o.get('duracion_min') for o in lista]
            f['duracion_min'] = sum(d for d in ds if d)
            faltan = [o['titulo'] for o in lista if not o.get('duracion_min')]
            f['_duracion_de'] = (f'suma de las {len(lista)} obras' if not faltan else
                                 f'suma PARCIAL: {len(lista) - len(faltan)} de {len(lista)} obras con duración; '
                                 f'sin duración: {" · ".join(faltan)}')
        if f.get('has_qa') and f['_duracion_de'].startswith('el festival'):
            # la app suma FESTIVAL_QA_MIN (30, src/config.js) a toda función con
            # conversatorio; la hora de fin del festival YA lo incluye
            f['duracion_min'] -= 30
            f['_duracion_de'] += ', con el conversatorio dentro (−30 que la app vuelve a sumar)'
        funciones.append(f)
    conocidas = [o['duracion_min'] for f in funciones for o in f['obras'] if o.get('duracion_min')]
    prom = round(sum(conocidas) / len(conocidas))
    for f in funciones:
        faltan = [o for o in f['obras'] if not o.get('duracion_min')]
        if faltan and f['_duracion_de'].startswith('suma'):
            f['duracion_min'] += prom * len(faltan)
            f['_duracion_de'] = (f'ESTIMADA (Juan, 29 oct): {f["_duracion_de"]}; + {len(faltan)} × {prom} min, '
                                 f'promedio de las {len(conocidas)} obras con duración')
    fuera = [o['titulo'] for o in cat if o['titulo'] not in usadas]
    n = sum(len(f['obras']) for f in funciones)
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('Calendario de programación IV FICIDI 2026 (PDF enviado por el festival)',
                                  archivo=f'fuentes/{FID}/{os.path.basename(PDF)}',
                                  metodo='pdftotext -layout; un bloque por función; obras cruzadas con el catálogo'),
        '_catalogo_sin_funcion': fuera, '_avisos': avisos, 'funciones': funciones},
        ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones · {n} obras · {len(fuera)} del catálogo sin función → '
          f'{os.path.relpath(DESTINO, REPO)}')
    for f in funciones:
        print(f'   {f["dia"]} {f["hora"]} {f["sede"][:34]:34} {f["titulo"][:32]:32} {len(f["obras"]):2} obras '
              f'{f["duracion_min"]:4} min · {f["_duracion_de"][:110]}')
    for x in fuera:
        print('   sin función ·', x)
    for a in avisos:
        print('   aviso ·', a)


if __name__ == '__main__':
    main()
