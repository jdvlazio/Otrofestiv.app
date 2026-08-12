# -*- coding: utf-8 -*-
"""Candidatos a `title_en` para el catálogo de FICDEH 2026.

REGLA (docs/FESTIVAL-CHECKLIST.md): `title_en` es el título internacional
OFICIAL verificado en circuito — NUNCA una traducción nuestra. Sin oficial, sin
title_en. Por eso este script no escribe nada: propone y deja que Juan apruebe.

Fuentes, en orden de autoridad:
  1. La propia programación del festival, que publica el internacional entre
     paréntesis («Silenciada (Silenced)»).
  2. TMDB: `title` en en-US cuando difiere de `original_title`. Ese campo ES el
     título de distribución internacional, no una traducción automática.

Descarta el caso inverso —«American Doctor (Médico estadounidense)»—, donde el
paréntesis es la traducción al español de un título que ya está en inglés: ahí
el título original ya sirve y no hace falta title_en.
"""
import json, os, re, subprocess, time, urllib.parse, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = f'{REPO}/festivals/staging/ficdeh-2026.json'
CAN = f'{REPO}/festivals/staging/ficdeh-2026-programacion-canonica.json'
OUT = f'{REPO}/festivals/staging/ficdeh-2026-title-en-candidatos.json'
KEY = os.environ.get('TMDB_API_KEY', '')


def api(path, **params):
    params['api_key'] = KEY
    url = f'https://api.themoviedb.org/3/{path}?' + urllib.parse.urlencode(params)
    r = subprocess.run(['curl', '-s', '--max-time', '25', url], capture_output=True)
    try:
        return json.loads(r.stdout.decode('utf-8', 'ignore'))
    except Exception:
        return {}


def ascii_ish(s):
    """¿Parece inglés? — sin tildes ni eñes. Filtro tosco pero suficiente para
    descartar que TMDB nos devuelva el mismo título en español."""
    return not re.search(r'[áéíóúñüàèìòùâêîôûç]', (s or '').lower())


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    can = json.load(open(CAN, encoding='utf-8'))['funciones']

    # 1) el paréntesis de la programación oficial
    del_festival = {}
    for x in can:
        m = re.match(r'^(.+?)\s*\(([^)]{3,60})\)\s*$', x['titulo'])
        if not m:
            continue
        base, par = m.group(1).strip(), m.group(2).strip()
        if ascii_ish(par) and not ascii_ish(base):      # ES (EN) → sirve
            del_festival[norm(base)] = par

    cands = []
    for f in cat['films']:
        if f.get('title_en'):
            continue
        t = f['title']
        hit = del_festival.get(norm(t))
        if hit:
            cands.append({'title': t, 'title_en': hit, 'fuente': 'programación oficial del festival',
                          'confianza': 'alta'})
            continue
        # 2) TMDB: title (en-US) ≠ original_title
        r = api('search/movie', query=t, include_adult='false')
        time.sleep(0.3)
        for c in (r.get('results') or [])[:3]:
            en, orig = (c.get('title') or '').strip(), (c.get('original_title') or '').strip()
            anio = (c.get('release_date') or '')[:4]
            if norm(orig) != norm(t) and norm(en) != norm(t):
                continue                                  # ni el original ni el en-US son nuestra obra
            if en and norm(en) != norm(orig) and ascii_ish(en):
                cands.append({'title': t, 'title_en': en, 'fuente': f'TMDB {c["id"]}',
                              'confianza': 'media', 'anio_tmdb': anio,
                              'anio_catalogo': f.get('year'), 'original_title': orig})
            break

    json.dump({'_nota': 'PROPUESTAS — requieren aprobación de Juan; title_en jamás se traduce',
               'candidatos': cands}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sin = sum(1 for f in cat['films'] if not f.get('title_en'))
    print(f'obras sin title_en: {sin} · candidatos hallados: {len(cands)}\n')
    for c in cands:
        extra = ''
        if c.get('anio_tmdb') and str(c.get('anio_catalogo')) != c['anio_tmdb']:
            extra = f"  ⚠️ año {c['anio_catalogo']} vs TMDB {c['anio_tmdb']}"
        print(f"  {c['title'][:38]:39} → «{c['title_en'][:34]}»  [{c['fuente']}]{extra}")


if __name__ == '__main__':
    main()
