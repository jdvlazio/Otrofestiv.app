#!/usr/bin/env python3
"""semanacine-2026-verificar.py — lo que se va a publicar, contra la lámina.

Relee la lámina «Programación 2026» (fuentes/semanacine-2026/programacion-DfKgpBVpyUt.jpg)
por su cuenta, con DOS motores de OCR (Vision y Tesseract), sin pasar por el
crudo, y exige para cada función del JSON:
  · su hora está impresa en la lámina («8:30 am», «12 pm», «6:30 pm»…), y
  · su título (o, en los conversatorios, el nombre entre comillas) también.
Y al revés: cada hora impresa tiene su función, salvo el sábado 7, que no
trae hora (no se publica: decisión de Juan, 2 nov). Sale 1 si algo no cuadra.
"""
import difflib, io, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import ocr  # noqa: E402

LAMINA = f'{REPO}/fuentes/semanacine-2026/programacion-DfKgpBVpyUt.jpg'


def plano(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
    return ' '.join(re.sub(r'[^0-9a-zñ]+', ' ', s).split())


def horas(t):
    out = set()
    for h, m, mer in re.findall(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.\s?m|p\.\s?m)\b', t, re.I):
        hh = int(h) % 12 + (12 if mer.lower().startswith('p') else 0)
        out.add(f'{hh:02d}:{m or "00"}')
    return out


def lee(texto, b):
    """Cada palabra del título está en la lámina (exacta o casi). Por palabras y no
    de corrido: Vision intercala la hora en medio del título partido en dos renglones."""
    palabras = set(plano(texto).split())
    return all(w in palabras or difflib.get_close_matches(w, palabras, 1, 0.8)
               for w in plano(b).split() if len(w) > 2)


def tesseract(p):
    """Tesseract sobre la lámina al doble, en color y en grises con varios umbrales:
    se juntan las lecturas."""
    from PIL import Image, ImageOps
    import tempfile
    im = Image.open(p).convert('RGB')
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    g = ImageOps.grayscale(im)
    # las horas van en recuadros amarillos con texto oscuro: umbrales 90 y 120, y el
    # modo de texto disperso (--psm 11), que es como Tesseract las encuentra
    out = []
    variantes = [(im, '3'), (g.point(lambda x: 255 if x > 150 else 0), '3'),
                 (ImageOps.invert(g).point(lambda x: 255 if x > 105 else 0), '3')]
    variantes += [(g.point(lambda x, t=t: 255 if x > t else 0), psm) for t in (90, 120) for psm in ('6', '11')]
    for v, psm in variantes:
        with tempfile.NamedTemporaryFile(suffix='.png') as f:
            v.save(f.name)
            out.append(subprocess.run(['tesseract', f.name, 'stdout', '--psm', psm],
                                      capture_output=True, text=True).stdout)
    return '\n'.join(out)


# lo que la lámina imprime distinto y tiene fuente que manda
EXCEPCIONES = {
    # la lámina dice 5 pm; la pieza propia del conversatorio, 4:00 pm, y Arturo Murgas
    # (organización) lo confirmó por correo el 2 nov: «4 pm»
    ('2026-11-06', '16:00'): '17:00',
}


def main():
    vision = '\n'.join(ocr.leer([LAMINA])[LAMINA])
    tess = tesseract(LAMINA)
    d = json.load(io.open(f'{REPO}/festivals/semanacine-2026.json', encoding='utf-8'))
    malos, usadas = [], set()
    for f in d['films']:
        m = re.search(r'"([^"]+)"', f['title'])
        tit = m.group(1) if m else f['title']
        for nombre, txt in (('Vision', vision), ('Tesseract', tess)):
            impresa = EXCEPCIONES.get((f['day'], f['time']), f['time'])
            if impresa not in horas(txt):
                malos.append(f"{f['day']} {f['time']} «{f['title']}»: {nombre} no lee esa hora")
            if not lee(txt, tit):
                malos.append(f"{f['day']} {f['time']} «{f['title']}»: {nombre} no lee el título")
        usadas.add(EXCEPCIONES.get((f['day'], f['time']), f['time']))
    sobra = horas(vision) - usadas
    if sobra:
        malos.append(f'horas impresas sin función en el JSON: {sorted(sobra)}')
    if malos:
        print('✗ semanacine-2026: el JSON no cuadra con la lámina')
        for x in malos:
            print('  ·', x)
        sys.exit(1)
    print(f"✓ semanacine-2026: {len(d['films'])} funciones, hora y título leídos por Vision y Tesseract en la lámina")


if __name__ == '__main__':
    main()
