#!/usr/bin/env python3
"""villadeleyvaiff-2026-crudo.py — la parrilla del 20 Festival Internacional de Cine
de Villa de Leyva (13–16 nov 2026) → crudo.

LA FUENTE es el carrusel «Programación · Real Fábrica» de @festcinevilla,
p/DfkomnaGQZw (10 nov 2026, 7 láminas), leído a ojo lámina por lámina (11 nov):
  02 Sala Blanca, viernes 13 · 03 Sala Blanca, sábado 14 y domingo 15
  04 Sala Rosada, viernes 13 · 05 Sala Rosada, sábado 14 · 06 Sala Rosada, domingo 15
Las láminas solo traen la Real Fábrica; el lunes 16 no aparece. Las obras de
cada bloque de competencia salen del catálogo del pre-onboarding (mismas
secciones); la ★ marca la Competencia Oficial de Largometraje (p/Dfhyu_fmw4p).

DECISIONES (11 nov 2026):
- Título de obra: el del catálogo (los PDF del festival). La lámina escribe
  «Soy Lidia» y «Vals para María Domingas»; el catálogo, «Sol en Lidia» y
  «Valsa para Maria Domingas» (título original). Queda en `_dudas`.
- Viernes 4:30 PM, Sala Blanca, no tiene rótulo: son las 4 obras de Escuelas que
  faltan en el bloque de las 2:30 → segundo bloque de Competencia Escuelas.
- «Las formas de la magia» (Corto Documental, domingo 5 PM) no está en el
  catálogo: entra con el país de la lámina.
- Foco Reygadas: la lámina no dice qué película; entra como programa sin obra.
- Entrada: el festival no anuncia pago → entrada libre (regla de Juan, 13 oct).
- Duración de un bloque: el hueco hasta la función siguiente de la misma sala,
  si no pasa de 150 min (un hueco más largo no es la duración del bloque).
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance  # noqa: E402

CATALOGO = f'{REPO}/festivals/staging/villadeleyvaiff-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/villadeleyvaiff-2026-crudo.json'
URL = 'https://www.instagram.com/p/DfkomnaGQZw/'
SEDE = 'Real Fábrica'
LARGO = 'Competencia Oficial Largometraje'
ESC, COL, INT = 'Competencia Escuelas', 'Competencia Corto Profesional Colombia', 'Competencia Corto Internacional'
ANI, EXP, DOC = 'Competencia Corto Animación', 'Competencia Corto Experimental', 'Competencia Corto Documental'
LDOC, FOCO, MUE = 'Competencia Largo Documental', 'Foco Reygadas', 'Muestra Especial'
PLAZA, FEST, ENC, EVT = 'Cine a la Plaza', 'Competencia Corto Festivalito', 'Encuentros', 'Evento'
PDF = 'https://www.villadeleyvaiff.co/_files/ugd/66001c_a296b2bfe67b41cdba2e0a1c661be1f5.pdf'
FESTIVALITO = ['Bumblebee', 'Danza de las muñecas', 'Danza invisible', 'Dance Dance Evolution', 'En la sombra de la garza',
               'Las zapatillas mágicas', 'Loop', 'My Little Life on the Island', 'Saba', 'Snorri Catch Me If You Candy']
EN_PLAZA = {'sede': 'Plaza Mayor', 'sala': '', '_src': {'url': PDF, 'date': '2026-11-11', 'nota': 'programa completo (PDF de la web, 11 nov), columna Cine a la Plaza'}}
EN_PDF = {'_src': {'url': PDF, 'date': '2026-11-11', 'nota': 'programa completo (PDF de la web, 11 nov)'}}
# título de la lámina → título del catálogo
ALIAS = {'Soy Lidia': 'Sol en Lidia', 'Vals para María Domingas': 'Valsa para Maria Domingas',
         'Día 1 Narita-Tokio': 'Día 1 Narita–Tokyo', 'Convocatoria general del gremio': '“Convocatoria general del gremio”',
         'Rol - El río se llevaba las manchas de la vida': 'Rol – El río se llevaba las manchas de la vida',
         'Agachar el rostro': 'Agachar el rostro', 'Sex Panchitos': 'Sex panchitos',
         'My Little Life on the Island': 'Mi pequeña vida en la isla', 'Snorri Catch Me If You Candy': 'Snorri'}
SUELTAS = {'Las formas de la magia': {'pais': 'Colombia'},
           'El fantasma': {'director': 'Ignacio Masllorens, David Lamelas', 'pais': 'Argentina'},
           'Las almas ni los ojos': {'director': 'Canela Reyes, César Jaimes', 'pais': 'Colombia'},
           'No nos moverán': {'director': 'Pierre Saint-Martin', 'pais': 'México'},
           'El jardín que soñamos': {'director': 'Joaquín Del Paso', 'pais': 'México'},
           'Tres hermanas': {'director': 'Joyce Ventura', 'pais': 'Colombia'},
           'La paga': {'director': 'Ciro Durán', 'pais': 'Colombia, Venezuela', 'anio': 1962},
           'Luz silenciosa': {'director': 'Carlos Reygadas', 'pais': 'México', 'anio': 2007},
           'Post Tenebras Lux': {'director': 'Carlos Reygadas', 'pais': 'México', 'anio': 2012},
           'Mu-ki-ra': {'director': 'Estefanía Piñeres', 'pais': 'Colombia', 'anio': 2026},
           'Goham': {'director': 'Chayanop Boonprakob, Nattawut Poonpiriya, Atta Hemwadee', 'pais': 'Tailandia', 'anio': 2026},
           'Masha y los osos': {'director': 'Antonina Ruzhe', 'pais': 'Rusia', 'anio': 2025},
           'Sinfonía de los bichos raros': {'director': 'Julián Duque', 'pais': 'Colombia', 'anio': 2026},
           'El corset': {'director': 'Louis Clichy', 'pais': 'Francia', 'anio': 2026},
           'Kiki: entregas a domicilio': {'director': 'Hayao Miyazaki', 'pais': 'Japón', 'anio': 1989},
           'Moon, mi amigo el panda': {'director': 'Gilles de Maistre', 'pais': 'Francia, Bélgica', 'anio': 2025},
           'Lactar': {'director': 'Harold Trompetero', 'pais': 'Colombia', 'anio': 2026}}
RETRO = 'Retrospectiva Festival: Cortos que nos han encantado'

# (lámina, sala, día, [(hora, sección, título del programa o None, [obras], extra)])
PARRILLA = [
    ('02', 'Sala Blanca', '2026-11-13', [
        ('14:30', ESC, None, ['Cielo de enero', 'Demian', 'El mejor regalo', 'La casa del marica', 'La muerta que habla'], {}),
        ('16:30', ESC, None, ['Los lobo', 'Soy Lidia', 'Términa', 'Vals para María Domingas'], {}),
        ('18:00', COL, 'Competencia Corto / Col 1', ['Chaski Pacha', 'Criatura'], {}),
        ('19:00', INT, None, ['Armónica', 'El derrumbe', 'El silencio de la tierra', 'Las heridas', 'Los chorros', 'Yegua'], {}),
        ('20:30', FOCO, None, ['Luz silenciosa'], {})]),
    ('03', 'Sala Blanca', '2026-11-14', [
        ('14:00', COL, 'Competencia Corto / Col 2', ['Agachar el rostro', 'Esquirlas de caracol', 'Gris', 'Malas posturas',
                                                     'Noche de vuelo', 'Refracción'], {}),
        ('18:30', LARGO, None, ['El fantasma'], {}),
        ('21:00', FOCO, None, ['Post Tenebras Lux'], {})]),
    ('03', 'Sala Blanca', '2026-11-15', [
        ('14:00', LARGO, None, ['Las almas ni los ojos'], {}),
        ('15:30', LARGO, None, ['No nos moverán'], {'has_qa': True}),
        ('18:00', LARGO, None, ['El jardín que soñamos'], {})]),
    ('04', 'Sala Rosada', '2026-11-13', [
        ('14:00', LDOC, None, ['Dama de las mil máscaras'], {}),
        ('15:30', LDOC, None, ['El extraordinario viaje del dragón'], {}),
        ('17:30', LDOC, None, ['Notas sobre un destierro'], {}),
        ('19:00', LDOC, None, ['Portento'], {})]),
    ('05', 'Sala Rosada', '2026-11-14', [
        ('14:00', MUE, None, ['Tres hermanas'], {}),
        ('16:00', ENC, 'Encuentro con Carlos Reygadas', [], {'tipo': 'evento', 'event_kind': 'charla', 'duracion_min': 120,
                  '_duracion_de': 'el hueco hasta el bloque siguiente de la sala (6:30 PM)', 'acceso': 'Entrada libre, hasta completar aforo', **EN_PDF}),
        ('18:30', ANI, None, ['A la sombra de los árboles', 'Bumblebee', 'Cuna de lobas', 'El cuerpo de Cristo',
                              'Emechiche, el renacer de los cabeciblancos', 'En la sombra de la garza', '¡Florecerán!',
                              'Merrimundi', 'Saba', 'Una vez en un cuerpo'], {}),
        ('20:00', EXP, None, ['Ballena', 'Chaika', 'Convocatoria general del gremio', 'Cuarto de flores',
                              'Día 1 Narita-Tokio', 'Las criaturas', 'Rol - El río se llevaba las manchas de la vida', 'Zakih'], {})]),
    ('06', 'Sala Rosada', '2026-11-15', [
        ('14:00', DOC, None, ['Baile por la ciudad', 'Claudete', 'Eda', 'Jeña'], {}),
        ('15:00', LDOC, None, ['Sex Panchitos'], {}),
        ('17:00', DOC, None, ['Las formas de la magia', 'Lia', 'Lo que no se puede borrar', 'Logos', 'Tragedia sentimental'], {}),
        ('18:30', MUE, None, ['La paga'], {})]),
    # ── programa completo (PDF de la web, 11 nov): Cine a la Plaza, Festivalito y las demás sedes
    ('pdf', 'Plaza', '2026-11-13', [
        ('10:00', PLAZA, 'Película para todos los niños y niñas de Villa de Leyva', [], {**EN_PLAZA, 'duracion_min': 90,
                  '_duracion_de': 'estimada: la fuente no dice qué película'}),
        ('13:00', PLAZA, RETRO, [], {**EN_PLAZA, 'duracion_min': 120, '_duracion_de': 'de 1 PM a 3 PM, según la fuente'}),
        ('15:30', PLAZA, None, ['Mu-ki-ra'], dict(EN_PLAZA)),
        ('18:00', PLAZA, None, ['Goham'], {**EN_PLAZA, '_nota': 'Apertura del festival · preestreno · Foco Cineplex'})]),
    ('pdf', 'Plaza', '2026-11-14', [
        ('10:00', PLAZA, RETRO, [], {**EN_PLAZA, 'duracion_min': 120, '_duracion_de': 'estimada como la del viernes; la fuente no da fin'}),
        ('15:00', PLAZA, None, ['Masha y los osos'], dict(EN_PLAZA)),
        ('17:00', PLAZA, None, ['Sinfonía de los bichos raros'], dict(EN_PLAZA)),
        ('19:00', LARGO, None, ['El corset'], {**EN_PLAZA, '_nota': 'presentación especial; ★ competencia oficial'})]),
    ('pdf', 'Plaza', '2026-11-15', [
        ('10:00', PLAZA, RETRO, [], {**EN_PLAZA, 'duracion_min': 240, '_duracion_de': 'de 10 AM a 2 PM, según la fuente'}),
        ('15:00', FEST, 'Premiación Festivalito + Cortos Festivalito', FESTIVALITO, dict(EN_PLAZA)),
        ('16:30', PLAZA, None, ['Kiki: entregas a domicilio'], dict(EN_PLAZA)),
        ('18:30', PLAZA, None, ['Moon, mi amigo el panda'], dict(EN_PLAZA)),
        ('21:00', PLAZA, None, ['Lactar'], dict(EN_PLAZA))]),
    ('pdf', '', '2026-11-14', [
        ('09:00', FEST, 'Festivalito: talleres y cine', FESTIVALITO, {**EN_PDF, 'sala': '', 'duracion_min': 180, '_duracion_de': 'de 9 AM a 12 M, según la fuente'}),
        ('14:00', ENC, 'Espacio Redes: ¿Cuál es el valor de los escritores audiovisuales?', [],
         {**EN_PDF, 'sede': 'Hotel Plaza Mayor', 'sala': '', 'tipo': 'evento', 'event_kind': 'charla', 'duracion_min': 90,
          '_duracion_de': 'estimada: la fuente no da fin'})]),
    ('pdf', '', '2026-11-15', [
        ('09:00', FEST, 'Festivalito: talleres y cine', FESTIVALITO, {**EN_PDF, 'sala': '', 'duracion_min': 180, '_duracion_de': 'de 9 AM a 12 M, según la fuente'})]),
    ('pdf', '', '2026-11-16', [
        ('15:30', EVT, 'Fragmentos', [], {**EN_PDF, 'sede': 'Claustro de San Francisco', 'sala': '', 'tipo': 'evento', 'event_kind': 'evento',
                  'invitados': 'Compañía Cuerpo de Indias', 'acceso': 'Con boleta: boletería en El Gato que bebe y lee', 'duracion_min': 60,
                  '_duracion_de': 'estimada: la fuente no da fin'})]),
]


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def main():
    cat = {norm(o['titulo']): o for o in json.load(io.open(CATALOGO, encoding='utf-8'))['obras']}
    funcs, fallos = [], []
    for lam, sala, dia, lista in PARRILLA:
        for i, (hora, sec, prog, obras, extra) in enumerate(lista):
            out = []
            for t in obras:
                tc = ALIAS.get(t, t)
                o = cat.get(norm(tc))
                if o:
                    out.append({k: o[k] for k in ('titulo', 'director', 'pais') if o.get(k)})
                elif t in SUELTAS:
                    out.append({'titulo': t, **SUELTAS[t]})
                else:
                    fallos.append(f'{dia} {hora}: «{t}» no está en el catálogo ni en SUELTAS')
            f = {'dia': dia, 'hora': hora, 'sede': SEDE, 'sala': sala, 'seccion': sec,
                 'acceso': 'Entrada libre (no se anuncia pago)',
                 '_src': {'url': URL, 'lamina': lam, 'date': '2026-11-10'}}
            sig = lista[i + 1][0] if i + 1 < len(lista) else None
            if len(out) == 1 and not prog:
                f.update(out[0])
            else:
                f['titulo'] = prog or sec
                if out:
                    f['obras'] = out
                if sig and mins(sig) - mins(hora) <= 150 and 'duracion_min' not in extra:
                    f['duracion_min'], f['_duracion_de'] = mins(sig) - mins(hora), 'hueco hasta la función siguiente de la sala'
            f.update(extra)
            funcs.append(f)
    if fallos:
        sys.exit('✗ ' + '\n  · '.join(fallos))
    # dos funciones con el mismo título de programa: se numeran
    vistos = {}
    for f in funcs:
        if f.get('obras') and f['titulo'] in (ESC, COL, INT, ANI, EXP, DOC, LDOC, 'Competencia Corto / Col 1', 'Competencia Corto / Col 2'):
            vistos.setdefault(f['titulo'], []).append(f)
    for t, fs in vistos.items():
        if len(fs) > 1:
            for n, f in enumerate(fs, 1):
                f['titulo'] = f'{t} {n}'
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('IG @festcinevilla, carrusel «Programación · Real Fábrica» (10 nov 2026)',
                                  que_aporta='día, hora y sala de la Real Fábrica, 13–15 nov', url=URL,
                                  metodo='lectura a ojo de las láminas 02–06'),
        '_acceso': {'estado': 'Entrada libre (no se anuncia pago)', 'revisado': '2026-11-11', 'fuentes': [URL],
                    '_por_que': 'el festival no anuncia pago (regla de Juan, 13 oct 2026)'},
        '_fuera': [{'titulo': '35 Ladrillos', 'dias': ['2026-11-14', '2026-11-15'], 'horas': ['18:00', '20:00'],
                    '_por_que': 'la fuente no da sede; sin sede no se publica', 'fuente': PDF}],
        '_dudas': ['«Soy Lidia» (lámina) / «Sol en Lidia» (catálogo): se usa el del catálogo',
                   '«Vals para María Domingas» (lámina) / «Valsa para Maria Domingas» (catálogo, título original)'],
        'funciones': funcs}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funcs)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
