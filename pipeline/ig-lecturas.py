#!/usr/bin/env python3
"""ig-lecturas.py <shortcode>… — CUATRO lecturas independientes de las láminas
de un carrusel de Instagram, y el informe de dónde no coinciden.

POR QUÉ EXISTE (22 sep 2026). Con Jardín verifiqué la parrilla «tres veces» y
se me cayó una película igual. La razón: las tres lecturas compartían camino.
A y B eran el MISMO motor de OCR con el MISMO parser sobre la misma imagen a
distinto tamaño, así que cuando el parser tiraba algo, lo tiraban las dos y
coincidían perfectamente. «Las lecturas están de acuerdo» no probaba nada.

Una lectura solo cuenta como independiente si falla por motivos distintos:

  A · Vision, con corrección de idioma       el camino de siempre
  B · Vision, SIN corrección de idioma       otro camino de DECODIFICACIÓN: con
                                             el corrector encendido Vision
                                             reescribe lo improbable contra su
                                             modelo de idioma. En la lámina 1 de
                                             Itagüí, A leyó «CIUDAD DE ITAGUI» y
                                             B «CIUDAD DE ITAGÜI»: el corrector
                                             se comió la diéresis del nombre del
                                             municipio.
  C · Vision sobre la lámina al doble        otro camino de RESOLUCIÓN: caza lo
                                             que se pierde por tamaño. El
                                             «(SO2E6)» de «Cien años de soledad»
                                             se leía a 1× y no a 2×.
  D · el texto ALT del post                  SIN OCR: la descripción que sirve
                                             el propio Instagram. No comparte
                                             ni motor ni píxeles.

Y la quinta, que no es automática y manda sobre las cuatro: MIRAR LA LÁMINA.
`--ojos <json>` recibe lo que se leyó a ojo y lo cruza como una lectura más.
Es la regla de Juan tras Jardín: el parser no se cree hasta haber comparado
cada imagen con lo que sacó.

QUÉ COMPARA. Tokens que importan, no registros parseados: horas, fechas,
duraciones, años y nombres propios. A propósito NO parsea el programa — un
comparador que pasa por el parser vuelve a tener el punto ciego que lo trajo
aquí. Su salida es un informe para ir a mirar la lámina.

    python3 pipeline/ig-lecturas.py DdmhX7gFIZa
    python3 pipeline/ig-lecturas.py DdmhX7gFIZa --salida fuentes/ig/itagui.json
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import ig  # noqa: E402

SWIFT = os.path.join(REPO, 'pipeline', 'ocr.swift')

# La hora se compara en 24h SIEMPRE. La lámina imprime «6:30 p. m.» y una
# transcripción a mano escribe «18:30»: sin aplicar el meridiano, las dos
# lecturas discrepan por construcción y el informe se llena de ruido que
# parece dato. Fueron 29 de 29 en la primera pasada de Itagüí.
RE_HORA = re.compile(r'\b(\d{1,2})[:.](\d{2})\s*(a\.?\s*m|p\.?\s*m)?', re.I)
RE_DURA = re.compile(r'\b(\d{1,3})\s*min', re.I)
RE_ANIO = re.compile(r'\b((?:19|20)\d{2})\b')
RE_DIA = re.compile(r'\b(\d{1,2})\s+de\s+[a-záéíóú]+', re.I)
# Un nombre propio: dos o más palabras capitalizadas seguidas, o una en VERSALES
# En la MISMA línea: `\s+` cruzaba saltos y pegaba «cola\ncamara» como si
# fuera un nombre propio, que es como la primera corrida produjo 175 avisos
# de basura.
RE_PROPIO = re.compile(
    r'\b([A-ZÁÉÍÓÚÑÜ][\wáéíóúñü]{2,}(?:[^\S\n]+[A-ZÁÉÍÓÚÑÜ][\wáéíóúñü]{2,})+)')


def sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn').lower()


def tokens(texto):
    """Lo que importa de una lectura, sin pasar por ningún parser."""
    t = {}
    horas = set()
    for h, m, mer in RE_HORA.findall(texto):
        hh = int(h)
        mer = (mer or '').replace('.', '').replace(' ', '').lower()
        if mer.startswith('p') and hh < 12:
            hh += 12
        elif mer.startswith('a') and hh == 12:
            hh = 0
        horas.add(f'{hh % 24:02d}:{m}')
    t['horas'] = horas
    t['duraciones'] = {f'{int(n)} min' for n in RE_DURA.findall(texto)}
    t['anios'] = set(RE_ANIO.findall(texto))
    t['dias'] = {sin_tildes(x) for x in RE_DIA.findall(texto)}
    t['propios'] = {sin_tildes(x) for x in RE_PROPIO.findall(texto)}
    return t


# LA FRANJA DE LOGOS NO ES PROGRAMACIÓN. Todo festival firma sus láminas con
# una tira de patrocinadores al pie, y ahí el OCR nunca coincide consigo mismo
# porque son LOGOTIPOS, no texto: «COMFAMA»/«comtama»/«ComfAmA», «PBA»/«PвA».
# En Itagüí esa franja produjo el 100% de las 175 discrepancias de la primera
# corrida y tapó las de verdad. Se recorta por geometría, no por lista negra.
PIE = 0.88


def vision(rutas, correccion=True, pie=PIE):
    cmd = ['swift', SWIFT, '--cajas']
    if not correccion:
        cmd.append('--sin-correccion')
    r = subprocess.run(cmd + list(rutas), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'✗ Vision falló ({r.returncode}): {(r.stderr or "")[:300]}')
    out = {}
    for linea in r.stdout.splitlines():
        if not linea.strip():
            continue
        d = json.loads(linea)
        cajas = [c for c in d.get('cajas', []) if c['y'] < pie]
        out[os.path.basename(d['ruta'])] = '\n'.join(c['t'] for c in cajas)
    return out


def al_doble(rutas, destino):
    """Las mismas láminas al 200%, cacheadas: el OCR es lo caro."""
    from PIL import Image
    os.makedirs(destino, exist_ok=True)
    out = []
    for p in rutas:
        dst = os.path.join(destino, os.path.basename(p))
        if not os.path.exists(dst):
            im = Image.open(p)
            im.resize((im.width * 2, im.height * 2), Image.LANCZOS).save(dst, quality=95)
        out.append(dst)
    return out


def alt_del_post(sc):
    """La descripción que sirve Instagram. No comparte ni motor ni píxeles."""
    r = subprocess.run(['python3', os.path.join(REPO, 'pipeline', 'ig_carrusel.py'), sc],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {}, ''
    alts = {}
    for i, lam in enumerate(d.get('laminas', [])):
        if lam.get('alt'):
            alts[f'{i:02d}.jpg'] = lam['alt']
    return alts, d.get('caption') or ''


def informe(lecturas, ojos=None):
    """Dónde NO coinciden. Un token que solo tiene una lectura hay que mirarlo."""
    if ojos:
        lecturas = dict(lecturas, **{'E·la mirada': ojos})
    laminas = sorted({k for v in lecturas.values() for k in v})
    avisos = []
    for lam in laminas:
        tk = {n: tokens(v.get(lam, '')) for n, v in lecturas.items()}
        presentes = {n for n in tk if lecturas[n].get(lam)}
        if len(presentes) < 2:
            continue
        for clase in ('horas', 'duraciones', 'anios', 'dias', 'propios'):
            todos = set().union(*(tk[n][clase] for n in presentes))
            for val in sorted(todos):
                tienen = {n for n in presentes if val in tk[n][clase]}
                if len(tienen) == len(presentes):
                    continue
                # el ALT y la mirada no transcriben la lámina entera: solo
                # cuentan cuando AÑADEN algo que el OCR no vio
                ocr = {n for n in presentes if n.startswith(('A', 'B', 'C'))}
                if not (tienen & ocr) and (ocr & presentes):
                    avisos.append((lam, clase, val, sorted(tienen), 'solo fuera del OCR'))
                elif tienen & ocr and len(tienen & ocr) < len(ocr & presentes):
                    avisos.append((lam, clase, val, sorted(tienen), 'las lecturas de OCR difieren'))
    return avisos


def main():
    # OJO: las banderas con valor se llevan su valor. Sin esto, `--salida x.json`
    # metía «x.json» como si fuera un shortcode.
    _con_valor = {'--salida', '--ojos', '--pie'}
    args, _saltar = [], False
    for a in sys.argv[1:]:
        if _saltar:
            _saltar = False
            continue
        if a in _con_valor:
            _saltar = True
            continue
        if not a.startswith('--'):
            args.append(a)
    if not args:
        sys.exit(__doc__)
    salida = None
    if '--salida' in sys.argv:
        salida = sys.argv[sys.argv.index('--salida') + 1]
    ojos = None
    if '--ojos' in sys.argv:
        ojos = json.load(open(sys.argv[sys.argv.index('--ojos') + 1], encoding='utf-8'))

    todo = {}
    for sc in args:
        rutas = ig.bajar_laminas(sc, ig.urls_laminas(sc))
        if not rutas:
            sys.exit(f'✗ {sc}: sin láminas. Instagram a veces no sirve el embed; '
                     f'abrilo en el NAVEGADOR y guardalas en fuentes/ig/{sc}/.')
        dobles = al_doble(rutas, os.path.join(ig.CACHE, f'{sc}-x2'))
        alts, pie = alt_del_post(sc)
        lecturas = {
            'A·vision':        vision(rutas, correccion=True),
            'B·sin-corrector': vision(rutas, correccion=False),
            'C·al-doble':      vision(dobles, correccion=True),
            'D·alt':           alts,
        }
        print(f'\n═══ {sc} · {len(rutas)} láminas')
        for n, v in lecturas.items():
            con = sum(1 for x in v.values() if x.strip())
            print(f'   {n:17} {con}/{len(rutas)} láminas con texto')
        if not alts:
            print('   ⚠ D·alt vacío — Instagram no sirvió descripción; quedan 3 lecturas')

        avisos = informe(lecturas, ojos and ojos.get(sc))
        print(f'\n   {len(avisos)} discrepancia(s) — cada una es una lámina que hay que MIRAR:')
        for lam, clase, val, tienen, por_que in avisos[:60]:
            print(f'      {lam} · {clase[:11]:11} «{val[:44]}» ← solo {", ".join(tienen)} ({por_que})')
        if len(avisos) > 60:
            print(f'      … y {len(avisos) - 60} más (están todas en el JSON de salida)')
        todo[sc] = {'lecturas': lecturas, 'pie': pie,
                    'discrepancias': [{'lamina': a, 'clase': b, 'valor': c,
                                       'solo_en': d, 'por_que': e} for a, b, c, d, e in avisos]}

    if salida:
        os.makedirs(os.path.dirname(salida) or '.', exist_ok=True)
        io.open(salida, 'w', encoding='utf-8').write(
            json.dumps(todo, ensure_ascii=False, indent=1) + '\n')
        print(f'\n✓ {salida}')


if __name__ == '__main__':
    main()
