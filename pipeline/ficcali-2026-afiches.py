#!/usr/bin/env python3
"""ficcali-2026-afiches.py — los afiches oficiales de las obras, de la web de FICCALI.

La biblioteca de medios de ficcali.com (API REST `media`) guarda el afiche de
cada obra de la Selección 2026 como «poster-<obra>» (subidos sep–oct 2026). No
están enlazados desde las fichas: se encuentran por nombre. El nombre no
siempre es el título («poster-donkey-princess» es Princesa burro, «poster-azote»
es Azotea), así que la tabla va escrita a mano, mirada una por una.

LO QUE NO ENTRA: un «poster» apaisado. Dos lo son (El león, Infinita canción:
el secreto) y uno es una miniatura (Sentenciados, 352×296): son stills o
recortes, no afiches, y la regla es solo el afiche original.

Escribe festivals/staging/ficcali-2026-afiches.json (título publicado → archivo
en fuentes/), que enriquecer.py usa SOLO donde TMDB y lo ya publicado no
tienen afiche.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = f'{REPO}/fuentes/ficcali-2026'
MEDIA = f'{DIR}/media-posters.json'
CAT = f'{REPO}/festivals/staging/ficcali-2026-catalogo.json'
DESTINO = f'{REPO}/festivals/staging/ficcali-2026-afiches.json'

# el nombre del archivo cuando no es el título de la ficha
SLUG = {
    'Azotea': 'poster-azote', 'Princesa burro': 'poster-donkey-princess',
    'Siempre soy tu animal materno': 'poster-forever-your-maternal-animal',
    'Flamencoterapia': 'poster-flomencoterapia', 'Y el río lloró': 'poster-y-el-lloro',
    'Mu-ki-ra': 'poster-mukira', 'Ellas, gardiennes de l’Amazonie': 'poster-ellas',
    'Jiru luiai': 'poster-jiru-iuiai', 'La línea del mar': 'poster-linea-del-mar',
    'Muiyukuna: Relatos de la chagra viva': 'poster-muiyukuna',
    'Namtrik, fogones lingüísticos': 'poster-namtrik',
    'Pueblo Viejo, guardianes de la montaña': 'poster-pueblo-viejo', 'Tuktu, Padre Maíz': 'poster-tuktu',
    'Écrire la vie: Annie Ernaux racontée par des lycéennes et des lycéens': 'poster-ecrire-la-vie',
    'Amélie y los secretos de la lluvia': 'poster-amelie',
    'Kiki: entregas a domicilio': 'poster-kiki-entregas-a-domicilio-2',
    # dos versiones: se toma la de mayor tamaño
    'Iluminada': 'poster-iluminada',
    'Ya se ven los tigres en la lluvia': 'poster-ya-se-ven-los-tigres-en-la-lluvia',
}


def slug_web(s):
    """El nombre de archivo que usa la web del festival (no es lib.slug)."""
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def bajar_media():
    out, n = [], 1
    while True:
        r = subprocess.run(['curl', '-s', 'https://ficcali.com/wp-json/wp/v2/media?search=poster&per_page=100'
                            f'&page={n}&after=2026-07-01T00:00:00&_fields=id,source_url,media_details,date,slug'],
                           capture_output=True, text=True).stdout
        try:
            d = json.loads(r, strict=False)
        except ValueError:
            break
        if not isinstance(d, list) or not d:
            break
        out += d
        n += 1
    json.dump(out, io.open(MEDIA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main():
    if '--bajar' in sys.argv or not os.path.exists(MEDIA):
        bajar_media()
    M = {m['slug']: m for m in json.load(io.open(MEDIA, encoding='utf-8'))}
    O = json.load(io.open(CAT, encoding='utf-8'))['obras']
    os.makedirs(f'{DIR}/afiches', exist_ok=True)
    afiches, sin, apaisados = {}, [], []
    for o in O:
        s = SLUG.get(o['titulo']) or f'poster-{slug_web(o["titulo"])}'
        m = M.get(s)
        if not m:
            sin.append(o['titulo'])
            continue
        w, h = m['media_details'].get('width') or 0, m['media_details'].get('height') or 0
        if w >= h:
            apaisados.append(f'{o["titulo"]} ({w}×{h})')
            continue
        ext = os.path.splitext(m['source_url'])[1].lower() or '.jpg'
        dest = f'{DIR}/afiches/{s}{ext}'
        if not os.path.exists(dest) or os.path.getsize(dest) < 5000:
            subprocess.run(['curl', '-sL', '--max-time', '40', m['source_url'], '-o', dest])
        if os.path.exists(dest) and os.path.getsize(dest) > 5000:
            afiches[o['titulo']] = {'archivo': os.path.relpath(dest, REPO),
                                    'fuente': f'ficcali.com, biblioteca de medios: {m["source_url"]} ({w}×{h})'}
        else:
            sin.append(f'{o["titulo"]} (no se pudo bajar)')
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': {'fuente': 'ficcali.com, biblioteca de medios (API REST `media`, «poster-<obra>»)',
                        'capturado': '2026-10-07', 'regla': 'solo donde TMDB y lo ya publicado no tienen afiche',
                        'genera': 'pipeline/ficcali-2026-afiches.py'},
        'afiches': dict(sorted(afiches.items()))}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(afiches)} afiches · {len(sin)} sin afiche en la web · {len(apaisados)} apaisados fuera '
          f'→ {os.path.relpath(DESTINO, REPO)}')
    for x in sin:
        print('   sin ·', x)
    for x in apaisados:
        print('   apaisado ·', x)


if __name__ == '__main__':
    main()
