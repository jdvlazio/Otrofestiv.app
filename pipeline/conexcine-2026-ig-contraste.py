#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-ig-contraste.py — CUARTA lectura: Instagram contra el PDF.

Las tres primeras lecturas (poppler, MuPDF y el OCR de la página) leen EL MISMO
DOCUMENTO. Coincidir entre ellas prueba que lo transcribimos bien; no prueba que
el documento esté completo. Instagram es otra fuente, del mismo festival, y es
la que puede decir que al PDF le falta algo.

QUÉ SE LEE. El carrusel «¡Selección Oficial CONEXCINE 2026!» (DbYizbxjmEQ):
diez láminas donde el festival lista, obra por obra, TÍTULO / Dir. NOMBRE /
DEPARTAMENTO, agrupadas por competencia. El dato está PINTADO —el pie no
repite ni un título—, así que se baja cada lámina por el embed y se lee con el
OCR del sistema. La regla es de Juan, del 18 sep: la programación que un
festival publica como imagen se lee lámina por lámina, nunca por el pie.

QUÉ APORTA QUE EL PDF NO TIENE: el DIRECTOR de cada corto. El PDF solo da
título y departamento.

Salida: festivals/staging/conexcine-2026-ig.json + informe.
Sale con 1 si hay una diferencia no declarada.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ig_carrusel import laminas
from ocr import leer
from lib import provenance, norm, hora24

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = f'{REPO}/festivals/staging/conexcine-2026-catalogo.json'
PAR = f'{REPO}/festivals/staging/conexcine-2026-parrilla.json'
CRUDO = f'{REPO}/festivals/staging/conexcine-2026-crudo.json'
OUT = f'{REPO}/festivals/staging/conexcine-2026-ig.json'
POST = 'DbYizbxjmEQ'
# Los posts que PINTAN día, hora o sede. Se leen sus láminas y se cruza lo
# pintado contra la parrilla del PDF: es la única forma de saber si el festival
# movió algo después de publicar el programa.
POSTS_HORARIO = {
    'DdWWCJijPdT': 'las dos funciones de «El Cine Colombiano Nos Late», 18 sep',
    'DcWGnJrEWrP': 'el MISMO anuncio, una semana antes',
}
# EL CARTEL CON LA PARRILLA ENTERA (19 sep). El festival publicó la
# programación completa como UNA IMAGEN: los cuatro días con sus horas y sus
# programas. Es una lectura independiente del PDF —otra pieza, otro diseño— y
# por eso se cruza aparte.
#
# NO se le piden los DÍAS. El cartel va a columnas y el OCR las lee en zigzag:
# las horas del jueves y las del viernes salen intercaladas, y repartirlas por
# día sería inventar. Lo que sí es firme es el CONJUNTO de horas y de
# programas pintados, y eso es lo que se compara.
POST_CARTEL = 'DdeEWMmjULL'
HORA_CARTEL_OK = {
    '18:00': 'el FIN de la exposición permanente («Sábado 26 6:00 p.m.»), que es '
             'una franja de todo el festival y no una función',
}
# EL FESTIVAL CAMBIÓ LA HORA Y LO DIJO DOS VECES. El post viejo pinta jueves
# 5:00 p.m. y viernes 6:00 p.m.; el PDF (8 sep) y el post del 18 sep pintan
# 4:00 y 5:30. Se publica lo nuevo, que además es lo que dice el programa, y
# queda escrito que la diferencia es de FECHA DE PUBLICACIÓN, no un error.
HORA_SUPERADA = {
    ('DcWGnJrEWrP', '17:00'): 'quedó en 16:00 — lo corrigen el PDF y el post del 18 sep',
    ('DcWGnJrEWrP', '18:00'): 'quedó en 17:30 — lo corrigen el PDF y el post del 18 sep',
}
DIR_IG = f'{REPO}/fuentes/ig/{POST}'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Safari/605.1.15')

COMPETENCIAS = {
    'COMPETENCIA ADULTOS': 'Competencia Adultos',
    'COMPETENCIA JUVENIL': 'Competencia Juvenil',
    'COMPETENCIA EN(FOCO) SANTANDERES': 'Competencia En(Foco) Santanderes',
    'COMPETENCIA VIRTUAL': 'Competencia Virtual',
}
DEPTOS = {
    'amazonas', 'antioquia', 'arauca', 'atlantico', 'bolivar', 'boyaca', 'caldas',
    'caqueta', 'casanare', 'cauca', 'cesar', 'choco', 'cordoba', 'cundinamarca',
    'guainia', 'guaviare', 'huila', 'la guajira', 'magdalena', 'meta', 'narino',
    'norte de santander', 'putumayo', 'quindio', 'risaralda', 'san andres',
    'santander', 'sucre', 'tolima', 'valle del cauca', 'vaupes', 'vichada',
    'bogota d.c.', 'bogota dc', 'bogota',
}

# Diferencias entendidas entre la grafía de IG y la del PDF. Se declara la
# pareja, no se normaliza a ciegas: son dos escrituras del mismo festival.
GRAFIA = {
    'bullerengue ritmo que sigue sonando': 'Bullerengue: ritmo que sigue sonando',
    'resistencia civil; entre la tierra y la memoria':
        'Resistencia civil: entre la tierra y la memoria',
    'mina de libertad': 'Mina de Libertad',
}




# El ancla se compara NORMALIZADA contra una lista NORMALIZADA. Escrita a medias
# —«bogota d.c.» crudo contra «bogota d c» normalizado— el ancla no casaba y se
# perdían las dos obras de Bogotá, «La tienda de Marcelita» y «Lo que vimos
# desde arriba», que además aparecían como diferencias falsas contra el PDF.
DEPTOS = {norm(d) for d in DEPTOS}


def baja():
    os.makedirs(DIR_IG, exist_ok=True)
    urls = laminas(POST)['laminas']
    ps = []
    for i, u in enumerate(urls, 1):
        p = f'{DIR_IG}/{i:02d}.jpg'
        if not os.path.exists(p) or os.path.getsize(p) < 5000:
            subprocess.run(['curl', '-sSL', '--max-time', '45', '-A', UA, '-o', p,
                            u if isinstance(u, str) else u.get('url')], check=False)
        ps.append(p)
    return ps


def lee_laminas(ps):
    """Cada lámina es TÍTULO / «Dir. …» / DEPARTAMENTO, repetido. El
    departamento cierra la ficha: es la única de las tres líneas que viene de
    una lista cerrada, así que es el ancla."""
    crudo = leer(ps)
    obras = []
    for p in ps:
        ls = crudo.get(p, [])
        # LA COMPETENCIA SE LEE EN CADA LÁMINA, y no se arrastra de la
        # anterior: la lámina 10 son los créditos («Gobernación de Norte de
        # Santander») y heredando la competencia de la 9 publicaba un corto
        # fantasma llamado «de Norte de».
        cab = ' '.join(l for l in ls[:6] if l.isupper())
        comp = next((v for k, v in COMPETENCIAS.items() if norm(k) in norm(cab)), '')
        if not comp:
            continue
        # LA CABECERA SE SALTA, y se salta CONTANDO MAYÚSCULAS, no buscando el
        # rótulo. Cada lámina abre con «CÚCUTA / NORTE DE / SANTANDER» y ese
        # «SANTANDER» es un departamento válido: como ancla cerraba una ficha
        # falsa. Buscar «dónde acaba el rótulo» tampoco sirvió: «Santander»
        # está CONTENIDO en «SANTANDERES», así que en la lámina de Juvenil el
        # corte saltaba hasta la línea 6 y se perdía «Del otro lado del solar».
        # La cabecera es la tira inicial de renglones en mayúscula, y ya.
        ini = 0
        while ini < len(ls) and ls[ini].isupper():
            ini += 1
        pend = []
        for l in ls[ini:]:
            if norm(l) in DEPTOS and pend:
                dire = next((x for x in reversed(pend)
                             if re.match(r'^D[ií]r', x.strip(), re.I)), '')
                antes = pend[:pend.index(dire)] if dire in pend else pend
                tit = antes[-1].strip() if antes else ''
                if tit and comp and not tit.isupper():
                    obras.append({
                        'titulo': GRAFIA.get(norm(tit), tit),
                        'director': re.sub(r'^D[ií\u0131]r\.?\s*', '', dire).strip(' /'),
                        'departamento': l.strip(), 'seccion': comp,
                        '_src': {'url': f'https://www.instagram.com/p/{POST}/',
                                 'lamina': os.path.basename(p), 'date': '2026-09-19'}})
                pend = []
            else:
                pend.append(l)
    return obras


def baja_post(sc):
    """Las imágenes de un post. `ig_carrusel` sabe de CARRUSELES: lee el
    `contextJSON` del embed, que solo existe cuando el post es un GraphSidecar.
    Un post de UNA imagen —como el cartel con la parrilla entera— lo hace
    reventar, así que se cae al <img> del propio embed, que siempre está."""
    os.makedirs(f'{REPO}/fuentes/ig/{sc}', exist_ok=True)
    try:
        urls = laminas(sc).get('laminas') or []
    except Exception:
        h = subprocess.run(['curl', '-sSL', '--max-time', '25', '-A', UA,
                            f'https://www.instagram.com/p/{sc}/embed/captioned/'],
                           capture_output=True, text=True).stdout
        m = re.findall(r'<img[^>]+class="EmbeddedMediaImage"[^>]+src="([^"]+)"', h) \
            or re.findall(r'"display_url":"([^"]+)"', h)
        urls = [m[0].replace('\\u0026', '&').replace('&amp;', '&')] if m else []
    ps = []
    for i, u in enumerate(urls, 1):
        q = f'{REPO}/fuentes/ig/{sc}/{i:02d}.jpg'
        if not os.path.exists(q) or os.path.getsize(q) < 5000:
            subprocess.run(['curl', '-sSL', '--max-time', '45', '-A', UA, '-o', q,
                            u if isinstance(u, str) else u.get('url')], check=False)
        if os.path.exists(q) and os.path.getsize(q) > 5000:
            ps.append(q)
    return ps


RE_HORA_SUELTA = re.compile(r'\b(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)


def horas_de(txt):
    """Las horas que un texto pinta, en 24 h y sin repetir."""
    return list(dict.fromkeys(
        hora24(f'{m.group(1)}:{m.group(2)} {m.group(3)}.m.')
        for m in RE_HORA_SUELTA.finditer(txt)))


RE_HORA_PINTADA = re.compile(
    r'(?:jueves|viernes|s[áa]bado|mi[ée]rcoles)\s+(2[3-6])\s+de\s+septiembre[,\s]+'
    r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)


def horas_pintadas():
    """Día y hora que cada lámina ANUNCIA, leídos del píxel."""
    vistos = []
    for sc in POSTS_HORARIO:
        for q in baja_post(sc):
            for l in leer([q]).get(q, []):
                m = RE_HORA_PINTADA.search(l)
                if m:
                    h = int(m.group(2)) + (12 if m.group(4).lower() == 'p'
                                           and int(m.group(2)) != 12 else 0)
                    vistos.append({'post': sc, 'lamina': os.path.basename(q),
                                   'dia': f'2026-09-{m.group(1)}',
                                   'hora': f'{h:02d}:{m.group(3)}', 'texto': l})
    return vistos


def main():
    ps = baja()
    ig = lee_laminas(ps)
    cat = json.load(open(CAT, encoding='utf-8'))['obras']

    por_ig = {norm(o['titulo']): o for o in ig}
    por_pdf = {norm(o['titulo']): o for o in cat}

    faltan_en_pdf = [o for k, o in por_ig.items() if k not in por_pdf]
    faltan_en_ig = [o for k, o in por_pdf.items() if k not in por_ig]

    json.dump({'_provenance': provenance(
        f'Instagram @fedecajas, carrusel «¡Selección Oficial CONEXCINE 2026!» '
        f'({POST}), 10 láminas',
        que_aporta='el DIRECTOR de cada corto, que el PDF no publica, y la '
                   'competencia a la que pertenece',
        url=f'https://www.instagram.com/p/{POST}/',
        metodo='las láminas se bajan por el embed público (sin sesión) y se leen '
               'con el OCR del sistema: el dato va PINTADO y el pie no repite ni '
               'un título'),
        'obras': ig,
        'solo_en_instagram': [{'titulo': o['titulo'], 'director': o['director'],
                               'seccion': o['seccion']} for o in faltan_en_pdf],
        'solo_en_el_pdf': [{'titulo': o['titulo'], 'seccion': o['seccion']}
                           for o in faltan_en_ig]},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    import collections
    c = collections.Counter(o['seccion'] for o in ig)
    print(f'Instagram · {len(ig)} obras leídas en {len(ps)} láminas')
    for k, v in c.items():
        print(f'  {v:2}  {k}')
    print(f'\nPDF · {len(cat)} cortos')
    print(f'directores que aporta IG y el PDF no tiene: '
          f'{sum(1 for o in ig if o["director"])}')

    if faltan_en_pdf:
        print(f'\n⚠ {len(faltan_en_pdf)} obra(s) que Instagram anuncia y el PDF NO lista:')
        for o in faltan_en_pdf:
            print(f'   · {o["titulo"]} — Dir. {o["director"]} ({o["departamento"]}) '
                  f'· {o["seccion"]}')
    if faltan_en_ig:
        print(f'\n⚠ {len(faltan_en_ig)} obra(s) del PDF que Instagram no anuncia:')
        for o in faltan_en_ig:
            print(f'   · {o["titulo"]} · {o["seccion"]}')
    if not faltan_en_pdf and not faltan_en_ig:
        print('\n✓ Instagram y el PDF listan exactamente las mismas obras')

    # ── la PARRILLA contra lo pintado en Instagram ───────────────────────────
    par = json.load(open(PAR, encoding='utf-8'))['bloques']
    slots = {(b['dia'], b['hora']) for b in par}
    print(f'\nhorarios pintados en Instagram, contra la parrilla del PDF:')
    choques = []
    for v in horas_pintadas():
        clave = (v['post'], v['hora'])
        if (v['dia'], v['hora']) in slots:
            print(f'   ✓ {v["dia"][-2:]} {v["hora"]}  {v["post"]}/{v["lamina"]}  '
                  f'coincide con la parrilla')
        elif clave in HORA_SUPERADA:
            print(f'   · {v["dia"][-2:]} {v["hora"]}  {v["post"]}/{v["lamina"]}  '
                  f'{HORA_SUPERADA[clave]}')
        else:
            choques.append(v)
            print(f'   ✗ {v["dia"][-2:]} {v["hora"]}  {v["post"]}/{v["lamina"]}  '
                  f'NO existe en la parrilla — «{v["texto"][:46]}»')
    if choques:
        sys.exit(1)

    # ── el CARTEL de programación, contra la parrilla entera ─────────────────
    fallos = []
    cartel = []
    for q in baja_post(POST_CARTEL):
        cartel += leer([q]).get(q, [])
    txt_c = ' '.join(cartel)
    horas_c = set(horas_de(txt_c))
    nuestras = {b['hora'] for b in par}
    print(f'\ncartel de programación ({POST_CARTEL}), {len(cartel)} líneas pintadas:')
    faltan_c = nuestras - horas_c
    if faltan_c:
        fallos.append(f'el cartel NO pinta estas horas que publicamos: {sorted(faltan_c)}')
    else:
        print(f'   ✓ las {len(nuestras)} horas que publicamos están pintadas en el cartel')
    sobran = {h for h in horas_c - nuestras if h not in HORA_CARTEL_OK}
    for h in sorted(horas_c - nuestras):
        if h in HORA_CARTEL_OK:
            print(f'   · {h} pintada y sin función: {HORA_CARTEL_OK[h]}')
    if sobran:
        fallos.append(f'el cartel pinta horas que no tenemos: {sorted(sobran)}')
    # y los programas: el nombre de cada uno tiene que estar pintado
    sin_pintar = [f['titulo'] for f in
                  json.load(open(CRUDO, encoding='utf-8'))['funciones']
                  if f.get('is_cortos') and f['titulo'].startswith('PROGRAMA')
                  and norm(f['titulo'].split(':', 1)[1]) not in norm(txt_c)]
    if sin_pintar:
        fallos.append(f'programas que el cartel no nombra: {sin_pintar}')
    else:
        print('   ✓ los 6 programas de cortos están nombrados en el cartel')

    if fallos:
        print(f'\n✗ {len(fallos)} diferencia(s):')
        for f_ in fallos:
            print('   ✗', f_)
        sys.exit(1)


if __name__ == '__main__':
    main()
