#!/usr/bin/env python3
"""itagui-2026-parrilla.py — la programación del 9° Festival Internacional de
Cine Ciudad de Itagüí, que solo existe como imágenes.

FUENTE: el carrusel de 15 láminas que @institutoitagui publicó el 22 SEP
(instagram.com/p/DdmhX7gFIZa/), una lámina por (día, sede). Su web no publica
programación.

CÓMO LEE. Con cajas, porque la posición ES el dato:

  · columna de la hora   x < 0.22   «6:30» y debajo «p. m.», en dos líneas
  · columna de contenido x >= 0.22  sede, sección, título y campos
  · cabecera             y ~ 0.19   «PROGRAMACIÓN: Miércoles 23 de septiembre»
  · pie                  y > 0.855  patrocinadores — fuera

Una SEDE es una línea de contenido sin hora a su altura y seguida de una
dirección. Todo lo que viene debajo es suyo hasta la siguiente sede.

LOS CAMPOS VIENEN ROTULADOS por el propio festival —«País:», «Director:»,
«Duración:», «Título original:», «Invitado especial:», «Actividad
complementaria:»— que es el caso fácil y hay que aprovecharlo: no se adivina
nada por posición si hay una etiqueta.

VERIFICACIÓN: `--contra <json>` cruza lo parseado contra la transcripción a
ojo, lámina por lámina. Es la regla de Juan tras Jardín: el parser no se cree
hasta comparar cada imagen con lo que sacó.

Esc.  festivals/staging/itagui-2026-parrilla.json
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

POST = 'DdmhX7gFIZa'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
SWIFT = f'{REPO}/pipeline/ocr.swift'
OUT = f'{REPO}/festivals/staging/itagui-2026-parrilla.json'

COL_HORA, PIE = 0.22, 0.855
# EL SELLO «COLOMBIA / CINE BIEN HECHO / CINE NO VISTO» vive arriba a la
# DERECHA (x≈0.84), o sea dentro de la columna de contenido, y se colaba como
# título del primer bloque de cada lámina. Todo lo que está por encima de la
# línea del día es marca del festival, no programación: el corte se toma de la
# propia cabecera, no de un número fijo, porque la cabecera cambia de altura
# entre láminas (y=0.19 en unas, y=0.47 en otras).
MARGEN_CABECERA = 0.02

MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
         'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10,
         'noviembre': 11, 'diciembre': 12}
DIAS = {'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2, 'jueves': 3,
        'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6}

RE_CABECERA = re.compile(
    r'(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\s+(\d{1,2})\s+de\s+'
    r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|'
    r'noviembre|diciembre)', re.I)
RE_HORA = re.compile(r'^(\d{1,2})[:.](\d{2})$')
RE_MERIDIANO = re.compile(r'^([ap])\.?\s*m\.?$', re.I)
RE_HORA_JUNTA = re.compile(r'^(\d{1,2})[:.](\d{2})\s*([ap])\.?\s*m\.?$', re.I)
RE_DIRECCION = re.compile(r'(carrera|calle|cra\.?|cl\.?|#|centro comercial|'
                          r'sexto piso|c\.?c\.?)\s', re.I)
# La sección va en VERSALES y sin rótulo. Se reconoce por la forma, no por lista:
# así una sección nueva del festival entra sola en vez de caerse en silencio.
RE_SECCION = re.compile(r'^[^a-záéíóúñü]{12,}$')
RE_CAMPO = re.compile(r'^([A-ZÁÉÍÓÚÑ][\wáéíóúñ ]{2,28}?):\s*(.*)$')

# Los rótulos del festival → nuestro campo. La palabra la pone el festival; acá
# solo se dice a qué columna va.
CAMPOS = {
    'pais': 'pais', 'país': 'pais',
    'pais invitado': 'pais', 'país invitado': 'pais',
    'titulo original': 'titulo_original', 'título original': 'titulo_original',
    'director': 'director', 'directores': 'director', 'directoras': 'director',
    'duracion': 'duracion_min', 'duración': 'duracion_min',
    'invitado especial': 'invitados', 'invitados especiales': 'invitados',
    'experto en cine invitado': 'invitados', 'director invitado': 'invitados',
    'actividad complementaria': 'complementaria',
    'proyeccion': '_proyeccion', 'proyección': '_proyeccion',
}


def ocr(rutas):
    r = subprocess.run(['swift', SWIFT, '--cajas'] + list(rutas),
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'✗ OCR falló: {(r.stderr or "")[:300]}')
    out = {}
    for linea in r.stdout.splitlines():
        if not linea.strip():
            continue
        d = json.loads(linea)
        out[os.path.basename(d['ruta'])] = [c for c in d['cajas'] if c['y'] < PIE]
    return out


def dia_de(cajas):
    """El día sale de la cabecera, y SOLO si el nombre del día y el número
    concuerdan con el calendario. Un OCR que lee «23» donde dice «28» se calla
    a sí mismo; uno que además tiene que casar con «Miércoles», no."""
    import datetime
    for c in cajas:
        m = RE_CABECERA.search(c['t'])
        if not m:
            continue
        nom, num, mes = m.group(1).lower(), int(m.group(2)), m.group(3).lower()
        f = datetime.date(2026, MESES[mes], num)
        if f.weekday() != DIAS[nom]:
            sys.exit(f'✗ cabecera incoherente: «{c["t"]}» — {nom} no cae en el {num}')
        return f.isoformat()
    return None


# EL ICONO DEL RELOJ SE LEE COMO «L». Está ~0,037 por encima de cada hora y,
# si la ventana se arma alrededor de una línea cualquiera de la columna, empuja
# el «p. m.» fuera de alcance: la hora sale en a. m. y la función se publica de
# madrugada. Así salieron seis fantasmas en la primera corrida —«3:00 p. m.»
# leído como 03:00, «6:30 p. m.» como 06:30— y las cazó el cruce contra la
# lectura a ojo. Por eso el anclaje es LA HORA, no una línea vecina.
SALTO_MERIDIANO = 0.055


def horas_de(cajas):
    """Cada hora de la columna, con su meridiano. Una hora SIN meridiano no se
    adivina: la lámina siempre lo imprime, así que su ausencia es un fallo de
    lectura y se dice en voz alta."""
    col = sorted([c for c in cajas if c['x'] < COL_HORA], key=lambda c: c['y'])
    out, mudas = [], []
    for i, c in enumerate(col):
        t = c['t'].strip()
        m = RE_HORA_JUNTA.match(t)
        if m:
            h, mm, mer = int(m.group(1)), m.group(2), m.group(3).lower()
        else:
            m = RE_HORA.match(t)
            if not m:
                continue
            h, mm, mer = int(m.group(1)), m.group(2), ''
            for d in col[i + 1:]:
                if d['y'] - c['y'] > SALTO_MERIDIANO:
                    break
                mm2 = RE_MERIDIANO.match(d['t'].strip())
                if mm2:
                    mer = mm2.group(1).lower()
                    break
        if not mer:
            mudas.append((c['y'], t))
            continue
        if mer == 'p' and h < 12:
            h += 12
        elif mer == 'a' and h == 12:
            h = 0
        out.append((c['y'], f'{h:02d}:{mm}'))
    out.sort()
    return out, mudas


def bloques(cajas):
    """Cada hora abre un bloque; el contenido se reparte por altura.

    LA HORA ESTÁ CENTRADA EN SU TARJETA, no arriba: el rótulo de sección y el
    título van POR ENCIMA de su propia hora. Una ventana que empiece justo
    encima de la hora se lleva el título de la tarjeta siguiente, y así el
    parser publicaba «El paseo 7» con el país, el director y la duración de
    «El año en que mis padres salieron de vacaciones». Salía coherente y era
    mentira.

    El corte va en el PUNTO MEDIO entre dos horas, que en una maqueta centrada
    cae siempre en el aire entre tarjetas.
    """
    horas, mudas = horas_de(cajas)
    cont = sorted([c for c in cajas if c['x'] >= COL_HORA], key=lambda c: c['y'])
    out = []
    for i, (y, h) in enumerate(horas):
        ini = (horas[i - 1][0] + y) / 2 if i else 0.0
        fin = (y + horas[i + 1][0]) / 2 if i + 1 < len(horas) else 1.0
        out.append({'hora': h, 'y': y,
                    'lineas': [c for c in cont if ini <= c['y'] < fin]})
    return horas, cont, out, mudas


def sedes_de(cont, horas):
    """Una SEDE: bloque de líneas sin hora a su altura, con una dirección debajo.

    EL NOMBRE ES LA PRIMERA LÍNEA DEL BLOQUE, no la que toca la dirección. El
    CAMI lo imprime en tres: «Auditorio Juan Carlos Escobar» / «Centro
    Administrativo Municipal de Itagüí (CAMI)» / «Sexto piso del Edificio
    Judicial (carrera 51 # 51-55)». Quedarse con la que precede a la dirección
    da el edificio y pierde el auditorio, que es el lugar al que va la gente.
    """
    ys = [y for y, _ in horas]
    sedes = []
    for i, c in enumerate(cont):
        if any(abs(c['y'] - y) < 0.035 for y in ys):
            continue
        sig = cont[i + 1] if i + 1 < len(cont) else None
        if not (sig and RE_DIRECCION.search(sig['t']) and not RE_DIRECCION.search(c['t'])):
            continue
        # subir mientras la línea de arriba sea del mismo bloque y no dirección
        j = i
        while j > 0:
            prev = cont[j - 1]
            if c['y'] - prev['y'] > 0.045 or RE_DIRECCION.search(prev['t']):
                break
            if any(abs(prev['y'] - y) < 0.035 for y in ys):
                break
            j -= 1
        if sedes and sedes[-1]['y'] >= cont[j]['y']:
            continue
        dirs = [d['t'] for d in cont[i:i + 4]
                if RE_DIRECCION.search(d['t']) and d['y'] - cont[j]['y'] < 0.09]
        sedes.append({'y': cont[j]['y'], 'nombre': cont[j]['t'].strip(),
                      'detalle': ' '.join(x['t'] for x in cont[j + 1:i + 1]
                                          if not RE_DIRECCION.search(x['t'])),
                      'direccion': ', '.join(dirs)})
    return sedes


# Rótulos que el festival pone DELANTE del nombre de la actividad, con dos
# puntos: «Evento: Sección de cortometrajes», «Conversatorio: Fausto, una vida
# de película». No son campos ni parte del título: la tarjeta ya los pinta.
ROTULOS = ('evento', 'conversatorio')


def ficha(lineas):
    """Sección, título y campos de una tarjeta, leídos POR ESTADOS.

    La maqueta es: [sección en versales] → [título, que puede ir en dos líneas]
    → [campos rotulados, que también pueden envolver]. Una vez empieza un
    campo, toda línea suelta es su continuación, NUNCA más título.

    Sin esa frontera el título se tragaba la segunda línea del campo anterior:
    «Una Madre» salía como «Una Madre Alberto Cardeño (actor)», porque
    «Invitados especiales: Diógenes Cuevas (director)» envuelve en la línea de
    abajo. Cinco funciones así, y las cazó el cruce contra la mirada.
    """
    d, titulo, ultimo = {}, [], None
    for c in sorted(lineas, key=lambda c: c['y']):
        t = c['t'].strip()
        if not t:
            continue
        if RE_SECCION.match(t):
            # UNA SECCIÓN SIEMPRE ABRE TARJETA. Si ya hay título, esta línea es
            # la cabecera de la tarjeta siguiente y el corte por punto medio se
            # quedó corto: «Clave de amor» salía como «Clave de amor OTRAS
            # MIRADAS: MUESTRA INTERNACIONAL».
            if titulo or 'seccion' in d:
                break
            d['seccion'] = t
            continue
        m = RE_CAMPO.match(t)
        etq = m.group(1).strip().lower() if m else None
        if m and etq in CAMPOS:
            campo, valor = CAMPOS[etq], m.group(2).strip()
            if campo == 'duracion_min':
                n = re.search(r'(\d{1,3})', valor)
                if n:
                    d[campo] = int(n.group(1))
                ultimo = None
                continue
            if valor:
                d[campo] = valor
                ultimo = campo
            continue
        if m and etq in ROTULOS and not titulo:
            d['rotulo'] = m.group(1).strip()
            resto_rot = m.group(2).strip()
            if resto_rot:
                titulo.append(resto_rot)
            else:
                # RÓTULO SIN NOMBRE = EL Q&A DE LA FUNCIÓN DE ARRIBA, no una
                # actividad suelta. La lámina del miércoles imprime
                # «Conversatorio:» a las 18:45 y nada detrás, porque a las 18:40
                # hay un corto de 5 minutos —«Leonel», con su equipo de
                # producción invitado— y eso es la conversación de después. El
                # festival debió sumarlo a la función; lo sumamos nosotros.
                # Se marca acá y `funde_qa()` lo pega a su función.
                d['_qa_suelto'] = m.group(1).strip()
            continue
        if ultimo:                      # continuación del campo de arriba
            d[ultimo] = (d[ultimo] + ' ' + t).strip()
            continue
        titulo.append(t)                # todavía en el título
    if titulo:
        d['titulo'] = ' '.join(titulo).strip()
    return d



# Cuánto puede separarse un Q&A de su función para seguir siendo suyo. 20
# minutos cubre el caso real (18:40 → 18:45) con margen, y no alcanza a saltar
# a la función siguiente, que en esta parrilla nunca está a menos de 15.
HUECO_QA = 20


def funde_qa(funciones):
    """Un bloque que solo trae un rótulo —«Conversatorio:» y nada más— es el
    Q&A de la función inmediatamente anterior EN LA MISMA SEDE. Se funde en
    ella y desaparece como función propia.

    Si no hay a quién pegarlo, NO se publica una función vacía: se falla. Una
    tarjeta sin nombre en la app no le sirve a nadie, y callarla es peor.
    """
    def minutos(h):
        a, b = h.split(':')
        return int(a) * 60 + int(b)

    fuera, huerfanos = [], []
    for f in funciones:
        rot = f.get('_qa_suelto')
        if not rot:
            continue
        dueño = None
        for g in funciones:
            if g is f or g.get('_qa_suelto'):
                continue
            if g['dia'] != f['dia'] or g.get('sede') != f.get('sede'):
                continue
            salto = minutos(f['hora']) - minutos(g['hora'])
            if 0 < salto <= HUECO_QA and (dueño is None or
                                          minutos(g['hora']) > minutos(dueño['hora'])):
                dueño = g
        if dueño is None:
            huerfanos.append(f'{f["dia"]} {f["hora"]} [{f.get("sede")}] «{rot}»')
            continue
        dueño['has_qa'] = True
        # «con el equipo/el director» = team; nombres propios invitados = guests
        dueño.setdefault('qa_type', 'team')
        dueño['_qa_desde'] = f['hora']
        # EL Q&A SE LLEVA SUS CAMPOS A LA FUNCIÓN. Con dos horas tan juntas
        # —18:40 y 18:45— el punto medio cae ENTRE las líneas de la primera
        # tarjeta, así que «Invitado especial: Equipo de producción» acabó en el
        # bloque del Q&A. Fundir sin arrastrar los campos borraba ese invitado.
        for k, v in f.items():
            if k in ('dia', 'hora', 'sede', 'direccion', '_lamina', '_qa_suelto',
                     'titulo', 'seccion', 'rotulo'):  # «Leonel» no es un conversatorio
                continue
            dueño.setdefault(k, v)
        fuera.append(f)
    if huerfanos:
        sys.exit('✗ rótulo sin nombre y sin función a la que pertenecer — no se '
                 'publica una tarjeta vacía:\n   ' + '\n   '.join(huerfanos))
    for f in fuera:
        funciones.remove(f)
    return len(fuera)


def main():
    rutas = sorted(f'{LAMINAS}/{n}' for n in os.listdir(LAMINAS) if n.endswith('.jpg'))
    crudo = ocr(rutas)
    funciones, sin_dia, sin_meridiano = [], [], []
    for ruta in rutas:
        k = os.path.basename(ruta)
        cajas = crudo.get(k) or []
        dia = dia_de(cajas)
        if not dia:
            sin_dia.append(k)
            continue
        y_cab = next((c['y'] for c in cajas if RE_CABECERA.search(c['t'])), 0)
        cajas = [c for c in cajas if c['y'] > y_cab + MARGEN_CABECERA]
        horas, cont, bls, mudas = bloques(cajas)
        for y, t in mudas:
            sin_meridiano.append(f'{k} y={y:.3f} «{t}»')
        sedes = sedes_de(cont, horas)
        for b in bls:
            # la sede vigente es la última declarada por encima de esta hora
            arriba = [s for s in sedes if s['y'] < b['y']]
            sede = arriba[-1] if arriba else None
            f = {'dia': dia, 'hora': b['hora'], '_lamina': k,
                 'sede': sede['nombre'] if sede else None,
                 'direccion': sede['direccion'] if sede else None}
            f.update(ficha([c for c in b['lineas'] if not any(
                abs(c['y'] - s['y']) < 0.06 and c['y'] >= s['y'] for s in sedes)]))
            funciones.append(f)

    n_qa = funde_qa(funciones)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f.get('sede') or ''))
    if sin_dia:
        sys.exit(f'✗ láminas sin día en la cabecera: {sin_dia}')
    if sin_meridiano:
        sys.exit('✗ hora sin «a. m.»/«p. m.» al lado — NO se adivina, porque '
                 'adivinarla publica la función doce horas antes:\n   '
                 + '\n   '.join(sin_meridiano))

    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @institutoitagui / @festicineoficial — el carrusel de programación',
            que_aporta='la programación entera: día, hora, sede con dirección, '
                       'sección y ficha. La web del festival no la publica',
            url=f'https://www.instagram.com/p/{POST}/',
            metodo='OCR con cajas sobre las 15 láminas; el día sale de la '
                   'cabecera y se valida contra el calendario; los campos '
                   'vienen rotulados por el festival'),
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')

    print(f'✓ {len(funciones)} funciones · {len({f["dia"] for f in funciones})} días '
          f'· {len({f["sede"] for f in funciones if f["sede"]})} sedes '
          f'· {n_qa} Q&A fundido(s) en su función → {OUT}')

    if '--contra' in sys.argv:
        ojos = json.load(open(sys.argv[sys.argv.index('--contra') + 1], encoding='utf-8'))
        cruzar(funciones, ojos['funciones'])


def cruzar(mias, ojos):
    """Lo parseado contra lo transcrito a ojo, obra por obra.

    POR (día, hora) NO BASTA: 38 funciones caen en 26 franjas, así que dos
    funciones a la misma hora en sedes distintas se tapan entre sí y el cruce
    sale verde sin haber mirado una de las dos. Es la trampa de la cobertura
    global —una hora repetida esconde a la que falta— y acá se cierra bajando
    la llave a (día, hora, SEDE, TÍTULO).
    """
    import unicodedata

    def norm(x):
        x = ''.join(c for c in unicodedata.normalize('NFD', str(x or ''))
                    if unicodedata.category(c) != 'Mn').lower()
        return re.sub(r'[^a-z0-9]+', ' ', x).strip()

    def clave(f):
        return (f['dia'], f['hora'], norm(f.get('sede'))[:22], norm(f.get('titulo'))[:34])

    a = {clave(f): f for f in mias}
    b = {clave(f): f for f in ojos}
    faltan = sorted(set(b) - set(a))
    sobran = sorted(set(a) - set(b))
    print('\n── parser contra la mirada ──')
    print(f'   parser: {len(mias)} funciones ({len(a)} llaves) · '
          f'mirada: {len(ojos)} ({len(b)} llaves)')
    for k in faltan:
        print(f'   ✗ la mirada vio y el parser NO: {k[0]} {k[1]} [{k[2]}] «{k[3]}»')
    for k in sobran:
        print(f'   ✗ el parser sacó y la mirada NO: {k[0]} {k[1]} [{k[2]}] «{k[3]}»')
    if faltan or sobran:
        sys.exit(f'\n✗ {len(faltan) + len(sobran)} diferencia(s) — mirar la lámina')
    # y campo a campo donde las dos tienen dato
    choques = []
    for k in a:
        for campo in ('pais', 'director', 'duracion_min', 'titulo_original'):
            va, vb = a[k].get(campo), b[k].get(campo)
            if va and vb and norm(va) != norm(vb):
                choques.append(f'{k[0]} {k[1]} «{k[3][:26]}» {campo}: parser «{va}» ≠ mirada «{vb}»')
    for c in choques:
        print(f'   ✗ {c}')
    print(f'   ✓ las dos lecturas coinciden en las {len(b)} funciones, '
          f'y en sus campos' if not choques else f'\n✗ {len(choques)} campo(s) en desacuerdo')
    if choques:
        sys.exit(1)


if __name__ == '__main__':
    main()
