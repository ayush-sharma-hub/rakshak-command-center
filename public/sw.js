// Project Rakshak — Progressive Web App Service Worker
const CACHE_NAME = 'rakshak-v3.1';
const OFFLINE_URLS = [
  '/citizen.html',
  '/map.html',
  '/app.js',
  '/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(OFFLINE_URLS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request).then((res) => {
        if (res) return res;
        if (event.request.headers.get('accept').includes('text/html')) {
          return caches.match('/citizen.html');
        }
      });
    })
  );
});

// Real-time Push Notification handler for mobile background wake-up
self.addEventListener('push', (event) => {
  let data = {
    title: '⚠️ SEOC UTTARAKHAND FLOOD WARNING',
    body: 'Urgent Evacuation Alert: High runoff velocity detected. Move to higher ground immediately.',
    url: '/map.html'
  };
  if (event.data) {
    try {
      data = Object.assign(data, event.data.json());
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: 'https://cdn-icons-png.flaticon.com/512/9440/9440539.png',
    badge: 'https://cdn-icons-png.flaticon.com/512/9440/9440539.png',
    vibrate: [500, 150, 500, 150, 800],
    data: { url: data.url || '/map.html' },
    requireInteraction: true
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Handle incoming notification click on mobile phone
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || '/map.html';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});


