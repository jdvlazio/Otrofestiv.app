# -*- coding: utf-8 -*-
"""Instagram de @narrarelfuturo → lo que la web del festival NO publica.

La web trae la parrilla (día, hora, sede, ficha). Instagram trae lo otro, y no
es poco:

  · SINOPSIS POR OBRA de los dos programas de cortos. La web lista título,
    país, año, duración y género; el pie de Instagram añade una línea de
    contenido por corto, que es lo que un usuario lee antes de decidir.
  · El bloque de la SALA VR con su horario y su sede, que la parrilla no
    modela porque la instalación no es una función.
  · El encuentro con las directoras DESPUÉS de la película inaugural — un Q&A
    que la ficha de la web no menciona.
  · Dos franjas ausentes del programa: #NewMediaLab y las charlas inaugurales.

IG SE LEE EN EL NAVEGADOR para descubrir los posts (regla de la casa: el fetch
de texto da falsos negativos, cicatriz de QAFF). Los pies se extraen del embed
público, que sí es fiable una vez que se sabe el shortcode.

OJO — TRES POSTS SON EL MISMO. `DdT1kVaEVDt`, `DdT1gauEWLB` y `DdT1eE6ET9c`
tienen el pie IDÉNTICO: el festival publicó tres veces el anuncio de apertura.
Contar posts no es contar contenido.
"""
import io, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
SALIDA = f'{ST}/narrarelfuturo-2026-ig.json'
IG = 'https://www.instagram.com/p/'

# shortcode → qué es. Descubiertos en el navegador el 15 sep 2026.
POSTS = {
    'DdSzM3HFpCM': ('programa', 'El Futuro del Futuro', 9),
    'DdS3Uuvlp8Z': ('programa', 'Narrar. Creer. Crecer', 10),
    'DdR-n97md3i': ('dia', 'Día 1 — apertura, Sala VR y película inaugural', 0),
    'DdVB8kHkbes': ('franja', '#NewMediaLab', 0),
    'DdU2qWvkbYO': ('franja', 'Charlas inaugurales', 0),
    # Barrido del 16 sep: el festival dedicó un post a una sola obra de la Sala
    # VR. No trae dato que falte —la ficha de la web ya da su sinopsis y la
    # tarjeta su director— pero CONTRASTA la ventana de la instalación desde una
    # segunda fuente, que es justo lo que no podíamos verificar: el pie repite
    # «15 a 18 · 2:00–6:00 p. m.» y «19 y 20 · 11:00 a. m.–6:00 p. m.».
    'DdS0Afdiz88': ('obra', 'Desert Palms (Sala VR)', 0),
}

# REVISADO Y DESCARTADO, para no volver a mirarlo: el reel `DdUf3y7CkWQ` («Ya
# estamos listos para recibirlos») es promoción de la sede, sin programación; y
# `DdT1kVaEVDt`, `DdT1gauEWLB`, `DdT1eE6ET9c` son el mismo anuncio de apertura
# publicado tres veces —de ahí salió el AFICHE OFICIAL, que es keyArt, no dato
# de parrilla—. El perfil no publica más: el muro corta con el muro de registro
# y no se inicia sesión.
DESCARTADOS = {
    'DdUf3y7CkWQ': 'reel promocional de la Cinemateca, sin programación',
    'DdT1gauEWLB': 'copia del anuncio de apertura (pie idéntico a DdT1kVaEVDt)',
    'DdT1eE6ET9c': 'copia del anuncio de apertura (pie idéntico a DdT1kVaEVDt)',
    'DdT1kVaEVDt': 'anuncio de apertura: de aquí sale el afiche oficial (keyArt)',
}

# La ventana que el festival publica para la instalación, para contrastarla con
# la que el crudo modela (VR_SESIONES). Si el pie cambia, esto grita.
VR_VENTANA = ('2:00 p. m.', '6:00 p. m.', '11:00 a. m.')

# EL EMBED NO SIRVE ESTE POST (devuelve la página de registro), así que su pie
# se transcribe aquí, leído en el navegador el 16 sep 2026. Se declara en vez de
# perderse: es la única fuente que CONTRASTA la ventana de la Sala VR desde
# fuera de la web del festival, y el parser avisa si algún día el embed empieza
# a servirlo (entonces esto sobra y se borra).
PIE_A_MANO = {
    'DdS0Afdiz88': """¿Y si varias historias pudieran suceder al mismo tiempo? \U0001f440\u2728

En #NarrarElFuturo llega Desert Palms, una experiencia VR interactiva escrita y dirigida por Tristan Seniuk (@tristanseniuk), que tuvo su estreno mundial en el 83.º Festival Internacional de Cine de Venecia, como parte de la selección Immersive, fuera de competencia.

La obra es además ganadora de la beca de producción de Biennale College Cinema – Immersive, y representa la culminación de su recorrido por este programa.

Una sala de espera de una clínica, desbordada por asistentes a un festival de música, se convierte en el escenario de una serie de encuentros cada vez más extraños, transformando una noche común en una experiencia donde la realidad comienza a desdibujarse.

\U0001f4cd Cinemateca de Bogotá · Laboratorios 1 y 2

\U0001f4c5 Martes 15 a viernes 18 de septiembre
\U0001f552 2:00 p. m. – 6:00 p. m.

\U0001f4c5 Sábado 19 y domingo 20 de septiembre
\U0001f55a 11:00 a. m. – 6:00 p. m.

\U0001f39f\ufe0f Entrada libre hasta completar aforo.""",
}

# LOS PIES DE LOS DOS PROGRAMAS VIENEN CORTADOS y no hay forma de completarlos:
# el embed trunca a ~2170 caracteres (2173 y 2169 medidos) y la página pública
# corta en el MISMO punto —también en su og:description—, así que sin iniciar
# sesión el final del pie no existe. Por eso el autochequeo dice 5 de 9 y 2 de
# 10 obras: no es un fallo del parser, es la fuente. No se pierde nada, porque
# la sinopsis de las 42 obras sale de su ficha en la web, que es más larga y más
# específica que la línea de Instagram. Lo que SÍ se verificó en el navegador el
# 16 sep: los cortos que el pie alcanza a listar aparecen en el MISMO ORDEN que
# en nuestra parrilla (los 5 primeros de «El Futuro del Futuro», los 6 primeros
# de «Narrar. Creer. Crecer»), el pie declara «9 cortometrajes» y «10», que es
# lo que tenemos, y el acceso coincide: boletería en la Cinemateca, entrada
# libre en Fontanar.
RUTA_IG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ig_carrusel.py')
# líneas de logística que se repiten tras CADA obra y no son contenido
RE_LOGISTICA = re.compile(r'^[\U0001F300-\U0001FAFF☀-➿]?\s*(📍|📅|🕓|🎟️|Cra\.|Calle|#\w)')


def carrusel(sc):
    r = subprocess.run([sys.executable, RUTA_IG, sc], capture_output=True, text=True)
    linea = (r.stdout or '').strip().split('\n')[0]
    if not linea.startswith('{'):
        return None
    return json.loads(linea)


def obras(caption):
    """Los bloques del pie que SON una obra. El pie repite sede, fecha, hora y
    boletería después de cada corto, así que el criterio no puede ser «bloque
    que empieza con emoji»: eso devuelve 26 bloques para 9 obras. Una obra es un
    bloque largo que no es logística."""
    out = []
    for b in re.split(r'\n(?=[\U0001F300-\U0001FAFF☀-➿])', caption):
        b = b.strip()
        if len(b) < 80 or RE_LOGISTICA.match(b):
            continue
        cuerpo = ' '.join(x.strip() for x in b.split('\n') if x.strip())
        cuerpo = re.sub(r'^[\U0001F300-\U0001FAFF☀-➿]+\s*', '', cuerpo)
        m = re.match(r'^(.+?)\s+de\s+(.+?)\s*\(([^)]*)\)\s*(.*)$', cuerpo)
        if m and len(m.group(1)) < 70:
            out.append({'titulo': m.group(1).strip(), 'autoria': m.group(2).strip(),
                        '_credito': m.group(3).strip(), 'sinopsis': m.group(4).strip()})
        else:
            out.append({'_texto': cuerpo})
    return out


def main():
    salida, avisos = [], []
    for sc, (tipo, nombre, esperadas) in POSTS.items():
        d = carrusel(sc)
        if not d and sc in PIE_A_MANO:
            d = {'caption': PIE_A_MANO[sc], 'laminas': []}
        if not d:
            avisos.append(f'{sc}: el embed no lo sirve — leer en el navegador')
            continue
        e = {'shortcode': sc, 'tipo': tipo, 'nombre': nombre,
             '_pie_a_mano': sc in PIE_A_MANO or None,
             '_src': f'{IG}{sc}/', 'laminas': len(d['laminas']),
             'caption': d['caption'],
             'imagenes': [l['url'] for l in d['laminas'] if not l['video']]}
        if tipo == 'programa':
            e['obras'] = obras(d['caption'])
            reales = [o for o in e['obras'] if o.get('titulo')]
            e['_obras_con_ficha'] = len(reales)
            if esperadas and len(reales) != esperadas:
                # Un aviso que siempre suena por la misma causa conocida deja de
                # leerse. Si el pie viene en el tope del embed (~2170), la causa
                # es el truncado —comprobado en el navegador— y se dice así; solo
                # es hallazgo nuevo cuando el pie llegó entero.
                if len(d['caption']) > 2100:
                    avisos.append(f'{sc} «{nombre}»: {len(reales)}/{esperadas} obras — '
                                  f'pie truncado por el embed en {len(d["caption"])} caracteres '
                                  f'(la fuente, no el parser); orden y total verificados en el navegador')
                else:
                    avisos.append(f'{sc} «{nombre}»: {len(reales)} obras leídas y la '
                                  f'parrilla declara {esperadas} — el pie llegó ENTERO, '
                                  f'esto es un hallazgo: mirarlo')
        if tipo == 'obra' and not all(x in d['caption'] for x in VR_VENTANA):
            avisos.append(f'{sc}: el pie ya no repite la ventana de la Sala VR '
                          f'{VR_VENTANA} — contrastar con VR_SESIONES del crudo')
        salida.append(e)

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'instagram.com/narrarelfuturo — posts descubiertos en el navegador, pies vía embed público',
        metodo='un post por programa o franja; el pie repite la logística tras cada obra',
        nota='tres posts del 15 sep tienen el pie IDÉNTICO: el anuncio de apertura se publicó tres veces'),
        '_posts': len(salida), 'posts': salida},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(salida)} posts')
    for e in salida:
        print(f"  {e['shortcode']}  {e['tipo']:<9} {e['nombre'][:38]:40} "
              f"{e.get('_obras_con_ficha', '—'):>3} obras · {len(e['imagenes'])} imágenes")
    for a in avisos:
        print('  ⚠', a)


if __name__ == '__main__':
    main()
