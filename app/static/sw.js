/* МИФУД Service Worker — минимальный кэш для offline-фоллбэка статики.
   Стратегии:
   - precache: критичная статика при install
   - fetch: network-first для HTML, cache-first для статики
   - SSE и POST/PUT/DELETE — всегда из сети, без кэша
*/

const CACHE = 'mifud-v3';
const PRECACHE = [
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/img/logo.png',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/manifest.json',
  '/static/offline.html',
  '/static/vendor/bootstrap.min.css',
  '/static/vendor/bootstrap.bundle.min.js',
  '/static/vendor/htmx.min.js',
  '/static/vendor/htmx-sse.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Только GET кэшируем
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // SSE — никогда не кэшируем (long-lived stream)
  if (url.pathname.startsWith('/sse/')) return;

  // Статика — cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match('/static/img/logo.png')))
    );
    return;
  }

  // HTML и остальное — network-first, кэш как fallback, offline.html — финальный fallback
  event.respondWith(
    fetch(req).then((res) => {
      if (res.ok && res.headers.get('content-type')?.includes('text/html')) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
      }
      return res;
    }).catch(() =>
      caches.match(req).then((hit) => hit || caches.match('/static/offline.html'))
    )
  );
});
