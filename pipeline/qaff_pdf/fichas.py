# -*- coding: utf-8 -*-
"""Las fichas de obra del PDF oficial del programa QAFF 2026.

El PDF tiene CAPA DE TEXTO —no es OCR—, así que estos datos no pueden tener
errores de lectura: o el festival lo escribió así, o no está. El ancla es la
línea «De <Director>» inmediatamente bajo el título; todo lo demás se lee por
etiqueta, nunca por posición (leer por posición fue lo que en la cosecha por OCR
pegó la sinopsis de una obra a otra en las páginas de dos fichas)."""
import re, sys, os, datetime
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

def extrae():
    P = paginas()
    out = []
    for n in sorted(P, key=int):
        ls = limpia(P[n])
        anclas = [i for i, l in enumerate(ls) if DE.match(l) and i > 0]
        for k, i in enumerate(anclas):
            fin = anclas[k + 1] - 1 if k + 1 < len(anclas) else len(ls)
            f = {'titulo': _titulo(ls, i), 'director': DE.match(ls[i]).group(1).strip(),
                 '_pagina': int(n)}
            cuerpo = ls[i + 1:fin]
            for j, l in enumerate(cuerpo):
                m = PAIS.match(l)
                if m and j < 3:
                    f['pais'], f['anio'] = m.group(1).strip(), int(m.group(2))
                m = ETIQ.match(l)
                if m:
                    et, v = m.group(1).lower(), m.group(2).strip()
                    if et.startswith('duraci') and v: f['duracion_min'] = _dur(v)
                    elif et.startswith('tipo'):       f['tipo'] = v
                    elif et.startswith('idioma'):     f['idioma'] = v
                    elif et.startswith('pa'):         f.setdefault('pais', v)
                    elif et.startswith('a'):
                        if v.isdigit(): f.setdefault('anio', int(v))
            if 'SINOPSIS' in cuerpo:
                s = cuerpo.index('SINOPSIS') + 1
                e = next((j for j in range(s, len(cuerpo)) if BIO.match(cuerpo[j])), len(cuerpo))
                # La fecha («14 SEPT.» / «2026») no es parte de la sinopsis, pero
                # TAMPOCO es adorno: es el DÍA en que se proyecta esa obra, y en
                # las sedes sin parrilla —Museo Nacional, Universidad Nacional—
                # es el único dato que la coloca. Filtrarla del texto estaba bien;
                # tirarla, no. Se guarda.
                _fecha = [x for x in cuerpo[s:e] if re.match(r'^\d{1,2}\s*SEPT\.?$', x)]
                if _fecha:
                    f['dia_sello'] = int(re.match(r'^(\d{1,2})', _fecha[0]).group(1))
                txt = [x for x in cuerpo[s:e]
                       if not re.match(r'^\d{1,2}\s*SEPT\.?$|^20\d\d$', x)]
                if txt: f['sinopsis'] = ' '.join(txt).strip()
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
