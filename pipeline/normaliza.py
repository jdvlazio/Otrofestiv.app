#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normaliza.py — escribir bien lo que ya se sabe: país, género, dirección, año y duración.

Hermano de ficha_obra.py (que dice qué es válido): acá, cómo se lleva lo que
imprimió el festival a la forma de la lista, SIN agregar información. Lo que no
se reconoce se deja igual —lo frena ficha_obra— o, si es un género que no dice
género, se quita (Juan, 24 nov 2026: «Ficción», formatos VR/IA y secciones: el de
su ficha verificada, y si no, vacío). Una sola función, la misma para publicar.py
y para lo ya publicado (ficha_unica.aplicar).
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import ficha_obra  # noqa: E402

_P = None


def _mapa():
    global _P
    if _P is None:
        d = json.load(open(os.path.join(REPO, 'pipeline', 'paises.json'), encoding='utf-8'))
        iso = {v['flag']: k for k, v in d['iso'].items() if k not in ficha_obra.NO_PAIS}
        _P = ({n: iso[f] for n, f in d['paises'].items() if f in iso}, {k: ficha_obra.NOMBRE.get(k, v['es']) for k, v in d['iso'].items()})
    return _P


# lo que los festivales escriben y la tabla no trae; None = no es un país, se quita
_ALIAS = {'eeuu': 'US', 'ee uu': 'US', 'usa': 'US', 'us': 'US', 'uk': 'GB', 'inglaterra': 'GB', 'escocia': 'GB', 'rd congo': 'CD',
          'democratic republic of congo': 'CD', 'macedonia': 'MK', 'rep dominicana': 'DO', 'republic of korea': 'KR', 'south korea': 'KR',
          'palestina': 'PS', 'hong kong': 'HK', 'republica checa': 'CZ', 'rumania': 'RO', 'arabia saudita': 'SA', 'bangladesh': 'BD',
          'turkiye': 'TR', 'federacion rusa': 'RU', 'qatar': 'QA', 'canarias': None, 'barranquilla': None, 'cataluna': None,
          'mekelle': None, 'tigray': None, 'wukro': None, 'costa de marfil': 'CI', 'ivory coast': 'CI', 'japon': 'JP'}


def _clave(s):
    from lib import norm
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', norm(s or ''))).strip()


def _un_pais(t):
    """→ nombre | '' (no es un país: se quita) | None (no se reconoce)."""
    if t in ficha_obra.HISTORICOS or t in ficha_obra.paises():
        return t
    k = _clave(t)
    m, nombre = _mapa()
    if k in _ALIAS:
        return nombre[_ALIAS[k]] if _ALIAS[k] else ''
    return nombre[m[k]] if k in m else None


def pais(c):
    """«Canadá/Colombia», «USA», «. Italia» → «Canadá, Colombia»… Todo o nada."""
    if not isinstance(c, str) or not c.strip():
        return c
    if _clave(c) in ('varios', 'varios paises', 'internacional'):
        return None                       # no nombra un país
    out = []
    for parte in re.split(r'[,/()]', c):
        parte = parte.strip(' .​\n')
        if not parte:
            continue
        p = _un_pais(parte)
        if p is None:
            sub = [x for x in re.split(r'\s+y\s+|\s+and\s+|\s*[-–—]\s*', parte) if x.strip()]
            r = [_un_pais(x.strip()) for x in sub]
            if len(sub) < 2 or None in r:
                return c
            out += r
        else:
            out.append(p)
    return ', '.join(dict.fromkeys(x for x in out if x)) or c


_GENERO = {'ficción': None, 'ficcion': None, 'thriller': 'Suspenso', 'thiller': 'Suspenso', 'suspense': 'Suspenso', 'sátira': 'Comedia',
           'familiar': 'Familia', 'película de tv': None, 'documentary': 'Documental', 'documentales': 'Documental', 'history': 'Historia',
           'comedy': 'Comedia', 'science fiction': 'Ciencia ficción', 'crime': 'Crimen', 'action': 'Acción', 'horror': 'Terror', 'war': 'Bélica',
           'music': 'Música', 'animation': 'Animación', 'mystery': 'Misterio', 'fábula': 'Fantasía', 'realismo mágico': 'Fantasía',
           'docu-ficción': 'Documental híbrido', 'docuficción': 'Documental híbrido', 'wéstern': 'Western', 'thriller político': 'Suspenso',
           'thriller psicológico': 'Suspenso', 'drama biográfico': 'Drama', 'documental biográfico': 'Documental', 'drama histórico': 'Drama',
           'cinedanza': 'Experimental', 'videodanza': 'Experimental', 'video-ensayo ia': 'Experimental', 'ciencia ficción ia': 'Ciencia ficción',
           'coming-of-age': 'Drama', 'ficción ia': None, 'ai': None, 'vr': None, 'vr 360': None, 'vr interactivo': None, '2d': None,
           'eco corto': None, 'ventana regional': None, 'siembra cine': None, 'naturaleza': None, 'ficción — drama': 'Drama', 'drama social': 'Drama'}
_FORMA = ('Animación', 'Documental híbrido', 'Documental')      # la técnica o el registro manda sobre el tono


def genero(g):
    """→ un género de la lista, o None si lo impreso no dice ninguno. Lo no reconocido, igual."""
    if not isinstance(g, str) or not g.strip():
        return g
    if g in ficha_obra.GENEROS:
        return g
    lista = {x.lower(): x for x in ficha_obra.GENEROS}
    k = g.strip().lower()
    if k in lista:
        return lista[k]
    if k in _GENERO:
        return _GENERO[k]
    out = []
    for parte in re.split(r'\s*(?:,|/| — | y )\s*', k):
        if parte in lista:
            out.append(lista[parte])
        elif parte in _GENERO:
            out.append(_GENERO[parte])
        elif not out:
            return g                      # ni la primera palabra se reconoce
    out = [x for x in out if x]
    if not out:
        return None
    if 'Documental' in out and 'Drama' in out and out[0] != 'Documental':
        return 'Documental'
    return next((x for x in out if x in _FORMA), out[0])


# con «:» o «.» siempre; sin signo, solo las palabras que no son un apellido
_CARGO = re.compile(r'(?i)^(?:(?:direcci[oó]n|dirigid[oa]s? por|dir|director[ae]?s?)\s*[:.]\s*|(?:direcci[oó]n|dirigid[oa]s? por)\s+)')


# créditos que ninguna regla general escribe bien
_EXACTO = {'Alunos e alunas da Escola Municipal João Victor, Lagoa Nova/RN e Equipe Animazul, Vitória/ES -': 'Escola Municipal João Victor, Equipe Animazul',
           'Jerónimo Vergara (gerome)': 'Jerónimo Vergara', 'Estudiantes IE Nueva Generación (Sáchica, Boyacá)': 'Estudiantes IE Nueva Generación',
           'Taller de usos críticos de archivos sonoros y audiovisuales (MIDBO) - Creación colectiva': 'Taller de usos críticos de archivos sonoros y audiovisuales',
           '@watchingyoulab + creaciones poéticas de procesos de memoria participantes + freestyle': 'Watching You Lab',
           'Sean Ono Lennon and co-directed by Brian Gonzalez': 'Sean Ono Lennon, Brian Gonzalez'}


def director(d):
    if not isinstance(d, str) or not d.strip():
        return d
    if d.strip() in _EXACTO:
        return _EXACTO[d.strip()]
    if re.fullmatch(r'(?i)varios|varias|n/?a|por confirmar', d.strip()):
        return None                       # no nombra a nadie
    d = _CARGO.sub('', re.sub(r'\s+', ' ', d).strip())
    guarda = {f'\0{i}\0': n for i, n in enumerate(ficha_obra.NOMBRE_COMPUESTO) if n in d}
    for k, n in guarda.items():
        d = d.replace(n, k)
    d = re.sub(r',?\s+(?:y|e|and|&|\+|[-–])\s+', ', ', d)
    d = re.sub(r'\s*[/;|]\s*|\s+·\s+', ', ', d)
    d = re.sub(r'\s*,\s*', ', ', d).strip(' ,')
    for k, n in guarda.items():
        d = d.replace(k, n)
    vistos = [x for x in dict.fromkeys(d.split(', ')) if x]
    d = ', '.join(vistos)
    return re.sub(r'(?<=[a-záéíóúñ]{3})\.$', '', d)


def anio(y):
    return int(y) if isinstance(y, str) and re.fullmatch(r'\s*\d{4}\s*', y) else y


def duracion(u):
    if isinstance(u, int) and not isinstance(u, bool) and 0 < u <= 900:
        return f'{u} min'
    m = re.fullmatch(r"\s*~?\s*(\d{1,3})\s*(?:min|mins|minutos|'|’)?\.?\s*", u) if isinstance(u, str) else None
    # «~» es «estimada» y la app lo lee (durEstimada): se conserva
    return f"{'~' if '~' in u else ''}{int(m.group(1))} min" if m and int(m.group(1)) else u


CAMPOS = {'country': pais, 'genre': genero, 'director': director, 'year': anio, 'duration': duracion}


def normalizar(o):
    """En el lugar. → [(campo, antes, después)]; después None = se quita."""
    out = []
    for k, f in CAMPOS.items():
        if o.get(k) in (None, ''):
            continue
        v = f(o[k])
        if v != o[k] or type(v) is not type(o[k]):
            out.append((k, o[k], v))
            if v is None:
                o.pop(k)
            else:
                o[k] = v
            if k == 'country':
                from lib import banderas
                b = banderas(v or '')
                if b:
                    o['flags'] = b
    return out
