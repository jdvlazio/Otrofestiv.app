#!/usr/bin/env python3
"""integrar.py — traer main a la rama de un festival y probar que no se perdió nada.

POR QUÉ (BOGOSHORTS, 25 nov 2026): la rama larga chocó con main en decisiones, sellos y
una docena de festivales ya publicados; se resolvió a mano y la comparación también.

    python3 pipeline/integrar.py                         # 1. mezcla origin/main (o termina la que está en curso)
    python3 pipeline/integrar.py --revisar <id> [<id>…]  # 2. compara con origin/main; los <id> son los de la rama

Se corre A DIARIO mientras la rama vive. Lo que hace el 1: mezcla por clave (no por
línea) los JSON de catalogo/ y festivals/ que cambiaron en los dos lados; si los dos
cambiaron el MISMO dato a valores distintos, o uno lo borró y el otro lo cambió, no
elige: lo dice y lo deja en conflicto. Reparte un decisiones.json de antes en un
archivo por obra. El código y los generados no los toca: dice cómo. No hace el commit.
Después del commit: catalogo_construir.py --escribir, validate.py y el 2.

El 2 frena (sale con 1) si falta main en la rama, si se perdió una decisión, un sello,
un original, una fusión, una función o un campo, o si en un festival AJENO cambió algo
de la función o el lugar. Lo que cambió de una obra compartida lo lista: es lo esperado,
y se lee. Las decisiones de main con otro valor también se listan.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
MAIN = os.environ.get('INTEGRAR_CONTRA', 'origin/main')     # otro ref, solo para ensayar una mezcla vieja
NADA = object()
GENERADO = {'docs/SCHEMA.md': 'node scripts/generate-schema-md.js',
            'assets/AFICHES-AJENOS.json': 'python3 scripts/afiches-ajenos.py'}
DE_LA_OBRA = {'director', 'year', 'country', 'flags', 'genre', 'synopsis', 'synopsis_es', 'synopsis_en', 'synopsis_lang', 'synopsis_pt',
              'poster', 'posterSource', 'posterPosition', 'title_en', 'tmdb_id', 'lbSlug', 'work_id', '_src', 'editorial_caption', 'runtime'}
LISTAS = ('films', 'film_list')


def correr(*a, ok=False):
    r = subprocess.run(a, cwd=REPO, capture_output=True, text=True)
    if r.returncode and not ok:
        raise SystemExit(f'✗ {" ".join(a)}\n{r.stderr.strip()}')
    return r


def leer(ref, p):
    """El JSON en esa versión, o NADA si no existe."""
    r = correr('git', 'show', f'{ref}:{p}', ok=True)
    return json.loads(r.stdout) if r.returncode == 0 else NADA


# ── la mezcla ────────────────────────────────────────────────────────────────
def claves(xs):
    """La clave de cada elemento de una lista, o None si no se puede confiar en ninguna."""
    if not xs or not all(isinstance(x, dict) for x in xs):
        return None
    for ks in (('id',), ('work_id', 'campo'), ('absorbido',), ('work_id',), ('title',)):
        c = [tuple(x.get(k) for k in ks) for x in xs]
        if all(all(v is not None for v in k) for k in c) and len(set(map(repr, c))) == len(c):
            return [repr((ks, k)) for k in c]
    return None


def mezclar(b, o, t, donde, choques):
    """Mezcla de tres lados. `b`, `o`, `t`: antes, nuestro, main (NADA = no está)."""
    if igual(o, t) or igual(t, b):
        return o
    if igual(o, b):
        return t
    if isinstance(o, dict) and isinstance(t, dict):
        b = b if isinstance(b, dict) else {}
        out = {}
        for k in list(t) + [k for k in o if k not in t]:
            v = mezclar(b.get(k, NADA), o.get(k, NADA), t.get(k, NADA), f'{donde}/{k}', choques)
            if v is not NADA:
                out[k] = v
        return out
    if isinstance(o, list) and isinstance(t, list):
        base = b if isinstance(b, list) else []
        co, ct, cb = claves(o), claves(t), claves(base) if base else []
        # las tres con la misma forma de clave; si no, no se adivina
        formas = {c[0].split("), ")[0] for c in (co, ct, cb) if c}
        if co and ct and cb is not None and len(formas) == 1:
            mo, mt, mb = dict(zip(co, o)), dict(zip(ct, t)), dict(zip(cb, base))
            orden = fusionar_orden(cb, co, ct, donde, choques)
            vs = [mezclar(mb.get(k, NADA), mo.get(k, NADA), mt.get(k, NADA), f'{donde}[{k}]', choques) for k in orden]
            return [v for v in vs if v is not NADA]
    choques.append(donde)
    return o


def fusionar_orden(cb, co, ct, donde, choques):
    """El orden: el de main si nuestro lado no reordenó; si no, el nuestro; los dos, choque."""
    comunes = set(co) & set(ct) & set(cb)
    f = lambda c: [k for k in c if k in comunes]
    if f(co) != f(cb) and f(ct) != f(cb) and f(co) != f(ct):
        choques.append(donde + ' (orden)')
    primero, segundo = (co, ct) if f(co) != f(cb) else (ct, co)
    out = list(primero)
    for i, k in enumerate(segundo):
        if k not in out:
            previo = next((x for x in reversed(segundo[:i]) if x in out), None)
            out.insert(out.index(previo) + 1 if previo else 0, k)
    return out


def igual(a, b):
    if a is NADA or b is NADA:
        return a is b
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def dec_por_clave(xs):
    """Las decisiones de una obra por (campo, vez): puede haber dos del mismo campo."""
    out, n = {}, {}
    for d in xs or []:
        i = n[d['campo']] = n.get(d['campo'], -1) + 1
        # `no-es` y `no-alta-tmdb` son varias por obra y no una detrás de otra
        k = (d['campo'], json.dumps(d['valor'], sort_keys=True)) if d['campo'] in ('no-es', 'no-alta-tmdb', 'ficha-ok') else (d['campo'], i)
        out[f'{k[0]}#{k[1]}'] = d
    return out


def mezclar_decisiones(b, o, t, donde, choques):
    """Tres listas de decisiones de UNA obra → la mezclada."""
    m = mezclar(dec_por_clave(b), dec_por_clave(o), dec_por_clave(t), donde, choques)
    return list(m.values())


def por_obra(xs):
    out = {}
    for d in xs or []:
        out.setdefault(d['work_id'], []).append(d)
    for w, L in out.items():                    # la posición, dentro de su obra
        for i, d in enumerate(L):
            if d.get('reemplaza') is not None:
                v = xs[d['reemplaza']]
                if v['work_id'] != w:
                    raise SystemExit(f'✗ {w} reemplaza una decisión de otra obra')
                L[i] = dict(d, reemplaza=next(j for j, x in enumerate(L) if x is v))
    return out


def decisiones_de(ref):
    """{obra: [decisiones]} en esa versión, viva donde viva."""
    viejo = leer(ref, 'catalogo/decisiones.json')
    if viejo is not NADA:
        return por_obra(viejo)
    out = {}
    nombres = correr('git', 'ls-tree', '-r', '--name-only', ref, '--', 'catalogo/decisiones/').stdout.split()
    if nombres:
        pedido = '\n'.join(f'{ref}:{p}' for p in nombres) + '\n'
        r = subprocess.run(['git', 'cat-file', '--batch'], cwd=REPO, input=pedido.encode(), capture_output=True).stdout
        i = 0
        for _ in nombres:
            j = r.index(b'\n', i)
            n = int(r[i:j].split()[2])
            for d in json.loads(r[j + 1:j + 1 + n]):
                out.setdefault(d['work_id'], []).append(d)
            i = j + 2 + n
    return out


def volcar(p, v):
    """Con la forma que ya tiene en main (una línea, o su sangría)."""
    r = correr('git', 'show', f'{MAIN}:{p}', ok=True)
    crudo = r.stdout if r.returncode == 0 else '{\n '
    ls = crudo.strip().split('\n')
    if len(ls) > 1:
        txt = json.dumps(v, ensure_ascii=False, indent=(len(ls[1]) - len(ls[1].lstrip(' '))) or 1)
    else:
        txt = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    ruta = os.path.join(REPO, p)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write(txt + ('\n' if crudo.endswith('\n') else ''))


def integrar():
    import catalogo
    correr('git', 'fetch', '-q', 'origin', 'main')
    en_curso = correr('git', 'rev-parse', '-q', '--verify', 'MERGE_HEAD', ok=True).stdout.strip()
    if en_curso:
        if en_curso != correr('git', 'rev-parse', MAIN).stdout.strip():
            raise SystemExit('✗ hay otra mezcla en curso (o main avanzó): termínala o abórtala')
    else:
        if correr('git', 'status', '--porcelain', '--untracked-files=no').stdout.strip():
            raise SystemExit('✗ hay cambios sin commit: guárdalos antes')
        if correr('git', 'rev-list', '--count', f'HEAD..{MAIN}').stdout.strip() == '0':
            print('✓ la rama ya tiene main')
            return 0
        correr('git', 'merge', '--no-commit', '--no-ff', MAIN, ok=True)
        if not correr('git', 'rev-parse', '-q', '--verify', 'MERGE_HEAD', ok=True).stdout.strip():
            raise SystemExit('✗ git no pudo empezar la mezcla')
    base = correr('git', 'merge-base', 'HEAD', MAIN).stdout.strip()
    cambio = lambda x: set(correr('git', '-c', 'core.quotepath=off', 'diff', '--name-only', '--no-renames', base, x).stdout.split('\n'))
    ambos = cambio('HEAD') & cambio(MAIN)
    choques, hechos = {}, []
    # decisiones: por obra, vengan de donde vengan
    b, o, t = decisiones_de(base), decisiones_de('HEAD'), decisiones_de(MAIN)
    final, mal = [], []
    for w in sorted(set(b) | set(o) | set(t)):
        xs = mezclar_decisiones(b.get(w), o.get(w), t.get(w), w, mal)
        n = len(final)
        final += [dict(d, reemplaza=d['reemplaza'] + n) if d.get('reemplaza') is not None else d for d in xs]
    viejo = os.path.join(REPO, 'catalogo', 'decisiones.json')
    if os.path.exists(viejo):
        os.remove(viejo)
    catalogo.escribir_decisiones(final)
    correr('git', 'add', '-A', '--', 'catalogo/decisiones', ok=True)
    correr('git', 'rm', '-q', '--cached', '--ignore-unmatch', 'catalogo/decisiones.json')
    for x in mal:
        choques.setdefault('decisiones (quedó el valor de la rama)', []).append(x)
    for p in sorted(ambos):
        if not re.match(r'(catalogo|festivals)/.*\.json$', p) or p.startswith('catalogo/decisiones'):
            continue
        if p.startswith(('catalogo/obras/', 'catalogo/procedencia/')):
            correr('git', 'checkout', MAIN, '--', p) if leer(MAIN, p) is not NADA else correr('git', 'rm', '-qf', '--ignore-unmatch', p)
            hechos.append(p)                    # derivado: lo rehace el constructor
            continue
        mal = []
        v = mezclar(leer(base, p), leer('HEAD', p), leer(MAIN, p), '', mal)
        if mal:
            choques[p] = mal
        if v is NADA:
            correr('git', 'rm', '-qf', '--ignore-unmatch', p)
        else:
            volcar(p, v)
            if not mal:
                correr('git', 'add', '--', p)
        hechos.append(p)
    quedan = [p for p in correr('git', 'diff', '--name-only', '--diff-filter=U').stdout.split('\n') if p and p not in choques]
    print(f'{len(hechos)} archivo(s) JSON mezclados por clave; {len(final)} decisiones')
    for p, xs in choques.items():
        print(f'✗ {p}: el mismo dato cambió en los dos lados (quedó el de la rama): decide y `git add`')
        for x in xs[:20]:
            print('   ', x)
    for p in quedan:
        print(f'· {p}: ' + (f'se regenera: {GENERADO[p]}' if p in GENERADO else 'a mano'))
    print('después: commit, catalogo_construir.py --escribir, validate.py, integrar.py --revisar <id>')
    return 1 if choques or quedan else 0


# ── la revisión ──────────────────────────────────────────────────────────────
def funciones(d):
    """{clave: función}; sin id, por título, día y hora."""
    out = {}
    for f in d.get('films') or []:
        k = f.get('id') or repr((f.get('title'), f.get('day'), f.get('time'), f.get('venue')))
        out[k] = f
    return out


def obras(f):
    out, n = {}, {}
    for o in f.get('film_list') or []:
        k = o.get('work_id') or o.get('title')
        n[k] = n.get(k, 0) + 1
        out[k if n[k] == 1 else (k, n[k])] = o
    return out


def comparar(a, b, ajeno=True):
    """(pérdidas, cambios de función o lugar, cambios de obra) entre dos versiones de un festival."""
    pierde, funcion, obra = [], [], []
    vacio = lambda v: v in (None, '', [], {})

    def campos(x, y, quien, es_obra):
        for k in sorted(set(x) | set(y)):
            if k in LISTAS or igual(x.get(k, NADA), y.get(k, NADA)):
                continue
            # la sinopsis en español se pasó de `synopsis_es` a `synopsis`: no se pierde
            mudo = k == 'synopsis_es' and y.get('synopsis_lang') == 'es' and not vacio(y.get('synopsis'))
            if not vacio(x.get(k)) and vacio(y.get(k)) and not mudo:
                pierde.append(f'{quien}: {k} = {str(x[k])[:60]}')
            elif es_obra and k in DE_LA_OBRA:
                obra.append(f'{quien}: {k}: {str(x.get(k))[:50]} → {str(y.get(k))[:50]}')
            else:
                funcion.append(f'{quien}: {k}: {str(x.get(k))[:50]} → {str(y.get(k))[:50]}')
    fa, fb = funciones(a), funciones(b)
    pierde += [f'función {fa[k].get("title")} ({k})' for k in fa if k not in fb]
    funcion += [f'función nueva {fb[k].get("title")} ({k})' for k in fb if k not in fa]
    for k in fa:
        if k not in fb:
            continue
        x, y = fa[k], fb[k]
        campos(x, y, str(x.get('title')), not x.get('film_list'))
        oa, ob = obras(x), obras(y)
        if len(oa) == len(ob) and set(oa) != set(ob):       # una fusión cambia el work_id: por título
            oa = {o.get('title'): o for o in oa.values()}
            ob = {o.get('title'): o for o in ob.values()}
        pierde += [f'{x.get("title")}: ya no trae «{oa[w].get("title")}»' for w in oa if w not in ob]
        funcion += [f'{x.get("title")}: trae «{ob[w].get("title")}»' for w in ob if w not in oa]
        for w in oa:
            if w in ob:
                campos(oa[w], ob[w], f'{x.get("title")} › {oa[w].get("title")}', True)
    campos({k: v for k, v in a.items() if k != 'films'}, {k: v for k, v in b.items() if k != 'films'}, 'festival', False)
    return pierde, funcion, obra


def faltan_decisiones(a, b):
    """(perdidas, con otro valor) de `a` (main) en `b`, por obra y campo."""
    perdidas, otras = [], []
    for w, xs in a.items():
        mb = dec_por_clave(b.get(w))
        for k, d in dec_por_clave(xs).items():
            if k not in mb:
                perdidas.append(f'{w} {k}')
            elif not igual(mb[k]['valor'], d['valor']):
                otras.append(f'{w} {d["campo"]}: {str(d["valor"])[:60]} → {str(mb[k]["valor"])[:60]}')
    return perdidas, otras


def revisar(propios):
    import catalogo
    correr('git', 'fetch', '-q', 'origin', 'main')
    frena, cuenta = [], 0
    faltan = correr('git', 'rev-list', '--count', f'HEAD..{MAIN}').stdout.strip()
    if faltan != '0':
        raise SystemExit(f'✗ a la rama le faltan {faltan} commits de main: primero integrar.py')
    disco = {}
    for d in por_obra(catalogo.decisiones()).items():
        disco[d[0]] = d[1]
    perdidas, otras = faltan_decisiones(decisiones_de(MAIN), disco)
    frena += [f'decisión perdida: {x}' for x in perdidas]
    for n in ('sellos', 'originales', 'fusiones'):
        a, p = leer(MAIN, f'catalogo/{n}.json'), os.path.join(REPO, 'catalogo', n + '.json')
        if a is NADA:
            continue
        b = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
        ids = (lambda x: {f['absorbido'] for f in x}) if isinstance(a, list) else set
        frena += [f'{n}: falta {k}' for k in sorted(ids(a) - ids(b))]
    print('decisiones de main con otro valor:', len(otras))
    for x in otras:
        print('   ', x)
    nombres = [x for x in correr('git', 'ls-tree', '--name-only', MAIN, '--', 'festivals/').stdout.split('\n') if x.endswith('.json')]
    for p in nombres:
        fid, ruta = os.path.basename(p)[:-5], os.path.join(REPO, p)
        if not os.path.exists(ruta):
            frena.append(f'falta {p}')
            continue
        a, b = leer(MAIN, p), json.load(open(ruta, encoding='utf-8'))
        if igual(a, b):
            continue
        pierde, funcion, obra = comparar(a, b)
        cuenta += 1
        print(f'{fid}: {len(obra)} datos de obra, {len(funcion)} de función o lugar, {len(pierde)} perdidos')
        for x in obra:
            print('   ', x)
        if fid not in propios:
            frena += [f'{fid}: {x}' for x in pierde + funcion]
    print(f'{cuenta} festival(es) de main cambian')
    for x in frena:
        print('✗', x)
    print('✗ no está lista' if frena else '✓ no se perdió nada de main')
    return 1 if frena else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(integrar())
    if a[0] == '--revisar' and not any(x.startswith('-') for x in a[1:]):
        sys.exit(revisar(set(a[1:])))
    sys.exit(__doc__)
