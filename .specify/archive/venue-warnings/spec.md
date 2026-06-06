# Spec — Venue warnings audit

## Problemas identificados

### 1. Velocidad transit subestimada
venueTravelMins usa 15 km/h para transit. NYC efectivo ≈ 10 km/h
(subway + overhead de caminar, esperar, transferir).
Aplica main thread (L4261) y worker (L7851).

### 2. Warnings hardcodeados en español
"~0 min hasta la siguiente", "~X min en carro entre estas sedes",
"Q&A · si te quedas no llegas", "Q&A · si te quedas tienes ~X min"
No usan t() — rotos en modo EN.

### 3. "en carro" para transit
FESTIVAL_TRANSPORT='transit' → warning dice "en carro". Incorrecto.
transit → sin modo explícito (el tiempo habla solo).
walking → "a pie". driving → "en carro".

### 4. Warning "~0 min" demasiado discreto
0 min entre funciones = físicamente inviable. Actualmente ámbar.
Debe ser rojo + copy que comunique imposibilidad, no solo el tiempo.

## Criterios de aceptación
- [ ] transit speed: 15 → 10 km/h en main thread y worker
- [ ] 4 strings de warning con t() keys ES+EN
- [ ] modo: transit → '' | walking → t('warn_a_pie') | driving → t('warn_en_carro')
- [ ] gap=0 con venues distintos → rojo + "no da tiempo llegar"
- [ ] validate.py 11/11
- [ ] QA browser: THU 11 muestra warning correcto en EN y ES
