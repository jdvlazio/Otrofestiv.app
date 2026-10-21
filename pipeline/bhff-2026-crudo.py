#!/usr/bin/env python3
"""bhff-2026-crudo.py — la programación del 8° Bogotá Horror Film Festival → crudo.

LAS FUENTES, todas del festival:
  · bogotahorrorfilmfest.com/programacion/ — la parrilla vive en el HTML como
    un arreglo JS (`const PROGRAMACION = [...]`) que la página dibuja: día, hora,
    sala, título, ficha («Dir. … · año · país · min») y tipo de función;
  · la Selección (bhff-2026-catalogo.json, sus 39 láminas);
  · los cortos de cada FRANJA vienen en la misma parrilla (`cortos`); los de las
    nacionales se contrastan contra el carrusel de Instagram (p/DdcszK2Dn7g,
    18 sep, leído por el embed público, sin sesión): mismo título y mismos
    minutos, o no se escribe nada;
  · prensa (Canal Trece, Semana): las direcciones de Casa 32 y Co.Laboratorio y
    el acceso — $7.000 en la Cinemateca de Bogotá; libre hasta completar aforo en
    cinematecas locales y espacios comunitarios.

LO QUE NO SE INVENTA:
  · «Cinematecas locales» son DOS (El Tunal y Fontanar del Río, Canal Trece) y
    el festival no dice cuál es cada función: quedan FUERA hasta que responda.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import DESCONOCIDO, provenance  # noqa: E402

DIR = f'{REPO}/fuentes/bhff-2026'
PROG_HTML = f'{DIR}/programacion.html'
CAT = f'{REPO}/festivals/staging/bhff-2026-catalogo.json'
FRANJAS_IG = f'{REPO}/fuentes/ig/DdcszK2Dn7g/post.json'
DESTINO = f'{REPO}/festivals/staging/bhff-2026-crudo.json'
URL = 'https://bogotahorrorfilmfest.com/programacion/'
IG = 'https://www.instagram.com/p/DdcszK2Dn7g/'
MES = {'OCT': 10}

# LA SALA de la parrilla → (sede, sala)
SEDES = {
    'Sala Capital': ('Cinemateca de Bogotá', 'Sala Capital'),
    'Sala 3': ('Cinemateca de Bogotá', 'Sala 3'),
    'Casa 32': ('Casa 32', ''),
    'CEFE Chapinero': ('Centro Felicidad Chapinero', ''),
    'Co - Laboratorio': ('Co.Laboratorio', ''),
}
NO_SE_SABE = {'Cinematecas locales': 'son dos (El Tunal y Fontanar del Río, según Canal Trece) y el festival '
                                     'no dice cuál es cada función; preguntado'}
# EL ACCESO, por sede (prensa: Canal Trece)
ACCESO = {'Cinemateca de Bogotá': 'Con boleta: $7.000'}
ACCESO_COMUNITARIO = 'Entrada libre hasta completar aforo'
# LA AUTORÍA que la parrilla da incompleta, corregida con el afiche de la obra
DIRECTOR = {
    'Ruth': ('Santiago Correa, Raquel Zapata, Marvin Cardona',
             'el afiche (lámina 39 de la Selección): «un film de Santiago Correa, Raquel Zapata, Marvin Cardona»; '
             'la parrilla y el IG dan solo a Marvin Cardona y la lámina solo a Santiago Correa'),
    'Yatsi y el Espíritu del Río': ('Valeria Salinas Yábar, Rous Condori Arango',
                                    'la lámina 22 de la Selección y el sitio de la directora (cargocollective.com/rous) '
                                    'dicen «Rous»; la parrilla, «Roux»'),
}

# «EL TEATRO» (15 oct, decisión de Juan): la parrilla lo llama «El Teatro:
# Monólogo de Horror» y no da director; el afiche y el pie del post de Casa 32
# (IG p/DecSAQRkevW, lámina 3) dicen «El Teatro — Cuidado con lo que deseas»,
# «De el director Nicolás Bernal», «Escrito por Alexander Mosquera». Manda el
# título del afiche de la obra
# El inicio de Parapeto (19:30, IG del festival) es una afirmación del modelo de la
# función: festivals/staging/bhff-2026-afirmaciones.json (docs/FUNCION.md)
TITULO_OBRA = {'El Teatro: Monólogo de Horror': 'El Teatro'}
DIRECTOR['El Teatro'] = ('Nicolás Bernal', 'afiche y pie de IG p/DecSAQRkevW (lámina 3): «De el director Nicolás Bernal»')

# EL AÑO que la parrilla da distinto de todas las demás fuentes
ANIO = {
    'Quazar': (2023, 'TMDB 1786245 (estreno 2023), Fantasmagoría 2026 y Villa del Cine 2026 dicen 2023; '
                     'solo la parrilla de BHFF dice 2026'),
}


def directores(s):
    """«A y B», «A / B», «A & B» → «A, B»."""
    return re.sub(r'\s+(?:y|/|&)\s+', ', ', s)
# LOS TALLERES no están en la parrilla ni traen fecha en su página
# (bogotahorrorfilmfest.com/talleres/): la fecha, la hora y la sala vienen del
# post de cada uno en Instagram (embed público, sin sesión). Inscripción
# gratuita con cupos limitados, dice la página. Sin duración publicada: va sin.
# LA TABLA DEL FESTIVAL (21 oct 2026), LA QUE MANDA: BHFF le respondió a Juan
# por mensaje con una imagen de su formulario de inscripción y la frase «Sigue
# como está en el formulario» (fuentes/bhff-2026/festival-mensaje-talleres-
# 20261021.jpg). La tabla, verbatim:
#   22 DE OCTUBRE. 3 PM — La Oscuridad y sus Ecos. Un siglo de monstruos — Yeimy Cardozo
#   22 DE OCTUBRE. 5 PM — Creando con las garras — Natt Martinez
#   (la tabla escribe sin tildes; los nombres van con la suya: «Martínez» como en el post
#   Deu5XIPuFHo, «Alarcón» como en Des_xjFN9gL — 21 oct 2026)
#   23 DE OCTUBRE. 3 PM — De la idea al guion — Jhonny Ortiz Alarcon
#   23 DE OCTUBRE. 5 PM — VFX para no técnicos: ¿Cómo hacer cine con VFX y no morir en el intento? — Guillermo Restrepo
#   24 DE OCTUBRE. 3 PM — Arte FX — Camilo Vélez
# Título e invitado van con la grafía de la tabla. Las afirmaciones
# «festival-mensaje» (bhff-2026-afirmaciones.json) llevan la frase literal.
# Sala: Lab 1 donde un post lo dice (Des_xjFN9gL, Deu5XIPuFHo, Dd-WRmzutXX,
# Dd-KmzEOkzm); «La Oscuridad y sus Ecos» no tiene post ni sala en ninguna
# fuente → la sede sin sala. Duración: ninguna fuente la publica → la estima
# el modelo (marca estimado).
# «Creando con las garras» es la que se publicó como «Maquillaje con las
# Garras» (f_d5b931d897): mismo id, título anterior declarado.
# url: el formulario del festival (la imagen es de él); la imagen vive en fuentes/,
# que no se versiona
MENSAJE = 'https://docs.google.com/forms/d/e/1FAIpQLSfYpIeJpeGTK1Co7ki-TKppGVm5ddRRy9pFZker683OKRTJtQ/viewform'
TALLERES = [
    {'titulo': 'La Oscuridad y sus Ecos. Un siglo de monstruos', 'dia': '2026-10-22', 'hora': '15:00',
     'invitados': 'Yeimy Cardozo', 'sala': None},
    {'titulo': 'Creando con las garras', 'dia': '2026-10-22', 'hora': '17:00', 'invitados': 'Natt Martínez',
     'ig': 'Deu5XIPuFHo'},
    {'titulo': 'De la idea al guion', 'dia': '2026-10-23', 'hora': '15:00', 'invitados': 'Jhonny Ortiz Alarcón',
     'ig': 'Des_xjFN9gL'},
    {'titulo': 'VFX para no técnicos: ¿Cómo hacer cine con VFX y no morir en el intento?', 'dia': '2026-10-23',
     'hora': '17:00', 'invitados': 'Guillermo Restrepo', 'ig': 'Dd-WRmzutXX'},
    {'titulo': 'Arte FX', 'dia': '2026-10-24', 'hora': '15:00', 'invitados': 'Camilo Vélez', 'ig': 'Dd-KmzEOkzm',
     'registration_url': 'https://docs.google.com/forms/d/e/1FAIpQLSfYpIeJpeGTK1Co7ki-TKppGVm5ddRRy9pFZker683OKRTJtQ/viewform'},
]
TALLERES_FUERA = ['Encuentro de Realizadores de Género: no está en la tabla del festival (mensaje, 21 oct) ni tiene fecha publicada']
# el tipo de función de la parrilla
KIND = {'Inauguración': 'apertura', 'Clausura': 'clausura'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def programacion():
    c = io.open(PROG_HTML, encoding='utf-8').read()
    i = c.index('const PROGRAMACION = [')
    j = c.index('];', i)
    js = c[i + len('const PROGRAMACION = '):j + 1]
    # del literal JS a JSON: claves sin comillas, comillas simples no hay
    js = re.sub(r'([{,]\s*)([a-zA-Z_]+)\s*:', r'\1"\2":', js)
    js = re.sub(r',\s*([\]}])', r'\1', js)
    return json.loads(js)


def franjas_ig():
    """Las franjas nacionales del carrusel: NOMBRE → [(título, director, año, min)]."""
    pie = json.load(io.open(FRANJAS_IG, encoding='utf-8'))['pie']
    out, actual = {}, None
    for x in [y.strip() for y in pie.split('\n')]:
        m = re.match(r'^(.+?) — (.+?) \((\d{4})\)(?: · (\d+) min)?$', x)
        if m and actual:
            out[actual].append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4)) if m.group(4) else None))
        elif x and x == x.upper() and not x.startswith('FRANJA') and len(x) > 4 and '·' not in x:
            actual = x
            out[actual] = []
    return {k: v for k, v in out.items() if v}


def hora(h, p):
    hh, mm = (int(x) for x in h.split(':'))
    if p.upper().startswith('P') and hh < 12:
        hh += 12
    return f'{hh:02d}:{mm:02d}'


def pais(s):
    """«Uruguay / Argentina» → «Uruguay, Argentina»; «USA» → «Estados Unidos» (el nombre que usan los demás festivales)."""
    return ', '.join({'USA': 'Estados Unidos'}.get(x.strip(), x.strip()) for x in s.split('/'))


def ficha(meta):
    """«Dir. X · 2026 · Colombia · 124 min» (+ «<b>+ Corto</b> — Dir · año · país · min»)."""
    principal, *extra = re.split(r'\s*<b>\+\s*', meta or '')
    p = [x.strip() for x in principal.split('·')]
    d = {}
    if p and p[0].startswith('Dir.'):
        d['director'] = directores(p[0][4:].strip())
    for x in p[1:]:
        if re.fullmatch(r'(19|20)\d{2}', x):
            d['anio'] = int(x)
        elif re.fullmatch(r'\d+ min', x):
            d['duracion_min'] = int(x.split()[0])
        elif x and 'Programa' not in x:
            d['pais'] = pais(x)
    cortos = []
    for e in extra:
        t, _, resto = e.partition('</b>')
        q = [x.strip() for x in resto.strip(' —').split('·')]
        c = {'titulo': t.strip()}
        if q and q[0] and not re.fullmatch(r'(19|20)\d{2}|\d+ min', q[0]):
            c['director'] = directores(q[0])
        for x in q[1:]:
            if re.fullmatch(r'(19|20)\d{2}', x):
                c['anio'] = int(x)
            elif re.fullmatch(r'\d+ min', x):
                c['duracion_min'] = int(x.split()[0])
            elif x:
                c['pais'] = pais(x)
        cortos.append(c)
    return d, cortos


def main():
    P = programacion()
    O = {plano(o['titulo']): o for o in json.load(io.open(CAT, encoding='utf-8'))['obras']}
    F = {plano(k): v for k, v in franjas_ig().items()}
    funciones, fuera, fallos = [], [], []
    n = 0
    for d in P:
        dia = f'2026-{MES[d["mes"]]:02d}-{int(d["dia"]):02d}'
        for e in d['eventos']:
            n += 1
            if e['sala'] in NO_SE_SABE:
                fuera.append(f'{dia} {e["titulo"]}: {NO_SE_SABE[e["sala"]]}')
                continue
            if e['sala'] not in SEDES:
                fallos.append(f'{dia} {e["titulo"]}: sala sin entrada en la tabla: {e["sala"]!r}')
                continue
            sede, sala = SEDES[e['sala']]
            r = {'dia': dia, 'hora': hora(e['hora'], e['periodo']), 'sede': sede,
                 'acceso': ACCESO.get(sede, ACCESO_COMUNITARIO),
                 '_src': {'url': URL, 'date': '2026-09-26'}}
            if sala:
                r['sala'] = sala
            act = e.get('act') or ''
            if 'Conversatorio' in act:
                r['has_qa'], r['qa_type'] = True, 'team'
            principal, cortos = ficha(e.get('meta'))
            t = e['titulo']
            if t.startswith('Franja '):
                nombre = t.split('·', 1)[1].strip()
                r.update({'titulo': nombre, 'seccion': t.split('·')[0].strip()})
                dur = re.search(r'(\d+) min', e.get('meta') or '')
                obras = [ficha(c.replace('<b>', '<b>+ ', 1))[1][0] for c in e.get('cortos') or []]
                for o in obras:
                    if o['titulo'] == o['titulo'].upper():
                        o['titulo'] = (O.get(plano(o['titulo'])) or {}).get('titulo', o['titulo'])
                    if o['titulo'] in DIRECTOR:
                        o['director'], o['_director_fuente'] = DIRECTOR[o['titulo']]
                    if o['titulo'] in ANIO:
                        o['anio'], o['_anio_fuente'] = ANIO[o['titulo']]
                ig = F.get(plano(nombre))
                if t.startswith('Franja Nacional'):
                    # el IG no da los minutos de todos: ahí se compara solo el título
                    b = [(plano(x[0]), x[3]) for x in ig or []]
                    a = [(plano(o['titulo']), o.get('duracion_min') if j >= len(b) or b[j][1] else None)
                         for j, o in enumerate(obras)]
                    if a != b:
                        fallos.append(f'{nombre}: la parrilla y el IG no dan los mismos cortos:\n      {a}\n      {b}')
                    r['_src']['franja'] = IG
                if obras:
                    r['obras'] = obras
                r['duracion_min'] = int(dur.group(1)) if dur else None
            elif act in KIND or t.startswith('Clausura'):
                r.update({'titulo': t, 'tipo': 'evento', 'event_kind': KIND.get(act, 'clausura'),
                          'seccion': 'Clausura', 'sinopsis': (e.get('meta') or '').strip() + '.'})
                r['duracion_min'] = 120
            else:
                r.update({'titulo': t, **principal})
                r['seccion'] = 'Inauguración' if act.startswith('Inauguración') else 'Proyecciones'
                if act.startswith('Inauguración'):
                    r['premiere'] = 'Inauguración'
                if cortos:
                    # LA FUNCIÓN DOBLE: el largo + el corto que lo acompaña («<b>+ Chaika</b>»)
                    obras = [{'titulo': t, **principal}] + cortos
                    for o in obras:
                        o['titulo'] = TITULO_OBRA.get(o['titulo'], o['titulo'])
                        if o['titulo'] in DIRECTOR:
                            o['director'], o['_director_fuente'] = DIRECTOR[o['titulo']]
                        if not o.get('pais') and (O.get(plano(o['titulo'])) or {}).get('pais'):
                            o['pais'] = O[plano(o['titulo'])]['pais']
                    r = {k: v for k, v in r.items() if k not in ('director', 'anio', 'pais')}
                    r['titulo'] = ' + '.join(o['titulo'] for o in obras)
                    r['obras'] = obras
                    r['duracion_min'] = sum(o.get('duracion_min') or 0 for o in obras) or None
            funciones.append({k: v for k, v in r.items() if v not in (None, '')})
    for x in TALLERES:
        t = {'dia': x['dia'], 'hora': x['hora'], 'sede': 'Cinemateca de Bogotá', 'sala': x.get('sala', 'Lab 1'),
             'acceso': 'Entrada libre con inscripción previa · Cupos limitados',
             'titulo': x['titulo'], 'tipo': 'evento', 'event_kind': 'taller', 'seccion': 'Talleres',
             'invitados': x['invitados'], 'registration_url': x.get('registration_url'),
             '_src': {'url': MENSAJE, 'date': '2026-10-21', 'acceso': 'https://bogotahorrorfilmfest.com/talleres/',
                      **({'ig': f'https://www.instagram.com/p/{x["ig"]}/'} if x.get('ig') else {})}}
        funciones.append({k: v for k, v in t.items() if v not in (None, '')})
    fuera += TALLERES_FUERA
    if len(funciones) - len(TALLERES) + len(fuera) - len(TALLERES_FUERA) + len(fallos) != n:
        fallos.append(f'{n} eventos y {len(funciones)} funciones + {len(fuera)} fuera')
    if fallos:
        sys.exit('✗ la programación no cuadra:\n  · ' + '\n  · '.join(fallos))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('bogotahorrorfilmfest.com/programacion/ (arreglo PROGRAMACION del HTML) + '
                                  'IG p/DdcszK2Dn7g (franjas nacionales)', url=URL,
                                  metodo='la parrilla del sitio; los cortos de cada franja, del carrusel'),
        '_fuera': fuera, 'funciones': funciones}, ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones ({sum(1 for f in funciones if f.get("obras"))} con obras) · '
          f'{len(fuera)} fuera → {os.path.relpath(DESTINO, REPO)}')
    for x in fuera:
        print('   fuera ·', x)


if __name__ == '__main__':
    main()
