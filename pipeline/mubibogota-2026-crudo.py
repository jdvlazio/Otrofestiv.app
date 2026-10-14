#!/usr/bin/env python3
"""mubibogota-2026-crudo.py — MUBI Fest Bogotá 2026 (Gimnasio Moderno, 24–25 oct).

LA FUENTE: https://mubifest.com/es/bogota, guardada en
fuentes/mubibogota-2026/bogota.html (11 oct 2026). Es una app Nuxt: los datos
viajan en <script id="__NUXT_DATA__"> serializados con devalue (un arreglo plano
donde cada objeto apunta a los demás por índice). Se decodifica ese arreglo y se
leen los 16 eventos tal cual: título, crédito, hora local (richDate con zona
America/Bogota), duración, etiquetas, botón de acceso y descripción. Nada se
transcribe a mano.

EL ACCESO es el botón de cada función, verbatim:
  «ENTRADA LIBRE» / «ASISTE GRATIS» → entrada libre;
  «REGISTRO PRÓXIMAMENTE»            → libre con inscripción (aún sin formulario);
  «BOLETAS PRONTO»                   → desconocido: la venta no ha abierto, no se
                                       inventa precio ni gratuidad.

Escribe festivals/staging/mubibogota-2026-crudo.json
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance, DESCONOCIDO  # noqa: E402

URL = 'https://mubifest.com/es/bogota'
FUENTE = f'{REPO}/fuentes/mubibogota-2026/bogota.html'
OUT = f'{REPO}/festivals/staging/mubibogota-2026-crudo.json'
SEDE = 'Gimnasio Moderno'

ACCESO = {'ENTRADA LIBRE': 'Entrada libre', 'ASISTE GRATIS': 'Entrada libre',
          'REGISTRO PRÓXIMAMENTE': 'Entrada libre con inscripción previa',
          'BOLETAS PRONTO': DESCONOCIDO,
          # desde el 13 oct: la venta abrió en Entradas Inteligentes, enlace por función
          'COMPRAR BOLETAS': 'Con boleta'}
# la sección es la ETIQUETA del festival (no hay otra taxonomía en el sitio); si
# una obra lleva varias, manda la más específica, en este orden
SECCION_ORDEN = ['FOCO', 'RESTAURADA', 'ESTRENO MUBI', 'FUNCIÓN AL AIRE LIBRE']
# las cuatro que no son películas: su etiqueta y su clase de actividad
ACTIVIDAD = {
    'MUBI PODCAST ENCUENTROS: FERNANDO EIMBCKE & FRANCO LOLLI': ('Charla en vivo', 'charla'),
    'CAMP EN EL CINE: ENTRE EL EXCESO Y EL ARTIFICIO': ('Charla en vivo', 'charla'),
    'DESAFÍO SORPRESA CON LESLEY WOLF': ('Al aire libre', 'experiencia'),
    'MUBI LIBRARY': ('MUBI Library', 'experiencia'),
}
# TÍTULOS: el sitio los escribe en MAYÚSCULA SOSTENIDA (caja-sostenida); el
# publicado va en caja de frase, PROPUESTA a Juan (11 oct)
TITULO = {
    'ROSE': 'Rose',
    'PULP: ¿QUÉ HARÍAS POR UNA CANCIÓN MÁS?': 'Pulp: ¿Qué harías por una canción más?',
    'LAS AVENTURAS DE PRISCILLA, REINA DEL DESIERTO': 'Las aventuras de Priscilla, reina del desierto',
    'ADOLESCENCIA, SEXO Y MUERTE EN CAMPAMENTO MIASMA': 'Adolescencia, sexo y muerte en Campamento Miasma',
    'TIERRA DE MI PADRE': 'Tierra de mi padre',
    'LA NIÑA SANTA': 'La niña santa',
    'MOSCAS': 'Moscas',
    'VOILÀ VARDA: CORTOMETRAJES DE AGNÈS VARDA': 'Voilà Varda: cortometrajes de Agnès Varda',
    'LA COSA': 'La cosa',
    'THELMA & LOUISE': 'Thelma & Louise',
    'COBARDE': 'Cobarde',
    'LA PAGA': 'La paga',
    'MUBI PODCAST ENCUENTROS: FERNANDO EIMBCKE & FRANCO LOLLI': 'MUBI Podcast Encuentros: Fernando Eimbcke & Franco Lolli',
    'CAMP EN EL CINE: ENTRE EL EXCESO Y EL ARTIFICIO': 'Camp en el cine: entre el exceso y el artificio',
    'DESAFÍO SORPRESA CON LESLEY WOLF': 'Desafío sorpresa con Lesley Wolf',
    'MUBI LIBRARY': 'MUBI Library',
}
SECCION_PUBLICADA = {'FOCO': 'Foco', 'RESTAURADA': 'Restaurada', 'ESTRENO MUBI': 'Estreno MUBI',
                     'FUNCIÓN AL AIRE LIBRE': 'Función al aire libre'}
# lo que la tarjeta dice de quién acompaña (el `eyebrow` o el subtítulo), en caja
# de frase; los subtítulos que son reclamo («GANA MERCH…») no son invitados
INVITADOS = {
    'MOSCAS': 'Q&A con el director',
    # «COMMON PEOPLE: MÚSICA PARA OUTSIDERS» — «El DJ Alejandro Marín», «Duración DJ set: 45 min»
    'PULP: ¿QUÉ HARÍAS POR UNA CANCIÓN MÁS?': 'DJ set de Alejandro Marín (45 min)',
    'LA PAGA': 'Q&A con Vladimir Durán y Pedro Adrián Zuluaga',
    'TIERRA DE MI PADRE': 'Epílogo sonoro con Julio Victoria',
    'CAMP EN EL CINE: ENTRE EL EXCESO Y EL ARTIFICIO': 'Con Vanessa Rosales, Felipe Cuéllar, Jimmy Rangel y Andrés Suárez',
}
DIRECTOR = {'ROSE': 'Markus Schleinzer', 'PULP: ¿QUÉ HARÍAS POR UNA CANCIÓN MÁS?': 'Garth Jennings',
            'LAS AVENTURAS DE PRISCILLA, REINA DEL DESIERTO': 'Stephan Elliott',
            'ADOLESCENCIA, SEXO Y MUERTE EN CAMPAMENTO MIASMA': 'Jane Schoenbrun',
            'TIERRA DE MI PADRE': 'Paweł Pawlikowski', 'LA NIÑA SANTA': 'Lucrecia Martel',
            'MOSCAS': 'Fernando Eimbcke', 'VOILÀ VARDA: CORTOMETRAJES DE AGNÈS VARDA': 'Agnès Varda',
            'LA COSA': 'John Carpenter', 'THELMA & LOUISE': 'Ridley Scott',
            'COBARDE': 'Lukas Dhont', 'LA PAGA': 'Ciro Durán'}


def nuxt(s):
    a = json.loads(re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', s, re.S).group(1))
    memo = {}

    def r(i):
        if i in memo:
            return memo[i]
        v = a[i]
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ('Reactive', 'ShallowReactive', 'Ref', 'ShallowRef'):
                out = r(v[1])
            else:
                out = [r(x) if isinstance(x, int) else x for x in v]
        elif isinstance(v, dict):
            out = {k: (r(x) if isinstance(x, int) else x) for k, x in v.items()}
        else:
            out = v
        memo[i] = out
        return out
    return [r(i) for i, v in enumerate(a) if isinstance(v, dict) and 'screenings' in v and 'title' in v]


def texto(bloques):
    return '\n'.join(t for t in (''.join(c.get('text', '') for c in b.get('children', []) if isinstance(c, dict))
                                 for b in bloques or [] if isinstance(b, dict)) if t.strip())


def main():
    eventos = nuxt(io.open(FUENTE, encoding='utf-8').read())
    if len(eventos) != 16:
        sys.exit(f'✗ la página trae {len(eventos)} eventos, no 16: revisar antes de seguir')
    funciones = []
    for e in eventos:
        t = html.unescape(e['title']).strip()
        etiquetas = [x.upper() for x in (e.get('labels') or []) if isinstance(x, str)]
        desc = texto(e.get('description'))
        for s in e['screenings']:
            loc = s['time']['local']               # «2026-10-24T14:30:00-05:00»
            if not loc.endswith('-05:00'):
                sys.exit(f'✗ {t}: hora fuera de la zona de Bogotá ({loc})')
            reg = {'titulo': TITULO[t], 'titulo_fuente': t, 'dia': loc[:10], 'hora': loc[11:16],
                   'sede': SEDE, 'acceso': ACCESO[s['button'].strip()],
                   **({'ticket_url': s['url']} if s.get('url') else {}),
                   '_src': {'url': URL, 'date': '2026-10-14', 'boton': s['button'].strip()}}
            dur = re.match(r'\s*(\d+)', e.get('duration') or '')
            if dur:
                reg['duracion_min'] = int(dur.group(1))
            if t in ACTIVIDAD:
                sec, kind = ACTIVIDAD[t]
                reg.update(tipo='evento', event_kind=kind, seccion=sec)
                # MUBI Library es un ESPACIO abierto los dos días («oct 24 - oct 25»,
                # desde la 1 p. m., sin duración): se visita, no se agenda (info:true)
                if t == 'MUBI LIBRARY':
                    reg['info'] = True
            else:
                reg['director'] = DIRECTOR[t]
                reg['seccion'] = SECCION_PUBLICADA[next(x for x in SECCION_ORDEN if x in etiquetas or (e.get('eyebrow') or '').upper() == x)]
                if 'Q&A' in etiquetas:
                    reg['has_qa'] = True
            if t in INVITADOS:
                reg['invitados'] = INVITADOS[t]
            # lo que dice la prosa de cada tarjeta (lectura A, 14 oct): el estreno
            # («PREMIERE EN COLOMBIA») y que TODO el festival es para mayores de 18
            # LA SALA (lectura C, 14 oct): la boletería de Entradas Inteligentes pone
            # las seis funciones pagas en el «Auditorio Gimnasio Moderno»; las que la
            # tarjeta marca «al aire libre», afuera. Las demás no lo dicen
            if s.get('url'):
                reg['sala'] = 'Auditorio'
            elif any('AIRE LIBRE' in x for x in etiquetas) or 'AIRE LIBRE' in (e.get('eyebrow') or '').upper():
                reg['sala'] = 'Al aire libre'
            if 'PREMIERE EN COLOMBIA' in (e.get('eyebrow') or '').upper():
                reg['premiere'] = 'Premiere en Colombia'
            if re.search(r'mayores de 18', desc or '', re.I):
                reg['clasificacion'] = 'Para mayores de 18 años'
            if desc:
                reg['sinopsis'] = desc.split('\n')[0]
            funciones.append(reg)
    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(URL, metodo='__NUXT_DATA__ de mubifest.com (devalue), 16 eventos'),
        'funciones': funciones}, ensure_ascii=False, indent=1))
    print(f'✓ {len(funciones)} funciones · {sum(1 for f in funciones if f.get("tipo") == "evento")} actividades → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
