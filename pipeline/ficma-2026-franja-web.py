#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-franja-web.py — la FRANJA ACADÉMICA de FICMA 17, de su web.

QUÉ SUSTITUYE. `ficma-2026-franja.py` leyó el PDF de la franja de AGOSTO: esas
12 actividades quedaron sin fecha cuando el sismo aplazó el festival. La web
volvió a publicar la franja para el 19–25 SEP en /talleresficma17/ y esa página
es hoy la única fuente con día, hora y sede de estas actividades. El PDF y su
sidecar quedan como histórico de la edición de agosto; NO se re-corren.

POR QUÉ UN PARSER Y NO UNA TABLA A MANO. La página ya se leyó dos veces a ojo
—el 11 sep dio seis actividades, el 13 dio cuatro— y `ficma-2026-reprogramado.py`
quedó con cuatro talleres transcritos a mano y una nota pendiente: «volver a
mirar esa página». Hoy trae ONCE. Una lectura a ojo no se puede re-correr ni
diffear; un parser sí, y el día que el festival mueva una hora se ve solo.

LA PÁGINA, POR DENTRO. Elementor: un contenedor hijo por actividad, con una
imagen y un bloque de texto. El texto trae el día en mayúsculas, el título
entre comillas y las etiquetas DIRECTOR/INVITADO/LUGAR/HORARIO/CUPOS.

LA IMAGEN DICE EL TIPO, Y NADA MÁS. Cada tarjeta lleva impreso el rótulo del
festival —TALLERES o CHARLAS—, que es su propia división de la franja y la que
decide la sección. Se lee con OCR (Vision) porque está pintado. El resto de la
tarjeta NO sirve: los archivos se llaman literalmente
`FICMA-17-FRANJA-ACADEMICA-VERSION-ANTERIOR_page-00NN.jpg` y dentro dicen
«AGOSTO». Son las láminas de la edición aplazada, reusadas como ilustración. El
TEXTO manda; la imagen solo aporta el rótulo.

ERRATAS DEL FESTIVAL, DECLARADAS UNA A UNA (abajo, en ERRATAS). Cuatro horarios
publicados dicen cosas imposibles —«10:00 am- 11:00 pm» para una charla de una
hora, «9:00 am 12:am» para una masterclass de la mañana—. No se corrigen con una
heurística silenciosa: cada una queda escrita con lo que dice la página, lo que
se publica y por qué.

Lee   https://laficma.com/talleresficma17/   (cacheada en fuentes/ficma-2026/)
Esc.  festivals/staging/ficma-2026-franja-web.json
"""
import html as _html
import json, os, re, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from ocr import leer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/ficma-2026/franja-web'
URL = 'https://laficma.com/talleresficma17/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')

DIAS = {'SABADO': 19, 'DOMINGO': 20, 'LUNES': 21, 'MARTES': 22,
        'MIERCOLES': 23, 'JUEVES': 24, 'VIERNES': 25}
ETIQUETAS = {'DIRECTOR': 'tallerista', 'DIRECTORA': 'tallerista',
             'INVITADO': 'invitados', 'INVITADA': 'invitados',
             'INVITADOS': 'invitados', 'INVITADAS': 'invitados',
             'LUGAR': 'sede_cruda', 'HORARIO': 'horario', 'HORA': 'horario',
             'CUPOS': 'cupos'}

# El festival escribe la inscripción UNA vez, arriba de todo: «INSCRIPCIÓN A
# TALLERES https://linktr.ee/ficma». No es una suposición nuestra que los
# talleres se inscriban: está dicho, y es el único enlace que la página da hoy.
# (Los formularios sueltos de agosto que guardaba el parser del PDF apuntan a
# unas fechas que ya no existen: no se reusan.)
INSCRIPCION = 'https://linktr.ee/ficma'

# ERRATAS DEL HORARIO PUBLICADO. Clave = el texto tal cual está en la página.
# valor = (hora inicio, duración en minutos o None, por qué).
ERRATAS = {
    '9:00 am 11:30 pm': ('09:00', 150,
        'la página cierra el rango en «pm»: sería un taller de 14 horas y media. '
        'La versión de agosto de este mismo taller duraba 150 min. Se lee 11:30 am.'),
    '10:00 am- 11:00 pm': ('10:00', 60,
        'charla de una hora anunciada «10:00 am - 11:00 pm». Se lee 11:00 am.'),
    '10:00 am – 11:00 pm': ('10:00', 60,
        'charla de una hora anunciada «10:00 am - 11:00 pm». Se lee 11:00 am.'),
    '9:00 am 12:am': ('09:00', 180,
        '«12:am» no existe; una masterclass que empieza a las 9 de la mañana y '
        'termina a las 12 termina al MEDIODÍA. La de agosto duraba 180 min.'),
    '10:00 m 12.00 pm': ('10:00', 120,
        '«10:00 m» por «10:00 am»: el panel va de 10 a 12 del día.'),
}

# Las tarjetas que no traen rótulo pintado, con su motivo. Hoy solo una: el
# taller de periodismo cultural se ilustra con la FOTO del tallerista, no con
# una lámina de la franja.
TIPO_DECLARADO = {
    'Taller de Periodismo Cultural':
        ('taller', 'la tarjeta es la foto de Felipe Moreno, sin rótulo; '
                   'el propio título dice que es un taller'),
}


# LO QUE HAY QUE PREGUNTARLE AL FESTIVAL. Sale de leer la página entera, no solo
# las fichas: el párrafo de entrada anuncia cosas que las fichas no tienen, y las
# fichas dicen cosas que se contradicen entre ellas.
HALLAZGOS = [
    'El taller de DIRECCIÓN DE ACTORES de Franco Lolli sigue anunciado en el '
    'párrafo de entrada («formación práctica en dirección de actores (Franco '
    'Lolli)») y NO tiene ficha en la página: ni día, ni hora, ni sede. En agosto '
    'era «De la realidad a la verdad», dos días en Casa En La Montaña. ¿Se cayó '
    'con el aplazamiento o falta publicarlo?',
    '«Escribir con la cámara: Del guion a la puesta en escena» (mar 22, 9:00) es '
    'la única ficha SIN LUGAR. En agosto era en la Universidad de Caldas. No se '
    'publica hasta que el festival diga dónde.',
    'Cuatro horarios dicen algo imposible: «10:00 am- 11:00 pm» (dos charlas de '
    'una hora), «9:00 am 11:30 pm» (el taller de Isabella Vega) y «9:00 am 12:am» '
    '(la masterclass). Se publican leyendo el cierre en la misma mitad del día.',
    'El taller de animación se anuncia de 5:00 a 8:00 pm y su propio texto dice '
    '«taller intensivo de 4 horas». Se publican las tres horas del horario.',
    'Las tarjetas que ilustran la página son las de la edición APLAZADA: los '
    'archivos se llaman «FRANJA-ACADEMICA-VERSION-ANTERIOR» y dentro dicen '
    'AGOSTO. Quien mire la imagen y no el texto lee la fecha vieja.',
    'La tarjeta de «Coleccionar para recordar» trae una tercera invitada, '
    'Juliana Gallego, que el texto de la página ya no nombra. Se publican las '
    'dos del texto.',
]


def bajar(url, nombre):
    """La página y sus imágenes, cacheadas: el parser se re-corre sin volver a
    pedirle nada al sitio del festival."""
    p = f'{CACHE}/{nombre}'
    if not os.path.exists(p) or os.path.getsize(p) < 500:
        os.makedirs(CACHE, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=60) as r, open(p, 'wb') as f:
            f.write(r.read())
    return p


def texto(frag):
    """El HTML de un bloque → renglones de texto, sin etiquetas."""
    t = re.sub(r'(?is)<br\s*/?>', '\n', frag)
    t = re.sub(r'(?is)</p\s*>', '\n\n', t)
    t = _html.unescape(re.sub(r'(?s)<[^>]+>', '', t))
    t = t.replace('​', '').replace('\xa0', ' ')
    return [re.sub(r'[ \t]+', ' ', x).strip() for x in t.split('\n')]


def bloques(pagina):
    """Los contenedores hijo de Elementor, en orden: (imagen, texto)."""
    s = open(pagina, encoding='utf-8', errors='replace').read()
    imgs = [(m.start(), m.group(1)) for m in re.finditer(r'<img [^>]*?src="([^"]+)"', s)]
    txts = [(m.start(), m.group(1)) for m in re.finditer(
        r'data-widget_type="text-editor\.default">\s*'
        r'<div class="elementor-widget-container">(.*?)</div>', s, re.S)]
    out = []
    for pos, frag in txts:
        previas = [u for p, u in imgs if p < pos]
        out.append((previas[-1] if previas else '', frag))
    return out


def dia_de(linea):
    m = re.match(r'([A-ZÁÉÍÓÚa-záéíóú]+)\s+(\d{1,2})\s*$', linea.strip())
    if not m:
        return ''
    d = DIAS.get(lib.sinacento(m.group(1)).upper())
    return f'2026-09-{d:02d}' if d and int(m.group(2)) == d else ''


def rotulo(img, cache_img):
    """TALLERES o CHARLAS, leído de la lámina. '' si la imagen no lo trae."""
    if not img:
        return ''
    for l in cache_img.get(img, []):
        u = lib.sinacento(l).upper().strip()
        if u.startswith('TALLERES'):
            return 'taller'
        if u.startswith('CHARLAS'):
            return 'charla'
    return ''


def main():
    pagina = bajar(URL, 'talleresficma17.html')
    crudos = bloques(pagina)

    # Las láminas, para el rótulo. Se bajan una vez y el OCR se cachea por hash.
    rutas = {}
    for img, _ in crudos:
        if img and 'LAUREL' not in img and 'PROMOTORES' not in img:
            rutas[img] = bajar(img, img.rsplit('/', 1)[-1])
    leidas = leer(sorted(set(rutas.values())))
    porurl = {u: leidas.get(p, []) for u, p in rutas.items()}

    acts, sin_dia = [], []
    for img, frag in crudos:
        L = [x for x in texto(frag) if x]
        if not L or not dia_de(L[0]):
            if L:
                sin_dia.append(L[0][:60])
            continue
        a = {'dia': dia_de(L[0]), 'imagen': img}
        titulo = L[1].strip(' .')
        a['titulo'] = re.sub(r'^[“”"«»\'“”]+|[“”"«»\'“”]+$', '',
                             titulo).strip()

        campos, resto, seccion = {}, [], 'sinopsis'
        for linea in L[2:]:
            m = re.match(r'^([A-ZÁÉÍÓÚ]+)\s*:?\s*(.*)$', linea)
            k = ETIQUETAS.get(lib.sinacento(m.group(1)).upper()) if m else None
            if k:
                campos[k] = m.group(2).strip()
                continue
            u = lib.sinacento(linea).upper()
            if u.startswith('PERFIL DEL INVITADO') or u.startswith('PERFIL DE'):
                seccion = 'perfil'
                continue
            if re.match(r'^DESCRIPCI[OÓ]N', u):
                # «DESCRIPCIÓN DEL TALLER: texto» — el rótulo se va, el texto se queda
                cola = re.sub(r'^DESCRIPCI[ÓO]N[^:]*:?\s*', '', linea, flags=re.I)
                if cola.strip():
                    resto.append(('sinopsis', cola.strip()))
                continue
            resto.append((seccion, linea))

        a['tipo'] = (rotulo(img, porurl)
                     or TIPO_DECLARADO.get(a['titulo'], ('', ''))[0] or '')
        if a['titulo'] in TIPO_DECLARADO:
            a['_tipo_declarado'] = TIPO_DECLARADO[a['titulo']][1]

        # invitados / tallerista / modera («Modera Diana Castellanos», al final)
        gente = campos.get('invitados', '')
        mod = re.search(r'[.,]?\s*modera[n]?\s*:?\s*(.+)$', gente, re.I)
        if mod:
            a['modera'] = mod.group(1).strip(' .')
            gente = gente[:mod.start()].strip(' .,')
        a['invitados'] = gente
        a['tallerista'] = campos.get('tallerista', '')

        horario = campos.get('horario', '').strip()
        a['_horario_publicado'] = horario
        if horario in ERRATAS:
            a['hora'], a['duracion_min'], a['_errata'] = ERRATAS[horario]
        else:
            # La mitad de los rangos van sin guion («5:00 pm 8:00 pm»): se le
            # pone para que el lector de rangos de lib los vea como uno solo.
            # Es puntuación, no interpretación: las dos horas ya están escritas.
            h = re.sub(r'(\d{1,2}[:.]\d{2}\s*[ap]\.?m\.?)\s+(?=\d{1,2}[:.]\d{2})',
                       r'\1 – ', horario, flags=re.I)
            a['hora'], a['duracion_min'] = lib.rango_horario(h)

        sede = campos.get('sede_cruda', '').strip(' .')
        a['sede_cruda'] = sede
        cupos = campos.get('cupos', '').strip()
        a['_cupos_publicado'] = cupos
        m = re.match(r'^(\d+)', cupos)
        a['cupos'] = int(m.group(1)) if m else None
        # El acceso: lo que dice la casilla CUPOS más lo que el festival declara
        # arriba de la página para TODOS los talleres.
        a.update(lib.acceso_campos(cupos))
        if a['tipo'] == 'taller':
            a['requires_registration'] = True
            a['registration_url'] = INSCRIPCION
        a['acceso'] = cupos or 'Entrada libre'

        # La hoja de vida del invitado NO es la sinopsis de la actividad. Casi
        # siempre viene bajo «PERFIL DEL INVITADO», pero el taller de periodismo
        # cultural no trae descripción: solo la bio, y arranca con el nombre del
        # tallerista. Un párrafo que empieza por su nombre es perfil, no sinopsis
        # —si entra como sinopsis, la tarjeta de la actividad cuenta quién es él
        # y no qué se va a hacer—.
        quien = lib.norm(a['tallerista'] or a['invitados'])
        if quien:
            marcado, en_perfil = [], False
            for s, x in resto:
                if s == 'sinopsis' and lib.norm(x).startswith(quien):
                    en_perfil = True   # y de ahí en adelante: la bio sigue
                marcado.append(('perfil' if en_perfil else s, x))
            resto = marcado
        a['sinopsis'] = ' '.join(x for s, x in resto if s == 'sinopsis').strip()
        a['perfil'] = ' '.join(x for s, x in resto if s == 'perfil').strip()
        acts.append(a)

    acts.sort(key=lambda x: (x['dia'], x['hora'] or '99:99', x['titulo']))
    out = {
        '_provenance': lib.provenance(
            f'{URL} — la franja académica reprogramada (19–25 SEP)',
            que_aporta='las 11 actividades de la franja con día, hora, sede, '
                       'cupo, inscripción y sinopsis; el tipo (taller/charla) '
                       'sale del rótulo impreso en cada lámina, leído con OCR',
            ojo='las láminas son las de AGOSTO (los archivos se llaman '
                'VERSION-ANTERIOR): solo se les cree el rótulo, no la fecha'),
        '_para_el_festival': HALLAZGOS,
        'actividades': acts,
    }
    json.dump(out, open(f'{ST}/ficma-2026-franja-web.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    t = sum(1 for a in acts if a['tipo'] == 'taller')
    print(f'{len(acts)} actividades · {t} talleres · {len(acts) - t} charlas')
    for a in acts:
        print(f"  {a['dia'][-2:]} {a['hora'] or '  ?  '} "
              f"{(str(a['duracion_min']) + 'm').rjust(5) if a['duracion_min'] else '    ?'} "
              f"{a['tipo'][:6].ljust(6)} {a['titulo'][:46].ljust(46)} "
              f"{a['sede_cruda'][:38]}")
    sin = [a['titulo'] for a in acts if not a['sede_cruda']]
    if sin:
        print('SIN SEDE declarada: ' + '; '.join(sin))
    if sin_dia:
        print(f'bloques sin día (no son actividad): {len(sin_dia)}')


if __name__ == '__main__':
    main()
