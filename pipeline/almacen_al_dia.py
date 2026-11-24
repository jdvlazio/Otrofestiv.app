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
Se decide de nuevo, con el índice fresco, justo antes de publicar cada uno.

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
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICO = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/'
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


def _bajar(u):
    with urllib.request.urlopen(u, timeout=60) as r:
        return r.read()


def indice():
    d = json.loads(_bajar(PUBLICO + f'indice.json?m={int(time.time())}'))['festivales']
    if not d:
        raise RuntimeError('el índice del almacén llegó vacío')
    return d


def estado(f, e):
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
    return decidir(dif, tocado(ruta) if dif else 0, fdif, tf, pub)


def main():
    lista, mal = [], []
    for f, e in sorted(indice().items()):
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
    print(f'A publicar ({len(lista)}): {" ".join(lista) or "nada"}')
    if '--probar' in sys.argv:
        return
    fin = time.time() + ESPERA

    def publicar(f, vuelta):
        try:
            if estado(f, indice()[f]) != 'publicar':   # alguien lo publicó mientras tanto
                print(f'· {f}: ya no hace falta')
                return True
        except Exception as x:
            print(f'· {f}: no pude compararlo ({x})')
            return False
        env = {**os.environ, 'OTF_ESPERA_AFICHES': str(max(0, int(fin - time.time())) if vuelta == 1 else 0)}
        return subprocess.run([sys.executable, 'pipeline/publicar-datos.py', f, '--desde-main'], cwd=REPO, env=env).returncode == 0

    mal += publicar_todos(lista, publicar)
    if mal:
        sys.exit(f'✗ sin publicar: {" ".join(mal)} — la próxima corrida los retoma')


if __name__ == '__main__':
    main()
