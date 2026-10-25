#!/usr/bin/env python3
"""villadeleyvaiff-2026-verificar.py — el catálogo contra las láminas, por un
camino que NO pasa por la transcripción a ojo.

1. Construye el --ojos desde el catálogo y corre pipeline/ig-lecturas.py sobre
   los 5 carruseles (A Vision, B sin corrector, C al doble, D ALT, E la mirada):
   el informe de discrepancias queda en fuentes/ig/villadeleyvaiff-2026-lecturas.json.
2. Cobertura en los dos sentidos, por TOKENS del OCR (A ∪ B ∪ C), sin parser:
   - cada palabra del título y del director del catálogo aparece pintada en
     SU lámina;
   - toda lámina de obra (ni portada ni cierre) tiene una obra del catálogo, y
     la lámina con «Dir.» que no esté en el catálogo hace fallar.
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
    sc = o['_src']['url'].rstrip('/').split('/')[-1]
    lam = os.path.basename(o['_src']['lamina'])
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
n = sum(len(v) for v in por_sc.values())
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ las {n} obras están pintadas en su lámina (A∪B∪C), y ninguna lámina con «Dir.» queda fuera')
