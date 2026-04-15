<<<<<<< Updated upstream
const CACHE = "lineup-202604150835";
=======
const CACHE = "lineup-202604141403";
>>>>>>> Stashed changes
const SHELL = ["/morning-lineup/", "/morning-lineup/index.html", "/morning-lineup/live.js"];

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names
          .filter(function (n) { return n !== CACHE; })
          .map(function (n) { return caches.delete(n); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (e) {
  var url = new URL(e.request.url);

  // Network-first for live API calls — must always be fresh.
  if (url.hostname === "statsapi.mlb.com" || url.hostname === "api.open-meteo.com") {
    e.respondWith(
      fetch(e.request).catch(function () {
        return caches.match(e.request);
      })
    );
    return;
  }

  // Network-first for everything else (HTML, JS, CSS). Falls back to cache
  // only when offline. Updated files always land on refresh — no hard-refresh
  // required. Cache exists purely as an offline safety net.
  e.respondWith(
    fetch(e.request)
      .then(function (response) {
        if (response && response.status === 200 && response.type === "basic") {
          var clone = response.clone();
          caches.open(CACHE).then(function (cache) {
            cache.put(e.request, clone);
          });
        }
        return response;
      })
      .catch(function () {
        return caches.match(e.request);
      })
  );
});
