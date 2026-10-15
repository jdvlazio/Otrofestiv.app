#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""herencia.py — QUÉ se hereda del catálogo, en un solo lugar (15 oct 2026).

Lo usan los dos caminos que llenan una obra con lo que el catálogo ya sabe:
  · enriquecer.py, al montar un festival con el pipeline;
  · heredar.py, sobre el JSON PUBLICADO de un festival que no tiene pipeline
    (los montados a mano antes de la v2: FICMontañas, Cinemancia 2025…).
Dos copias de estas reglas divergirían (memoria «tabla generada, no dos a
mano»): por eso las dos llaman a `valor()`.

Cada campo se hereda SOLO si el catálogo da UN valor: con dos géneros distintos
o dos títulos en inglés, heredar uno sería elegir por los festivales.
"""
import os

from lib import norm, tmdb_get

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# campo del enriquecido → campo publicado
CAMPOS = {'genero': 'genre', 'title_en': 'title_en', 'lbSlug': 'lbSlug', 'anio': 'year',
          'synopsis_es': 'synopsis', 'synopsis_en': 'synopsis_en', 'poster': 'poster'}


def _uno(xs):
    xs = [x for x in dict.fromkeys(xs) if x]
    return xs[0] if len(xs) == 1 else None


_VALOR = {
    'genero': lambda w: _uno(w.get('generos') or []),
    'title_en': lambda w: _uno(a['titulo'] for a in w.get('aliases') or [] if a.get('idioma') == 'en'),
    'lbSlug': lambda w: (w.get('xref') or {}).get('letterboxd'),
    'anio': lambda w: w.get('anio'),
    # LA SINOPSIS (14 oct 2026): «Bertha» salió sin sinopsis en BIFF con la de
    # QAFF publicada; es texto que ya pasó por un montaje
    'synopsis_es': lambda w: (w.get('sinopsis') or {}).get('es'),
    'synopsis_en': lambda w: (w.get('sinopsis') or {}).get('en'),
    # EL AFICHE: nunca un fotograma (veredicto del catálogo)
    'poster': lambda w: (w.get('afiche') or {}).get('archivo')
              if (w.get('afiche') or {}).get('veredicto') != 'fotograma' else None,
}


def afiche_ajeno_vale(ruta_web):
    """Un afiche de OTRO festival nuestro ¿es un afiche? (pipeline/afiche_criterio.py):
    ni tarjeta de solo texto ni la tarjeta de sección que ese festival diseñó."""
    from afiche_criterio import veredicto
    from ocr import leer
    r = REPO + ruta_web
    return veredicto(r, ' '.join(leer([r]).get(r, [])), ajena=True) is None


def valor(w, campo, fid, titulo, tmdb_id=None, key=None):
    """Lo que el catálogo da para `campo` de la obra `w` en el festival `fid`,
    o None si no hay un valor único que valga. No mira lo que la presentación
    ya tiene: eso lo decide cada camino (la fuente manda, lo publicado manda)."""
    # LA SINOPSIS NO SE HEREDA DE SÍ MISMA (14 oct 2026): si el único festival
    # que publicó la obra es este, su sinopsis del catálogo es la propia (Itagüí
    # recibía su nota de invitados y la duplicaba). Letterboxd y afiche propios
    # SÍ vuelven: son lo publicado tal cual
    if campo in ('synopsis_es', 'synopsis_en') and set(w.get('presentaciones') or []) <= {fid}:
        return None
    v = _VALOR[campo](w)
    if not v:
        return None
    # EL AFICHE AJENO: que no sea el de este festival de vuelta, que exista en
    # disco, y que SEA un afiche (afiche_criterio)
    if campo == 'poster':
        _v = str(v)
        if _v.startswith(f'/assets/{fid}/') or (_v.startswith('/assets/') and (
                not os.path.exists(REPO + _v) or not afiche_ajeno_vale(_v))):
            return None
    if campo == 'title_en':
        # un title_en igual al título no es un título en inglés
        if norm(v) == norm(titulo):
            return None
        # CON FICHA DE TMDB, el inglés lo dice TMDB (Cinemancia 2026 publicó un
        # título viejo en caché): se hereda solo si coincide
        if tmdb_id:
            _en = (tmdb_get(f'/movie/{tmdb_id}', key, language='en-US') or {}).get('title') or ''
            if norm(v) != norm(_en):
                return None
    return v


def poster_source(w, v):
    """La procedencia de un afiche heredado."""
    _ver = (w.get('afiche') or {}).get('veredicto')
    return 'tmdb' if 'image.tmdb.org' in str(v) else 'custom' if _ver == 'oficial-festival' else 'oficial'
