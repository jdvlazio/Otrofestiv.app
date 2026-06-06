# Spec — normTitle: normalización global de apostrophes y comillas tipográficas

## Problema
Los JSONs de festival contienen comillas tipográficas (U+2019 ', U+2018 ',
U+201C ", U+201D ") en campos title. El código usa igualdad estricta
(===) para lookups en FILMS, watchlist, prioritized, watched, filmRatings.
Cualquier mismatch de un carácter rompe silenciosamente toda la cadena:
poster no carga, sheet no abre, prioridades aparecen sin imagen.

## Causa raíz
Dos contratos implícitos nunca documentados:
1. Los JSONs pueden traer cualquier variante tipográfica
2. El código asume igualdad estricta de strings

## Solución

### normTitle(t) — función pura
Convierte U+2019→' U+2018→' U+201C→" U+201D→" y cualquier
otra variante tipográfica a su equivalente ASCII.
Definida una vez, cerca de las utils de texto.

### loadFestival — punto único de normalización
FILMS = films.map(f => ({...f, title: normTitle(f.title)}))
Un solo punto. Todo lo que deriva de FILMS (dataset.title, Sets,
ratings) hereda el título normalizado automáticamente.

### validate.py — check [title-normalization]
Detecta cualquier título en festivals/*.json que contenga
caracteres U+2019/U+2018/U+201C/U+201D. Error con lista exacta.
Bloquea push. Previene regresión en festivales futuros.

### Script normalize-festival-titles.py
Normaliza los JSONs actuales en batch.
Genera log de qué títulos fueron modificados.
Se corre una vez por festival en onboarding.

## Criterios de aceptación
- [ ] normTitle definida y documentada
- [ ] loadFestival normaliza FILMS al cargar
- [ ] FILMS.find con título tipográfico → encuentra film
- [ ] watchlist/prioritized con título tipográfico → match correcto
- [ ] validate.py check [title-normalization] detecta U+2019 en JSON
- [ ] Script normaliza los 4 JSONs actuales, log de cambios
- [ ] validate.py 11/11 (o 12/12 con nuevo check)
- [ ] QA browser: Opening Night y Finnegan's muestran poster en Priorities
- [ ] Commit atómico con documentación

---

## Fase 2 — normTitle en puntos de entrada (CRIT-01)

### Problema
normTitle normaliza FILMS al cargar (loadFestival) pero no normaliza
títulos que entran desde el UI o desde localStorage.
Resultado: Sets tienen U+2019, FILMS tiene U+0027 → lookup falla.

### Estrategia — 5 puntos de entrada, no 30 write points

1. loadState() — restaura Sets desde localStorage (datos históricos)
   Normalizar: watchlist, watched, prioritized al parsear de JSON
   
2. togglePelWL(title) — título viene del DOM vía pel-sheet
   Normalizar: title = normTitle(title) al inicio de la función

3. togglePelPrio(title) — título viene del DOM vía pel-sheet
   Normalizar: title = normTitle(title) al inicio de la función

4. toggleWatched(title) — título viene del DOM vía pel-sheet
   Normalizar: title = normTitle(title) al inicio de la función
   
5. addSuggestion(title) — título viene del DOM vía sugerencias
   Normalizar: title = normTitle(title) al inicio de la función

### Invariante resultante
Todo título que entra al sistema pasa por normTitle.
Ningún write point interno necesita cambio.
Cualquier función nueva que llame a estas 5 hereda la garantía.

### Criterios de aceptación Fase 2
- [ ] loadState normaliza watchlist, watched, prioritized al cargar
- [ ] Las 4 funciones públicas normalizan title al inicio
- [ ] FILMS.find con U+2019 encuentra el film (porque FILMS tiene U+0027)
- [ ] Priority chips muestran poster con títulos apostrophe
- [ ] Algoritmo termina con prioridades apostrophe — P5.1 PASS
- [ ] validate.py 12/12
- [ ] QA browser: P3.1 y P5.1 pasan
- [ ] Commit atómico
