# -*- coding: utf-8 -*-
"""Formato intermedio → build publicable de TIFF 2026.

ENTRA  tiff-2026-crudo.json (638 funciones públicas) + venues-geo + oficial
SALE   tiff-2026-build.json  → tiff-2026-publicar.py → festivals/tiff-2026.json

TRES COSAS QUE ESTE PASO RESUELVE Y QUE NO SON OBVIAS

1. LOS PAÍSES HAY QUE TRADUCIRLOS, O NO HAY BANDERAS. TIFF los publica en
   inglés («United States of America», «Czech Republic») y `countryToFlags` de
   la app deriva la bandera del nombre en ESPAÑOL. Sin la tabla de abajo, 638
   funciones se quedan sin una sola bandera. Son los 67 países que aparecen de
   verdad en el programa: si mañana entra uno nuevo, este script aborta en vez
   de dejarlo mudo.

2. EL PÓSTER SOLO ENTRA SI ES UN PÓSTER. TMDB cubre 143 de las 244 obras. De
   las 101 restantes, TIFF tiene imagen para casi todas, pero son STILLS 16:9 y
   meterlas en una ranura de afiche es justo lo que prohíbe la doctrina de
   pósters. Solo se rescatan aquellas cuyo nombre de archivo declara que son
   afiche (6). Las otras 95 quedan SIN póster, que es el estado honesto.

3. LA SINOPSIS ESTÁ EN INGLÉS. TIFF las publica en inglés y TMDB solo tenía
   español para 26. Van con `synopsis_lang:'en'` —que el schema contempla— y
   duplicadas en `synopsis_en`. Es una decisión de producto pendiente de Juan,
   no un descuido: queda declarada, no escondida.
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import dias_config, provenance, slug

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'

PAIS_ES = {
    'United States of America': 'Estados Unidos', 'Canada': 'Canadá', 'France': 'Francia',
    'United Kingdom': 'Reino Unido', 'Italy': 'Italia', 'Germany': 'Alemania',
    'Spain': 'España', 'Norway': 'Noruega', 'Australia': 'Australia', 'Japan': 'Japón',
    'Mexico': 'México', 'South Korea': 'Corea del Sur', 'Belgium': 'Bélgica',
    'Denmark': 'Dinamarca', 'Ireland': 'Irlanda', 'Chile': 'Chile', 'Austria': 'Austria',
    'Brazil': 'Brasil', 'China': 'China', 'India': 'India', 'Netherlands': 'Países Bajos',
    'Singapore': 'Singapur', 'Sweden': 'Suecia', 'Poland': 'Polonia', 'Colombia': 'Colombia',
    'Taiwan': 'Taiwán', 'Argentina': 'Argentina', 'Luxembourg': 'Luxemburgo',
    'South Africa': 'Sudáfrica', 'Peru': 'Perú', 'Ukraine': 'Ucrania', 'Iceland': 'Islandia',
    'Bulgaria': 'Bulgaria', 'Nigeria': 'Nigeria', 'Palestine': 'Palestina', 'Iran': 'Irán',
    'Hong Kong': 'Hong Kong', 'Philippines': 'Filipinas', 'Turkey': 'Turquía',
    'Romania': 'Rumania', 'Rwanda': 'Ruanda', 'Gabon': 'Gabón',
    'Central African Republic': 'República Centroafricana',
    'Democratic Republic of Congo': 'República Democrática del Congo', 'Nepal': 'Nepal',
    'Indonesia': 'Indonesia', 'Saudi Arabia': 'Arabia Saudita', 'Lebanon': 'Líbano',
    'New Zealand': 'Nueva Zelanda', 'Thailand': 'Tailandia', 'Costa Rica': 'Costa Rica',
    'Panama': 'Panamá', 'Haiti': 'Haití', 'Guatemala': 'Guatemala', 'Israel': 'Israel',
    'Czech Republic': 'República Checa', 'Vietnam': 'Vietnam', 'Malaysia': 'Malasia',
    'Bangladesh': 'Bangladés', 'Portugal': 'Portugal', 'Greece': 'Grecia', 'Qatar': 'Catar',
    'Slovenia': 'Eslovenia', 'Ghana': 'Ghana', 'Uruguay': 'Uruguay', 'Latvia': 'Letonia',
    'Chad': 'Chad', 'USSR': 'URSS', 'Armenia': 'Armenia', 'Egypt': 'Egipto',
    'Finland': 'Finlandia', 'Greenland': 'Groenlandia', 'Switzerland': 'Suiza',
    'Afghanistan': 'Afganistán', 'Cambodia': 'Camboya', 'Croatia': 'Croacia',
    'Estonia': 'Estonia', 'Georgia': 'Georgia', 'Hungary': 'Hungría', 'Iraq': 'Irak',
    'Jordan': 'Jordania', 'Kenya': 'Kenia', 'Lithuania': 'Lituania', 'Morocco': 'Marruecos',
    'Pakistan': 'Pakistán', 'Senegal': 'Senegal', 'Serbia': 'Serbia', 'Tunisia': 'Túnez',
}
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

# País (nombre de TIFF, en inglés) → ISO-3166 alpha-2. La BANDERA se deriva del
# código, no se escribe a mano: un emoji de bandera son dos «regional indicator»
# y teclearlos uno por uno es pedir una errata invisible.
#
# Las banderas van en el propio film y no en `_COUNTRY_FLAGS` de la app porque
# esa tabla vive en src/controller/, que es código de app y no de este chat. El
# guardián [country-flags] acepta las dos vías, y la del dato no necesita a nadie.
ISO2 = {
    'United States of America': 'US', 'Canada': 'CA', 'France': 'FR',
    'United Kingdom': 'GB', 'Italy': 'IT', 'Germany': 'DE', 'Spain': 'ES',
    'Norway': 'NO', 'Australia': 'AU', 'Japan': 'JP', 'Mexico': 'MX',
    'South Korea': 'KR', 'Belgium': 'BE', 'Denmark': 'DK', 'Ireland': 'IE',
    'Chile': 'CL', 'Austria': 'AT', 'Brazil': 'BR', 'China': 'CN', 'India': 'IN',
    'Netherlands': 'NL', 'Singapore': 'SG', 'Sweden': 'SE', 'Poland': 'PL',
    'Colombia': 'CO', 'Taiwan': 'TW', 'Argentina': 'AR', 'Luxembourg': 'LU',
    'South Africa': 'ZA', 'Peru': 'PE', 'Ukraine': 'UA', 'Iceland': 'IS',
    'Bulgaria': 'BG', 'Nigeria': 'NG', 'Palestine': 'PS', 'Iran': 'IR',
    'Hong Kong': 'HK', 'Philippines': 'PH', 'Turkey': 'TR', 'Romania': 'RO',
    'Rwanda': 'RW', 'Gabon': 'GA', 'Central African Republic': 'CF',
    'Democratic Republic of Congo': 'CD', 'Nepal': 'NP', 'Indonesia': 'ID',
    'Saudi Arabia': 'SA', 'Lebanon': 'LB', 'New Zealand': 'NZ', 'Thailand': 'TH',
    'Costa Rica': 'CR', 'Panama': 'PA', 'Haiti': 'HT', 'Guatemala': 'GT',
    'Israel': 'IL', 'Czech Republic': 'CZ', 'Vietnam': 'VN', 'Malaysia': 'MY',
    'Bangladesh': 'BD', 'Portugal': 'PT', 'Greece': 'GR', 'Qatar': 'QA',
    'Slovenia': 'SI', 'Ghana': 'GH', 'Uruguay': 'UY', 'Latvia': 'LV',
    'Chad': 'TD', 'Armenia': 'AM', 'Egypt': 'EG', 'Finland': 'FI',
    'Switzerland': 'CH', 'Afghanistan': 'AF', 'Cambodia': 'KH', 'Croatia': 'HR',
    'Estonia': 'EE', 'Georgia': 'GE', 'Hungary': 'HU', 'Iraq': 'IQ',
    'Jordan': 'JO', 'Kenya': 'KE', 'Lithuania': 'LT', 'Morocco': 'MA',
    'Pakistan': 'PK', 'Senegal': 'SN', 'Serbia': 'RS', 'Tunisia': 'TN',
    'Greenland': 'GL', 'Belarus': 'BY', 'Kazakhstan': 'KZ', 'Mongolia': 'MN',
    # La URSS no tiene bandera Unicode: los Pelechian se quedan con la de Armenia,
    # que es donde se hicieron. Preferimos una bandera cierta a un globo.
    'USSR': None,
}


def bandera(iso):
    """ISO-3166 alpha-2 → emoji. 'CA' → 🇨🇦, por desplazamiento Unicode."""
    if not iso or len(iso) != 2:
        return ''
    return ''.join(chr(0x1F1E6 + ord(c) - ord('A')) for c in iso.upper())


def flags_de(txt):
    """Banderas de una lista de países en inglés, sin repetir y en orden."""
    out = []
    for p in re.split(r',\s*', txt or ''):
        p = p.strip()
        if p in ISO2 and ISO2[p]:
            f = bandera(ISO2[p])
            if f not in out:
                out.append(f)
    return ''.join(out)




def es_afiche(url):
    """Solo lo que DECLARA ser afiche. Un still no se asciende por conveniencia."""
    return bool(re.search(r'poster|key.?art|1sheet', (url or '').split('/')[-1], re.I))


def pais_es(txt):
    if not txt:
        return None
    fuera, out = [], []
    for p in re.split(r',\s*', txt):
        p = p.strip()
        if not p:
            continue
        if p not in PAIS_ES:
            fuera.append(p)
        out.append(PAIS_ES.get(p, p))
    return (', '.join(out), fuera)


def main():
    crudo = json.load(open(f'{ST}/tiff-2026-crudo.json', encoding='utf-8'))
    F = crudo['funciones']
    geo = json.load(open(f'{ST}/tiff-2026-venues-geo.json', encoding='utf-8'))
    ofi = {o['titulo']: o for o in
           json.load(open(f'{ST}/tiff-2026-oficial.json', encoding='utf-8'))['obras']}

    dias = sorted({f['dia'] for f in F})
    orden_dia = {d: i for i, d in enumerate(dias)}

    sin_pais, films = set(), []
    for f in F:
        pais, fuera = pais_es(f.get('pais')) if f.get('pais') else (None, [])
        sin_pais.update(fuera)
        img = (ofi.get(f['titulo']) or {}).get('poster')
        if f.get('poster_tmdb'):
            poster, fuente = TMDB_IMG + f['poster_tmdb'], 'tmdb'
        elif es_afiche(img):
            poster, fuente = ('https:' + img if img.startswith('//') else img), 'festival'
        else:
            poster, fuente = None, None

        films.append({
            'title': f['titulo'],
            'type': 'film',
            'director': f.get('director'),
            'year': int(f['anio']) if str(f.get('anio') or '').isdigit() else None,
            'duration': f'{f["duracion_min"]} min' if f.get('duracion_min') else None,
            'country': pais,
            'language': f.get('idiomas'),
            'genre': ', '.join(f.get('generos') or []) or None,
            'section': f['seccion'],
            'section_tags': f.get('etiquetas_seccion'),
            # Decisión 3: el idioma de la sinopsis se DECLARA.
            'synopsis': f.get('sinopsis'),
            'synopsis_lang': 'en',
            'synopsis_en': f.get('sinopsis'),
            'poster': poster,
            'posterSource': fuente,
            'lbSlug': f.get('lbSlug'),
            'tmdbId': f.get('tmdb_id'),
            'day': f['dia'], 'time': f['hora'], 'day_order': orden_dia[f['dia']],
            'venue': f['sede'], 'sala': f['sala'],
            'has_qa': f.get('has_qa', False),
            'flags': flags_de(f.get('pais')),
            'is_cortos': f['is_cortos'],
            # is_programa activa la ficha enriquecida de programa (main.js):
            # nuestro film_list trae director, país, duración y sinopsis por corto.
            'is_programa': bool(f['is_cortos']),
            'film_list': [{
                'title': c['titulo'],
                'title_orig': c.get('titulo_original'),
                'director': c.get('director'),
                'country': (pais_es(', '.join(c['pais'].split(', ')))[0]
                            if c.get('pais') else None),
                'flags': flags_de(c.get('pais')),
                'duration': f'{c["duracion_min"]} min' if c.get('duracion_min') else None,
                'year': int(c['anio']) if str(c.get('anio') or '').isdigit() else None,
                'synopsis': c.get('sinopsis'), 'synopsis_lang': 'en',
                'lbSlug': c.get('lbSlug'),
                'poster': None, 'posterSource': None,
            } for c in (f.get('film_list') or [])] if f['is_cortos'] else None,
            'is_free': False,
            'requires_registration': False,
            'ticketUrl': f.get('boleta'),
            'accessibility': f.get('accesibilidad') or None,
            'format': f.get('formato'),
            'premium': f.get('acceso') == 'premiumScreening',
            # [sin-procedencia]: un dato sin fuente es un dato no confiable.
            '_src': {'url': 'https://www.tiff.net' + ((ofi.get(f['titulo']) or {}).get('url') or ''),
                     'fuente': 'tiff.net/festivalfilmlist'},
        })

    if sin_pais:
        sys.exit(f'Países sin traducir, se quedarían sin bandera: {sorted(sin_pais)}. '
                 'Añadilos a PAIS_ES — un país mudo es un país invisible.')

    secciones = {}
    for i, (nom, meta) in enumerate(crudo['_secciones_propuestas'].items(), 1):
        secciones[f'{meta["emoji"]} {nom}'] = {'en': meta['en'],
                                               'archetype': meta['archetype'], 'order': i}
    # La sección viaja en el film con emoji, como en el resto de festivales.
    emoji_de = {n: f'{m["emoji"]} {n}' for n, m in crudo['_secciones_propuestas'].items()}
    for x in films:
        x['section'] = emoji_de.get(x['section'], x['section'])
        if x['section_tags']:
            x['section_tags'] = [emoji_de.get(t, t) for t in x['section_tags']]

    venues = {}
    for nom in sorted({f['venue'] for f in films}):
        g = geo.get(nom, {})
        venues[f'{nom} - Toronto'] = {k: v for k, v in
                                      {'short': nom, 'lat': g.get('lat'), 'lng': g.get('lng'),
                                       'city': 'Toronto', 'address': g.get('address', ''),
                                       '_nota': g.get('_nota')}.items() if v is not None}
    for x in films:
        x['venue'] = f'{x["venue"]} - Toronto'

    d0, d1 = dias[0], dias[-1]
    out = {
        '_provenance': provenance('tiff-2026-crudo + venues-geo + oficial',
                                  metodo='build publicable; solo funciones publicas'),
        # [festival-name-parity]: este name tiene que ser IDÉNTICO al de
        # FESTIVAL_CONFIG, o el JSON lo pisa en runtime. El nombre largo
        # vive en fullName.
        'name': 'TIFF',
        'shortName': 'TIFF',
        'fullName': 'TIFF — Toronto International Film Festival',
        'city': 'Toronto', 'country': 'CA',
        # OJO: TIFF comunica «Sep 10–20», pero hay UNA función pública el 9
        # («Hope», Special Events, TIFF Lightbox). Se incluye el día —nunca se
        # esconde una función real— y por eso el rótulo dice 9. Decisión
        # pendiente de Juan: rótulo nuestro (9–20) vs. el del festival (10–20).
        'dates': '9–20 SEP', 'dates_en': 'SEP 9–20', 'year': 2026,
        'timezoneOffset': '-04:00',
        'storageKey': 'tiff2026_',
        'festivalStartStr': f'{d0}T00:00:00', 'festivalEndStr': f'{d1}T23:59:00',
        **dias_config(dias, mes_es='septiembre'),
        # [prio-limit] exige round(días/2) acotado a [3,8]. Con 12 días → 6.
        'prioLimit': max(3, min(8, round(len(dias) / 2))),
        # 0 slots compartidos: cada función es su propia fila y los cortos van
        # dentro de film_list, no como obras que comparten horario.
        'sharedSlotIsOneScreening': False,
        'sections': secciones, 'venues': venues, 'films': films,
    }
    p = f'{ST}/tiff-2026-build.json'
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    obras = {x['title'] for x in films}
    print(f'── {p}')
    print(f'   films(funciones) {len(films)} · obras {len(obras)} · secciones {len(secciones)} '
          f'· sedes {len(venues)} · días {len(dias)}')
    print(f'   póster: tmdb {sum(1 for x in films if x["posterSource"]=="tmdb")} · '
          f'festival {sum(1 for x in films if x["posterSource"]=="festival")} · '
          f'sin {sum(1 for x in films if not x["poster"])}')
    print(f'   obras sin póster: {len({x["title"] for x in films if not x["poster"]})}/{len(obras)}')
    print(f'   con bandera derivable: {sum(1 for x in films if x["country"])}/{len(films)}')


if __name__ == '__main__':
    main()
