import io,os,re
RUIDO=re.compile(r'^(?:[A-ZÁÉÍÓÚÑ](?:\s+[A-ZÁÉÍÓÚÑ])*\.?|[.\s·–—-]+)$')
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
    Una línea de mayúsculas sueltas separadas por espacios NUNCA es contenido."""
    out=[]
    for l in c.split('\n'):
        s=' '.join(l.split())
        if not s or RUIDO.match(s): continue
        out.append(s)
    return out
