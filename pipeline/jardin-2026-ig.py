#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-ig.py — lo que el Festival de Cine de Jardín publicó PINTADO.

LA WEB TIENE EL CATÁLOGO; INSTAGRAM TIENE TODO LO DEMÁS. `jardin-2026-catalogo.py`
ya trae las 37 obras con su ficha desde festicinejardin.com. Lo que la web NO
publica —y a cuatro días del festival sigue sin publicar— es dónde y cuándo. Eso
salió por Instagram, y **dentro de las imágenes**:

  · LAS CINCO SEDES de esta edición, en un mapa publicado el 20 sep. Dos se
    movieron por el sismo del 10 de agosto: la cancha Moisés Rojas Peláez quedó
    inutilizable y el festival reubicó las charlas y las proyecciones.
  · LA ÚNICA FUNCIÓN FECHADA: la inaugural. El pie da día, hora y sede; la
    LÁMINA da la obra, el director y la duración. El pie no dice qué película es.
  · UNA SEGUNDA LECTURA de siete obras de la Muestra Central, con año, país y
    duración — que es lo que permite contrastar la web contra su propio
    Instagram. Ver `jardin-2026-contraste.py`: no coinciden.

POR QUÉ SE LEEN LOS PÍXELES Y NO EL PIE. Regla de la casa desde #NarrarElFuturo:
el pie redondea y el preview miente. Acá se comprueba solo — el post de la
inaugural tiene seis láminas y el pie no nombra la película.

DOS TRAMPAS DE ESTE FESTIVAL, declaradas para que nadie las coseche:

  1. La lámina 3 del post del mapa lleva DE FONDO una foto de una edición
     anterior, con títulos de cortos perfectamente legibles («Tierra encima»,
     «El sol del río», «TRIO»…). NO son de esta edición. El OCR los lee; este
     script los tira por `RUIDO_DE_FONDO` y la razón queda escrita.
  2. «MUESTRA CENTRAL Parte I» está FIJADO en el perfil, así que aparece arriba
     aunque haya dos posts posteriores. Y su pie nombra SIETE obras mientras el
     carrusel trae SEIS láminas: «Nuestra tierra», de Lucrecia Martel, no tiene
     lámina. Se registra desde el pie y marcada.

Lee   (Instagram, vía el embed público — sin sesión)
Esc.  festivals/staging/jardin-2026-ig.json
      fuentes/jardin-2026/ig/<shortcode>-NN.jpg   (gitignored)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ig_carrusel import laminas
from lib import norm, provenance
from ocr import leer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
FUENTES = f'{REPO}/fuentes/jardin-2026/ig'
OUT = f'{ST}/jardin-2026-ig.json'

# shortcode → (clase, rótulo, láminas esperadas). El número se DECLARA: si el
# festival edita el carrusel, el paso falla en vez de leer de menos en silencio.
POSTS = {
    'DdhXOGxgS3U': ('mapa', 'Las sedes de esta edición, con los cambios del sismo', 4),
    'Ddc1aLQlhWo': ('apertura', 'Acto inaugural — estreno mundial', 6),
    'DdVAi3zliEt': ('muestra', 'MUESTRA CENTRAL Parte I', 7),
    'DcytNbdlgrv': ('caleidoscopio', 'Selección oficial · Documental', 9),
    'Dczc9LIls6f': ('caleidoscopio', 'Selección oficial · Ficción', 11),
    'DczQXk6Ft3W': ('caleidoscopio', 'Selección oficial · Experimental', 8),
}

# MIRADO Y DESCARTADO, para no volver a abrirlo cada corrida.
DESCARTADOS = {
    'DdaCzQoS_cE': 'reel: los mismos 22 cortos de los tres carruseles, en vídeo',
    'DcUMTxQAc2x': 'anuncio de la edición: tema, fechas y qué habrá. Sin parrilla',
    'DdXuartlmbJ': 'invitado (Sebastián Lanz) y «una conversación» — sin día, '
                   'hora ni sede: no es una función',
    'Ddh0vXUCa64': 'NO ES DEL FESTIVAL: @danicooltura, «Películas imperdibles». '
                   'Recomendación de un tercero, no fuente',
}

# Las cinco sedes, tal como las numera el mapa. Se declaran para VERIFICAR la
# lectura, no para sustituirla: si el OCR no las encuentra todas, el paso falla.
SEDES = [
    'Teatro Municipal de Jardín',
    'Casa de la Cultura',
    'Escuela Jahel Peláez Montoya',
    'Placa deportiva Simón Bolívar',
    'Coliseo Municipal',
]

# TRAMPA 1. Fotos de ediciones anteriores usadas como fondo. Lo que el OCR saque
# de estas láminas no es programación de 2026.
RUIDO_DE_FONDO = {
    ('DdhXOGxgS3U', 3): 'de fondo, una foto de una edición anterior proyectando '
                        'Caleidoscopio en la cancha Moisés Rojas: se leen títulos '
                        'de cortos («Tierra encima», «El sol del río», «TRIO») que '
                        'NO son de esta edición',
}

# TRAMPA 2. La obra que el pie nombra y ninguna lámina pinta.
SOLO_EN_EL_PIE = {
    'Nuestra tierra': {
        'anio': 2025, 'pais': 'Argentina', 'director': 'Lucrecia Martel',
        '_por_que': 'el pie de «MUESTRA CENTRAL Parte I» la lista como una de las '
                    'siete, pero el carrusel solo trae seis láminas y ninguna es '
                    'suya. Ficha desde el pie; la duración no la da (la web dice '
                    '122 min)',
    },
}

RE_CAMPO = re.compile(r'^\s*(Nombre|País|Pais|Duración|Duracion|Dirección|'
                      r'Direccion|Año|Ano)\s*:\s*(.+?)\s*$')
RE_DIR = re.compile(r'^\s*Dir[.:]\s*(.+?)\s*$')
RE_MIN = re.compile(r'(\d{2,3})\s*min')
RE_FECHA = re.compile(r'(?:Jueves|Viernes|Sábado|Domingo|Lunes|Martes|Miércoles)\s+'
                      r'(\d{1,2})\s+de\s+(\w+)', re.I)
RE_HORA = re.compile(r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', re.I)
MESES = {'septiembre': 9}


def baja(sc, n_esperadas):
    """Las láminas del carrusel en disco, y el pie. El embed no pide sesión."""
    import subprocess
    os.makedirs(FUENTES, exist_ok=True)
    d = laminas(sc)
    if len(d['laminas']) != n_esperadas:
        sys.exit(f'✗ {sc}: el carrusel trae {len(d["laminas"])} láminas y este '
                 f'script declara {n_esperadas}. Mirar el post antes de tocar '
                 f'el número.')
    rutas = []
    for l in d['laminas']:
        p = f'{FUENTES}/{sc}-{l["i"]:02}.jpg'
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            subprocess.run(['curl', '-sS', '--max-time', '60', '-o', p, l['url']],
                           check=True)
        rutas.append(p)
    return rutas, d['caption']


def ficha(lineas):
    """«Nombre: X / País: Y / Duración: Z / Dirección: W / Año: N» → dict.

    El valor puede seguir en la línea de abajo: el festival parte las líneas
    largas por la mitad y la continuación no lleva etiqueta."""
    d, ultimo = {}, None
    CLAVE = {'Nombre': 'titulo', 'País': 'pais', 'Pais': 'pais',
             'Duración': 'duracion', 'Duracion': 'duracion',
             'Dirección': 'director', 'Direccion': 'director',
             'Año': 'anio', 'Ano': 'anio'}
    for ln in lineas:
        m = RE_CAMPO.match(ln)
        if m:
            ultimo = CLAVE[m.group(1)]
            d[ultimo] = m.group(2)
        elif ultimo and ln.strip() and not ln.startswith(('Festiv', 'de cine', '11')):
            d[ultimo] = f'{d[ultimo]} {ln.strip()}'.strip()
    if d.get('anio'):
        d['anio'] = int(re.sub(r'\D', '', d['anio'])[:4] or 0) or None
    return d


def lee_muestra(rutas, txt, hall):
    """Las láminas de ficha del carrusel de la Muestra Central."""
    obras = []
    for p in rutas:
        d = ficha(txt[p])
        if not d.get('titulo'):
            continue                       # portada o créditos: no es una ficha
        # «Cuando las montañas tiemblan (When the Mountains Tremble)»: la lámina
        # pinta el título original entre paréntesis en la línea de abajo. Es
        # `title_en`, no parte del nombre.
        titulo, en = d['titulo'], ''
        m_en = re.match(r'^(.*?)\s*\(([^()]{4,})\)\s*$', titulo)
        if m_en and re.search(r'[A-Za-z]', m_en.group(2)) and ' ' in m_en.group(2):
            titulo, en = m_en.group(1).strip(), m_en.group(2).strip()
        o = {'titulo': titulo, '_lamina': os.path.basename(p)}
        if en:
            o['title_en'] = en
        for k in ('pais', 'director', 'anio'):
            if d.get(k):
                o[k] = d[k]
        # LA DURACIÓN, TAL COMO LA PUBLICARON. Una lámina trae DOS, cada una con
        # su fuente: «92 min. según Proimágenes / 94 min. según OjoAgua». No se
        # elige acá — se guardan las dos y el contraste decide.
        mins = RE_MIN.findall(d.get('duracion', ''))
        if mins:
            o['duracion_min'] = int(mins[0])
        if len(mins) > 1:
            o['_duracion_literal'] = d['duracion']
            hall.append(f'«{o["titulo"]}»: la lámina publica DOS duraciones con su '
                        f'fuente cada una — «{d["duracion"]}». Se toma la primera '
                        f'y queda el literal.')
        # El campo País de una lámina trae los IDIOMAS. Es un error del festival
        # al armar la pieza, no una lectura nuestra: se marca y no se publica.
        if o.get('pais') and re.search(r'(?i)espa[ñn]ol|ingl[ée]s|lenguas', o['pais']):
            o['_pais_dudoso'] = o.pop('pais')
            hall.append(f'«{o["titulo"]}»: el campo País de la lámina trae los '
                        f'IDIOMAS («{o["_pais_dudoso"]}»). No se publica.')
        obras.append(o)
    for t, extra in SOLO_EN_EL_PIE.items():
        if norm(t) in {norm(o['titulo']) for o in obras}:
            sys.exit(f'✗ «{t}» YA tiene lámina: quitarla de SOLO_EN_EL_PIE.')
        if norm(t) not in norm(txt.get('_caption', '')):
            sys.exit(f'✗ «{t}» no está ni en lámina ni en el pie. Releer el post.')
        obras.append({'titulo': t, '_solo_en_el_pie': True, **extra})
        hall.append(f'«{t}» la nombra el pie y no tiene lámina: {extra["_por_que"]}')
    return obras


def banda(p):
    """El tercio de abajo de la lámina, recortado a un PNG en el scratch.

    LA TARJETA DEL TÍTULO ES LA BANDA DE ABAJO, y leer la lámina entera mete
    dos defectos que se vieron en esta misma corrida: el fondo de «Primer amor»
    es una cancha con vallas publicitarias y el OCR devolvía «TRAS / 192 / FRE /
    RAD / DEPORTIVO / CP» antes del título; y un título de dos líneas —«Un
    aparato para detectar / fantasmas»— se quedaba en «fantasmas» al tomar solo
    la línea anterior al «Dir:». Recortando la banda, lo que queda dentro es la
    tarjeta y nada más: el título entero, aunque ocupe dos líneas."""
    from PIL import Image
    os.makedirs(f'{FUENTES}/_banda', exist_ok=True)
    o = f'{FUENTES}/_banda/{os.path.basename(p)[:-4]}.png'
    if not os.path.exists(o):
        im = Image.open(p)
        w, h = im.size
        im.crop((0, int(0.60 * h), w, h)).save(o)
    return o


def lee_caleidoscopio(rutas, cache_ocr):
    """Título + «Dir: …» por lámina, leídos en la banda. Portada y cierre no
    traen «Dir:» y por eso se caen solos."""
    bandas = [banda(p) for p in rutas]
    txt = leer(bandas)
    cache_ocr.update(txt)
    obras = []
    for p, b in zip(rutas, bandas):
        ls = [x.strip() for x in txt[b] if x.strip()]
        i = next((k for k, x in enumerate(ls) if RE_DIR.match(x)), None)
        if i is None or i == 0:
            continue
        # el director puede seguir en la línea de abajo: dos firmas, dos líneas
        dire = [RE_DIR.match(ls[i]).group(1)] + [x for x in ls[i + 1:] if x]
        obras.append({'titulo': ' '.join(ls[:i]), 'director': ', '.join(dire),
                      '_lamina': os.path.basename(p)})
    return obras


def lee_apertura(rutas, txt, hall):
    """La única función con día, hora y sede de todo el corpus."""
    plano = '\n'.join(x for p in rutas for x in txt[p])
    mf, mh = RE_FECHA.search(plano), RE_HORA.search(plano)
    if not (mf and mh):
        sys.exit('✗ apertura: sin fecha o sin hora en las láminas. Releer el post.')
    mes = MESES.get(norm(mf.group(2)))
    if not mes:
        sys.exit(f'✗ apertura: mes «{mf.group(2)}» desconocido')
    h = int(mh.group(1)) % 12 + (12 if mh.group(3).lower() == 'p' else 0)
    sede = next((s for s in SEDES if norm(s) in norm(plano)), '')
    if not sede:
        sys.exit('✗ apertura: la sede que nombra la lámina no está en SEDES')
    # El título va en la lámina 1 y la ficha en la 2; el pie no nombra la obra.
    mt = re.search(r'(?im)^\s*(?:ACTO INAUGURAL|АСТО INAUGURAL)\s*\n\s*(.+?)\s*'
                   r'(?:\((\d{4})\))?\s*$', '\n'.join(txt[rutas[0]]))
    if not mt:
        sys.exit('✗ apertura: la lámina 1 no nombra la obra bajo «ACTO INAUGURAL»')
    dur = RE_MIN.search(plano)
    dire = re.search(r'Dir\.\s*(.+)', plano)
    hall.append('el pie del post de la inaugural NO nombra la película: da día, '
                'hora y sede, y la obra solo está pintada en la lámina 1.')
    return {
        'dia': f'2026-09-{int(mf.group(1)):02}', 'hora': f'{h:02}:{mh.group(2)}',
        'sede': sede, 'titulo': mt.group(1).strip(),
        'seccion': 'Muestra Central', 'event_kind': 'apertura',
        **({'anio': int(mt.group(2))} if mt.group(2) else {}),
        **({'duracion_obra': int(dur.group(1))} if dur else {}),
        **({'director': dire.group(1).strip()} if dire else {}),
        '_estreno': 'Estreno mundial, según el pie y la lámina 1',
    }


def lee_mapa(rutas, txt):
    """Las cinco sedes numeradas del mapa. Se verifica que estén las cinco."""
    plano = norm('\n'.join(x for p in rutas for x in txt[p]))
    faltan = [s for s in SEDES if norm(s) not in plano]
    if faltan:
        sys.exit(f'✗ el mapa no nombra {faltan}. Mirar la lámina antes de '
                 f'tocar SEDES.')
    return list(SEDES)


def main():
    txt, rutas_por_post, pies, hall = {}, {}, {}, []
    for sc, (clase, rotulo, n) in POSTS.items():
        rutas, pies[sc] = baja(sc, n)
        rutas_por_post[sc] = rutas
        leidas = leer(rutas)
        for p, ls in leidas.items():
            i = int(os.path.basename(p).rsplit('-', 1)[1][:2])
            if (sc, i) in RUIDO_DE_FONDO:
                txt[p] = []
                hall.append(f'{sc} lámina {i}: descartada — {RUIDO_DE_FONDO[(sc, i)]}')
            else:
                txt[p] = ls
        print(f'{sc}  {clase:14} {len(rutas)} láminas  {rotulo}', flush=True)

    # el pie del post de la Muestra, que es donde vive «Nuestra tierra»
    txt['_caption'] = pies['DdVAi3zliEt']

    muestra = lee_muestra(rutas_por_post['DdVAi3zliEt'], txt, hall)
    apertura = lee_apertura(rutas_por_post['Ddc1aLQlhWo'], txt, hall)
    sedes = lee_mapa(rutas_por_post['DdhXOGxgS3U'], txt)
    cortos = []
    for sc, (clase, rotulo, _) in POSTS.items():
        if clase == 'caleidoscopio':
            cat = rotulo.split('·')[-1].strip()
            for o in lee_caleidoscopio(rutas_por_post[sc], txt):
                cortos.append({**o, 'categoria': cat, '_post': sc})

    json.dump({'_provenance': provenance(
        'Instagram de @festicinejardin — las láminas de seis carruseles, leídas '
        'con el OCR del sistema sobre los píxeles',
        que_aporta='las 5 sedes de la edición (mapa del 20 sep, con las dos '
                   'reubicaciones del sismo), la única función fechada (la '
                   'inaugural) y una segunda lectura de 7 obras de la Muestra '
                   'Central y de los 22 cortos de CALEIDOSCOPIO',
        url='https://www.instagram.com/festicinejardin/',
        metodo='el dato está PINTADO: el pie del post de la inaugural no nombra '
               'siquiera la película. Se bajan las láminas por el embed público '
               'y se leen con pipeline/ocr.py',
        alcance=f'{len(POSTS)} posts · {sum(n for _, _, n in POSTS.values())} '
                f'láminas'),
        'sedes': sedes, 'funciones': [apertura],
        'muestra_central': muestra, 'caleidoscopio': cortos,
        '_hallazgos': hall, '_descartados': DESCARTADOS,
        '_ruido_de_fondo': {f'{k[0]} lámina {k[1]}': v
                            for k, v in RUIDO_DE_FONDO.items()}},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n{len(sedes)} sedes · {len([apertura])} función fechada · '
          f'{len(muestra)} obras de la Muestra Central · {len(cortos)} cortos '
          f'→ {OUT.split("/")[-1]}')
    print(f'\n  {apertura["dia"]} {apertura["hora"]}  «{apertura["titulo"]}»  '
          f'{apertura["sede"]}')
    for s in sedes:
        print(f'  · {s}')
    if hall:
        print(f'\n{len(hall)} hallazgo(s):')
        for h in hall:
            print(f'   ⚠ {h}')


if __name__ == '__main__':
    main()
