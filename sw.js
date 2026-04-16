// Otrofestiv — Service Worker
// Cache strategy: Network First para HTML, Cache First para assets

const CACHE_NAME = 'otrofestiv-v8';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

// Página offline de fallback — se muestra cuando no hay caché ni red
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Otrofestiv — Sin conexión</title>
<style>
  body{margin:0;background:#0A0A0A;color:#F0EDE8;font-family:system-ui,sans-serif;
       display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px;box-sizing:border-box}
  h1{color:#D4900A;font-size:20px;margin-bottom:12px}
  p{color:#888;font-size:14px;line-height:1.6;max-width:280px}
  button{margin-top:24px;padding:12px 24px;background:#D4900A;color:#000;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}
</style>
</head>
<body>
  <div>
    <h1>Sin conexión</h1>
    <p>Otrofestiv necesita conexión la primera vez. Vuelve a intentarlo cuando tengas internet.</p>
    <button onclick="location.reload()">Reintentar</button>
  </div>
</body>
</html>`;

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== location.origin) return;

  // HTML → Network First, fallback a caché, fallback a offline page
  if (request.destination === 'document') {
    // cache: 'no-store' bypasses HTTP cache headers from GitHub Pages
    // ensuring we always get the latest HTML without needing a SW bump
    const freshRequest = new Request(request, { cache: 'no-store' });
    event.respondWith(
      fetch(freshRequest)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          return response;
        })
        .catch(() =>
          caches.match(request).then(cached =>
            cached || new Response(OFFLINE_HTML, {
              headers: { 'Content-Type': 'text/html; charset=utf-8' }
            })
          )
        )
    );
    return;
  }

  // Assets → Cache First, fallback a red
  event.respondWith(
    caches.match(request)
      .then(cached => cached || fetch(request))
  );
});
