#!/usr/bin/env python3
# ── lint-catalog.py — linter de CONTENIDO de catálogos de festival ────────────
#
# Nace de la retro de FICDEH (26 jul 2026, pedida por Juan): los guardianes
# existentes validan la FORMA del JSON (campos, formatos, duplicados) pero no el
# CONTENIDO extraído — y cada festival exige código de extracción nuevo, que
# trae bugs nuevos. Todos los errores de FICDEH los cazó un humano notando que
# "algo huele raro"; este linter mecaniza ese olfato:
#
#   [duracion-vs-seccion]  largometraje de 1 min = imposible (bug real: el HTML
#                          partía "102" y el parseo capturó "1")
#   [sinopsis-pura]        la sinopsis no contiene metadata ("Director: …
#                          Ubicación: Cinemateca … Sala 2" — bug real: 92/92)
#   [titulo-bilingue]      "Silenciada (Silenced)" pegado rompe la búsqueda
#                          TMDB (bug real: 7 títulos, 10 fichas perdidas)
#   [pais-sano]            país segmentable en países conocidos ("Colombia Peru"
#                          pegado, "Peru Ubicación: …" con basura — bugs reales)
#   [director-persona]     el director parece nombre de persona, no metadata
#   [poster-phash-dup]     pósters DUPLICADOS POR PÍXELES (dHash) aunque el
#                          archivo/URL difiera — el gate por URL no los ve
#
# Uso:
#   python3 scripts/lint-catalog.py festivals/staging/ficdeh-2026.json   # uno
#   python3 scripts/lint-catalog.py --root          # festivals/*.json (sin staging)
#   python3 scripts/lint-catalog.py --root --ci     # modo CI: solo gates de texto
#                                                   # (sin PIL), exit 1 si ERROR
# Doctrina: ERROR = imposible/corrupto (bloquea). WARNING = raro (revisar).

import json, sys, re, os, glob

ERRORS, WARNINGS = [], []
def err(check, msg):  ERRORS.append(f'[{check}] {msg}')
def warn(check, msg): WARNINGS.append(f'[{check}] {msg}')

# ── países conocidos (es) — segmentación por coincidencia más larga ───────────
PAISES = {
 'Colombia','México','Argentina','Brasil','Chile','Perú','Ecuador','Venezuela',
 'Bolivia','Uruguay','Paraguay','Cuba','Panamá','Costa Rica','Nicaragua',
 'Honduras','El Salvador','Guatemala','República Dominicana','Puerto Rico',
 'Haití','Jamaica','Estados Unidos','Canadá','España','Francia','Alemania',
 'Italia','Portugal','Reino Unido','Irlanda','Países Bajos','Bélgica','Suiza',
 'Austria','Suecia','Noruega','Dinamarca','Finlandia','Islandia','Polonia',
 'República Checa','Chequia','Hungría','Rumania','Grecia','Turquía','Rusia',
 'Ucrania','Georgia','Armenia','Israel','Palestina','Líbano','Irán','Irak',
 'Siria','Qatar','Arabia Saudita','Emiratos Árabes Unidos','Jordania','Egipto',
 'Marruecos','Túnez','Argelia','Senegal','Ghana','Nigeria','Kenia','Etiopía',
 'Sudáfrica','Mozambique','Angola','Congo','República Democrática del Congo',
 'Sáhara Occidental','India','China','Japón','Corea del Sur','Taiwán',
 'Hong Kong','Filipinas','Indonesia','Malasia','Singapur','Tailandia','Vietnam',
 'Camboya','Bangladés','Bangladesh','Pakistán','Nepal','Sri Lanka','Australia',
 'Nueva Zelanda','Luxemburgo','Mónaco','Serbia','Croacia','Eslovenia','Bosnia',
 'Macedonia del Norte','Albania','Bulgaria','Eslovaquia','Estonia','Letonia',
 'Lituania','Kosovo','Moldavia','Bielorrusia','Curazao','Guyana','Surinam',
 'Belice','Trinidad y Tobago','Afganistán','Kazajistán','Uzbekistán','Mongolia',
 'Birmania','Myanmar','Laos','Costa de Marfil','Camerún','Uganda','Tanzania',
 'Zimbabue','Zambia','Malaui','Ruanda','Burundi','Mali','Burkina Faso','Níger',
 'Chad','Sudán','Somalia','Libia','Mauritania','Yemen','Omán','Kuwait','Baréin',
 'Chipre','Malta','Groenlandia','Fiyi','Papúa Nueva Guinea',
 # nombres EN — festivales con data en inglés (Tribeca) las usan tal cual
 'United States','United Kingdom','Mexico','Spain','France','Germany','Italy',
 'Brazil','Peru','Japan','Sweden','Norway','Denmark','Finland','Iceland',
 'Netherlands','Belgium','Switzerland','Austria','Ireland','Poland','Greece',
 'Turkey','Czech Republic','Slovakia','Hungary','Romania','New Zealand',
 'South Korea','South Africa','Canada','Australia','China','India','Russia',
 'Ukraine','Israel','Egypt','Morocco','Argentina','Chile','Colombia','Portugal',
 'Democratic Republic of Congo','Philippines','Indonesia','Thailand','Vietnam',
 'Taiwan','Hong Kong','Singapore','Malaysia','Lebanon','Iran','Jordan','Kenya',
 'Nigeria','Ghana','Ethiopia','Croatia','Serbia','Slovenia','Bulgaria','Estonia',
 'Latvia','Lithuania','Panama','Cuba','Haiti','Dominican Republic','Pakistan',
 'Saudi Arabia','Türkiye','Cameroon','Luxembourg','North Macedonia','Kosovo',
 'Bosnia and Herzegovina','Moldova','Belarus','Uzbekistan','Kazakhstan',
 'Mongolia','Myanmar','Cambodia','Laos','Ivory Coast','Tunisia','Algeria',
 'Libya','Sudan','Somalia','Uganda','Tanzania','Zambia','Zimbabwe','Malawi',
 'Rwanda','Mozambique','Angola','Namibia','Botswana','Cyprus',
 'United Arab Emirates','Kuwait','Bahrain','Oman','Yemen','Iraq','Syria',
 'Afghanistan','Palestine','Greenland','Fiji',
}
_MARCAS_METADATA = re.compile(
    r'Director(?:a|es|as)?\s*:|Duraci[oó]n\s*:|Ubicaci[oó]n\s*:|Hora\s*:|'
    r'A[nñ]o\s*:|Pa[ií]s(?:es)?\s*:|Sala\s+\d|Sinopsis\s*:', re.I)

def _rows(data):
    films = data.get('films', data if isinstance(data, list) else [])
    for f in films:
        if f.get('type') == 'event': continue
        if f.get('film_list'):
            for it in f['film_list']: yield f, it
            yield None, f          # el contenedor también se lintea (título/póster)
        else:
            yield None, f

def _dur_min(s):
    m = re.match(r'^(\d+)\s*min$', str(s or '').strip())
    return int(m.group(1)) if m else None

def _pais_ok(txt):
    """True si el campo país se puede segmentar 100% en países conocidos.
    Separadores aceptados: ',' y '/' (festivales viejos usan slash)."""
    if str(txt).strip() in ('Varios', 'Various'): return True
    for parte in [p.strip() for p in re.split(r'[,/]', str(txt)) if p.strip()]:
        resto = parte
        while resto:
            m = next((p for p in sorted(PAISES, key=len, reverse=True)
                      if resto == p or resto.startswith(p + ' ')), None)
            if not m: return False
            resto = resto[len(m):].strip()
    return True

def lint_file(path, ci=False):
    data = json.load(open(path, encoding='utf-8'))
    base = os.path.basename(path)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    if '/staging/' in os.path.abspath(path):
        repo = os.path.dirname(repo)
    hashes = {}

    for parent, it in _rows(data):
        t = it.get('title', '¿?')
        ref = f'{base}: "{t[:44]}"'

        # [duracion-vs-seccion] — imposibles físicos según la sección declarada
        n = _dur_min(it.get('duration'))
        sec = (it.get('section') or (parent or {}).get('section') or '').lower()
        if n is not None:
            if 'largometraje' in sec and n < 40:
                err('duracion-vs-seccion', f'{ref}: {n} min en sección de largometraje (<40)')
            if 'cortometraje' in sec and n > 60 and not it.get('film_list'):
                err('duracion-vs-seccion', f'{ref}: {n} min en sección de cortometraje (>60)')
            if n == 0 or n > 400:
                err('duracion-vs-seccion', f'{ref}: duración absurda ({n} min)')

        # [sinopsis-pura] — texto limpio, sin metadata pegada
        for k in ('synopsis', 'synopsis_en'):
            s = it.get(k) or ''
            if s and _MARCAS_METADATA.search(s):
                err('sinopsis-pura', f'{ref}: {k} contiene metadata pegada '
                    f'("{_MARCAS_METADATA.search(s).group(0)}…")')
            if s and len(s) < 40:
                warn('sinopsis-pura', f'{ref}: {k} sospechosamente corta ({len(s)} chars)')

        # [titulo-bilingue] — "Título (Translated Title)" pegado
        m = re.match(r'^(.+?)\s*\(([^)]{4,})\)\s*$', t)
        if m and not re.fullmatch(r'[\d\s\-–]+', m.group(2)):
            inner = m.group(2)
            if re.search(r'[a-záéíóúñ]', inner, re.I) and len(inner.split()) >= 1 \
               and not it.get('title_en'):
                warn('titulo-bilingue', f'{ref}: posible título bilingüe pegado '
                     f'— separar en title/title_en ("{inner}")')

        # [pais-sano]
        c = it.get('country') or ''
        if c:
            if _MARCAS_METADATA.search(c):
                err('pais-sano', f'{ref}: country con basura de metadata ("{c[:60]}")')
            elif not _pais_ok(c):
                warn('pais-sano', f'{ref}: country no segmenta en países conocidos ("{c[:60]}")')

        # [director-persona] — metadata pegada = ERROR; dígitos solos = WARNING
        # (hay directores reales con dígito: "One9" dirigió el doc de Nas)
        d = it.get('director') or ''
        if d:
            if _MARCAS_METADATA.search(d):
                err('director-persona', f'{ref}: director no parece persona ("{d[:60]}")')
            elif re.search(r'\d', d):
                warn('director-persona', f'{ref}: director con dígitos ("{d[:60]}") — verificar')
            elif len(d) > 140:
                warn('director-persona', f'{ref}: director larguísimo ({len(d)} chars) — ¿lista pegada?')

        # [poster-phash-dup] — recolectar pósters locales para dHash
        p = it.get('poster') or ''
        if not ci and p.startswith('/assets/'):
            fp = os.path.join(repo, p.lstrip('/'))
            if os.path.exists(fp):
                hashes.setdefault(fp, []).append(ref)

    # dHash perceptual (solo fuera de CI; degrada con aviso si no hay PIL)
    if not ci and hashes:
        try:
            from PIL import Image
            seen = {}
            for fp, refs in hashes.items():
                try:
                    im = Image.open(fp).convert('L').resize((9, 8))
                    px = list(im.tobytes())
                    bits = sum(1 << i for i in range(64)
                               if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])
                except Exception:
                    continue
                for prev_fp, prev_bits in seen.items():
                    if prev_fp != fp and bin(bits ^ prev_bits).count('1') <= 4:
                        err('poster-phash-dup',
                            f'{os.path.basename(fp)} ≈ {os.path.basename(prev_fp)} '
                            f'(misma imagen por píxeles) — {refs[0]}')
                seen[fp] = bits
        except ImportError:
            warn('poster-phash-dup', 'PIL no disponible — dedup perceptual saltado')

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ci = '--ci' in sys.argv
    if '--root' in sys.argv:
        args = sorted(glob.glob('festivals/*.json'))
    if not args:
        print(__doc__ or 'Uso: lint-catalog.py <json…> | --root [--ci]'); sys.exit(1)
    for p in args:
        lint_file(p, ci=ci)
    for w in WARNINGS: print(f'  ⚠ {w}')
    for e in ERRORS:   print(f'  ✗ {e}')
    print(f'\nlint-catalog: {len(ERRORS)} errores · {len(WARNINGS)} warnings '
          f'en {len(args)} archivo(s)')
    sys.exit(1 if ERRORS else 0)

if __name__ == '__main__':
    main()
