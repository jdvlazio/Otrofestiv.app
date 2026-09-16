# -*- coding: utf-8 -*-
"""Instagram de @narrarelfuturo → lo que la web del festival NO publica.

La web trae la parrilla (día, hora, sede, ficha). Instagram trae lo otro, y no
es poco:

  · SINOPSIS POR OBRA de los dos programas de cortos. La web lista título,
    país, año, duración y género; el pie de Instagram añade una línea de
    contenido por corto, que es lo que un usuario lee antes de decidir.
  · El bloque de la SALA VR con su horario y su sede, que la parrilla no
    modela porque la instalación no es una función.
  · El encuentro con las directoras DESPUÉS de la película inaugural — un Q&A
    que la ficha de la web no menciona.
  · Dos franjas ausentes del programa: #NewMediaLab y las charlas inaugurales.

IG SE LEE EN EL NAVEGADOR para descubrir los posts (regla de la casa: el fetch
de texto da falsos negativos, cicatriz de QAFF). Los pies se extraen del embed
público, que sí es fiable una vez que se sabe el shortcode.

OJO — TRES POSTS SON EL MISMO. `DdT1kVaEVDt`, `DdT1gauEWLB` y `DdT1eE6ET9c`
tienen el pie IDÉNTICO: el festival publicó tres veces el anuncio de apertura.
Contar posts no es contar contenido.
"""
import io, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
SALIDA = f'{ST}/narrarelfuturo-2026-ig.json'
IG = 'https://www.instagram.com/p/'

# shortcode → qué es. Descubiertos en el navegador el 15 sep 2026.
POSTS = {
    'DdSzM3HFpCM': ('programa', 'El Futuro del Futuro', 9),
    'DdS3Uuvlp8Z': ('programa', 'Narrar. Creer. Crecer', 10),
    'DdR-n97md3i': ('dia', 'Día 1 — apertura, Sala VR y película inaugural', 0),
    'DdVB8kHkbes': ('franja', '#NewMediaLab', 0),
    'DdU2qWvkbYO': ('franja', 'Charlas inaugurales', 0),
}
RUTA_IG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ig_carrusel.py')
# líneas de logística que se repiten tras CADA obra y no son contenido
RE_LOGISTICA = re.compile(r'^[\U0001F300-\U0001FAFF☀-➿]?\s*(📍|📅|🕓|🎟️|Cra\.|Calle|#\w)')


def carrusel(sc):
    r = subprocess.run([sys.executable, RUTA_IG, sc], capture_output=True, text=True)
    linea = (r.stdout or '').strip().split('\n')[0]
    if not linea.startswith('{'):
        return None
    return json.loads(linea)


def obras(caption):
    """Los bloques del pie que SON una obra. El pie repite sede, fecha, hora y
    boletería después de cada corto, así que el criterio no puede ser «bloque
    que empieza con emoji»: eso devuelve 26 bloques para 9 obras. Una obra es un
    bloque largo que no es logística."""
    out = []
    for b in re.split(r'\n(?=[\U0001F300-\U0001FAFF☀-➿])', caption):
        b = b.strip()
        if len(b) < 80 or RE_LOGISTICA.match(b):
            continue
        cuerpo = ' '.join(x.strip() for x in b.split('\n') if x.strip())
        cuerpo = re.sub(r'^[\U0001F300-\U0001FAFF☀-➿]+\s*', '', cuerpo)
        m = re.match(r'^(.+?)\s+de\s+(.+?)\s*\(([^)]*)\)\s*(.*)$', cuerpo)
        if m and len(m.group(1)) < 70:
            out.append({'titulo': m.group(1).strip(), 'autoria': m.group(2).strip(),
                        '_credito': m.group(3).strip(), 'sinopsis': m.group(4).strip()})
        else:
            out.append({'_texto': cuerpo})
    return out


def main():
    salida, avisos = [], []
    for sc, (tipo, nombre, esperadas) in POSTS.items():
        d = carrusel(sc)
        if not d:
            avisos.append(f'{sc}: el embed no lo sirve — leer en el navegador')
            continue
        e = {'shortcode': sc, 'tipo': tipo, 'nombre': nombre,
             '_src': f'{IG}{sc}/', 'laminas': len(d['laminas']),
             'caption': d['caption'],
             'imagenes': [l['url'] for l in d['laminas'] if not l['video']]}
        if tipo == 'programa':
            e['obras'] = obras(d['caption'])
            reales = [o for o in e['obras'] if o.get('titulo')]
            e['_obras_con_ficha'] = len(reales)
            if esperadas and len(reales) != esperadas:
                avisos.append(f'{sc} «{nombre}»: {len(reales)} obras leídas y la '
                              f'parrilla declara {esperadas} — mirar el pie entero')
        salida.append(e)

    os.makedirs(ST, exist_ok=True)
    json.dump({'_provenance': provenance(
        'instagram.com/narrarelfuturo — posts descubiertos en el navegador, pies vía embed público',
        metodo='un post por programa o franja; el pie repite la logística tras cada obra',
        nota='tres posts del 15 sep tienen el pie IDÉNTICO: el anuncio de apertura se publicó tres veces'),
        '_posts': len(salida), 'posts': salida},
        io.open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'── {os.path.basename(SALIDA)} · {len(salida)} posts')
    for e in salida:
        print(f"  {e['shortcode']}  {e['tipo']:<9} {e['nombre'][:38]:40} "
              f"{e.get('_obras_con_ficha', '—'):>3} obras · {len(e['imagenes'])} imágenes")
    for a in avisos:
        print('  ⚠', a)


if __name__ == '__main__':
    main()
