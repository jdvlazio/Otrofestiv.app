#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""caja.py — programas y secciones en Título (regla de Juan, 15 oct 2026).

«Muestra de Cortos», «Selección Oficial de Cortometrajes Latinoamericanos»,
«Colombia Viva». Las PALABRAS son del festival (secciones tal cual); la CAJA es
de la app. La RAE (Ortografía 2010) pide mayúscula en las palabras con peso de
los nombres de eventos, certámenes y colecciones, y solo en la primera palabra
de los títulos de obras: por eso una sección o un programa va en Título y una
obra no se toca nunca —tampoco las uniones «Obra + Obra», que son títulos—.

Un solo dueño: lo usan ensamblar.py (cada montaje sale en Título),
caja-titulo.py (lo ya publicado) y validate.py [caja-titulo] (que no vuelva).
"""
import re

# conectores: van en minúscula salvo al comienzo (o tras «:», «—», «·», «(»…)
MENORES = {'de', 'del', 'la', 'las', 'el', 'los', 'y', 'e', 'o', 'u', 'en', 'a', 'al', 'con', 'por',
           'para', 'sin', 'sobre', 'entre', 'que', 'lo', 'un', 'una', 'unos', 'unas', 'es', 'son',
           'se', 'su', 'sus', 'como', 'si', 'me', 'te', 'mi', 'mis', 'tu', 'tus', 'ni', 'desde',
           'hasta', 'hacia', 'tras', 'ante', 'bajo',
           # palabras de otro idioma dentro de un nombre en español
           'of', 'the', 'and', 'in', 'on', 'at', 'for', 'to', 'by', 'du', 'des'}
# nombres propios que su dueño escribe en minúscula
MARCAS = {'ojoboca'}
# festivales en otro idioma: su caja tiene otras reglas (com, na, by…)
OTRO_IDIOMA = {'olhar-2026', 'tribeca-2026', 'tiff-2026'}
_CORTE = set(':·—–.¿¡(/')
_EMOJI = re.compile(r'^[^\wÁÉÍÓÚÑ¿¡(«"\']+\s*')


def titulo(s):
    """La caja de Título de un nombre de programa o de sección."""
    out, prim = [], True
    for tok in re.split(r'(\s+)', s):
        if not tok.strip():
            out.append(tok)
            continue
        pre, w, post = re.match(r"^([¿¡(«\"']*)(.*?)([.,:;!?)»\"'…]*)$", tok).groups()
        if pre and any(c in _CORTE for c in pre):
            prim = True
        if (w and w not in MARCAS and re.fullmatch(r"[a-záéíóúñü][a-záéíóúñü'’]*", w)
                and (prim or w not in MENORES)):
            w = w[0].upper() + w[1:]
        out.append(pre + w + post)
        # «Prog.» es abreviatura, no fin de frase
        prim = ((any(c in _CORTE for c in post) and not (post == '.' and w.lower() == 'prog'))
                or w in ('—', '–', '·', '/', '+'))
    return ''.join(out)


def seccion(s):
    """La sección publicada lleva emoji delante: se titula lo que sigue."""
    m = _EMOJI.match(s or '')
    pre = m.group() if m else ''
    return pre + titulo((s or '')[len(pre):]) if s else s


def es_titulo_de_obra(f):
    """¿El «programa» es en realidad el título de una obra o la unión de varias
    («Esperando abril + Los bandidos del hotel azul»)? Entonces no se toca."""
    obras = [o.get('title', '') for o in f.get('film_list') or []]
    if f.get('title') in obras:
        return True
    partes = [p.strip() for p in re.split(r'\s\+\s', f.get('title') or '')]
    return len(partes) > 1 and all(any(p == o or p in o for o in obras) for p in partes)


def es_programa(f):
    return bool(f.get('is_cortos') or f.get('is_programa')) and not es_titulo_de_obra(f)


def fuera_de_caja(d, fid):
    """[(qué, hoy, debería)] — lo que en un festival publicado no está en Título."""
    if fid in OTRO_IDIOMA:
        return []
    out, vis = [], set()
    for f in d.get('films') or []:
        if es_programa(f) and titulo(f['title']) != f['title'] and f['title'] not in vis:
            vis.add(f['title'])
            out.append(('programa', f['title'], titulo(f['title'])))
    for s in list((d.get('sections') or {}).keys()) + [f.get('section') for f in d.get('films') or []]:
        if s and seccion(s) != s and s not in vis:
            vis.add(s)
            out.append(('sección', s, seccion(s)))
    return out
