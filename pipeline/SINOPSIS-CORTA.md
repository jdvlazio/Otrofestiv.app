---
name: sinopsis-corta
description: Condensar la sinopsis de una obra a 350 caracteres sin cambiar su idea, con un redactor y un verificador distintos. Úsalo al montar un festival con sinopsis largas, cuando validate.py [sinopsis-larga] frene, o cuando Juan pida acortar sinopsis.
---

# Sinopsis corta

La app se lee en un celular. La síntesis **reescribe**, no recorta; el original queda
entero en el almacén. Dueño: `pipeline/sinopsis_cortas.py`.

## Pasos
1. `python3 pipeline/sinopsis_cortas.py --pendientes <festival> > lote.json` (lotes de máximo 15).
2. **Redactar** `corta` de cada una, con la guía. Si `original_cortado`, recuperar primero el original en su fuente; si no aparece, se deja fuera y se avisa.
3. `--revisar lote.json` hasta que no objete. Esto NO prueba fidelidad.
4. **Verificar con otro agente** que no redactó (Agent general-purpose), con el encargo de abajo.
5. Corregir y volver a verificar **las corregidas**. Dos rondas sin «fiel» → la lee Juan.
6. Anotar `redacta`, `verifica` (distintos) y `veredicto: fiel`. `--registrar lote.json`.
7. `catalogo_construir.py --escribir`, `sinopsis_unicas.py --aplicar <festival> --escribir`, `sinopsis_cortas.py --congelar`.

El primer lote de un festival que Juan no haya visto se le muestra, antes y después, antes de publicar.

## Español e inglés
Toda obra con sinopsis la tiene en los dos idiomas (`[sinopsis-par]`). Al acortar, el redactor deja **las dos** desde el original, y el verificador compara cada una contra el original y entre sí: mismos hechos, mismo tono. Se traduce el sentido, no las palabras: español de Colombia, sin calcos. Si existe la sinopsis oficial en el otro idioma, manda. El género de una persona real no se supone.

## Guía de redacción (máximo 350; lo natural es 220–320)
Antes de escribir, anota del original: **quién**, **qué pasa o qué mira**, **qué está en juego**, **forma** (documental, experimental, animación: si la dice) y **tono**. Eso es lo que debe sobrevivir.
- Solo lo que dice el original. Ni datos de memoria, ni un sinónimo que suba o baje la intensidad.
- **Cada acción con su sujeto**: si lo hace la película, no se lo atribuyas a los personajes.
- No crear causas ni simultaneidades («por eso», «mientras tanto») que el original no tiene.
- Conservar la palabra cargada que da el tono («turbador», «absurdo»), antes que un dato.
- Se va: premios, trayectoria, opinión del festival, nombres secundarios, fechas sueltas, repetición, el final.
- Si el original abre con «[Título] es…», empezar por la obra misma.
- Nombres propios tal cual. Frases cortas. Voseo o tuteo, primera persona y tercera: la del original.
- Una lista de ideas sin conexión no es una sinopsis: debe leerse de corrido en voz alta.

## Encargo del verificador
> Lee <archivo>: cada obra trae `original` y `corta`. Eres verificador exigente. No uses nada fuera del original ni edites archivos. Por obra: (1) lo que la corta dice y el original no, o cambia (quién hace qué, causa, tiempo, cantidad, intensidad), citando ambos; (2) la idea CENTRAL perdida (no los detalles: 350 caracteres obligan a perderlos); (3) tono; (4) español y lectura de corrido; (5) si cuenta el final. Veredicto: fiel / con ajuste (da la frase corregida) / no fiel. No inventes problemas.

Lista de control tomada de la skill de resumen de seb1n/awesome-ai-agent-skills (MIT): cifras, nombres propios y relaciones causales contra la fuente.

## Errores reales (piloto del 23 nov 2026: 9 redactadas, 2 fieles a la primera)
- *Analogue natives*: «reflexionan sobre su oficio y el arte de vivir en condiciones precarias». Lo segundo lo mira el filme, no ellos. **Sujeto cambiado.**
- *Pulse*: «al poco rato lo encuentra colgado». El original lo encuentra vivo y extraño, y después muere; «mientras tanto» era «por otro lado». **Secuencia y simultaneidad inventadas.**
- *La última ronda en Venecia*: «sus planes de vida y amor». Son los de Giulio. **Posesivo ambiguo.**
- *Hansel and Gretel Get Kicked Out*: se fue «subvierte la mirada criminalizadora», que es la idea. **Central perdida.**
