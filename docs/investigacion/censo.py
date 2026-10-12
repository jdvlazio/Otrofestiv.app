import json, glob, os, re, unicodedata, collections, sys
REPO = sys.argv[1]
OUT = sys.argv[2]

def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def mins(v):
    m = re.search(r'\d+', str(v or ''))
    return int(m.group()) if m else None

recs = []  # (fest, obra, is_prog_child)
for f in sorted(glob.glob(f'{REPO}/festivals/*.json')):
    fid = os.path.basename(f)[:-5]
    j = json.load(open(f, encoding='utf-8'))
    for x in j.get('films') or []:
        if not isinstance(x, dict): continue
        if x.get('type') == 'event': continue
        if x.get('title'): recs.append((fid, x, False))
        for o in x.get('film_list') or []:
            if isinstance(o, dict) and o.get('title') and o.get('type') != 'event':
                recs.append((fid, o, True))

def key(o):
    if o.get('tmdb_id'): return ('tmdb', str(o['tmdb_id']))
    return ('td', norm(o['title']) + '|' + norm(o.get('director') or ''))

groups = collections.defaultdict(list)
for fid, o, ch in recs:
    groups[key(o)].append((fid, o))

FIELDS = ['tmdb_id', 'poster', 'synopsis', 'synopsis_en', 'year', 'duration', 'country', 'director', 'lbSlug']
cov = {k: sum(1 for _, o, _ in recs if o.get(k)) for k in FIELDS}
# cobertura por obra única (algún registro lo tiene)
covu = {k: sum(1 for g in groups.values() if any(o.get(k) for _, o in g)) for k in FIELDS}

multi = {k: g for k, g in groups.items() if len({fid for fid, _ in g}) >= 2}
sin_tmdb = [k for k in groups if k[0] == 'td']
sin_tmdb_recs = sum(1 for _, o, _ in recs if not o.get('tmdb_id'))
n_prog_children = sum(1 for _, _, ch in recs if ch)
fests = sorted({fid for fid, _, _ in recs})
per_fest = collections.Counter(fid for fid, _, _ in recs)

# contradicciones
def contra(g):
    byf = {}
    for fid, o in g:
        byf.setdefault(fid, o)  # primera por festival
    out = {}
    def vals(k, f=lambda v: v):
        d = {fid: f(o.get(k)) for fid, o in byf.items() if o.get(k)}
        return d
    d = vals('director', lambda v: norm(v))
    if len(set(d.values())) > 1: out['director'] = {fid: byf[fid]['director'] for fid in d}
    y = vals('year', int)
    if len(set(y.values())) > 1: out['year'] = y
    du = vals('duration', mins)
    if du and max(du.values()) - min(du.values()) > 3: out['duration'] = {fid: byf[fid]['duration'] for fid in du}
    p = vals('poster')
    if len(set(p.values())) > 1: out['poster'] = p
    s = vals('synopsis', lambda v: re.sub(r'\s+', ' ', v.strip()))
    if len(set(s.values())) > 1: out['synopsis'] = {fid: byf[fid]['synopsis'][:90] + '…' for fid in s}
    return out

contras = {}
for k, g in multi.items():
    c = contra(g)
    if c: contras[k] = c
cnt_by_field = collections.Counter(f for c in contras.values() for f in c)

# sidecars
side = {'correcciones': {}, 'sinopsis': {}, 'afiches': {}}
titles_side = {'correcciones': set(), 'sinopsis': set(), 'afiches': set()}
for f in sorted(glob.glob(f'{REPO}/festivals/staging/*.json')):
    b = os.path.basename(f)[:-5]
    for tipo in side:
        if b.endswith('-' + tipo):
            j = json.load(open(f, encoding='utf-8'))
            node = j.get('fichas') if tipo == 'correcciones' else j.get(tipo)
            if node is None:
                # ficma ig-correcciones: lista 'ok'
                node = j.get('ok') or {}
            n = len(node)
            side[tipo][b] = n
            if isinstance(node, dict):
                for t in node: titles_side[tipo].add(norm(t))
# titulos multi (norm) set
multi_titles = set()
for k, g in multi.items():
    for _, o in g: multi_titles.add(norm(o['title']))
side_multi = {tipo: sorted(t for t in ts if t in multi_titles) for tipo, ts in titles_side.items()}

L = []
w = L.append
w('# Censo de obras publicadas — festivals/*.json\n')
w(f'Fecha: 2026-10-12 · repo clon7 (rama rev/ficma-main) · {len(fests)} festivales: {", ".join(fests)}\n')
w('Método: se recorren `films[]` de cada JSON y los `film_list[]` de los programas; se ignoran `type=="event"`. '
  'Clave de obra única: `tmdb_id` si existe; si no, `norm(title)|norm(director)` (lib.norm: minúsculas, sin tildes, solo alfanumérico). '
  'Un «registro» es cada aparición (una obra con 3 funciones en un festival = 3 registros).\n')
w('## 1. Totales\n')
w(f'- Registros de obra: **{len(recs)}** (de los cuales {n_prog_children} viven dentro de `film_list` de programas; {len(recs)-n_prog_children} son entradas de primer nivel)')
w(f'- Obras únicas (tmdb_id o título+director): **{len(groups)}**')
w(f'  - agrupadas por tmdb_id: {sum(1 for k in groups if k[0]=="tmdb")}')
w(f'  - agrupadas por título+director (sin tmdb_id): {len(sin_tmdb)}')
w(f'- Registros por festival: ' + ', '.join(f'{f}={n}' for f, n in sorted(per_fest.items())))
w('')
w('## 2. Obras en 2 o más festivales\n')
w(f'- Obras únicas presentes en ≥2 festivales: **{len(multi)}** ({len(multi)/len(groups)*100:.1f}% del catálogo único)')
dist = collections.Counter(len({fid for fid, _ in g}) for g in multi.values())
w('- Distribución: ' + ', '.join(f'{n} festivales → {c} obras' for n, c in sorted(dist.items())))
w('\n### Las 30 más repetidas\n')
w('| # | Obra (director) | Festivales | clave |')
w('|---|---|---|---|')
top = sorted(multi.items(), key=lambda kv: (-len({fid for fid, _ in kv[1]}), kv[1][0][1]['title']))[:30]
for i, (k, g) in enumerate(top, 1):
    o = g[0][1]
    fs = sorted({fid for fid, _ in g})
    w(f'| {i} | {o["title"]} ({o.get("director") or "—"}) | {len(fs)}: {", ".join(fs)} | {k[0]}:{k[1][:40]} |')
w('')
w('## 3. Contradicciones entre festivales (obras repetidas)\n')
w(f'- Obras repetidas con al menos un campo contradictorio: **{len(contras)}** de {len(multi)}')
w('- Por campo: ' + ', '.join(f'{f}={c}' for f, c in cnt_by_field.most_common()))
w('  - Nota: `poster` distinto incluye el caso frecuente de rutas `/assets/<festival>/…` propias de cada festival aunque la imagen sea la misma; `synopsis` distinta incluye variantes de redacción/longitud.')
w('\n### 20 ejemplos concretos\n')
# priorizar las que tienen director/year/duration
ordered = sorted(contras.items(), key=lambda kv: (-sum(f in kv[1] for f in ('director','year','duration')), -len(kv[1])))
for k, c in ordered[:20]:
    g = multi[k]
    w(f'**{g[0][1]["title"]}** — `{k[0]}:{k[1][:50]}`')
    for f, d in c.items():
        w(f'- {f}:')
        for fid, v in d.items():
            w(f'  - {fid}: {v}')
    w('')
w('## 4. Cobertura por campo\n')
w('| Campo | registros con dato | % registros | obras únicas con dato (algún registro) | % únicas |')
w('|---|---|---|---|---|')
for f in FIELDS:
    w(f'| {f} | {cov[f]} | {cov[f]/len(recs)*100:.1f}% | {covu[f]} | {covu[f]/len(groups)*100:.1f}% |')
w('')
w('## 5. Obras sin tmdb_id\n')
w(f'- Registros sin tmdb_id: **{sin_tmdb_recs}** de {len(recs)} ({sin_tmdb_recs/len(recs)*100:.1f}%)')
w(f'- Obras únicas sin tmdb_id (candidatas a id propio): **{len(sin_tmdb)}** de {len(groups)} ({len(sin_tmdb)/len(groups)*100:.1f}%)')
sin_dir = sum(1 for k in sin_tmdb if k[1].endswith('|'))
w(f'  - de ellas, sin director (clave solo por título): {sin_dir}')
w(f'  - de ellas, en ≥2 festivales: {sum(1 for k in multi if k[0]=="td")}')
# posible duplicados: mismo norm title con y sin tmdb
bt = collections.defaultdict(set)
for k, g in groups.items():
    for _, o in g: bt[norm(o['title'])].add(k)
dup_t = {t: ks for t, ks in bt.items() if len(ks) > 1}
w(f'  - títulos normalizados que caen en más de una clave (posibles duplicados por director distinto o tmdb_id vs sin tmdb_id): {len(dup_t)}')
for t, ks in sorted(dup_t.items())[:25]:
    w(f'    - «{t}»: ' + ' / '.join(f'{k[0]}:{k[1][:40]}' for k in sorted(ks)))
w('')
w('## 6. Sidecars de decisiones (festivals/staging)\n')
for tipo, d in side.items():
    w(f'### *-{tipo}.json — {len(d)} archivos, {sum(d.values())} entradas en total')
    for b, n in d.items(): w(f'- {b}: {n}')
    w(f'- Títulos de estos sidecars que corresponden a obras en ≥2 festivales: **{len(side_multi[tipo])}**')
    for t in side_multi[tipo]: w(f'  - {t}')
    w('')
json.dump({'recs': len(recs), 'unique': len(groups), 'multi': len(multi), 'contras': len(contras), 'cnt': cnt_by_field, 'side': side, 'side_multi': {k: len(v) for k, v in side_multi.items()}, 'cov': cov, 'sin_tmdb': len(sin_tmdb)}, open(OUT + '.json', 'w'), indent=1, ensure_ascii=False)
open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L[:40]))
