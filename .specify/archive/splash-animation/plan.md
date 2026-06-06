# Plan — Splash animation: fix PWA

## Arquitectura de la solución

### Principio de diseño
**Todos los elementos son visibles por defecto.**
La animación es ADITIVA — JS añade los efectos sobre elementos ya visibles.
Si JS o CSS falla en cualquier punto, el splash está completamente funcional.

### Cambio 1: Eliminar animation-fill-mode:both del CSS
Las barras y los fades NO usarán `fill-mode:both` (que requiere backwards fill).
En su lugar:
- Las barras son creadas por JS con `style.transform='scaleY(1)'` inmediatamente
- Transición CSS aplica cuando se añade la clase (de scaleY(1) a scaleY(0))
- `.splash-action` y `.splash-tagline` también controlados via JS style

### Cambio 2: Arquitectura JS de 3 fases

**Fase 0 (inmediata):** JS crea barras con scaleY(1) inline y oculta chars/action/tagline via style inline.

**Fase 1 (doble rAF):** Añade la clase `splash-animating` que triggea las transiciones CSS hacia el estado visible.

**Fase 2 (fallback via animationend):** Si `.splash-bar-top` no dispara `animationend` en 1500ms, JS elimina las barras y fuerza visibilidad de todos los elementos — garantía de que el splash nunca queda roto.

### Cambio 3: CSS sin backwards fill
```css
/* Barras: default scaleY(0), JS las pone en scaleY(1) inline */
.splash-bar-top { ... transform:scaleY(0); transition:transform .65s ... }
.splash-bar-top.bar-active { transform:scaleY(0); } /* la clase triggea la transición */
```

O más simple: usar `transition` en lugar de `animation` para las barras.
JS setea `scaleY(1)` → doble rAF → JS remueve el inline style → CSS default `scaleY(0)` toma efecto via transition.

### Cambio 4: Fuentes en SW STATIC_ASSETS
Añadir `/fonts/plus-jakarta-sans-latin-{400,500,600,700,800}-normal.woff2` a STATIC_ASSETS.
El SW ya maneja el install event con `c.addAll(STATIC_ASSETS)`.

### Protección validate.py
Siempre correr `python3 validate.py` sin pipe. Verificar returncode=0 antes de git add.

## Archivos a modificar
- `index.html` — CSS splash (bars/action/tagline animation) + JS _initSplashAnimation
- `sw.js` — STATIC_ASSETS (fonts)
- Tras cambio sw.js: regenerar via bump-version.js
