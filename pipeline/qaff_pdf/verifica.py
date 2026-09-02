# -*- coding: utf-8 -*-
"""Cada dato de programa.py contra la página del PDF que dice ser su fuente.

Un guardián que solo comprueba la FORMA de la tabla no sirve de nada aquí: lo
que puede estar mal es el CRUCE —una obra atribuida a la franja de al lado— y
eso solo se ve yendo a la página. Si el festival reimprime el programa, esto
falla, que es exactamente lo que debe hacer."""
import re, sys, os, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limpia import paginas, limpia
import programa as pr

def n(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())

def hora12(h):
    """'19:30' → las formas en que el programa la imprime: «7:30 pm», «7:30pm»."""
    H, M = map(int, h.split(':'))
    h12 = H % 12 or 12
    return [f'{h12}:{M:02d}']

P = {k: limpia(v) for k, v in paginas().items()}
fallos = []

for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
    txt = n(' '.join(P[str(pag)]))
    for o in obras:
        if n(o) not in txt:
            fallos.append(f'p{pag}: la obra «{o}» ({sede} {dia} {hora}) NO está en la página')
    if not any(h in ' '.join(P[str(pag)]) for h in hora12(hora)):
        fallos.append(f'p{pag}: la hora {hora} ({sede} {dia}) no aparece impresa')
    if f'{int(dia)} DE SEPTIEMBRE' not in ' '.join(P[str(pag)]).upper():
        fallos.append(f'p{pag}: el día {dia} no aparece impreso')
    if sala and n(sala.split(' - ')[0]) not in txt:
        fallos.append(f'p{pag}: la sala «{sala}» no aparece impresa')

for tipo, sede, sala, dia, ini, fin, titulo, quien, pag in pr.ACTIVIDADES:
    pags = pag if isinstance(pag, tuple) else (pag,)
    pl = ' '.join(l for q in pags for l in P[str(q)])
    txt = n(pl)
    up = pl.upper()
    if not (re.search(rf'\b{int(dia)}\s*SEPT', up) or f'{int(dia)} DE SEPTIEMBRE' in up
            or re.search(rf'\b{int(dia)}\s+SEPTIEMBRE', up)):
        fallos.append(f'p{pags}: «{titulo}» dice día {dia} y la página no lo imprime')
    if not any(h in pl for h in hora12(ini)):
        fallos.append(f'p{pags}: «{titulo}» dice {ini} y la página no lo imprime')
    for quien_uno in re.split(r'·', quien):
        # «Modera X» / «Moderan A, B y C»: el verbo va en mayúscula y NO es un
        # apellido. Sin quitarlo, el guardián acusa a diez páginas de no imprimir
        # un nombre que nunca dijeron —un falso positivo del propio guardián.
        quien_uno = re.sub(r'^\s*Moderan?\s+', '', quien_uno)
        for nombre in re.findall(
                r"[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ'’-]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ'’-]+)+",
                quien_uno):
            if n(nombre) not in txt:
                fallos.append(f'p{pags}: «{titulo}» nombra a {nombre} y la página no lo imprime')

if __name__ == '__main__':
    print(f'{len(pr.FUNCIONES)} funciones · {sum(len(f[4]) for f in pr.FUNCIONES)} cupos · '
          f'{len(pr.ACTIVIDADES)} actividades verificadas contra el PDF')
    if fallos:
        print(f'\n✗ {len(fallos)} fallos:')
        for f in fallos: print('   ', f)
        sys.exit(1)
    print('\n✓ todo lo transcrito está en la página que declara')
