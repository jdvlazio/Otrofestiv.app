#!/usr/bin/env python3
"""villadeleyvaiff-2026-verificar.py — el catálogo contra las láminas, por un
camino que NO pasa por la transcripción a ojo.

1. Construye el --ojos desde el catálogo y corre pipeline/ig-lecturas.py sobre
   los 8 carruseles (A Vision, B sin corrector, C al doble, D ALT, E la mirada):
   el informe de discrepancias queda en fuentes/ig/villadeleyvaiff-2026-lecturas.json.
2. Cobertura en los dos sentidos, por TOKENS del OCR (A ∪ B ∪ C), sin parser:
   - cada palabra del título y del director del catálogo aparece pintada en
     SU lámina;
   - toda lámina de obra (ni portada ni cierre) tiene una obra del catálogo, y
     la lámina con «Dir.» que no esté en el catálogo hace fallar.
3. Contra los PDF de la web (fuentes/villadeleyvaiff-2026/, capa de texto, sin OCR):
   cada «Dir.» de cada PDF está en el catálogo con esa sección y cada obra del
   catálogo está en el PDF de su sección. La pág. 6 de Cortos Internacional es
   una imagen sin texto («Los chorros», mirada a ojo): se declara en PAGINA_IMAGEN.
"""
import io, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = f'{REPO}/festivals/staging/villadeleyvaiff-2026-catalogo.json'
SALIDA = f'{REPO}/fuentes/ig/villadeleyvaiff-2026-lecturas.json'
OJOS = f'{REPO}/fuentes/ig/villadeleyvaiff-2026-ojos.json'


def sin_marcas(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


def palabras(s):
    return {w for w in re.findall(r'[a-z0-9]+', sin_marcas(s)) if len(w) > 1}


obras = json.load(io.open(CAT, encoding='utf-8'))['obras']
por_sc = {}
for o in obras:
    for src in (o['_src'], o['_src'].get('tambien')):
        if not src or 'lamina' not in src:
            continue
        sc = src['url'].rstrip('/').split('/')[-1]
        lam = os.path.basename(src['lamina'])
        por_sc.setdefault(sc, {})[lam] = f"{o['titulo'].upper()}\nDir. {o['director']}\n{o['pais'].replace(', ', ' - ')}"

io.open(OJOS, 'w', encoding='utf-8').write(json.dumps(por_sc, ensure_ascii=False, indent=1))
if '--sin-ocr' not in sys.argv or not os.path.exists(SALIDA):
    subprocess.run([sys.executable, f'{REPO}/pipeline/ig-lecturas.py', *por_sc,
                    '--ojos', OJOS, '--salida', SALIDA], check=True)
lect = json.load(io.open(SALIDA, encoding='utf-8'))

fallos = []
for sc, lams in por_sc.items():
    L = lect[sc]['lecturas']
    todas = sorted({k for n in ('A·vision', 'B·sin-corrector', 'C·al-doble') for k in L[n]})
    for lam in todas:
        ocr = ' '.join(L[n].get(lam, '') for n in ('A·vision', 'B·sin-corrector', 'C·al-doble'))
        if lam in lams:
            titulo, dire, _ = lams[lam].split('\n')
            falta = (palabras(titulo) | palabras(dire)) - palabras(ocr) - {'dir'}
            if falta:
                fallos.append(f'{sc}/{lam}: «{titulo} / {dire}» — no pintado: {sorted(falta)}')
        elif re.search(r'\bDir\.', ocr):
            fallos.append(f'{sc}/{lam}: lámina con «Dir.» que NO está en el catálogo')
PDFS = {'Competencia Escuelas': 'cortos-escuelas', 'Competencia Corto Experimental': 'cortos-experimental',
        'Competencia Corto Documental': 'cortos-documental', 'Competencia Largo Documental': 'largos-documental',
        'Competencia Corto Internacional': 'cortos-internacional', 'Competencia Corto Animación': 'cortos-animacion',
        'Competencia Corto Festivalito': 'cortos-festivalito', 'Competencia Corto Profesional Colombia': 'cortos-colombia'}
PAGINA_IMAGEN = {'Los chorros'}
for seccion, nombre in PDFS.items():
    txt = subprocess.run(['pdftotext', f'{REPO}/fuentes/villadeleyvaiff-2026/{nombre}.pdf', '-'],
                         capture_output=True, text=True, check=True).stdout
    aqui = [o for o in obras if seccion in (o['seccion'], o.get('_seccion_tambien'))]
    for o in aqui:
        if o['titulo'] in PAGINA_IMAGEN:
            continue
        falta = (palabras(o['titulo']) | palabras(o['director'])) - palabras(txt)
        if falta:
            fallos.append(f'PDF {nombre}: «{o["titulo"]}» no está: {sorted(falta)}')
    leidos = len(re.findall(r'^Dir\.', txt, re.M)) + len(PAGINA_IMAGEN & {o['titulo'] for o in aqui})
    if leidos != len(aqui):
        fallos.append(f'PDF {nombre}: {leidos} obras y {len(aqui)} en el catálogo')
n = sum(len(v) for v in por_sc.values())
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ las {n} apariciones están pintadas en su lámina (A∪B∪C), ninguna lámina con «Dir.» queda fuera, y las {len(obras)} obras cuadran con los 8 PDF de la web')
