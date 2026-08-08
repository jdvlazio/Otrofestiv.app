# -*- coding: utf-8 -*-
"""Del OCR de FICMA 17 → un registro por función.

La plantilla del PDF es rígida y eso es lo que hace fiable el parseo: la
columna de DATOS vive a la derecha (x≳0.55) y el póster ocupa la izquierda.
Sin ese corte, las críticas impresas en el afiche («UMA AVENTURA SOBRE
RESISTÊNCIA») se cuelan como si fueran campos.

Cada etiqueta —DIRECCIÓN:, PAÍS:, DURACIÓN:, AÑO:, LUGAR:, HORA:— toma como
valor la línea siguiente de SU columna, no la siguiente del documento.
"""
import json, re, os, unicodedata, collections

S = os.path.dirname(os.path.abspath(__file__))
# La columna de datos está acotada por AMBOS lados. A la izquierda para dejar
# fuera el póster —sus críticas impresas se colaban como campos—; a la derecha
# porque el rótulo «FERIA INTERNACIONAL DE CINE DE MANIZALES» va rotado en el
# margen y pdftotext/Vision lo devuelven como líneas sueltas en x≳0.88, que
# aterrizaban como nombre de sede.
COL_X, COL_X_MAX = 0.55, 0.88
DIAS = 'LUNES|MARTES|MIÉRCOLES|MIERCOLES|JUEVES|VIERNES|SÁBADO|SABADO|DOMINGO'
MES = {'ENERO':1,'FEBRERO':2,'MARZO':3,'ABRIL':4,'MAYO':5,'JUNIO':6,'JULIO':7,
       'AGOSTO':8,'SEPTIEMBRE':9,'OCTUBRE':10,'NOVIEMBRE':11,'DICIEMBRE':12}
# Tabla canónica sede→(sede, sala). Explícita y no heurística sobre el guion:
# «Cine al barrio - Samaria» también lo lleva y ahí Samaria es el LUGAR, no una
# sala. Confirmado por el festival (8 ago): Olimpia y Fundadores son salas del
# Teatro los Fundadores, y Fundadores es la sala grande.
SEDE_SALA = {
    'Auditorio Olimpia - Teatro los Fundadores': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Olimpia':                                   ('Teatro los Fundadores', 'Sala Olimpia'),
    'Sala Fundadores':                           ('Teatro los Fundadores', 'Sala Fundadores'),
    'Fundadores':                                ('Teatro los Fundadores', 'Sala Fundadores'),
}
# Ciclos itinerantes del festival: la marca va delante y el lugar real detrás.
CICLOS = ('Cine al barrio', 'Cine bajo la niebla', 'Cine al aire libre', 'Expoferias')
ETIQUETAS = {'DIRECCIÓN':'director','DIRECCION':'director','PAÍS':'pais','PAIS':'pais',
             'DURACIÓN':'duracion','DURACION':'duracion','AÑO':'anio','ANO':'anio',
             'LUGAR':'sede','HORA':'hora'}


def sinacento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.upper())
                   if unicodedata.category(c) != 'Mn')


def hora24(s):
    m = re.search(r'(\d{1,2})[:.](\d{2})\s*([ap])', s.strip(), re.I)
    if not m:
        return ''
    h, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == 'p' and h != 12: h += 12
    if ap == 'a' and h == 12: h = 0
    return f'{h:02d}:{mm}'


def main():
    d = json.load(open(f'{S}/ocr.json', encoding='utf-8'))
    paginas = sorted(d, key=lambda k: int(re.search(r'(\d+)', k).group(1)))

    dia_actual = None
    funcs, portadas, sin_clasificar = [], [], []

    for pag in paginas:
        # El rótulo «FERIA INTERNACIONAL DE CINE DE MANIZALES» va ROTADO en los
        # márgenes. Vision lo devuelve como líneas normales y sus fragmentos
        # («PE MANIZALES», «pENANIZALES» — rotado, el OCR lo destroza) se pegaban
        # al nombre de la sede. Se reconocen por geometría, no por texto: una
        # línea horizontal es más ancha que alta; una rotada, al revés.
        ls = sorted([l for l in d[pag] if l['w'] > l['h']], key=lambda l: l['y'])
        texto = ' '.join(l['t'] for l in ls)
        # El sello «PRESENCIA DEL DIRECTOR / DE LA DIRECTORA» flota sobre la
        # maqueta y su posición varía: unas veces cae en la cabecera y se lee
        # como sección, otras junto a la columna y se lee como país. Se guarda
        # como has_qa (arriba, sobre el texto completo) y se saca del flujo.
        SELLO = re.compile(r'^(PRESENCIA|DEL DIRECTOR|DE LA DIRECTOR)', re.I)
        ls = [l for l in ls if not SELLO.match(sinacento(l['t']).strip())]

        # ── portada de día: «PROGRAMACIÓN / LUNES 10 DE AGOSTO DE 2026» ──
        mp = re.search(rf'({DIAS})\s+(\d{{1,2}})\s+DE\s+([A-ZÁÉÍÓÚ]+)\s+DE\s+(\d{{4}})',
                       sinacento(texto).replace('  ', ' '), re.I)
        if mp and 'PROGRAMACION' in sinacento(texto):
            mes = MES.get(sinacento(mp.group(3)), 0)
            dia_actual = f'{mp.group(4)}-{mes:02d}-{int(mp.group(2)):02d}'
            portadas.append({'pagina': pag, 'dia': dia_actual, 'rotulo': mp.group(0)})
            continue

        # ── página de función ──
        col = [l for l in ls if COL_X <= l['x'] <= COL_X_MAX]
        es_etiqueta = lambda t: ETIQUETAS.get(sinacento((re.match(r'^([A-ZÁÉÍÓÚÑ]+)\s*:', t.strip()) or [None, ''])[1]))
        campos = {}
        for i, l in enumerate(col):
            k = es_etiqueta(l['t'])
            if not k:
                continue
            # El valor puede venir pegado a la etiqueta o debajo, y ocupar VARIAS
            # líneas: «Auditorio Olimpia - / Universidad de Caldas» se partía en
            # dos y la sede quedaba en «Auditorio Olimpia -». Se toma todo hasta
            # la etiqueta siguiente.
            partes = [l['t'].split(':', 1)[1].strip()]
            for sig in col[i + 1:]:
                if es_etiqueta(sig['t']):
                    break
                partes.append(sig['t'].strip())
            v = ' '.join(p for p in partes if p)
            # Cola de basura del rótulo rotado que sobrevivió al filtro de
            # geometría: un token suelto de 1–2 caracteres al final («… Cine
            # fest ~», «… Universidad Nacional- g»). Nunca es parte del nombre.
            v = re.sub(r'[\s\-~]+\S{1,2}$', '', v) if re.search(r'[\s\-~]+\S{1,2}$', v) and len(v) > 12 else v
            campos[k] = re.sub(r'\s*[-~]\s*$', '', v).strip()

        if not campos.get('hora') and not campos.get('sede'):
            sin_clasificar.append({'pagina': pag, 'texto': texto[:160]})
            continue

        # Sección y título: las líneas centradas de arriba, antes de la primera
        # etiqueta. El título va entre comillas, pero puede ocupar DOS líneas
        # («"El hogar fue sepultado en esa tierra / que nunca pudimos
        # encontrar"»): se unen y se extrae el tramo entrecomillado completo.
        # y>0.10 deja fuera la franja superior (logo, badge de día y hora): sin
        # ese corte, «MIÉRCOLES 12» ganaba como sección por ser mayúscula y larga.
        # La cabecera es un bloque centrado: primero la SECCIÓN en mayúsculas,
        # debajo el TÍTULO. Se lee por orden y no por forma —«ARTE» y «MÚSICA»
        # son secciones de 4 y 6 letras, y un umbral de longitud las perdía—.
        # x<0.70 deja fuera el sello «PRESENCIA / DEL DIRECTOR» de la esquina.
        cabeza = [l['t'].strip() for l in ls if 0.10 < l['y'] < 0.26 and l['x'] < 0.70]
        # La sección puede ocupar VARIAS líneas: «EN ALIANZA CON / EL FESTIVAL
        # DE DERECHOS HUMANOS». Se toman todas las mayúsculas seguidas del tope.
        # El nombre va verbatim como lo escribe el festival — no se normaliza.
        k = 0
        while k < len(cabeza) and cabeza[k].isupper():
            k += 1
        seccion = ' '.join(cabeza[:k])
        resto = ' '.join(cabeza[k:])
        # El título va entrecomillado y puede ocupar dos líneas. Cuando el OCR
        # pierde las comillas, se toma el resto de la cabecera tal cual.
        mt = re.search(r'[“"«]\s*(.+?)\s*[”"»]', resto, re.S)
        titulo = re.sub(r'\s+', ' ', mt.group(1) if mt else resto).strip()
        # «PRESENCIA DEL DIRECTOR», sello en la esquina: es un Q&A. Solo lo trae
        # esta fuente; ninguna otra lo publica.
        has_qa = 'PRESENCIA' in sinacento(texto) and 'DIRECTOR' in sinacento(texto)
        # badge superior derecho: «JUEVES 13» y «3:00 PM»
        badge_dia = next((l['t'] for l in ls if l['y'] < 0.08 and re.match(rf'({DIAS})\s+\d', sinacento(l['t']))), '')
        badge_hora = next((l['t'] for l in ls if l['y'] < 0.08 and re.search(r'\d{1,2}:\d{2}\s*[AP]', l['t'], re.I)), '')

        dur = re.search(r'(\d+)', campos.get('duracion', ''))
        anio = re.search(r'(19|20)\d{2}', campos.get('anio', ''))
        funcs.append({
            'pagina': pag,
            'dia': dia_actual,
            'dia_badge': badge_dia,
            'hora': hora24(campos.get('hora', '')) or hora24(badge_hora),
            'sede': campos.get('sede', ''),
            'seccion': seccion,
            'titulo': titulo,
            'director': campos.get('director', ''),
            'pais': campos.get('pais', ''),
            'duracion_min': int(dur.group(1)) if dur else None,
            'anio': int(anio.group(0)) if anio else None,
            'has_qa': has_qa,
        })

    # sede/sala/ciclo, en el mismo paso: si vive fuera, una recorrida del parser
    # lo pisa (pasó en FICDEH y costó una tarde).
    for f in funcs:
        cruda = f['sede']
        if cruda in SEDE_SALA:
            f['sede'], f['sala'], f['ciclo'] = (*SEDE_SALA[cruda], '')
        else:
            c = next((x for x in CICLOS if cruda.lower().startswith(x.lower())), '')
            f['sede'] = cruda.split('-', 1)[1].strip() if (c and '-' in cruda) else cruda
            f['sala'], f['ciclo'] = '', c
        f['_sede_cruda'] = cruda

    json.dump({'_fuente': 'FICMA 17 - PROGRAMACIÓN.pdf · 87 páginas de imagen, OCR con Vision (macOS)',
               'portadas': portadas, 'funciones': funcs, 'sin_clasificar': sin_clasificar},
              open(f'{S}/ficma-crudo.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    faltan = lambda k: sum(1 for f in funcs if not f[k])
    print(f'páginas {len(paginas)} · portadas de día {len(portadas)} · funciones {len(funcs)} · sin clasificar {len(sin_clasificar)}')
    print(f'días detectados: {sorted(p["dia"] for p in portadas)}')
    print(f'obras distintas: {len({f["titulo"] for f in funcs if f["titulo"]})}')
    for k in ('titulo','hora','sede','seccion','director','pais','duracion_min','anio','dia'):
        print(f'  sin {k:13} {faltan(k)}')
    print('\nsedes:', dict(collections.Counter(f['sede'] for f in funcs)))


if __name__ == '__main__':
    main()
