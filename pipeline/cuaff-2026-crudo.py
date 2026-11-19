#!/usr/bin/env python3
"""cuaff-2026-crudo.py — CUAFF 2026 (Colombian Urban Art Film Festival, 3.ª edición) → crudo.

Cinemateca de Bogotá, 20–22 nov 2026. Lo trajo el vigía (issue #1269, 17 nov):
Festhome sigue diciendo 27–29 nov, está desactualizado.

DOS FUENTES, Y QUIÉN MANDA EN QUÉ:
  · IG @colombianurbanfilm, 11 posts del 10 al 16 nov (leídos por el EMBED sin
    sesión, fuentes/ig/<sc>/post.json): día, hora, SALA y acceso de cada función
    — salen del pie, y la lámina 01 del taller (Dfz5iWUlVID) los repite pintados.
  · Las fichas de la Cinemateca (/node/peliculas/4030–4036, «Festivales y
    Muestras · Colombian Urban Art Film Festival», bajadas el 17 nov a
    fuentes/cuaff-2026/): QUÉ OBRAS tiene cada programa, con director, año, país
    y duración. Los posts de IG solo presentan 3 de 5 y 3 de 4.
    Los números cuadran: 26+39 = 65 · 5+5+8+26+15 = 59 ≈ 60 · 18+8+8+30 = 64.
  La AGENDA de la Cinemateca (agenda/11, 20–22 nov) aún no los lista (17 nov);
  las cuatro franjas que CUAFF anuncia están libres en sus salas: no contradice.

TÍTULOS: manda el afiche/post del festival sobre la ficha de la sala.
  «El Lejano Sur» (afiche del post DfkEI-ZFSa2; la Cinemateca dice «El Ajeno sur»).
  «Still Free» (afiche del post DfkG3folR3w, «A film by Icer & Ka»; la Cinemateca
  dice «Latam tour», y el post lleva #LatamTour: es la misma obra, 18 min, Krone).

FUERA: la ficha 4033 «Graffiti & trenes» (Roofianes2, Graffiti Subway Mission,
Verticalbiner manila, Autosabotaje; 66 min) existe en la Cinemateca, pero
ningún post ni la agenda le dan día ni hora (17 nov). No se publica sin función.

ACCESO (verbatim): Wholetrain «valor 6.000 pesos por entrada taquilla de
Cinemateca»; Sanber «ENTRADA GRATUITA»; el taller «Entrada libre con inscripción
previa» (el enlace se pide por mensaje directo: no hay formulario público). Las
demás no anuncian pago → regla de Juan (13 oct): entrada libre.

Escribe festivals/staging/cuaff-2026-crudo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/cuaff-2026-crudo.json'
SEDE = 'Cinemateca de Bogotá'
IG = 'https://www.instagram.com/p/{}/'
CINE = 'https://cinematecadebogota.gov.co/node/peliculas/{}'
LIBRE = 'Entrada libre (no se anuncia pago)'
SEC = 'CUAFF 2026'          # el sello de todos los posts: «CUAFF 2026 | Cine, Arte Urbano y Comunidad»


def corto(t, d, pais, anio, mins):
    return {'titulo': t, 'director': d, 'pais': pais, 'anio': anio, 'duracion_min': mins, 'tipo': 'corto'}


F = [
    dict(titulo='Wholetrain', dia='20', hora='19:00', sala='Sala Capital', seccion=SEC,
         director='Florian Gaag', pais='Alemania', anio=2006, duracion_min=82,
         acceso='Con boleta: $6.000 en la taquilla de la Cinemateca',
         descripcion='Estreno de la versión remasterizada en 4K.',
         _src={'ig': 'Dfj4c_vlcMO', 'cinemateca': 4030}),
    dict(titulo='Graffiti y cámara: documentar la calle', dia='21', hora='09:00', sala='Laboratorio 1',
         seccion='Taller', tipo='evento', event_kind='taller', duracion_min=120,
         acceso='Entrada libre con inscripción previa',
         descripcion='Taller teórico-analítico sobre cómo registrar muralismo, graffiti y acciones urbanas '
                     'desde una mirada audiovisual consciente. Dictado por Anonimato Visual. '
                     'Inscripciones por mensaje directo a @colombianurbanfilm.',
         _src={'ig': 'Dfz5iWUlVID'}),
    dict(titulo='Breaking la vida', dia='21', hora='14:30', sala='Sala 3', seccion=SEC,
         director='Abraham Escobedo-Salas', pais='México', anio=2022, duracion_min=92, acceso=LIBRE,
         _src={'ig': 'DfkAU_slfaS', 'cinemateca': 4031}),
    dict(titulo='Hip Hop y Comunidad', dia='21', hora='17:00', sala='Sala 3', seccion=SEC,
         tipo='programa', duracion_min=65, acceso=LIBRE,
         obras=[corto('Uniendo plazas: Los padres del under', 'Alberto Tolaba', 'Argentina', 2025, 26),
                corto('Homenajes de memorias, del Hip hop en ciudad Bolívar', 'Kno Delix, Johan Duarte',
                      'Colombia', 2025, 39)],
         _src={'ig': 'DfkCq1vlXAe', 'cinemateca': 4032}),
    dict(titulo='Hip Hop, Comunidad y Graffiti', dia='22', hora='13:30', sala='Sala 3', seccion=SEC,
         tipo='programa', duracion_min=60, acceso=LIBRE,
         obras=[corto('Código cypher vol1', 'Hitana, Sir Cesaro', 'Argentina', 2026, 5),
                corto('El arte de Gravitar', 'Camila Estupiñán', 'Colombia', 2024, 5),
                corto('El Lejano Sur', 'Isben Isaeb', 'Colombia', 2026, 8),
                corto('Instrucciones para interpretar graffiti, el beso de los invisibles', 'Iván Alba',
                      'Colombia', 2025, 26),
                corto('Diario de los nuevos 20s', 'Juan Pablo Huston', 'Colombia', 2026, 15)],
         _src={'ig': 'DfkEI-ZFSa2 DfkFGHmlZnr DfkVdFolQHW', 'cinemateca': 4034}),
    dict(titulo='Graffiti, Trenes y Street', dia='22', hora='16:00', sala='Sala 2', seccion=SEC,
         tipo='programa', duracion_min=64, acceso=LIBRE,
         obras=[corto('Still Free', 'Krone', 'Colombia', 2026, 18),
                corto('VSK en metal', 'Peds Shaumers', 'Colombia', 2026, 8),
                corto('Adrenaline Tour: Bella Ciao', 'Ozono', 'Italia', 2026, 8),
                corto('Morbo x Noches Aires', 'Newen', 'Argentina', 2026, 30)],
         _src={'ig': 'DfkG3folR3w DfvPV3zDP5z DfzaftWlRzG', 'cinemateca': 4035}),
    dict(titulo='Sanber: vivencias de un bajo mundo', dia='22', hora='19:00', sala='Sala Capital',
         seccion='Clausura', director='Luis Carlos Ayala', pais='Colombia', anio=2026, duracion_min=90,
         has_qa=True, acceso='Entrada gratuita', descripcion='Proyección y conversatorio.',
         _src={'ig': 'DfkahZulbIz', 'cinemateca': 4036}),
]

# SINOPSIS en español: el texto de cada ficha de la Cinemateca (4030–4036), verbatim (19 nov 2026).
SINOPSIS = {
 "4030": "Lo que mantiene unido a este grupo de amigos es una causa artística urbana llamada graffiti que persigue la ley. Tienen normas y valores propios. Se rigen por un código honesto y estricto y sueñan, que para eso son artistas, con fama, respeto y reconocimiento. Pero de momento toca agitar el spray con nocturnidad y lo más urgente, escapar de la policía y responder al reto de un grupo rival, los temibles KBS, que les arrojan el guante de pintar entero un tren de cercanías.",
 "4031": "Seis jóvenes bailarines provenientes de distintas clases sociales y antecedentes son unidos por el poder del hip-hop. Su amistad y deseos de volverse profesionales los llevarán por un viaje vital y transformador filmado a lo largo de 8 años. A través de la paternidad, el amor, las batallas y decepciones, descubrirán qué tipo de hombres quieren ser.",
 "4032": "El hip hop es mucho más que música: es memoria, identidad, resistencia y construcción colectiva. Este bloque reúne dos miradas documentales de Argentina y Colombia que exploran cómo la cultura urbana transforma territorios, conecta generaciones y fortalece los vínculos comunitarios. A través de sus protagonistas, las calles se convierten en escenarios de expresión, encuentro y memoria, donde el arte mantiene vivas las historias de quienes han construido el movimiento desde sus raíces.",
 "4034": "El hip hop y el graffiti son expresiones culturales que nacen de las calles, construyen identidad y fortalecen los lazos comunitarios. Este bloque reúne cinco producciones audiovisuales de Colombia y Argentina que exploran el arte urbano como lenguaje de encuentro, memoria, transformación social y resistencia cultural. A través del movimiento, la música, las intervenciones gráficas y las narrativas de sus protagonistas, descubrimos cómo las nuevas generaciones reinterpretan sus territorios, mantienen viva la cultura underground y encuentran en el arte una forma de expresión colectiva.",
 "4035": "El graffiti no conoce fronteras. Entre trenes, calles, muros y recorridos clandestinos, este bloque nos sumerge en la esencia más cruda y auténtica de la cultura underground. Cuatro producciones audiovisuales de Colombia, Italia y Argentina retratan la adrenalina, los viajes, los códigos y las experiencias que definen el graffiti sobre metal y el movimiento del street bombing. Una mirada a las conexiones internacionales entre escritores de graffiti, donde cada recorrido se convierte en una aventura y cada intervención deja una huella en el paisaje urbano. Arte, riesgo, identidad y libertad se encuentran en historias que revelan la fuerza de una cultura que permanece en constante movimiento.",
 "4036": "Documental que busca, en un relato de paralelismos, encontrar todos los matices posibles sobre un pedacito del centro de Bogotá, un microcosmos que se entrelaza y muere con la renovación de la ciudad. Graffiti, Rap y literatura (Mario Mendoza) aportan con datos inéditos todo lo que pasó en algún momento en uno de los barrios marginalizados del centro de Bogotá"
}


def main():
    funciones = []
    for f in F:
        r = dict(f)
        src = r.pop('_src')
        r['dia'] = f'2026-11-{r["dia"]}'
        r['sede'] = SEDE
        r['_src'] = {'url': IG.format(src['ig'].split()[0]), 'posts': src['ig'].split(),
                     'tipo': 'festival-ig', 'date': '2026-11-16'}
        if src.get('cinemateca'):
            r['_src']['ficha_sala'] = CINE.format(src['cinemateca'])
            if str(src['cinemateca']) in SINOPSIS:
                r['sinopsis'] = SINOPSIS[str(src['cinemateca'])]
        if r.get('obras'):
            suma = sum(o['duracion_min'] for o in r['obras'])
            if abs(suma - r['duracion_min']) > 1:
                sys.exit(f'✗ {r["titulo"]}: las obras suman {suma}, el programa dice {r["duracion_min"]}')
        funciones.append(r)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('https://www.instagram.com/colombianurbanfilm/',
                                  metodo='pies de 11 posts por embed sin sesión + fichas 4030–4036 de la Cinemateca',
                                  que_aporta='día, hora, sala, acceso (IG); obras de cada programa (Cinemateca)'),
        'funciones': funciones,
        '_fuera': {'Roofianes2, Graffiti Subway Mission, Verticalbiner manila, Autosabotaje (ficha 4033 «Graffiti & trenes»)': 'ficha 4033 de la Cinemateca sin día ni hora en ninguna fuente (17 nov)'}},
        ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funciones)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
