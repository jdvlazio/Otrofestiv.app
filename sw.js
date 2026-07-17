// Otrofestiv — Service Worker v16
// Estrategia: HTML siempre desde red. Assets en caché.
// v14: hadController guard en cliente (fix first-install double-reload)
//      version.json con android/ios independientes para staged rollout
// v15: navigate de clientes en CADA activación, no solo first-install.
//      controllerchange en iOS WKWebView es flaky — este reload es la
//      garantía de que HTML cacheado se descarta inmediatamente al deploy.
// v16: DEPLOY-SAFE — se cachea el último index.html bueno; si la red falla durante
//      el reload forzado por deploy, se sirve ese HTML en vez de OFFLINE_HTML (una
//      sesión viva ya no se destruye por un deploy con señal mala). Audit P3 #10.

const CACHE_NAME = 'otrofestiv-v202607171545';
const BUILD = '202607171545';
// Caché PERSISTENTE de assets inmutables (pósters, iconos, fonts): NO se borra
// en activate. Durante un festival deployamos a diario; sin esto, cada deploy
// obligaba a re-descargar ~8MB de pósters ya vistos (señal rural en sede).
const ASSETS_CACHE = 'otrofestiv-assets-v1';

const STATIC_ASSETS = [
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      // Se borran los cachés versionados; ASSETS_CACHE (inmutables) sobrevive deploys.
      return Promise.all(keys.filter(key => key !== ASSETS_CACHE).map(key => caches.delete(key)))
        .then(() => caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS)))
        .then(() => self.clients.claim())
        .then(() => self.clients.matchAll({type:'window'}).then(clients => {
          // Reload de TODOS los clientes en cada activación — invalida HTML
          // cacheado por el browser/WKWebView. Antes solo en first-install,
          // pero controllerchange en iOS WebView es flaky. Este navigate es
          // la garantía dura de que el HTML viejo se reemplaza inmediatamente.
          clients.forEach(client => client.navigate(client.url));
        }));
    })
  );
});

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Otrofestiv — Sin conexión</title>
<style>body{margin:0;background:#0A0A0A;color:#F0EDE8;font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px;box-sizing:border-box}h1{color:#D4900A;font-size:20px;margin-bottom:12px}p{color:#888;font-size:14px;line-height:1.6;max-width:280px}button{margin-top:24px;padding:12px 24px;background:#D4900A;color:#000;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}</style>
</head><body><div><h1>Sin conexión</h1><p>Necesitas conexión la primera vez.</p><button onclick="location.reload()">Reintentar</button></div></body></html>`;

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;

  // HTML → siempre desde red. no-cache (no no-store): revalida con ETag contra
  // el servidor — 304 de ~cientos de bytes cuando no cambió, cuerpo completo
  // cuando sí. Misma garantía de frescura por deploy, ~97% menos datos por apertura.
  // DEPLOY-SAFE: se cachea el último HTML bueno. El activate fuerza navigate(reload)
  // de todos los clientes en CADA deploy; si la red falla EN ESE instante (señal
  // rural en sede, deploys diarios en septiembre), sin caché el reload mataba una
  // sesión que funcionaba → OFFLINE_HTML. Ahora sirve el último index.html cacheado
  // y la sesión sobrevive. El caché es del build actual (CACHE_NAME se purga en
  // activate y se re-puebla al primer fetch ok), así que nunca sirve HTML stale.
  if (request.destination === 'document') {
    event.respondWith(
      fetch(new Request(request, { cache: 'no-cache' }))
        .then(res => {
          if (res.ok) { const clone = res.clone(); caches.open(CACHE_NAME).then(c => c.put(request, clone)); }
          return res;
        })
        .catch(() => caches.match(request, { ignoreSearch: true })
          .then(c => c || caches.match('/', { ignoreSearch: true }))
          .then(c => c || new Response(OFFLINE_HTML, {headers:{'Content-Type':'text/html;charset=utf-8'}}))
        )
    );
    return;
  }

  // Módulos de la app (/src/) → network-first como el HTML (p8 Step 0,
  // D-INFRA-1=B). El código vive en src/main.js + futuros src/*.js; deben
  // propagar en cada deploy igual que el HTML (no quedarse cacheados stale).
  // Fallback a caché para offline.
  if (url.pathname.startsWith('/src/')) {
    event.respondWith(
      fetch(new Request(request, { cache: 'no-cache' }))
        .then(res => {
          if (res.ok) { const clone = res.clone(); caches.open(CACHE_NAME).then(c => c.put(request, clone)); }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // JSONs de festivales → network-first CON fallback a último-bueno en caché.
  // El fetch no-store preserva frescura (datos pueden cambiar); el caché solo
  // entra si la red falla. Resiliencia para quien vuelve: si el edge del CDN
  // se cuelga, sirve la última copia buena en vez de quedar con films=0 (grid
  // vacío). Solo se cachean respuestas ok — un cuerpo colgado nunca completa el
  // put, así que no envenena el caché.
  if (url.pathname.startsWith('/festivals/')) {
    event.respondWith(
      fetch(new Request(request, { cache: 'no-cache' }))
        .then(res => {
          if (res.ok) { const clone = res.clone(); caches.open(CACHE_NAME).then(c => c.put(request, clone)); }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Assets estáticos (pósters, iconos, fonts — inmutables) → caché primero,
  // guardados en ASSETS_CACHE que sobrevive deploys (ver arriba).
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(res => {
      if (res.ok && (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/fonts/'))) {
        const clone = res.clone();
        caches.open(ASSETS_CACHE).then(c => c.put(request, clone));
      }
      return res;
    }))
  );
});
