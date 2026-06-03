# Hallazgo — reload en la primera apertura (Service Worker `client.navigate`)

> **Diagnóstico, NO implementación.** No tocar el SW durante Tribeca (cache-busting delicado).
> Agendado post-festival, junto al resto del trabajo de SW (y el pin).
> Causa raíz compartida con el falso rojo del synthetic monitor (ver `fix/monitoring-tolerate-sw-reload`).

## Pregunta original
¿El guard `_hadController` (main.js:1692) pierde la carrera en la primerísima carga de un visitante nuevo (sin SW previo) → ve un `reload()` extra al abrir por primera vez?

## Respuesta: SÍ hay reload en first-open — pero el guard NO "pierde una carrera": está **bypasseado**

El reload de first-open **no** viene del handler del cliente (que el guard sí cubre), sino del **propio Service Worker**, que el guard no puede tocar.

### Mecanismo exacto
`sw.js:24-39` — handler `activate` (introducido en **v15**):
```js
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(k => caches.delete(k)))
        .then(() => caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)))
        .then(() => self.clients.claim())
        .then(() => self.clients.matchAll({type:'window'}).then(clients => {
          clients.forEach(client => client.navigate(client.url));   // ← LÍNEA 35: reload de TODOS los clientes
        }))
    )
  );
});
```
- En una **primera carga fresca**: HTML carga → SW instala (`skipWaiting`, sw.js:21) → `activate` → `clients.claim()` → **`client.navigate(client.url)` recarga la página** (línea 35).
- El guard `_hadController` (main.js:1691-1700) gobierna **solo** el reload del *cliente* (`controllerchange → location.reload()`), y además ese path es `!_isIOS`. La `client.navigate()` del SW es **independiente del cliente y de la plataforma** → se ejecuta igual, en la primera activación, en todos los clientes. El guard queda **inerte para este reload**.
- v15 lo agregó a propósito: "navigate de clientes en CADA activación… controllerchange en iOS WKWebView es flaky — este reload es la garantía dura de que el HTML viejo se reemplaza al deploy" (sw.js:5-7). El efecto colateral es que también recarga en la **primera** activación (cuando no hay HTML viejo que reemplazar) — reintroduciendo el double-reload que el guard v14 buscaba evitar.

### Evidencia (probes contra producción, contextos frescos)
- Chromium fresco (no-iOS): `navCount=2` (un reload), URL queda `/` **sin `?v=`** → reload pelado = `client.navigate`, no el poll de version.json (que usa `?v=`).
- **UA iPhone 14 fresco** (app marca `_isIOS=true`, reload del cliente SKIPPED): **`navCount=2` igual** (3/3 probes) → prueba que el reload es del SW, no del handler del cliente. **El hiccup afecta iOS también.**

## ¿En qué condiciones ocurre el hiccup?
| Escenario | ¿Reload? | Nota |
|---|---|---|
| **Primer-open de visitante nuevo** (sin SW previo) | **SÍ, 1 reload** | El hiccup. Un parpadeo/re-bootstrap al abrir por primera vez. |
| Open normal repetido (SW ya activo, sin deploy) | No | `activate` no re-dispara. |
| Open justo después de un deploy (nuevo sw.js) | Sí, 1 reload | **Intencional** — toma la versión nueva. |

**Alcance de plataforma:**
- Browser desktop/Android, **mobile Safari y PWA** (donde el SW corre): afectados → el visitante nuevo ve **un reload** en el primer open.
- **App nativa iOS (SwiftUI WKWebView):** el soporte de SW en WKWebView es limitado y la app ya carga con `reloadIgnoringLocalAndRemoteCacheData` en cada cold-launch (ver `ContentView.swift`). Si el WKWebView no corre el SW, este reload **no aplica** ahí. **Requiere confirmación en dispositivo** — no asumido.

**Severidad:** baja. Un reload en el primerísimo open; la app funciona post-reload. Pero es la primera impresión para un tester nuevo que entre por Safari/PWA durante Tribeca.

## Arreglo de raíz propuesto (post-festival — NO implementar ahora)
En `sw.js` `activate`, ejecutar `client.navigate()` **solo cuando es una actualización** (había caché vieja antes de borrar), no en la primera instalación:
```js
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const isUpdate = keys.length > 0;            // había un SW/caché previo → es deploy, no first-install
    await Promise.all(keys.map(k => caches.delete(k)));
    const c = await caches.open(CACHE_NAME); await c.addAll(STATIC_ASSETS);
    await self.clients.claim();
    if (isUpdate) {                               // ← solo recargar en updates, no en first-install
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach(client => client.navigate(client.url));
    }
  })());
});
```
- Restaura la intención de v14 ("sin reload en first-install") **conservando** la garantía de v15 ("refresh duro en cada deploy").
- Es SW-side → no depende de `controllerchange` (que es flaky en iOS WKWebView) → mantiene la cobertura iOS que v15 buscaba.
- **Caveat:** el cache-busting de HTML en WKWebView fue históricamente delicado (motivo de v15). Cualquier cambio al SW debe probarse en el iPhone real (app SwiftUI) antes de mergear. Por eso: **post-festival, con piso firme.**

## Relación con el monitor
Misma raíz. El fix del monitor (`fix/monitoring-tolerate-sw-reload`, Tarea 1) **tolera** este reload (no lo elimina) → devuelve el monitor a verde sin tocar producción. El arreglo de raíz de aquí elimina el reload de first-install. Son complementarios: el del monitor es ahora; éste es post-festival.
