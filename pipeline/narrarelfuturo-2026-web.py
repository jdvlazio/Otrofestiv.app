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
# CADA PARSER ESCRIBE SU PROPIO SIDECAR. La primera versión de los dos parsers
# de este festival escribía `-crudo.json`, y el segundo que corriera borraba al
# primero: perdí 8 funciones y 27 obras de la Cinemateca sin un solo error en
# pantalla. El crudo lo arma el paso de fusión, que es el único con derecho a
# escribirlo.
SALIDA = f'{ST}/narrarelfuturo-2026-web.json'
SALIDA_VR = f'{ST}/narrarelfuturo-2026-vr.json'

# Etiquetas con que el festival encabeza cada tarjeta. Son SUYAS y se pasan tal
# cual (PROTOCOLO §5: la palabra la pone el festival). Sirven además para saber
# si la 3ª línea es etiqueta o ya es el título: la clausura no lleva etiqueta.
SEDES_CONOCIDAS = ('Cinemateca de Bogotá', 'Universidad Jorge Tadeo Lozano',
                   'Cinemateca Fontanar del Río')

ETIQUETAS = ('Largometraje', 'Cortos', 'RT Meet The Creators', 'Taller',
             'Conversatorio', 'Masterclass', 'Instalación VR Activa')
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
    """«1h 33min» → 93 · «26 min 28s» → 26 · «14 min» → 14.

    Los segundos se REDONDEAN, no se descartan. La primera versión los
    descartaba con un razonamiento que sonaba bien —«26 min 28 s no dura 27»— y
    era falso en agregado: 34 obras llevan segundos y truncarlas se comía 18
    minutos del catálogo. Lo decidió el dato, no el argumento: las duraciones
    que el festival declara por programa (83, 87, 91 min) cuadran con la suma
    REDONDEADA, y la agenda de la Cinemateca —fuente independiente— publica esas
    mismas obras ya redondeadas al minuto."""
    s = s.strip()
    m = re.match(r'^(\d+)\s*h\s*(\d+)?\s*min', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    m = re.match(r'^(\d+)\s*min\s*(\d+)\s*s', s)
    if m:
        return int(m.group(1)) + (1 if int(m.group(2)) >= 30 else 0)
    m = re.match(r'^(\d+)\s*min', s)
    return int(m.group(1)) if m else None


def bajar():
    p = f'{CACHE}/programa-2026.html'
    if os.path.exists(p) and os.path.getsize(p) > 100000:
        return io.open(p, encoding='utf-8', errors='replace').read()
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(['curl', '-sL', '--max-time', '60', '-A', UA, URL, '-o', p], check=True)
    return io.open(p, encoding='utf-8', errors='replace').read()


def enlaces(bloque):
    """Los href de la tarjeta, por lo que dice su texto. La lección de
    CineAutopsia: los seis enlaces de TuBoleta estaban en la fuente y no
    llegaron al JSON porque nadie los buscó. Acá el festival no escribe
    «Entrada…» en todas: dice «Inscribirse Aquí» o «Compra tu boleta aquí», y
    el enlace es el dato que hace accionable la casilla."""
    out = {}
    # La ventana tiene que ser ANCHA: el <a> de Elementor mete ~180 caracteres
    # de spans anidados entre el href y el texto, y con 120 no casaba ninguno
    # —devolvía cero enlaces sin fallar—.
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.{0,600}?)</a>', bloque, re.S):
        txt = re.sub(r'<[^>]+>', '', m.group(2)).strip().lower()
        if 'inscrib' in txt:
            out.setdefault('registration_url', https(m.group(1)))
        elif 'boleta' in txt or 'compra' in txt:
            out.setdefault('ticket_url', https(m.group(1)))
    return out


def https(u):
    """El contrato exige ^https:// y el festival publica su bit.ly en http.
    Verificado el 15 sep 2026: https://bit.ly/RTElFuturo responde 301 al mismo
    formulario. Es el MISMO recurso, no otro — por eso se normaliza el esquema y
    no se cambia el enlace."""
    return re.sub(r'^http://', 'https://', u)


def una(L, bloque=''):
    """Una tarjeta de FUNCIÓN → una función del formato intermedio."""
    f = {'dia': DIAS.get(RE_DIA.match(L[0]).group(1)), 'obras': [], '_src': URL}
    hh = RE_HORA.match(L[1])
    f['hora'] = f"{int(hh.group(1)) % 12 + (12 if hh.group(3).lower() == 'p' else 0):02d}:{hh.group(2)}"
    # 3ª línea: etiqueta del festival, o ya el título si la tarjeta no la lleva
    # (la clausura). No se inventa una etiqueta para las que no la tienen.
    if L[2] in ETIQUETAS or L[2].startswith('Cortos'):
        f['event_kind'] = L[2].split(' ·')[0]
        f['titulo'] = L[3] if len(L) > 3 else L[2]
        resto = 4
    else:
        f['titulo'] = L[2]
        resto = 3
    # «Cortos · Nombre del programa» → el nombre del programa ES el título
    if f['titulo'].startswith('Cortos ·'):
        f['titulo'] = f['titulo'].split('·', 1)[1].strip()
        f['es_programa'] = True

    for k in range(resto, len(L)):
        x = L[k]
        mf = RE_FICHA.match(x)
        if mf and minutos(mf.group('dur')) is not None:
            ficha = {'pais': mf.group('pais').strip(), 'anio': int(mf.group('anio')),
                     'duracion_min': minutos(mf.group('dur')),
                     'genero': (mf.group('gen') or '').strip()}
            prev = L[k - 1]
            if prev.startswith('Dir.'):
                ficha['director'] = re.sub(r'^Dir\.\s*', '', prev).strip()
                ficha['titulo'] = L[k - 2]
                f['obras'].append(ficha)
            elif not f.get('anio'):
                f.update(ficha)
            else:
                f['obras'].append({**ficha, 'titulo': prev})
        elif x == 'Dir.' and k + 1 < len(L) and not f.get('director'):
            f['director'] = L[k + 1]
        elif re.match(r'^\*?\s*Entrada', x, re.I):
            f.setdefault('acceso', x.lstrip('*').strip())
        elif re.match(r'^\.?\s*(Sala|Hemiciclo|Aula|Laboratorio)\b', x):
            f.setdefault('sala', x.lstrip('. ').rstrip(',').strip())
        else:
            # La sede no siempre viene sola en su línea: a veces llega como
            # «, Universidad Jorge Tadeo Lozano, Cra. 4 #22-61», con coma
            # delante y la dirección detrás. Se busca CONTENIDA, no igual.
            for sede in SEDES_CONOCIDAS:
                if sede in x:
                    f.setdefault('sede', sede)
                    break
    f.update(enlaces(bloque))
    # La palabra del festival manda; si no escribió «Entrada…» la deduce el
    # enlace que SÍ publicó, y se dice cuál de las dos cosas es.
    if not f.get('acceso'):
        if f.get('registration_url'):
            f['acceso'] = 'Entrada gratis con inscripción'
        elif f.get('ticket_url'):
            f['acceso'] = 'Boletería'
        else:
            f['acceso'] = lib.DESCONOCIDO
    f.setdefault('sede', '')
    f.setdefault('sala', '')
    if not f['obras']:
        del f['obras']
    return f


def vr(L):
    """Una tarjeta de la INSTALACIÓN VR → una obra. No son funciones: la
    instalación está abierta en bloque (15–18 de 2 a 6, 19–20 de 11 a 6) y sus
    ocho obras no tienen hora propia. Meterlas como funciones habría inventado
    dieciséis horarios que el festival no publica."""
    o = {'titulo': L[0], '_src': URL}
    for k, x in enumerate(L):
        mf = RE_FICHA.match(x)
        if mf and minutos(mf.group('dur')) is not None:
            o.update({'pais': mf.group('pais').strip(), 'anio': int(mf.group('anio')),
                      'duracion_min': minutos(mf.group('dur')),
                      'genero': (mf.group('gen') or '').strip()})
        elif x == 'Dir.' and k + 1 < len(L):
            o.setdefault('director', L[k + 1])
        elif len(x) > 110 and not o.get('sinopsis'):
            o['sinopsis'] = x
    return o


def main():
    h = bajar()
    funcs, vrs = [], []
    for b in tarjetas(h):
        L = lineas(b)
        if len(L) > 1 and RE_DIA.match(L[0]) and RE_HORA.match(L[1]):
            funcs.append(una(L, b))
        else:
            vrs.append(vr(L))

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        URL, metodo='tarjetas .evento-card del HTML servido; el día se lee del TEXTO de cada tarjeta',
        nota='la web etiqueta las 24 tarjetas con la clase dia-15 —su filtro por día está roto— así que la clase no sirve'),
        '_funciones': len(funcs), '_obras': sum(len(x.get('obras') or []) for x in funcs),
        'funciones': funcs},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({'_provenance': provenance(
        URL, metodo='tarjetas sin día/hora de la misma página',
        nota='obras de la instalación VR: abierta en bloque, sin hora por obra'),
        '_obras': len(vrs), 'obras': vrs},
        io.open(SALIDA_VR, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'── {os.path.basename(SALIDA)} · {len(funcs)} funciones · '
          f"{sum(len(x.get('obras') or []) for x in funcs)} obras en programas")
    for x in sorted(funcs, key=lambda y: (y['dia'], y['hora'])):
        print(f"  {x['dia'][-5:]} {x['hora']}  {x['titulo'][:32]:34} "
              f"{(x.get('event_kind') or '—')[:20]:22} {(x.get('sala') or '—')[:16]:18} "
              f"{(x['sede'] or '—')[:26]:28} {len(x.get('obras') or []) or '':>2}")
    import collections
    print('  días:', dict(sorted(collections.Counter(x['dia'][-2:] for x in funcs).items())))
    print(f'── {os.path.basename(SALIDA_VR)} · {len(vrs)} obras de la instalación VR')
    for o in vrs:
        print(f"  {o['titulo'][:34]:36} {(o.get('director') or '—')[:22]:24} "
              f"{(o.get('pais') or '—')[:18]:20} {o.get('duracion_min','—')} min")


if __name__ == '__main__':
    main()
