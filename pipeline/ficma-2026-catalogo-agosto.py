# -*- coding: utf-8 -*-
"""Congela el CATÁLOGO de FICMA 17 antes de que la reprogramación lo encoja.

El festival volvió del 19 al 26 de septiembre con una parrilla nueva y, de las
90 funciones de agosto, hoy solo 11 están reanunciadas. Publicar solo esas 11 es
lo correcto —no se inventa una fecha que nadie declaró—, pero arrastraba dos
problemas que este paso resuelve:

  1. El ensamblador de septiembre sacaba la ficha de cada obra del JSON PUBLICADO.
     En cuanto ese JSON se encoge, re-correrlo devuelve un catálogo vacío: el
     script dejaba de ser re-corrible en el momento mismo de usarlo. Ahora lee
     esta foto, que no cambia.
  2. Los ~79 pósters de las obras que salieron quedaban huérfanos en assets/ y
     [asset-huerfano] los marcaba para borrar. Son justo los que harán falta
     cuando el festival publique el resto de la parrilla. Acá quedan nombrados.

La foto se toma de `origin/main`, que es el último estado con las 90 funciones.
No se vuelve a tomar: si se corre con el JSON ya encogido, aborta.
"""
import json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = f'{REPO}/festivals/staging/ficma-2026-catalogo-agosto.json'
FICHA = ('title', 'director', 'year', 'duration', 'country', 'flags', 'genre',
         'poster', 'posterSource', 'synopsis', 'synopsis_en', 'synopsis_lang',
         'tmdb_id', 'lbSlug', 'title_en')


def main():
    if os.path.exists(SALIDA):
        print(f'ya existe, no se vuelve a tomar: {os.path.basename(SALIDA)}')
        return
    crudo = subprocess.run(['git', 'show', 'origin/main:festivals/ficma-2026.json'],
                           capture_output=True, text=True, cwd=REPO).stdout
    d = json.loads(crudo)
    if len(d['films']) < 80:
        sys.exit('origin/main ya viene encogido: la foto tiene que salir del estado '
                 'con las 90 funciones de agosto. Buscá el commit anterior.')
    obras = {}
    for f in d['films']:
        if f.get('title'):
            obras.setdefault(f['title'], {k: f[k] for k in FICHA if f.get(k) is not None})
    json.dump({'_provenance': {
        'fuente': 'festivals/ficma-2026.json en origin/main — la edición de AGOSTO, con sus 90 funciones',
        'capturado': '2026-09-15',
        'por_que': 'la reprogramación de septiembre publica 11 funciones; esta foto guarda '
                   'la ficha de las 90 obras para cuando salga el resto de la parrilla, y '
                   'es lo que lee ficma-2026-septiembre.py (no el JSON publicado, que cambia)'},
        'obras': obras},
        open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con = lambda k: sum(1 for o in obras.values() if o.get(k))
    print(f'{len(obras)} obras congeladas · póster {con("poster")} · sinopsis {con("synopsis")} · lbSlug {con("lbSlug")}')


if __name__ == '__main__':
    main()
