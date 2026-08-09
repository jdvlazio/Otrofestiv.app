# -*- coding: utf-8 -*-
"""enriquecer.py <fest-id> [--posters] — la ficha de cada obra, VERIFICADA.

Herramienta genérica sobre el formato intermedio. En FICMA esto fueron cuatro
scripts (tmdb, repesca, title-en, letterboxd); aquí es una pasada por obra:

  1. TMDB por título, aceptando SOLO lo que pasa ficha_verifica() — director ✓
     y (año ±1 o duración ±3 min). La lección Tribeca: sin match no se adivina.
  2. Del id verificado: póster, sinopsis ES y EN, género, y title_en cuando el
     título en en-US difiere del nuestro (si son iguales, el campo duplicaría).
  3. lbSlug por el atajo letterboxd.com/tmdb/<id> — el slug lo da Letterboxd
     desde su propio mapeo, nunca lo inferimos de un título (homónimos).

Lee   festivals/staging/<id>-crudo.json          (formato intermedio, lib.cargar_crudo)
Opc.  festivals/staging/<id>-correcciones.json   {"titulo_oficial":{}, "alias":{}}
        · titulo_oficial: el OCR o el programa escriben mal el título; se
          corrige contra el afiche («AA95» → «AA965»). El título CORREGIDO es
          el que se busca y el que sale en el reporte.
        · alias: el festival rebautizó la obra; se BUSCA por el nombre de
          distribución («Nina y los cuentos del Erizo» → «Nina et le secret du
          hérisson») pero el título del festival se conserva.
Esc.  festivals/staging/<id>-enriquecido.json
      assets/<id>/<slug>.jpg                     (con --posters, w780)

Requiere TMDB_API_KEY en el entorno.
"""
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import (cargar_crudo, ficha_verifica, norm, provenance, slug,
                 tmdb_get, UA)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'


def variantes(titulo, alias):
    """Formas de buscar el mismo título: alias del festival, el entrecomillado
    interno («La Sirena (The Siren)» → ambos lados), y el título entero."""
    v = []
    if titulo in alias:
        v.append(alias[titulo])
    v.append(titulo)
    m = re.match(r'^(.+?)\s*\((.+)\)\s*$', titulo)
    if m:
        v += [m.group(2).strip(), m.group(1).strip()]
    return list(dict.fromkeys(v))


def lb_slug(tmdb_id):
    """302 de letterboxd.com/tmdb/<id> → slug. '' si no hay mapeo (y ese es el
    estado honesto: la UI oculta el botón; nunca se cuelga un homónimo)."""
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{redirect_url}',
                        '--max-time', '25', '-A', UA,
                        f'https://letterboxd.com/tmdb/{tmdb_id}/'], capture_output=True)
    m = re.match(r'https://letterboxd\.com/film/([^/]+)/?$', r.stdout.decode().strip())
    return m.group(1) if m else ''


def enriquecer_obra(f, key, alias):
    """→ dict verificado o None. `f` es una función del formato intermedio."""
    for q in variantes(f['titulo'], alias):
        for lang in ('es-ES', 'en-US'):
            res = tmdb_get('/search/movie', key, query=q, language=lang,
                           include_adult='false')
            for c in (res.get('results') or [])[:6]:
                det = tmdb_get(f"/movie/{c['id']}", key, language='es-ES',
                               append_to_response='credits')
                det_en = tmdb_get(f"/movie/{c['id']}", key, language='en-US',
                                  append_to_response='credits')
                # créditos de ambos idiomas: los en-US vienen romanizados
                # (宮崎吾朗 → «Goro Miyazaki») y sin ellos el director nunca casa
                det.setdefault('credits', {}).setdefault('crew', []).extend(
                    det_en.get('credits', {}).get('crew', []))
                if not ficha_verifica(f, det):
                    continue
                en = det_en.get('title') or ''
                out = {'tmdb_id': c['id'],
                       'titulo_original': det.get('original_title'),
                       'poster_path': det.get('poster_path'),
                       'synopsis_es': det.get('overview') or '',
                       'synopsis_en': det_en.get('overview') or '',
                       'genero': (det.get('genres') or [{}])[0].get('name', ''),
                       'anio_tmdb': int((det.get('release_date') or '0')[:4] or 0),
                       'duracion_tmdb': det.get('runtime') or 0,
                       '_verificado': 'director✓ + año/duración',
                       '_busqueda': q}
                if en and norm(en) not in (norm(f['titulo']), norm(out['titulo_original'] or '')):
                    out['title_en'] = en
                sl = lb_slug(c['id'])
                if sl:
                    out['lbSlug'] = sl
                return out
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: TMDB_API_KEY=… python3 pipeline/enriquecer.py <fest-id> [--posters]')
    fid, posters = sys.argv[1], '--posters' in sys.argv
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')

    crudo = cargar_crudo(f'{ST}/{fid}-crudo.json')
    corr_p = f'{ST}/{fid}-correcciones.json'
    corr = json.load(open(corr_p, encoding='utf-8')) if os.path.exists(corr_p) else {}
    tit_of = corr.get('titulo_oficial', {})
    alias = corr.get('alias', {})

    obras = {}
    for f in crudo['funciones']:
        if f.get('en_app', True) and f.get('tipo', 'film') in ('film', ''):
            t = tit_of.get(f['titulo'], f['titulo'])
            obras.setdefault(t, {**f, 'titulo': t})

    ok, sin = {}, []
    for i, (t, f) in enumerate(sorted(obras.items()), 1):
        e = enriquecer_obra(f, key, alias)
        if e:
            ok[t] = e
            print(f'[{i:3}/{len(obras)}] OK  {t[:46]:48} tmdb {e["tmdb_id"]}'
                  f'{"  lb✓" if e.get("lbSlug") else ""}'
                  f'{"  en✓" if e.get("title_en") else ""}', flush=True)
        else:
            sin.append(t)
            print(f'[{i:3}/{len(obras)}] —   {t[:46]:48} sin ficha verificable', flush=True)
        time.sleep(0.2)

    if posters:
        os.makedirs(f'{REPO}/assets/{fid}', exist_ok=True)
        n = 0
        for t, e in ok.items():
            if not e.get('poster_path'):
                continue
            dest = f'{REPO}/assets/{fid}/{slug(t)}.jpg'
            if os.path.exists(dest) and os.path.getsize(dest) > 5000:
                n += 1; continue
            subprocess.run(['curl', '-sL', '--max-time', '30', '-o', dest,
                            f'https://image.tmdb.org/t/p/w780{e["poster_path"]}'])
            if os.path.getsize(dest) > 5000:
                n += 1
        print(f'pósters en assets/{fid}/: {n}')

    json.dump({'_provenance': provenance(
        'TMDB + letterboxd.com/tmdb/<id>, emparejado con ficha_verifica() '
        '(director + año ±1 o duración ±3 min). Lo que no verifica no entra.'),
        'verificadas': ok, 'sin_ficha': sorted(sin)},
        open(f'{ST}/{fid}-enriquecido.json', 'w', encoding='utf-8'),
        ensure_ascii=False, indent=1)
    print(f'\n{len(obras)} obras · verificadas {len(ok)} · sin ficha {len(sin)}')
    print(f'  con póster {sum(1 for e in ok.values() if e["poster_path"])} · '
          f'con lbSlug {sum(1 for e in ok.values() if e.get("lbSlug"))} · '
          f'con title_en {sum(1 for e in ok.values() if e.get("title_en"))}')


if __name__ == '__main__':
    main()
