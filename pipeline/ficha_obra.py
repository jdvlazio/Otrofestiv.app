#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficha_obra.py — LA REGLA de cada campo de una obra. Un dato entra por lista o por forma, o no entra.

POR QUÉ (Juan, 24 nov 2026): «no puede ser que en una lista de países del mundo
puedas poner otro dato». Se publicó «Qatar» como género y nadie lo vio, porque
ningún campo tenía dueño. La obra es la película, verificada; el festival solo
agrega la función y el lugar. Acá vive qué es válido en cada campo; que sea
VERDAD se verifica con su fuente (identidad), y que sea el MISMO en todos los
festivales, en obra_unica.py.

TRINQUETE: lo que hoy incumple está anotado en pipeline/ficha-deuda.json por
festival, regla, obra y VALOR (huella). Solo se quita: un dato malo nuevo no se
tapa arreglando otro, ni cambiando uno malo por otro malo. Un festival nuevo
parte de cero.

    python3 pipeline/ficha_obra.py [<festival>]     # qué incumple
    python3 pipeline/ficha_obra.py --congelar       # la deuda (solo si BAJÓ)
"""
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
DEUDA = os.path.join(REPO, 'pipeline', 'ficha-deuda.json')

# Lista cerrada, aprobada por Juan el 24 nov 2026. VR o IA son formato, no género.
GENEROS = ('Acción', 'Animación', 'Aventura', 'Bélica', 'Ciencia ficción', 'Comedia', 'Crimen', 'Documental',
           'Documental híbrido', 'Drama', 'Experimental', 'Familia', 'Fantasía', 'Historia', 'Misterio', 'Música',
           'Musical', 'Romance', 'Suspenso', 'Terror', 'Western')
# El nombre que se lee acá, donde el de la lista ISO (CLDR) es otro
NOMBRE = {'PS': 'Palestina', 'HK': 'Hong Kong', 'CZ': 'República Checa', 'RO': 'Rumania', 'SA': 'Arabia Saudita',
          'BD': 'Bangladesh', 'CD': 'República Democrática del Congo', 'CI': 'Costa de Marfil', 'MO': 'Macao', 'MM': 'Myanmar'}
# códigos de la tabla que no son un país (pseudoidiomas, agrupaciones, islas sin código propio)
NO_PAIS = {'XA', 'XB', 'EU', 'EZ', 'UN', 'QO', 'EA', 'IC', 'AC', 'TA', 'DG', 'CP', 'CQ'}
# nombres propios que llevan «e» o «&»: no separan personas
NOMBRE_COMPUESTO = ('Inês Pedrosa e Melo', 'Colectivo Pix & Hertz')
_NO_NOMBRE = re.compile(r'(?i)^(varios|varias|n/?a|por confirmar|tba|tbd|desconocid[oa]s?|null|none|undefined)$')
_PENDIENTE = re.compile(r'(?i)\b(sinopsis no disponible|pr[oó]ximamente|por confirmar|lorem ipsum|synopsis (not available|coming soon)|no synopsis)\b')
_AFICHE = re.compile(r'^(https://\S+|data:image/\S+|/[A-Za-z0-9]{20,}\.(?:jpe?g|png|webp))$')
HISTORICOS = ('URSS', 'Yugoslavia', 'Checoslovaquia')      # sin código vigente
EN_CURSO = 1                                               # la del año próximo es posible; más allá, no
_CARGO = re.compile(r'(?i)^(direcci[oó]n|dirigid[oa]|dir\.?|director[ae]?s?|realizaci[oó]n|cura)\b\s*[:.]?\s')
_SEPARADOR = re.compile(r'\s(?:y|e|and|&|\+|-|–)\s|/|;|·|\||,(?! )|,\s*$')
_FESTIVAL_EN = re.compile(r"(?i)\bTIFF\b|\bwinner of\b|\bpalme d.or\b|\bun certain regard\b|\bworld premiere\b|\bofficial selection\b|\bfestival jury\b")
_CIERRE = re.compile(r'[.!?…][»”"’\')\]]*$|[»”"’]\.?$')
_EN = set('the of and to in is his her with from that their for by on as who an when she he they at it'.split())
_OTROS = {'español': set('el los las una del que con por para su sus como más sin entre cuando'.split()),
          'francés': set('le les des une est et dans qui pour avec sur aux son ses'.split()),
          'portugués': set('uma um dos das não em com seu sua ele ela ao pela'.split())}


def paises():
    iso = json.load(open(os.path.join(REPO, 'pipeline', 'paises.json'), encoding='utf-8'))['iso']
    return {NOMBRE.get(k, v['es']) for k, v in iso.items() if k not in NO_PAIS} | set(HISTORICOS)


def _texto(s):
    """Lo común a los textos que se leen."""
    out = []
    if not _CIERRE.search(s.strip()):
        out.append('cierre')
    if s != s.strip() or re.search(r'\s{2,}|[\n\t​]', s):
        out.append('espacios')
    return out


def revisar(o, nombres=None, anio_tope=None):
    """Una obra publicada → ['campo:regla', …]. Vacío = cumple. Un campo vacío no incumple."""
    import datetime
    from sinopsis_unicas import defectos, _EVENTO, _ROTO
    nombres = nombres or paises()
    tope = anio_tope or datetime.date.today().year + EN_CURSO
    out = []
    c = o.get('country')
    if c not in (None, '') and (not isinstance(c, str) or any(x not in nombres for x in c.split(', ')) or len(set(c.split(', '))) < len(c.split(', '))):
        out.append('país:fuera de lista')
    g = o.get('genre')
    if g not in (None, '') and g not in GENEROS:
        out.append('género:fuera de lista')
    y = o.get('year')
    if y not in (None, ''):
        if type(y) is not int:
            out.append('año:no es número')
        elif not 1888 <= y <= tope:
            out.append('año:imposible')
    d = o.get('director')
    if d not in (None, ''):
        if not isinstance(d, str):
            out.append('director:no es texto')
        else:
            if _CARGO.search(d):
                out.append('director:cargo')
            if any(_SEPARADOR.search(x) for x in [', '.join(y for y in d.split(', ') if y not in NOMBRE_COMPUESTO)]):
                out.append('director:separador')
            if d != d.strip() or re.search(r'\s{2,}|@|https?:|[()<>]', d) or re.search(r'[a-záéíóúñ]{3,}\.$', d) \
                    or any(not re.search(r'[^\W\d_]', x) or x in nombres or _NO_NOMBRE.match(x) for x in d.split(', ') if x):
                out.append('director:basura')
    s = o.get('synopsis_es') or o.get('synopsis')
    if s not in (None, ''):
        if not isinstance(s, str):
            out.append('sinopsis:no es texto')
        else:
            out += ['sinopsis:' + x for x in defectos(s) + _texto(s)]
            if len(s) < 120 and _PENDIENTE.search(s):
                out.append('sinopsis:pendiente')
            ws = re.findall(r'[^\W\d_]+', s.lower())
            fr = sum(w in _OTROS['francés'] - {'le', 'les', 'son', 'sur'} for w in ws)     # también son español
            if len(ws) >= 8 and fr > sum(w in _OTROS['español'] for w in ws):
                out.append('sinopsis:en francés')
            if o.get('synopsis_lang') not in (None, 'es') and not o.get('synopsis_es'):
                out.append('sinopsis:marcada en otro idioma')
    e = o.get('synopsis_en')
    if e not in (None, ''):
        if not isinstance(e, str):
            out.append('sinopsis en inglés:no es texto')
        else:
            ws = re.findall(r'[^\W\d_]+', e.lower())
            n = max(1, len(ws))
            en = sum(w in _EN for w in ws) / n
            if len(ws) >= 4 and any(sum(w in S for w in ws) / n > en for S in _OTROS.values()):
                out.append('sinopsis en inglés:otro idioma')
            if len(ws) < 4 or _PENDIENTE.search(e):
                out.append('sinopsis en inglés:no cuenta la obra')
            if _ROTO.search(e):
                out.append('sinopsis en inglés:texto roto')
            if _FESTIVAL_EN.search(e) or _EVENTO.search(e):
                out.append('sinopsis en inglés:habla del festival')
            out += ['sinopsis en inglés:' + x for x in _texto(e)]
    u = o.get('duration')
    if u not in (None, '') and not (isinstance(u, str) and re.fullmatch(r'[1-9]\d{0,2} min', u) and int(u.split()[0]) <= 900):
        out.append('duración:forma')
    l = o.get('lbSlug')
    if l not in (None, '') and (str(l) in ('null', 'none', 'undefined') or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', str(l))):
        out.append('letterboxd:forma')
    t = o.get('tmdb_id')
    if t not in (None, '') and not (type(t) is int and t > 0):
        out.append('tmdb:no es número')
    p = o.get('poster')
    if p not in (None, ''):
        if isinstance(p, str) and re.match(r'/?assets/', p):
            if not os.path.isfile(os.path.join(REPO, p.lstrip('/'))):
                out.append('afiche:no existe')
        elif not (isinstance(p, str) and _AFICHE.match(p)):
            out.append('afiche:forma')
    ti = o.get('title')
    if not isinstance(ti, str) or not ti.strip() or re.fullmatch(r'(?i)n/a|null|none|undefined|sin t[ií]tulo\?', ti.strip()):
        out.append('título:falta')
    elif ti != ti.strip() or re.search(r'\s{2,}|[\n\t\u200b]', ti):
        out.append('título:espacios')
    return out


CAMPO = {'país': 'country', 'género': 'genre', 'año': 'year', 'director': 'director', 'sinopsis en inglés': 'synopsis_en',
         'duración': 'duration', 'letterboxd': 'lbSlug', 'tmdb': 'tmdb_id', 'afiche': 'poster', 'título': 'title'}


def _huella(o, regla):
    import hashlib
    k = regla.split(':')[0]
    v = (o.get('synopsis_es') or o.get('synopsis'), o.get('synopsis_lang')) if k == 'sinopsis' else o.get(CAMPO[k])
    return hashlib.sha1(json.dumps(v, ensure_ascii=False, default=str).encode()).hexdigest()[:8]


def incumplen(d, nombres=None):
    """{regla: {'obra:huella del valor': título}} de un festival."""
    import catalogo
    nombres = nombres or paises()
    out = {}
    for f in (d or {}).get('films') or []:
        if not isinstance(f, dict):
            out.setdefault('festival:función ilegible', {})[str(f)[:20]] = str(f)[:40]
            continue
        f = dict(f, film_list=[x for x in f['film_list'] if isinstance(x, dict)]) if f.get('film_list') else f
        for o in catalogo.obras_de(f):
            for r in revisar(o, nombres):
                out.setdefault(r, {})[f"{o.get('work_id') or '?' + str(o.get('title'))}:{_huella(o, r)}"] = o.get('title')
    return out


def deuda():
    if not os.path.exists(DEUDA):
        return {}
    return {k: v for k, v in json.load(open(DEUDA, encoding='utf-8')).items() if not k.startswith('_')}


def excedidos(festivales, techo=None):
    """→ [(festival, regla, [títulos])]: lo que incumple y NO estaba anotado."""
    techo, n, out = deuda() if techo is None else techo, paises(), []
    for fid, d in sorted(festivales.items()):
        for r, obras in sorted(incumplen(d, n).items()):
            ya = set(techo.get(fid, {}).get(r, []))
            huellas = {x.split(':')[-1] for x in ya}     # una función nueva aún sin enlazar: vale su valor
            nuevas = [str(t) for k, t in obras.items() if k not in ya and not (k.startswith('?') and k.split(':')[-1] in huellas)]
            if nuevas:
                out.append((fid, r, sorted(nuevas)))
    return out


def holgura(festivales, techo=None):
    """Lo anotado que ya se arregló: hay que quitarlo (--congelar)."""
    techo, n = deuda() if techo is None else techo, paises()
    out = []
    for fid, rs in sorted(techo.items()):
        hoy = incumplen(festivales.get(fid), n)
        out += [f'{fid} {r} {len(set(ks) - set(hoy.get(r, {})))}' for r, ks in sorted(rs.items()) if set(ks) - set(hoy.get(r, {}))]
    return out


def autoprueba():
    """Cada regla tiene que atrapar su cebo, y una obra sana no incumple nada. [] = ve todo."""
    sana = {'title': 'Término', 'director': 'Arthur J. Bressan, Jr.', 'year': 2025, 'country': 'Colombia, Palestina', 'genre': 'Documental híbrido',
            'synopsis': 'Una mujer vuelve a su pueblo y encuentra la casa de sus padres convertida en un hotel.', 'synopsis_lang': 'es',
            'synopsis_en': 'A woman returns to her village and finds that her parents\' house has become a hotel.',
            'duration': '90 min', 'lbSlug': 'termino-2025', 'tmdb_id': 5}
    cebos = {'país:fuera de lista': [{'country': 'Colombia/Francia'}, {'country': 'Spain'}, {'country': 'Drama'}, {'country': 'Colombia,'}, {'country': 'Pseudobidi'}, {'country': 'Unión Europea'}, {'country': 'Colombia, Colombia'}],
             'género:fuera de lista': [{'genre': 'Qatar'}, {'genre': 'Documentary'}, {'genre': 'Drama / Terror'}, {'genre': 'VR 360'}],
             'año:no es número': [{'year': '2025'}, {'year': True}], 'año:imposible': [{'year': 1800}, {'year': 2090}],
             'director:cargo': [{'director': 'Dirección: Ana Díaz'}, {'director': 'CURA Simón Uribe'}],
             'director:separador': [{'director': 'Ana Díaz y Luz Paz'}, {'director': 'Ana Díaz / Luz Paz'}, {'director': 'A Díaz & L Paz'}, {'director': 'Ana Díaz + Luz Paz'}, {'director': 'Ana Díaz,Luz Paz'}, {'director': 'Ana Díaz - Luz Paz'}, {'director': 'Ana Díaz,'}],
             'director:basura': [{'director': 'Ana Díaz Ordóñez.'}, {'director': '@ana'}, {'director': 'Colombia'}, {'director': '???'}, {'director': '2025'},
                                 {'director': 'Varios'}, {'director': 'Ana Díaz (Colombia)'}],
             'afiche:forma': [{'poster': 'basura'}, {'poster': 5}], 'título:falta': [{'title': ''}, {'title': 'N/A'}, {'title': 5}],
             'sinopsis:pendiente': [{'synopsis': 'Sinopsis no disponible, próximamente más información de la película.'}],
             'sinopsis:en francés': [{'synopsis': 'En marge de Barcelone, Vallbona est une enclave entourée par une rivière et des voies ferrées.'}],
             'sinopsis en inglés:no cuenta la obra': [{'synopsis_en': 'Qatar.'}], 'sinopsis en inglés:texto roto': [{'synopsis_en': '<p>A drama about the war.</p>.'}],
             'sinopsis:cierre': [{'synopsis': 'Una mujer vuelve a su pueblo y encuentra la casa de sus padres convertida en un'}],
             'sinopsis:en inglés': [{'synopsis': sana['synopsis_en']}],
             'sinopsis:marcada en otro idioma': [{'synopsis_lang': 'pt'}],
             'sinopsis en inglés:otro idioma': [{'synopsis_en': sana['synopsis']}, {'synopsis_en': 'Una mujer vuelve a casa.'}, {'synopsis_en': 'En marge de Barcelone, Vallbona est une enclave entourée par une rivière et des voies ferrées.'}],
             'sinopsis en inglés:habla del festival': [{'synopsis_en': 'Winner of the Palme d’Or, this is a drama about the trial of a family in Norway.'}],
             'duración:forma': [{'duration': 24}, {'duration': '~6 min'}, {'duration': '999 min'}], 'letterboxd:forma': [{'lbSlug': 'film:151'}, {'lbSlug': 'null'}],
             'tmdb:no es número': [{'tmdb_id': '5'}], 'afiche:no existe': [{'poster': '/assets/no/existe.jpg'}, {'poster': 'assets/no.jpg'}, {'poster': '/assets/'}], 'título:espacios': [{'title': 'Dos  espacios'}]}
    n = paises()
    mal = [f'{r} no ve {c}' for r, cs in cebos.items() for c in cs if r not in revisar({**sana, **c}, n, 2030)]
    for s in ('Ana y Luis son hermanos. La madre le pide que le cuente qué ocurrió aquella noche.',
              'Un preso será liberado próximamente y vuelve a pensar en la casa de su infancia, donde su hermana lo espera desde hace más de veinte años.'):
        if revisar({**sana, 'synopsis': s}, n, 2030):
            mal.append(f'frena una sinopsis sana: {s[:40]}')
    if revisar(sana, n, 2030):
        mal.append(f'la obra sana incumple {revisar(sana, n, 2030)}')
    if excedidos({'nuevo': {'films': [dict(sana, type='film', genre='Qatar')]}}, {})[:1] == []:
        mal.append('un festival nuevo no parte de cero')
    return mal


def _festivales():
    from obra_unica import _festivales as f
    return f()


if __name__ == '__main__':
    a, fs = sys.argv[1:], _festivales()
    if a[:1] == ['--congelar']:
        ahora = {f: {r: sorted(o) for r, o in sorted(incumplen(d).items())} for f, d in sorted(fs.items())}
        ahora = {f: r for f, r in ahora.items() if r}
        if os.path.exists(DEUDA):
            sube = excedidos(fs)
            if sube:
                sys.exit('✗ la deuda solo baja; subió en: ' + ', '.join(f'{x[0]} {x[1]}: {x[2][:2]}' for x in sube[:8]))
        with open(DEUDA, 'w', encoding='utf-8') as fh:
            json.dump({'_nota': 'Obras que incumplen la regla de un campo, por festival. Solo baja (pipeline/ficha_obra.py).', **ahora},
                      fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(sum(len(n) for r in ahora.values() for n in r.values()), 'incumplimientos en', len(ahora), 'festivales')
    else:
        tot = {}
        for f, d in sorted(fs.items()):
            if a and f != a[0]:
                continue
            for r, o in incumplen(d).items():
                tot[r] = tot.get(r, 0) + len(o)
                if a:
                    print(f'{r}: ' + ' · '.join(sorted(str(x) for x in o.values())[:12]))
        print(json.dumps(dict(sorted(tot.items(), key=lambda x: -x[1])), ensure_ascii=False, indent=1))
