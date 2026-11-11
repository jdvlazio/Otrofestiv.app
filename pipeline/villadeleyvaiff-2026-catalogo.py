#!/usr/bin/env python3
"""villadeleyvaiff-2026-catalogo.py — las competencias del 20 Festival
Internacional de Cine de Villa de Leyva (13–16 nov 2026, lema «De Corazón»).
PRE-ONBOARDING. NO es Villa del Cine (villadelcine2026), que es otro festival.

LA FUENTE: ocho carruseles de @festcinevilla, descubiertos por Apify y
bajados SIN SESIÓN por el embed (ig.urls_laminas + ig.bajar_laminas) a
fuentes/ig/<sc>/. El dato está PINTADO en la lámina (título, «Dir.», país);
el pie solo trae arrobas. Transcripción a ojo, lámina por lámina, cruzada con
pipeline/ig-lecturas.py <sc> --ojos (villadeleyvaiff-2026-verificar.py).

  Dezv0XgmfuC (22 oct)  COMPETENCIA ESCUELAS             portada «Cortos Escuelas»       9
  De2SOuWmRFm (23 oct)  RESULTADOS - CORTO EXPERIMENTAL  portada «Cortos Experimental»   9
  De2jZJeGZFd (23 oct)  COMPETENCIA- CORTO DOCUMENTAL    portada «Cortos Documental»     8
  De4KTcokcBw (24 oct)  COMPETENCIA- LARGO DOCUMENTAL    portada «Largos Documental»     5
  De5rlOskZXe (25 oct)  COMPETENCIA- CORTO INTERNACIONAL portada «Cortos Internacional»  6
  De8I8Qqkdah (25 oct)  COMPETENCIA - CORTO ANIMACIÓN    portada «Cortos Animación»     10
  De9ghZ8ka6I (26 oct)  COMPETENCIA- CORTO FESTIVALITO   portada «Cortos Festivalito»   10
  DfASiVIkW3R (27 oct)  COMPETENCIA- CORTO PROFESIONAL COLOMBIA  portada «Cortos Colombia» 8

SEGUNDA FUENTE: los PDF de la web (villadeleyvaiff.co, creados 28–29 oct, copia en
fuentes/villadeleyvaiff-2026/). Repiten las láminas salvo una obra que el carrusel
no trae: «Lo que calla el hoyo» (Cortos Documental, pág. 9) → SOLO_PDF.

Tres obras están en Animación Y Festivalito: una sola fila, con _seccion_tambien.
Cortos Colombia no pinta país: lo da la sección. «Zacarìas» va pintado con acento
grave en la lámina y el PDF: errata obvia, se escribe «Zacarías».
«20 LAB Ópera de Leyva» (De96CbVGaEr, 7 proyectos) NO entra: son proyectos en
desarrollo, no obras que se proyecten.

Lámina 00 = portada; la ÚLTIMA = cierre «De Corazón». Las láminas son STILLS
bajo una banda de color, no afiches: de aquí no sale ningún afiche.

Sección: la cabecera del pie, en Título («Competencia Corto Documental»). El de
experimental dice «RESULTADOS» en vez de «COMPETENCIA»: es la selección (el
festival no ha ocurrido) y se nombra como sus pares, anotado aquí.
Títulos: la lámina va en MAYÚSCULA sostenida → mayúscula inicial, sin tocar
letra ni tilde. «Lia», «Maria», «Gonzalez» van como están pintados.

Falta: año y duración de todo (las láminas no los traen); programación.
El script FRENA si un post no da tantas obras como láminas menos portada y cierre.
Escribe festivals/staging/villadeleyvaiff-2026-catalogo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

OUT = f'{REPO}/festivals/staging/villadeleyvaiff-2026-catalogo.json'
IG = 'https://www.instagram.com/p/{}/'

# (shortcode, fecha, sección, tipo, láminas, [(título, director, país)])
POSTS = [
    ('Dezv0XgmfuC', '2026-10-22', 'Competencia Escuelas', 'corto', 11, [
        ('Cielo de enero', 'Sofía Plesky', 'Argentina'),
        ('Demian', 'Diego Padilla', 'México'),
        ('El mejor regalo', 'Argenis Herrera', 'Chile'),
        ('La casa del marica', 'Nicolás Malano', 'Argentina'),
        ('La muerta que habla', 'Candela Gonzalez, Agustín Fittipaldi', 'Argentina'),
        ('Los lobo', 'Saaed García', 'Colombia'),
        ('Términa', 'Juan José Guevara', 'Colombia'),
        ('Sol en Lidia', 'Andrea Boggiano', 'Perú'),
        ('Valsa para Maria Domingas', 'Eugênia Santana', 'Brasil'),
    ]),
    ('De2SOuWmRFm', '2026-10-23', 'Competencia Corto Experimental', 'corto', 11, [
        ('Ballena', 'Ricardo Monteiro', 'Brasil, Cuba'),
        ('Chaika', 'Ingrid Paola Bonilla', 'Colombia, Cuba'),
        ('“Convocatoria general del gremio”', 'Bruna Pessoa', 'Brasil'),
        ('Cuarto de flores', 'Sofía Guerrini', 'Argentina'),
        ('Día 1 Narita–Tokyo', 'João Krefer', 'Japón'),
        ('Las criaturas', 'Francisco Zornosa', 'Colombia'),
        ('Oigo una ciudad', 'Ciro Araujo', 'Brasil'),
        ('Rol – El río se llevaba las manchas de la vida', 'Selma Parreira', 'Brasil'),
        ('Zakih', 'Sara Tavares', 'Brasil'),
    ]),
    ('De2jZJeGZFd', '2026-10-23', 'Competencia Corto Documental', 'corto', 10, [
        ('Baile por la ciudad', 'Rosana Dias', 'Brasil'),
        ('Claudete', 'Gabriela Kopp', 'Brasil'),
        ('Eda', 'Giovanna Tumini', 'Argentina'),
        ('Jeña', 'Mónica Loza', 'México, Cuba'),
        ('Lia', 'Erika Piragauta', 'Colombia'),
        ('Logos', 'Britney Federline', 'Brasil'),
        ('Lo que no se puede borrar', 'Iñaki Dubourg', 'Argentina'),
        ('Tragedia sentimental', 'Juan Ferro', 'Colombia'),
    ]),
    ('De4KTcokcBw', '2026-10-24', 'Competencia Largo Documental', 'largo', 7, [
        ('Dama de las mil máscaras', 'Wainer Méndez', 'Costa Rica'),
        ('El extraordinario viaje del dragón', 'Kaori Flores Y.', 'Venezuela'),
        ('Notas sobre un destierro', 'Gustavo Castro', 'Brasil'),
        ('Portento', 'Gabriela Nápoles', 'México'),
        ('Sex panchitos', 'Gustavo Gamou', 'México'),
    ]),
    ('De5rlOskZXe', '2026-10-25', 'Competencia Corto Internacional', 'corto', 8, [
        ('Armónica', 'Michele Diniz', 'Brasil'),
        ('El derrumbe', 'Iván Djeredjian', 'Argentina'),
        ('El silencio de la tierra', 'Rogelio Escatel', 'México'),
        ('Las heridas', 'Nicolás Llanos', 'Chile'),
        ('Los chorros', 'Juan Manuel Álvarez', 'Argentina'),
        ('Yegua', 'Virginia Scaro', 'Argentina'),
    ]),
    ('De8I8Qqkdah', '2026-10-25', 'Competencia Corto Animación', 'corto', 12, [
        ('A la sombra de los árboles', 'Yulia Ivanova', 'Rusia'),
        ('Bumblebee', 'Natalia Chernysheva', 'Rusia'),
        ('Cuna de lobas', 'Emilia Schettino', 'México'),
        ('El cuerpo de Cristo', 'Bea Lema', 'España'),
        ('Emechiche, el renacer de los cabeciblancos', 'Juan Camilo González', 'Colombia, Argentina'),
        ('En la sombra de la garza', 'Nicolas Bianco', 'Francia'),
        ('¡Florecerán!', 'Claudia Ruiz', 'Argentina'),
        ('Merrimundi', 'Niles Atallah', 'Chile'),
        ('Saba', 'Liron Topaz', 'USA'),
        ('Una vez en un cuerpo', 'María Cristina Pérez', 'Colombia'),
    ]),
    ('De9ghZ8ka6I', '2026-10-26', 'Competencia Corto Festivalito', 'corto', 12, [
        ('Bumblebee', 'Natalia Chernysheva', 'Rusia'),
        ('Dance dance evolution', 'Jonathan Abbaszadeh, Finn Falk, Yosi Hsu, Mia Lou, Huidi Zhang, Ruiwen Zhang', 'Francia'),
        ('Danza de las muñecas', 'Yulia Ivanova', 'Rusia'),
        ('Danza invisible', 'Marina Kerber, Cristiane Oliveira', 'Brasil'),
        ('En la sombra de la garza', 'Nicolas Bianco', 'Francia'),
        ('Las zapatillas mágicas', 'Luber Yesid Zúñiga', 'Colombia'),
        ('Loop', 'Mali Delepière, Flora Jacon, Alicia Salvi, Hongyi Liu, Saïd Saïd, Tristan Truphemus', 'Francia'),
        ('Mi pequeña vida en la isla', 'Nina Bisyarina', 'Rusia'),
        ('Saba', 'Liron Topaz', 'USA'),
        ('Snorri', 'Thierry Marchand', 'Alemania'),
    ]),
    ('DfASiVIkW3R', '2026-10-27', 'Competencia Corto Profesional Colombia', 'corto', 10, [
        ('Agachar el rostro', 'Camilo Medina Noy', 'Colombia'),
        ('Criatura', 'Juan Pablo Ríos', 'Colombia'),
        ('Chaski Pacha', 'Ramiro Fierro', 'Colombia'),
        ('Esquirlas de caracol', 'Manuel Alejandro Sánchez', 'Colombia'),
        ('Gris', 'Loren Escandón', 'Colombia'),
        ('Malas posturas', 'Juan Pablo Castro', 'Colombia'),
        ('Noche de vuelo', 'Zacarías Flores del Campo', 'Colombia'),
        ('Refracción', 'Isabella Palacio', 'Colombia'),
    ]),
]

PDF_DOC = 'https://www.villadeleyvaiff.co/_files/ugd/66001c_061dc0d2b25b413f952e19f20bb5786b.pdf'
SOLO_PDF = [
    {'titulo': 'Lo que calla el hoyo', 'director': 'Francisco Zornosa', 'pais': 'Colombia',
     'tipo': 'corto', 'seccion': 'Competencia Corto Documental',
     '_src': {'url': PDF_DOC, 'date': '2026-10-29',
              'pdf': 'fuentes/villadeleyvaiff-2026/cortos-documental.pdf', 'pagina': 9}},
]


def main():
    obras = []
    for sc, fecha, seccion, tipo, laminas, filas in POSTS:
        if len(filas) != laminas - 2:
            sys.exit(f'✗ {sc}: {len(filas)} obras y {laminas - 2} láminas de obra')
        dir_ig = f'{REPO}/fuentes/ig/{sc}'
        if not os.path.isdir(dir_ig):
            sys.exit(f'✗ faltan las láminas de {sc}: ig.bajar_laminas(sc, ig.urls_laminas(sc))')
        for i, (titulo, director, pais) in enumerate(filas, 1):
            lamina = f'fuentes/ig/{sc}/{i:02d}.jpg'
            igual = next((o for o in obras if o['titulo'] == titulo and o['director'] == director), None)
            if igual:
                igual['_seccion_tambien'] = seccion
                igual['_src']['tambien'] = {'url': IG.format(sc), 'date': fecha, 'lamina': lamina}
                continue
            obras.append({'titulo': titulo, 'director': director, 'pais': pais,
                          'tipo': tipo, 'seccion': seccion,
                          '_src': {'url': IG.format(sc), 'date': fecha,
                                   'lamina': lamina}})
    obras += SOLO_PDF
    json.dump({'_provenance': provenance('https://www.instagram.com/festcinevilla/',
                                         metodo='láminas de 8 carruseles IG (embed, sin sesión), a ojo + ig-lecturas; PDF de la web',
                                         publicado='2026-10-22/29'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
