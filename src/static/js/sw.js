const CACHE_NAME = 'biosecure-pwa-v1';

// App Shell assets to pre-cache
const PRECACHE_ASSETS = [
  '/',
  '/offline',
  '/manifest.json',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/js/offline-detector.js',
  '/static/js/guided-camera.js',
  '/static/js/id-scanner.js',
  '/static/js/pwa.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/favicon-32x32.png',
  '/static/icons/favicon-16x16.png'
];

// Install Event: Pre-cache App Shell
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing Service Worker v1...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[Service Worker] Pre-caching App Shell assets');
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn('[Service Worker] Pre-cache partial failure (non-critical):', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Clean up old caches & take immediate control
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating Service Worker v1...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Smart caching strategy
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Ignore non-GET requests (e.g. POST photo uploads or attendance submissions)
  if (request.method !== 'GET') {
    return;
  }

  // Handle HTML Page Navigation Requests (Network First, Fallback to Cache / Offline Page)
  if (request.mode === 'navigate' || (request.headers.get('accept') && request.headers.get('accept').includes('text/html'))) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Clone and update cache with fresh copy
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          return response;
        })
        .catch(async () => {
          console.log('[Service Worker] Network failed for navigation; checking cache for:', url.pathname);
          const cachedResponse = await caches.match(request);
          if (cachedResponse) {
            return cachedResponse;
          }
          // If requested page isn't in cache, show offline fallback page
          const offlinePage = await caches.match('/offline');
          if (offlinePage) {
            return offlinePage;
          }
          return new Response(
            '<html><body><h1>Offline</h1><p>BioSecure AI is offline and the requested page is not cached.</p></body></html>',
            { headers: { 'Content-Type': 'text/html' } }
          );
        })
    );
    return;
  }

  // Handle Static Assets (CSS, JS, Images, Fonts, Icons, CDNs) — Stale-While-Revalidate
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('tailwindcss.com') ||
    url.hostname.includes('unpkg.com') ||
    url.hostname.includes('googleapis.com') ||
    url.hostname.includes('gstatic.com')
  ) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              const responseClone = networkResponse.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
            }
            return networkResponse;
          })
          .catch(() => cachedResponse);

        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // Default Network-First for other GET requests
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

// Message listener for skipWaiting trigger
self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});
