#!/usr/bin/env python3
"""cineparalapaz-2026-crudo.py — la PROGRAMACIÓN del IV Festival Cine para la Paz → crudo.

LA FUENTE (16 nov 2026, la detectó el vigía): IG @cineparalapaz, carrusel
p/DfzeOb2lq6q, «IV FESTIVAL CINE PARA LA PAZ · PROGRAMACIÓN 2026», 5 láminas
(00 portada «18–21 noviembre 2026 · Bogotá»; 01–04 un día cada una, con sede,
dirección y franjas). Leídas a ojo en fuentes/ig/DfzeOb2lq6q-x2/; segunda y
tercera lectura: ig-lecturas.py (Vision y tesseract) contra este crudo.

QUÉ CAMBIÓ RESPECTO A LA SELECCIÓN OFICIAL (Dfk4smulKBB, 10 nov): las
franjas de cada obra. Manda la programación, que es la más nueva y la que dice
sede y hora. «La niebla de la paz» (Joel Stangle) está en la Selección pero NO
en la programación: no se publica función (queda en el catálogo).
Tres obras NUEVAS que no estaban en la Selección: «LezAma. Vivir filmando»,
«Horizonte» (César Acevedo) y «Mindalae – Viajero Kichwa» (Samia Maldonado).

UNA FRANJA CON VARIAS OBRAS = UN BLOQUE (función con sus obras); su duración
es la de la franja que imprime la lámina.

ACCESO: ninguna lámina ni post dice precio, salvo el cierre musical («Cover:
$20.000»). Regla de Juan (13 oct): sin aviso de pago = entrada libre.

Escribe festivals/staging/cineparalapaz-2026-crudo.json
"""
import io, json, os, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/cineparalapaz-2026-crudo.json'
CAT = f'{REPO}/festivals/staging/cineparalapaz-2026-catalogo.json'
URL = 'https://www.instagram.com/p/DfzeOb2lq6q/'
LIBRE = 'Entrada libre'
TROCHA = 'La Trocha · Casa de la Paz'
CENTRAL = 'Universidad Central'
LUBIANKA = 'Lubianka'
TULLPA = 'Centro Cultural La Tullpa'
ALPAMANDA = 'Alpamanda Peña Cultural'
SEL = 'Selección Oficial'                        # el título del carrusel de las 17 obras (Dfk4smulKBB)
ESP = 'Proyecciones especiales'                  # PROPUESTA para Juan: las 3 obras fuera de la Selección
ACT = 'Encuentros y actividades'                 # PROPUESTA para Juan: encuentro, conversatorio, premiación, música

# (día, inicio, fin, título, sede, sala, sección, lámina, obras[(título, min)], extra)
F = [
    ('18', '09:00', '11:00', 'Encuentro con Boris Guevara', TROCHA, None, ACT, '01.jpg', [],
     dict(tipo='evento', event_kind='encuentro',
          descripcion='Fragmentos y diálogo sobre su trayectoria audiovisual. Modera: Pedro Adrián Zuluaga.')),
    ('18', '11:00', '13:00', 'Selección Oficial', TROCHA, None, SEL, '01.jpg',
     [('Hecho a mano', 10), ('Refugiar el Gesto', 11), ('La coca: Buen vivir del pueblo Nasa', 19),
      ('La pandemia del feminicidio en Colombia', 23)], {}),
    ('18', '14:00', '15:00', 'Selección Oficial', TROCHA, None, SEL, '01.jpg',
     [('Kinesis', 10), ('Manos que dan vida', 15), ('Cajamarca: El viaje del desengaño', 21)], {}),
    ('18', '15:00', '17:00', 'LA + Taller: Autorretrato como una herramienta para la salud menstrual', TROCHA, None, SEL,
     '01.jpg', [('LA', 62)], dict(tipo='evento', event_kind='taller')),
    ('19', '09:00', '11:00', 'LezAma. Vivir filmando', CENTRAL, 'Caja de Colores', ESP, '02.jpg', [('LezAma. Vivir filmando', 52)],
     dict(has_qa=True, qa_type='team',
          descripcion='Proyección y conversatorio con Emmanuel Jaramillo, productor general. Modera: Diego Pachón.')),
    ('19', '11:00', '13:00', 'Selección Oficial', CENTRAL, 'Caja de Colores', SEL, '02.jpg',
     [('De la misma Tierra', 19), ('Medellín, yo te saludo', 4), ('Un berraco Partido', 10),
      ('Un Milagro Cada Día', 26), ('Nueve jueves en Riachuelo', 24), ('Paseando Te Cuento', 9)], {}),
    ('20', '11:00', '12:00', 'Conversatorio "La Propia Inopia"', LUBIANKA, None, ACT, '03.jpg', [],
     dict(tipo='evento', event_kind='conversatorio')),
    ('20', '13:00', '15:05', 'Horizonte', LUBIANKA, None, ESP, '03.jpg', [('Horizonte', 125)], {}),
    ('20', '15:15', '16:30', 'Por una gota de leche', LUBIANKA, None, SEL, '03.jpg', [('Por una gota de leche', 60)],
     dict(has_qa=True)),
    ('20', '16:40', '17:00', '¿Una pola o qué?', LUBIANKA, None, SEL, '03.jpg', [('¿Una pola o qué?', 15)], {}),
    ('20', '18:00', None, 'Premiación', LUBIANKA, None, ACT, '03.jpg', [], dict(tipo='evento', event_kind='premiación')),
    ('20', '21:00', None, 'Cierre musical · Concierto andino: Yananty y Runa Taky', ALPAMANDA, None, ACT, '03.jpg', [],
     dict(tipo='evento', event_kind='concierto', acceso='Con boleta: cover $20.000')),
    ('21', '15:00', None, 'Mindalae – Viajero Kichwa', TULLPA, None, ESP, '04.jpg', [('Mindalae – Viajero Kichwa', 76)],
     dict(descripcion='Proyección internacional.')),
    ('21', '17:00', None, 'Samay Punlla · Conmemoración a las almas', TULLPA, None, ACT, '04.jpg', [],
     dict(tipo='evento', event_kind='encuentro',
          descripcion='Encuentro sagrado entre los vivos y las almas. Cabildo Indígena Kichwa de Bogotá. '
                      'Música: Pakarimuk, Runapak, Kapary, Ukamau, Walka. Danzas: Tumarina.')),
]

# las 3 obras que no traía la Selección (lo que dicen las láminas)
NUEVAS = {
    'LezAma. Vivir filmando': {'director': 'Mónica Moya', 'duracion_min': 52},   # TMDB 1049488, IMDb tt36577296, Letterboxd: dir. Mónica Moya (la lámina nombra solo al productor)
    'Horizonte': {'director': 'César Acevedo', 'duracion_min': 125},
    'Mindalae – Viajero Kichwa': {'director': 'Samia Maldonado', 'duracion_min': 76},
}


def plano(t):
    return unicodedata.normalize('NFD', t.lower()).encode('ascii', 'ignore').decode().replace(' ', '')


def main():
    cat = {plano(o['titulo']): o for o in json.load(io.open(CAT, encoding='utf-8'))['obras']}
    funciones, usadas = [], set()
    for dia, ini, fin, tit, sede, sala, sec, lam, obras, extra in F:
        extra = dict(extra)
        r = {'titulo': tit, 'dia': f'2026-11-{dia}', 'hora': ini, 'sede': sede, 'seccion': sec,
             'acceso': extra.pop('acceso', LIBRE),
             '_src': {'url': URL, 'lamina': lam, 'date': '2026-11-16', 'tipo': 'festival-ig'}}
        if sala:
            r['sala'] = sala
        if fin:
            h0, m0 = map(int, ini.split(':'))
            h1, m1 = map(int, fin.split(':'))
            r['duracion_min'] = (h1 * 60 + m1) - (h0 * 60 + m0)
        ob = []
        for t, mins in obras:
            o = dict(cat.get(plano(t)) or {'titulo': t, **NUEVAS.get(t, {})})
            o['titulo'] = o.get('titulo') or t
            o.setdefault('duracion_min', mins)
            ob.append(o)
            usadas.add(plano(t))
        if tit == SEL and len(ob) > 1:   # bloque sin nombre en la lámina: sus obras, como las lista
            r['titulo'] = ' / '.join(t for t, _ in obras)
        if len(ob) == 1 and not extra.get('tipo'):
            o = ob[0]
            for k in ('director', 'pais', 'anio'):
                if o.get(k):
                    r[k] = o[k]
            r['duracion_min'] = o.get('duracion_min') or r.get('duracion_min')
        elif ob:
            r['obras'] = ob
            r.setdefault('tipo', 'evento' if extra.get('tipo') else 'programa')
        r.update(extra)
        funciones.append(r)
    fuera = sorted(o['titulo'] for k, o in cat.items() if k not in usadas)
    if fuera != ['La niebla de la paz']:
        sys.exit(f'✗ obras de la Selección sin función: {fuera} (se esperaba solo «La niebla de la paz»)')
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(URL, metodo='5 láminas leídas a ojo (fuentes/ig/DfzeOb2lq6q-x2)',
                                  que_aporta='día, hora, sede, sala, obras de cada franja, acceso'),
        'funciones': funciones,
        '_fuera': {'La niebla de la paz': 'está en la Selección Oficial (10 nov) pero no en la programación del 16 nov'}},
        ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
