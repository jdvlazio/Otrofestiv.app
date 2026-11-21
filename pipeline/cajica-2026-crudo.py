#!/usr/bin/env python3
"""cajica-2026-crudo.py — Festival de Cine de Cajicá 2026 → crudo.

FUENTE ÚNICA: culturacajica.gov.co/festival-de-cine-2026/ (bajada a
fuentes/cajica-2026/ por `correr.py --bajar`). La programación vive en un
<script> como `const programacion=[...]` (día → eventos con hora, lugar,
categoría, requisito, tipo, título, datos, cortos con su minutaje y registros);
las inscripciones de los dos talleres del sábado, en el mapa `enlaces`.

COPY: el título es el de la web (Título por caja.py en ensamblar si grita);
la sección es la `categoria` de cada tarjeta TAL CUAL.

ACCESO: la web no publica ningún precio → libre (regla de Juan, 13 oct 2026).
Los talleres: «Requiere inscripción previa» con su URL. El taller de doblaje
trae dos modalidades: se publica la de participantes activos (20 cupos) y la de
oyentes (60 cupos) va en la nota.

COBERTURA INVERSA: todo evento de la web sale en el crudo (10); si suma uno, frena.
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import hora24, provenance  # noqa: E402

SRC = f'{REPO}/fuentes/cajica-2026/festival-de-cine-2026.html'
OUT = f'{REPO}/festivals/staging/cajica-2026-crudo.json'
URL = 'https://www.culturacajica.gov.co/festival-de-cine-2026/'
SEDE = 'Centro Cultural y de Convenciones Fernando Botero'
ESPERADOS = 10  # la web trae 10 tarjetas (20 nov); el brief decía 11

h = open(SRC, encoding='utf-8').read()
js = re.search(r'const programacion=(\[.*?\]);const escapar', h, re.S).group(1)
# objeto JS → JSON: claves sin comillas y `!0`
js = re.sub(r'([{,])([a-zA-Z_]+):', r'\1"\2":', js).replace('!0', 'true')
prog = json.loads(js)
enl = dict(re.findall(r'\["([^"]+)","(https://culturacajica\.app/[^"]+)"\]', h))


def mins(d):
    m = re.match(r'(\d+):(\d{2})', d)
    return round(int(m.group(1)) + int(m.group(2)) / 60)


def corto(c, categoria=''):
    t = c['titulo']
    o = {'titulo': t, 'duracion_min': mins(c['duracion']), '_duracion_fuente': c['duracion']}
    # País: SmartFilms es un concurso nacional colombiano; «Talento Local y Nacional» y el
    # teaser del IMCTC (Cajicá) también son de Colombia. El resto, sin país declarado (20 nov).
    if 'SmartFilms' in t or 'Talento Local y Nacional' in categoria or 'IMCTC' in t:
        o['pais'] = 'Colombia'
    if ' – ' in t:
        a, b = t.split(' – ', 1)
        o['titulo'] = a.strip()
        if b.strip() == 'SmartFilms':
            o['_nota'] = 'la web lo rotula «– SmartFilms»'
        else:
            o['director'] = b.strip()
    return o


# «Sangre de Dios»: sin ficha en TMDB (20 nov 2026) ni sinopsis del festival.
# La sinopsis se redacta desde la prensa del tráiler (Publimetro, 21 jul 2026,
# https://www.publimetro.co/cultura/2026/07/21/la-sangre-de-dios-revela-su-primer-trailer-la-nueva-pelicula-de-lucho-velasco-apuesta-por-la-accion-el-misterio-y-una-leyenda-ancestral-colombiana/).
LARGOS = {'SANGRE DE DIOS': dict(director='Lucho Velasco', pais='Colombia', anio=2026, sinopsis=(
              'Gabriel, un exmilitar dispuesto a todo por salvar a su hija, se cruza con Nahuel, un guerrero '
              'indígena que guarda un secreto ancestral, y con Jaime Almagro, un empresario farmacéutico que '
              'quiere convertirlo en negocio. Los tres se disputan en el cañón del Chicamocha «la sangre de Dios», '
              'una sustancia que, según la leyenda, vence la enfermedad y desafía la muerte.')),
          'TUNDAMA': dict(director='Diego Yaya, Edison Yaya', pais='Colombia')}
funciones = []
for dia in prog:
    for ev in dia['eventos']:
        lugar = ev['lugar']
        sala = lugar.split('— ')[-1]  # «Centro … — 3.er piso, Biblioteca» o la sala sola
        hora = ev['hora']
        f = {'titulo': ev['titulo'], 'dia': dia['fecha'], 'hora': hora24(hora),
             'sede': SEDE, 'sala': sala, 'seccion': ev['categoria'],
             '_src': {'url': URL, 'fecha': dia['titulo'], 'hora': hora, 'lugar': lugar,
                      'categoria': ev['categoria'], 'tipo': ev.get('tipo', ''),
                      'requisito': ev.get('requisito', '')}}
        datos = '; '.join(f"{d['etiqueta']}: {d['texto']}" for d in ev.get('datos', []))
        if ev.get('cortos'):
            f['obras'] = [corto(c, ev['categoria']) for c in ev['cortos']]
            f['acceso'] = 'Entrada libre'
        elif ev['titulo'] in LARGOS:
            f.update(LARGOS[ev['titulo']])
            # la web grita el título de los largos: se publica en caja de título
            f['titulo'] = {'SANGRE DE DIOS': 'Sangre de Dios', 'TUNDAMA': 'Tundama'}[ev['titulo']]
            f['acceso'] = 'Entrada libre'
        else:
            f['tipo'] = 'evento'
            f['event_kind'] = 'taller' if ev['estilo'] == 'taller' else 'conversatorio'
            f['invitados'] = datos
        if ev.get('requisito'):
            f['acceso'] = 'Entrada libre con inscripción previa'
            url = enl.get(ev['titulo']) or (ev.get('registros') or [{}])[0].get('url')
            if not url:
                sys.exit(f'taller sin enlace de inscripción: {ev["titulo"]}')
            f['registration_url'] = url
        f.setdefault('acceso', 'Entrada libre')
        r = re.match(r'.*?m\. a (.*)$', hora)
        if r:
            ini, fin = hora24(hora), hora24(r.group(1))
            f['duracion_min'] = (int(fin[:2]) * 60 + int(fin[3:])) - (int(ini[:2]) * 60 + int(ini[3:]))
            f['_duracion_de'] = f'la franja de la web «{hora}»'
        funciones.append(f)

if len(funciones) != ESPERADOS:
    sys.exit(f'la web trae {len(funciones)} actividades, se esperaban {ESPERADOS}: revisar')
for t in enl:
    assert any(f['titulo'] == t for f in funciones), f'enlace sin actividad: {t}'

out = {'_provenance': provenance(f'{URL} — const programacion + enlaces'), 'funciones': funciones}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(funciones)} funciones → {OUT}')
