# -*- coding: utf-8 -*-
"""Sinopsis, póster y title_en desde TMDB → `cinemancia-2026-tmdb.json`.

SIN BÚSQUEDA. Se entra por el `tmdbId` que ya trae el barrido de fichas, y ese
id salió del enlace que Letterboxd publica en la ficha cuyo slug es el de la
lista oficial del festival. O sea: la cadena de custodia es
festival → Letterboxd → TMDB, sin que nadie adivine un título por el camino.
Por eso aquí NO se corre `ficha_verifica`: no hay candidato que descartar, el
id es el correcto por construcción. (La verificación por director ya se hizo
en el paso anterior, y es la que autoriza a confiar en este id.)

Aun así se comprueba una cosa: que el director que devuelve TMDB coincida con
el del PDF. No para elegir —no hay a quién elegir— sino para detectar que un
id apunte a otra obra por un error de datos en Letterboxd. Si no coincide, el
dato entra marcado y no en silencio.

  · sinopsis ES: overview en es-CO, con es-ES y es-MX de respaldo. Nunca se
    traduce: si no hay sinopsis en español, el campo va vacío y queda como
    pendiente que el festival debe llenar (incidente Tribeca, 107 sinopsis
    inventadas).
  · sinopsis EN: overview en en-US.
  · póster: se guarda la RUTA de TMDB, no se descarga. Bajarlos es el paso de
    `encuadrar-posters.py`, que además los lleva al lienzo 2:3.
  · title_en: solo si el título en en-US difiere del nuestro.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHAS = f'{REPO}/festivals/staging/cinemancia-2026-fichas.json'
OUT = f'{REPO}/festivals/staging/cinemancia-2026-tmdb.json'
KEY = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY en el entorno')


def main():
    obras = json.load(open(FICHAS, encoding='utf-8'))['obras']
    con_id = [o for o in obras if o.get('tmdbId')]
    print(f'{len(con_id)} obras con tmdbId · {len(obras) - len(con_id)} sin él\n')

    out, con_es, con_en, con_post, discrepan = [], 0, 0, 0, []
    for i, o in enumerate(con_id, 1):
        det = lib.tmdb_get(f'/movie/{o["tmdbId"]}', KEY, language='es-CO')
        if not det or det.get('success') is False:
            print(f'[{i:3}] ?? {o["title"][:44]} — TMDB no respondió'); continue
        sin_es = (det.get('overview') or '').strip()
        for lang in ('es-ES', 'es-MX'):
            if sin_es:
                break
            sin_es = (lib.tmdb_get(f'/movie/{o["tmdbId"]}', KEY,
                                   language=lang).get('overview') or '').strip()
        # Los créditos se piden en en-US A PROPÓSITO: en es-CO (o en el idioma
        # original) TMDB devuelve el nombre en su alfabeto —«Евгения Арбугаева»,
        # «蔡明亮»— y director_coincide, que compara tokens latinos, no puede
        # casarlo con el del PDF. Pedirlos romanizados es lo que dice la lib, y
        # olvidarlo produjo 3 discrepancias falsas en la primera pasada.
        en = lib.tmdb_get(f'/movie/{o["tmdbId"]}', KEY, language='en-US',
                          append_to_response='credits')
        sin_en = (en.get('overview') or '').strip()
        t_en = (en.get('title') or '').strip()

        dirs = [p['name'] for p in en.get('credits', {}).get('crew', [])
                if p.get('job') == 'Director']
        coincide = lib.director_coincide(o['director'], dirs)
        if not coincide:
            discrepan.append((o, dirs))

        out.append({**o,
                    'synopsis': sin_es, 'synopsis_en': sin_en,
                    'title_en': t_en if t_en and t_en != o['title'] else o.get('title_en'),
                    'poster_tmdb': det.get('poster_path') or '',
                    'runtime_tmdb': det.get('runtime') or None,
                    'tmdb_director': dirs,
                    '_director_coincide': coincide,
                    '_src_tmdb': f'TMDB /movie/{o["tmdbId"]} (id vía Letterboxd, no por búsqueda)'})
        con_es += bool(sin_es); con_en += bool(sin_en); con_post += bool(det.get('poster_path'))
        print(f'[{i:3}/{len(con_id)}] {"OK" if coincide else "!!"} {o["title"][:38]:40} '
              f'ES{"✓" if sin_es else "·"} EN{"✓" if sin_en else "·"} '
              f'P{"✓" if det.get("poster_path") else "·"}', flush=True)
        time.sleep(0.25)

    for o in obras:
        if not o.get('tmdbId'):
            out.append({**o, 'synopsis': '', 'synopsis_en': '', 'poster_tmdb': ''})

    d = {'_provenance': lib.provenance(
            'TMDB por id verificado (cadena festival → Letterboxd → TMDB, sin búsqueda por título)',
            nota=('No se traduce nada: sin overview en español el campo va vacío y queda '
                  'como pendiente del festival (incidente Tribeca).')),
         'obras': out}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    n = len(obras)
    print(f'\n{OUT.split("/")[-1]}  ·  {n} obras')
    print(f'   sinopsis ES {con_es}/{n} · sinopsis EN {con_en}/{n} · póster TMDB {con_post}/{n}')
    faltan = [o['title'] for o in out if not o.get('synopsis')]
    print(f'\n   SIN sinopsis en español ({len(faltan)}) — esto es lo que hay que pedirle al festival:')
    for t in faltan:
        print(f'      · {t[:60]}')
    if discrepan:
        print(f'\n   ⚠ director distinto en TMDB ({len(discrepan)}) — revisar el id:')
        for o, dirs in discrepan:
            print(f'      · {o["title"][:40]:42} PDF «{o["director"]}» vs TMDB {dirs}')


if __name__ == '__main__':
    main()
