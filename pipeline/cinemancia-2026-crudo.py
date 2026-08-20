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


def obras_en(crudo, cat):
    """TODAS las obras del catálogo que aparecen en un título de parrilla.

    Una celda de la parrilla junta varias películas con «+» y les intercala el
    director: «La tempestá + No contéis con los dedos + Vampir Cuadecuc Pere
    Portabella» son TRES. Quedarse con la coincidencia más larga —que era lo
    que hacía— perdía las otras dos, y eso pasaba en 28 funciones.

    Se buscan todas por posición y se descartan las que se solapan: si «Verano»
    cae dentro de un título más largo ya encontrado, no es una obra aparte.
    """
    c = clave(crudo)
    hits = []
    for k, o in cat.items():
        if len(k) < 6:
            continue
        i = c.find(k)
        if i >= 0:
            hits.append((i, i + len(k), k, o))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out, ocupado = [], []
    for ini, fin, k, o in hits:
        if any(ini < f2 and fin > i2 for i2, f2 in ocupado):
            continue
        if any(o is x for x in out):
            continue
        ocupado.append((ini, fin))
        out.append(o)
    return out


def main():
    par = json.load(open(f'{S}/cinemancia-2026-programacion-oficial.json', encoding='utf-8'))['funciones']
    of = json.load(open(f'{S}/cinemancia-2026-programas-oficial.json', encoding='utf-8'))
    cat = catalogo()

    # El índice lleva SEDE, no solo día y hora. Dos funciones distintas pueden
    # coincidir en horario en sedes distintas: el sábado 5 a las 18:00 corren a
    # la vez la Retrospectiva Navarro y el pase de Pere Portabella, y sin la
    # sede la charla de Portabella se pegaba a las dos.
    # Se agrupa por día y hora, y la sede desempata por CONTENCIÓN de prefijo:
    # la hoja escribe «Teatro Caribe» y la parrilla «Teatro Caribe Itagüí», así
    # que un corte fijo de N caracteres los separaba. Con una sola candidata en
    # ese horario no hace falta desempatar.
    def mete(d, k, v): d.setdefault((k['dia'], k['hora']), []).append((clave(k['sede']), v))
    pases, charlas = {}, {}
    for p in of['programas']:
        for x in p['pases']: mete(pases, x, p)
    for c in of['charlas']: mete(charlas, c, c)

    def busca(idx, f):
        cand = idx.get((f['dia'], f['hora']))
        if not cand: return None
        # La sede SIEMPRE tiene que coincidir. El atajo «si solo hay una
        # candidata, dásela» pegaba la misma charla a las dos funciones que
        # corren a esa hora en sedes distintas.
        cs = clave(f['sede'])
        for sede, v in cand:
            if cs.startswith(sede[:12]) or sede.startswith(cs[:12]): return v
        return None

    programas, sin_obra = [], []
    for f in par:
        e = {'dia': f['dia'], 'hora': f['hora'], 'sede': f['sede'],
             '_src': 'PDF oficial de programación del festival'}
        if f.get('duracion_min'): e['duracion_min'] = f['duracion_min']
        if f.get('_hora_inferida'): e['_hora_inferida'] = True
        e['acceso'] = acceso_de(f['sede'], f['titulo_crudo'])

        p = busca(pases, f)
        ch = busca(charlas, f)          # un programa TAMBIÉN puede llevar debate
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
            if ch:
                e['_charla'] = {'descripcion': ch['descripcion'], 'invitados': ch['invitados']}
        else:
            # Función simple: la obra sale del catálogo por el título crudo.
            halladas = obras_en(f['titulo_crudo'], cat)
            hallada = halladas[0] if halladas else None
            # Un PROGRAMA DOBLE se titula con las dos, unidas por «+», que es
            # como lo escribe el festival en su parrilla. Ponerle el nombre de
            # la primera escondía la segunda: quien leía «La corazonada» no
            # tenía manera de saber que también se proyecta «Cairo Streets».
            if ch:
                e['titulo'] = ch['titulo']
            elif len(halladas) > 1:
                e['titulo'] = ' + '.join(o['title'] for o in halladas)
            elif hallada:
                e['titulo'] = hallada['title']
            else:
                e['titulo'] = f['titulo_crudo']
            e['obras'] = [obra_de(o) for o in halladas]
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

    # Un programa que se repite se anuncia dos veces, y la parrilla solo lista
    # su contenido en UNO de los pases: «Retrospectiva Sergio Navarro Programa
    # 2» sale vacío el sábado 5 y con sus dos títulos el jueves 10, ambos con
    # 87'. Mismo nombre de programa y misma duración = mismo programa, y las
    # obras del pase que sí las trae valen para el otro.
    porprog = {}
    for e, f in zip(programas, par):
        nom = re.sub(r'\s+', ' ', f['titulo_crudo']).strip()
        m = re.match(r'^(.*?\bPrograma\s*\d)\b', nom, re.I)
        if not m or not e['obras']: continue
        porprog.setdefault((clave(m.group(1)), e.get('duracion_min')), e['obras'])
    heredadas = 0
    for e, f in zip(programas, par):
        if e['obras']: continue
        nom = re.sub(r'\s+', ' ', f['titulo_crudo']).strip()
        m = re.match(r'^(.*?\bPrograma\s*\d)\b', nom, re.I)
        if not m: continue
        src = porprog.get((clave(m.group(1)), e.get('duracion_min')))
        if src:
            e['obras'] = [dict(o) for o in src]
            e['_obras_src'] = 'contenido tomado del otro pase del MISMO programa (mismo nombre y misma duración)'
            heredadas += 1
    print(f'programas que heredan su contenido del otro pase: {heredadas}')

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
