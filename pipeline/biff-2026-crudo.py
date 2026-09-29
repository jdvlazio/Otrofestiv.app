#!/usr/bin/env python3
"""biff-2026-crudo.py — la programación del BIFF 12 → crudo.

CUATRO LECTURAS de la parrilla, todas del propio festival, y el crudo no sale
si no coinciden:
  1. las FICHAS del PDF (biff-2026-catalogo.py): cada película anota sus
     funciones con SEDE Y SALA ESCRITAS («Dom. 11 - 19:30 | Cinemateca - Sala
     Capital»). Es la fuente de la sede y la sala;
  2. la tabla «Programación por días» (biff-2026-pordias.py): día, hora y
     título de las 149 funciones de película —exacto contra las fichas— y las 4
     charlas abiertas que solo están allí;
  3. los ÍCONOS de esa tabla (biff-2026-iconos.py): equipo presente, solo con
     invitación, entrada libre;
  4. la agenda de la Cinemateca de Bogotá: 53 de sus 55 funciones coinciden en
     día, hora y sala, y trae el enlace de compra de cada una.
La grilla «por salas» desempata lo que la tabla deduce mal (la sala de las
charlas).

LO QUE NO SE INVENTA:
  · la entrada de los cine conciertos del Teatro Mayor y El Ensueño: ninguna
    fuente la dice → DESCONOCIDO;
  · la duración de las charlas: el hueco hasta la siguiente en su sala, con
    tope de 90 min.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import DESCONOCIDO, provenance  # noqa: E402

D = f'{REPO}/fuentes/biff-2026'
CATALOGO = f'{REPO}/festivals/staging/biff-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/biff-2026-crudo.json'
PDF_URL = 'https://biff.co/documentos/Programacion_BIFF_12_DIGITAL.pdf'
DURACION_POR_DEFECTO = 90

# ── LA SEDE Y LA SALA, de lo que escribe cada ficha ────────────────────────
SEDES = {
    'Cinemateca - Sala Capital': ('Cinemateca de Bogotá', 'Sala Capital'),
    'Cinemateca - Sala 1': ('Cinemateca de Bogotá', 'Sala 1'),
    'Cinemateca - Sala 2': ('Cinemateca de Bogotá', 'Sala 2'),
    'Cinemateca - Sala 3': ('Cinemateca de Bogotá', 'Sala 3'),
    'Cinemateca - Calle Museo': ('Cinemateca de Bogotá', 'Calle Museo'),
    'Av. Chile - Sala 1': ('Cine Colombia Multiplex Avenida Chile', 'Sala 1'),
    'Av. Chile - Sala 2': ('Cine Colombia Multiplex Avenida Chile', 'Sala 2'),
    'Av. Chile - Sala 3': ('Cine Colombia Multiplex Avenida Chile', 'Sala 3'),
    'Av. Chile - Sala 4': ('Cine Colombia Multiplex Avenida Chile', 'Sala 4'),
    'Teatro El Ensueño': ('Teatro El Ensueño', ''),
    'Teatro Mayor J. M. Santo Domingo': ('Teatro Mayor Julio Mario Santo Domingo', 'Teatro Estudio'),
    'Centro Felicidad Chapinero': ('Centro Felicidad Chapinero', 'Teatro'),
    'Artes U. Javeriana, Aula Múltiple': ('Pontificia Universidad Javeriana', 'Aula Múltiple'),
    'Parque Santander': ('Parque Santander', ''),
    'Plaza de Mercado La Concordia': ('Plaza Distrital de Mercado La Concordia', ''),
    'Plazoleta CityU': ('City U', 'Plazoleta principal'),
    'Aud. Fundadores U. Central': ('Universidad Central', 'Auditorio Fundadores'),
    'U. Tadeo, Aula Máxima': ('Universidad Jorge Tadeo Lozano', 'Aula Máxima'),
}
# La sala de las charlas, la que IMPRIMEN LAS DOS GRILLAS (por salas págs. 35–36,
# por días 46–50). Aquí decía Sala 2 para sábado y domingo con un comentario que
# atribuía eso a la grilla: la grilla, mirada, dice Sala 3 (triple lectura, 29 sep).
SALA_CHARLA = {'2026-10-10': 'Sala 3', '2026-10-11': 'Sala 3',
               '2026-10-12': 'Sala Capital', '2026-10-14': 'Sala Capital'}

# «BIFF Bang»: el PDF escribe BIFF BANG y la web «Biff Bang!»; BIFF es sigla
# (lib.SIGLAS) y Bang es palabra. La caja la decide Juan.
SECCION_CHARLA = 'Charlas abiertas BIFF Bang'
PROGRAMA = 'Muestra de cortometrajes BIFF Bang'

# ── LA DURACIÓN QUE EL FESTIVAL IMPRIME MAL, con su prueba ─────────────────
# «El deshielo» (Manuela Martelli): 88 min en el PDF, en la web y en la
# Cinemateca (que copia al festival); 108 en el Festival de Cannes (Un Certain
# Regard, su estreno), CineChile, TMDB 1210268 y Wikipedia. Con 88 la app no
# avisaría de choques en los últimos 20 minutos. Revisado a pedido de Juan
# (29 sep 2026): «las duraciones siempre hay que compararlas entre fuentes».
DURACION_ERRATA = {'El Deshielo': 108}

ACCESO_ICONO = {'libre': 'Entrada libre', 'invitacion': 'Ingreso únicamente con invitación'}
FUNCION = re.compile(r'^(Lun|Mar|Mié|Jue|Vie|Sáb|Dom)\. (\d{1,2}) - (\d{1,2}:\d{2}) \| (.+)$')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def main():
    cat = json.load(io.open(CATALOGO, encoding='utf-8'))
    tabla = json.load(io.open(f'{D}/por-dias-iconos.json', encoding='utf-8'))['funciones']
    icono = {(f['dia'], f['hora'].zfill(5), plano(f['titulo'])): f['icono'] for f in tabla}
    cin = {(c[0], c[1], c[2]): c for c in json.load(io.open(f'{D}/cinemateca/funciones.json', encoding='utf-8'))}
    web = {plano(w['titulo_web']): w for w in json.load(io.open(f'{D}/web.json', encoding='utf-8'))['fichas']}

    funciones, fallos, usados = [], [], set()

    def base(dia, hora, sede_ficha, titulo_pdf):
        if sede_ficha not in SEDES:
            fallos.append(f'sede sin entrada en la tabla: {sede_ficha!r}')
            return None
        sede, sala = SEDES[sede_ficha]
        k = (dia, hora, plano(titulo_pdf))
        if k not in icono:
            fallos.append(f'{dia} {hora} «{titulo_pdf}»: está en su ficha y NO en la tabla por días')
            return None
        usados.add(k)
        r = {'dia': dia, 'hora': hora, 'sede': sede,
             '_src': {'url': PDF_URL, 'date': '2026-09-26'}}
        if sala:
            r['sala'] = sala
        ics = (icono[k] or '').split('+')     # una celda puede traer dos íconos
        if 'equipo' in ics:
            r['has_qa'], r['qa_type'] = True, 'team'
        for ic in ics:
            if ic in ACCESO_ICONO:
                r['acceso'] = ACCESO_ICONO[ic]
        return r, k

    for o in cat['obras']:
        if o.get('programa'):
            continue
        w = web.get(plano(o['titulo_pdf']), {})
        for f in o['funciones_ficha']:
            m = FUNCION.match(f)
            dia, hora = f'2026-10-{int(m.group(2)):02d}', m.group(3).zfill(5)
            b = base(dia, hora, m.group(4), o['titulo_pdf'])
            if not b:
                continue
            r, k = b
            r.update({'titulo': o['titulo'], 'seccion': o['seccion'], 'director': o['director'],
                      'pais': o.get('pais'), 'anio': o.get('anio'),
                      'duracion_min': DURACION_ERRATA.get(o['titulo'], o.get('duracion_min')),
                      # UN género ([genero-unico]): el primero de la ficha
                      'genero': re.split(r'\s*[,|]\s*', o.get('genero') or '')[0] or None,
                      'idioma': o.get('idioma'), 'sinopsis': o.get('sinopsis')})
            if o['titulo'] in DURACION_ERRATA:
                r['_duracion_fuente'] = o.get('duracion_min')
            if o['titulo'] == 'Fjord' and dia == '2026-10-08':
                r['premiere'] = 'Inauguración'      # «Inauguración + FJORD» en la grilla
            # LA CLAUSURA: la Presentación del PDF (pág. 4) dice que «el cierre del
            # BIFF tendrá como protagonista a COBARDE»; ninguna función lo rotula.
            # De sus tres, la del último día en la sala de la inauguración (Sala
            # Capital) y en horario de gala; las otras dos son en Cine Colombia,
            # sáb y dom. Decisión de Juan (29 sep); la web no nombra clausura.
            if o['titulo'] == 'Cobarde' and (dia, hora) == ('2026-10-14', '19:30'):
                r['premiere'] = 'Clausura'
            if 'acceso' not in r:
                c = cin.get(k[:2] + (plano(o['titulo']),))
                if r['sede'] == 'Cinemateca de Bogotá' and c and c[5]:
                    r['acceso'], r['ticket_url'] = 'Con boleta', c[5]
                elif r['sede'].startswith('Cine Colombia') and w.get('cinecolombia'):
                    r['acceso'], r['ticket_url'] = 'Con boleta', w['cinecolombia']
                elif r['sede'] == 'Cinemateca de Bogotá' and w.get('tuboleta'):
                    r['acceso'], r['ticket_url'] = 'Con boleta', w['tuboleta']
                else:
                    r['acceso'] = DESCONOCIDO
            funciones.append({k2: v for k2, v in r.items() if v not in (None, '')})

    # el PROGRAMA de cortos: 8 obras, 7 funciones, todas de entrada libre
    prog = cat['programas'][PROGRAMA]
    obras_p = [o for o in cat['obras'] if o.get('programa') == PROGRAMA]
    for f in prog['funciones_ficha']:
        m = FUNCION.match(f)
        dia, hora = f'2026-10-{int(m.group(2)):02d}', m.group(3).zfill(5)
        b = base(dia, hora, m.group(4), PROGRAMA)
        if not b:
            continue
        r, _ = b
        r.update({'titulo': PROGRAMA, 'seccion': PROGRAMA, 'acceso': 'Entrada libre',
                  'duracion_min': sum(o['duracion_min'] for o in obras_p),
                  'obras': [{'titulo': o['titulo'], 'director': o['director'], 'pais': o.get('pais'),
                             'anio': o.get('anio'), 'duracion_min': o.get('duracion_min'),
                             'genero': re.split(r'\s*[,|]\s*', o.get('genero') or '')[0] or None}
                            for o in obras_p]})
        funciones.append(r)

    # las CHARLAS: solo en la tabla por días
    for f in tabla:
        if 'CHARLA ABIERTA' not in f['titulo'].upper():
            continue
        k = (f['dia'], f['hora'].zfill(5), plano(f['titulo']))
        usados.add(k)
        tit = re.sub(r'^BIFF BANG CHARLA ABIERTA:\s*', '', f['titulo'], flags=re.I).strip()
        funciones.append({'titulo': tit[:1] + tit[1:].lower(), 'titulo_pdf': f['titulo'],
                          'dia': f['dia'], 'hora': f['hora'].zfill(5), 'sede': 'Cinemateca de Bogotá',
                          'sala': SALA_CHARLA[f['dia']], 'tipo': 'evento', 'event_kind': 'charla',
                          'seccion': SECCION_CHARLA,
                          'acceso': next((ACCESO_ICONO[i] for i in (f['icono'] or '').split('+') if i in ACCESO_ICONO), DESCONOCIDO),
                          '_src': {'url': PDF_URL, 'date': '2026-09-26'}})

    # COBERTURA INVERSA: toda fila de la tabla por días quedó en el crudo
    for k in icono:
        if k not in usados:
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: está en la tabla por días y en NINGUNA ficha')
    if fallos:
        sys.exit('✗ las lecturas no coinciden:\n  · ' + '\n  · '.join(fallos))

    # duración de las charlas: el hueco hasta la siguiente en su sala, con tope
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones if g['dia'] == f['dia'] and g['sede'] == f['sede']
                     and g.get('sala') == f.get('sala') and mins(g['hora']) > mins(f['hora']))
        hueco = sig[0] - mins(f['hora']) if sig else None
        f['duracion_min'] = hueco if hueco and hueco <= DURACION_POR_DEFECTO else DURACION_POR_DEFECTO
        f['_duracion_de'] = ('el hueco hasta la siguiente en su sala' if hueco and hueco <= DURACION_POR_DEFECTO
                             else f'{DURACION_POR_DEFECTO} min declarados: la fuente no la da')

    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f.get('sala', '')))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'PDF oficial del BIFF 12 + agenda de la Cinemateca de Bogotá + biff.co',
            que_aporta='la programación entera: día, hora, sede, sala, acceso y enlaces de compra',
            url=PDF_URL,
            metodo='las fichas (sede y sala escritas) cruzadas contra la tabla por días en los dos '
                   'sentidos; íconos por píxeles; Cinemateca y web para las boletas'),
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    from collections import Counter
    print(f'✓ {len(funciones)} funciones · {len({f["sede"] for f in funciones})} sedes · '
          f'acceso: {dict(Counter(f["acceso"] for f in funciones))} → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
