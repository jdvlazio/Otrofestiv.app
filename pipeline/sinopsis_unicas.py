#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sinopsis_unicas.py — UNA sinopsis por obra, y cuándo una nueva la reemplaza.

Decisión de Juan (23 nov 2026): la sinopsis es de la OBRA, como el afiche
(afiches_unicos.py). Medido ese día: 184 obras con más de una en español, y solo
15 eran el mismo texto o casi. Se leyeron las 184 sugeridas; lo elegido vive en
catalogo/decisiones.json (campo `sinopsis.es`), que el constructor respeta.

UNA SINOPSIS CUENTA LA OBRA, en español y sin nada del evento. Defectos que se
encontraron PUBLICADOS: la lista de actores, enlaces de compra, «Q&A con el
director» pegado, una proyección con autodescripción, inglés y portugués en el
campo español. `defectos()` los detecta.

EL CRITERIO cuando llega una nueva:
  · no hay sinopsis en el almacén           → ENTRA (si no es defectuosa);
  · la nueva es defectuosa                  → se MANTIENE la que está;
  · la que está es defectuosa y la nueva no → se REEMPLAZA;
  · mismo texto (o la nueva contenida)      → se MANTIENE;
  · la nueva contiene entera a la que está  → se REEMPLAZA;
  · cualquier otra                          → se REVISA: la lee una persona.
Lo elegido a mano por Juan nunca se reemplaza solo. Lo ya comparado queda en
`vistas` (huellas) y no se vuelve a preguntar.

    python3 pipeline/sinopsis_unicas.py --revisar [<festival>]   # no escribe
    python3 pipeline/sinopsis_unicas.py --registrar <archivo>
    python3 pipeline/sinopsis_unicas.py --aplicar [<festival>] [--escribir]   # lo elegido, a lo publicado
"""
import hashlib
import json
import os
import re
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ES = set('el la los las un una de del que en con por para su sus se es y como al lo entre cuando sin más'.split())
_EN = set('the of and to in is his her with from that their for by on as who an when she he they'.split())
_PT = set('uma um dos das não em com seu sua ele ela os as ao pela'.split())
_EVENTO = re.compile(r'(?i)(invitad[oa]s?:|\bconversatorio\b|ep[ií]logo sonoro|q&a|\benlace\b.{0,30}\bentrada|comprar (?:la )?(?:entrada|boleta)'
                     r'|proyecci[oó]n con (?:auto|audio)|con la presencia del? (?:la )?(?:director|productor|actor|actriz|equipo|realizador)|www\.|https?:)')
_CREDITO = re.compile(r'(?i)(filmaffinity|wikipedia|\bimdb\b|\([A-Z]\.[A-Z]\.\)$)')
_FICHA = re.compile(r'(?i)(duraci[oó]n exacta|\bes un (?:corto|largo)metraje\b.{0,60}\bdirigido por|(?:^|[.\s])(?:reparto|elenco|m[uú]sicos|gui[oó]n|direcci[oó]n|producci[oó]n)\s*:|realizador y montajista)')
_RESTO = re.compile(r'(?i)(?:^|[.!?\n]\s*)(?:tr[aá]iler|v[ií]deos?|bastidores)\W*$|v[ií]deos?tr[aá]iler')
_ROTO = re.compile(r'¸|[\ufb01\ufb02\ufffd]|&[a-z]+;|</?[a-z]+>|[.!?]\s\d{1,3}$')
_CORTE = re.compile(r'[a-záéíóúñ]{2}- [a-záéíóúñ]{2}')


def plana(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(re.findall(r'\w+', s))


def huella(s):
    return hashlib.sha1(plana(s).encode()).hexdigest()[:12]


def defectos(s):
    ws = re.findall(r'[^\W\d_]+', (s or '').lower())
    n = max(1, len(ws))
    es, en, pt = (sum(w in S for w in ws) / n for S in (_ES, _EN, _PT))
    d = []
    if len(ws) >= 12 and en > es:
        d.append('en inglés')
    elif len(ws) >= 12 and pt > es * .9:
        d.append('en portugués')
    for rx, que in ((_EVENTO, 'habla del evento'), (_CREDITO, 'crédito de otra base'), (_FICHA, 'ficha técnica'),
                    (_RESTO, 'resto de página web'), (_ROTO, 'texto roto')):
        if rx.search((s or '').strip()):
            d.append(que)
    # palabra partida por la maquetación («Cris- tal»), no un inciso «-un anciano-»;
    # y las comas convertidas en punto y coma (la hoja de Popayán y Miradas)
    if 'texto roto' not in d and ((_CORTE.search(s or '') and ' -' not in (s or '')) or ((s or '').count(';') >= 3 and ',' not in s)):
        d.append('texto roto')
    if len(ws) < 4:
        d.append('demasiado corta')
    mayus = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+', s or '')
    if n >= 10 and len(mayus) / n > .6:
        d.append('parece una lista de nombres')
    return d


def decidir(actual, nueva, a_mano=False):
    """'entra' | 'mantener' | 'reemplazar' | 'revisar'."""
    if not (nueva or '').strip() or defectos(nueva):
        return 'mantener'
    if not (actual or '').strip():
        return 'entra'
    a, n = plana(actual), plana(nueva)
    if n in a:
        return 'mantener'
    if defectos(actual) or a in n:
        return 'revisar' if a_mano else 'reemplazar'
    return 'revisar'


def _almacen():
    import sys
    sys.path.insert(0, os.path.join(REPO, 'pipeline'))
    import catalogo
    return catalogo


def revisar(solo=None):
    """Sinopsis publicadas que no son la elegida → [(acción, título, festival, texto)]."""
    import glob
    cat = _almacen()
    dec = {d['work_id']: d for d in cat.decisiones() if d['campo'] == 'sinopsis.es'}
    out, vistos = [], set()
    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        d = json.load(open(p, encoding='utf-8'))
        if (solo and fid != solo) or not isinstance(d, dict):
            continue
        for f in d.get('films', []):
            for o in (f.get('film_list') or [f]):
                e, s = dec.get(o.get('work_id')), o.get('synopsis_es') or o.get('synopsis')
                if not e or not s:
                    continue
                h = huella(s)
                if h == huella(e['valor']) or h in (e.get('vistas') or []) or (o['work_id'], h) in vistos:
                    continue
                vistos.add((o['work_id'], h))
                out.append((decidir(e['valor'], s, e.get('a_mano', False)), o.get('title'), fid, s))
    return out


def aplicar(d, obs=None, decs=None):
    """La sinopsis elegida de cada obra, en el JSON del festival `d` (en el lugar).
    La usa publicar.py, y --aplicar sobre lo ya publicado: la misma función, para
    que un re-armado dé lo mismo. Una elegida vacía QUITA el texto (no había nada
    que contara la obra: lista de actores). → [(título, antes, después)]"""
    if decs is None:
        decs = _almacen().decisiones()
    eleg = {x['work_id']: x['valor'] for x in decs if x['campo'] == 'sinopsis.es'}
    out = []
    for f in d.get('films', []):
        for o in (f.get('film_list') or [f]):
            w = o.get('work_id')
            if w not in eleg or o.get('type') == 'event':
                continue
            # la app lee `synopsis_es` ANTES que `synopsis` (locSynopsis): si queda, tapa
            # la elegida. Olhar y Tribeca la traían (24 nov 2026: 67 sin cambiar a la vista)
            s, v = o.get('synopsis_es') or o.get('synopsis') or '', eleg[w]
            sobra = o.pop('synopsis_es', None) is not None
            if s == v and not sobra:
                continue
            out.append((o.get('title'), s, v))
            if v:
                o['synopsis'], o['synopsis_lang'] = v, 'es'
            else:
                o.pop('synopsis', None)
                o.pop('synopsis_lang', None)
    return out


def _guardar(p, d):
    """Respeta la forma del archivo (una línea o indentado)."""
    crudo = open(p, encoding='utf-8').read()
    if '\n' in crudo.strip():
        l = crudo.split('\n')[1]
        txt = json.dumps(d, ensure_ascii=False, indent=(len(l) - len(l.lstrip(' '))) or 1)
    else:
        txt = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(txt + ('\n' if crudo.endswith('\n') else ''))


def registrar(ruta):
    cat = _almacen()
    decs = cat.decisiones()
    ya = {d['work_id'] for d in decs if d['campo'] == 'sinopsis.es'}
    n = 0
    for e in json.load(open(ruta, encoding='utf-8')):
        if e['work_id'] not in ya:
            decs.append({**e, 'campo': 'sinopsis.es'})
            n += 1
    with open(os.path.join(cat.DIR, 'decisiones.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(decs, ensure_ascii=False, indent=1))
    return n


if __name__ == '__main__':
    import sys
    from collections import Counter
    if '--registrar' in sys.argv:
        print(registrar(sys.argv[sys.argv.index('--registrar') + 1]), 'sinopsis registradas')
    elif '--aplicar' in sys.argv:
        import glob
        solo = next((a for a in sys.argv[1:] if not a.startswith('--')), None)
        tot = 0
        for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
            if solo and os.path.basename(p) != f'{solo}.json':
                continue
            d = json.load(open(p, encoding='utf-8'))
            c = aplicar(d) if isinstance(d, dict) else []
            if c:
                print(f'{os.path.basename(p)[:-5]:22} {len(c)}')
                tot += len(c)
                if '--escribir' in sys.argv:
                    _guardar(p, d)
        print(tot, 'sinopsis' + ('' if '--escribir' in sys.argv else ' (solo muestra; --escribir para guardarlo)'))
    elif '--revisar' in sys.argv:
        xs = revisar(next((a for a in sys.argv[1:] if not a.startswith('--')), None))
        for a, t, fid, s in xs:
            if a != 'mantener':
                print(f'{a:10} «{t}» · {fid}: {s[:160]}')
        print(dict(Counter(x[0] for x in xs)))
    else:
        sys.exit(__doc__)
