#!/usr/bin/env python3
"""cinecorto.py — la ficha de un corto colombiano en cinecorto.co.

cinecorto.co es el catálogo del cortometraje colombiano que mantiene el
Festival de Cine Corto de Popayán. Da lo que TMDB casi nunca tiene de un corto
colombiano reciente: AÑO, DURACIÓN y SINOPSIS, con los créditos completos.
Nació dentro del catálogo de Popayán (28 sep 2026) y sale acá porque sirve a
cualquier festival: en Mamut era la única fuente de «These are not our
memories».

EL CANDADO ES LA DIRECCIÓN, como en TMDB y Proimágenes: un título igual con otra
dirección es otra obra. No trae afiches: sus imágenes son fotogramas, y un
fotograma no es un afiche.

TRES TRAMPAS MEDIDAS en sus fichas (las encontró Popayán):
  · la etiqueta del director cambia: «Dirección», «Director», «Directora»…;
  · la duración viene como «7», «7 min» o «17:32 min»;
  · algunas fichas traen el JSON-LD de SEO DENTRO del contenido, y era el
    «párrafo largo» que se tomaba por sinopsis.
"""
import html
import json
import re
import time
import urllib.parse
import urllib.request

from lib import director_coincide, norm

API = 'https://cinecorto.co/wp-json/wp/v2'
UA = 'Mozilla/5.0 Otrofestiv'


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
        except Exception:
            time.sleep(1)
    return None


def _campo(t, etiqueta):
    m = re.search(rf'\n{etiqueta}\s*\n\s*([^\n]*)', t)
    return m.group(1).strip() if m else ''


def ficha(titulo, director):
    """→ {url, direccion, anio, duracion_min, categoria, sinopsis, sinopsis_en} o None."""
    res = _get(f'{API}/search?search={urllib.parse.quote(titulo)}&subtype=post&per_page=10') or []
    for r in res:
        if norm(html.unescape(r.get('title', ''))) != norm(titulo):
            continue
        post = _get(f'{API}/posts/{r["id"]}?_fields=content,link')
        if not post:
            continue
        cuerpo = re.sub(r'<script.*?</script>', '', post['content']['rendered'], flags=re.S)
        t = '\n' + re.sub(r'\n\s*\n+', '\n', html.unescape(re.sub(r'<[^>]+>', '\n', cuerpo)))
        d_cc = _campo(t, '(?:Dirección|Directora?e?s?|Dirigid[oa] por)')
        if not director_coincide(director, [d_cc]):
            continue
        anio = _campo(t, 'Año')
        m = re.match(r'(\d+)', _campo(t, 'Duración'))
        sinopsis = sinopsis_en = ''
        for linea in t.split('Selecciones y premios')[0].split('\n'):
            linea = linea.strip()
            if len(linea) < 120:
                continue
            w = f' {norm(linea)} '
            es = sum(w.count(f' {x} ') for x in ('el', 'la', 'de', 'que', 'y', 'en', 'los', 'su', 'una'))
            en = sum(w.count(f' {x} ') for x in ('the', 'and', 'of', 'to', 'her', 'his', 'is', 'with', 'a'))
            if es >= en and not sinopsis:
                sinopsis = linea
            elif en > es and not sinopsis_en:
                sinopsis_en = linea
        return {'url': post['link'], 'direccion': d_cc,
                'anio': int(anio[:4]) if anio[:4].isdigit() else None,
                'duracion_min': int(m.group(1)) if m else None,
                'categoria': _campo(t, 'Categoría'),
                'sinopsis': sinopsis, 'sinopsis_en': sinopsis_en}
    return None
