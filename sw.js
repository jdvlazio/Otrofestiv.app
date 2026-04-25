// Otrofestiv — Service Worker v11
// Estrategia: HTML siempre desde red. Assets en caché.

const CACHE_NAME = 'otrofestiv-v202604250402';
const BUILD = '202604251902';

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
    caches.keys().then(keys =>
      Promise.all(keys.map(key => caches.delete(key)))
    ).then(() => {
      return caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS));
    }).then(() => self.clients.claim())
    .then(() => {
      return self.clients.matchAll({type:'window',includeUncontrolled:true})
        .then(clients => clients.forEach(c => c.postMessage({type:'SW_UPDATED',build:BUILD})));
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

  // Assets → caché primero
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request))
  );
});
