const CACHE = "lineup-202604280410";
const SHELL = ["/morning-lineup/", "/morning-lineup/index.html"];

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
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.origin !== location.origin) return;

  var isHTML = e.request.mode === "navigate"
    || (url.pathname.endsWith("/") || url.pathname.endsWith(".html"));

  if (isHTML) {
    // Network-first: always fetch fresh HTML, cache fallback for offline
    e.respondWith(
      fetch(e.request).then(function (resp) {
        if (resp && resp.status === 200) {
          var copy = resp.clone();
          caches.open(CACHE).then(function (cache) { cache.put(e.request, copy); });
        }
        return resp;
      }).catch(function () {
        return caches.match(e.request);
      })
    );
  } else {
    // Stale-while-revalidate: serve cached asset instantly, refresh in background
    e.respondWith(
      caches.open(CACHE).then(function (cache) {
        return cache.match(e.request).then(function (hit) {
          var fetchPromise = fetch(e.request).then(function (resp) {
            if (resp && resp.status === 200 && resp.type === "basic") {
              cache.put(e.request, resp.clone());
            }
            return resp;
          }).catch(function () { return hit; });
          return hit || fetchPromise;
        });
      })
    );
  }
});

self.addEventListener("push", function (e) {
  var payload = {};
  try { payload = e.data ? e.data.json() : {}; } catch (err) { payload = {}; }

  var title = payload.title || "Morning Lineup";
  var body = payload.body || "";
  var url = payload.url || "/morning-lineup/";
  var tag = payload.tag || undefined;
  var icon = payload.icon || "/morning-lineup/icons/icon-192.png";

  var options = {
    body: body,
    tag: tag,
    icon: icon,
    badge: "/morning-lineup/icons/icon-192.png",
    data: { url: url }
  };

  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  var target = (e.notification.data && e.notification.data.url) || "/morning-lineup/";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clients) {
      for (var i = 0; i < clients.length; i++) {
        var c = clients[i];
        if (c.url.indexOf(target) !== -1 && "focus" in c) return c.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })
  );
});
