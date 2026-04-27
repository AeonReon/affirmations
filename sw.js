// Minimal service worker — just satisfies Chrome's WebAPK install criteria
// so the home-screen icon installs as a real app, not a "shortcut" with a
// browser-link arrow badge. No caching — main HTML keeps its no-store
// headers and the existing cache-busting flow stays intact.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
