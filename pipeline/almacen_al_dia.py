#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""almacen_al_dia.py — deja el almacén al día con main (lo corre el job «Datos al almacén»).

POR QUÉ (24 nov 2026, revisión senior): el job publicaba «lo que cambió en ESTE
push». Un fallo cortaba la tanda y lo que faltaba no lo recogía nadie; un push
reemplazado en la cola se perdía; repetir un run viejo publicaba datos viejos.

LA REGLA, para cada festival del almacén: si su JSON (o su ficha) no es el de main
Y main lo tocó DESPUÉS de lo publicado, se publica. Lo publicado después gana
siempre: es una publicación a mano desde una rama, o una vuelta atrás. No importa
qué push disparó el job: lo que falló o se perdió lo retoma la corrida siguiente.
Eso vale solo si publicó una PERSONA: lo que puso este mismo job (autor
«github-actions» en la rama `datos`) cede siempre ante main — si no, un job lento
que publica v1 después del merge de v2 dejaría v1 para siempre.
Límite conocido: la ficha se fecha por el último cambio de TODO src/config.js.
Se decide de nuevo, con el índice fresco, justo antes de publicar cada uno.

EL ALTA (25 nov 2026, BOGOSHORTS quedó en la web y no en el almacén hasta un comando aparte):
un festival de main que NO está en el almacén, VISIBLE en la config (group distinto de
'test') y sin terminar, entra solo, con su ficha. El acto a propósito es el merge que lo hace
visible; sus controles de primera publicación (sello_funcion.control) frenan igual aquí.
Más de ALTAS_JUNTAS a la vez no es un alta: es un índice a medias o un error, y no
entra ninguno (Juan, 18 oct: nunca de golpe). Uno oculto o terminado entra a mano.
Para RETIRAR uno del almacén, primero se oculta (group 'test'): si no, vuelve solo.

Un festival que falla no detiene a los demás; se reintenta al final y, si sigue
fallando, el job termina en rojo diciendo cuáles.

    python3 pipeline/almacen_al_dia.py [--probar]
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICO = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/'
ALTAS_JUNTAS = 2
ESPERA = 600      # s para TODA la corrida, a que el deploy suba los afiches


def decidir(json_difiere, t_json, ficha_difiere, t_ficha, publicado):
    """'igual' | 'publicar' | 'adelante'. Tiempos en segundos."""
    if json_difiere:
        return 'publicar' if t_json > publicado else 'adelante'   # adelante: tampoco su ficha (viajan juntos)
    if ficha_difiere:
        return 'publicar' if t_ficha > publicado else 'adelante'
    return 'igual'


def ficha_difiere(local, indice, sha_keyart):
    """La ficha de main contra la del índice; el keyArt, por huella (el índice guarda la URL)."""
    if not indice:
        return False                      # una ficha entra de a una y a propósito
    l, i = dict(local), dict(indice)
    kl, ki = l.pop('keyArt', '') or '', i.pop('keyArt', '') or ''
    if l != i:
        return True
    m = re.search(r'/keyart/([0-9a-f]{12})\.', ki)
    return (m.group(1) if m else ki) != (sha_keyart or kl)


def publicar_todos(lista, publicar, pausa=60, dormir=time.sleep):
    """publicar(f, vuelta) → bool. Los que fallan se repiten una vez al final → los que quedan mal."""
    mal = [f for f in lista if not publicar(f, 1)]
    if mal:
        print(f'· {len(mal)} fallaron; espero {pausa} s y los repito: {" ".join(mal)}')
        dormir(pausa)
        mal = [f for f in mal if not publicar(f, 2)]
    return mal


def tocado(*rutas):
    """Cuándo entró a main el último cambio de esas rutas (segundos)."""
    r = subprocess.run(['git', '-C', REPO, 'log', '-1', '--first-parent', '--format=%ct', 'HEAD', '--', *rutas],
                       check=True, capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def traer_datos():
    subprocess.run(['git', '-C', REPO, 'fetch', '-q', 'origin', '+refs/heads/datos:refs/remotes/origin/datos'], check=True, timeout=120)


def lo_puso_el_job(commit, *rutas):
    """¿El último que cambió esas rutas en `datos`, hasta ese commit, fue este job?"""
    r = subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%an', commit, '--', *rutas], check=True, capture_output=True, text=True)
    return r.stdout.strip() == 'github-actions'


def _bajar(u):
    with urllib.request.urlopen(u, timeout=60) as r:
        return r.read()


def indice():
    d = json.loads(_bajar(PUBLICO + f'indice.json?m={int(time.time())}'))['festivales']
    if not d:
        raise RuntimeError('el índice del almacén llegó vacío')
    return d


def config():
    """{id de archivo: (grupo, fin)} de FESTIVAL_CONFIG."""
    js = ("const m=await import(process.argv[1]);const o={};for(const[k,c]of Object.entries(m.FESTIVAL_CONFIG))"
          "o[k]=[c.group||'',c.festivalEndStr||''];process.stdout.write(JSON.stringify(o))")
    r = subprocess.run(['node', '--input-type=module', '-e', js, os.path.join(REPO, 'src', 'config.js')],
                       capture_output=True, text=True, check=True, timeout=60)
    return {re.sub(r'-?(\d+)$', r'-\1', k): tuple(v) for k, v in json.loads(r.stdout).items()}


def altas(conf, en_almacen, existe, hoy):
    """Los festivales que entran solos."""
    return sorted(f for f, (grupo, fin) in conf.items()
                  if f not in en_almacen and grupo != 'test' and fin[:10] >= hoy and existe(f))


def hoy_colombia():
    return datetime.fromtimestamp(time.time() - 5 * 3600, timezone.utc).strftime('%Y-%m-%d')


def estado(f, e):
    if e is None:
        return 'publicar'                 # alta: no está en el almacén
    ruta = f'festivals/{f}.json'
    p = os.path.join(REPO, ruta)
    if not os.path.exists(p):
        return 'adelante'                 # publicado desde una rama que main aún no tiene
    dif = hashlib.sha256(open(p, 'rb').read()).hexdigest() != e['sha256']
    fdif, tf = False, 0
    if e.get('ficha'):
        r = subprocess.run(['node', 'scripts/ficha-de.mjs', re.sub(r'-(\d+)$', r'\1', f)], cwd=REPO, capture_output=True, text=True)
        local = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
        k = (local.get('keyArt') or '').lstrip('/')
        kp = os.path.join(REPO, k)
        sha = hashlib.sha256(open(kp, 'rb').read()).hexdigest()[:12] if k and os.path.isfile(kp) else ''
        if local and ficha_difiere(local, e['ficha'], sha):
            fdif, tf = True, tocado('src/config.js', *([k] if sha else []))
    pub = datetime.fromisoformat(e['publicado'].replace('Z', '+00:00')).timestamp()
    if dif or fdif:
        if lo_puso_el_job(e['commit'], *([ruta] if dif else [f'fichas/{f}.json', *([k] if sha else [])])):
            pub = 0
    return decidir(dif, tocado(ruta) if dif else 0, fdif, tf, pub)


def main():
    traer_datos()
    lista, mal = [], []
    ix = indice()
    try:
        nuevos = altas(config(), ix, lambda f: os.path.exists(os.path.join(REPO, f'festivals/{f}.json')), hoy_colombia())
    except Exception as x:
        print(f'· no pude ver si falta algún alta ({x})')
        nuevos, mal = [], ['(altas)']
    if len(nuevos) > ALTAS_JUNTAS:
        print(f'· {len(nuevos)} festivales fuera del almacén a la vez: no entra ninguno solo: {" ".join(nuevos)}')
        mal += nuevos
        nuevos = []
    for f in nuevos:
        print(f'· ALTA: {f} no está en el almacén')
    for f, e in sorted(ix.items()):
        try:
            d = estado(f, e)
        except Exception as x:
            print(f'· {f}: no pude compararlo ({x})')
            mal.append(f)
            continue
        if d == 'adelante':
            print(f'· {f}: lo publicado es posterior a main: no se toca')
        elif d == 'publicar':
            lista.append(f)
    lista += nuevos
    print(f'A publicar ({len(lista)}): {" ".join(lista) or "nada"}')
    if '--probar' in sys.argv:
        return
    fin = time.time() + ESPERA

    def publicar(f, vuelta):
        try:
            traer_datos()
            e = indice()
            if estado(f, e.get(f) if f in nuevos else e[f]) != 'publicar':   # alguien lo publicó mientras tanto
                print(f'· {f}: ya no hace falta')
                return True
        except Exception as x:
            print(f'· {f}: no pude compararlo ({x})')
            return False
        env = {**os.environ, 'OTF_ESPERA_AFICHES': str(max(0, int(fin - time.time())) if vuelta == 1 else 0)}
        return subprocess.run([sys.executable, 'pipeline/publicar-datos.py', f, '--desde-main',
                               *(['--alta'] if f not in e else [])], cwd=REPO, env=env).returncode == 0

    mal += publicar_todos(lista, publicar)
    if mal:
        sys.exit(f'✗ sin publicar: {" ".join(mal)} — la próxima corrida los retoma')


if __name__ == '__main__':
    main()
