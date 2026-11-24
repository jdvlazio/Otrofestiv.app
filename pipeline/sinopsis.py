# -*- coding: utf-8 -*-
"""sinopsis.py — NINGUNA OBRA SIN SINOPSIS EN ESPAÑOL EN SILENCIO (19 nov 2026).

Pedido de Juan: «Deberíamos poner un guardián para las sinopsis. Que haga
búsqueda exhaustiva y que en caso tal traduzca. Solo en casos extremos, dejarla
sin sinopsis.» CUAFF salió con 0 de 14 sinopsis en español aunque la
Cinemateca las publica en cada ficha, y nada lo frenó.

Dueño único de la regla; la consultan publicar.py (frena al publicar) y
validate.py [sinopsis-cobertura] (vigila lo publicado). Mismo patrón que
`sin_afiche`:

· Alcance: OBRAS —películas y las obras dentro de un programa—, no
  actividades (talleres, conversatorios): su título ya dice qué son, y
  exigirles sinopsis llenaría la lista de excepciones sin aportar nada.
  Decisión de Juan, 19 nov.
· Una obra sin `synopsis` en español queda PENDIENTE, con su acción:
    traducir → hay sinopsis en otro idioma (synopsis_en); se traduce con el
               contexto de la obra, no a ciegas.
    buscar   → no hay ninguna; se recorre la CASCADA de abajo.
· Dejarla sin sinopsis exige declararlo en `sin_sinopsis` de
  festivals/staging/<id>-correcciones.json, por título de obra o de su
  programa: {"_por_que": "...", "fuentes": ["ficha de la sala", "TMDB", ...]}.
  Sin porqué o sin fuentes revisadas, la declaración no cuenta.
· DEUDA CONGELADA: lo ya publicado sin sinopsis el 19 nov 2026 está en
  pipeline/sinopsis-deuda.json (pendientes por festival, con el nombre de su
  archivo: aleste-2026, el mismo id que usan publicar.py y las correcciones). Ese número solo
  puede bajar. Un festival que no está ahí parte de cero.

· UNA SINOPSIS DEFECTUOSA CUENTA COMO SI NO ESTUVIERA (23 nov 2026, Juan: «un
  error gigante que debemos corregir con un guardián muy serio»). Este guardián
  solo miraba que HUBIERA texto, y pasaron publicadas la lista de actores
  (Popayán leyó la columna equivocada), enlaces de compra (la web de Ficcali,
  heredados a tres festivales), un texto acreditado a FilmAffinity (estaba así en
  TMDB), inglés, portugués y conversatorios. La regla la da
  sinopsis_unicas.defectos(); la acción es `corregir`. Un falso positivo se
  declara en `sinopsis_revisada` de -correcciones.json con su `_por_que`.

CASCADA de búsqueda (en orden; la sinopsis del festival manda porque es la
que el público lee en el programa):
  1. la ficha de la obra en la web de la sala o del festival
  2. TMDB en español        (el enriquecido ya la trae si existe)
  3. TMDB en inglés         (→ traducir)
  4. FilmFreeway / Festhome
  5. la web o las redes del director o la productora

    python3 pipeline/sinopsis.py <id>             # pendientes de un festival, con su acción
    python3 pipeline/sinopsis.py --todos          # resumen de todos los publicados
    python3 pipeline/sinopsis.py --congelar       # reescribe la deuda (solo si BAJÓ)
"""
import glob, json, os, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEUDA = os.path.join(REPO, 'pipeline', 'sinopsis-deuda.json')
CASCADA = ('ficha de la sala o del festival', 'TMDB en español', 'TMDB en inglés',
           'FilmFreeway / Festhome', 'web del director o la productora')


def _n(s):
    s = unicodedata.normalize('NFD', str(s or '')).lower()
    return ''.join(c for c in s if c.isalnum())


def _es(o):
    return str(o.get('synopsis') or o.get('synopsis_es') or '').strip()


def _otro(o):
    return str(o.get('synopsis_en') or '').strip()


def revisadas(fid, raiz=REPO):
    """`sinopsis_revisada`: textos que el detector marca y una persona leyó."""
    p = os.path.join(raiz, 'festivals', 'staging', f'{fid}-correcciones.json')
    if not os.path.exists(p):
        return set()
    v = (json.load(open(p, encoding='utf-8')) or {}).get('sinopsis_revisada') or {}
    return {_n(k) for k, x in v.items() if isinstance(x, dict) and str(x.get('_por_que') or '').strip()}


def declaradas(fid, raiz=REPO):
    """`sin_sinopsis` del festival → {título normalizado: entrada}. Solo cuentan
    las que traen porqué Y fuentes revisadas."""
    p = os.path.join(raiz, 'festivals', 'staging', f'{fid}-correcciones.json')
    if not os.path.exists(p):
        return {}
    out = {}
    for k, v in ((json.load(open(p, encoding='utf-8')) or {}).get('sin_sinopsis') or {}).items():
        if not isinstance(v, dict):
            continue
        fuentes = [x for x in (v.get('fuentes') or []) if str(x).strip()]
        if str(v.get('_por_que') or '').strip() and fuentes:
            out[_n(k)] = v
    return out


def obras(films):
    """(obra, programa|None) por cada obra única. Las actividades no cuentan."""
    vistas = set()
    for f in films or []:
        if f.get('event_kind') or f.get('type') == 'event':
            continue
        inner = [o for o in (f.get('film_list') or []) if isinstance(o, dict)]
        for o in (inner or [f]):
            t = o.get('title')
            if not t or _n(t) in vistas:
                continue
            vistas.add(_n(t))
            yield o, (f if inner else None)


def pendientes(fid, films, raiz=REPO):
    """Obras sin sinopsis en español y sin declaración → [{titulo, programa, accion}]."""
    from sinopsis_unicas import defectos
    dec, rev = declaradas(fid, raiz), revisadas(fid, raiz)
    out = []
    for o, prog in obras(films):
        if _es(o):
            ds = [] if _n(o['title']) in rev else defectos(_es(o))
            if ds:
                out.append({'titulo': o['title'], 'programa': prog.get('title') if prog else None,
                            'accion': 'corregir', 'defectos': ds})
            continue
        if _n(o['title']) in dec or (prog is not None and _n(prog.get('title')) in dec):
            continue
        out.append({'titulo': o['title'], 'programa': prog.get('title') if prog else None,
                    'accion': 'traducir' if _otro(o) else 'buscar'})
    return out


def deuda():
    if not os.path.exists(DEUDA):
        return {}
    return {k: v for k, v in json.load(open(DEUDA, encoding='utf-8')).items() if not k.startswith('_')}


def excede(fid, films, raiz=REPO):
    """(pendientes, techo) si el festival tiene MÁS pendientes que su deuda congelada;
    None si está dentro. Un festival sin deuda registrada tiene techo 0."""
    p = pendientes(fid, films, raiz)
    techo = deuda().get(fid, 0)
    return (p, techo) if len(p) > techo else None


def linea(x):
    prog = f' (en «{x["programa"][:30]}»)' if x.get('programa') else ''
    if x['accion'] == 'corregir':
        return f'«{x["titulo"][:50]}»{prog} — corregir: ' + ', '.join(x['defectos'])
    verbo = 'traducir: hay sinopsis en inglés' if x['accion'] == 'traducir' else 'buscar: ' + ' → '.join(CASCADA)
    return f'«{x["titulo"][:50]}»{prog} — {verbo}'


def _publicados():
    for p in sorted(glob.glob(os.path.join(REPO, 'festivals', '*.json'))):
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get('films'), list):
            yield os.path.basename(p)[:-5], d['films']


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] in ('--todos', '--congelar'):
        conteo = {}
        for nombre, films in _publicados():
            n = len(pendientes(nombre, films))
            if n:
                conteo[nombre] = n
        if a[0] == '--todos':
            for fid, n in sorted(conteo.items()):
                print(f'{fid:28} {n:4}  (techo {deuda().get(fid, 0)})')
            print(f'TOTAL {sum(conteo.values())}')
            sys.exit(0)
        viejo = deuda()
        subio = {k: (viejo.get(k, 0), v) for k, v in conteo.items() if v > viejo.get(k, 0)}
        if viejo and subio and '--nueva-regla' not in a:
            sys.exit('✗ la deuda solo baja; subió en: ' +
                     ', '.join(f'{k} {a_}→{b_}' for k, (a_, b_) in subio.items()))
        json.dump({'_nota': 'Obras publicadas sin sinopsis en español y sin `sin_sinopsis`, '
                            'por festival. Solo baja (pipeline/sinopsis.py).', **conteo},
                  open(DEUDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        print(f'deuda congelada: {sum(conteo.values())} en {len(conteo)} festivales')
        sys.exit(0)
    nombre = a[0]
    p = os.path.join(REPO, 'festivals', f'{nombre}.json')
    if not os.path.exists(p):
        sys.exit(f'✗ no existe {p} (usar el nombre del archivo: aleste-2026)')
    pend = pendientes(nombre, json.load(open(p, encoding='utf-8'))['films'])
    for x in pend:
        print('·', linea(x))
    print(f'{len(pend)} pendiente(s) · techo {deuda().get(nombre, 0)}')
