#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ig-programa.py <fest-id> <shortcode>... — leer la programación que un festival
publica en Instagram COMO IMÁGENES, y cruzarla contra lo que tenemos publicado.

POR QUÉ EXISTE (18 sep 2026, víspera de FICMA). El festival publicó un carrusel
por día, una lámina por función. Yo leí los PIES y no las láminas, y así se me
pasaron dos cosas que Juan vio en el post con los ojos: que «Onward» va dos
veces el mismo día y que la inaugural son dos funciones (7:00 el corto, 7:30 el
largo). Todos los festivales publican así. Si la herramienta no lee la imagen,
no lee el programa.

QUÉ HACE, sin sesión y re-corrible:

  1. Baja las láminas de cada post por el EMBED público (ig_carrusel.py) y las
     cachea en fuentes/ig/<shortcode>/.
  2. Las lee con OCR CON CAJAS (ficma-2026-ocr.swift): la posición importa
     porque una hora arriba a la derecha es el badge y una hora junto a «HORA:»
     es el campo; un título es la línea más alta de la mitad superior.
  3. De cada lámina saca lo que se pueda con reglas GENÉRICAS —horas, día del
     mes, campos por etiqueta (LUGAR/HORA/DIRECCIÓN/DURACIÓN/PAÍS/AÑO), título
     por tamaño— y también parsea el PIE si se le da (`--pies <json>`), que
     es la otra mitad de la misma fuente.
  4. CRUZA en las dos direcciones contra festivals/<id>.json:
       · lámina sin función nuestra a esa (día, hora)      → nos FALTA algo
       · función nuestra sin lámina ese día (día cubierto) → nos SOBRA o cambió
     y compara sede y título cuando los dos lados los tienen.

QUÉ NO HACE. No escribe la parrilla ni corrige nada: su salida es un informe,
y lo leído lámina por lámina queda en fuentes/ig/<id>-ig-leido.json (material
de trabajo, fuera del repo) para mirarlo cuando un aviso no se entienda.
Decidir sigue siendo del plan del festival — pero ahora con las láminas
leídas, no con el pie.

Sale con 1 si hay alguna discrepancia no declarada. Se declara en
festivals/staging/<id>-ig-correcciones.json —`ok`: lista de {shortcode,
lamina, por_que} o {titulo, por_que}— para que un aviso ya entendido no vuelva
a sonar. Cada entrada dice POR QUÉ: es lo que hace re-corrible la decisión.

    python3 pipeline/ig-programa.py ficma-2026 DdcEwsJmvmy DdcEFYkGnCR ...
    python3 pipeline/ig-programa.py ficma-2026 --pies scratch/pies.json Ddc...
"""
import io, json, os, re, subprocess, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, hora24
import ig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
SWIFT = f'{REPO}/pipeline/ficma-2026-ocr.swift'

RE_HORA = re.compile(r'\b\d{1,2}[:.]\d{2}\s*[ap]\.?\s*m\b\.?', re.I)
DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
RE_DIA = re.compile(r'\b(' + '|'.join(DIAS) + r')\s*(\d{1,2})\b', re.I)
MESES = {m: i + 1 for i, m in enumerate(['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
         'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'])}
RE_FECHA = re.compile(r'\b(\d{1,2})\s+de\s+(' + '|'.join(MESES) + r')\b', re.I)
ETIQUETAS = ('lugar', 'hora', 'direccion', 'duracion', 'pais', 'ano', 'seccion', 'sede')
# Líneas que nunca son título: marcas, patrocinios y el sello de presencia.
RUIDO = re.compile(r'presencia|ficma|alcald|secretar|cultura|fundaci|proyecto|estimulos|'
                   r'gobierno|ministerio|colombia\b|manizales$|sala oscura|cnacc|egeda|jardin|cosas perdidas|'
                   r'del director|de la directora|^\W*$', re.I)


GENERICAS = {'cine', 'sala', 'casa', 'centro', 'barrio', 'auditorio', 'teatro', 'parque',
             'manizales', 'cultural', 'cultura', 'universidad'}


def se_parecen(a, b):
    """Dos nombres de sede/obra se parecen si comparten una palabra que no sea
    genérica, o si el OCR los deja casi iguales («SOVORA» / «Sonora»)."""
    import difflib
    pa = {w for w in re.findall(r'[a-z0-9]{4,}', plano(a))} - GENERICAS
    pb = {w for w in re.findall(r'[a-z0-9]{4,}', plano(b))} - GENERICAS
    if pa & pb:
        return True
    a, b = plano(a).strip(), plano(b).strip()
    n = min(len(a), len(b))
    return difflib.SequenceMatcher(None, a[:n], b[:n]).ratio() >= 0.75


def plano(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').lower()


RE_RANGO = re.compile(r'(\d{1,2}[:.]\d{2}\s*[ap]\.?\s*m\.?)\s*(?:-|–|—|a|hasta)\s*(\d{1,2}[:.]\d{2}\s*[ap]\.?\s*m\.?)', re.I)


def horas_de(txt):
    """Las horas de INICIO que un texto anuncia. Un rango («10:00 am - 12:00 pm»)
    es una función con fin, no dos funciones; «1:30 pm & 4:00 pm» sí son dos."""
    txt = RE_RANGO.sub(lambda m: m.group(1), txt)
    return list(dict.fromkeys(hora24(m.group(0)) for m in RE_HORA.finditer(txt)))


def ocr(rutas):
    """{ruta: [líneas con caja]} — el swift indexa por basename, así que va por carpeta."""
    out = {}
    por_dir = {}
    for r in rutas:
        por_dir.setdefault(os.path.dirname(r), []).append(r)
    for d, rs in por_dir.items():
        p = subprocess.run(['swift', SWIFT] + rs, capture_output=True, text=True)
        if p.returncode:
            sys.exit(f'OCR falló en {d}: {p.stderr[:200]}')
        j = json.loads(p.stdout)
        for r in rs:
            out[r] = j.get(os.path.basename(r), [])
    return out


def leer_lamina(lineas, anio, mes_defecto):
    """Lo que una lámina dice, por reglas de posición y etiqueta."""
    txt = ' '.join(l['t'] for l in lineas)
    horas = horas_de(txt)
    # el día: primero el badge «SÁBADO 19» (es del programa), y solo si no hay,
    # una fecha escrita — que puede ser la del afiche de la obra, no la función
    dia = None
    m = RE_DIA.search(plano(txt))
    if m and mes_defecto:
        dia = f'{anio}-{mes_defecto:02d}-{int(m.group(2)):02d}'
    else:
        m = RE_FECHA.search(plano(txt))
        if m:
            dia = f'{anio}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}'
    # campos por etiqueta: «LUGAR:» y lo que sigue debajo, en la misma columna
    campos = {}
    for i, l in enumerate(lineas):
        t = plano(l['t']).strip(' :')
        for e in ETIQUETAS:
            if t == e or t.startswith(e + ':'):
                resto = l['t'].split(':', 1)[1].strip() if ':' in l['t'] and t != e else ''
                val = [resto] if resto else []
                for k in lineas[i + 1:]:
                    kt = plano(k['t']).strip(' :')
                    if any(kt == e2 or kt.startswith(e2 + ':') for e2 in ETIQUETAS):
                        break
                    if k['y'] - l['y'] > 0.2:
                        break
                    if abs(k['x'] - l['x']) > 0.06:
                        continue          # una línea de otra columna (créditos del afiche)
                    val.append(k['t'])
                campos[e] = ' '.join(val).strip()
    # título: la línea más ALTA de la mitad superior que no es hora, día ni ruido
    con_comillas = [l for l in lineas if l['y'] < 0.5 and re.search(r'[“"«].{3,}[”"»]', l['t'])]
    cand = con_comillas or [l for l in lineas if l['y'] < 0.3 and not RE_HORA.search(l['t'])
            and not RE_DIA.search(plano(l['t'])) and not RUIDO.search(l['t'])
            and len(l['t']) > 3 and l['w'] > 0.12]
    titulo = max(cand, key=lambda l: l['h'])['t'] if cand else ''
    titulo = re.sub(r'^[\s“"«]+|[\s”"»]+$', '', titulo)
    badge = [hora24(m.group(0)) for l in lineas if l['y'] < 0.1 for m in RE_HORA.finditer(l['t'])]
    hf = horas_de(campos.get('hora', ''))
    contradice = badge and hf and badge[0] != hf[0]
    if hf:
        horas = list(dict.fromkeys(hf + [h for h in horas if h not in badge or not contradice]))
    return {'dia': dia, 'horas': horas, 'titulo': titulo, 'campos': campos,
            'badge_vs_campo': f'badge {badge[0]} · HORA {hf[0]}' if contradice else ''}


RE_PIE = re.compile(r'^\s*[•·\-]\s*(.+?)\s*(?:\||–|—|-)?\s*$', re.M)


def leer_pie(pie, anio):
    """Las líneas «• 9:00 AM | Título … 📍 Sede» del pie, si las hay."""
    dia = None
    m = RE_FECHA.search(plano(pie))
    if m:
        dia = f'{anio}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}'
    out = []
    bloques = re.split(r'\n\s*(?=•)', pie)
    for b in bloques:
        b = b.strip()
        if not b.startswith('•'):
            continue
        horas = horas_de(b)
        if not horas:
            continue
        cuerpo = b.split('|', 1)[1] if '|' in b else RE_HORA.sub('', b)
        titulo = re.split(r'\(Dir\.|—|📍|\n', cuerpo)[0].strip(' •:')
        sede = ''
        ms = re.search(r'📍\s*(.+)', b)
        if ms:
            sede = ms.group(1).strip()
        out.append({'dia': dia, 'horas': horas, 'titulo': titulo, 'sede': sede})
    return dia, out


def main():
    args = [a for a in sys.argv[1:]]
    if len(args) < 2:
        sys.exit(__doc__)
    fid = args.pop(0)
    pies = {}
    if '--pies' in args:
        i = args.index('--pies')
        pies = json.load(io.open(args[i + 1], encoding='utf-8'))
        pies = pies.get('posts', pies)
        del args[i:i + 2]
    scs = args

    fest = json.load(io.open(f'{REPO}/festivals/{fid}.json', encoding='utf-8'))
    anio = fest['year']
    mes = None
    m = re.match(r'(\d{4})-(\d{2})', fest.get('festivalStartStr', ''))
    if m:
        mes = int(m.group(2))
    por_dia_hora = {}
    for f in fest['films']:
        por_dia_hora.setdefault((f['day'], f['time']), []).append(f)

    # pies indexados por shortcode, vengan como {dia: {shortcode, pie}} o lista
    pie_de = {}
    for k, v in (pies.items() if isinstance(pies, dict) else enumerate(pies)):
        pie_de[v.get('shortcode')] = v.get('pie', '')

    ok_p = f'{ST}/{fid}-ig-correcciones.json'
    # se declara por (shortcode, lámina) o, para lo nuestro que IG no trae, por título
    ok = {(o.get('shortcode') or o.get('titulo'), o.get('lamina', 0)): o['por_que']
          for o in (json.load(io.open(ok_p, encoding='utf-8')).get('ok', [])
                    if os.path.exists(ok_p) else [])}

    sidecar, avisos, dias_cubiertos = [], [], set()
    rutas_por_sc = {sc: ig.bajar_laminas(sc, ig.urls_laminas(sc)) for sc in scs}
    todas = [r for rs in rutas_por_sc.values() for r in rs]
    leido = ocr(todas)

    for sc in scs:
        dia_pie, items_pie = leer_pie(pie_de.get(sc, ''), anio)
        laminas = []
        dias_post = set()
        for n, r in enumerate(rutas_por_sc[sc], 1):
            lam = leer_lamina(leido[r], anio, mes)
            lam['archivo'] = os.path.relpath(r, REPO)
            lam['n'] = n
            laminas.append(lam)
            if lam['dia']:
                dias_post.add(lam['dia'])
        # cada post es UN día: la lámina que lea otra fecha (la del afiche) se corrige
        mayoria = dia_pie or (max(dias_post, key=lambda d: sum(l['dia'] == d for l in laminas))
                              if dias_post else None)
        for lam in laminas:
            if mayoria and lam['dia'] != mayoria:
                lam['dia_leido'], lam['dia'] = lam['dia'], mayoria
        dias_post = {mayoria} if mayoria else set()
        dias_cubiertos |= dias_post
        sidecar.append({'shortcode': sc, 'url': f'https://www.instagram.com/p/{sc}/',
                        'dia_pie': dia_pie, 'pie_items': items_pie, 'laminas': laminas})

        # lámina → nuestra parrilla
        for lam in laminas:
            if not lam['horas'] or not lam['dia']:
                if lam['titulo'] and lam['n'] > 1:   # la 1ª suele ser portada
                    avisos.append((sc, lam['n'], f'lámina {lam["n"]} sin hora o día legible: '
                                   f'«{lam["titulo"]}»'))
                continue
            if lam['badge_vs_campo']:
                avisos.append((sc, lam['n'], f'lámina {lam["n"]}: «{lam["titulo"]}» se contradice '
                               f'sola: {lam["badge_vs_campo"]}'))
            for h in lam['horas']:
                nuestras = por_dia_hora.get((lam['dia'], h), [])
                if not nuestras:
                    avisos.append((sc, lam['n'], f'lámina {lam["n"]}: {lam["dia"]} {h} '
                                   f'«{lam["titulo"]}» — NO tenemos función a esa hora'))
                    continue
                if lam['titulo'] and not any(se_parecen(lam['titulo'], f['title']) for f in nuestras):
                    avisos.append((sc, lam['n'], f'lámina {lam["n"]}: {lam["dia"]} {h} '
                                   f'«{lam["titulo"]}» — a esa hora tenemos '
                                   + ' / '.join(f['title'] for f in nuestras)))
                lugar = lam['campos'].get('lugar') or lam['campos'].get('sede')
                if lugar and not any(se_parecen(lugar, f['venue']) for f in nuestras):
                    avisos.append((sc, lam['n'], f'lámina {lam["n"]}: sede «{lugar}» ≠ '
                                   + ' / '.join(f['venue'] for f in nuestras)))
        # pie → nuestra parrilla (la misma fuente, escrita)
        for it in items_pie:
            if not it['dia']:
                continue
            for h in it['horas']:
                nuestras = por_dia_hora.get((it['dia'], h), [])
                if not nuestras:
                    avisos.append((sc, 0, f'pie: {it["dia"]} {h} «{it["titulo"]}» — NO '
                                   f'tenemos función a esa hora'))

    # nuestra parrilla → láminas: lo que publicamos un día cubierto y no está en IG
    vistos = set()
    for e in sidecar:
        for lam in e['laminas']:
            for h in lam['horas']:
                vistos.add((lam['dia'], h))
        for it in e['pie_items']:
            for h in it['horas']:
                vistos.add((it['dia'], h))
    for f in fest['films']:
        if f['day'] not in dias_cubiertos:
            continue
        if (f['day'], f['time']) not in vistos:
            avisos.append((f['title'], 0, f'publicamos {f["day"]} {f["time"]} «{f["title"]}» y NO '
                           f'está en el post de ese día'))

    os.makedirs(ig.CACHE, exist_ok=True)
    io.open(f'{ig.CACHE}/{fid}-ig-leido.json', 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram — carruseles de programación leídos LÁMINA POR LÁMINA (OCR con '
            'cajas) vía el embed público; el pie, si se dio, del volcado con sesión',
            posts=len(sidecar), laminas=sum(len(e['laminas']) for e in sidecar),
            url=[e['url'] for e in sidecar]),
        'posts': sidecar}, ensure_ascii=False, indent=1) + '\n')

    n_lam = sum(len(e['laminas']) for e in sidecar)
    print(f'{fid}: {len(sidecar)} posts · {n_lam} láminas · días cubiertos: '
          + ', '.join(sorted(dias_cubiertos)))
    pend = [(sc, n, msg) for sc, n, msg in avisos if (sc, n) not in ok]
    for sc, n, msg in avisos:
        if (sc, n) in ok:
            print(f'   · entendido ({ok[(sc, n)][:50]}): {msg[:80]}')
    for sc, n, msg in pend:
        print(f'   ✗ {sc}: {msg}')
    if pend:
        print(f'\n✗ {len(pend)} aviso(s) sin explicar — leer la lámina antes de decidir')
        sys.exit(1)
    print('\n✓ cada lámina tiene su función y cada función su lámina')


if __name__ == '__main__':
    main()
