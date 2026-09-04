# -*- coding: utf-8 -*-
"""Las fichas de obra del PDF oficial del programa QAFF 2026.

El PDF tiene CAPA DE TEXTO —no es OCR—, así que estos datos no pueden tener
errores de lectura: o el festival lo escribió así, o no está. El ancla es la
línea «De <Director>» inmediatamente bajo el título; todo lo demás se lee por
etiqueta, nunca por posición (leer por posición fue lo que en la cosecha por OCR
pegó la sinopsis de una obra a otra en las páginas de dos fichas)."""
import re, sys, os, datetime, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'festivals', 'staging')
_ruta = lambda nom: os.path.join(STAGING, nom)
from limpia import paginas, limpia

ETIQ = re.compile(r'^(Duraci[óo]n|Tipo de Proyecto|Idioma|Pa[íi]s|A[ñn]o|Distribuci[óo]n|'
                  r'Fecha de Finalizaci[óo]n|Directora?e?s?|Guionistas?|Guionista|'
                  r'Productor[ae]?s?|Director de Fotograf[íi]a|Editor[ae]?s?|'
                  r'Director/Guionista)\s*:\s*(.*)$', re.I)
DE   = re.compile(r'^De\s+(.{2,90})$')
PAIS = re.compile(r'^(.{2,60}?)\s*[–-]\s*((?:19|20)\d{2})\s*$')
BIO  = re.compile(r'^Biograf[íi]a\s+(?:de|del)\b', re.I)

def _titulo(ls, i):
    """El título va SOBRE la línea «De <Director>», y a veces ocupa dos o tres
    renglones: «RELATOS» / «DE LA GUAJIRITA». Tomar solo el último renglón deja
    títulos mutilados que luego no cruzan con la parrilla —y un título que no
    cruza se convierte en una obra huérfana, no en un error visible.
    Se sube mientras la línea siga siendo un título: versales, sin etiqueta y
    corta. La biografía de la ficha anterior es prosa en minúsculas, así que
    no se cuela."""
    partes = []
    for j in range(i - 1, max(i - 4, -1), -1):
        l = ls[j].strip()
        letras = [c for c in l if c.isalpha()]
        if (not l or ':' in l or len(l) > 60 or not letras
                or sum(c.isupper() for c in letras) / len(letras) < 0.8):
            break
        partes.insert(0, l)
    return ' '.join(partes).strip()

def _dur(s):
    """«18'20''» → 18 · «120'» → 120 · «60’» → 60. Se trunca a minutos enteros:
    la app no muestra segundos y redondear hacia arriba inventaría duración."""
    m = re.match(r"\s*(\d{1,3})\s*['’]?\s*(\d{1,2})?", s or '')
    return int(m.group(1)) if m else None

SELLO = re.compile(r'^\d{1,2}\s*SEPT\.?$|^SEPT\.?$|^20\d\d$')


def extrae():
    """Una ficha, en la exportación del 4 sep 2026, sale así:

        18 / SEPT. / 2026          ← el sello, ENCIMA
        Director: …  Duración: …   ← las etiquetas, ENCIMA
        ORANGO                     ← el título
        De Samuel Kay Forrest      ← el ancla
        Guinea-Bissau – 2024
        <la sinopsis>
        Biografía del Director - …
        <la biografía>
        SINOPSIS                   ← el rótulo, AL FINAL y suelto

    La versión anterior cortaba la sinopsis a partir del rótulo «SINOPSIS», y en
    la exportación de agosto el rótulo iba ANTES del texto. Al reexportar el
    festival, el rótulo pasó al final y el corte se llevó el bloque de la ficha
    SIGUIENTE: las 52 sinopsis quedaron cambiadas de obra, con los créditos de la
    vecina. Ahora no se ancla en el rótulo —que es decoración— sino en lo que
    delimita de verdad: la sinopsis es la prosa entre «País – Año» y la
    «Biografía», y las etiquetas y el sello se buscan por encima del título."""
    P = paginas()
    out = []
    for n in sorted(P, key=int):
        ls = limpia(P[n])
        anclas = [i for i, l in enumerate(ls) if DE.match(l) and i > 0]
        bios = [i for i, l in enumerate(ls) if BIO.match(l)]
        sello_pag = next((int(re.match(r'^(\d{1,2})', x).group(1)) for x in ls
                          if re.match(r'^\d{1,2}\s*SEPT\.?$', x)), None)
        for k, i in enumerate(anclas):
            f = {'titulo': _titulo(ls, i), 'director': DE.match(ls[i]).group(1).strip(),
                 '_pagina': int(n)}
            # ── ARRIBA del título: el sello y las etiquetas de ESTA ficha ──
            ini = 0 if k == 0 else next((x + 1 for x in bios if x < i and
                                         (k == 0 or x > anclas[k - 1])), 0)
            arriba = ls[ini:i]
            # ── ABAJO del ancla: país, sinopsis y donde empieza la biografía ──
            fin_bio = next((x for x in bios if x > i), len(ls))
            abajo = ls[i + 1:fin_bio]

            for l in arriba:
                m = ETIQ.match(l)
                if not m:
                    continue
                et, v = m.group(1).lower(), m.group(2).strip()
                if et.startswith('duraci') and v:  f['duracion_min'] = _dur(v)
                elif et.startswith('tipo'):        f['tipo'] = v
                elif et.startswith('idioma'):      f['idioma'] = v
                elif et.startswith('pa'):          f.setdefault('pais', v)
                elif et.startswith('a') and v.isdigit(): f.setdefault('anio', int(v))
            # El sello de fecha es el DÍA en que se proyecta, y en el Museo
            # Nacional y la Universidad Nacional es el único dato que la coloca.
            sello = next((int(re.match(r'^(\d{1,2})', x).group(1)) for x in arriba
                          if re.match(r'^\d{1,2}\s*SEPT\.?$', x)), None)
            if sello or sello_pag:
                f['dia_sello'] = sello or sello_pag

            # La región de esta ficha llega hasta el ancla siguiente. Dentro,
            # se tira todo lo que NO es prosa: etiquetas, sellos, el rótulo
            # «SINOPSIS», los encabezados de biografía y las líneas en versales,
            # que son el título de la ficha de al lado.
            sig = anclas[k + 1] if k + 1 < len(anclas) else len(ls)
            region = ls[i + 1:sig]
            # «De Emma Christopher, Sergio Leyva» / «Seiglie»: el nombre del
            # director parte en dos renglones y la cola se colaba en la sinopsis.
            if region and len(region[0].split()) <= 2 and region[0][:1].isupper() \
                    and not PAIS.match(region[0]) and not ETIQ.match(region[0]):
                f['director'] = (f['director'] + ' ' + region[0]).strip()
                region = region[1:]
            prosa = []
            for l in region:
                if PAIS.match(l) and not prosa:
                    f.setdefault('pais', PAIS.match(l).group(1).strip())
                    f.setdefault('anio', int(PAIS.match(l).group(2)))
                    continue
                letras = [c for c in l if c.isalpha()]
                if (ETIQ.match(l) or SELLO.match(l) or BIO.match(l)
                        or l.strip().upper() == 'SINOPSIS'
                        or (letras and len(l) < 60
                            and sum(c.isupper() for c in letras) / len(letras) > 0.8)):
                    prosa.append(None)          # corta el bloque
                    continue
                prosa.append(l)
            # La BIOGRAFÍA se reconoce porque empieza por el nombre de quien
            # dirige —«Ernestina Miranda es lideresa…»—, no por el rótulo: en la
            # p57 la sinopsis va DESPUÉS de la biografía y en la p77 los
            # encabezados están al principio de la página. Un rótulo cuya
            # posición cambia con cada exportación no delimita nada.
            # Por DIRECTOR, no por palabra: «Mar Ajé» no tiene ni un token de
            # más de tres letras, y contando palabras se perdía como persona.
            _sa = lambda x: ''.join(c for c in unicodedata.normalize('NFD', x.lower())
                                    if unicodedata.category(c) != 'Mn')
            dirs = [d.strip() for d in re.split(r',| y ', f['director']) if d.strip()]
            nombres = {_sa(d.split()[0]) for d in dirs if d.split()}
            nombres |= {_sa(w) for d in dirs for w in d.split() if len(w) > 3}
            bloques, cur = [], []
            for x in prosa + [None]:
                if x is None:
                    if cur: bloques.append(cur)
                    cur = []
                else:
                    cur.append(x)
            def es_bio(b):
                pri = b[0].split()
                return bool(nombres & {_sa(w.strip('.,')) for w in pri[:3]})
            sin = [b for b in bloques if not es_bio(b)]
            if not sin:
                # RESCATE, y solo aquí: hay fichas donde la sinopsis va PEGADA al
                # final de la biografía, sin rótulo ni línea en blanco que las
                # separe (La Tinaja, p57). Si ya hay sinopsis por el camino
                # normal esto no se toca —cortar la biografía de una ficha que sí
                # la tiene inventaría una sinopsis con el currículum del
                # director—. Se corta en el primer renglón que empieza frase
                # después de que TODAS las personas que dirigen hayan tenido su
                # biografía: hasta ahí es currículum, de ahí en adelante no.
                for b in bloques:
                    ini_bio = [j for j, x in enumerate(b)
                               if {_sa(w.strip('.,')) for w in x.split()[:3]} & nombres]
                    if not ini_bio or len(ini_bio) < len(dirs):
                        continue
                    for j in range(ini_bio[-1] + 1, len(b)):
                        if b[j - 1].rstrip().endswith('.'):
                            sin = [b[j:]]
                            break
                    if sin:
                        break
            if sin:
                f['sinopsis'] = ' '.join(x for b in sin for x in b).strip()
            out.append(f)
    return out


if __name__ == '__main__':
    import json
    fs = extrae()
    print(f'fichas: {len(fs)} · títulos distintos: {len({f["titulo"] for f in fs})}')
    for k in ('director','pais','anio','duracion_min','tipo','idioma','sinopsis'):
        print(f'   {k:<14}{sum(1 for f in fs if f.get(k))}')
    json.dump({'_provenance': {
        'fuente': 'fichas de obra del PDF oficial del programa QAFF 2026 '
                  '(quibdoafricafilmfestival.com/es/program-2026)',
        'capturado': datetime.date.today().isoformat(),
        'metodo': 'capa de texto del PDF, no OCR; ancla «De <Director>», campos por etiqueta'},
        'obras': fs}, open(_ruta('qaff-2026-bogota-fichas.json'), 'w'),
        ensure_ascii=False, indent=1)
