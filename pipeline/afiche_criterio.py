# -*- coding: utf-8 -*-
"""afiche_criterio.py — DUEÑO ÚNICO de «¿esta imagen es un afiche?».

POR QUÉ EXISTE (7 oct 2026). Una auditoría de lo publicado encontró 10 imágenes
que no eran afiches en festivales en producción, y ninguna la vio un validador:
  · 9 TARJETAS DE SECCIÓN de SiembraFest («Sección | Programa I · Muertos de
    risa», laurel «Siembra Fest») heredadas por FILCMAR, Fantasmagoría,
    Girardota y Popayán, porque el enriquecido reusa lo ya publicado en otro
    festival nuestro y SiembraFest las había marcado `oficial`;
  · 1 TARJETA DE SOLO TEXTO («La libertad doble»: un rectángulo verde con el
    título) que TMDB tiene como su afiche en español; las otras tres de esa
    ficha son afiches de verdad.
Las etiquetas de origen no sirven para decidir: dicen `oficial` en una tarjeta,
`tmdb` en un rectángulo verde y `custom` en afiches reales. Decide la IMAGEN.

Juan (7 oct): «son demasiados para revisar, usemos los que cumplan un criterio
serio». Lo que no cumple queda SIN afiche (la app pinta su respaldo): mejor
vacío que ajeno.

LAS DOS PRUEBAS, calibradas contra los 973 afiches locales publicados:
  1. TARJETA DE TEXTO: la fracción de filas con contenido (bordes) es < 12%.
     El rectángulo verde da 6%; el afiche real más vacío del corpus, 18%
     («Far from the Trees», un sol rojo sobre azul). Un afiche minimalista
     llena más filas que un título solo.
  2. TARJETA DE FESTIVAL: la OCR lee el encabezado de sección de un festival
     («Sección | Programa …»). Solo pesa cuando la imagen es de OTRO festival:
     en el suyo es su lámina, y es decisión de ese festival.
"""
import re
import unicodedata

UMBRAL_CONTENIDO = 0.12
_TARJETA = re.compile(r'\bseccion\b.{0,40}\bprograma\b')


def _plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def contenido_vertical(ruta):
    """Fracción de filas (de 176, sobre la imagen a 120×180) con más de 3 bordes."""
    from PIL import Image, ImageFilter
    im = Image.open(ruta).convert('L').resize((120, 180))
    e = im.filter(ImageFilter.FIND_EDGES).load()
    filas = sum(1 for y in range(2, 178) if sum(1 for x in range(2, 118) if e[x, y] > 35) > 3)
    return filas / 176


def es_tarjeta_de_texto(ruta):
    return contenido_vertical(ruta) < UMBRAL_CONTENIDO


def es_tarjeta_de_festival(texto_ocr):
    return bool(_TARJETA.search(_plano(texto_ocr)))


def veredicto(ruta, texto_ocr=None, ajena=False):
    """→ None si es un afiche; si no, el motivo. `ajena`: la imagen es de OTRO
    festival (se reusa); `texto_ocr`: lo leído por pipeline/ocr.py, si lo hay."""
    c = contenido_vertical(ruta)
    if c < UMBRAL_CONTENIDO:
        return f'tarjeta de solo texto ({c:.0%} de filas con contenido)'
    if ajena and texto_ocr is not None and es_tarjeta_de_festival(texto_ocr):
        return 'tarjeta de sección de otro festival'
    return None
