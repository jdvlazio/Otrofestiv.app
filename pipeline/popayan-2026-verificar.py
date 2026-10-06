#!/usr/bin/env python3
"""popayan-2026-verificar.py — lo que se va a publicar, contra la página de programación.

Relee la página del festival por su cuenta —del HTML, con otro corte: busca
cada «<sede> / <hora>» en el texto plano entero, sin partir en renglones— y
exige, en los dos sentidos:
  · cada horario impreso está en el build con su día, hora y título, y el
    build no publica ninguna función que la página no traiga;
  · cada bloque del build lleva tantas obras como créditos «dirigido…» hay
    entre su horario y el siguiente en la página;
  · toda sede tiene pin verificado a mano, o su porqué escrito.

Desde la versión del 30 sep la página trae también la sede SOLA en un renglón
y debajo cada actividad con la hora delante («… Pantalla gigante 3:00 pm
Apertura muestra …», Terra Plaza), «6: 30 pm» con espacio, y funciones «solo
inscritos y aceptados» que no se publican. Este lector las busca a su manera,
en el texto plano, sin reusar el normalizador del crudo.
"""
import html
import io
import json
import os
import re
import sys
import unicodedata
import importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'popayan-2026'
CIUDAD = 'Popayán'
_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/popayan-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)
MESES_DIA = re.compile(r'(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+(\d{1,2})\s+de\s+octubre')
_H = r'(\d{1,2})(?::\s*(\d{2}))?\s*([ap])\.?\s*m\.?'
# En texto plano no hay dónde cortar la sede del título anterior: se anclan las
# sedes que imprime la página, y TODO « / <hora>» del texto tiene que ser una
# de ellas (una sede nueva no pasa en silencio).
# la sede que imprime la página → el prefijo de su sede en el build
SEDES_PAGINA = {'Teatro Bolívar': 'Teatro Bolívar', 'Auditorio Maya Facultad de Artes Unicauca': 'Facultad de Artes Unicauca',
                'Museo de Arte Moderno de Popayán MAMPO': 'Museo de Arte Moderno de Popayán MAMPO',
                'Casa Taller Sirirí': 'Casa Taller Sirirí', 'Mikuna Casa Cultural': 'Mikuna Casa Cultural',
                'Centro Comercial Terra Plaza – Pantalla gigante': 'Centro Comercial Terra Plaza'}
_SEDE = '(' + '|'.join(map(re.escape, SEDES_PAGINA)) + ')'
# desde el 6 oct la hora va también PEGADA a la sede, sin la barra
# («Teatro Bolívar 3 pm Muestra…», «… Pantalla gigante 2:00 pm Proyección…»)
HORARIO = re.compile(_SEDE + r'\s*(?:/\s*)?' + _H, re.I)
CUALQUIER_HORA = re.compile(r'\b\d{1,2}(?::\s*\d{2})?\s*[ap]\.?\s*m\b', re.I)
# la hora DELANTE de la actividad (Terra Plaza): con minutos, sin «/» antes, y
# seguida de mayúscula; la sede es la última impresa sola antes
DELANTE = re.compile(r'(?<![/\d:])(?<!/\s)\b(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s+(?=[A-ZÁÉÍÓÚ])')
CON_MINUTOS = re.compile(r'\b\d{1,2}:\s*\d{2}\s*[ap]\.?\s*m\b', re.I)
INSCRITOS = re.compile(r'inscritos\s+y\s+aceptados', re.I)


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    d = json.load(io.open(f'{REPO}/fuentes/{FID}/programacion2026.json', encoding='utf-8'))
    texto = html.unescape(re.sub(r'<[^>]+>', ' ', d['content']['rendered']))
    texto = re.sub(r'\s+', ' ', texto)
    # cortes: días y horarios, en orden de aparición
    horarios = list(HORARIO.finditer(texto))
    delante = [m for m in DELANTE.finditer(texto)]
    # una hora DELANTE que ya es la de un horario pegado a su sede no se cuenta dos veces
    ocupado = [(m.start(), m.end()) for m in horarios]
    delante = [m for m in delante if not any(a <= m.start() < b for a, b in ocupado)]
    marcas = sorted([(m.start(), 'dia', m) for m in MESES_DIA.finditer(texto)] +
                    [(m.start(), 'hor', m) for m in horarios] + [(m.start(), 'del', m) for m in delante],
                    key=lambda x: x[0])
    # COBERTURA INVERSA: toda hora que ARRANCA algo (la que no es el fin de un
    # rango «9 am – 1 pm») está en un horario con sede o delante de una actividad
    arranques = [m for m in CUALQUIER_HORA.finditer(texto)
                 if not re.search(r'[–-]\s*$|\by\s+\d{1,2}\s+a\s*$|\ba\s*$', texto[max(0, m.start() - 6):m.start()])]
    if len(arranques) != len(horarios) + len(delante):
        sys.exit(f'✗ {len(arranques)} horas que arrancan algo y {len(horarios)} con sede + {len(delante)} '
                 f'delante de una actividad: hay una forma nueva en la página')
    pagina, dia, fuera = [], None, 0
    for n, (pos, tipo, m) in enumerate(marcas):
        if tipo == 'dia':
            dia = f'2026-10-{int(m.group(2)):02d}'
            continue
        if tipo == 'hor':
            sede = m.group(1)
            hh, mm, ap = m.group(2), m.group(3), m.group(4)
        else:
            antes = [x for x in re.finditer(_SEDE, texto[:pos])]
            if not antes:
                sys.exit(f'✗ una hora delante de una actividad sin sede antes: {texto[pos:pos + 60]!r}')
            sede = antes[-1].group(1)
            hh, mm, ap = m.group(1), m.group(2), m.group(3)
        h = int(hh) % 12 + (12 if ap.lower() == 'p' else 0)
        hora = f'{h:02d}:{mm or "00"}'
        fin = marcas[n + 1][0] if n + 1 < len(marcas) else len(texto)
        tramo = texto[m.end():fin]
        # el rango de un taller («9 am – 1 pm y 2 a 5 pm») no es parte del título
        tramo = re.sub(r'^\s*[–-]\s*\d{1,2}(?::\d{2})?\s*[ap]m(\s+y\s+\d{1,2}\s+a\s+\d{1,2}\s*[ap]m)?', '', tramo)
        if INSCRITOS.search(tramo.split(' dirigid')[0]):
            fuera += 1
            continue
        # el título: hasta «Películas», o el nombre de la sede que abre la
        # tanda siguiente de Terra Plaza
        titulo = re.split(r'\s+Pel[ií]culas(?:\s+|$)|\s+' + _SEDE, tramo.strip(), maxsplit=1)[0].rstrip('. ')
        cred = lambda t: len(re.findall(r'dirigid[oa]s?\s*(?:y\s+producid[oa]s?\s*)?por', t, re.I))
        # LA FRANJA COMPARTIDA (6 oct): «Apertura del Festival Selección Oficial
        # Documental (primer bloque) …» bajo un solo «7:00 pm» — dos funciones
        par = re.match(r'^(Apertura del Festival)\s+(Selección Oficial.*)$', titulo)
        if par:
            pagina.append({'dia': dia, 'hora': hora, 'sede': SEDES_PAGINA[sede], 'titulo': par.group(1), 'creditos': 0})
            titulo = par.group(2)
        # el bloque que la página deja sin nombre: el que le declara el crudo
        decl = crudo.TITULO_SIN_NOMBRE.get((dia, hora, sede))
        if decl:
            titulo = decl
        pagina.append({'dia': dia, 'hora': hora, 'sede': SEDES_PAGINA[sede], 'titulo': titulo,
                       'creditos': cred(tramo)})
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    # la clave lleva la SEDE: el jueves a las 6:30 pm hay tres funciones a la vez
    pub = {(f['day'], f['time'], f['venue'].replace(f' - {CIUDAD}', ''), plano(f['title'])): f for f in build['films']}
    pag = {}
    for p in pagina:
        # el título de la página puede traer la descripción de la actividad detrás
        # («Vodcast en Vivo Grabación de Video Podcast…»): se busca el del build
        # que la abre
        t = plano(p['titulo'])
        # (6 oct: sin «Películas», el título de la página sigue con la primera
        # obra; y el build le pone «· Parte N» o la sede a los homónimos)
        base = lambda x: re.sub(r' (parte \d+|casa taller siriri|mikuna casa cultural)$', '', x)
        cand = [k for k in pub if k[:3] == (p['dia'], p['hora'], p['sede']) and
                (t == k[3] or t.startswith(base(k[3]) + ' ') or t == base(k[3]) or k[3].startswith(t + ' '))]
        # (y al revés: «CineCorto en el Barrio» en la página es «… · Casa Taller
        # Sirirí» en el build, el sufijo que le pone el crudo para distinguirlo)
        k = cand[0] if len(cand) == 1 else (p['dia'], p['hora'], p['sede'], t)
        pag[k] = max(pag.get(k, 0), p['creditos'])      # el par repetido del miércoles
    fallos = []
    for k, n in pag.items():
        f = pub.get(k)
        if not f:
            fallos.append(f'en la página y NO en el build: {k}')
        elif len(f.get('film_list') or []) != n:
            fallos.append(f'{k}: {n} créditos en la página, {len(f.get("film_list") or [])} obras en el build')
    for k in pub:
        if k not in pag:
            fallos.append(f'en el build y NO en la página: {k}')
    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None and not (g.get('_prec') == 'manual' and g.get('_todo')):
            fallos.append(f'sede {v!r} sin pin y sin porqué')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano')
    if fallos:
        sys.exit('✗ el build no coincide con la página:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ los {len(pag)} horarios de la página están en el build con sus obras '
          f'({sum(pag.values())}) y el build no publica ninguno más · {fuera} solo para inscritos, fuera · '
          f'{sum(1 for x in build["venues"].values() if x.get("lat") is not None)} sedes con pin manual, '
          f'{sum(1 for x in build["venues"].values() if x.get("lat") is None)} sin pin con su porqué')


if __name__ == '__main__':
    main()
