#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""narrarelfuturo-2026-charlas.py — la franja de CHARLAS, que no está en la parrilla.

POR QUÉ EXISTE ESTE PASO. El festival publica su programación en cuatro sitios y
/programa-2026/ —la parrilla— NO trae las charlas: se buscó «futuro de lo real»
y «día de tu suerte» en su HTML y no aparecen ni una vez. Viven solo en
/charlas-2026/, una página del menú del sitio. Sin este paso, el día inaugural
del festival salía con dos actividades (la instalación VR y la película) cuando
tuvo cuatro, y las dos que faltaban son justo con las que abrió.

La lección, que ya costó dos veces: la parrilla de un festival no es el
programa del festival. El menú del sitio es el índice de verdad — ahí están
también #HackathonVR360 (laboratorio cerrado de 20 seleccionados, convocatoria
cerrada el 8 sep, sede que solo reciben por correo: no se publica) y #Invitados
(fichas de personas, no actividades).

Lee   https://narrarelfuturo.com/charlas-2026/
Esc.  festivals/staging/narrarelfuturo-2026-charlas.json
"""
import io, json, os, re, subprocess, sys, time
import html as _html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/narrarelfuturo-2026'
URL = 'https://narrarelfuturo.com/charlas-2026/'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'

MES = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05',
       'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09',
       'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
SEDE = ('Universidad Jorge Tadeo Lozano', 'Aula Máxima')
PIE = 'Festival de Cine & Nuevos Medios es un punto'


def bajar():
    p = f'{CACHE}/charlas-2026.html'
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sL', '--max-time', '35', '-A', UA, URL, '-o', p], check=True)
        time.sleep(0.25)
    return io.open(p, encoding='utf-8', errors='replace').read()


def texto(h):
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', h, flags=re.S | re.I)
    t = _html.unescape(re.sub(r'<[^>]+>', '\n', t))
    return [x.strip() for x in t.split('\n') if x.strip()]


def h24(hh, mm, ap):
    return f'{int(hh) % 12 + (12 if ap.lower().startswith("p") else 0):02d}:{mm}'


def main():
    L = texto(bajar())
    fin = next((k for k, x in enumerate(L) if PIE in x), len(L))
    # Cada charla empieza en su línea de CUÁNDO («Martes 15») y el título es lo
    # que hay encima: una línea, o dos cuando el título es largo y la maqueta lo
    # parte («Pronto llegará el día de tu suerte: ¿Estamos, al fin, ante una /
    # industria del cine y los nuevos medios?»).
    anclas = [k for k, x in enumerate(L[:fin]) if re.match(r'^\w+ \d{1,2}$', x)
              and k + 1 < fin and re.match(r'^de \w+ \|', L[k + 1])]
    charlas = []
    for i, k in enumerate(anclas):
        ini_t = anclas[i - 1] + 1 if i else 0
        titulo = []
        for x in reversed(L[max(ini_t, 0):k]):
            if re.match(r'^(Panelistas|Modera|Inscrib|Charlas 2026|#NEF|Programa)', x) or len(x) > 200:
                break
            titulo.insert(0, x)
        d = {'titulo': ' '.join(titulo).strip(), '_src': URL, 'tipo': 'charla'}
        cuando = L[k] + ' ' + L[k + 1] + (' ' + L[k + 2] if k + 2 < fin else '')
        m = re.search(r'(\d{1,2}).*?de (\w+).*?(\d{1,2}):(\d{2})\s*([ap])m\s*a\s*(\d{1,2}):(\d{2})\s*([ap])m', cuando, re.I)
        if m:
            d['dia'] = f'2026-{MES.get(m.group(2).lower(), "09")}-{int(m.group(1)):02d}'
            d['hora'] = h24(m.group(3), m.group(4), m.group(5))
            _fin = h24(m.group(6), m.group(7), m.group(8))
            a = int(d['hora'][:2]) * 60 + int(d['hora'][3:])
            b = int(_fin[:2]) * 60 + int(_fin[3:])
            # ERRATA DEL SITIO: la segunda charla dice «11:00am a 12:30am», y
            # 12:30 de la madrugada daría una duración negativa. El mediodía es
            # pm. Se corrige y se deja dicho, no se calla.
            if b <= a:
                b += 12 * 60
                d['_nota_hora'] = f'la web escribe «{m.group(6)}:{m.group(7)}{m.group(8)}m»; se lee como pm'
            d['duracion_min'] = b - a
        d['sede'], d['sala'] = SEDE
        # Panelistas y moderación: la página los rotula, no hay que adivinar
        # quién es quién. Cada nombre viene en su línea y el cargo en la
        # siguiente, empezando por «·» o «-».
        bloque = L[k:anclas[i + 1] if i + 1 < len(anclas) else fin]
        def gente(rotulo):
            try:
                j = next(x for x, y in enumerate(bloque) if y.startswith(rotulo))
            except StopIteration:
                return []
            out = []
            for y in bloque[j + 1:]:
                if re.match(r'^(Panelistas|Modera|Inscrib)', y):
                    break
                if re.match(r'^[·\-]', y):
                    if out:
                        out[-1]['cargo'] = y.lstrip('·- ').strip()
                    continue
                m2 = re.match(r'^(.+?)\s*·\s*(.+)$', y)
                if m2:
                    out.append({'nombre': m2.group(1).strip(), 'cargo': m2.group(2).strip()})
                else:
                    out.append({'nombre': y.strip()})
            return out
        d['panelistas'] = gente('Panelistas')
        d['modera'] = gente('Modera')
        cuerpo = [x for x in bloque if len(x) > 160]
        if cuerpo:
            d['sinopsis'] = ' '.join(cuerpo)
        charlas.append(d)

    h = bajar()
    m = re.search(r'href="([^"]*(?:bit\.ly|forms\.gle)[^"]*)"', h)
    # La FOTO de cada charla: el festival subió una por conversación y van en
    # orden en la página, cada una entre el título de su charla y el de la
    # siguiente. Se asigna por POSICIÓN en el HTML, que aquí es inequívoca, y no
    # por nombre de archivo («IMG_7907.JPG.jpg» no dice nada).
    _titulos = [d['titulo'].split(' | ')[0][:34] for d in charlas]
    _cortes = []
    for t in _titulos:
        k = h.find(t, 100000)
        _cortes.append(k if k > 0 else len(h))
    _imgs = [(mm.start(), re.sub(r'-\d+x\d+(\.\w+)$', r'\1', mm.group(1)))
             for mm in re.finditer(r'<img[^>]+src="(https://narrarelfuturo\.com/wp-content/uploads/[^"]+)"', h)
             if not re.search(r'cropped-|_perfil|logo|favicon|CONEJOS|Mesa-de-trabajo', mm.group(1), re.I)]
    for i, d in enumerate(charlas):
        ini = _cortes[i]
        fin_ = _cortes[i + 1] if i + 1 < len(_cortes) else len(h)
        propias = [u for pos, u in _imgs if ini < pos < fin_]
        if propias:
            d['imagen'] = propias[0]
        if m:
            d['registration_url'] = re.sub(r'^http://', 'https://', m.group(1))
            d['acceso'] = 'Entrada gratis con inscripción'

    os.makedirs(ST, exist_ok=True)
    io.open(f'{ST}/narrarelfuturo-2026-charlas.json', 'w', encoding='utf-8').write(
        json.dumps({'_provenance': provenance(
            'narrarelfuturo.com/charlas-2026 — la franja de charlas, ausente de la parrilla',
            nota='se comprobó que /programa-2026/ no menciona ninguna de las dos'),
            'charlas': charlas}, ensure_ascii=False, indent=1) + '\n')
    print(f'── narrarelfuturo-2026-charlas.json · {len(charlas)} charlas')
    for d in charlas:
        print(f"  {d.get('dia')} {d.get('hora')} ({d.get('duracion_min')} min)  {d['titulo'][:52]:<54} "
              f"{len(d.get('panelistas') or [])} panelistas · {'sinopsis' if d.get('sinopsis') else 'SIN sinopsis'}")
    falt = [d['titulo'] for d in charlas if not (d.get('dia') and d.get('hora') and d.get('sede'))]
    if falt:
        print('  ⚠ sin día/hora/sede:', falt)


if __name__ == '__main__':
    main()
