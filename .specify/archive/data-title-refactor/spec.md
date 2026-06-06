# Spec — Refactor: data-title + event delegation

## Problema
22 construcciones de `safeT` con 3 estrategias de encoding incompatibles
(&#39;, \', &quot;) generan bugs silenciosos en títulos con apostrophes.
17 títulos afectados en producción. Cualquier festival futuro con títulos
con caracteres especiales hereda el bug.

## Causa raíz
Pasar strings como argumentos en atributos HTML `onclick` requiere
escapar los caracteres especiales. No existe un encoding único correcto
para todos los contextos (HTML attr + JS string). El problema es estructural.

## Solución
**Eliminar el paso de strings via onclick.**
Usar `data-title` attribute + event delegation.

### Patrón actual (problemático)
```html
<div onclick="openPelSheet('Hell&#39;s Kitchen')">
```

### Patrón nuevo (correcto)
```html
<div class="js-open-pel" data-title="Hell's Kitchen">
```
```js
// Un único listener delegado en el contenedor
document.addEventListener('click', e => {
  const card = e.target.closest('.js-open-pel');
  if (card) openPelSheet(card.dataset.title);
});
```

## Alcance
- Funciones primarias a migrar: openPelSheet(), openRatingSheet(),
  togglePriority(), togglePelPrio(), toggleWatched()
- Funciones secundarias (confirmReplace, toggleFilmAlternatives, etc.):
  auditar caso por caso — pueden necesitar múltiples data-* attrs
- El decode en openPelSheet (c22a7fb) se mantiene como safety net

## Criterios de aceptación
- [ ] Cero construcciones de safeT en el código
- [ ] Todos los títulos con apostrophes abren sheet correctamente
- [ ] Sin regresiones en ninguna tab
- [ ] validate.py 10/10
- [ ] QA en browser con títulos: Hell's Kitchen, Mare's Nest, That's the Weight...

## Riesgos
- Alto volumen de cambios en templates — requiere QA exhaustivo
- Event delegation debe coexistir con stopPropagation() existente
- data-title debe preservarse en re-renders (innerHTML replacement)
