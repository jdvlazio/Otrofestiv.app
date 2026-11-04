#!/usr/bin/env python3
"""Lo que no entra a la app: la app es para planear, así que una actividad
cerrada no se publica, y lo dejado fuera a propósito sigue fuera (Juan, 4 nov
2026, tras casi publicar el laboratorio de CINETORO, «solo para participantes
aceptados»).

Dos comprobaciones sobre las funciones que van a salir:
  · ninguna dice que es cerrada (no se mira la sinopsis: ahí puede contar otra cosa);
  · ninguna es algo de `_fuera` del crudo. Solo se comparan las entradas con título
    (clave de dict, o `titulo`/`que` de un registro): las de texto libre no se pueden
    cotejar sin falsos, porque una obra fuera un día puede estar en un día oficial.
    Si el registro trae `dia`, solo choca ese día.
"""
import json, os, re, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERRADA = re.compile(r'participantes aceptad|inscritos y aceptad|seleccionad[oa]s por convocatoria'
                     r'|convocatoria cerrada|evento exclusivo|evento para aliados'
                     r'|solo para (seleccionad|invitad)', re.I)
NO_SE_LEE = {'synopsis', 'synopsis_en', 'synopsis_pt', 'film_list', '_src'}
MIN_PREFIJO = 12    # un título más corto que esto solo choca completo


def _norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\W+', ' ', s).strip()


def _dejados(fuera):
    """[(título normalizado, día o None)] de las entradas de `_fuera` con título."""
    if isinstance(fuera, dict):
        return [(_norm(k), None) for k in fuera]
    out = []
    for x in fuera or []:
        if isinstance(x, dict) and (x.get('titulo') or x.get('que')):
            out.append((_norm(x.get('titulo') or x['que']), x.get('dia')))
    return out


def _mismo(a, b):
    if a == b:
        return True
    corto, largo = sorted((a, b), key=len)
    return len(corto) >= MIN_PREFIJO and largo.startswith(corto + ' ')


def revisar(films, fuera=None):
    errores = []
    dejados = _dejados(fuera)
    for f in films:
        rotulo = f"{f.get('day')} {f.get('time')} «{f.get('title')}»"
        visible = {k: v for k, v in f.items() if k not in NO_SE_LEE}
        m = CERRADA.search(json.dumps(visible, ensure_ascii=False))
        if m:
            errores.append(f'{rotulo}: actividad cerrada («{m.group()}»): no se puede planear, no entra')
        t = _norm(f.get('title', ''))
        for d, dia in dejados:
            if _mismo(t, d) and (not dia or dia == f.get('day')):
                errores.append(f'{rotulo}: está en `_fuera` del crudo: se dejó fuera a propósito')
    return errores


def revisar_festival(fest, films):
    ruta = os.path.join(REPO, 'festivals', 'staging', f'{fest}-crudo.json')
    fuera = None
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as a:
            fuera = json.load(a).get('_fuera')
    return revisar(films, fuera)
