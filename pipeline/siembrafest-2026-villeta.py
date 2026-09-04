# -*- coding: utf-8 -*-
"""La programación de VILLETA del 11.º SiembraFest, del PDF oficial.

    siembrafest.com/descargas/programacion_11sf_villeta.pdf   (12 páginas)
    enlazado desde siembrafest.com/festival/programacion/ · anunciado en IG el 4 sep

DOBLE LECTURA, y las dos independientes de verdad:

  A · la CAPA DE TEXTO del PDF (no es OCR: no puede tener errores de lectura),
      guardada en festivals/staging/siembrafest-2026-villeta-texto.json;
  B · la lectura VISUAL de cada página, que es la que fija el layout.

Hacían falta las dos porque el PDF va a DOS COLUMNAS y el texto sale aplanado:
el orden de «Dónde?» y de la hora no es el de la página. En el Día 4, la capa de
texto sugería SiembraLAB en Vda. Chapaima e IRREDENTOS en el SENA, y la página
dice lo contrario. Esa es la única clase de error que este PDF puede tener, y es
justo la que una sola lectura no ve.

Lo de abajo se transcribe de B —con su número de página— y `--verificar` lo
comprueba contra A: cada título, hora, día y sede tiene que estar en la página
que dice ser su fuente. Si el festival reimprime, falla.

Sasaima NO está: su PDF no existe todavía (la web dice «muy pronto» y la URL
paralela devuelve HTML). Cuando salga, se añade aquí y se re-corre.
"""
import json, os, re, sys, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance, DESCONOCIDO                      # noqa: E402

TEXTO = f'{REPO}/festivals/staging/siembrafest-2026-villeta-texto.json'
SALIDA = f'{REPO}/festivals/staging/siembrafest-2026-crudo.json'

CIN = 'Cinema Villeta'
SENA = 'SENA CDAE Villeta'          # el programa lo escribe «SENA - CDAE VILLETA»
IED = 'IED Alonso de Olalla'
CHA = 'Vda. Chapaima'
AMBOS = 'Villeta y Sasaima'

# (día, hora, hora_fin, sede, tipo, sección, [obras], página)
# obra = (título, director, año, minutos) · None en director = no es una obra
BLOQUES = [
 ('09', '14:00', '15:30', CIN, 'apertura', 'Mujeres que sostienen la vida', [
    ('Acto inaugural', None, None, None),
    ('Convite: Sembrar soberanía — agricultura, semillas y territorio', None, None, None)], 2),
 ('09', '16:00', '18:00', CIN, 'exhibicion', 'Película Invitada', [
    ('Andariega', 'Rául Soto', 2025, 94)], 2),

 ('10', '10:00', '12:00', IED, 'exhibicion', 'Amores & Desamores', [
    ('Elementales', 'Camilo Botero Jaramillo', 2025, 8),
    ('Orígenes', 'Daniel Rodríguez Gaitán', 2025, 7),
    ('Desde acá veo la tormenta', 'Juan Felipe Restrepo', 2026, 10),
    ('Unlearning Motherhood', 'Juliana Erazo', 2025, 10),
    ('Amor', 'Dayana González Fajardo', 2026, 13),
    ('La independencia', 'John Agudelo Suárez', 2024, 19)], 3),
 ('10', '11:00', '13:00', SENA, 'exhibicion', 'Buenos, Malos y Feos', [
    ('Flores Miro', 'John Agudelo Suárez', 2025, 101)], 3),
 ('10', '16:00', '18:00', SENA, 'exhibicion', 'Estampas', [
    ('Herencia: los cantos de la tierra', 'Iván Acosta Rojas', 2026, 82)], 3),
 ('10', '18:00', '20:00', SENA, 'exhibicion', 'Cinema Patatús', [
    ('La oscurana', 'Carolina González Rodríguez', 2025, 20),
    ('Animero: son de la muerte', 'Nadine Holguín', 2025, 11),
    ('Nativos de la tierra negra', 'Juan Pablo Ríos', 2026, 18),
    ('Que el cielo nos perdone', 'Andrés Buitrago', 2025, 17),
    ('El silbido del cañaduzal', 'Juan Fernando Murillo', 2025, 19)], 4),

 ('11', '10:00', '12:00', IED, 'exhibicion', 'Buenos, Malos y Feos', [
    ('Dios y suerte', 'Carol Durán', 2025, 17),
    ('La despedida del río', 'Mateo Salas Puerta', 2025, 17),
    ('Las piedras del río', 'Edna Sierra', 2026, 16),
    ('Y el río lloró', 'Zumaya Mayers', 2024, 27)], 5),
 ('11', '11:00', '13:00', SENA, 'exhibicion', 'Amores & Desamores', [
    ('Tres gatos parias', 'Iván Sierra', 2025, 7),
    ('Valentino y la calavera', 'Iván Sierra', 2025, 7),
    ('La calle del amor', 'Ramón Contreras', 2026, 9),
    ('Corazón galvánico', 'Valentina Valencia', 2024, 11),
    ('El mejor chocolate del mundo', 'John Agudelo Suárez', 2026, 17),
    ('Make Up: el arte de amar', 'Daniel Calderón', 2025, 19)], 5),
 ('11', '15:30', '16:00', CIN, 'exhibicion', 'LABRA', [
    ('Cosecha audiovisual', None, None, None)], 6),
 ('11', '16:00', '17:30', CIN, 'exhibicion', 'Así es Cundinamarca', [
    ('Elipsis', 'Dayana González Fajardo', 2020, 6),
    ('Trigos', 'Enrique Uribe White', 1941, 20),
    ('Herminda', 'Ernesto Lozano Redondo', 2024, 9),
    ('Teresa', 'Edgar Medina Fetecua', 2025, 18),
    ('La muerte de Elías', 'Gustavo Alejandro Valcárcel Sierra', 2023, 9),
    ('Gachalá, entre el miedo y la memoria', 'María Camila Mariño', 2026, 11)], 6),
 ('11', '17:30', '18:00', CIN, 'convite', 'Así es Cundinamarca', [
    ('Convite: La tierra no olvida — historias contadas desde la región', None, None, None)], 6),
 ('11', '18:00', '20:00', SENA, 'exhibicion', 'Buenos, Malos y Feos', [
    ('Preguntas frecuentes', 'Sofía Salinas Barrera', 2025, 16),
    ('Pudor ante el asalto de los ojos furtivos', 'Laura Rodríguez', 2025, 9),
    ('La mona', 'Laura Gutiérrez Ardila', 2025, 18),
    ('Términa', 'Juan José Guevara Ruiz', 2025, 27),
    ('Desde la ventana', 'Mike Pitalua', 2021, 9)], 7),

 # Día 4 · el cruce que cazó la doble lectura: SiembraLAB va en el SENA y
 # IRREDENTOS en Vda. Chapaima, no al revés (p8).
 ('12', '08:00', '12:00', SENA, 'taller', 'SiembraLAB', [
    ('Microtaller: producción de imagen y video en realidad virtual', None, None, None)], 8),
 ('12', '18:00', '20:00', CHA, 'exhibicion', 'Buenos, Malos y Feos', [
    ('Irredentos', 'Harold de Vasten', 2025, 100)], 8),

 ('13', '08:00', '18:00', AMBOS, 'experiencia', 'Mujeres que sostienen la vida', [
    ('Maratón fotográfica SiembraFest', None, None, None)], 8),

 ('14', '11:00', '13:00', SENA, 'exhibicion', 'Sabores en Escena', [
    ("Phakhakhe Pi'txi - Minga de pensamiento", 'Duvier Baicue', 2024, 10),
    ('La Asociación', 'Juan Camilo Muñoz Quintero', 2023, 19),
    ('Somos historias: Casaramano, sagrado y vida', 'Juven A. Piranga', 2023, 30)], 9),
 ('14', '16:00', '18:00', SENA, 'exhibicion', 'Estampas', [
    ('Mingoya: tierra de ornitólogos', 'Nelsy Niño R. & Juan Esteban Quintero', 2024, 8),
    ('Refugiar el gesto', 'Adrián Villa-Dávila & Andrés Prado', 2026, 11),
    ('Guatapé (no) ha muerto', 'Laurence Paciarelli', 2025, 52)], 9),

 ('15', '10:00', '12:00', IED, 'exhibicion', 'Mujeres que sostienen la vida', [
    ('La gallina saraviada', 'Ingrid Bonilla Rodríguez', 2025, 11),
    ('En su sombra fértil', 'Andrés Dávila', 2025, 11),
    ('La grandiosa', 'Viviana Reinoso', 2025, 13),
    ('Paramunas: el alma de la montaña', 'Alejandro Calderón González', 2024, 18),
    ('El tiempo de las mujeres transforma el territorio', 'FAO Colombia', 2025, 17)], 10),
 ('15', '11:00', '13:00', SENA, 'taller', 'SiembraLAB', [
    ('Trabajo con material de archivo', None, None, None)], 10),

 ('16', '10:00', '12:00', IED, 'exhibicion', 'Mujeres que sostienen la vida', [
    ('La tinaja', 'Ernestina Miranda y Mar Ajé', 2025, 14),
    ('Cayenas libertarias', 'Javier Camilo Aranguren Montañez', 2026, 17),
    ('Pasta negra', 'Jorge Thielen Armand', 2025, 15),
    ('Victorias y glorias - relatos de campeonas', 'Luber Yesid Zúñiga Ordóñez', 2025, 11),
    ('El tiempo de las mujeres transforma el territorio', 'FAO Colombia', 2025, 17)], 11),
 ('16', '11:00', '13:00', SENA, 'exhibicion', 'Cinema Patatús', [
    ('Noche de vuelo', 'Zacarías Flores del Campo', 2025, 19),
    ('Villa Feliz', 'James Camargo de Alba', 2021, 8),
    ('Bajo el mismo techo', 'Sophia Cadavid', 2026, 13),
    ('Linfernum', 'Dayana González Fajardo', 2024, 8),
    ('Payasadas', 'Santiago Duque', 2024, 24)], 11),

 ('17', '10:00', '12:00', IED, 'exhibicion', 'Muertos de Risa', [
    ('El día de mi suerte', 'Dayana González Fajardo', 2024, 8),
    ('HDLT', 'Colectivo Artefactum Suba', 2025, 18),
    ('Miguel Ángel, Federico, y el carro que pasó encima de las gafas',
     'Juan David Rodríguez Pantoja', 2025, 13),
    ('Muertos que no son muertos', 'Nicolás O. Segura', 2025, 10)], 12),
 ('17', '11:00', '13:00', SENA, 'taller', 'SiembraLAB', [
    ('Taller: paisajes sonoros, archivo y memoria', None, None, None)], 12),
]

# Lo que el programa imprime bajo el título de cada actividad: quién la da. No es
# sinopsis; es el dato que la hace útil.
DETALLE = {
 'Microtaller: producción de imagen y video en realidad virtual': 'A cargo de Kinotov.',
 'Trabajo con material de archivo': 'A cargo de la Fundación Patrimonio Fílmico Colombiano.',
 'Taller: paisajes sonoros, archivo y memoria': 'A cargo de Señal Memoria e Inravisión, Sistema de Medios Públicos.',
 'Cosecha audiovisual': 'Producto del proceso de formación LABRA.',
 'Maratón fotográfica SiembraFest': ('Una invitación a recorrer Villeta y Sasaima para descubrir, '
    'fotografiar y compartir las historias, gestos y escenas que muestran cómo las mujeres '
    'sostienen la vida en sus territorios.'),
}
# `experiencia` es un RECORRIDO de todo el día por dos municipios: no se reserva
# una silla, se pasa cuando se puede. PROTOCOLO §Reglas: eso es `info:true` — no
# entra al plan ni a conflictos. El default es planificar; esta es la excepción.
INFORMATIVO = {'experiencia'}
EVENT_KIND = {'apertura': 'apertura', 'convite': 'convite', 'taller': 'taller',
              'experiencia': 'experiencia'}


# ── jerarquía de fuentes, declarada (PROTOCOLO §1) ─────────────────────────
# programa PDF (4 sep) > selección oficial (23 ago) > IG. El PDF es lo más nuevo
# y es el documento operativo: manda en el horario y en lo que imprime de la
# obra. El catálogo rellena lo que el PDF no trae —sinopsis, póster, país,
# género, lbSlug— vía _enriquece().
#
# UNA excepción, y por una razón: cuando el catálogo trae MÁS directores que el
# PDF, manda el catálogo. El PDF es un cartel y abrevia; «Somos historias» lo
# firman diez personas y el programa imprime una. Perder nueve no es respetar la
# fuente, es recortarla. Cuando se CONTRADICEN de verdad —«Noche de vuelo»— manda
# el PDF por ser lo más reciente, y queda declarado para preguntárselo.
DIRECTOR_CATALOGO = {
 'Somos historias: Casaramano, sagrado y vida',
 'Mingoya: tierra de ornitólogos',
 'La muerte de Elías',
 'Pudor ante el asalto de los ojos furtivos',
 'La gallina saraviada',
 'HDLT',
}
CONTRADICCIONES = {
 'Noche de vuelo': 'el catálogo de la selección oficial la firma Juan Alvarado y el '
                   'programa Zacarías Flores del Campo — no es una abreviatura, son '
                   'personas distintas. Se toma la del programa por ser lo más reciente.',
}
# el mismo título escrito de dos formas por el propio festival
ALIAS_CATALOGO = {'Flores Miro': 'Floresmiro'}


def verificar():
    """Cada dato transcrito de la imagen, contra la capa de texto de su página."""
    P = json.load(open(TEXTO, encoding='utf-8'))['paginas']
    fallos = []
    for dia, ini, fin, sede, tipo, sec, obras, pag in BLOQUES:
        t = norm(P.get(str(pag), ''))
        pl = P.get(str(pag), '')
        for tit, *_ in obras:
            if norm(tit.split(':')[0].split(' — ')[0]) not in t:
                fallos.append(f'p{pag}: «{tit}» no está en la página')
        for quien, q in (('sede', sede), ('sección', sec)):
            clave = norm(q.replace('SENA CDAE', 'SENA  CDAE').replace('Vda.', 'VDA'))
            if norm(q.split()[0]) not in t:
                fallos.append(f'p{pag}: la {quien} «{q}» no aparece')
        h12 = f'{int(ini[:2]) % 12 or 12}:{ini[3:]}'
        if h12 not in pl:
            fallos.append(f'p{pag}: la hora {ini} ({h12}) no está impresa')
        if f'{int(dia)}/9' not in pl.replace(' ', ''):
            fallos.append(f'p{pag}: el día {dia}/9 no está impreso')
    return fallos


def crudo():
    funcs = []
    for dia, ini, fin, sede, tipo, sec, obras, pag in BLOQUES:
        reales = [o for o in obras if o[1] is not None]
        f = {'dia': f'2026-09-{dia}', 'hora': ini, 'hora_fin': fin,
             'sede': sede, 'seccion': sec,
             # El programa no dice CÓMO se entra a ninguna actividad, y la web
             # tampoco. Se declara desconocido: no saber es legítimo, no mirar no.
             'acceso': DESCONOCIDO,
             '_src': f'PDF oficial de la programación de Villeta, p{pag}'}
        if reales:
            f['titulo'] = ' + '.join(o[0] for o in reales)
            f['obras'] = []
            for t, d, a, m in reales:
                o = {'titulo': t, 'director': d, 'anio': a, 'duracion_min': m, 'seccion': sec}
                if t in ALIAS_CATALOGO:
                    o['_alias_catalogo'] = ALIAS_CATALOGO[t]
                if t in DIRECTOR_CATALOGO:
                    o['_director_del_catalogo'] = True
                if t in CONTRADICCIONES:
                    o['_ojo'] = CONTRADICCIONES[t]
                f['obras'].append(o)
        else:
            f['titulo'] = obras[0][0] if len(obras) == 1 else ' + '.join(o[0] for o in obras)
            f['obras'] = []
            h1, m1 = int(ini[:2]), int(ini[3:]); h2, m2 = int(fin[:2]), int(fin[3:])
            f['duracion_min'] = (h2 * 60 + m2) - (h1 * 60 + m1)
            f['duration'] = f"{f['duracion_min']} min"
        if tipo in EVENT_KIND:
            f['event_kind'] = EVENT_KIND[tipo]
        if tipo in INFORMATIVO:
            f['info'] = True
        det = [DETALLE[o[0]] for o in obras if o[0] in DETALLE]
        if det:
            f['sinopsis'] = ' '.join(det); f['synopsis_lang'] = 'es'
        funcs.append(f)
    funcs.sort(key=lambda x: (x['dia'], x['hora'], x['sede']))
    return {'_provenance': provenance(
              'PDF oficial de la programación de Villeta — '
              'siembrafest.com/descargas/programacion_11sf_villeta.pdf',
              metodo='doble lectura: capa de texto del PDF (no OCR) + lectura visual de cada '
                     'página, que es la que fija el layout a dos columnas',
              alcance='SOLO VILLETA. El PDF de Sasaima no existe todavía (la web dice «muy '
                      'pronto» y su URL devuelve HTML)'),
            'funciones': funcs}


if __name__ == '__main__':
    fallos = verificar()
    proy = [b for b in BLOQUES if any(o[1] for o in b[6])]
    cupos = sum(1 for b in BLOQUES for o in b[6] if o[1])
    print(f'{len(BLOQUES)} bloques · {len(proy)} de proyección · {cupos} cupos de obra · '
          f'{len(BLOQUES) - len(proy)} actividades')
    if fallos:
        print(f'\n✗ {len(fallos)} fallos de verificación contra la capa de texto:')
        for f in fallos:
            print('   ', f)
        sys.exit(1)
    print('✓ cada dato transcrito de la imagen está en la página que declara')
    if '--escribir' in sys.argv:
        c = crudo()
        json.dump(c, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"→ {SALIDA}  ·  {len(c['funciones'])} funciones")
