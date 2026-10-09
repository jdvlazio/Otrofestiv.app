#!/usr/bin/env python3
"""fantasmagoria-2026-base.py — la cartelera oficial del festival manda sobre la noticia.

POR QUÉ EXISTE (7 oct 2026). El crudo se armó el 1 oct con la noticia «Ya puedes
empezar a programarte…» (wp-json post 6481), que el festival no volvió a tocar
desde el 28 sep. Pero el festival hizo su propia cartelera web
(cartelerafantasmagoria.fan) y la alimenta desde una base que su equipo edita:
el 6 oct publicó la versión 2, con 94 funciones contra nuestras 85, ocho
cambios de hora o sede, dos funciones que se cruzaron de día (Critters y la de
X-Files) y diez actividades que no teníamos. Para ellos el festival es del 14
al 25 de octubre.

LA BASE DICE QUÉ, CUÁNDO Y DÓNDE; la noticia aporta lo que la base no trae
(sinopsis de la página de largometrajes, las obras de cada programa de
cortos, el tipo de actividad). Este paso corre DESPUÉS del crudo de la noticia
y lo rehace contra la base:

  · cada registro de la base se empareja con una función del crudo (título
    parecido + día + sede + hora). Si empareja, la función conserva su título
    publicado (la watchlist guarda por título) y toma de la base el día, la
    hora, la sede, la sala y el acceso;
  · lo que la base trae y el crudo no, entra con los datos de la base;
  · lo que el crudo tiene y la base ya no, SALE (y se lista);
  · cobertura inversa: todo registro de la base termina en una función.

LA LECTURA es la misma que hace el navegador de cualquier visitante: un GET
público, de solo lectura, a la función `programacion_publicada` de su
Supabase, con la clave publicable que la propia página expone. Se guarda por
versión en fuentes/ para que el paso se pueda re-correr sin red.

    python3 pipeline/fantasmagoria-2026-base.py           # usa la copia guardada
    python3 pipeline/fantasmagoria-2026-base.py --bajar   # baja la versión vigente
"""
import difflib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import DESCONOCIDO  # noqa: E402

_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/fantasmagoria-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)
plano = crudo.plano

DIR = f'{REPO}/fuentes/fantasmagoria-2026/cartelera'
ACTUAL = f'{DIR}/publicada.json'
ENDPOINT = 'https://wggmrznxnzyoufcnzdef.supabase.co/rest/v1/rpc/programacion_publicada'
CLAVE = 'sb_publishable_Rgz2FMkfOqpY-sYjT1YjAQ_5S-yTInx'   # publicable: la expone la página
URL = 'https://www.cartelerafantasmagoria.fan/'
DESTINO = crudo.DESTINO

# LA SEDE como la escribe la base → (sede del crudo, sala). La sede del crudo
# es la que tiene pin en -venues-geo.json.
SEDES = {
    'Cineprox Las Américas': 'Cineprox Las Américas',
    'Centro Colombo Americano': 'Centro Colombo Americano',
    'COMFAMA': 'Comfama San Ignacio',
    'Museo de Arte Moderno de Medellín (MAMM)': 'Museo de Arte Moderno de Medellín - MAMM',
    'Planetario de Medellín': 'Planetario de Medellín',
    'Librería Antimateria': 'Librería Antimateria',
    'Twitch · Sociedad Fantasmagoría': crudo.SEDE_EN_LINEA,
    'La Pascasia': 'La Pascasia',
    'Cámara de Comercio': 'Cámara de Comercio de Medellín',
    'Centro de Desarrollo Cultural de Moravia': 'Centro de Desarrollo Cultural de Moravia',
    'Universidad de Antioquia': 'Paraninfo Universidad de Antioquia',
    'Comfama Otraparte (Envigado)': 'Comfama Otraparte',
    'Universidad Nacional': 'Universidad Nacional',
    'Parque Biblioteca Belén': 'Parque Biblioteca Belén',
    'Estación Metrocable Andalucía': 'Estación Metrocable Andalucía',
    'Draco Hobby': 'Draco Hobby',
    # su tabla de sedes: «Plazoleta Nueva Villa de Aburrá, Carrera 80A # 32B-26»
    'La Villa': 'Nueva Villa de Aburrá',
    # el mismo punto: Google Maps lo llama «Silencio y Ruido» (ver -venues-geo)
    'Bar Silencio Ruido': 'Silencio',
    'Bar Silencio / Ruido': 'Silencio',     # así lo escribe la v5 (7 oct)
    'Parque de los Deseos': 'Parque de los Deseos',
    'Universidad Luis Amigó': 'Universidad Católica Luis Amigó',
    'La Comarca': 'La Comarca',
    # sedes nuevas de la versión 2, con pin a mano
    'Biblioteca Comfenalco Castilla': 'Biblioteca Comfenalco Castilla',
    'Casa Libre': 'Casa Libre',
    'Instituto Alexander von Humboldt': 'Instituto Cultural Alexander von Humboldt',
}
# la sala: la de la base, salvo las que no son una sala
SALA = {'Sala por confirmar': '', 'Transmisión en línea': '', 'San Ignacio': '',
        'Mediateca (San Ignacio)': 'Mediateca', 'Librerías y café (Laureles)': '',
        'Paraninfo UdeA': ''}   # repite la sede
# LA SECCIÓN de lo nuevo: la de la base, unificada con la que ya publicamos
# cuando es la misma con un apellido («… - Taller», «… - Contacto»)
SECCION = {'Muestra Fantasmagoritos - Taller': 'Muestra Fantasmagoritos',
           'Expediente Fantasmagoría - Contacto': 'Expediente Fantasmagoría',
           'Fiesta': 'Actividades'}   # la otra fiesta del festival ya va en Actividades
# el tipo de actividad, por la palabra del título (vocabulario que la app conoce)
KIND = [('taller', 'taller'), ('conversatorio', 'conversatorio'), ('charla', 'charla'),
        ('torneo', 'torneo'), ('fiesta', 'fiesta'), ('club de lectura', 'evento'),
        ('presentaci', 'encuentro'), ('premiaci', 'clausura'), ('lectura', 'evento')]


def bajar():
    r = subprocess.run(['curl', '-sS', '--max-time', '30', ENDPOINT, '-H', f'apikey: {CLAVE}'],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    if not isinstance(d, dict) or not d.get('funciones'):
        sys.exit(f'✗ la base no devolvió funciones: {r.stdout[:200]}')
    os.makedirs(DIR, exist_ok=True)
    for p in (ACTUAL, f'{DIR}/publicada-v{d["version"]}.json'):
        json.dump(d, io.open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return d


def parecido(a, b):
    a, b = plano(a), plano(b)
    if not a or not b:
        return 0
    if a in b or b in a:
        return 1
    wa, wb = set(a.split()), set(b.split())
    return max(difflib.SequenceMatcher(None, a, b).ratio(), len(wa & wb) / max(1, min(len(wa), len(wb))))


# LA DOBLE DE JAIRO PINILLA (Archivo Fantasmagoría, 22 oct) junta dos obras en un
# registro: se publican como programa, cada una con su ficha. Antes era UNA obra
# y ninguna de las dos se buscaba en TMDB (8 oct).
OBRAS_DOBLE = {
    '2026-10-22-17-00-kondor-el-mago-el-cigarro-mortal-de-jairo-pinilla': [
        {'titulo': 'Kondor, El Mago', 'director': 'Jairo Pinilla', 'pais': 'Colombia', 'anio': 1975},
        {'titulo': 'El Cigarro Mortal', 'director': 'Jairo Pinilla', 'pais': 'Colombia'}],
}


def acceso(r):
    """La entrada de la base, con las palabras que ya usa el crudo."""
    txt = ' '.join([r.get('entrada') or ''] + (r.get('notas') or []))
    return crudo.acceso(txt) if txt.strip() else DESCONOCIDO


def nueva(r):
    """Una función que la noticia no tenía, armada con lo que trae la base."""
    f = {'titulo': crudo.recta(r['titulo']).rstrip('.').strip(),
         'seccion': SECCION.get(crudo.seccion_publicada(r['seccion'] or ''),
                                crudo.seccion_publicada(r['seccion'] or '')),
         'director': r.get('direccion'), 'pais': ', '.join(r.get('paises') or []) or None,
         'anio': r.get('anio'), 'duracion_min': r.get('duracion')}
    t = plano(r['titulo'])
    if r['tipo'] in ('charla', 'encuentro'):
        f.update({'tipo': 'evento',
                  'event_kind': next((k for w, k in KIND if w in t), 'evento')})
    if r.get('extra'):
        f['invitados'] = r['extra'].rstrip('.') + '.'
    return f


def main():
    d = bajar() if '--bajar' in sys.argv else json.load(io.open(ACTUAL, encoding='utf-8'))
    base = d['funciones']
    cr = json.load(io.open(DESTINO, encoding='utf-8'))
    viejas = cr['funciones']
    fallos, usados, salida, nuevas, movidas = [], set(), [], [], []
    for r in sorted(base, key=lambda r: (r['fecha'], r['hora'])):
        if r['sede'] not in SEDES:
            fallos.append(f'{r["fecha"]} {r["hora"]}: sede sin entrada en la tabla: {r["sede"]!r}')
            continue
        sede = SEDES[r['sede']]
        sala = SALA.get(r.get('sala') or '', r.get('sala') or '')
        # el emparejamiento: título parecido, y lo demás desempata
        cands = [(parecido(r['titulo'], g['titulo'])
                  + (1 if g['dia'] == r['fecha'] else 0)
                  + (0.5 if g['hora'] == r['hora'] else 0)
                  + (0.5 if g['sede'] == sede else 0), i, g)
                 for i, g in enumerate(viejas)
                 # solo entre títulos parecidos: si no, una franja ocupada por
                 # otra actividad (Expediente, 17 a las 19:00) le gana a la
                 # misma obra en otro día (Critters, que pasó del 18 al 17)
                 if i not in usados and parecido(r['titulo'], g['titulo']) >= 0.5]
        best = max(cands, key=lambda c: c[0], default=None)
        if best and best[0] >= 1.6:
            usados.add(best[1])
            f = dict(best[2])
            antes = (f['dia'], f['hora'], f['sede'], f.get('sala', ''))
            if antes != (r['fecha'], r['hora'], sede, sala):
                movidas.append(f'{f["titulo"][:46]}: {" ".join(x for x in antes if x)} → '
                               f'{" ".join(x for x in (r["fecha"], r["hora"], sede, sala) if x)}')
        else:
            f = nueva(r)
            nuevas.append(f'{r["fecha"]} {r["hora"]} {f["titulo"][:60]}')
        f.update({'dia': r['fecha'], 'hora': r['hora'], 'sede': sede, 'acceso': acceso(r),
                  '_src': {'url': URL, 'date': d['creada'][:10], 'base_version': d['version'],
                           'id': r['id']}})
        f.pop('sala', None)
        if sala:
            f['sala'] = sala
        if r.get('virtual'):
            f.update({'online': True, 'stream_url': crudo.STREAM_URL, 'stream_platform': 'Twitch'})
        if r.get('invitados') or any('presencia' in n.lower() for n in r.get('notas') or []):
            f['has_qa'], f['qa_type'] = True, 'team'
        if r['id'] in OBRAS_DOBLE:
            f['obras'] = [dict(o) for o in OBRAS_DOBLE[r['id']]]
            f.pop('director', None)
        salida.append({k: v for k, v in f.items() if v not in (None, '')})
    fuera = [f'{g["dia"]} {g["hora"]} {g["titulo"][:60]}' for i, g in enumerate(viejas) if i not in usados]

    # duración de lo que no la trae (actividades nuevas): la regla del crudo
    for f in salida:
        # (también una función de cine sin duración en la base: la doble de
        # Jairo Pinilla, «Kondor, El Mago + El Cigarro Mortal», no la trae)
        if f.get('duracion_min'):
            continue
        ini = int(f['hora'][:2]) * 60 + int(f['hora'][3:])
        sig = sorted(int(g['hora'][:2]) * 60 + int(g['hora'][3:]) for g in salida
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and g.get('sala') == f.get('sala')
                     and g['hora'] > f['hora'])
        f['duracion_min'] = min(sig[0] - ini, 90) if sig else 60

    # COBERTURA INVERSA: un registro de la base = una función, sin perder ni sumar
    if len(salida) + len(fallos) != len(base):
        fallos.append(f'{len(base)} registros en la base y {len(salida)} funciones')
    ids = [f['_src']['id'] for f in salida]
    if len(set(ids)) != len(ids):
        fallos.append('dos funciones salieron del mismo registro de la base')
    if fallos:
        sys.exit('✗ la base no cuadra:\n  · ' + '\n  · '.join(fallos))
    salida.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    cr['funciones'] = salida
    cr['_base'] = {'url': URL, 'version': d['version'], 'creada': d['creada'],
                   'nuevas': nuevas, 'movidas': movidas, 'fuera_de_la_base': fuera}
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps(cr, ensure_ascii=False, indent=1))
    print(f'✓ base v{d["version"]} ({d["creada"][:16]}): {len(salida)} funciones · '
          f'{len(nuevas)} nuevas · {len(movidas)} cambiaron · {len(fuera)} salen → {os.path.relpath(DESTINO, REPO)}')
    for t, xs in (('nuevas', nuevas), ('cambiaron', movidas), ('salen', fuera)):
        for x in xs:
            print(f'   {t[:3]} · {x}')


if __name__ == '__main__':
    main()
