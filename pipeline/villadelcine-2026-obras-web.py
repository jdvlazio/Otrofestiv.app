#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-obras-web.py — una página por obra en villadelcine.com.

QUÉ APORTA QUE EL PDF NO TIENE. El sitio publica una ficha por obra bajo
`/festival-2024-2/<slug>/` —82 páginas, listadas en `wp-sitemap-posts-page-1.xml`,
la ruta se llama así por herencia de 2024 y no por el año—. De cada una salen:

  · la SINOPSIS EN INGLÉS. El PDF trae la española; juntas dan el par
    sinopsis/sinopsis_en sin traducir nada nosotros.
  · el AFICHE de la obra (webp subido en 2026/09).
  · el INSTAGRAM del director o de la obra, cuando lo ponen.
  · la duración como «17:40» y el país, que sirven para CONTRASTAR el PDF.

QUÉ NO APORTA: ni día, ni hora, ni sede. Eso solo está en la retícula del PDF.

POR QUÉ SE CACHEA. 82 páginas son 82 peticiones al sitio de un festival chico
en su semana de apertura. Se bajan una vez a `fuentes/` y el paso se re-corre
sin volver a tocarlos.

Lee   https://villadelcine.com/wp-sitemap-posts-page-1.xml + una página por obra
Esc.  festivals/staging/villadelcine-2026-obras-web.json
"""
import html as _html
import json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/villadelcine-2026/obras'
OUT = f'{ST}/villadelcine-2026-obras-web.json'
SITEMAP = 'https://villadelcine.com/wp-sitemap-posts-page-1.xml'
BASE = 'https://villadelcine.com/festival-2024-2/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')

# El logotipo del sitio aparece en todas las páginas: no es el afiche de nadie.
NO_ES_AFICHE = re.compile(r'Logo_VDC|logo|favicon|placeholder', re.I)
RE_DUR = re.compile(r'^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})$')
# Los países que nombran estas fichas, tal como los escriben (con sus erratas:
# «Brasi», «Usbekistán»). Una lista y no una heurística: ver el docstring de
# `una()`.
PAIS = re.compile(
    r'(?i)\s*(colombia|m[ée]xico|mexico|brasi[l]?|argentina|chile|per[úu]|ecuador|'
    r'venezuela|uruguay|paraguay|bolivia|guatemala|cuba|panam[áa]|costa rica|'
    r'espa[ñn]a|francia|italia|alemania|portugal|reino unido|inglaterra|irlanda|'
    r'b[ée]lgica|holanda|pa[íi]ses bajos|suiza|austria|suecia|noruega|dinamarca|'
    r'finlandia|polonia|rusia|ucrania|rep[úu]blica checa|grecia|turqu[íi]a|'
    r'usbekist[áa]n|uzbekistan|kazajist[áa]n|india|china|jap[óo]n|taiw[áa]n|corea|'
    r'ir[áa]n|israel|nigeria|sud[áa]frica|marruecos|egipto|australia|canad[áa]|'
    r'usa|ee\.?uu\.?|estados unidos|guatemala / usa|[a-zá-ú]+(?:\s*[,/]\s*[a-zá-ú]+)+)'
    r'\s*')


def baja(url, nombre):
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 500:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sSL', '--max-time', '45', '-A', UA, '-o', p, url],
                       check=True)
        time.sleep(0.3)
    return open(p, encoding='utf-8', errors='replace').read()


def texto(h):
    t = _html.unescape(re.sub(r'(?s)<(script|style).*?</\1>', '', h))
    t = re.sub(r'(?s)<[^>]+>', '\n', t)
    return [x.strip() for x in t.split('\n') if x.strip()]


def una(slug):
    """La ficha de una obra, leída POR ETIQUETA y no por orden.

    La página no tiene <h1>. Arriba van, en bloque, título / crédito /
    duración / (año o país) / sinopsis en inglés; abajo, los campos rotulados
    «Duración:», «Año:» y «Director»/«Directores». MANDAN LOS ROTULADOS: en
    «Extinction» el crédito de arriba dice Gustavo Espíndola y el campo
    Director dice Frank Benítez, y en «Grief» la duración de arriba es 15:00 y
    la rotulada 15:30. Lo de arriba no se descarta ni se interpreta: queda como
    `_credito_superior` y se reporta, porque una segunda línea no es una
    autoría —eso ya nos costó publicar una obra huérfana—.
    """
    h = baja(BASE + slug + '/', slug + '.html')
    ls = texto(h)
    ini = max((i for i, l in enumerate(ls) if l.upper() == 'ACREDITACIÓN'), default=-1)
    cuerpo = ls[ini + 1:]
    if not cuerpo:
        return None
    titulo = cuerpo[0]

    def tras(*etiquetas):
        for i, l in enumerate(cuerpo):
            if l.lower().rstrip(':').strip() in etiquetas and i + 1 < len(cuerpo):
                return cuerpo[i + 1]
        return ''

    corte = next((i for i, l in enumerate(cuerpo)
                  if l.lower().rstrip(':') == 'duración'), len(cuerpo))
    cabeza = cuerpo[1:corte]
    director = tras('director', 'directores', 'dirección')
    # EL PAÍS Y EL AÑO VIENEN ROTULADOS en muchas páginas («País:», «Año:») y
    # yo los estaba adivinando de una línea suelta contra una lista blanca: 37
    # páginas lo decían con todas las letras y no las leía. «Añ0:», con un cero
    # en vez de la o, está así en tres de ellas.
    pais_rot = tras('país', 'pais')
    anio_rot = tras('año', 'ano', 'añ0', 'an0')
    dur = tras('duración') or next((c for c in cabeza if RE_DUR.match(c)), '')
    anio = anio_rot or tras('año')
    sinopsis = next((c for c in cabeza if len(c) > 60), '')
    # EL PAÍS SOLO SI ES UN PAÍS. La línea que sigue a la duración a veces es el
    # país, a veces el año y a veces nada, así que tomar «la siguiente corta»
    # dejaba países llamados «Carnal pleasures» o «Duración: 03». El país
    # normativo es el del PDF, que viene rotulado; acá solo se acepta lo que
    # figura en la lista, y lo demás se deja vacío a propósito.
    pais = pais_rot or next((c for c in cabeza[1:] if PAIS.fullmatch(c.strip())), '')
    credito = cabeza[0] if cabeza else ''
    dur_arriba = next((c for c in cabeza if RE_DUR.match(c)), '')

    afiches = [u for u in re.findall(r'<img[^>]+src="([^"]+)"', h)
               if not NO_ES_AFICHE.search(u)]
    igs = [u for u in re.findall(r'href="(https://[^"]*instagram\.com/[^"]+)"', h)
           if 'festivalvilladelcine' not in u]
    m = RE_DUR.match(dur or '')
    mins = None
    if m:
        hh, mi, se = m.group(1), int(m.group(2)), int(m.group(3))
        mins = (int(hh) * 60 if hh else 0) + mi + (1 if se >= 30 else 0)
    return {
        'slug': slug, 'titulo': titulo,
        'director': director or credito,
        **({'_director_sin_rotulo': True} if not director and credito else {}),
        **({'_credito_superior': credito} if director and credito
           and credito != director else {}),
        **({'_duracion_arriba': dur_arriba} if dur_arriba and dur_arriba != dur else {}),
        'pais': pais, 'anio': int(anio) if re.fullmatch(r'(19|20)\d{2}', anio or '') else None,
        'duracion_texto': dur, 'duracion_min': mins, 'sinopsis_en': sinopsis,
        'afiches': afiches[:3], 'instagram': list(dict.fromkeys(igs))[:2],
        '_src': BASE + slug + '/'}


def main():
    xml = baja(SITEMAP, 'sitemap-pages.xml')
    slugs = [m for m in re.findall(
        r'<loc>https://villadelcine\.com/festival-2024-2/([^/<]+)/</loc>', xml)]
    obras, sin_leer = [], []
    for s in slugs:
        try:
            o = una(s)
        except Exception as e:
            sin_leer.append(f'{s}: {str(e)[:50]}')
            continue
        if o and o['titulo']:
            obras.append(o)
        else:
            sin_leer.append(s)

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'villadelcine.com — la página de cada obra bajo /festival-2024-2/',
        que_aporta='sinopsis en inglés, afiche, Instagram del realizador, y la '
                   'duración y el país con que CONTRASTAR el PDF de programación',
        url=SITEMAP,
        metodo='las páginas se listan en el sitemap de WordPress y se cachean en '
               'fuentes/: son 82 peticiones al sitio de un festival chico en su '
               'semana de apertura y no se repiten en cada corrida'),
        'obras': obras}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con_sin = sum(1 for o in obras if o['sinopsis_en'])
    con_af = sum(1 for o in obras if o['afiches'])
    print(f'{len(obras)}/{len(slugs)} obras · {con_sin} con sinopsis EN · '
          f'{con_af} con afiche → {os.path.basename(OUT)}')
    if sin_leer:
        print(f'⚠ {len(sin_leer)} sin leer: ' + ', '.join(sin_leer[:6]))


if __name__ == '__main__':
    main()
