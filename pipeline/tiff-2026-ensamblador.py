# -*- coding: utf-8 -*-
"""Ensambla TIFF 2026: de los sidecars al formato intermedio del pipeline.

ENTRA
  tiff-2026-oficial.json   244 obras + 887 funciones (endpoint de TIFF)
  tiff-2026-cortos.json    13 programas con sus 72 cortos
  tiff-2026-lbslug.json    lbSlug por obra y por corto
  tiff-2026-tmdb.json      duración, país, póster de TMDB

SALE
  tiff-2026-crudo.json     formato intermedio (lib.py) → geocodificar → publicar

LAS CUATRO DECISIONES QUE ESTE ENSAMBLADOR TOMA, Y POR QUÉ

1. SOLO FUNCIONES PÚBLICAS. `audienceType` distingue «General Public» (638) de
   «Press & Market» (247) y «Private» (2). Decisión de Juan del 13 ago: las de
   prensa no se muestran. Ofrecer una función a la que nadie puede entrar es
   peor que no listarla. El filtro vive AQUÍ, en un solo sitio, y no en cada
   consumidor del dato.

2. UN PROGRAMA NO ES UNA OBRA. Los 13 programas («Short Cuts 2026 Programme
   01», «Wavelengths 2…») son el envase que TIFF vende; las obras son los 72
   cortos que van dentro. Van como `is_cortos` + `film_list`, que es el modelo
   que ya usan FICDEH y FICMA. El programa NO lleva lbSlug; cada corto sí.

3. LA DURACIÓN NO SALE DE LA FUNCIÓN. `endTime - startTime` incluye
   presentación, Q&A y cambio de sala: en la muestra da 153 min para una obra
   de 142. Se usa la duración de la obra (TMDB o Letterboxd) y, para los
   cortos, la que declara el propio TIFF. Sin dato → sin duración, nunca una
   estimada.

4. EL PÓSTER NO SALE DE TIFF. Su campo `posterUrl` mezcla 111 stills, 19
   heroes y solo 46 afiches: es «la imagen que usamos», no un afiche. Meterlo
   en una ranura de póster estiraría stills 16:9. Se usa el póster de TMDB
   (172 de 259) y el resto queda pendiente de curaduría.

LO QUE ESTE ENSAMBLADOR **NO** DECIDE
El emoji y el arquetipo de cada sección son artefacto de diseño y los aprueba
Juan. La tabla SECCIONES de abajo es una PROPUESTA marcada como tal; el nombre
de la sección va verbatim como lo publica TIFF, según la regla de secciones.
"""
import json, os, sys, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'

# Las 6 sedes, con el nombre TAL CUAL lo publica TIFF. Toronto es una sola
# ciudad: `ciudad` va vacío, como manda el formato intermedio.
SEDES = {
    'Scotiabank Theatre Toronto': 'Scotiabank Theatre Toronto',
    'TIFF Lightbox': 'TIFF Lightbox',
    'Roy Thomson Hall': 'Roy Thomson Hall',
    'VISA Screening Room at the Princess of Wales Theatre':
        'VISA Screening Room at the Princess of Wales Theatre',
    'John Bassett Theatre': 'John Bassett Theatre',
    'Royal Alexandra Theatre': 'Royal Alexandra Theatre',
}

# PROPUESTA — pendiente de aprobación de Juan (emoji + arquetipo).
# El NOMBRE es verbatim de TIFF y no se traduce: la app es es+en y estas
# secciones ya nacen en inglés, así que `en` == nombre.
SECCIONES = {
    'Gala Presentations':      ('🎩', 'Apertura / Gala'),
    'Special Presentations':   ('⭐', 'Muestra / País'),
    'Centrepiece':             ('🎯', 'Muestra / País'),
    'Discovery':               ('🔎', 'Perspectivas / Miradas'),
    'Platform':                ('🏆', 'Competencia'),
    'TIFF Docs':               ('🎥', 'Perspectivas / Miradas'),
    'Midnight Madness':        ('🌙', 'Especiales / Eventos'),
    'Wavelengths':             ('〰️', 'Perspectivas / Miradas'),
    'Short Cuts':              ('✂️', 'Cortos / Programas'),
    'TIFF Classics':           ('🏛️', 'Retrospectiva / Tributo'),
    'Primetime':               ('📺', 'Especiales / Eventos'),
    'In Conversation With...': ('🎙️', 'Charlas / Industria'),
    'Special Events':          ('🎪', 'Especiales / Eventos'),
    'TIFF Next Wave Selects':  ('🌊', 'Perspectivas / Miradas'),
    # TIFF la publica como «Unhidden Gems presented by Redbreast». La regla de
    # secciones es verbatim, pero verbatim aquí mete una marca de whisky en la
    # interfaz: Juan decidió el 13 ago quitar el patrocinador. Es la excepción
    # a la regla, y por eso queda escrita aquí y no aplicada en silencio.
    'Unhidden Gems presented by Redbreast': ('💎', 'Muestra / País', 'Unhidden Gems'),
}

# Las charlas no son proyecciones. Ver el vocabulario del proyecto:
# «actividad» es el paraguas, «función» es solo proyección.
SECCIONES_DE_CHARLA = {'In Conversation With...'}


def publicado(clave):
    """Nombre con el que la sección sale a la app.

    Por defecto es el que publica TIFF, verbatim. La tabla puede traer un
    tercer elemento cuando hay una excepción aprobada —hoy solo «Unhidden
    Gems», a la que Juan le quitó el patrocinador—. Dueño único: si este
    nombre se calculara en dos sitios, uno de los dos se olvidaría.
    """
    v = SECCIONES.get(clave)
    return v[2] if v and len(v) > 2 else clave


def main():
    ofi = json.load(open(f'{ST}/tiff-2026-oficial.json', encoding='utf-8'))['obras']
    cor = json.load(open(f'{ST}/tiff-2026-cortos.json', encoding='utf-8'))['programas']
    slugs = json.load(open(f'{ST}/tiff-2026-lbslug.json', encoding='utf-8'))['obras']
    tmdb = {x['lbSlug']: x for x in
            json.load(open(f'{ST}/tiff-2026-tmdb.json', encoding='utf-8'))['obras']}

    por_clave = {s['clave']: s for s in slugs}
    cortos_de = {p['slug']: p['cortos'] for p in cor}

    def datos_lb(clave):
        s = por_clave.get(clave)
        if not s:
            return {}
        t = tmdb.get(s['lbSlug'], {})
        return {'lbSlug': s['lbSlug'], 'tmdb_id': s.get('tmdb_id'),
                'duracion': t.get('duracion_tmdb') or t.get('duracion'),
                'poster_tmdb': t.get('poster_tmdb'),
                'anio': t.get('anio_tmdb') or t.get('anio'),
                'paises': t.get('paises')}

    funciones, secciones_vistas, multiseccion = [], set(), []
    saltadas = {'no_publica': 0, 'cancelada': 0}

    for o in ofi:
        es_programa = o['slug'] in cortos_de
        lb = {} if es_programa else datos_lb(o['slug'])
        # TIFF cuelga 18 obras de DOS secciones. La app modela una sola, así
        # que se toma la primera —que es la curatorial— y la segunda se
        # conserva como etiqueta. Antes se descartaba sin decir nada, y un
        # dato que desaparece callado es el peor de los dos errores posibles.
        todas_sec = o['secciones'] or ['(sin sección)']
        sec = publicado(todas_sec[0])
        etiquetas = [publicado(x) for x in todas_sec[1:]]
        secciones_vistas.update(todas_sec)
        if etiquetas:
            multiseccion.append({'titulo': o['titulo'], 'seccion': sec,
                                 'etiquetas': etiquetas})

        lista = None
        if es_programa:
            lista = []
            for c in cortos_de[o['slug']]:
                clb = datos_lb(c['id'])
                lista.append({
                    'titulo': c['titulo'],
                    'titulo_original': c.get('tituloAlt'),
                    'director': ', '.join(c.get('directores') or []) or None,
                    'anio': c.get('anio'),
                    'duracion_min': int(c['duracion']) if str(c.get('duracion') or '').isdigit() else None,
                    'pais': ', '.join(c.get('paises') or []) or None,
                    'sinopsis': c.get('sinopsis') or None,
                    'lbSlug': clb.get('lbSlug'),
                })

        for f in o['funciones']:
            # Decisión 1: solo público. Un pase de prensa no es asistible.
            if f['audiencia'] != 'General Public':
                saltadas['no_publica'] += 1
                continue
            if f['cancelada']:
                saltadas['cancelada'] += 1
                continue
            ini = f['ini']          # «2026-09-14 15:20:00», hora local de Toronto
            dia, hora = ini[:10], ini[11:16]
            funciones.append({
                'titulo': o['titulo'],
                'dia': dia, 'hora': hora,
                'sede': SEDES.get(f['sede'], f['sede']),
                'sala': f['sala'] or '',
                'ciudad': '',
                'director': ', '.join(o.get('directores') or []) or None,
                'pais': o.get('paises') or (', '.join(lb.get('paises') or []) or None),
                'anio': lb.get('anio'),
                # Decisión 3: nunca endTime - startTime.
                'duracion_min': lb.get('duracion'),
                'has_qa': False,
                'acceso': 'regular' if 'regular' in (f['costo'] or []) else (
                    (f['costo'] or [None])[0]),
                'en_app': True,
                # extras que el publicador consume
                'seccion': sec,
                'etiquetas_seccion': etiquetas or None,
                'sinopsis': o.get('sinopsis') or None,
                'sinopsis_lang': 'en',
                'idiomas': o.get('idiomas'),
                'generos': o.get('generos') or [],
                'lbSlug': lb.get('lbSlug'),
                'tmdb_id': lb.get('tmdb_id'),
                # Decisión 4: el póster sale de TMDB, no de TIFF.
                'poster_tmdb': lb.get('poster_tmdb'),
                'is_cortos': es_programa,
                'film_list': lista,
                'tipo': 'charla' if sec in SECCIONES_DE_CHARLA else 'proyeccion',
                'boleta': f.get('boleta'),
                'accesibilidad': f.get('accesibilidad') or [],
                'formato': f.get('formato'),
            })

    faltan = secciones_vistas - set(SECCIONES)
    if faltan:
        sys.exit(f'Secciones sin entrada en SECCIONES: {sorted(faltan)}. '
                 'Una sección nueva es una decisión de diseño, no un default.')

    dias = sorted({f['dia'] for f in funciones})
    salida = f'{ST}/tiff-2026-crudo.json'
    json.dump({'_provenance': provenance(
                   'tiff-2026-oficial + tiff-2026-cortos + tiff-2026-lbslug + tiff-2026-tmdb',
                   metodo='solo funciones «General Public»; programas como is_cortos+film_list'),
               '_festival': {'id': 'tiff2026', 'ciudad': 'Toronto', 'pais': 'Canadá',
                             'timezoneOffset': '-04:00', 'dias': dias},
               '_secciones_propuestas': {publicado(k): {'emoji': e, 'archetype': a,
                                                             'en': publicado(k)}
                                         for k, (e, a) in ((x, v[:2]) for x, v in SECCIONES.items())
                                         if k in secciones_vistas},
               '_saltadas': saltadas, '_multiseccion': multiseccion,
               'funciones': funciones},
              open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'── {salida}')
    print(f'   funciones públicas {len(funciones)} · saltadas '
          f'{saltadas["no_publica"]} prensa/privadas + {saltadas["cancelada"]} canceladas')
    print(f'   días {len(dias)} ({dias[0]} → {dias[-1]}) · sedes {len({f["sede"] for f in funciones})} '
          f'· salas {len({f["sala"] for f in funciones})}')
    print(f'   obras en 2 secciones: {len(multiseccion)} (la 2ª queda como etiqueta)')
    print(f'   secciones {len(secciones_vistas)} · programas de cortos '
          f'{len({f["titulo"] for f in funciones if f["is_cortos"]})}')
    print(f'   con lbSlug {sum(1 for f in funciones if f["lbSlug"])}/{len(funciones)} · '
          f'con póster {sum(1 for f in funciones if f["poster_tmdb"])}/{len(funciones)} · '
          f'con duración {sum(1 for f in funciones if f["duracion_min"])}/{len(funciones)}')


if __name__ == '__main__':
    main()
