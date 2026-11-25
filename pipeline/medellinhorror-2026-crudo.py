#!/usr/bin/env python3
"""medellinhorror-2026-crudo.py — Medellín Horror Fest 2026 (26–29 nov) → crudo.

FUENTES
  · Revista Digital ed. 01, pág. 4: tres largos en House of Demons, con día y hora, ENTRADA GRATIS.
  · Agenda oficial de Comic Con Medellín (medellin.comicconcolombia.com/es/agenda, capturada el
    25 nov): "Medellín Horror Film Fest - Selección de cortos", Salón Circo digital, 27 nov
    10:30–11:00 AM y 29 nov 6:31–7:00 PM. La agenda escribe ":31" solo para no pisar la franja
    anterior (que termina 6:30): se publica 18:30.
  · Las 13 obras de la Selección Oficial: medellinhorror-2026-catalogo.py (revista págs. 9–10 y pósteres).

QUÉ NO SE SABE: cuáles de los 13 cortos (105 min en total) van en cada pase de 30 min. Por eso los
pases van sin desglose y los 13 van en un bloque sin horario (docs/SCHEMA.md, bloques `unscheduled`).

28 NOV: ninguna fuente programa cine del festival ese día.
"""
import importlib.util, io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/medellinhorror-2026-crudo.json'
_s = importlib.util.spec_from_file_location('cat', f'{REPO}/pipeline/medellinhorror-2026-catalogo.py')
cat = importlib.util.module_from_spec(_s); _s.loader.exec_module(cat)
AGENDA = 'https://medellin.comicconcolombia.com/es/agenda'
BOLETAS = 'https://medellin.comicconcolombia.com/es/boleteria'
# afiches del festival para los cuatro cortos sin ficha TMDB
AFICHE = {t: {'poster': f'/assets/medellinhorror-2026/{a}.jpg', 'posterSource': 'editorial'} for t, a in (
    ('Tenebrios', 'tenebrios'), ('Familier / Familiar', 'familier-familiar'),
    ('Borrowed Light', 'borrowed-light'), ('There Is Something Behind You', 'there-is-something-behind-you'))}
# sinopsis de las cuatro sin ficha: texto de su fuente y traducción nuestra (25 nov 2026)
SINOPSIS = {
    # https://filmfreeway.com/TENEBRIOS (en)
    'Tenebrios': ('En plena crisis de salud, Jano ve cómo su cuerpo se deteriora sin explicación. Cautivado por la flauta hipnótica de su vecino, su obsesión crece mientras surgen gusanos de todo lo que lo rodea.',
                  "Jano, in the throes of a health crisis, watches his body inexplicably deteriorate. Enthralled by his neighbor's hypnotic flute, his obsession grows as worms emerge from his surroundings."),
    # https://frightnights.eu/programm-2026/familier-familiar/ (de)
    'Familier / Familiar': ('Élodie despierta en la noche, sola en la cama matrimonial. Mientras busca a su esposo, se encuentra de pronto frente a su silueta al final del pasillo. Tiene su voz, habla como él, pero… ¿de verdad es su esposo?',
                            'Élodie wakes up at night, alone in her marital bed. While looking for her husband, she suddenly finds herself facing his silhouette at the end of the hallway. He has his voice, he speaks like him, but… Is it really her husband?'),
    # https://clawcleaverflicks.com/borrowed-light (en)
    'Borrowed Light': ('Un vigilante nocturno se sobresalta cuando su pantalla de seguridad detecta un movimiento. Su investigación lo lleva a un encuentro inquietante.',
                       'A night watchman is startled by a detected motion on his security screen. His investigation leads to an eerie encounter.'),
    # https://preciosamedia.com/es/portfolio/hay-algo-detras-de-ti/ (es)
    'There Is Something Behind You': ('¿Alguna vez has sentido que algo te observa en la oscuridad? ¿Escuchas sonidos extraños en las noches? ¿Has querido despertar de un sueño y no has podido? Explora junto a Morgana, una astuta y enigmática gata negra, distintas historias de misterio vividas por niñas y niños en diferentes lugares y momentos de su vida.',
                                      'Have you ever felt something watching you in the dark? Do you hear strange sounds at night? Have you wanted to wake from a dream and could not? Join Morgana, a clever and enigmatic black cat, as she explores mystery stories lived by girls and boys in different places and moments of their lives.'),
}
ANIO = {'Tenebrios': 2025, 'Familier / Familiar': 2025, 'Borrowed Light': 2025, 'There Is Something Behind You': 2025}


def extra(t):
    if t not in SINOPSIS:
        return {}
    es, en = SINOPSIS[t]
    return {'sinopsis': es, 'sinopsis_en': en, 'anio': ANIO[t], 'genero': 'Animación' if t.startswith('There') else 'Terror'}



def main():
    fs = []
    for tit, dire, dia, hora, ev in cat.LARGOS:
        fs.append({'titulo': tit, 'director': dire, 'dia': dia, 'hora': hora, 'sede': 'House of Demons',
                   'acceso': 'Entrada gratis', 'seccion': 'Largometrajes',
                   # Sierra: 88 min en el programa de BHFF 2026; la revista no da duraciones de los largos
                   **({'duracion_min': 88} if tit.startswith('Sierra') else {}),
                   '_src': {'url': cat.REVISTA, 'lamina': 'pág. 4', 'date': cat.FECHA, 'tipo': 'festival-programa'}})
    for dia, hora, precio in (('2026-11-27', '10:30', '$36.000'), ('2026-11-29', '18:30', '$44.000')):
        fs.append({'titulo': 'Medellín Horror Film Fest - Selección de cortos', 'dia': dia, 'hora': hora,
                   'sede': 'Plaza Mayor', 'sala': 'Salón Circo digital', 'duracion_min': 30,
                   'tipo': 'evento', 'event_kind': 'evento', 'seccion': cat.SO,
                   'acceso': f'Con boleta: entrada a Comic Con Medellín ({precio} + $3.000 de servicio)',
                   'ticket_url': BOLETAS,
                   'descripcion': 'Selección de cortos del festival en Comic Con Medellín. Dura 30 minutos.',
                   '_src': {'url': AGENDA, 'date': '2026-11-25', 'tipo': 'sala-agenda'}})
    fs.append({'titulo': 'Cortometrajes Internacionales', 'seccion': cat.SO, 'tipo': 'programa',
               'is_cortos': True, 'unscheduled': True,
               'acceso': 'Con boleta: entrada a Comic Con Medellín', 'ticket_url': BOLETAS,
               'obras': [dict({'titulo': t, 'director': d, 'pais': p, 'duracion_min': m})
                         | AFICHE.get(t, {}) | extra(t)
                         for _, t, d, p, _x, m, _w, _g in cat.CORTOS],
               '_src': {'url': cat.REVISTA, 'lamina': 'págs. 9–10', 'date': cat.FECHA, 'tipo': 'festival-programa'}})
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(cat.REVISTA, metodo='revista (texto + lámina a ojo) y agenda oficial de Comic Con (HTML)',
                                  que_aporta='día, hora, sede y acceso'),
        'funciones': fs}, ensure_ascii=False, indent=1) + '\n')
    print(len(fs), 'funciones')


if __name__ == '__main__':
    main()
