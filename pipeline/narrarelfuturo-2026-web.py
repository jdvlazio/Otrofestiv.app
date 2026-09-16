# -*- coding: utf-8 -*-
"""narrarelfuturo.com/programa-2026/ → crudo de #NarrarElFuturo.

FUENTE PRIMARIA. La página trae la programación oficial completa —día, hora,
sala, sede, dirección, género, duración, sinopsis y la frase de acceso— para
los seis días, incluidos el 15 y el 20 que la Cinemateca no cubre, y las sedes
que no son suyas (Universidad Jorge Tadeo Lozano).

NO ESTABA ENLAZADA EN EL MENÚ del sitio (solo #Inicio, #Talleres,
#HackathonVR360, #Invitados, #NEF), así que un barrido de la home no la
encuentra. La pasó Juan. Queda escrita acá para que el próximo no la busque.

La Cinemateca (narrarelfuturo-2026-cinemateca.py) queda como CORROBORACIÓN: dos
fuentes independientes para las mismas 8 funciones de sus salas.

LA UNIDAD ES LA TARJETA, no la línea. Cada función es un `<div class="…
evento-card …">` y ahí dentro va TODO: día, hora, título, «País · Año ·
Duración · Género», sinopsis, dirección, sala, sede y la frase de acceso. Las 24
están en el HTML servido, así que esto no necesita navegador.

Dos trampas que costaron dos versiones de este parser, y las dos eran mías:

  · APLANAR LA PÁGINA EN LÍNEAS Y DEDUPLICAR. Heredé el `dict.fromkeys` de los
    snippets con que exploré la página; en un parser destruye la estructura,
    porque «4:00pm» se repite cada día. Salían 5 funciones de 24 y un solo día.
  · `L.index(x)` PARA MIRAR LA LÍNEA ANTERIOR. Devuelve la PRIMERA aparición,
    no la actual, y en esta página los títulos y las fichas se repiten.

Y una trampa que es DEL SITIO, no mía: las 24 tarjetas llevan la clase
`dia-15`, incluidas las que dicen «Jue 17» en su propio texto. El filtro por día
de su web está roto. El día se lee del TEXTO de la tarjeta; la clase se ignora.
"""
import io, json, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
from lib import provenance, UA

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
SALIDA = f'{ST}/narrarelfuturo-2026-crudo.json'
URL = 'https://narrarelfuturo.com/programa-2026/'

DIAS = {'15': '2026-09-15', '16': '2026-09-16', '17': '2026-09-17',
        '18': '2026-09-18', '19': '2026-09-19', '20': '2026-09-20'}
# El día viene en formas MEZCLADAS —«Martes 15», «Mié 16», «Jueves 17»—, así que
# se acepta cualquier prefijo de día y manda el número. Una primera versión solo
# aceptaba la abreviatura de tres letras y descartó 19 de las 24 tarjetas.
RE_DIA = re.compile(r'^(?:Lun|Mar|Mié|Mie|Jue|Vie|Sáb|Sab|Dom)[a-zé]*\s+(\d{1,2})$', re.I)
RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap])m$', re.I)
# «Chile · 2025 · 1h 33min · Documental, Experimental»
RE_FICHA = re.compile(
    r'^(?P<pais>[^·]+?)\s*·\s*(?P<anio>(?:19|20)\d\d)\s*·\s*(?P<dur>[^·]+?)\s*(?:·\s*(?P<gen>.+))?$')


def lineas(bloque):
    """Las líneas de UNA tarjeta, en orden y sin deduplicar."""
    import html as _h
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', bloque, flags=re.S)
    t = _h.unescape(re.sub(r'<[^>]+>', '\n', t).replace('&nbsp;', ' '))
    return [x.strip() for x in t.split('\n') if x.strip()]


def tarjetas(h):
    return re.split(r'(?=<div class="[^"]*evento-card)', h)[1:]


def minutos(s):
    """«1h 33min» → 93 · «26 min 28s» → 26 · «11 min23s» → 11 · «14 min» → 14.
    Los segundos se DESCARTAN, no se redondean: la app muestra minutos y una
    obra de 26 min 28 s no dura 27. Ese medio minuto inventado se acumula en la
    suma de un programa de diez cortos."""
    s = s.strip()
    m = re.match(r'^(\d+)\s*h\s*(\d+)?\s*min', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    m = re.match(r'^(\d+)\s*min', s)
    return int(m.group(1)) if m else None


def bajar():
    p = f'{CACHE}/programa-2026.html'
    if os.path.exists(p) and os.path.getsize(p) > 100000:
        return io.open(p, encoding='utf-8', errors='replace').read()
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(['curl', '-sL', '--max-time', '60', '-A', UA, URL, '-o', p], check=True)
    return io.open(p, encoding='utf-8', errors='replace').read()


def una(L):
    """Una tarjeta → una función del formato intermedio."""
    f = {'obras': [], '_src': URL}
    for k, x in enumerate(L):
        m = RE_DIA.match(x)
        if m and not f.get('dia'):
            f['dia'] = DIAS.get(m.group(1))
            continue
        m = RE_HORA.match(x)
        if m and not f.get('hora'):
            hh = int(m.group(1)) % 12 + (12 if m.group(3).lower() == 'p' else 0)
            f['hora'] = f'{hh:02d}:{m.group(2)}'
            continue
        mf = RE_FICHA.match(x)
        if mf and minutos(mf.group('dur')) is not None:
            prev = L[k - 1] if k else ''
            ficha = {'pais': mf.group('pais').strip(), 'anio': int(mf.group('anio')),
                     'duracion_min': minutos(mf.group('dur')),
                     'genero': (mf.group('gen') or '').strip()}
            if prev.startswith('Dir.'):
                # obra dentro de un programa: «Título / Dir. Nombre / ficha»
                ficha['director'] = re.sub(r'^Dir\.\s*(Dir\.\s*)?', '', prev).strip()
                ficha['titulo'] = L[k - 2] if k >= 2 else ''
                f['obras'].append(ficha)
            elif not f.get('titulo'):
                f['titulo'] = prev
                f.update(ficha)
            else:
                f['obras'].append({**ficha, 'titulo': prev})
            continue
        if x == 'Dir.' and k + 1 < len(L) and not f.get('director'):
            # en un largo la etiqueta va SOLA y el nombre en la línea siguiente
            f['director'] = L[k + 1]
        elif re.match(r'^\*?\s*Entrada', x, re.I):
            f.setdefault('acceso', x.lstrip('*').strip())
        elif re.match(r'^\.?\s*Sala\b', x):
            f.setdefault('sala', x.lstrip('. ').rstrip(',').strip())
        elif x.rstrip(',') in ('Cinemateca de Bogotá', 'Universidad Jorge Tadeo Lozano',
                               'Cinemateca Fontanar del Río'):
            f.setdefault('sede', x.rstrip(','))
    f.setdefault('sede', '')
    f.setdefault('sala', '')
    f.setdefault('acceso', lib.DESCONOCIDO)
    if not f['obras']:
        del f['obras']
    return f


def main():
    h = bajar()
    funciones = [una(lineas(b)) for b in tarjetas(h)]
    sin_dia = [f for f in funciones if not f.get('dia') or not f.get('hora') or not f.get('titulo')]
    funciones = [f for f in funciones if f.get('dia') and f.get('hora') and f.get('titulo')]

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        URL,
        metodo='tarjetas .evento-card del HTML servido; el día se lee del texto de cada tarjeta',
        nota='la web del festival etiqueta las 24 tarjetas con la clase dia-15: su filtro por día está roto y la clase no sirve'),
        '_funciones': len(funciones),
        '_obras': sum(len(x.get('obras') or []) for x in funciones),
        'funciones': funciones},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {SALIDA}')
    for x in sorted(funciones, key=lambda y: (y['dia'], y['hora'])):
        print(f"  {x['dia'][-5:]} {x['hora']}  {x['titulo'][:34]:36} "
              f"{(x.get('sala') or '—')[:16]:18} {(x['sede'] or '—')[:28]:30} "
              f"{len(x.get('obras') or []) or '':>2}  {x['acceso'][:30]}")
    import collections
    print(f"\n{len(funciones)} funciones · {sum(len(x.get('obras') or []) for x in funciones)} obras en programas")
    print('días:', dict(sorted(collections.Counter(x['dia'][-2:] for x in funciones).items())))
    if sin_dia:
        print(f'  ⚠ {len(sin_dia)} tarjeta(s) sin día/hora/título — mirar a mano')


if __name__ == '__main__':
    main()
