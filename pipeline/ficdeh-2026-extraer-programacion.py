# -*- coding: utf-8 -*-
"""Extracción CANÓNICA de la programación de FICDEH 2026 (11 ciudades × 8 días).

Reemplaza el goteo de extracciones parciales que fue el origen de casi todos
los errores del onboarding: la sala se descubrió tarde porque cada pasada leía
solo los campos que hacían falta en ese momento. Aquí se lee TODO lo que el
sitio publica por función, de una vez, y de ahí sale el sidecar.

Estructura del sitio (Next.js server-rendered, /programacion/<ciudad>?fecha=):
    <section>            → una SEDE (h2 = nombre, siguiente bloque = dirección)
      <li>               → una FUNCIÓN
        <span>           → hora («2:00 p.m.»)
        <button>         → título
        <p>              → «Director · 17 min · Sala»
        <img>            → póster (/uploads/obras/…)

La SALA es el tercer campo de ese <p> y no existe en ninguna otra vista: no
está en el JSON de la función ni en la ficha de la obra. Sin ella, el anclaje
(día|hora|sede|sala) mete en un mismo bloque películas que van en salas
distintas — el Colombo Americano de Medellín proyecta en SALA 1, 2 y 3 a la vez.

Ojo con «Proyección en loop» (Ibagué): no es una función con principio y fin,
es proyección continua. Se conserva el texto crudo de la sala para poder
distinguirlas.

curl necesita User-Agent de navegador; sin él, Vercel responde con su checkpoint.
"""
import json, re, html, subprocess, time, os, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/ficdeh-2026-programacion-canonica.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
CIUDADES = ['bogota', 'medellin', 'cali', 'barranquilla', 'cartagena', 'armenia',
            'ibague', 'quibdo', 'pereira', 'manizales', 'tunja']
FECHAS = [f'2026-08-{d}' for d in range(12, 20)]
CIUDAD_NOMBRE = {'bogota': 'Bogotá', 'medellin': 'Medellín', 'cali': 'Cali',
                 'barranquilla': 'Barranquilla', 'cartagena': 'Cartagena',
                 'armenia': 'Armenia', 'ibague': 'Ibagué', 'quibdo': 'Quibdó',
                 'pereira': 'Pereira', 'manizales': 'Manizales', 'tunja': 'Tunja'}


def get(url):
    for _ in range(3):
        r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '40', '-A', UA,
                            '-H', 'Accept: text/html,application/xhtml+xml', url],
                           capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 3000:
            return r.stdout.decode('utf-8', 'ignore')
        time.sleep(1.5)
    return ''


def limpio(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def hora24(h):
    m = re.match(r'(\d{1,2}):(\d{2})\s*([ap])\.?\s*m', h.strip(), re.I)
    if not m:
        return h.strip()
    hh, mm, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    if ap == 'p' and hh != 12:
        hh += 12
    if ap == 'a' and hh == 12:
        hh = 0
    return f'{hh:02d}:{mm}'


def parse(page, ciudad, fecha):
    out = []
    for sec in re.split(r'<section', page)[1:]:
        h = re.search(r'<h[23][^>]*>(.*?)</h[23]>', sec, re.S)
        if not h:
            continue
        sede = limpio(h.group(1))
        dsp = sec[h.end():h.end() + 400]
        dirm = re.search(r'<p[^>]*>(.*?)</p>', dsp, re.S)
        direccion = limpio(dirm.group(1)) if dirm else ''
        for li in re.findall(r'<li[^>]*>(.*?)</li>', sec, re.S):
            spans = [limpio(s) for s in re.findall(r'<span[^>]*>(.*?)</span>', li, re.S)]
            hora = next((s for s in spans if re.search(r'[ap]\.?\s*m', s, re.I)), '')
            # El segundo <span> —cuando existe— es el tipo de acceso: «Función
            # privada», «Boletería en taquilla», «Entrada libre», «Inscripción».
            # «Función privada» NO es para el público y no puede entrar a la app.
            acceso = next((s for s in spans if s and s != hora), '')
            tit = re.findall(r'<button[^>]*>(.*?)</button>', li, re.S)
            meta = re.search(r'<p[^>]*>(.*?)</p>', li, re.S)
            img = re.search(r'<img[^>]+src="([^"]+)"', li)
            titulo = next((limpio(t) for t in tit if len(limpio(t)) > 2), '')
            if not (hora and titulo):
                continue
            partes = [p.strip() for p in limpio(meta.group(1)).split('·')] if meta else []
            di = next((i for i, p in enumerate(partes) if re.fullmatch(r'\d+\s*min', p, re.I)), -1)
            out.append({
                'ciudad': CIUDAD_NOMBRE[ciudad], 'dia': fecha,
                'hora': hora24(hora), 'sede': sede, 'acceso': acceso,
                'en_app': 'privada' not in acceso.lower(),
                'direccion': direccion, 'titulo': titulo,
                'director': ' · '.join(partes[:di]) if di > 0 else '',
                'duracion': partes[di] if di >= 0 else '',
                'sala': ' · '.join(partes[di + 1:]) if di >= 0 else '',
                'poster_url': img.group(1) if img else '',
            })
    return out


def main():
    todo = []
    for c in CIUDADES:
        for f in FECHAS:
            page = get(f'https://www.ficdeh.com/programacion/{c}?fecha={f}')
            fs = parse(page, c, f) if page else []
            todo.extend(fs)
            print(f'  {c:13} {f}  {len(fs):3} funciones', flush=True)
            time.sleep(0.2)

    # el mismo <li> no puede salir dos veces; si sale, el parser está mal
    vistas, dedup = set(), []
    for x in todo:
        k = (x['ciudad'], x['dia'], x['hora'], x['sede'], x['titulo'])
        if k in vistas:
            continue
        vistas.add(k)
        dedup.append(x)

    json.dump({'_provenance': {
        'fuente': 'https://www.ficdeh.com/programacion/<ciudad>?fecha=<AAAA-MM-DD>',
        'capturado': '2026-08-05',
        'que_trae': 'sede, dirección, sala, hora, título, director, duración y póster por función',
        'ojo': 'La SALA solo existe en esta vista. «Proyección en loop» (Ibagué) no es una función con principio y fin.',
    }, 'funciones': dedup}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n{len(dedup)} funciones · {len(todo)-len(dedup)} repetidas descartadas')
    print(f'con sala: {sum(1 for x in dedup if x["sala"])} · en loop: {sum(1 for x in dedup if "loop" in x["sala"].lower())}')
    print(f'públicas (en_app): {sum(1 for x in dedup if x["en_app"])} · privadas excluidas: {sum(1 for x in dedup if not x["en_app"])}')
    print('\ntipos de acceso:')
    for a, n in collections.Counter(x['acceso'] or '(sin marcar)' for x in dedup).most_common():
        print(f'  {n:4}  {a}')
    print(f'sedes: {len({(x["sede"],x["ciudad"]) for x in dedup})}')
    print('\nsalas por ciudad:')
    for (c, s), n in sorted(collections.Counter((x['ciudad'], x['sala']) for x in dedup if x['sala']).items()):
        print(f'  {n:3}  {c:13} {s}')


if __name__ == '__main__':
    main()
