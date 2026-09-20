#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-fichas-tmdb.py — lo que TMDB sepa de estos 46 cortos.

POR QUÉ NO BASTA `enriquecer.py`. Su candado exige director ✓ **y además** año
±1 o duración ±3. El PDF de CONEXCINE no publica NI año NI duración de ningún
corto —solo título y departamento—, así que ese candado no puede abrirse
nunca, por buena que sea la coincidencia: el paso genérico devolvía «0
verificadas» con 34 obras esperando en TMDB.

EL CANDADO QUE SÍ CORRESPONDE ya existe en `lib.ficha_tmdb` y es el que usan
FICMA y Villa del Cine: cuando no hay año ni duración con qué contrastar,
decide el TÍTULO IDÉNTICO más el DIRECTOR. El director se verifica SIEMPRE.

NO ES UN LISTÓN MÁS BAJO, ES OTRO LISTÓN, y hace falta. Medido sobre estas 38
obras: cuatro tienen en TMDB una película con el MISMO TÍTULO y otro director.
Dos de ellas son obras distintas —«La Esperanza» es un largo argentino de 2005
de Francisco D'Intino, «Reflejos» es un corto de 2025 de Regina Romero
Capetillo—, y sin comprobar el director les habríamos pegado una ficha ajena,
que es peor que dejarlas sin ficha.

Los otros dos son la MISMA PERSONA con el nombre escrito de otra forma, y por
eso van declarados uno por uno en NOMBRE_MISMO: el festival escribe un apellido
y TMDB el otro. Eso se mira, no se automatiza — una regla que acepte «un nombre
de pila en común» volvería a abrir la puerta a las dos ajenas.

RE-CORRIBLE SIN VOLVER A PAGARLO. Lo sondeado se guarda en el propio archivo de
salida y se reutiliza por TÍTULO + DIRECTOR. Los aciertos no caducan —un
tmdb_id es el que es—; los fallos caducan a los 7 días, porque TMDB gana fichas
y una caché que recuerde «no está» para siempre deja de verificar.
`--refrescar` la ignora.

Lee   festivals/staging/conexcine-2026-catalogo.json  (título + departamento)
      festivals/staging/conexcine-2026-ig.json        (el DIRECTOR, de las láminas)
Esc.  festivals/staging/conexcine-2026-fichas-tmdb.json
      assets/conexcine-2026/<slug>.jpg                (póster w780)

Requiere TMDB_API_KEY en el entorno.
"""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import UA, banderas, ficha_tmdb, norm, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/conexcine-2026'
CAT = f'{ST}/conexcine-2026-catalogo.json'
IG = f'{ST}/conexcine-2026-ig.json'
OUT = f'{ST}/conexcine-2026-fichas-tmdb.json'

DIAS_NEGATIVO = 7

# EL MISMO NOMBRE, ESCRITO DE OTRA FORMA. Mirado uno por uno: no es una regla.
NOMBRE_MISMO = {
    'Promesa': ('Yosman S. Lindarte',
                'el festival lo acredita «Yosman Serrano» y TMDB «Yosman S. '
                'Lindarte»: apellidos compuestos, cada fuente usó uno. Mismo '
                'corto (2026, Norte de Santander, Competencia En(Foco))'),
    'Kuagro': ('Diego Casseres',
               'el festival escribe «Diego Caceres» y TMDB «Diego Casseres»: '
               'la misma persona con una ese de más. Mismo corto (2026, Bolívar)'),
}

# MISMO TÍTULO, OTRA OBRA. Se declaran para que nadie las tome más adelante
# creyendo que el candado se quedó corto.
NO_ES_LA_MISMA = {
    'La Esperanza': 'TMDB 929545 es un largometraje argentino de 2005 de '
                    'Francisco D\'Intino. El nuestro es un corto de Andrés '
                    'Flechas, Norte de Santander',
    'Reflejos': 'TMDB 1552805 es un corto de 2025 de Regina Romero Capetillo. '
                'El nuestro es de María Nicol Contreras Barbosa, Tolima',
}


def _hoy():
    return datetime.date.today().isoformat()


def _vigente(fecha, dias):
    try:
        d = datetime.date.fromisoformat(fecha)
    except (TypeError, ValueError):
        return False
    return (datetime.date.today() - d).days < dias


def lb_slug(tmdb_id):
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'], capture_output=True)
    s = r.stdout.decode().strip()
    return s.rsplit('/film/', 1)[-1].strip('/') if '/film/' in s else ''


def baja_poster(poster_path, titulo):
    os.makedirs(ASSETS, exist_ok=True)
    dest = f'{ASSETS}/{slug(titulo)}.jpg'
    if not os.path.exists(dest) or os.path.getsize(dest) < 5000:
        for intento in range(4):
            try:
                req = urllib.request.Request(
                    f'https://image.tmdb.org/t/p/w780{poster_path}',
                    headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    datos = r.read()
                if len(datos) < 5000:
                    raise OSError(f'{len(datos)} bytes: truncado')
                open(dest, 'wb').write(datos)
                break
            except Exception as e:
                if intento == 3:
                    print(f'    ⚠ sin póster para «{titulo}»: {e}', flush=True)
                    return ''
                time.sleep(2 * (intento + 1))
    return f'/assets/conexcine-2026/{os.path.basename(dest)}'


def cache_previa(refrescar):
    if refrescar or not os.path.exists(OUT):
        return {}, {}
    d = json.load(open(OUT, encoding='utf-8'))
    ok = {t: e for t, e in d.get('fichas', {}).items() if e.get('_director')}
    no = {x['titulo']: x for x in d.get('sin_ficha', [])
          if x.get('_sondeado') and _vigente(x['_sondeado'], DIAS_NEGATIVO)}
    return ok, no


def main():
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')
    refrescar = '--refrescar' in sys.argv
    cat = json.load(open(CAT, encoding='utf-8'))['obras']
    ig = json.load(open(IG, encoding='utf-8'))['obras'] if os.path.exists(IG) else []
    dires = {norm(o['titulo']): o['director'] for o in ig if o.get('director')}
    prev_ok, prev_no = cache_previa(refrescar)

    fichas, sin, reusadas, ajenas = {}, [], 0, []
    obras = [o for o in cat if not o.get('virtual')]
    for i, o in enumerate(obras, 1):
        t = o['titulo']
        director = NOMBRE_MISMO.get(t, (dires.get(norm(t), ''),))[0] or dires.get(norm(t), '')
        if t in NO_ES_LA_MISMA:
            ajenas.append((t, NO_ES_LA_MISMA[t]))
            sin.append({'titulo': t, 'director': dires.get(norm(t), ''),
                        '_por_que': NO_ES_LA_MISMA[t], '_sondeado': _hoy()})
            print(f'[{i:2}/{len(obras)}] ✗   {t[:40]:42} mismo título, OTRA obra', flush=True)
            continue

        c = prev_ok.get(t)
        if c and c['_director'] == director and (
                not c.get('poster') or os.path.exists(f'{REPO}{c["poster"]}')):
            fichas[t] = c
            reusadas += 1
            print(f'[{i:2}/{len(obras)}] ··  {t[:40]:42} tmdb {c["tmdb_id"]} '
                  f'(de la corrida del {c["_sondeado"]})', flush=True)
            continue
        c = prev_no.get(t)
        if c and c.get('director') == director:
            sin.append(c)
            reusadas += 1
            print(f'[{i:2}/{len(obras)}] ··  {t[:40]:42} sin ficha el {c["_sondeado"]}',
                  flush=True)
            continue

        if not director:
            sin.append({'titulo': t, 'director': '',
                        '_por_que': 'sin director: el candado exige uno SIEMPRE',
                        '_sondeado': _hoy()})
            print(f'[{i:2}/{len(obras)}] —   {t[:40]:42} sin director', flush=True)
            continue

        r = ficha_tmdb({'titulo': t, 'director': director}, key)
        time.sleep(0.2)
        if not r:
            sin.append({'titulo': t, 'director': director, '_sondeado': _hoy()})
            print(f'[{i:2}/{len(obras)}] —   {t[:40]:42} {director[:22]}', flush=True)
            continue
        det, det_en, como = r
        e = {'tmdb_id': det['id'], '_verificado': como,
             '_director': director, '_sondeado': _hoy()}
        if t in NOMBRE_MISMO:
            e['_nombre_declarado'] = NOMBRE_MISMO[t][1]
        anio = int((det.get('release_date') or '0')[:4] or 0)
        if anio:
            e['anio'] = anio
        if det.get('runtime'):
            e['duracion_min'] = det['runtime']
        if det.get('genres'):
            e['genero'] = det['genres'][0]['name']
        if det.get('overview'):
            e['sinopsis'] = det['overview']
        if det_en.get('overview'):
            e['sinopsis_en'] = det_en['overview']
        en = det_en.get('title') or ''
        if en and norm(en) != norm(t):
            e['title_en'] = en
        paises = [p.get('name', '') for p in (det.get('production_countries') or [])]
        if paises:
            e['pais'] = paises[0]
            e['flags'] = banderas(paises[0])
        if det.get('poster_path'):
            ruta = baja_poster(det['poster_path'], t)
            if ruta:
                e['poster'], e['posterSource'] = ruta, 'tmdb'
        sl = lb_slug(det['id'])
        if sl:
            e['lbSlug'] = sl
        fichas[t] = e
        print(f'[{i:2}/{len(obras)}] OK  {t[:40]:42} tmdb {det["id"]}'
              f'{"  póster✓" if e.get("poster") else ""}'
              f'{"  lb✓" if e.get("lbSlug") else ""}', flush=True)

    json.dump({'_provenance': provenance(
        'TMDB (api.themoviedb.org) + Letterboxd por el redirect /tmdb/<id>',
        que_aporta='año, duración, país, género, sinopsis, póster y lbSlug de los '
                   'cortos de CONEXCINE que TMDB tiene',
        candado='lib.ficha_tmdb — el PDF no publica año ni duración de ningún '
                'corto, así que decide TÍTULO IDÉNTICO + DIRECTOR. El director '
                'se verifica siempre: cuatro obras tienen en TMDB una película '
                'del mismo título con otro director',
        alcance=f'{len(fichas)} de {len(obras)} cortos con ficha'),
        'fichas': fichas, 'sin_ficha': sin,
        'mismo_titulo_otra_obra': dict(ajenas),
        'nombre_declarado': {k: v[1] for k, v in NOMBRE_MISMO.items()}},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n{len(fichas)} con ficha ({sum(1 for e in fichas.values() if e.get("poster"))} '
          f'con póster) · {len(sin)} sin ficha · {reusadas} de la caché'
          f'{" (--refrescar)" if refrescar else ""}')
    if ajenas:
        print(f'\n{len(ajenas)} con el MISMO TÍTULO y otra obra detrás, declaradas:')
        for t, p in ajenas:
            print(f'   ✗ «{t}» — {p}')


if __name__ == '__main__':
    main()
