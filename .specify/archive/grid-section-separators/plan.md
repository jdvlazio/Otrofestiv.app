# Plan — Separadores de sección en Grid TODO

## Decisión de arquitectura
Clase nueva `.poster-grid-sep` con `grid-column: 1/-1`. Reutiliza tokens existentes del design system — no crea valores nuevos. Patrón visual: `.sec-drop-hdr` (ya existe en dropdown de sección).

## CSS
Nueva clase en el bloque de `.poster-grid`:
```css
.poster-grid-sep{
  grid-column:1/-1;
  padding:var(--sp-4) var(--sp-2) var(--sp-1);
  font-size:var(--t-label);
  font-weight:var(--w-display);
  letter-spacing:.08em;
  color:var(--gray2);
  text-transform:uppercase;
  pointer-events:none;
  user-select:none;
}
```

## JS — `renderPeliculaView()`
Condición: solo inyectar separadores cuando `activeDay === 'all'`.

En el `entries.map(...)` que construye el HTML del grid, trackear la sección anterior y emitir el separador cuando cambia:
```js
let _prevSec = null;
// dentro del map:
const _secLabel = f.section ? f.section.replace(/^[\p{Emoji}\s]+/u,'').trim() : '';
const _sep = (activeDay==='all' && f.section && f.section !== _prevSec)
  ? `<div class="poster-grid-sep">${_secLabel}</div>`
  : '';
_prevSec = f.section || _prevSec;
// emitir _sep + card
```

## Archivos a tocar
- `index.html` — CSS: 1 clase nueva. JS: ~5 líneas en `renderPeliculaView()`

## Riesgos
- El `map()` es funcional — necesita un workaround para trackear estado entre iteraciones (usar `reduce` o variable externa al map)
