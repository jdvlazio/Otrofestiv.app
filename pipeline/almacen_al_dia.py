#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""almacen_al_dia.py — deja el almacén igual a main (lo corre el job «Datos al almacén»).

POR QUÉ (24 nov 2026, revisión senior): el job publicaba «lo que cambió en ESTE
push». Un fallo cortaba la tanda y lo que faltaba no lo recogía nadie; un push
cancelado por la cola se perdía; repetir un run viejo publicaba datos viejos.

Ahora compara la HUELLA de cada festival del almacén con la de main y publica los
que difieren, sea cual sea el push: si una corrida falla, la siguiente la completa.
Un festival que falla no detiene a los demás; se reintenta al final y, si sigue
fallando, el job termina en rojo diciendo cuáles.

EL ALMACÉN PUEDE IR ADELANTE de main: publicar-datos.py a mano publica desde una
rama antes del merge. Se distingue por historia: si lo que hay en el almacén es
una versión que main YA tuvo, está atrasado y se publica; si main nunca la tuvo,
está adelante y NO se toca, salvo que este push haya cambiado ese festival.

    python3 pipeline/almacen_al_dia.py --cambiados "fest-a fest-b" [--probar]
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICO = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/'


def decidir(difiere, en_historia, cambiado):
    """'igual' | 'publicar' | 'adelante' para un festival."""
    if not difiere:
        return 'igual'
    return 'publicar' if cambiado or en_historia else 'adelante'


def publicar_todos(lista, publicar, pausa=60, dormir=time.sleep):
    """Publica cada uno; los que fallan se reintentan una vez al final → los que quedan mal."""
    mal = [f for f in lista if not publicar(f)]
    if mal:
        print(f'· {len(mal)} fallaron; espero {pausa} s y los repito: {" ".join(mal)}')
        dormir(pausa)
        mal = [f for f in mal if not publicar(f)]
    return mal


def blob(b):
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def blobs_de_main(ruta):
    """Los blobs que ese archivo ha tenido en la historia de main."""
    r = subprocess.run(['git', '-C', REPO, 'log', '--format=', '--raw', '--no-abbrev', '-m', '--first-parent', 'HEAD', '--', ruta],
                       check=True, capture_output=True, text=True)
    return {x for l in r.stdout.splitlines() if l.startswith(':') for x in l.split()[2:4]}


def _bajar(u):
    with urllib.request.urlopen(u, timeout=60) as r:
        return r.read()


def main():
    a = sys.argv
    cambiados = set(a[a.index('--cambiados') + 1].split()) if '--cambiados' in a else set()
    indice = json.loads(_bajar(PUBLICO + f'indice.json?m={int(time.time())}'))['festivales']
    if not indice:
        sys.exit('✗ el índice del almacén llegó vacío: no se publica nada')
    lista = []
    for f, e in sorted(indice.items()):
        ruta = f'festivals/{f}.json'
        p = os.path.join(REPO, ruta)
        if not os.path.exists(p):
            continue                       # publicado desde una rama que main aún no tiene
        b = open(p, 'rb').read()
        difiere = hashlib.sha256(b).hexdigest() != e['sha256']
        hist = difiere and f not in cambiados and blob(_bajar(PUBLICO + e['archivo'])) in blobs_de_main(ruta)
        d = decidir(difiere, hist, f in cambiados)
        if d == 'adelante':
            print(f'· {f}: el almacén tiene una versión que main no tuvo nunca (publicada desde una rama): no se toca')
        elif d == 'publicar' or f in cambiados:   # un cambiado igual puede traer ficha nueva
            lista.append(f)
    print(f'A publicar ({len(lista)}): {" ".join(lista) or "nada"}')
    for f in sorted(cambiados - set(indice)):
        print(f'· {f} no está en el almacén: entra con publicar-datos.py, a propósito')
    if '--probar' in a:
        return
    mal = publicar_todos(lista, lambda f: subprocess.run(
        [sys.executable, 'pipeline/publicar-datos.py', f, '--desde-main'], cwd=REPO).returncode == 0)
    if mal:
        sys.exit(f'✗ sin publicar: {" ".join(mal)} — la próxima corrida los retoma')


if __name__ == '__main__':
    main()
