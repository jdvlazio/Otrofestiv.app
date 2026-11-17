#!/usr/bin/env python3
"""under-2026-crudo.py — la PROGRAMACIÓN del XXII Festival Transterritorial de
Cine Underground, sede Medellín (25 nov – 3 dic 2026) → crudo.

LA FUENTE (16 nov 2026): IG @cineundermedellin, reel p/Df0rYtRxmgp. La
programación va en los CUADROS del video, no en el pie. Cuadros sacados del
reel (720×1280) a fuentes/ig/Df0rYtRxmgp/ (00 portada, 01 mié 25, 02 jue 26,
03 vie 27, 04 fiesta vie 27, 05 sáb 28 taller, 06 sáb 28 experimental, 07 dom
29, 08 cierre «+50 obras +20 países»), al doble en -x2/. Leídos a ojo; segunda
y tercera lectura: ig-lecturas.py (Vision y Tesseract) → under-2026-verificar.py.

SOLO 25–29 NOV. La portada dice «25 nov – 3 dic», pero el reel no trae nada
del 30 nov al 3 dic: sedes y fechas POR ANUNCIAR. El vigía sigue la cuenta.

SEDE ÚNICA (pie de cada cuadro): Perpetua Lab, Calle 34 # 45-07, segundo
piso, Distrito Creativo Perpetuo Socorro.

ACCESO: solo la fiesta dice precio («Aporte 10k») y el taller pide
inscripción, el del sábado («Inscripción previa. Cupos limitados»; el del
domingo no lo dice, así que va sin inscripción). Regla de Juan
(13 oct): sin aviso de pago = entrada libre.

Escribe festivals/staging/under-2026-crudo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/under-2026-crudo.json'
URL = 'https://www.instagram.com/p/Df0rYtRxmgp/'
SEDE = 'Perpetua Lab'
LIBRE = 'Entrada libre'

# Secciones: el rótulo de cada día, VERBATIM (propuesta: lo decide Juan)
DOC = 'Documental Activismo Social'
ANI = 'Animación'
FEM = 'Feminismos y disidencias sexuales'
CRE = 'Actividad creativa'
EXP = 'Cine experimental'
ACA = 'Actividad académica'

# (día, hora, título, sección, cuadro, obras[(título, director, país, año, min)], extra)
F = [
    ('25', '18:30', 'Apertura', DOC, '01.jpg',
     [('Borrachos mientras escuchamos las gotas caer', 'Santiago Gómez Ramírez', 'Colombia', 2026, 21),
      ('The sight is a wound', 'Parham Ghalamdar', 'Irán', 2025, 7)], {}),
    ('25', '20:00', 'Las muertes más bellas del mundo', DOC, '01.jpg',
     [('Las muertes más bellas del mundo', 'Quique Avilés, Ellie Walton', 'Estados Unidos', 2024, 71)], {}),
    ('26', '19:00', 'Programa 1', ANI, '02.jpg',
     [('Duelo', 'Sebastian Barnes', 'Argentina', 2025, 12),
      ('1 paseo por la ciudad', 'Alejandro Acuña Sevilla, Sara Coello Coello', 'México', 2025, 8),
      ('Comb story', 'Ernesto Rodriguez Cruz', 'Estados Unidos', 2026, 3),
      ('Cyclotron', 'Brian Gibson', 'Estados Unidos', 2026, 4),
      ('SKRFF', 'Corrie Francis Parks, Daniel Nuderscher', 'Austria', 2024, 7),
      ('Tapeworm Alexis & the Opera Diva', 'Thaïs Odermatt', 'Suiza', 2025, 11),
      ("The Shapeshifter's lament", 'Gaele Sobott', 'Australia', 2025, 10),
      ('Teatime', 'David Mathews', 'Austria', 2026, 4),
      ('Rattling', 'Nguyen Thao Nguyen', 'Vietnam', 2026, 3)], {}),
    ('27', '17:00', 'verdever', FEM, '03.jpg',
     [('Elegy for the Lost', 'William Hong-Xiao Wei', 'Francia, España, Reino Unido', 2025, 29),
      ('Objectionable Fruit', 'Hogan Seidel, Gabby Follett', 'Estados Unidos', 2026, 15),
      ('Ser, no ser, ser muchas', 'Silbando bembas', 'Argentina', 2025, 13),
      ('Perros', 'Ezequiel Rossi, Facundo Salomón', 'Argentina', 2026, 10)],
     dict(descripcion='Conversatorio con el Club de lectura y escritura de ciencia ficción Anarco Feminista.')),
    ('27', '21:00', 'Fiesta Under · El Vikingo Selektor', FEM, '04.jpg', [],
     dict(tipo='evento', event_kind='fiesta', acceso='Con boleta: aporte $10.000',
          descripcion='Post punk, dark wave, dark techno, industrial, EBM.')),
    ('28', '15:00', 'Orígenes de los lenguajes audiovisuales experimentales y laboratorio de creación', CRE,
     '05.jpg', [],
     dict(tipo='evento', event_kind='charla taller', acceso='Entrada libre con inscripción previa. Cupos limitados',
          descripcion='A cargo de: Hernán D. Arango S. Realizador audiovisual, editor y docente universitario '
                      'con más de 20 años de experiencia en cine y televisión. Magíster en Artes Digitales.')),
    ('28', '19:00', 'Experimental', EXP, '06.jpg',
     [('Cosmopoética: el ciclo de vida de una estrella masiva', 'Sofía Orozco Payares', 'Colombia', 2026, 10),
      ('Antifragility', 'Serafim Chikhladze', 'Rusia', 2026, 19),
      ('Fata Morgana', 'Hannu Nieminen', 'Finlandia', 2026, 5),
      ('Ghost Noon', 'Ting-Kin Chan', 'China', 2026, 7),
      ('Spheres', 'Marlin Gerigk', 'Alemania', 2026, 6),
      ('Und ich behaupte', 'Patrick Müller', 'Alemania', 2026, 3),
      ('Hansel and Gretel Get Kicked Out', 'MilleFeuille', 'Canadá', 2026, 11)], {}),
    ('29', '15:00', 'Hacerlo Sin Permiso. Laboratorio de Apropiación', ACA, '07.jpg', [],
     dict(tipo='evento', event_kind='charla taller',
          descripcion='A cargo de: El Gabinete Cine Club / Manifiesto / La Pola Records.')),
    ('29', '17:00', 'Función sorpresa', ACA, '07.jpg', [],
     dict(tipo='evento', event_kind='función sorpresa', descripcion='El Gabinete Cine Club.')),
]


def main():
    funciones = []
    for dia, hora, tit, sec, cuadro, obras, extra in F:
        extra = dict(extra)
        r = {'titulo': tit, 'dia': f'2026-11-{dia}', 'hora': hora, 'sede': SEDE, 'seccion': sec,
             'acceso': extra.pop('acceso', LIBRE),
             '_src': {'url': URL, 'lamina': cuadro, 'date': '2026-11-16', 'tipo': 'festival-ig'}}
        ob = [{'titulo': t, 'director': d, 'pais': p, 'anio': a, 'duracion_min': m} for t, d, p, a, m in obras]
        if len(ob) == 1:
            r.update({k: v for k, v in ob[0].items() if k != 'titulo'})
        elif ob:
            r['obras'] = ob
            r['tipo'] = 'programa'
            r['duracion_min'] = sum(o['duracion_min'] for o in ob)
        r.update(extra)
        funciones.append(r)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(URL, metodo='9 cuadros del reel leídos a ojo (fuentes/ig/Df0rYtRxmgp-x2)',
                                  que_aporta='día, hora, sede, obras de cada función, director/país/año/min, acceso'),
        'funciones': funciones,
        '_por_anunciar': '30 nov – 3 dic: la portada dice «25 nov - 3 dic», sin programación ni sedes (16 nov)'},
        ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
