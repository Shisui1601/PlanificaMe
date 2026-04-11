/**
 * sw.js — Service Worker de PlanificaMe
 * ───────────────────────────────────────
 * Estrategias:
 *   • Shell estático (HTML principal)   → Cache-first
 *   • API /api/*                        → Network-first (cache fallback 30s)
 *   • Fuentes / CDN externo             → Stale-while-revalidate
 *   • Push notifications                → Muestra notificación del SO
 */

const VERSION    = 'v1.0.0';
const CACHE_APP  = `planificame-app-${VERSION}`;
const CACHE_API  = `planificame-api-${VERSION}`;
const CACHE_CDN  = `planificame-cdn-${VERSION}`;

// Recursos a pre-cachear al instalar
const PRECACHE = [
  '/',
  '/index.html',
  '/manifest.json',
];

// ───────────────────────────────────────
// INSTALL — pre-cacheo del shell
// ───────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_APP)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

// ───────────────────────────────────────
// ACTIVATE — limpiar cachés viejos
// ───────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith('planificame-') && ![CACHE_APP, CACHE_API, CACHE_CDN].includes(k))
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ───────────────────────────────────────
// FETCH — estrategias por tipo de recurso
// ───────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Solo manejar GET
  if (request.method !== 'GET') return;

  // API → Network-first con timeout de 5s, fallback a caché
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstAPI(request));
    return;
  }

  // CDN externo (fonts, lucide) → Stale-while-revalidate
  if (!url.origin.includes(self.location.origin)) {
    event.respondWith(staleWhileRevalidate(request, CACHE_CDN));
    return;
  }

  // App shell → Cache-first, network fallback
  event.respondWith(cacheFirstApp(request));
});

async function networkFirstAPI(request) {
  const cache = await caches.open(CACHE_API);
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const response = await fetch(request, { signal: controller.signal });
    clearTimeout(timeout);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ offline: true, error: 'Sin conexión' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function cacheFirstApp(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_APP);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Offline: devolver index.html para que la SPA maneje la ruta
    const fallback = await caches.match('/index.html');
    return fallback || new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => cached);
  return cached || networkPromise;
}

// ───────────────────────────────────────
// PUSH NOTIFICATIONS
// ───────────────────────────────────────
self.addEventListener('push', event => {
  let data = { title: '📅 PlanificaMe', body: 'Tienes una actividad próxima', tag: 'planificame-reminder' };
  try { data = { ...data, ...event.data.json() }; } catch {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body:    data.body,
      tag:     data.tag || 'planificame',
      icon:    data.icon || '/favicon.svg',
      badge:   data.badge || '/favicon.svg',
      vibrate: [100, 50, 100],
      data:    { url: data.url || '/' },
      actions: data.actions || [
        { action: 'open',    title: '📅 Abrir' },
        { action: 'dismiss', title: 'Descartar' },
      ]
    })
  );
});

// ───────────────────────────────────────
// NOTIFICATION CLICK
// ───────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus();
          client.postMessage({ type: 'NOTIFICATION_CLICK', url });
          return;
        }
      }
      clients.openWindow(url);
    })
  );
});

// ───────────────────────────────────────
// BACKGROUND SYNC (recordatorios offline)
// ───────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-reminders') {
    event.waitUntil(syncReminders());
  }
});

async function syncReminders() {
  try {
    const cache = await caches.open('planificame-pending-reminders');
    const keys  = await cache.keys();
    for (const req of keys) {
      const res = await cache.match(req);
      const data = await res.json().catch(() => null);
      if (!data) continue;
      await self.registration.showNotification(`📅 ${data.title}`, {
        body:    `Recordatorio: ${data.time || ''}`,
        tag:     `reminder-${data.id}`,
        data:    { url: '/' },
        vibrate: [100, 50, 100],
      });
      await cache.delete(req);
    }
  } catch (e) {
    console.warn('[SW] syncReminders error:', e);
  }
}
