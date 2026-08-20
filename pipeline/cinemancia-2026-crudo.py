# -*- coding: utf-8 -*-
"""Arma el crudo de Cinemancia 2026 desde las DOS fuentes oficiales.

  · la PARRILLA del PDF  → las 86 funciones: día, hora, sede, duración
  · la HOJA del festival → qué obras van en cada programa, y las 10 charlas

La parrilla dice CUÁNDO y DÓNDE; la hoja dice QUÉ. Ninguna de las dos basta:
la parrilla anuncia «Competencia de cortometrajes Programa 1» sin listar sus
cortos, y la hoja no tiene las funciones que no son programa.

El catálogo previo (build.json) aporta sinopsis y datos de las obras que ya
teníamos; las 15 obras nuevas de la competencia internacional entran con lo
que trae la hoja.
"""
import json, re, unicodedata, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = f'{REPO}/festivals/staging'

def clave(s):
    """Clave de comparación SIN espacios. No es lib.clave(), que los conserva:
    acá se busca un título DENTRO de otro («Macho Dancer» dentro de «Macho
    Dancer Lino Brocka») y los espacios del original estorban."""
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

def catalogo():
    """Las 109 obras del catálogo, fusionando TRES fuentes por obra.

    Ninguna basta sola, y el publicador lo cazó al ver que el build perdía
    sinopsis contra producción:

      · el sidecar tmdb trae las 109 obras, pero solo 52 sinopsis;
      · el sidecar web trae 56 sinopsis sacadas de la ficha del festival;
      · y el JSON PUBLICADO trae 89, porque a lo largo del onboarding se
        arreglaron a mano ahí y nadie las devolvió aguas arriba.

    Se fusiona en ese orden y gana el primero que tenga el campo lleno, así
    que un arreglo hecho abajo no se pierde al regenerar."""
    d = json.load(open(f'{S}/cinemancia-2026-tmdb.json', encoding='utf-8'))
    # Se indexa el título ENTERO y además cada parte separada por «/». Los
    # títulos bilingües no vienen en el mismo orden ni con las mismas
    # variantes: el catálogo trae «La tercera opción / Die dritte Option / The
    # Third Option» y la parrilla solo las dos primeras, así que buscar la
    # clave entera dentro del crudo nunca casaba.
    # sinopsis de la ficha web del festival, por título
    web = {}
    try:
        for o in json.load(open(f'{S}/cinemancia-2026-web.json', encoding='utf-8'))['obras']:
            if o.get('synopsis_web'): web[clave(o.get('title_web'))] = o['synopsis_web']
    except FileNotFoundError:
        pass
    # lo que ya está PUBLICADO: último recurso, pero es donde viven los
    # arreglos a mano que nunca volvieron al sidecar
    pub = {}
    try:
        pd = json.load(open(f'{REPO}/festivals/cinemancia-2026.json', encoding='utf-8'))
        for f in pd['films']:
            for o in [f] + list(f.get('film_list') or []):
                if o.get('title'): pub.setdefault(clave(o['title']), o)
    except FileNotFoundError:
        pass
    for o in d['obras']:
        k = clave(o.get('title'))
        p = pub.get(k, {})
        o.setdefault('tmdb_id', o.get('tmdbId'))
        if not o.get('synopsis'): o['synopsis'] = web.get(k) or p.get('synopsis')
        for campo_pub in ('synopsis_en', 'title_en', 'poster', 'posterSource', 'duration', 'country'):
            if not o.get(campo_pub) and p.get(campo_pub): o[campo_pub] = p[campo_pub]
        if not o.get('poster') and o.get('poster_tmdb'):
            o['poster'], o['posterSource'] = o['poster_tmdb'], 'tmdb'
        if not o.get('duration') and o.get('runtime_tmdb'): o['duration'] = f"{o['runtime_tmdb']} min"
    out = {}
    for o in d['obras']:
        for campo in ('title', 'title_en'):
            t = o.get(campo)
            if not t: continue
            out.setdefault(clave(t), o)
            for parte in t.split('/'):
                if len(clave(parte)) > 6: out.setdefault(clave(parte), o)
    return out

def obra_de(o):
    """Ficha del catálogo → obra del crudo, con los nombres del contrato."""
    d = {'titulo': o.get('title'), 'director': o.get('director'),
         'seccion': o.get('section'),
         'pais': o.get('country'), 'anio': o.get('year'),
         'sinopsis': o.get('synopsis'), 'synopsis_en': o.get('synopsis_en'),
         'title_en': o.get('title_en'), 'poster': o.get('poster'),
         'posterSource': o.get('posterSource'), 'tmdb_id': o.get('tmdb_id'),
         'lbSlug': o.get('lbSlug')}
    dur = o.get('duration') or o.get('duracion_min') or o.get('runtime')
    m = re.match(r'^(\d+)', str(dur or ''))
    if m: d['duracion_min'] = int(m.group(1))
    if d.get('anio'):
        try: d['anio'] = int(d['anio'])
        except (TypeError, ValueError): d.pop('anio')
    return {k: v for k, v in d.items() if v not in (None, '', [], {})}

# CÓMO SE ENTRA — literal de la nota «Información importante · Boletería» del
# PDF oficial (pág. 2). No se deduce: el festival lo dice con todas las letras.
#
#   «A excepción de las funciones en Cineprox Las Américas y Cine MAMM, las
#    funciones del festival son de entrada libre.»
#
# El build anterior ponía is_free en las 89 funciones por igual, incluidas las
# de esas dos sedes, que SÍ cobran. En Cineprox las sillas son numeradas y la
# boleta se compra en taquilla; en Cine MAMM, en el primer piso del museo.
SEDES_PAGAS = {
    'Cineprox Las Américas': 'Boleta en taquilla — sillas numeradas',
    'Cine MAMM': 'Boleta en el primer piso del museo',
}
# Estas actividades piden inscripción previa (misma nota del PDF).
CON_INSCRIPCION = re.compile(r'Foro de la [Cc]r[íi]tica|C[áa]psula de Proyectos|'
                             r'Seminario de la imagen|Laboratorio Internacional de Montaje')


def acceso_de(sede, titulo):
    for k, v in SEDES_PAGAS.items():
        if k.lower() in (sede or '').lower(): return v
    if CON_INSCRIPCION.search(titulo or ''): return 'Entrada libre con inscripción previa'
    return 'Entrada libre'


def main():
    par = json.load(open(f'{S}/cinemancia-2026-programacion-oficial.json', encoding='utf-8'))['funciones']
    of = json.load(open(f'{S}/cinemancia-2026-programas-oficial.json', encoding='utf-8'))
    cat = catalogo()

    # índice de pases: (día, hora) → programa, y (día, hora) → charla
    pases, charlas = {}, {}
    for p in of['programas']:
        for x in p['pases']: pases[(x['dia'], x['hora'])] = p
    for c in of['charlas']: charlas[(c['dia'], c['hora'])] = c

    programas, sin_obra = [], []
    for f in par:
        e = {'dia': f['dia'], 'hora': f['hora'], 'sede': f['sede'],
             '_src': 'PDF oficial de programación del festival'}
        if f.get('duracion_min'): e['duracion_min'] = f['duracion_min']
        if f.get('_hora_inferida'): e['_hora_inferida'] = True
        e['acceso'] = acceso_de(f['sede'], f['titulo_crudo'])

        p = pases.get((f['dia'], f['hora']))
        if p:
            # PROGRAMA: las obras las manda la hoja del festival, en su orden.
            e['titulo'] = p['programa']
            e['obras'] = []
            for o in p['obras']:
                base = cat.get(clave(o['titulo']))
                d = obra_de(base) if base else {}
                d.update({k: v for k, v in o.items() if v not in (None, '')})
                e['obras'].append(d)
            e['_src'] = 'hoja oficial del festival (orden de programas)'
        else:
            ch = charlas.get((f['dia'], f['hora']))
            # Función simple: la obra sale del catálogo por el título crudo.
            hallada = None
            for k, o in cat.items():
                if len(k) > 5 and k in clave(f['titulo_crudo']):
                    if hallada is None or len(k) > len(clave(hallada['title'])): hallada = o
            e['titulo'] = (ch['titulo'] if ch else
                           (hallada['title'] if hallada else f['titulo_crudo']))
            e['obras'] = [obra_de(hallada)] if hallada else []
            if not hallada: sin_obra.append(f)
            if ch:
                e['_charla'] = {'descripcion': ch['descripcion'], 'invitados': ch['invitados']}
                e['_src'] = 'hoja oficial del festival (conversatorios y charlas)'
        # La sección es de la FUNCIÓN, no solo de la obra: el ensamblador la
        # lee de f['seccion']. En un programa, todas sus obras comparten
        # sección; en una función simple, es la de su única obra.
        secs = [o.get('seccion') for o in e['obras'] if o.get('seccion')]
        if secs:
            e['seccion'] = max(set(secs), key=secs.count)
        for o in e['obras']: o.pop('seccion', None)
        programas.append(e)

    out = {'_provenance': {
        'fuente': 'PDF oficial de programación + hoja de programas y charlas enviada por el festival',
        'capturado': '2026-08-20',
        'metodo': 'la parrilla da cuándo y dónde; la hoja da qué obras van en cada programa',
        'nota': 'el barrido anterior sacaba el horario de la ficha de cada película: salían 89 funciones sueltas en vez de programas, sin la inauguración ni la clausura'},
        '_funciones': len(programas), 'programas': programas}
    json.dump(out, open(f'{S}/cinemancia-2026-crudo.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'{len(programas)} funciones · {sum(len(p["obras"]) for p in programas)} obras')
    print(f'funciones sin obra identificada: {len(sin_obra)}')
    for f in sin_obra[:30]: print(f'   {f["dia"]} {f["hora"]} · {f["titulo_crudo"][:62]}')

if __name__ == '__main__':
    main()
