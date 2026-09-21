# -*- coding: utf-8 -*-
import re
# Partículas que van en minúscula DENTRO del nombre, nunca al principio.
#
# Las primeras son de NOMBRE DE PERSONA, que es para lo que nació esta función:
# «John de la Cruz», «Ludwig van Beethoven».
#
# Las de la segunda línea son PREPOSICIONES Y ARTÍCULOS de título, y hacían
# falta porque `titular()` también rebaja títulos gritados. Sin ellas,
# «TORMENTA EN LLAMAS» salía «Tormenta En Llamas», con la preposición en alto:
# en español un título va en caja baja salvo nombres propios (Villa del Cine,
# 21 sep 2026). Con ellas sale «Tormenta en llamas».
MINUS = {'de','del','la','las','los','y','da','das','do','dos','van','von','di','du','le','e','el',
         'en','a','al','con','por','para','sin','sobre','un','una','unos','unas',
         'o','u','ni','que','se','su','sus','the','of','and','to','in','on','for'}
def titular(n, minimo=6):
    """MAYÚSCULA SOSTENIDA → Título. Solo toca nombres gritados enteros: si el
    original ya mezcla mayúsculas y minúsculas, se respeta tal cual —puede ser
    una grafía deliberada, como «Gomxz» o «McCalle».

    `minimo` es el largo por debajo del cual NO se toca, y su valor por defecto
    protege a las siglas: DASC, FPFC, ENACC y IA tienen que seguir gritando.
    Se baja SOLO cuando quien llama sabe que su corpus no tiene siglas —los 19
    nombres de programa de Villa del Cine, donde «ECOS» y «VOCES» se quedaban
    en mayúscula al lado de «Destellos» y el resultado era incoherente—."""
    letras=[c for c in n if c.isalpha()]
    if len(letras)<minimo or sum(1 for c in letras if c.isupper())/len(letras) <= 0.85:
        return n
    out=[]
    for i,p in enumerate(re.split(r'(\s+|-)', n)):
        if not p.strip() or p=='-': out.append(p); continue
        b=p.lower()
        out.append(b if (i>0 and b in MINUS) else b[:1].upper()+b[1:])
    return ''.join(out)
