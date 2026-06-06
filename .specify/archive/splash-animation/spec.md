# Spec — Splash animation (ESTADO FINAL)

## Implementación aprobada
Progressive enhancement: GSAP si carga desde CDN, splash estático si no.

## Secuencia (Browser/Mac Safari donde GSAP disponible)
1. Barras letterbox (JS-creadas) cubren top/bot con scaleY:1
2. tl.to(bars, scaleY:0) — letterbox se abre
3. tl.from(chars, opacity:0, y:8, stagger) — spell-out letra por letra
4. tl.from(action, opacity:0, y:14) — selector sube
5. tl.from(tagline, opacity:0) — tagline aparece

## Comportamiento por entorno
- Chrome desktop: animación completa ✅
- Safari Mac: animación completa ✅  
- iOS Safari / PWA: splash estático sin animación (GSAP no carga desde CDN) ✅
- Sin GSAP: cero efectos secundarios — wordmark y layout intactos ✅

## Garantías de fallback
- typeof gsap === 'undefined' → return inmediato, nada tocado
- catch block: elimina barras del DOM, clearProps en elementos
- Wordmark nunca tiene opacity:0 por defecto

## SW / Caché
- BUILD_VERSION en index.html actualizado por bump-version.js en cada deploy
- SW_UPDATED handler: recarga si splash visible (primera apertura post-update)
- HTML siempre desde red (cache: no-store en SW)
