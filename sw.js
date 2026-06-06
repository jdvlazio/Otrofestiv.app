// Otrofestiv — Service Worker v15
// Estrategia: HTML siempre desde red. Assets en caché.
// v14: hadController guard en cliente (fix first-install double-reload)
//      version.json con android/ios independientes para staged rollout
// v15: navigate de clientes en CADA activación, no solo first-install.
//      controllerchange en iOS WKWebView es flaky — este reload es la
//      garantía de que HTML cacheado se descarta inmediatamente al deploy.

const CACHE_NAME = 'otrofestiv-v202606061233';
const BUILD = '202606061233';

const STATIC_ASSETS = [
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/i18n/es.json',
  '/i18n/en.json',
];

self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(keys.map(key => caches.delete(key)))
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

  // HTML → siempre desde red, sin caché
  if (request.destination === 'document') {
    event.respondWith(
      fetch(new Request(request, { cache: 'no-store' }))
        .catch(() => caches.match(request)
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
      fetch(new Request(request, { cache: 'no-store' }))
        .then(res => {
          if (res.ok) { const clone = res.clone(); caches.open(CACHE_NAME).then(c => c.put(request, clone)); }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // i18n JSONs → cache-first (cambian solo en deploy, SW se actualiza)
  if (url.pathname.startsWith('/i18n/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        const networkFetch = fetch(request).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(request, clone));
          }
          return res;
        });
        return cached || networkFetch;
      })
    );
    return;
  }

  // JSONs de festivales → siempre desde red (datos pueden cambiar)
  if (url.pathname.startsWith('/festivals/')) {
    event.respondWith(
      fetch(new Request(request, { cache: 'no-store' }))
        .catch(() => caches.match(request))
    );
    return;
  }

  // Assets estáticos → caché primero
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request))
  );
});
