#!/usr/bin/env python3
"""ficfusa-2026-catalogo.py — la Selección Oficial de FICFUSA 2026 (13.ª versión,
11–16 nov 2026, Fusagasugá). PRE-ONBOARDING, radar #1032.

LA FUENTE: el post «Selección oficial FICFUSA 2026» (wp-json posts/9882,
publicado 21 oct 2026). Declara 62 obras (42 en competencia, 20 en muestras),
y las va subiendo por tandas. Al 4 nov 11:54 publica 53 tarjetas en cinco
secciones: faltan 9 de las 20 no competitivas (ni en la página, ni en wp-json
media, ni en Instagram). Las tarjetas se leen del HTML de la página: wp-json
posts/9882 trae los shortcodes del constructor, sin ellas.

El dato está PINTADO en las tarjetas: se lee con pipeline/ocr.py y se cruza con
la transcripción a ojo (OJOS). El script FRENA si una tarjeta no trae el
director, el año o la duración transcritos: la lectura a ojo no se cree sin la
del OCR.

Escribe festivals/staging/ficfusa-2026-catalogo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
from ocr import leer  # noqa: E402

SRC = f'{REPO}/fuentes/ficfusa-2026'
OUT = f'{REPO}/festivals/staging/ficfusa-2026-catalogo.json'
URL = 'https://ficfusa.com/seleccion-oficial-ficfusa-2026/'
UP = 'https://ficfusa.com/wp-content/uploads/2026/10/'

# Transcrito a ojo de cada tarjeta (22 oct). El OCR leyó «materidad»: manda la lámina.
SECCION = 'Hecho por Colombianas'   # verbatim: «CORTOMETRAJES DIRIGIDOS POR MUJERES · HECHO POR COLOMBIANAS»
# Mismo molde: el antetítulo describe, el título grande es el nombre → en Título.
REGION = 'Un Relato Hecho Región'  # verbatim: «CORTOMETRAJES NACIONALES · Un relato hecho región»
MUJERES = 'Hechos de Mujeres'  # «CORTOMETRAJES NACIONALES E INTERNACIONALES · Hechos de mujeres» (el antetítulo dice cortos; las 10 tarjetas son de 1:02 h a 1:59 h)
CORTO = 'Un Hecho Corto'  # «CORTOMETRAJES NACIONALES · Un hecho corto»
FUERA = 'Selección Oficial'  # «FUERA DE COMPETENCIA · Selección oficial»: 11 de las 20 no competitivas

OJOS = [
    ('seleccion-oficial-hecho-por-colombianas-ficfusa-desaprender-la-maternidad.webp',
     dict(titulo='Desaprender la maternidad', director='Juliana Erazo Gómez', anio=2025,
          pais='Colombia, Países bajos', duracion_min=11, genero='Animación', _dur='10:45')),
    ('akababuru-expresion-de-asombro-ficfusa.webp',
     dict(titulo='Akababuru: expresión de asombro', director='Irati Dojura Landa Yagarí', anio=2025,
          pais='Colombia', duracion_min=14, genero='Fantasía', _dur='13:32')),
    ('nina-chilapa-ficfusa-seleccion-oficial-hecho-por-colombianas.webp',
     dict(titulo='Niña chilapa', director='Juana Lotero López', anio=2025,
          pais='Colombia', duracion_min=17, genero='Documental', _dur='17')),
    # 22 oct 22:54–23:02: la página suma tres (media 9908–9910).
    ('seleccion-oficial-ficfusa-una-vez-en-un-cuerpo.webp',
     dict(titulo='Una vez en un cuerpo', director='María Cristina Pérez', anio=2025,
          pais='Colombia, Estados Unidos', duracion_min=11, genero='Animación', _dur='10:20', _fecha='2026-10-22')),
    ('chaika-seleccion-oficial-ficfusa.webp',
     dict(titulo='Chaika', director='Ingrid Paola Bonilla Rodríguez', anio=2025,
          pais='Colombia', duracion_min=15, genero='Ciencia ficción', _dur='14:40', _fecha='2026-10-22')),
    ('salsa-ficfusa-seleccion-oficial.webp',
     dict(titulo='Salsa', director='Antonina Kerguelén Román', anio=2024,
          pais='Colombia', duracion_min=14, genero='Ficción', _dur='14', _fecha='2026-10-22')),
    # 23 oct 20:58–21:30: la página suma siete más a «Hecho por Colombianas» (media 9913–9922).
    ('seleccion-ficfusa-pudor-ante-el-asalto-de-los-ojos-furtivos.webp',
     dict(titulo='Pudor ante el asalto de los ojos furtivos', director='Laura María Rodríguez', anio=2025,
          pais='Colombia', duracion_min=9, genero='Animación', _dur='8:35', _fecha='2026-10-23')),
    ('sinfonia-del-viaje-a-la-luna-ficfusa.webp',
     dict(titulo='Sinfonía del viaje a la luna', director='Sandra Reyes Sotomayor', anio=2026,
          pais='Colombia', duracion_min=10, genero='Animación', _dur='9:24', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-kanekalon.webp',
     dict(titulo='Kanekalon', director='Sara J. Asprilla', anio=2025,
          pais='Colombia', duracion_min=13, genero='Ficción', _dur='12:30', _fecha='2026-10-23')),
    ('la-mona-seleccion-oficial-ficfusa-2026.webp',
     dict(titulo='La mona', director='Laura Gutiérrez Ardila', anio=2025,
          pais='Colombia', duracion_min=19, genero='Ficción, Wéstern', _dur='18:18', _fecha='2026-10-23')),
    ('seleccion-ficfusa-entrelazadas.jpg',
     dict(titulo='Entrelazadas', director='Alejandra Morales García', anio=2024,
          pais='Colombia', duracion_min=15, genero='Animación, Híbrido', _dur='14:36', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-madres-de-nacimiento.webp',
     dict(titulo='Madres de nacimiento', director='Gloria Isabel Gómez Ceballos', anio=2025,
          pais='Francia', duracion_min=9, genero='Documental, Experimental', _dur='8:08', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-chicha-la-chicharra.webp',
     dict(titulo='Chicha la chicharra', director='Sofía Alejandra Uzcátegui León', anio=2025,
          pais='Colombia', duracion_min=10, genero='Animación', _dur='10', _fecha='2026-10-23')),
    # 23 oct 22:21–22:55: sección nueva «CORTOMETRAJES NACIONALES · Un relato hecho región» (media 9927–9933).
    ('seleccion-oficial-ficfusa-tuktu-padre-maiz.webp',
     dict(titulo='Tuktu padre maíz', director='Mauricio Prieto', anio=2025,
          pais='Colombia', duracion_min=14, genero='Animación', _dur='13:45', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-como-el-agua-la-piedra-y-la-espuma.webp',
     dict(titulo='Como el agua, la piedra y la espuma', director='Diana Marcela Moreno', anio=2024,
          pais='Colombia', duracion_min=26, genero='Documental', _dur='25:01', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-la-gran-hazana.webp',
     dict(titulo='La gran hazaña', director='Luber Yesid Zúñiga Ordóñez', anio=2024,
          pais='Colombia', duracion_min=15, genero='Drama, Aventura', _dur='14:56', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-bajo-el-ultimo-aliento.webp',
     dict(titulo='Bajo el último aliento', director='Pedro Valencia', anio=2024,
          pais='Colombia', duracion_min=6, genero='Drama, Experimental', _dur='5:15', _fecha='2026-10-23', _sec=REGION)),
    # 30 oct 09:07–13:02 (media 9936–9976) y 2–4 nov (10004–10019): completan las cuatro competitivas
    # y abren «FUERA DE COMPETENCIA · Selección oficial». Mirado tarjeta por tarjeta.
    ('seleccion-oficial-ficfusa-mas-alla.webp',
     dict(titulo='Más allá', director='Bettina López Mendoza', anio=2025,
          pais='Colombia, Venezuela, Estados Unidos, Canadá', duracion_min=16, genero='Drama, Fantasía', _dur='15:24 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-sonidos-de-resistencia.webp',
     dict(titulo='Sonidos de la resistencia', director='Juan Ruiz', anio=2023,
          pais='Colombia', duracion_min=11, genero='Documental', _dur='10:07 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-sukua.webp',
     dict(titulo='Sukua', director='Omar E. Ospina Giraldo', anio=2025,
          pais='Colombia', duracion_min=17, genero='Drama', _dur='16:42 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-cayenas-libertarias.webp',
     dict(titulo='Cayenas libertarias', director='Javier Camilo Aranguren', anio=2025,
          pais='Colombia', duracion_min=18, genero='Documental', _dur='17:02 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-la-gallina-saraviada.webp',
     dict(titulo='La gallina saraviada', director='Ingrid Paola Bonilla Rodríguez', anio=2025,
          pais='Colombia', duracion_min=11, genero='Drama rural', _dur='11 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-relatos-del-camino.webp',
     dict(titulo='Relatos del camino', director='Daniel Prieto', anio=2025,
          pais='Colombia', duracion_min=12, genero='Animación, Documental', _dur='11:52 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-legado.webp',
     dict(titulo='Legado', director='Zumaya Mayers y Rodrigo Cuervo', anio=2024,
          pais='Colombia, Ecuador', duracion_min=25, genero='Documental', _dur='24:31 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-pawa.webp',
     dict(titulo='Pawa', director='Marbel Ina Vanegas Jusayu', anio=2026,
          pais='Colombia', duracion_min=23, genero='Ficción', _dur='22:05 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-secuencia.webp',
     dict(titulo='Secuencia', director='Chiro Castellanos H', anio=2025,
          pais='Colombia', duracion_min=16, genero='Ficción, Drama', _dur='15:21 min', _fecha='2026-10-30', _sec=REGION, _tipo='corto')),
    ('seleccion-oficial-ficfusa-puntos-de-fuga.webp',
     dict(titulo='Puntos de fuga', director='Lina Rodríguez', anio=2025,
          pais='Colombia, Canadá', duracion_min=72, genero='Documental', _dur='1:12 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-la.webp',
     dict(titulo='La', director='Tephy Piedrahita Avellaneda', anio=2026,
          pais='Colombia, Argentina', duracion_min=62, genero='Animación, Documental, Experimental', _dur='1:02 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-la-luz-por-primera-vez.webp',
     dict(titulo='La luz por primera vez', director='Ibeth Rey y Frank Rodríguez Rojas', anio=2026,
          pais='Colombia, España', duracion_min=78, genero='Documental', _dur='1:18 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-la-vida-es.webp',
     dict(titulo='La vida es', director='Lorena Villarreal', anio=2025,
          pais='México', duracion_min=119, genero='Drama, Comedia', _dur='1:59 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-pelicula-sobre-las-olas.webp',
     dict(titulo='Sobre las olas', director='Horacio Alcalá', anio=2025,
          pais='España, México', duracion_min=98, genero='Drama', _dur='1:38 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-comparsa.webp',
     dict(titulo='Comparsa', director='Vickie Curtis y Doug Anderson', anio=2025,
          pais='Guatemala, Estados Unidos', duracion_min=78, genero='Documental', _dur='1:18 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-truck-mama.webp',
     dict(titulo='Truck mama', director='Zippy Nyaruri', anio=2025,
          pais='Kenia, Países bajos, Arabia saudí, Sudáfrica', duracion_min=85, genero='Documental', _dur='1:25 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-framing-her.webp',
     dict(titulo='Framing her', director='Coco Wouters', anio=2026,
          pais='Bélgica, Suecia, Reino Unido, Noruega', duracion_min=92, genero='Documental', _dur='1:32 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-matinino.webp',
     dict(titulo='Matininó', director='Gabriela Díaz Arp', anio=2026,
          pais='Puerto Rico, República Dominicana', duracion_min=89, genero='Documental, Fantasía', _dur='1:29 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-la-peluqueria-no-se-cierra.webp',
     dict(titulo='La peluquería no se cierra', director='Vanesa Valdemoros', anio=2026,
          pais='España', duracion_min=69, genero='Documental', _dur='1:09 h', _fecha='2026-10-30', _sec=MUJERES, _tipo='largo')),
    ('seleccion-oficial-ficfusa-ir-hacia-dentro.webp',
     dict(titulo='Ir hacia adentro', director='Laura Alejandra Jiménez Ruiz', anio=2025,
          pais='Colombia', duracion_min=6, genero='Animación, Experimental', _dur='5:42 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('seleccion-oficial-ficfusa-sol-de-niebla.webp',
     dict(titulo='Sol de niebla', director='Maria Jose Ibarra y Florentino Vargas', anio=2026,
          pais='Colombia', duracion_min=6, genero='Documental, Experimental', _dur='5:48 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('seleccion-oficial-ficfusa-oyeme-pelicula.webp',
     dict(titulo='Óyeme', director='Joanna Cecilia Gómez', anio=2025,
          pais='Colombia', duracion_min=5, genero='Drama, Realismo mágico', _dur='4:33 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('seleccion-oficial-ficfusa-victorias-y-glorias-relatos-de-campeonas.webp',
     dict(titulo='Victorias y Glorias - Relatos de campeonas', director='Luber Yesid Zúñiga Ordóñez', anio=2025,
          pais='Colombia', duracion_min=12, genero='Documental', _dur='11:10 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('seleccion-oficial-ficfusa-que-el-cielo-nos-perdone.webp',
     dict(titulo='Que el cielo nos perdone', director='Andrés Buitrago', anio=2025,
          pais='Colombia', duracion_min=17, genero='Horror, Terror', _dur='16:49 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('seleccion-oficial-ficfusa-animista-1.webp',
     dict(titulo='Animista', director='Sebastián Giraldo', anio=2024,
          pais='Colombia', duracion_min=9, genero='Experimental', _dur='8:20 min', _fecha='2026-10-30', _sec=CORTO, _tipo='corto')),
    ('ficfusa-muestra-internacional-2026-domingo.webp',
     dict(titulo='Domingo', director='Day Sena', anio=2025,
          pais='Brasil', duracion_min=21, genero='Drama', _dur='20:01 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-internacional-2026-un-trato-brillante.webp',
     dict(titulo='Un trato brillante', director='Libertad Benavides, Alex Parra, Alicia Bullich, Luz Rodriguez, Carolina Cuellar, Consuelo Soto, María Bonillo y Beatriz Esteban', anio=2026,
          pais='España', duracion_min=9, genero='Fantasía, Stop motion', _dur='8:40 m', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-internacional-floreceran.webp',
     dict(titulo='Florecerán!', director='Claudia Ruiz', anio=2026,
          pais='Argentina', duracion_min=2, genero='Documental Animado', _dur='1:42 m', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-arbol-en-pie.webp',
     dict(afiche='assets/ficcali-2026/arbol-en-pie.jpg', titulo='Árbol en pie', director='Red Comunitaria Trans, Rodrigo Torrijos y Mapa López', anio=2026,
          pais='Colombia', duracion_min=6, genero='Bullerengue, Afrotravesti', _dur='5:55 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-transversal-30ff.webp',
     dict(titulo='Transversal 30ff', director='Checho Mejía', anio=2025,
          pais='Colombia', duracion_min=6, genero='Comedia', _dur='6:00 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-cuando-la-palabra-se-hace-busqueda.webp',
     dict(titulo='Cuando la palabra se hace búsqueda: El eco de sus voces', director='Frank Benítez Peña', anio=2026,
          pais='Colombia', duracion_min=61, genero='Documental', _dur='1:01 h', _fecha='2026-11-04', _sec=FUERA, _tipo='largo')),
    ('ficfusa-muestra-nacional-el-espejo-de-la-vida.webp',
     dict(titulo='El espejo de la vida', director='Simón Sánchez Plazas', anio=2025,
          pais='Colombia', duracion_min=10, genero='Animación, Drama', _dur='9:17 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-hdlt.webp',
     dict(afiche='assets/filcmar-2026/hdlt.jpg', titulo='Hdlt', director='Artefactum Suba', anio=2025,
          pais='Colombia', duracion_min=19, genero='Falso documental, Comedia', _dur='18:22 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-la-libertad-es-mi-causa.webp',
     dict(titulo='La libertad es mi causa', director='Claudia Bermúdez Vélez', anio=2024,
          pais='Colombia', duracion_min=101, genero='Documental', _dur='1:41 h', _fecha='2026-11-04', _sec=FUERA, _tipo='largo')),
    ('muestra-nacional-ficfusa-salud-mutante.webp',
     dict(titulo='Salud Mutante', director='Daniel Rodríguez Gaitán', anio=2025,
          pais='Colombia', duracion_min=19, genero='Ciencia ficción, Distopía', _dur='18:03 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
    ('ficfusa-muestra-nacional-sinfonia-de-oficios.webp',
     dict(titulo='Sinfonía Incompleta de Oficios del Fonce', director='Nelson Omar Silva Sánchez', anio=2024,
          pais='Colombia', duracion_min=16, genero='Sinfonía urbana', _dur='15:54 min', _fecha='2026-11-04', _sec=FUERA, _tipo='corto')),
]


def main():
    rutas = [f'{SRC}/{a}' for a, _ in OJOS]
    falta = [r for r in rutas if not os.path.exists(r)]
    if falta:
        sys.exit('✗ faltan las tarjetas: curl -sL ' + UP + '<archivo> -o fuentes/ficfusa-2026/<archivo>\n  ' + '\n  '.join(falta))
    ocr = leer(rutas)
    obras = []
    for (arch, o), r in zip(OJOS, rutas):
        txt = ' '.join(ocr[r])
        dur = o['_dur'] if o['_dur'].split()[-1] in ('h', 'm', 'min') else o['_dur'] + ' min'
        for tok in (o['director'], str(o['anio']), dur):
            if tok not in txt:
                sys.exit(f'✗ {arch}: el OCR no corrobora «{tok}»')
        o = dict(o); o.pop('_dur'); fecha = o.pop('_fecha', '2026-10-21'); sec = o.pop('_sec', SECCION); tipo = o.pop('_tipo', 'corto')
        if sec == FUERA:
            o['competencia'] = False
        obras.append({**o, 'tipo': tipo, 'seccion': sec,
                      '_src': {'url': URL, 'tarjeta': UP + arch, 'date': fecha}})
    json.dump({'_provenance': provenance(URL, metodo='wp-json posts/9882 + tarjetas leídas con ocr.py y a ojo',
                                         publicado='2026-10-21'),
               '_nota': 'el post declara 62 obras (42 en competencia, 20 en muestras); al 4 nov 11:54 publica estas 53: las 42 competitivas y 11 de las 20 fuera de competencia',
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
