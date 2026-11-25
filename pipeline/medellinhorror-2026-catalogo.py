#!/usr/bin/env python3
"""medellinhorror-2026-catalogo.py — Medellín Horror Fest 2026 (sexta edición).
PRE-ONBOARDING (18 nov 2026).

LAS FUENTES (todas en fuentes/medellinhorror-2026/, gitignored):
  · revista-01.pdf — «Revista Digital edición 01 Medellín Horror Fest 2026»,
    enlazada desde la home de medellinhorrorfest.com. Págs. 9–10: las 13 obras
    de la SELECCIÓN OFICIAL con dirección, país y duración. Págs. 3–4: los tres
    largometrajes en House of Demons Medellín, con día y hora pintados en la
    lámina (pág. 4) y «ENTRADA GRATIS · Cra. 80 #33-41, Laureles».
  · web/*.webp — los 13 pósteres del carrusel de medellinhorrorfest.com/seleccion-2026/
    (publicados el 14 nov). Contrastan título y director.

TRIPLE LECTURA: (1) texto del PDF (pdftotext), (2) la lámina a ojo
(pdftoppm a 220 ppp), (3) OCR del sistema (pipeline/ocr.py) sobre los 13
pósteres de la web. Lo que el póster corrige del PDF va en CORRIGE con su porqué.

COBERTURA INVERSA: la revista dice «13 cortometrajes seleccionados» (pág. 8) y
la web carga 13 pósteres; las dos listas son las mismas 13 (assert abajo).
La revista dice «Tres largometrajes» (portada) y la pág. 4 trae tres.

NINGUNA fuente trae AÑO. Los cortos no tienen día ni hora: van en Hero Academy
de Comic Con Medellín (Plaza Mayor, 27–29 nov) «muy pronto más información»
(/actividades/, 18 nov).

Escribe festivals/staging/medellinhorror-2026-catalogo.json
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import slug  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/medellinhorror-2026-catalogo.json'
FECHA = '2026-11-18'
REVISTA = 'https://medellinhorrorfest.com/wp-content/uploads/2026/11/Revista-Digital-edicion-01-Medellin-Horror-Fest-2026.pdf'
WEB = 'https://medellinhorrorfest.com/seleccion-2026/'
SO = 'Selección Oficial'   # web: «SELECCIÓN OFICIAL 2026»; revista págs. 9–10: «SELECCIÓN OFICIAL:»

# (n, título, dirección, país, duración txt, minutos, póster web, pág. revista)
CORTOS = [
    (1, 'Happy', 'Victor Basallote', 'España', '7 minutos', 7, 'Happy', 9),
    (2, 'Last Generation', 'Silvia Conesa', 'España', '9 minutos', 9, 'Last-Generation', 9),
    (3, 'Rewritten', 'Andrés Molano Moncada', 'Colombia', '10 minutos', 10, 'Rewritten', 9),
    (4, 'Familier / Familiar', 'Julien Homère', 'Francia', '10 minutos 39 segundos', 11, 'Familiar', 9),
    (5, 'House Rules', 'Geri Courtney-Austein', 'Estados Unidos', '9 minutos 58 segundos', 10, 'House-Rules', 9),
    (6, 'Forgetting', 'Jesus Cazares', 'México', '10 minutos', 10, 'Forgetting', 9),
    (7, 'Tenebrios', 'Tarik Antón Ferro', 'Argentina', '6 minutos 59 segundos', 7, 'TENEBRIOS', 9),
    (8, 'The Screaming', 'Guillaume Boivin, Steve Villeneuve', 'Canadá', '8 minutos', 8, 'The-Screaming', 10),
    (9, 'There Is Something Behind You', 'Julián Andrés Gómez Reyes', 'Colombia', '6 minutos 25 segundos', 6,
     'There-is-Something-Behind-You', 10),
    (10, 'Bugaboo', 'Benjamín Morehead', 'Estados Unidos', '5 minutos 24 segundos', 5, 'Bugaboo', 10),
    (11, 'Snacktime', 'Alphonse Ferrari', 'Francia', '7 minutos 46 segundos', 8, 'Snacktime', 10),
    (12, 'Closing Hour', 'Tim Smink', 'Países Bajos', '8 minutos 34 segundos', 9, 'Closing-Hour', 10),
    (13, 'Borrowed Light', 'Christian Stahlhofen', 'Suecia', '6 minutos 16 segundos', 6, 'Borrowed-Light', 10),
]
CORRIGE = {
    'The Screaming': 'póster: «UN FILM DE GUILLAUME BOIVIN ET STEVE VILLENEUVE» (la revista: «Boivín»)',
    'Borrowed Light': 'póster: «DIRECTOR & CINEMATOGRAPHER CHRISTIAN STAHLHOFEN»; la revista dice «Submitter '
                      'registrado en FilmFreeway Christian Markus Stalhhofen», no director',
    'Tenebrios': 'revista y póster en mayúsculas («TENEBRIOS»): caja de oración',
}
NOTA = {'Familier / Familiar': 'revista: «Versión con subtítulos en español según FilmFreeway»'}

# Largometrajes: revista pág. 4, lámina «26 Y 27 DE NOVIEMBRE DE 2026 · HOUSE OF DEMONS MEDELLÍN»
LARGOS = [
    ('El Susurro', 'Gustavo Hernández', '2026-11-26', '20:00',
     'pág. 4: «26 DE NOV 8:00PM»; póster: «DEL DIRECTOR DE VIRUS:32 · LA CASA MUDA» (= Gustavo Hernández); '
     'pág. 3: «LARGOMETRAJE INVITADO AL FESTIVAL · PELÍCULA DEL DIRECTOR DE VIRUS 32»'),
    ('Demonatrix', 'Jeff Ferrell, Aurelio Voltaire', '2026-11-26', '22:00',
     'pág. 4: «26 DE NOV 10:00PM»; póster: «A FILM BY JEFF FERRELL AND AURELIO VOLTAIRE»'),
    ('Sierra: El álbum mortuorio', 'Carlos Ortiz', '2026-11-27', '22:00',
     'pág. 4: «27 DE NOV 10:00PM»; pág. 3: «DIRIGIDA POR CARLOS ORTIZ»; índice: «Sierra: El álbum mortuorio»'),
]


def main():
    assert [c[0] for c in CORTOS] == list(range(1, 14)), 'la revista y la web dicen 13'
    obras = []
    for n, tit, dire, pais, dtxt, m, web, pag in CORTOS:
        o = {'titulo': tit, 'director': dire, 'pais': pais, 'duracion_txt': dtxt, 'duracion_min': m,
             'tipo': 'corto', 'seccion': SO,
             'franja': 'Hero Academy · Comic Con Medellín, 27–29 nov (sin día ni hora publicados)',
             'imagen_web': f'fuentes/medellinhorror-2026/web/{web}.webp',
             '_src': {'url': f'{REVISTA}#page={pag}', 'poster': f'https://medellinhorrorfest.com/wp-content/uploads/2026/11/{web}.webp',
                      'date': FECHA}}
        # lo que el póster pinta como título, cuando difiere del de la revista
        if tit == 'Forgetting':
            o['titulo_poster'] = 'El olvido'      # «EL OLVIDO · UN CORTOMETRAJE DE J. CAZARES V.»
        if tit == 'Familier / Familiar':
            o['titulo_poster'] = 'Familier'       # «FAMILIER · written and directed by JULIEN HOMÈRE»
        # el afiche oficial de la web, ya preparado por altas.py --preparar (proporción
        # 0,66–0,71) y copiado a assets/: solo las obras sin ficha de TMDB lo necesitan
        _a = f'assets/medellinhorror-2026/{slug(tit)}.jpg'
        if os.path.exists(f'{REPO}/{_a}'):
            o['afiche'] = _a
            o['_afiche_de'] = o['_src']['poster']
        if tit in CORRIGE:
            o['_corrige'] = CORRIGE[tit]
        if tit in NOTA:
            o['_nota'] = NOTA[tit]
        obras.append(o)
    for tit, dire, dia, hora, ev in LARGOS:
        obras.append({'titulo': tit, 'director': dire, 'tipo': 'largo',
                      'franja': f'{dia} {hora} · House of Demons Medellín (Cra. 80 #33-41, Laureles) · ENTRADA GRATIS',
                      '_evidencia': ev, '_src': {'url': f'{REVISTA}#page=4', 'date': FECHA}})
    d = {'_provenance': {'fuente': f'Revista Digital edición 01 ({REVISTA}) + pósteres de {WEB}',
                         'capturado': FECHA,
                         'metodo': 'pdftotext + lámina a ojo + OCR del sistema (pipeline/ocr.py) de los 13 pósteres'},
         'obras': obras}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(obras)} obras → {OUT}')


if __name__ == '__main__':
    main()
