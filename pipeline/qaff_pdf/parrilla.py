# -*- coding: utf-8 -*-
"""Los créditos que la PARRILLA imprime junto a cada obra: «(Director) - 12'44 - País».

Es una fuente distinta de la ficha: el festival los escribió dos veces, en dos
sitios del mismo PDF. Donde discrepan, hay que mirar —no elegir a ciegas."""
import re, sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'festivals', 'staging')
_ruta = lambda nom: os.path.join(STAGING, nom)
from limpia import paginas, limpia
import programa as pr

CRED = re.compile(r"^\(([^)]{2,80})\)\s*[-–]?\s*(\d{1,3})\s*['’]\s*(\d{1,2})?\s*(?:[-–]\s*(.+))?$")
# Cuando el nombre de los directores es largo, el festival parte el crédito en
# dos renglones: «(A, B)» y debajo «52'40 - Guadeloupe». Sin esta variante se
# pierden seis obras —y perderlas en silencio es lo peor que puede pasar aquí.
SOLO_DIR = re.compile(r"^\(([^)]{2,80})\)\s*$")
# el separador entre duración y país a veces es un guion, a veces una barra y a
# veces NADA: «52'40 Guadeloupe / 2025 – Documental». Exigirlo perdía una obra.
SOLO_DUR = re.compile(r"^(\d{1,3})\s*['’]\s*(\d{1,2})?\s*(?:[-–/]?\s*(.+))?$")
BY       = re.compile(r"^By\s+(.+?)\s+(\d{1,3})\s*['’]\s*(\d{1,2})?\s*[-–]\s*(.+)$")
# Las páginas de Cinemateca cierran cada obra con una línea propia:
# «Malawi / 2025 - Documental», «Estados Unidos / 2026 – Ficción». Ahí están el
# año y el tipo, y a veces el país que no cupo en la línea del crédito.
PAT = re.compile(r'^([A-Za-zÁÉÍÓÚÑáéíóúñ .\-]{3,40})\s*/\s*((?:19|20)\d{2})\s*[-–]?\s*(.*)$')
DUR  = re.compile(r"^(\d{1,3})\s*['’]\s*(\d{1,2})?\s*$")

def _cola(ls, j):
    """La línea «País / Año – Tipo» que va justo debajo del crédito."""
    if j + 1 >= len(ls):
        return {}
    m = PAT.match(ls[j + 1].strip())
    if not m:
        return {}
    out = {'anio': int(m.group(2))}
    if m.group(3).strip():
        out['tipo'] = m.group(3).strip()
    if m.group(1).strip():
        out['pais_cola'] = m.group(1).strip()
    return out


def creditos():
    P = {k: limpia(v) for k, v in paginas().items()}
    out = {}
    for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
        # Una función puede declarar DOS páginas: el Museo Nacional y la
        # Universidad Nacional no tienen parrilla, así que su día sale del sello
        # de la ficha y su hora de la página del Diálogo de ese mismo día.
        # verifica.py ya lo contemplaba; esto no, y reventaba con un KeyError en
        # cuanto se corría suelto. No se notó porque el crudo importa presencias()
        # y nunca llegaba hasta aquí: lo destapó correr.py al ejecutar el paso.
        ls = [l for q in (pag if isinstance(pag, tuple) else (pag,)) for l in P[str(q)]]
        for o in obras:
            # el crédito es la línea siguiente al título (a veces la subsiguiente,
            # cuando el nombre de la obra ocupa dos renglones)
            idx = [i for i, l in enumerate(ls) if l.upper().startswith(o.upper()[:22])]
            for i in idx:
                for j in (i + 1, i + 2):
                    if j >= len(ls): break
                    m = CRED.match(ls[j]) or BY.match(ls[j])
                    if m:
                        out.setdefault(o, []).append(
                            {'director': m.group(1).strip(), 'duracion_min': int(m.group(2)),
                             'pais': (m.group(4) or '').strip() or None, '_pagina': pag,
                             **_cola(ls, j)})
                        break
                    md = SOLO_DIR.match(ls[j])
                    if md and j + 1 < len(ls):
                        mu = SOLO_DUR.match(ls[j + 1])
                        if mu:
                            out.setdefault(o, []).append(
                                {'director': md.group(1).strip(),
                                 'duracion_min': int(mu.group(1)),
                                 'pais': (mu.group(3) or '').split('/')[0].strip() or None,
                                 '_pagina': pag, **_cola(ls, j + 1)})
                            break
                else:
                    continue
                break
    return out

if __name__ == '__main__':
    import json, collections
    c = creditos()
    todas = {o for f in pr.FUNCIONES for o in f[4]}
    print(f'obras distintas en parrilla: {len(todas)} · con crédito leído: {len(c)}')
    faltan = sorted(todas - set(c))
    if faltan:
        print('\nsin crédito en la parrilla:')
        for f in faltan: print('   ', f)
    # ¿el mismo título con créditos distintos en páginas distintas?
    for t, v in c.items():
        for k in ('director', 'duracion_min'):
            vals = {str(x[k]).upper() for x in v}
            if len(vals) > 1:
                print(f'  ⚠ «{t}» difiere en {k} entre páginas {[x["_pagina"] for x in v]}: {vals}')
    json.dump({'_provenance': {
        'fuente': 'créditos impresos junto a cada obra en las parrillas del PDF oficial '
                  'del programa QAFF 2026',
        'capturado': datetime.date.today().isoformat(),
        'metodo': 'capa de texto del PDF, no OCR; «(Director) - 12\'44 - País» y la línea '
                  '«País / Año – Tipo» que la sigue'},
        'obras': c}, open(_ruta('qaff-2026-bogota-creditos-parrilla.json'), 'w'),
        ensure_ascii=False, indent=1)


# ── invitados en sala ───────────────────────────────────────────────────────
PRES = re.compile(r'(?i)(?:con la |^\+\s*\()?presencia (de|del)\s+(?:la\s+)?'
                  r'(directora|director|guionista|guinista|protagonista)')

def presencias():
    """«con la presencia de la directora» va pegada a UNA obra de la parrilla.
    Para la app eso es Q&A, y el flag vive en la función, no en la obra: hay que
    saber a qué franja pertenece la obra marcada. Se resuelve por la página y
    por la lista de obras de cada función, y se EXIGE que cada marca caiga en
    una sola función —si cayera en dos, el dato sería una conjetura."""
    P = {k: limpia(v) for k, v in paginas().items()}
    out, huerfanas = {}, []
    for pag, ls in P.items():
        for i, l in enumerate(ls):
            m = PRES.search(l)
            if not m:
                continue
            quien = {'guinista': 'guionista'}.get(m.group(2).lower(), m.group(2).lower())
            # el título es esta misma línea (cuando la marca va pegada, «CAIDA
            # LIBRE + (Presencia del director)») o la última línea de arriba que
            # no sea un crédito entre paréntesis
            aqui = re.sub(r'\s*\+?\s*\(?\s*(?:con la\s+)?presencia\s+de.*$', '', l, flags=re.I).strip()
            titulo = aqui if aqui else None
            if not titulo:
                for j in range(i - 1, max(i - 6, -1), -1):
                    t = ls[j].strip()
                    if t and not t.startswith('(') and not re.match(r'^[\d\W]+$', t):
                        titulo = t; break
            cand = [(s, sa, d, h) for s, sa, d, h, obras, p in pr.FUNCIONES
                    if p == int(pag) and any(o.upper() == (titulo or '').upper() for o in obras)]
            if len(cand) == 1:
                out.setdefault(cand[0], set()).add((quien, titulo))
            else:
                huerfanas.append((pag, titulo, quien, len(cand)))
    return out, huerfanas
