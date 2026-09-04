import io,os,re
RUIDO=re.compile(r'^(?:[A-ZÁÉÍÓÚÑ](?:\s+[A-ZÁÉÍÓÚÑ])*\.?|[.\s·–—-]+)$')
# El lomo vertical es SIEMPRE la misma marca girada 90°, pero cada exportación de
# Canva la parte distinto: en el PDF de agosto salía con las letras separadas
# («Q U I B D O») y en el del 4 sep salen pegadas y dobladas («QQUUIIBBDDOO»).
# Un filtro escrito contra UNA de las dos formas deja pasar la otra, y entonces
# 70 páginas «cambian» sin que nadie haya tocado el programa. Se juzga por lo que
# la línea DICE al colapsar las letras dobles: si es un trozo de la marca, es lomo.
MARCA = 'quibdoafricafilmfestivalcom' * 3
# Los trozos cortos se declaran a la vista: con el criterio de substring habría
# que bajar el umbral a 4 y entonces «ÁFRICA», que sí es contenido, caería.
LOMO_CORTO = {'aa', 'll', 'mf', 'lcom', 'll.com', 'l.com', 'ww', 'www'}
def _es_lomo(l):
    x = re.sub(r'[^a-z]', '', l.lower())
    if not x:
        return False
    if l.strip().lower() in LOMO_CORTO or x in LOMO_CORTO:
        return True
    y = re.sub(r'(.)\1', r'\1', x)          # QQUUIIBBDDOO → quibdo
    return len(x) >= 8 and (x in MARCA or y in MARCA)
def paginas(p=None):
    # el texto va versionado junto al crudo: un generador que lee de un
    # scratchpad no se puede volver a correr mañana
    p = p or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '..', '..', 'festivals', 'staging',
                          'qaff-2026-bogota-programa.txt')
    txt=io.open(p,encoding='utf-8').read()
    return {n:c for n,c in re.findall(r'\n--- p(\d+)\n(.*?)(?=\n--- p\d+\n|\Z)',txt,re.S)}
def limpia(c):
    """El lomo vertical del programa sale del PDF como letras sueltas repetidas
    («T T / V V / I I …»): es la marca «FESTIVAL DE CINE AFRO QUIBDÓ» girada 90°.
    Una línea de mayúsculas sueltas separadas por espacios NUNCA es contenido.

    Cada exportación de Canva parte el lomo distinto —separado en el PDF de
    agosto, pegado y doblado en el del 4 sep—, así que además de la forma suelta
    se reconoce por lo que DICE al colapsar las dobles (_es_lomo)."""
    out=[]
    for l in c.split('\n'):
        s=' '.join(l.split())
        if not s or RUIDO.match(s) or _es_lomo(s): continue
        out.append(s)
    return out
