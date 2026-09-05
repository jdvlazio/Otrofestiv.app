# -*- coding: utf-8 -*-
"""Lee la GUÍA OFICIAL en PDF de Medellín → sidecar de staging.

Es la fuente de MAYOR autoridad para Medellín: el festival la confirmó como la
versión con los horarios actualizados, por encima del Excel y del sitio web.

Trae cosas que ninguna otra fuente da:
  · la SALA dentro de la sede («Cra. 45 # 53 - 24. Centro - SALA 1»)
  · el título internacional entre paréntesis
  · marcas de «Q&A» y «Estreno nacional» por función
  · país, año y duración en una línea («Reino Unido - Estados Unidos I 2026 I 102’»)

El PDF está maquetado a DOS COLUMNAS, así que pdftotext las entrelaza y el texto
plano sale inservible. Aquí se leen las palabras con coordenadas
(`pdftotext -bbox-layout`), se reparten por columna según su x y se ordenan por
y — que es la única forma de recuperar el orden de lectura real.
"""
import json, os, re, subprocess, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/ficdeh-2026/FICDEH_PROGRAMACIÓN_MEDELLÍN_2026.pdf'
OUT = f'{REPO}/festivals/staging/ficdeh-2026-medellin-pdf.json'
CORTE_X = 500          # frontera entre la columna izquierda y la derecha
# Una dirección colombiana: «Cra. 45 # 53 - 24», «Cl. 51 # 36 - 66», «Carrera 22 - Calle 67»
ES_DIR = re.compile(r'^\s*(Cra?\.|Cl\.|Calle|Carrera|Kra\.|Dg\.|Diagonal|Av\.|Avenida|Transversal|Tv\.)\s*\d', re.I)
DIAS = {'MIÉRCOLES': 2, 'JUEVES': 3, 'VIERNES': 4, 'SÁBADO': 5,
        'DOMINGO': 6, 'LUNES': 0, 'MARTES': 1}


def lineas_de_pagina(p):
    """→ líneas en orden de lectura real (columna izquierda entera, luego derecha)."""
    xml = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(p), '-l', str(p), PDF, '-'],
                         capture_output=True).stdout.decode('utf-8', 'ignore')
    palabras = [(float(a), float(b), t) for a, b, _, _, t in
                re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', xml)]
    out = []
    for col in (0, 1):
        ws = [w for w in palabras if (w[0] < CORTE_X) == (col == 0)]
        filas = collections.defaultdict(list)
        for x, y, t in ws:
            filas[round(y / 6)].append((x, t))       # agrupa por banda horizontal
        for k in sorted(filas):
            out.append(' '.join(t for _, t in sorted(filas[k])).strip())
    # El pie de página («MEDELLÍN», «PROGRAMACIÓN», la url) va rotado en el
    # margen y pdftotext lo pega al final de la línea que le queda más cerca.
    limpias = []
    for l in out:
        for a, b in (('ﬁ', 'fi'), ('ﬂ', 'fl'), ('ﬀ', 'ff'), ('ﬃ', 'ffi')):
            l = l.replace(a, b)
        l = re.sub(r'\s*(MEDELL[ÍI]N|PROGRAMACI[ÓO]N|www\.FICDEH\.com)\s*$', '', l).strip()
        if l and not re.fullmatch(r'(MEDELL[ÍI]N|PROGRAMACI[ÓO]N|www\.FICDEH\.com|D[íi]a|\d{1,2})', l, re.I):
            limpias.append(l)
    return limpias


def main():
    n_pag = int(re.search(r'Pages:\s+(\d+)',
                subprocess.run(['pdfinfo', PDF], capture_output=True).stdout.decode()).group(1))
    lineas = []
    for p in range(1, n_pag + 1):
        lineas += lineas_de_pagina(p)

    # Gramática del PDF, muy regular:
    #   HORA · [DÍA N / AGOSTO] · SEDE · DIRECCIÓN(- SALA N) · y luego 1..n obras:
    #   TÍTULO · [(título internacional)] · Dir. … · Categoría · PAÍS I AÑO I DUR’ · [Estreno | Q&A]
    funcs, dia, hora, sede, direccion, sala = [], None, None, None, '', ''
    pend = []            # líneas de la obra en curso, hasta su línea de país/año/duración
    unidas, k = [], 0
    while k < len(lineas):
        l = lineas[k]
        if l.endswith('-') and k + 1 < len(lineas) and re.search(r'\sI\s\d{4}\sI\s', lineas[k + 1]):
            l = l.rstrip('- ') + ' - ' + lineas[k + 1]; k += 1
        unidas.append(l); k += 1
    lineas = unidas

    for l in lineas:
        md = re.match(r'^(MIÉRCOLES|JUEVES|VIERNES|SÁBADO|DOMINGO|LUNES|MARTES)\s+(\d{1,2})\s*/\s*AGOSTO', l, re.I)
        if md:
            dia = f'2026-08-{int(md.group(2)):02d}'
            pend = []
            continue
        mh = re.match(r'^(\d{1,2}):(\d{2})\s*([AP])\.?\s*M\.?$', l.strip(), re.I)
        if mh:
            hh, mm, ap = int(mh.group(1)), mh.group(2), mh.group(3).upper()
            if ap == 'P' and hh != 12: hh += 12
            if ap == 'A' and hh == 12: hh = 0
            hora, sede, direccion, sala, pend = f'{hh:02d}:{mm}', None, '', '', []
            continue
        if re.fullmatch(r'Proyecci[óo]n infantil', l.strip(), re.I):
            continue                       # etiqueta de sección, no una sede
        if hora and sede is None:
            sede = l.strip(); continue
        if sede and not direccion:
            direccion = l.strip()
            ms = re.search(r'-\s*(SALA\s*\d+)\s*$', direccion, re.I)
            if ms:
                sala = ms.group(1).upper()
                direccion = direccion[:ms.start()].strip(' -')
            continue
        # Una MISMA hora puede tener DOS sedes. Se reconoce porque la línea
        # siguiente es una dirección; sin esto, la segunda sede se cuela como
        # título de la obra y arrastra su dirección detrás.
        if ES_DIR.match(l) and pend:
            sede, direccion, sala = pend[-1], l.strip(), ''
            ms = re.search(r'-\s*(SALA\s*\d+)\s*$', direccion, re.I)
            if ms:
                sala = ms.group(1).upper()
                direccion = direccion[:ms.start()].strip(' -')
            pend = []
            continue
        mp = re.match(r'^(.+?)\s+I\s+(\d{4})\s+I\s+(\d+)\s*[’\']', l)
        if mp:
            # El título puede ocupar VARIAS líneas («Apotnojushi la Casa» / «del
            # Viento»): se toman todas las de antes del paréntesis o del «Dir.».
            corte = next((k for k, x in enumerate(pend)
                          if re.match(r'^(Dir\.|\(|Largometraje|Cortometraje|Película|Charlas|Retrospectiva|Estreno)', x)),
                         len(pend))
            titulo = ' '.join(pend[:corte]).strip()
            inter = next((x[1:-1] for x in pend if x.startswith('(') and x.endswith(')')), '')
            direc = next((x[4:].strip() for x in pend if x.startswith('Dir.')), '')
            categ = next((x for x in pend if re.match(r'^(Largometraje|Cortometraje|Película|Retrospectiva)', x)), '')
            funcs.append({'dia': dia, 'hora': hora, 'sede': sede, 'direccion': direccion,
                          'sala': sala, 'titulo': titulo, 'titulo_internacional': inter,
                          'director': direc, 'categoria': categ, 'pais': mp.group(1).strip(),
                          'anio': mp.group(2), 'duracion': f'{mp.group(3)} min',
                          'has_qa': False, 'estreno': False})
            pend = []
            continue
        if re.search(r'Q&amp;A|Q&A', l) and funcs:
            funcs[-1]['has_qa'] = True
        if re.search(r'Estreno', l) and funcs:
            funcs[-1]['estreno'] = True
        if l.strip() and not re.match(r'^\d+$|^Día$', l.strip()):
            pend.append(l.strip())

    # Seis fichas cuyo título el parser no recupera (maquetas puntuales: el
    # título va en una caja aparte de su bloque). Se completan a mano leyendo el
    # PDF, en orden de aparición dentro de su bloque de hora+sede. Preferible una
    # tabla explícita y auditable a seguir generalizando el parser con un único
    # documento de muestra.
    PARCHE = {
        ('2026-08-14', '16:30', 'La Pascasia'):                        ['1982'],
        ('2026-08-15', '10:00', 'Centro Cultural Banco de la República'):
            ['El Paraíso de Ainara', 'In Four Stops'],
        ('2026-08-16', '14:30', 'Colombo Americano de Medellín'):
            ['Más allá', 'Akababuru: Expresión de asombro'],
        ('2026-08-18', '18:00', 'Comfama Cineclub Bello'):             ['Desierto verde'],
        # «Rueda Libre…: Cra. 22 # 18 - 77» — el nombre de la sede lleva dos puntos
        # y la dirección detrás, así que el título queda al final de esa línea.
        ('2026-08-18', '18:30', 'Rueda Libre Festival de Cine de la Ceja'): ['La Raya'],
    }
    # Sedes cuyo nombre y dirección ocupan dos líneas: el parser toma la primera
    # como dirección y la segunda queda pegada al título.
    for f in funcs:
        m = re.match(r'^(?:.*?(?:Cra?\.|Cl\.|Calle|Carrera|Dg\.)\s*[\d#\-\s\.]+|.*?SALA\s*\d+)\s+(.+)$', f['titulo'])
        if m and len(f['titulo']) > 20 and m.group(1).strip():
            f['titulo'] = m.group(1).strip()
            f['_titulo_depurado'] = 'la dirección de la sede venía pegada al título'

    for k, titulos in PARCHE.items():
        huecos = [f for f in funcs
                  if (f['dia'], f['hora'], f['sede']) == k and not f['titulo']]
        for f, t in zip(huecos, titulos):
            f['titulo'] = t
            f['_titulo_manual'] = 'leído del PDF; el parser no lo recupera'

    json.dump({'_provenance': {
        'fuente': 'FICDEH_PROGRAMACIÓN_MEDELLÍN_2026.pdf — guía oficial impresa',
        'recibido': '2026-08-06',
        'autoridad': 'LA MÁS ALTA para Medellín: el festival la confirmó como la versión '
                     'con los horarios actualizados, por encima del Excel y del sitio web.',
        'ojo': 'Maquetado a dos columnas: el texto plano de pdftotext entrelaza ambas. '
               'Se reconstruye por coordenadas.',
    }, 'funciones': funcs, '_lineas': lineas},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{n_pag} páginas · {len(lineas)} líneas · {len(funcs)} funciones')
    print(f'con día: {sum(1 for f in funcs if f["dia"])} · con sala: {sum(1 for f in funcs if f["sala"])} · con Q&A: {sum(1 for f in funcs if f["has_qa"])} · estrenos: {sum(1 for f in funcs if f["estreno"])}')
    print(f'días: {sorted({f["dia"] for f in funcs if f["dia"]})}')


if __name__ == '__main__':
    main()
