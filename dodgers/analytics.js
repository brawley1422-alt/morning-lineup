(function () {
  "use strict";

  // Morning Lineup in-house analytics. Fires one pageview event on load and
  // exposes window.mlTrack(eventType, extra) for custom events (share clicks,
  // install accepts, signup submits). Writes straight to the existing Supabase
  // project's `events` table via the anon key — no third-party tracker, no
  // cookies, no external dependencies.
  //
  // Security: anon key + RLS. The events table allows inserts from anyone
  // and no reads from anyone — data is only visible in the Supabase dashboard
  // with the service role. See docs/supabase/events.sql for the schema.
  //
  // Graceful degrade: if the network fails, the user is on an ad-blocker, or
  // the fetch is interrupted by navigation, nothing breaks and no error shows.

  var SUPABASE_URL = "https://xicuxuvuyalpngbhhkpl.supabase.co";
  var SUPABASE_ANON_KEY = "sb_publishable_n0rJdo0RsjVUla839uR1nQ_0-t2lzFh";
  var ENDPOINT = SUPABASE_URL + "/rest/v1/events";

  // Anonymous ID persists across visits on the same browser so we can group
  // pageviews by person for anon users. Random, short, no PII. Migrates any
  // existing per-tab sessionStorage value so in-flight sessions don't reset.
  var sid;
  try {
    sid = localStorage.getItem("ml_aid");
    if (!sid) {
      try { sid = sessionStorage.getItem("ml_sid"); } catch (e) { /* ignore */ }
      if (!sid) {
        sid = Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
      }
      localStorage.setItem("ml_aid", sid);
    }
  } catch (e) {
    sid = null;
  }

  // Read the current Supabase user id, if any, straight out of the shared
  // auth storage (see auth/session.js — storageKey: "ml-auth"). This avoids
  // having to import session.js (which would require making this a module)
  // and there's no race: analytics.js and session.js read from the same key.
  function currentUserId() {
    try {
      var raw = localStorage.getItem("ml-auth");
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      return (parsed && parsed.user && parsed.user.id) || null;
    } catch (e) {
      return null;
    }
  }

  // Derive the team slug from the URL path. Non-team paths (home/, auth/,
  // settings/, landing) return null so we don't mis-attribute.
  var NON_TEAM = {
    home: 1, auth: 1, settings: 1, data: 1, archive: 1, icons: 1,
    scorecard: 1, tests: 1, docs: 1, scripts: 1, config: 1, teams: 1,
    press: 1, admin: 1,
  };
  function currentTeamSlug() {
    var m = (location.pathname || "").match(/\/([a-z0-9-]+)\/?/);
    if (!m) return null;
    var slug = m[1];
    return NON_TEAM[slug] ? null : slug;
  }

  function send(eventType, extra) {
    if (!eventType) return;
    var body = {
      event_type: String(eventType).slice(0, 64),
      team_slug: currentTeamSlug(),
      path: (location.pathname || "") + (location.search || ""),
      referrer: document.referrer || null,
      session_id: sid,
      user_id: currentUserId(),
      ua: (navigator.userAgent || "").slice(0, 256),
    };
    if (extra && typeof extra === "object") {
      // Allow callers to pass a small extra object that gets merged in.
      // We only whitelist a couple of fields to keep the row shape stable.
      if (typeof extra.team_slug === "string") body.team_slug = extra.team_slug;
      if (typeof extra.path === "string") body.path = extra.path;
    }
    try {
      fetch(ENDPOINT, {
        method: "POST",
        headers: {
          "apikey": SUPABASE_ANON_KEY,
          "Authorization": "Bearer " + SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
          "Prefer": "return=minimal",
        },
        body: JSON.stringify(body),
        keepalive: true,
      }).catch(function () { /* swallow */ });
    } catch (e) { /* swallow */ }
  }

  // Public API for future custom events.
  window.mlTrack = send;

  function firePageview() {
    send("pageview");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", firePageview);
  } else {
    firePageview();
  }
})();
