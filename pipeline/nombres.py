# -*- coding: utf-8 -*-
import re
# Partículas que van en minúscula DENTRO del nombre, nunca al principio.
MINUS = {'de','del','la','las','los','y','da','das','do','dos','van','von','di','du','le','e','el'}
def titular(n):
    """MAYÚSCULA SOSTENIDA → Título. Solo toca nombres gritados enteros: si el
    original ya mezcla mayúsculas y minúsculas, se respeta tal cual —puede ser
    una grafía deliberada, como «Gomxz» o «McCalle»."""
    letras=[c for c in n if c.isalpha()]
    if len(letras)<6 or sum(1 for c in letras if c.isupper())/len(letras) <= 0.85:
        return n
    out=[]
    for i,p in enumerate(re.split(r'(\s+|-)', n)):
        if not p.strip() or p=='-': out.append(p); continue
        b=p.lower()
        out.append(b if (i>0 and b in MINUS) else b[:1].upper()+b[1:])
    return ''.join(out)
