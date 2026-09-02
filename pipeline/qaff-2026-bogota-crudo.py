#!/usr/bin/env python3
"""Crudo de QAFF 2026 — BOGOTÁ.

Quibdó quedó CANCELADO por el terremoto del 10 ago (confirmado por Juan, 2 SEP):
la 8ª edición es solo en Bogotá. Este crudo sustituye a las 47 funciones de
Quibdó que quedaron ocultas en producción, no las complementa.

DOS FUENTES, cada una en lo suyo:
  · LA PARRILLA (día, hora, sede, sala, qué se proyecta) sale del programa
    oficial en flipbook, publicado el 2 SEP. Extraída y verificada por DOS
    auditorías independientes que coincidieron en los 68 cupos —mismo día,
    hora, sede y título, cero diferencias—. Ver
    festivals/staging/qaff-2026-bogota-auditoria.json y -auditoria-3.json.
  · LAS OBRAS salen de NUESTRO catálogo del onboarding del Chocó, que costó
    meses: 38 de las 57 obras de Bogotá ya estaban enriquecidas con sinopsis,
    afiche, director, país y año. Esas se heredan enteras. Las otras 19 se
    siembran con lo que imprime el propio programa (director, duración y país
    en las 19; año y género en 15) y se enriquecen aparte.

Por qué el crudo y no un JSON a mano: el mismo camino genérico que el resto
—crudo → ensamblar → publicar— para que el contrato, las banderas y los
guardianes se apliquen igual que a los demás festivales.
"""
import json, re, unicodedata, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(BASE, 'festivals', 'staging')

def n(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', (s or ''))
                  .encode('ascii', 'ignore').decode().lower())

# Las 5 sedes con su dirección salen del «Plano de orientación» del programa
# (p2), que es la única página que las lista con nomenclatura y dirección.
SEDES = {
    'cinematecadebogota':          'Cinemateca de Bogotá',
    'alianzafrancesa':             'Alianza Francesa',
    'universidaddelosandes':       'Universidad de los Andes',
    'pontificiauniversidadjaveriana': 'Pontificia Universidad Javeriana',
}
def sede_norm(s):
    """Normaliza a UN nombre por sede (el programa las escribe de varias
    formas). La forma publicada «<Sede> - <Ciudad>» NO se decide aquí: la
    declara la tabla `sedes` del plan, que es donde vive ese mapeo para todos
    los festivales."""
    k = n(s)
    for kk, v in SEDES.items():
        if kk in k or k in kk: return v
    return (s or '').strip()

MINUS = {'de','del','la','las','el','los','y','a','en','un','una','the','of','and','ni','du','le'}
def titulo_casa(t):
    """El programa imprime los títulos en VERSALES; nuestro catálogo los guarda
    en capital normal («Caída Libre», «Face to Face»). Se baja SOLO lo que
    viene todo en mayúsculas —si el festival ya lo escribió mixto, se respeta—
    y se dejan intactas las palabras que no son iniciales. No se traduce ni se
    reordena nada: es tipografía, no contenido."""
    t = (t or '').strip()
    if not t or t != t.upper(): return t
    out = []
    for i, w in enumerate(t.split()):
        if w.isupper() and len(w) <= 4 and not w.isalpha(): out.append(w); continue
        b = w.capitalize()
        if i and b.lower() in MINUS: b = b.lower()
        out.append(b)
    return ' '.join(out)

def dur_min(d):
    """«19'57» son 19 min y 57 s → 19. «120'» → 120. El festival mezcla los dos."""
    if not d: return None
    m = re.match(r"(\d+)", str(d))
    return int(m.group(1)) if m else None

def fichas_pdf():
    """Las fichas que el festival publica en el PDF de su programa
    (quibdoafricafilmfestival.com/es/program-2026). El PDF tiene CAPA DE TEXTO:
    no es OCR, no puede tener errores de lectura. De ahí salen país, año y la
    SINOPSIS EN ESPAÑOL de las obras que el catálogo del Chocó no traía —el
    hueco que dos cosechas por OCR no lograron llenar sin corromper datos."""
    p = os.path.join(BASE, 'festivals', 'staging', 'qaff-2026-bogota-fichas-pdf.json')
    if not os.path.exists(p): return {}
    d = json.load(open(p, encoding='utf-8'))
    return {n(k): v for k, v in d.items()}


def catalogo():
    """Todo lo que ya sabemos de las obras, de las dos fuentes nuestras."""
    dic = {}
    for f in ('qaff-2026.json', 'staging/qaff-2026.json'):
        p = os.path.join(BASE, 'festivals', f)
        if not os.path.exists(p): continue
        for o in json.load(open(p, encoding='utf-8'))['films']:
            for k in ('title', 'title_en'):
                if o.get(k): dic.setdefault(n(o[k]), o)
    return dic

# El programa marca, junto a una obra suelta, «con la presencia de la
# directora / del director / de la guionista / del protagonista». Es un
# invitado en sala: para la app eso es Q&A. Se declara por FUNCIÓN (sede,
# día, hora) porque el flag vive en la función, no en la obra, y cada una
# de estas nueve marcas resolvió a una sola función del crudo con la obra
# nombrada dentro — sexta verificación cruzada del programa de Bogotá.
INVITADOS = {
    ('Pontificia Universidad Javeriana', '2026-09-15', '10:00'): 'directoras de Caída Libre y Tía Ciata',
    ('Pontificia Universidad Javeriana', '2026-09-17', '10:00'): 'guionista de Soñé su nombre',
    ('Pontificia Universidad Javeriana', '2026-09-18', '10:00'): 'protagonista de Amazonas: Cocinas Indígenas de Selva y Río',
    ('Universidad de los Andes', '2026-09-15', '14:00'): 'directora de Fitofascias',
    ('Universidad de los Andes', '2026-09-16', '13:00'): 'directoras de Caída Libre y Tía Ciata',
    ('Cinemateca de Bogotá', '2026-09-18', '17:00'): 'director de Iniciación en la Octava Dimensión',
    ('Cinemateca de Bogotá', '2026-09-19', '14:00'): 'director de Caída Libre',
}

def hereda(cat, titulo):
    k = n(titulo)
    if k in cat: return cat[k]
    for kk, v in cat.items():
        if len(k) > 7 and (k in kk or kk in k): return v
    return None

def main():
    aud = json.load(open(os.path.join(S, 'qaff-2026-bogota-auditoria-3.json'), encoding='utf-8'))
    cat = catalogo()
    fpdf = fichas_pdf()
    programas, heredadas, sembradas = [], 0, 0
    for pg in aud['paginas']:
        sede = sede_norm(pg.get('sede'))
        for fu in pg.get('funciones', []):
            obras = []
            for o in (fu.get('obras') or []):
                base = hereda(cat, o.get('titulo'))
                e = {'titulo': o.get('titulo')}
                if base:
                    # NUESTRO catálogo manda en la obra; el programa solo
                    # rellena lo que a él le falte.
                    for c in ('title', 'director', 'country', 'year', 'synopsis',
                              'synopsis_lang', 'synopsis_en', 'poster', 'posterSource',
                              'lbSlug', 'duration', 'section'):
                        if base.get(c) is not None: e[c] = base[c]
                    e['titulo'] = base.get('title') or o.get('titulo')
                    e['_obra_src'] = 'catálogo del onboarding del Chocó'
                    heredadas += 1
                else:
                    e.update({'director': o.get('director'), 'pais': o.get('pais'),
                              'anio': o.get('anio'), 'genero': o.get('genero')})
                    e['titulo'] = titulo_casa(o.get('titulo'))
                    e['_obra_src'] = 'ficha impresa en el programa de Bogotá (2 SEP)'
                    fp = fpdf.get(n(o.get('titulo')))
                    if fp:
                        if fp.get('sinopsis'):
                            e['sinopsis'] = fp['sinopsis']; e['synopsis_lang'] = 'es'
                        if fp.get('pais'): e['pais'] = fp['pais']
                        if fp.get('anio'): e['anio'] = fp['anio']
                        e['_obra_src'] = 'ficha del PDF oficial del programa (capa de texto, no OCR)'
                    sembradas += 1
                d = dur_min(o.get('duracion'))
                if d: e['duracion_min'] = d
                if o.get('nota'): e['_nota'] = o['nota']
                obras.append({k: v for k, v in e.items() if v not in (None, '', [], {})})
            if not obras: continue
            # El título de la función: el nombre del bloque si el festival le
            # puso uno; si son dos obras, unidas por «+» como en el resto del
            # repo; si es una sola, la obra.
            nb = fu.get('bloque_titulo')
            if nb: titulo = nb
            elif len(obras) == 1: titulo = obras[0]['titulo']
            else: titulo = ' + '.join(o['titulo'] for o in obras)
            f = {'dia': fu.get('dia'), 'hora': fu.get('hora'), 'sede': sede,
                 'titulo': titulo, 'obras': obras,
                 # El programa NO dice cómo se entra a ninguna función de
                 # Bogotá. No se hereda el «entrada libre» de Quibdó: eran otra
                 # ciudad y otras sedes, y la Cinemateca suele cobrar boleta.
                 # El contrato exige declarar la ignorancia, no callarla.
                 'acceso': 'desconocido',
                 '_src': 'programa oficial en flipbook (2 SEP 2026), verificado por dos auditorías independientes'}
            if fu.get('sala'):
                # La dirección que el programa mete entre paréntesis es de la
                # SEDE, no de la sala: «Auditorio Centro Ático (Carrera 7 #
                # 40-62)» → «Auditorio Centro Ático».
                f['sala'] = re.sub(r'\s*\([^)]*\)\s*$', '', fu['sala']).strip()
            if fu.get('hora_fin'): f['hora_fin'] = fu['hora_fin']
            if len(obras) > 1: f['is_cortos'] = True
            # La SECCIÓN es de la función, y sale de sus obras: son las del
            # propio festival, ya guardadas en el catálogo del Chocó. Gana la
            # más frecuente entre las obras que la declaran. Si NINGUNA la
            # declara —las 19 sembradas no la traen— la función queda sin
            # sección y se cuenta aparte: inventarla sería peor.
            _inv = INVITADOS.get((sede, f['dia'], f['hora']))
            if _inv:
                f['has_qa'] = True
                f['_qa_src'] = 'el programa anuncia la presencia de ' + _inv
            secs = [o['section'] for o in obras if o.get('section')]
            if secs:
                # el catálogo del Chocó guarda la sección YA publicada («☕ Panorama
                # Diaspórica»); el plan la indexa pelada y el emoji lo pone el
                # ensamblador. Devolverla con emoji la deja huérfana del mapa.
                f['seccion'] = re.sub(r'^\S+\s+', '', max(set(secs), key=secs.count))
            for o in obras: o.pop('section', None)
            dm = sum(o.get('duracion_min') or 0 for o in obras)
            if dm: f['duracion_min'] = dm
            programas.append(f)
    programas.sort(key=lambda x: (x['dia'] or '', x['hora'] or '', x['sede']))
    out = {
        '_provenance': {
            'capturado': '2026-09-02',
            'parrilla': 'programa oficial en flipbook, online.fliphtml5.com/QAFF2026/Programa-QAFF2026 (2 SEP 2026)',
            'verificacion': 'dos auditorías independientes sobre las imágenes; coincidieron en los 68 cupos sin una sola diferencia',
            'obras': 'heredadas del catálogo del onboarding del Chocó; las que no estaban, sembradas con la ficha impresa',
            'quibdo': 'CANCELADO por el terremoto del 10 ago — la edición es solo en Bogotá',
            'sin_prelanzamiento': 'el prelanzamiento del 5 SEP en el Museo Nacional queda fuera por decisión de Juan',
        },
        '_funciones': len(programas),
        'programas': programas,
    }
    json.dump(out, open(os.path.join(S, 'qaff-2026-bogota-crudo.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'{len(programas)} funciones · {heredadas} obras heredadas · {sembradas} sembradas del programa')
    import collections
    for k, v in collections.Counter(f['sede'] for f in programas).most_common():
        print(f'   {v:3}  {k}')

if __name__ == '__main__':
    main()
