# -*- coding: utf-8 -*-
"""Fichas de la Cinemateca de Bogotá → crudo de #NarrarElFuturo.

Mismo camino que abrió CineAutopsia: la agenda de la Cinemateca publica lo que
el festival NO publica en su web —obras de cada programa, sede, sala, día y
hora—. Acá resuelve además un problema que el festival solo cuenta en Instagram.

LO QUE HACE ÚTIL A ESTA FUENTE, y que el listado no enseña: **la ficha nombra
al festival**. La línea siguiente a «Festivales y Muestras» dice
«#NarrarElFuturo: Festival de Cine & Nuevos Medios». Sin eso la agenda sería
inservible para esto: en la misma semana y las mismas salas conviven CICLA,
QAFF-Bogotá y los ciclos propios de la Cinemateca, y el listado los mezcla.

CÓMO SE ENCONTRARON LOS NODOS (15 sep 2026): la agenda acepta un rango de
fechas por query (`field_date_interval_value[min|max][date]`) y se recorre por
SEDE —/agenda/11 Centro, /12 El Tunal, /80 Fontanar del Río, /112 CEFE
Chapinero—. En la ventana 15–20 SEP dio 46 nodos, de los que 8 son del
festival. No se adivinó ninguno: se leyó la ficha de los 46.

EL PARÁMETRO `?sede=` NO ES DECORATIVO. La misma ficha servida sin él viene sin
la línea de «Sede / Mes DD H:MM AM/PM»: el día y la hora desaparecen y el parser
devolvería funciones sin fecha. Se prueba sede por sede hasta que la línea
aparece, y se deja dicho cuál la dio.
"""
import io, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
SALIDA = f'{ST}/narrarelfuturo-2026-crudo.json'

NODOS = ['3077', '3078', '3079', '3080', '3178', '3211', '2821', '2003']
SEDES = ['11', '80', '12', '112']          # Centro, Fontanar, El Tunal, CEFE
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
         'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
         'noviembre': 11, 'diciembre': 12}
RE_FECHA = re.compile(
    r'^([A-Za-zÁÉÍÓÚáéíóú]+)\s+(\d{1,2})\s+(\d{1,2}):(\d{2})\s*([AP])\.?M\.?$')


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' ').replace('&amp;', '&')
    return [x.strip() for x in t.split('\n') if x.strip()]


def bajar(n, sede):
    p = f'{CACHE}/nef-{n}-s{sede}.html'
    if os.path.exists(p) and os.path.getsize(p) > 20000:
        return io.open(p, encoding='utf-8', errors='replace').read()
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA,
                    f'https://cinematecadebogota.gov.co/node/peliculas/{n}?sede={sede}',
                    '-o', p], check=True)
    time.sleep(0.5)
    return io.open(p, encoding='utf-8', errors='replace').read()


def parse(n, h, sede):
    L = texto(h)
    d = {'_nodo': n, '_sede_param': sede,
         '_src': f'https://cinematecadebogota.gov.co/node/peliculas/{n}?sede={sede}'}
    d['titulo'] = re.sub(r'\s*\|\s*Cinemateca\s*$', '', L[0])
    for i, x in enumerate(L):
        if x == 'Festivales y Muestras' and i + 1 < len(L):
            d['_festival'] = L[i + 1]
            break
    for x in L:
        if re.fullmatch(r'(19|20)\d\d', x):
            d.setdefault('anio', int(x))
        elif re.fullmatch(r'\d+\s*min\.?', x):
            d.setdefault('duracion_min', int(re.search(r'\d+', x).group()))
    for k, et in (('clasificacion', 'Clasificación:'), ('idioma', 'Idioma:'),
                  ('subtitulos', 'Subtítulos:'), ('formato', 'Formato:')):
        if et in L:
            d[k] = L[L.index(et) + 1]
    # OBRAS: título y, debajo, «(Dir. Nombre, año) País. NN min.»
    obras = []
    for i, x in enumerate(L[:-1]):
        m = re.match(r'^\(Dir\.\s*(.+?),\s*((?:19|20)\d\d)\)\s*(.*?)\.\s*(\d+)\s*min', L[i + 1])
        if m and len(x) < 90 and not x.endswith(':'):
            obras.append({'titulo': x, 'director': m.group(1).strip(),
                          'anio': int(m.group(2)), 'pais': m.group(3).strip(),
                          'duracion_min': int(m.group(4))})
    if obras:
        d['obras'] = obras
    for i, x in enumerate(L):
        m = RE_FECHA.match(x)
        if m:
            mes = MESES.get(m.group(1).lower())
            hh = int(m.group(3)) % 12 + (12 if m.group(5).upper() == 'P' else 0)
            d['sede'] = L[i - 1] if i else ''
            d['dia'] = f'2026-{mes:02d}-{int(m.group(2)):02d}' if mes else None
            d['hora'] = f'{hh:02d}:{m.group(4)}'
            break
    largos = [x for x in L if len(x) > 110 and 'Dir.' not in x]
    if largos:
        d['sinopsis'] = largos[0]
    m = re.search(r'(?:src|data-src)="(/sites/default/files/\d{4}-\d{2}/[^"]+\.(?:png|jpg|jpeg|webp))"', h, re.I)
    if m:
        d['poster'] = 'https://cinematecadebogota.gov.co' + m.group(1)
    # LA CASILLA DE ACCESO no se deja en blanco (PROTOCOLO §2 paso 4). La ficha
    # de la Cinemateca dice «Entrada libre» cuando lo es y enlaza su taquilla
    # cuando se paga. Lo que no diga ninguna de las dos se declara DESCONOCIDO:
    # no saber es legítimo, no mirar no.
    m = re.search(r'href="(https://[^"]*(?:tuboleta|tickets)[^"]*)"', h, re.I)
    if m:
        d['ticket_url'] = m.group(1)
    d['acceso'] = ('Entrada libre' if re.search(r'Entrada libre', h, re.I)
                   else ('Boletería en taquilla' if d.get('ticket_url') else lib.DESCONOCIDO))
    return d


def main():
    nodos = sys.argv[1:] or NODOS
    out, sin_fecha = [], []
    for n in nodos:
        elegido = None
        for sede in SEDES:
            d = parse(n, bajar(n, sede), sede)
            if d.get('dia'):
                elegido = d
                break
            elegido = elegido or d
        if not elegido.get('dia'):
            sin_fecha.append(n)
        out.append(elegido)
    # Solo del festival: la agenda mezcla varios y la ficha es quien lo dice.
    ajenas = [d for d in out if 'NarrarElFuturo' not in (d.get('_festival') or '')]
    out = [d for d in out if 'NarrarElFuturo' in (d.get('_festival') or '')]

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'cinematecadebogota.gov.co/node/peliculas/<nodo>?sede=<id>',
        metodo='fichas server-rendered de la agenda de la Cinemateca, barridas por rango de fechas y por sede',
        nota='la ficha NOMBRA al festival; el listado no. En la misma semana y salas conviven CICLA, QAFF-Bogotá y los ciclos de la casa'),
        '_funciones': len(out),
        '_obras': sum(len(d.get('obras') or []) for d in out),
        'funciones': out},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {SALIDA}\n')
    for d in out:
        print(f"══ [{d['_nodo']}] {d['titulo']}")
        print(f"   {d.get('dia','?')} {d.get('hora','?')} · {d.get('sede','?')} · "
              f"{d.get('duracion_min','?')} min · acceso: {d.get('acceso')}")
        for o in (d.get('obras') or []):
            print(f"      {o['duracion_min']:3} min · {o['titulo'][:38]:40} {o['director'][:24]:26} {o['pais']}")
    print(f"\n── {len(out)} funciones · {sum(len(d.get('obras') or []) for d in out)} obras en programas")
    if ajenas:
        print(f'   descartadas por no ser del festival: {[d["_nodo"] for d in ajenas]}')
    if sin_fecha:
        print(f'   ⚠ SIN día/hora en ninguna sede: {sin_fecha} — mirar la ficha a mano')


if __name__ == '__main__':
    main()
