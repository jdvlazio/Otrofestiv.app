#!/usr/bin/env python3
"""bogoshorts-2026-catalogo.py — el CATÁLOGO oficial del 24.º BOGOSHORTS → los
cortos de cada programa.

LA FUENTE: 24BSFF_catalogo2026.pdf (198 págs., InDesign, CON TEXTO, del 13 nov
2026), en fuentes/bogoshorts-2026/catalogo2026.pdf. Cada página de programa
lleva su rótulo vertical «Competencia Nacional Ficción - CN-FIC1»: el código
manda (es el mismo de la grilla). Cada corto trae:

    Título [/ traducción / traducción]
    País(es) / año / mm’ss’’ / Color / idioma
    sinopsis ES        sinopsis EN
    dirección / direction X producción / production …

Se lee con `pdftotext -bbox-layout` (bloques con coordenadas), NO en orden de
lectura: las páginas de 4–6 cortos mezclan las columnas en el texto plano. Por
cada línea de ficha técnica (país / año / duración) se busca, EN SU COLUMNA (la
misma x), el título justo encima, la sinopsis justo debajo y la primera línea
«dirección / direction» antes de la siguiente ficha. Cortofilia trae la
dirección en la propia ficha («Dir. X / País / …»).

Lo que NO se inventa: si el catálogo no trae un campo, queda vacío. Los títulos
en escritura no latina (CVR, F3) no salen como texto del PDF: queda la
traducción y la obra lleva `_nota`.

Duración: mm’ss’’ → minutos REDONDEADOS (PROTOCOLO: «las duraciones declaradas
cuadraban con la suma REDONDEADA»).

Contraste: los 10 programas de bogoshorts-2026-programas.json (boletines e IG)
tienen que listar los mismos títulos que el catálogo; las diferencias se imprimen.

Escribe festivals/staging/bogoshorts-2026-cortos.json  (lo lee el crudo)
"""
import html, io, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

PDF = f'{REPO}/fuentes/bogoshorts-2026/catalogo2026.pdf'
URL = 'https://info.bogoshorts.com/sccs/prensa/2026/docs_2026/24BSFF_catalogo2026.pdf'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-cortos.json'
PROG = f'{REPO}/festivals/staging/bogoshorts-2026-programas.json'
PAGINAS = range(56, 199)          # antes: editoriales, jurados, premios

# «Colombia / 2026 / 15’59’’ / Color / Wayuunaiki»; Cortofilia: «Dir. X / Colombia / 2018 / 26’00’’ …»;
# erratas del propio catálogo: «13’06’», «7”59’», y el largo «117’» (sin segundos)
META = re.compile(r"^(?:Dir\. (?P<dir>[^/]+?) / )?(?P<pais>[^/]+?) / (?P<anio>(?:19|20)\d\d) / "
                  r"(?P<m>\d+)\s*[’'′”]+\s*(?:(?P<s>\d+)\s*[’'′”″\"]*)?\s*(?:/ (?P<resto>.*))?$")
# el rótulo de la página: «… - CN-FIC1»
ROTULO = re.compile(r' - ([A-Z0-9]+(?:-[A-Z0-9]+)+|CVR|HUMOR)$')
# el catálogo abrevia dos códigos que la grilla escribe completos
CODIGO_GRILLA = {'HOM-CES': 'HOM-CESAR'}
NO_SINOPSIS = re.compile(r'^(dirección|Premier|Califica|Contacto|Proyecciones)')
ROL = re.compile(r'\s[a-záéíóúñ]+(?: [a-záéíóúñ]+)* / [a-z]')


def bloques(p):
    o = subprocess.run(['pdftotext', '-bbox-layout', '-f', str(p), '-l', str(p), PDF, '-'],
                       capture_output=True, text=True).stdout
    bs = []
    for b in re.finditer(r'<block xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</block>',
                         o, re.S):
        ls = [' '.join(html.unescape(w) for w in re.findall(r'>([^<]*)</word>', ln))
              for ln in re.findall(r'<line.*?</line>', b[5], re.S)]
        bs.append((float(b[1]), float(b[2]), float(b[3]), float(b[4]), [x for x in ls if x.strip()]))
    return [b for b in bs if b[4]]


def unir(lineas):
    """Une las líneas de un párrafo; «des-» + «cubre» → «descubre»."""
    t = ''
    for ln in lineas:
        ln = ln.strip()
        if t.endswith('-') and ln[:1].islower() and not t.endswith(' -'):
            t = t[:-1] + ln
        else:
            t = (t + ' ' + ln).strip()
    return re.sub(r'\s+', ' ', t)


def director(linea):
    d = linea.split('dirección / direction', 1)[1].strip()
    m = ROL.search(' ' + d)
    return (d[:m.start() - 1] if m else d).strip(' ,')


def huella(t):
    t = unicodedata.normalize('NFKD', t.lower().replace('’', "'"))
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in t if not unicodedata.combining(c)))


EN = re.compile(r"\b(the|and|of|his|her|with|is|a|to|that|their|from|who|an|in|every|other)\b", re.I)
ES = re.compile(r"\b(el|la|los|las|de|que|y|en|un|una|su|con|por|se|del|al)\b", re.I)
# dos columnas impresas en las mismas líneas: pdftotext las mezcla (leída a ojo, catálogo pág. 88)
MEZCLADAS = {'Red Elephant': (
    '¿Qué aspecto tiene lo queer cuando has pasado la vida borrando sus huellas para sobrevivir? En Red Elephant, el director '
    'comparte su recorrido por la violencia silenciosa de la burocracia, donde lo queer debe traducirse en pruebas y el trauma '
    'en testimonio. En el sistema de asilo belga, a solicitantes LGBTQ+, muchos provenientes de lugares donde callar era '
    'sobrevivir, se les exige narrar lo indecible y contar sus heridas más íntimas a desconocidos.')}


MEZCLADAS_EN = {'Red Elephant': (
    'What does queerness look like when you’ve spent a lifetime erasing every trace of it to stay alive? In Red Elephant, the '
    'director shares his journey through the quiet violence of bureaucracy, where queerness must be translated into evidence, '
    'and trauma into testimony. In Belgium’s asylum system, LGBTQ+ seekers, many from worlds where silence meant survival, are '
    'asked to speak the unspeakable, recounting their most intimate wounds to strangers they’ve only just met.')}

# «Título / traducción / traducción»: cuál de los títulos alternos del catálogo es el INGLÉS. Es el primero, salvo
# aquí: el original ya está en inglés o el alterno es español/otra lengua → sin title_en (leídos uno por uno, 23 nov 2026)
SIN_INGLES = {'They’re Here', 'A Body that Hurts', 'O sigilo', 'Nothing Here is Lost', 'To the North', 'Virgin Fandango',
              'If Only', 'Night Feeds', 'I Wanna Go Home', 'The Getaway', 'The Birthday Gift', 'The Tide Inside', 'See You in the Morning',
              'Fiction', 'Transastralisme', 'Grounded', 'Cat Me If You Can', 'Au-dessus du vacarme'}
INGLES = {'L’uomo meccanico': 'The Mechanical Man',
          # el PDF imprime el artista en el título inglés también; el título es lo de antes
          'La ciudad de las flores (Maleza y Los Floripondios)': 'City of Flowers'}


def solo_es(t):
    """La sinopsis sin la versión en inglés que le sigue (Cortofilia las apila)."""
    out = []
    for fr in re.split(r'(?<=[.!?…])\s+', t):
        if out and len(EN.findall(fr)) > len(ES.findall(fr)) + 1:
            break
        out.append(fr)
    return ' '.join(out)


def es_ingles(t):
    return len(EN.findall(t)) > len(ES.findall(t)) and len(t) > 25


def sinopsis_en(bs, caja, sin, lim):
    """La versión inglesa que el catálogo imprime de la MISMA sinopsis: al lado (misma altura),
    debajo en la misma columna (páginas de 4–6 cortos) o apilada tras la española (Cortofilia).
    Tiene que leerse como inglés; si no, vacío."""
    cola = unir(sin)[len(solo_es(unir(sin))):].strip()
    if es_ingles(cola):
        return cola
    x, y, yf = caja[0], caja[1], caja[3]
    lado = [c for c in bs if 60 < c[0] - x < 330 and abs(c[1] - y) < 12]
    abajo = [c for c in bs if abs(c[0] - x) < 4 and yf - 1 <= c[1] < min(lim, yf + 40)
             and not NO_SINOPSIS.match(c[4][0]) and not any(META.match(z) for z in c[4])]
    for c in sorted(abajo, key=lambda c: c[1]) + sorted(lado, key=lambda c: c[0]):
        t = unir(c[4])
        if es_ingles(t) and not any(META.match(z) for z in c[4]) and not re.search(r'\w / (music|cast|sound|editing|screenplay)\b', t):
            return t
    return ''


def leer():
    progs, orden = {}, []
    for p in PAGINAS:
        bs = bloques(p)
        cod = next((ROTULO.search(ln)[1] for b in bs if b[2] - b[0] < 25 and b[3] - b[1] > 60 for ln in b[4] if ROTULO.search(ln)), None)
        for b in bs:
            for i, ln in enumerate(b[4]):
                m = META.match(ln)
                if not m:
                    continue
                if not cod:
                    sys.exit(f'✗ pág. {p}: una ficha sin rótulo de programa: {ln}')
                x = b[0]

                def col(c):
                    return abs(c[0] - x) < 4
                # título: las líneas previas del mismo bloque, o el bloque justo encima.
                # Cortofilia apila «Director de X / Estreno: …», «Cortometraje: TÍTULO»
                # y «Dir. X / País …»; el largo, «Dir. A, B y C.» sobre la ficha.
                previas = b[4][:i]
                dir_previa = next((re.sub(r'^Dir\.\s*', '', z).strip(' .') for z in previas if z.startswith('Dir. ')), '')
                corto = next((z.split(':', 1)[1].strip() for z in previas if z.startswith('Cortometraje:')), '')
                previas = [z for z in previas if not re.match(r'(Dir\. |Director|Directora|Codirector|Estreno:)', z)]
                if corto:
                    tit = [corto]
                elif previas:
                    tit = previas
                else:
                    enc = [c for c in bs if c[3] <= b[1] + 1 and b[1] - c[3] < 14 and x - 4 < c[0] < x + 150
                           and not ROTULO.search(' '.join(c[4]))]
                    tit = max(enc, key=lambda c: c[3])[4] if enc else []
                # una línea que es solo puntuación («.»): un glifo que el PDF no trae como texto
                glifo = bool(tit) and bool(re.fullmatch(r'\W+', tit[0].strip()))
                if glifo:
                    tit = tit[1:]
                # lo que sigue a la ficha en su bloque: primero la continuación del idioma
                # («Sin diálogos, texto en pantalla | en catalán»), después la sinopsis
                tras = b[4][i + 1:]
                cont = ''
                while tras and tras[0][:1].islower() and len(tras[0]) < 40:
                    cont, tras = (cont + ' ' + tras[0]).strip(), tras[1:]
                caja = b
                if tras:
                    sin = tras
                else:
                    deb = [c for c in bs if col(c) and c[1] >= b[3] - 1 and c[1] - b[3] < 30
                           and not NO_SINOPSIS.match(c[4][0])]
                    sin = min(deb, key=lambda c: c[1])[4] if deb else []
                    caja = min(deb, key=lambda c: c[1]) if deb else b
                # dirección: la primera «dirección / direction» de la columna antes de la próxima ficha
                prox = [c[1] for c in bs if col(c) and c[1] > b[3] + 1 and any(META.match(z) for z in c[4])]
                lim = min(prox) if prox else 1e9
                dr = [c for c in bs if col(c) and b[3] - 1 <= c[1] < lim and c[4][0].startswith('dirección / direction')]
                d = m['dir'] or dir_previa or (director(unir(min(dr, key=lambda c: c[1])[4])) if dr else '')
                partes = [s.strip() for s in re.split(r'\s+/\s*|\s*/\s+', unir(tit))]
                obra = {'titulo': partes[0], 'director': d.strip(), 'pais': m['pais'].strip(),
                        'anio': int(m['anio'])}
                if partes[1:]:
                    obra['titulos_alt'] = partes[1:]
                if not partes[0]:          # escritura no latina: el PDF no la trae como texto
                    obra['titulo'] = partes[1] if len(partes) > 1 else ''
                    obra['titulos_alt'] = partes[2:]
                    obra['_nota'] = 'título original en escritura no latina, ilegible como texto en el PDF; va la traducción'
                    if not obra['titulos_alt']:
                        del obra['titulos_alt']
                if glifo:
                    obra['_nota'] = 'el título empieza con un carácter que el PDF no trae como texto (sale «.»)'
                seg = int(m['m']) * 60 + int(m['s'] or 0)
                obra['duracion_min'] = (seg + 30) // 60
                obra['_duracion'] = ln.split(' / ')[3 if m['dir'] else 2].strip()
                if m['resto']:
                    resto = [s.strip() for s in m['resto'].split(' / ')]
                    if cont:
                        resto[-1] = resto[-1] + ' ' + cont
                    if resto[-1] and not re.match(r'(Color|B&N|B&W)', resto[-1]):
                        obra['language'] = resto[-1]
                if sin:
                    obra['sinopsis'] = MEZCLADAS.get(obra['titulo']) or solo_es(unir(sin))
                en = MEZCLADAS_EN[obra['titulo']] if obra['titulo'] in MEZCLADAS_EN else sinopsis_en(bs, caja, sin, lim) if sin else ''
                if en:
                    obra['synopsis_en'] = en
                # el catálogo no cierra algunas con punto ([ficha-obra] sinopsis:cierre); el texto está completo
                for k in ('sinopsis', 'synopsis_en'):
                    if obra.get(k) and re.search(r'\w$', obra[k]):
                        obra[k] += '.'
                obra['_src'] = {'url': URL, 'pagina': p, 'date': '2026-11-13'}
                t = INGLES.get(obra['titulo']) or (obra.get('titulos_alt') or [''])[0]
                if t and obra['titulo'] not in SIN_INGLES and huella(t) != huella(obra['titulo']):
                    obra['title_en'] = t
                c = CODIGO_GRILLA.get(cod, cod)
                if c not in progs:
                    orden.append(c)
                progs.setdefault(c, []).append(obra)
    return progs


def main():
    progs = leer()
    faltan = [(c, o['titulo'], k) for c, os_ in progs.items() for o in os_
              for k in ('titulo', 'director', 'sinopsis') if not o.get(k)]
    for c, t, k in faltan:
        print(f'  · {c} «{t}» sin {k} en el catálogo')
    # contraste con los boletines / IG (no aporta: señala)
    if os.path.exists(PROG):
        prev = json.load(open(PROG, encoding='utf-8'))['programas']
        for c, os_ in prev.items():
            a = {huella(o['titulo']) for o in os_}
            b = {huella(o['titulo']) for o in progs.get(c, [])} | \
                {huella(t) for o in progs.get(c, []) for t in o.get('titulos_alt', [])}
            solo = [o['titulo'] for o in os_ if huella(o['titulo']) not in b]
            if solo:
                print(f'  ⚠ {c}: boletín/IG lista y el catálogo no (por título): {solo}')
            if len(os_) != len(progs.get(c, [])):
                print(f'  ⚠ {c}: boletín/IG {len(os_)} obras, catálogo {len(progs.get(c, []))}')
    json.dump({'_provenance': provenance(URL, metodo='pdftotext -bbox-layout: por ficha técnica, título encima, '
                                         'sinopsis debajo y «dirección / direction» en la misma columna'),
               'programas': progs}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(progs)} programas, {sum(map(len, progs.values()))} cortos → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
