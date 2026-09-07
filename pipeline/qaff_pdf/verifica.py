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


def imprime_dia(lineas, dia):
    """¿Esta página estampa ese día?

    El sello sale del PDF partido de formas distintas según la exportación:
    «17 SEPT.» en una línea, o «SEPT.» / «2026» / «17» en tres y desordenadas.
    Exigirlos juntos hacía fallar una página que SÍ lo imprime. Se acepta el
    número suelto solo si hay un «SEPT» cerca — si no, cualquier 17 del texto
    (una duración, una dirección) daría el día por bueno, que es ablandarlo."""
    d = int(dia)
    up = [l.upper() for l in lineas]
    for i, l in enumerate(up):
        if re.search(rf'\b{d}\s*SEPT', l) or f'{d} DE SEPTIEMBRE' in l:
            return True
        if l.strip().rstrip('.') == str(d):
            vecinas = up[max(0, i - 2):i + 3]
            if any('SEPT' in v for v in vecinas):
                return True
    return False
fallos = []

for sede, sala, dia, hora, obras, pag in pr.FUNCIONES:
    # La fuente puede ser MÁS de una página: el Museo Nacional y la Universidad
    # Nacional no tienen parrilla, así que el día sale de la ficha (que lo lleva
    # estampado) y la hora y la sala de la página del Diálogo de ese mismo día.
    pags = pag if isinstance(pag, tuple) else (pag,)
    pl = ' '.join(l for q in pags for l in P[str(q)])
    txt = n(pl)
    for o in obras:
        if n(o) not in txt:
            fallos.append(f'p{pags}: la obra «{o}» ({sede} {dia} {hora}) NO está en la página')
    if not any(h in pl for h in hora12(hora)):
        fallos.append(f'p{pags}: la hora {hora} ({sede} {dia}) no aparece impresa')
    if not imprime_dia([l for q in pags for l in P[str(q)]], dia):
        fallos.append(f'p{pags}: el día {dia} no aparece impreso')
    if sala and n(sala.split(' - ')[0]) not in txt:
        fallos.append(f'p{pags}: la sala «{sala}» no aparece impresa')

for tipo, sede, sala, dia, ini, fin, titulo, quien, pag in pr.ACTIVIDADES:
    pags = pag if isinstance(pag, tuple) else (pag,)
    pl = ' '.join(l for q in pags for l in P[str(q)])
    txt = n(pl)
    if not imprime_dia([l for q in pags for l in P[str(q)]], dia):
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
