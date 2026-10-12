#!/usr/bin/env python3
"""catalogo_construir.py — fase 1 del catálogo único (docs/CATALOGO-OBRAS.md).

MODO SIMULACIÓN por defecto: lee los 32 festivales publicados, agrupa sus obras
y escribe INFORMES en una carpeta de trabajo (--salida), nunca en catalogo/.
Nada se publica ni se fusiona solo.

El reconocimiento tiene TRES salidas (EIDR / DAMA-DMBOK):
  · COINCIDE   — mismo tmdb_id; o misma huella de título + mismo apellido de
                 director + año ±1 (o año ausente en uno de los dos lados).
  · CANDIDATO  — va a Juan: misma huella y una fuente sin director; o mismo
                 director y año con título parecido (≥ 0,85, traducciones/akas);
                 o misma huella y director pero años a más de 1 de distancia.
  · NO COINCIDE — todo lo demás (homónimos, remakes).
Un candidato NUNCA se une solo: queda en candidatos.json hasta que Juan decida.

    python3 pipeline/catalogo_construir.py --salida <carpeta>
"""
import difflib
import glob
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from catalogo import huella, apellido  # noqa: E402
from lib import sinacento  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UMBRAL = 0.85


def registros():
    """Cada obra publicada, con su festival. Las de dentro de los programas de
    cortos también; las actividades no."""
    out = []
    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        try:
            d = json.load(io.open(p, encoding='utf-8'))
        except Exception:
            continue
        for f in d.get('films', []):
            if f.get('type') == 'event':
                continue
            for o in (f.get('film_list') if f.get('film_list') else [f]):
                if o.get('type') == 'event' or not o.get('title'):
                    continue
                dur = re.match(r'\d+', str(o.get('duration') or ''))
                anio = o.get('year')
                out.append({'fest': fid, 'titulo': o['title'], 'director': (o.get('director') or '').strip(),
                            'anio': int(anio) if str(anio or '').isdigit() else None,
                            'duracion': int(dur.group()) if dur else None,
                            'pais': o.get('country'), 'tmdb': o.get('tmdb_id'), 'lb': o.get('lbSlug'),
                            'poster': o.get('poster'), 'sinopsis': o.get('synopsis'),
                            'sinopsis_en': o.get('synopsis_en'), 'title_en': o.get('title_en')})
    return out


class Uniones:
    def __init__(self, n):
        self.p = list(range(n))

    def raiz(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def une(self, a, b):
        self.p[self.raiz(a)] = self.raiz(b)


def _anio_ok(a, b):
    return a is None or b is None or abs(a - b) <= 1


def construir(R):
    U = Uniones(len(R))
    for r in R:
        r['_h'], r['_ap'] = huella(r['titulo']), apellido(r['director'])
    # 1. mismo tmdb_id
    por_tmdb = defaultdict(list)
    for i, r in enumerate(R):
        if r['tmdb']:
            por_tmdb[r['tmdb']].append(i)
    for ids in por_tmdb.values():
        for j in ids[1:]:
            U.une(ids[0], j)
    # 2. misma huella + mismo apellido + año compatible
    por_h = defaultdict(list)
    for i, r in enumerate(R):
        if r['_h']:
            por_h[r['_h']].append(i)
    candidatos = []
    for h, ids in por_h.items():
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = R[ids[x]], R[ids[y]]
                if a['tmdb'] and b['tmdb'] and a['tmdb'] != b['tmdb']:
                    continue                      # dos fichas distintas: no es la misma
                if a['fest'] == b['fest']:
                    U.une(ids[x], ids[y])         # un festival no repite título para dos obras
                    continue
                if a['_ap'] and b['_ap']:
                    if a['_ap'] != b['_ap']:
                        continue                  # homónimos
                    if _anio_ok(a['anio'], b['anio']):
                        U.une(ids[x], ids[y])
                    else:
                        candidatos.append((ids[x], ids[y], f'mismo título y director, años {a["anio"]} y {b["anio"]}'))
                elif (a['duracion'] and b['duracion'] and abs(a['duracion'] - b['duracion']) <= 3) or \
                        (a['anio'] and b['anio'] and abs(a['anio'] - b['anio']) <= 1):
                    U.une(ids[x], ids[y])         # sin director en un lado, pero duración o año lo corroboran (regla de lib.ya_publicada)
                else:
                    candidatos.append((ids[x], ids[y], 'mismo título; una fuente sin director'))
    # 3. mismo director + año, título parecido (traducción / aka): solo candidato
    por_bloque = defaultdict(list)
    for i, r in enumerate(R):
        if r['_ap'] and r['anio']:
            por_bloque[(r['_ap'], r['anio'])].append(i)
    for ids in por_bloque.values():
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                a, b = R[ids[x]], R[ids[y]]
                if U.raiz(ids[x]) == U.raiz(ids[y]) or a['_h'] == b['_h']:
                    continue
                s = difflib.SequenceMatcher(None, a['_h'], b['_h']).ratio()
                if s >= UMBRAL:
                    candidatos.append((ids[x], ids[y], f'mismo director y año, títulos parecidos ({s:.2f})'))
    # los candidatos que ya quedaron unidos por otra vía no se preguntan
    vistos, cand = set(), []
    for x, y, por in candidatos:
        k = tuple(sorted((U.raiz(x), U.raiz(y))))
        if k[0] == k[1] or k in vistos:
            continue
        vistos.add(k)
        cand.append((x, y, por))
    grupos = defaultdict(list)
    for i in range(len(R)):
        grupos[U.raiz(i)].append(i)
    return list(grupos.values()), cand


def _dir(s):
    return re.sub(r'[^a-z ]', '', sinacento(s or '').lower()).strip()


def contradicciones(R, grupo):
    """Lo que la misma obra dice distinto en cada festival."""
    out = {}
    for campo, norma in (('director', _dir), ('anio', lambda v: v), ('pais', lambda v: v)):
        vals = {R[i]['fest']: R[i][campo] for i in grupo if R[i][campo] not in (None, '')}
        if len({norma(v) for v in vals.values()}) > 1:
            out[campo] = vals
    durs = {R[i]['fest']: R[i]['duracion'] for i in grupo if R[i]['duracion']}
    if durs and max(durs.values()) - min(durs.values()) > 3:
        out['duracion (va a versiones)'] = durs
    tm = {R[i]['fest']: R[i]['tmdb'] for i in grupo if R[i]['tmdb']}
    if len(set(tm.values())) > 1:
        out['tmdb'] = tm
    return out


def main():
    if '--salida' not in sys.argv:
        sys.exit('uso: catalogo_construir.py --salida <carpeta>  (simulación: nunca escribe catalogo/)')
    sal = sys.argv[sys.argv.index('--salida') + 1]
    if os.path.abspath(sal).startswith(os.path.join(REPO, 'catalogo')):
        sys.exit('✗ la simulación no escribe en catalogo/')
    os.makedirs(sal, exist_ok=True)
    R = registros()
    grupos, cand = construir(R)
    multi = [g for g in grupos if len({R[i]['fest'] for i in g}) > 1]
    contra = [(g, contradicciones(R, g)) for g in multi]
    contra = [(g, c) for g, c in contra if c]
    fmt = lambda i: {k: R[i][k] for k in ('fest', 'titulo', 'director', 'anio', 'duracion', 'tmdb')}
    json.dump([{'a': fmt(x), 'b': fmt(y), 'por_que': por} for x, y, por in cand],
              io.open(f'{sal}/candidatos.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump([{'obra': R[g[0]]['titulo'], 'festivales': sorted({R[i]['fest'] for i in g}), 'difiere': c}
               for g, c in sorted(contra, key=lambda gc: -len(gc[0]))],
              io.open(f'{sal}/contradicciones.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    resumen = {'registros': len(R), 'obras': len(grupos), 'en_varios_festivales': len(multi),
               'con_contradicciones': len(contra), 'candidatos': len(cand),
               'sin_tmdb': sum(1 for g in grupos if not any(R[i]['tmdb'] for i in g)),
               'por_motivo': {m: sum(1 for *_, p in cand if p.startswith(m)) for m in
                              ('mismo título y director', 'mismo título; una fuente', 'mismo director y año')}}
    json.dump(resumen, io.open(f'{sal}/resumen.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
