# Plan — data-title refactor

## Fase 1: Funciones primarias (openPelSheet, openRatingSheet)
Estas son las más críticas — afectan directamente la experiencia del usuario.

### 1a. Añadir clase js-open-pel a todos los cards que abren pel-sheet
Todos los elementos con onclick="openPelSheet('${safeT}')" →
class="... js-open-pel" data-title="${f.title}"

### 1b. Añadir event listener delegado
```js
document.getElementById('grid')?.addEventListener('click', e => {
  const el = e.target.closest('.js-open-pel');
  if(el) openPelSheet(el.dataset.title);
});
```
Pero grid se re-renderiza. Mejor: listener en document, filtrar por clase.

### 1c. openPelSheet sigue recibiendo string — sin cambio de firma
El decode textarea ya está como safety net.

## Fase 2: Funciones secundarias
togglePriority, togglePelPrio, toggleWatched — misma estrategia con
data-* attrs específicos.

## Fase 3: Limpieza
Eliminar todas las construcciones safeT huérfanas.

## Orden de ejecución
Fase 1 → QA → Fase 2 → QA → Fase 3 → validate → commit único
