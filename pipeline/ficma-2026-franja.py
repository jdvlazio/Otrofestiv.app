# -*- coding: utf-8 -*-
"""Lee la FRANJA ACADÉMICA de FICMA 17 → sidecar de staging.

Segundo PDF del festival, mismo origen que el de programación: 15 páginas de
imagen en formato de post de Instagram, sin texto. Se lee con el mismo OCR
(pipeline/ficma-2026-ocr.swift) y se parsea aquí.

La plantilla es distinta a la de las películas —la columna de datos va a la
IZQUIERDA (x≈0.09), no a la derecha— y cambia según el tipo, que es la propia
división del festival:

  · TALLERES  → DIRECTOR: · LUGAR: · HORA: · CUPOS:
  · CHARLAS   → INVITADOS: · MODERA: · LUGAR: · HORA:  (+ badge ENTRADA LIBRE)

Dos cosas que solo trae esta fuente y que el resto del onboarding necesita:

  · Los talleres publican RANGO horario («8:00 - 5:00pm») → duración real, no
    los 90 min por defecto que el dominio aplicaría. Y los que ocupan dos días
    lo dicen en el badge («LUNES 10 Y MARTES 11») → son UN bloque, is_recurring.
  · «CUPOS: 15, previa inscripción» → requires_registration. Las charlas, en
    cambio, llevan ENTRADA LIBRE impreso.
"""
import json, os, re, unicodedata, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OCR = f'{ST}/ficma-2026-franja-ocr.json'
OUT = f'{ST}/ficma-2026-franja.json'
ANIO = 2026
MES = 8
DIAS = 'LUNES|MARTES|MIÉRCOLES|MIERCOLES|JUEVES|VIERNES|SÁBADO|SABADO|DOMINGO'
ETIQUETAS = {'DIRECTOR': 'tallerista', 'DIRECTORA': 'tallerista', 'INVITADOS': 'invitados',
             'INVITADAS': 'invitados', 'INVITADO': 'invitados', 'MODERA': 'modera',
             'LUGAR': 'sede', 'HORA': 'hora', 'CUPOS': 'cupos'}


# Títulos que el OCR no recupera. Leídos del PDF a ojo y corregidos a mano:
# preferible una tabla explícita y auditable a forzar el parser con un caso.
TITULO_MANUAL = {
    # El OCR devolvió «Escribir con la camercena guion a la puesta en»: se comió
    # la segunda línea y fundió «cámara: Del» en una palabra inexistente.
    'fa-03.jpg': 'Escribir con la cámara: Del guion a la puesta en escena',
}


# Formularios de inscripción, del linktr.ee/ficma oficial (8 ago 2026). Van por
# TÍTULO del PDF, que es el nombre que manda (decisión de Juan): el linktree
# anuncia el taller de Franco Lolli como «Dirección de Actores» y el programa lo
# titula «De la realidad a la verdad» — mismo taller, mismo tallerista, mismas
# fechas. Se conserva el del programa.
#
# Un solo formulario cubre DOS talleres: el festival los plantea como
# alternativa —se elige uno— y así lo dice el propio form.
REGISTRO = {
    'Un sueño se hace realidad en 1 minuto':
        'https://docs.google.com/forms/d/e/1FAIpQLScQwx4mCGbX-JGI9Y6Tranmsa1C-yet1ZDFwF8MjxcoPBUraQ/viewform',
    'Cine en Movimiento: Taller Teórico-Práctico de Plano Secuencia':
        'https://docs.google.com/forms/d/e/1FAIpQLScQwx4mCGbX-JGI9Y6Tranmsa1C-yet1ZDFwF8MjxcoPBUraQ/viewform',
    'Escribir con la cámara: Del guion a la puesta en escena':
        'https://docs.google.com/forms/d/e/1FAIpQLSd07hqBATf6G3_k06cDOulhXe3cSSgveOjwPj0iEuHDCfQVEg/viewform',
    # Este es el enlace que publica el festival y Juan aprobó usarlo (8 ago).
    # Queda anotado que en una sesión anónima redirige a accounts.google.com en
    # vez de abrir el formulario: es una URL de edición (/forms/d/<id>/) y no la
    # pública (/forms/d/e/<hash>/viewform), como sí son las otras dos. Si algún
    # usuario reporta que le pide iniciar sesión, la causa es esta y se arregla
    # pidiéndole al festival el enlace de «Enviar → enlace».
    'De la realidad a la verdad':
        'https://docs.google.com/forms/d/1AS6rYYOERaPJz0nHi6pEamrpxn7aHza94goW0a6lU7c/viewform',
}

# Descripciones que el formulario oficial sí da y el PDF no.
SINOPSIS = {
    'Escribir con la cámara: Del guion a la puesta en escena':
        'Un espacio para reflexionar sobre la relación entre guion, dirección y lenguaje '
        'visual, y sobre cómo las decisiones de la puesta en escena pueden potenciar, '
        'transformar o incluso replantear aquello que estaba escrito.',
}


# La franja nombra las mismas sedes de otra manera —la trampa que en FICDEH
# duplicó funciones—. Se normaliza contra los nombres que ya usa la programación,
# con sala aparte cuando el nombre la lleva dentro.
SEDE_CANONICA = {
    'Sala Fundadores':                    ('Teatro los Fundadores', 'Sala Fundadores'),
    'Auditorio Colombo Americano':        ('Colombo', 'Auditorio'),
    'Universidad de Caldas - sede principal': ('Universidad de Caldas', 'Sede principal'),
    'Hall de la Secretaría de la Mujer y Equidad de Genero Orquídeas':
        ('Secretaría de la Mujer y Equidad de Género', 'Hall Orquídeas'),
    'Auditorio casa de Secretaria de Cultura':
        ('Casa de la Secretaría de Cultura', 'Auditorio'),
}


# Cambios que el festival anunció DESPUÉS de publicar el PDF. Van en tabla y no
# editando el crudo: el PDF sigue siendo la fuente y esto es la corrección
# encima, con su fecha, para que se vea qué cambió y cuándo.
CAMBIOS = {
    # Anunciado el 8 ago: la Master Class de Andrés Buitrago pasa del miércoles
    # 12 al jueves 13. El PDF y el propio formulario de inscripción todavía dicen
    # miércoles. Hora y sede se conservan —el anuncio solo habla del día— y
    # quedan por confirmar.
    'Escribir con la cámara: Del guion a la puesta en escena': {
        'dias': ['2026-08-13'],
        '_cambio': 'del miércoles 12 al jueves 13 — anunciado por el festival el 8 ago, '
                   'después del PDF. Hora (9:00) y sede sin confirmar: el aviso solo '
                   'mencionó el día.',
    },
}


def sinacento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').upper())
                   if unicodedata.category(c) != 'Mn')


def a24(h, m, ampm):
    h = int(h)
    if ampm == 'pm' and h != 12:
        h += 12
    if ampm == 'am' and h == 12:
        h = 0
    return f'{h:02d}:{int(m or 0):02d}'


def horas(txt):
    """«8:00 - 5:00pm» → ('08:00', 300 min). «11:00 am» → ('11:00', None).

    El am/pm suele venir SOLO al final del rango: en «8:00 - 5:00pm» las 8:00
    son de la mañana y las 5:00 de la tarde. Se resuelve por orden —si el fin
    queda antes que el inicio, el inicio era a.m.— y no asumiendo nada.
    """
    t = txt.lower().replace('.', '')
    r = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)?\s*[-–a]\s*(\d{1,2})[:.]?(\d{2})?\s*(am|pm)', t)
    if r:
        h1, m1, ap1, h2, m2, ap2 = r.groups()
        fin = a24(h2, m2, ap2)
        ini = a24(h1, m1, ap1 or ap2)
        if ini >= fin:                       # 8:00pm–5:00pm es imposible → era a.m.
            ini = a24(h1, m1, 'am')
        d = (int(fin[:2]) * 60 + int(fin[3:])) - (int(ini[:2]) * 60 + int(ini[3:]))
        return ini, (d if d > 0 else None)
    u = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(am|pm)', t)
    return (a24(*u.groups()) if u else ''), None


def main():
    d = json.load(open(OCR, encoding='utf-8'))
    out = []
    for pag in sorted(d, key=lambda k: int(re.search(r'(\d+)', k).group(1))):
        ls = sorted([l for l in d[pag] if l['w'] > l['h']], key=lambda l: l['y'])
        texto = ' '.join(l['t'] for l in ls)
        tipo = ('taller' if re.search(r'\bTALLERES\b', sinacento(texto)) else
                'charla' if re.search(r'\bCHARLAS\b', sinacento(texto)) else '')
        # Los días viven en el badge superior; «LUNES 10 Y MARTES 11» = dos sesiones.
        badge = ' '.join(l['t'] for l in ls if l['y'] < 0.09)
        dias = [f'{ANIO}-{MES:02d}-{int(x):02d}'
                for x in re.findall(rf'(?:{DIAS})\s+(\d{{1,2}})', sinacento(badge))]
        if not tipo or not dias:
            continue                          # portadas y contraportada

        # Título: el bloque entrecomillado del centro, puede ocupar 3 líneas.
        cab = ' '.join(l['t'] for l in ls if 0.12 < l['y'] < 0.33 and l['x'] < 0.75)
        mt = re.search(r'[“"«]\s*(.+?)\s*[”"»]', cab, re.S)
        titulo = TITULO_MANUAL.get(pag) or (re.sub(r'\s+', ' ', mt.group(1)) if mt else '')

        # Columna de datos: IZQUIERDA. Cada etiqueta toma las líneas hasta la
        # siguiente etiqueta de su columna.
        col = [l for l in ls if l['x'] < 0.45 and l['y'] > 0.30]
        es_etq = lambda t: ETIQUETAS.get(sinacento((re.match(r'^([A-ZÁÉÍÓÚÑ]+)\s*:', t.strip()) or [None, ''])[1]))
        campos = {}
        for i, l in enumerate(col):
            k = es_etq(l['t'])
            if not k:
                continue
            partes = [l['t'].split(':', 1)[1].strip()]
            for sig in col[i + 1:]:
                if es_etq(sig['t']):
                    break
                partes.append(sig['t'].strip())
            campos[k] = ' '.join(p for p in partes if p).strip()

        # La hora de un taller de dos días trae un rango POR día («Lunes 8:00 -
        # 5:00pm / Martes 8:00 - 5:00pm»); basta el primero: son iguales y el
        # bloque se modela como sesiones separadas del mismo taller.
        hora, dur = horas(campos.get('hora', ''))
        cupos = campos.get('cupos', '')
        mc = re.search(r'(\d+)', cupos)
        out.append({
            'pagina': pag, 'tipo': tipo, 'titulo': titulo, 'dias': dias,
            'hora': hora, 'duracion_min': dur,
            'sede': SEDE_CANONICA.get(campos.get('sede', ''), (campos.get('sede', ''), ''))[0],
            'sala': SEDE_CANONICA.get(campos.get('sede', ''), ('', ''))[1],
            '_sede_cruda': campos.get('sede', ''),
            'tallerista': campos.get('tallerista', ''),
            'invitados': campos.get('invitados', ''),
            'modera': campos.get('modera', ''),
            'cupos': int(mc.group(1)) if mc else None,
            'requires_registration': 'inscrip' in cupos.lower(),
            'entrada_libre': 'ENTRADA LIBRE' in sinacento(texto),
            'is_recurring': len(dias) > 1,
            'registration_url': REGISTRO.get(titulo, ''),
            'synopsis': SINOPSIS.get(titulo, ''),
        })

    for a in out:
        c = CAMBIOS.get(a['titulo'])
        if c:
            a['_dias_pdf'] = a['dias']
            a.update({k: v for k, v in c.items() if not k.startswith('_')})
            a['_cambio'] = c['_cambio']
            a['is_recurring'] = len(a['dias']) > 1

    json.dump({'_provenance': {
        'fuente': 'FICMA 17 - FRANJA ACADÉMICA.pdf — 15 páginas de imagen (posts de '
                  'Instagram), OCR con Vision (macOS)',
        'recibido': '2026-08-08',
        'que_aporta': 'las 12 actividades de la franja: 6 talleres y 6 charlas, con sede, '
                      'hora, duración real (los talleres publican rango), cupo e inscripción.',
    }, 'actividades': out}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{len(out)} actividades · talleres {sum(1 for x in out if x["tipo"]=="taller")} · '
          f'charlas {sum(1 for x in out if x["tipo"]=="charla")}')
    for x in out:
        print(f'  {x["tipo"]:7} {"·".join(y[-2:] for y in x["dias"]):6} {x["hora"] or "??":6} '
              f'{str(x["duracion_min"] or "—"):>4}min  {x["titulo"][:42]:44} {x["sede"][:22]:24}'
              f'{" INSCRIP" if x["requires_registration"] else ""}{" BLOQUE" if x["is_recurring"] else ""}')
    falta = [x['pagina'] for x in out if not (x['titulo'] and x['hora'] and x['sede'])]
    print(f'incompletas: {falta or "ninguna"}')
    sin_form = [x['titulo'][:38] for x in out if x['requires_registration'] and not x['registration_url']]
    print(f'piden inscripción y no publican formulario ({len(sin_form)}): {sin_form}')


if __name__ == '__main__':
    main()
