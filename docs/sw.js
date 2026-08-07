/* Offline cache so the trainer works poolside with no signal. */
var CACHE = "salidas-v3";   // bump = evict the old synthesised audio
var ASSETS = [
  "./",
  "index.html",
  "styles.css",
  "app.js",
  "manifest.webmanifest",
  "audio/v_arbitro.ogg",
  "audio/v_arbitro.m4a",
  "audio/v_marcas.ogg",
  "audio/v_marcas.m4a",
  "audio/referee_beeps.ogg",
  "audio/referee_beeps.m4a",
  "audio/start_beep.ogg",
  "audio/start_beep.m4a",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      // don't let one missing file abort the whole install
      return Promise.all(ASSETS.map(function (u) {
        return c.add(u).catch(function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        return k === CACHE ? null : caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = new URL(e.request.url);
  if (url.origin !== location.origin) return;   // let fonts hit the network

  e.respondWith(
    caches.match(e.request).then(function (hit) {
      if (hit) return hit;
      return fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () {
        return caches.match("index.html");
      });
    })
  );
});
