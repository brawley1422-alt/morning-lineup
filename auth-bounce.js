// Fast synchronous auth bounce — if no ml-auth token, send guests to /home/.
// Loaded as an external script in <head> so it runs before body parse.
// External (not inline) so strict CSP script-src 'self' can stay.
try {
  var raw = localStorage.getItem("ml-auth");
  if (!raw) {
    window.location.replace("home/");
  } else {
    var parsed = JSON.parse(raw);
    var expiresAt = (parsed && parsed.expires_at) || 0;
    if (!parsed || !parsed.access_token || expiresAt * 1000 < Date.now()) {
      window.location.replace("home/");
    }
  }
} catch (e) {
  window.location.replace("home/");
}
