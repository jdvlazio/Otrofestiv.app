# -*- coding: utf-8 -*-
"""PDF oficial del listado → `cinemancia-2026-listado.json` (109 obras).

FUENTE Y JERARQUÍA (decidida el 9 ago 2026, patrón FICDEH):

    PDF oficial  >  artículo web  >  fichas de /peliculas/

Las tres fuentes se contradicen y por eso el orden importa. El artículo
«Cinemancia 2026 revela la programación oficial de su sexta edición» dice 109
películas y 11 secciones; el encabezado del PDF dice 108 y 13; contando las
entradas del propio PDF salen 109 en 16 encabezados de sección (los dos
«Programa N» y las funciones de apertura/clausura seguramente no cuentan como
«sección» para ellos). Y la página /peliculas/ solo tiene 56 fichas con badge
«Edición 2026» de las 109: está a medio publicar. Manda el PDF, que es el
único que trae la ficha completa de cada obra.

El PDF trae capa de texto —4 páginas, ~8800 operadores— así que NO hay OCR:
se extrae con `pdftotext -layout`. Cada entrada viene en un formato rígido:

    ●  Título (Dir. Nombre, País, Año, NN’)

con estas variantes, todas contempladas:

  · título doble «Original / Traducción» (Auslandsreise / Viaje al extranjero)
  · sin el prefijo «Dir.» (toda la sección de Sergio Navarro)
  · varios países separados por coma (Bolivia, Estados Unidos)
  · año y país invertidos (Valparaíso eterno: «1991, Chile»)
  · la entrada partida en dos líneas cuando no cabe a lo ancho

DOS TRAMPAS que costaron un intento cada una:

  1. La continuación de una entrada partida parece un encabezado de sección.
     Se resuelve por PARÉNTESIS BALANCEADO: la entrada no termina hasta que
     cierra el paréntesis. Es determinista, no heurístico.
  2. «Historia(s) del cine: Argentina» es un encabezado CON paréntesis, así
     que no se puede excluir por ese carácter. Un encabezado es una línea sin
     viñeta que además NO parece entrada (sin «Dir.» y sin «año, duración’»).
     Sin esto, sus 8 obras se van a la sección anterior.

El PDF NO se versiona (pesa 1.8 MB y `fuentes/` está en .gitignore): se baja
al vuelo desde Drive. La URL y la fecha quedan en `_provenance`.
"""
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/cinemancia-2026-listado.json'
DRIVE_ID = '166jpX4CUxRNDKxzy9kIDaEEVZaq3s4PN'
URL_PDF = f'https://drive.google.com/uc?export=download&id={DRIVE_ID}'
URL_NOTA = ('https://cinemanciafestival.com/'
            'cinemancia-2026-revela-la-programacion-oficial-de-su-sexta-edicion')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

# Una línea es ENTRADA si trae «Dir.» o el patrón «año, duración’». Todo lo
# demás que venga suelto y empiece en mayúscula es encabezado de sección.
ENTRADA = re.compile(r'Dir\.|\d{4}\s*,\s*\d+\s*[’\'′]')
SECCION = re.compile(r'^\s{0,10}([A-ZÁÉÍÓÚÑ¿][^●]{3,95})\s*$')
RUIDO = ('A continuación', 'Del 3 al', 'www.', 'Cinemancia Festival Internacional')
FICHA = re.compile(r'^(?P<t>.+?)\s*\((?:Dir\.?\s*)?(?P<resto>[^()]*?)\)')


def texto_del_pdf():
    """→ el PDF de Drive como texto. Requiere pdftotight… perdón, pdftotext."""
    if not subprocess.run(['which', 'pdftotext'], capture_output=True).returncode == 0:
        sys.exit('falta pdftotext (brew install poppler)')
    with tempfile.TemporaryDirectory() as tmp:
        pdf, txt = f'{tmp}/listado.pdf', f'{tmp}/listado.txt'
        subprocess.run(['curl', '-sL', '-A', UA, URL_PDF, '-o', pdf], check=True)
        if open(pdf, 'rb').read(4) != b'%PDF':
            sys.exit('Drive no devolvió un PDF (¿cambió el enlace o pide login?)')
        subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', pdf, txt], check=True)
        return open(txt, encoding='utf-8').read()


def entradas(raw):
    """→ [(sección, texto de la entrada)] respetando el orden del PDF."""
    raw = raw.replace('​', '').replace('­', '')   # zero-width y soft hyphen
    out, seccion, buf = [], None, None
    cerrado = lambda b: b.count('(') > 0 and b.count('(') == b.count(')')

    def push():
        nonlocal buf
        if buf:
            out.append((seccion, ' '.join(buf.split())))
            buf = None

    for l in raw.split('\n'):
        if '●' in l:
            push()
            buf = l.split('●', 1)[1].strip()
            if cerrado(buf):
                push()
        elif buf is not None:                    # continuación: manda el paréntesis
            buf += ' ' + l.strip()
            if cerrado(buf):
                push()
        else:
            m = SECCION.match(l)
            if m and not ENTRADA.search(l) and not any(r in l for r in RUIDO):
                seccion = ' '.join(m.group(1).split())
    push()
    return out


def ficha(seccion, txt):
    txt = re.sub(r'\s*www\..*$', '', txt)        # pie de página pegado a la última
    m = FICHA.match(txt)
    if not m:
        return None
    p = [x.strip() for x in m.group('resto').split(',')]
    dur = next((x for x in p if re.search(r"\d+\s*[’'′]", x)), None)
    anio = next((x for x in p if re.fullmatch(r'(18|19|20)\d\d', x)), None)
    i = p.index(dur) if dur else len(p)
    return {
        'section': seccion,
        'title': m.group('t').strip(' –-—'),
        'director': p[0],
        # el país es lo que queda entre el director y la duración, quitando el año:
        # cubre «Bolivia, Estados Unidos» y también el «1991, Chile» invertido.
        'country': ', '.join(x for x in p[1:i]
                             if x != anio and not re.fullmatch(r'(18|19|20)\d\d', x)),
        'year': int(anio) if anio else None,
        'duration': int(re.search(r'(\d+)', dur).group(1)) if dur else None,
        '_raw': txt,
    }


def main():
    items = entradas(texto_del_pdf())
    obras, malas = [], []
    for sec, txt in items:
        f = ficha(sec, txt)
        (obras if f else malas).append(f or txt)

    d = {'_provenance': lib.provenance(
            f'PDF oficial del listado ({URL_PDF}), enlazado desde {URL_NOTA}',
            jerarquia='PDF oficial > artículo web > fichas de /peliculas/',
            nota=('El artículo dice 109 obras y 11 secciones; el encabezado del PDF '
                  'dice 108 y 13; contando las entradas del PDF salen 109 en 16 '
                  'encabezados. /peliculas/ solo publica 56 de las 109.')),
         'obras': obras}
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    import collections
    print(f'{OUT.split("/")[-1]}  ·  obras {len(obras)} · sin parsear {len(malas)}')
    for s, n in collections.Counter(o['section'] for o in obras).items():
        print(f'   {n:3}  {s}')
    vacios = {c: sum(1 for o in obras if not o.get(c))
              for c in ('director', 'country', 'year', 'duration')}
    print(f'   campos vacíos: {vacios}')
    for t in malas:
        print(f'   ✗ sin parsear: {t[:90]}')
    if malas:
        sys.exit(1)


if __name__ == '__main__':
    main()
