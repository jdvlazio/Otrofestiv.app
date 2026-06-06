# Spec — Auditoría "film" en empty states EN

## Problema
Strings EN usan "film/films" en empty states y mensajes genéricos,
excluyendo eventos, talleres y otros tipos. ES ya usa "título/títulos".

## Criterio aprobado (Content Designer)
- Empty states y mensajes genéricos → "title/titles" o sin sustantivo
- Strings que refieren a un film específico → "film" se mantiene
- Sin (s) — pluralización debe resolverse en JS o con frase sin sustantivo

## 8 keys a modificar (solo EN)
empty_intereses, empty_intereses_2 (ya correcto), empty_vistas,
filter_sin_peliculas, toast_horario_lib, plan_choca,
plan_no_intereses, plan_revisa_planeaste

## Aplica a todos los festivales — vía t()
