// push-ui.js — Web Push client for Morning Lineup.
//
// Public surface:
//   initNotificationsPanel(root)  — mounts the Notifications card in /settings
//   subscribeThisDevice()         — prompts permission + subscribes
//   unsubscribeThisDevice()       — revokes + deletes DB row
//   getSubscriptionStatus()       — { permission, subscribed, supported }
//
// Depends on auth/session.js (same Supabase client) and the schema from
// docs/supabase/push-schema.sql.

import { supabase, getSession } from "./auth/session.js";

// REPLACE after running `npx web-push generate-vapid-keys` — see
// docs/push-notifications/vapid-setup.md step 2.
export const VAPID_PUBLIC_KEY = "REPLACE_ME_VAPID_PUBLIC_KEY";

const NOTIF_TYPES = [
  { key: "morning_lineup", label: "Morning Lineup", hint: "Daily briefing at 6 a.m. CT" },
  { key: "lineup_posted",  label: "Lineup Posted",  hint: "Starting nine announced" },
  { key: "final",          label: "Game Final",     hint: "Final score + scorecard link" },
  { key: "transaction",    label: "Transactions",   hint: "Trades, DFAs, call-ups, options" },
  { key: "injured_list",   label: "Injured List",   hint: "IL placements and activations" },
  { key: "prospect_watch", label: "Prospect Watch", hint: "Notable events from your tracked prospects" },
];

const TV_SYNC_OPTIONS = [
  { v: 0,   label: "Off" },
  { v: 30,  label: "30 s" },
  { v: 60,  label: "1 min" },
  { v: 120, label: "2 min" },
  { v: 300, label: "5 min" },
  { v: 600, label: "10 min" },
];

const TEAM_LABELS = {
  "angels": "Angels", "astros": "Astros", "athletics": "Athletics", "blue-jays": "Blue Jays",
  "braves": "Braves", "brewers": "Brewers", "cardinals": "Cardinals", "cubs": "Cubs",
  "dbacks": "Diamondbacks", "dodgers": "Dodgers", "giants": "Giants", "guardians": "Guardians",
  "mariners": "Mariners", "marlins": "Marlins", "mets": "Mets", "nationals": "Nationals",
  "orioles": "Orioles", "padres": "Padres", "phillies": "Phillies", "pirates": "Pirates",
  "rangers": "Rangers", "rays": "Rays", "reds": "Reds", "red-sox": "Red Sox",
  "rockies": "Rockies", "royals": "Royals", "tigers": "Tigers", "twins": "Twins",
  "white-sox": "White Sox", "yankees": "Yankees",
};

// ---------- browser helpers ----------
export function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

function isStandaloneIOS() {
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const standalone = window.matchMedia?.("(display-mode: standalone)").matches
    || window.navigator.standalone === true;
  return { ios, standalone };
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

async function getRegistration() {
  if (!("serviceWorker" in navigator)) return null;
  return navigator.serviceWorker.ready;
}

export async function getSubscriptionStatus() {
  if (!pushSupported()) return { supported: false, permission: "denied", subscribed: false };
  const reg = await getRegistration();
  const existing = await reg?.pushManager.getSubscription();
  return {
    supported: true,
    permission: Notification.permission,
    subscribed: !!existing,
    endpoint: existing?.endpoint ?? null,
  };
}

export async function subscribeThisDevice() {
  if (!pushSupported()) throw new Error("Push not supported in this browser.");
  if (VAPID_PUBLIC_KEY === "REPLACE_ME_VAPID_PUBLIC_KEY") {
    throw new Error("VAPID key not configured. See docs/push-notifications/vapid-setup.md.");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notifications blocked. Enable in browser settings.");

  const session = await getSession();
  if (!session) throw new Error("Sign in first.");

  const reg = await getRegistration();
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
  });

  const subJson = sub.toJSON();
  const payload = {
    user_id: session.user.id,
    endpoint: subJson.endpoint,
    p256dh: subJson.keys.p256dh,
    auth: subJson.keys.auth,
    user_agent: navigator.userAgent.slice(0, 200),
  };

  const { error } = await supabase
    .from("push_subscriptions")
    .upsert(payload, { onConflict: "endpoint" });
  if (error) throw error;

  return sub;
}

export async function unsubscribeThisDevice() {
  const reg = await getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (sub) {
    await supabase.from("push_subscriptions").delete().eq("endpoint", sub.endpoint);
    await sub.unsubscribe();
  }
}

// ---------- data helpers ----------
async function loadFollowedTeams(userId) {
  const { data, error } = await supabase
    .from("followed_teams")
    .select("team_slug, position")
    .eq("user_id", userId)
    .order("position", { ascending: true });
  if (error) throw error;
  return data ?? [];
}

async function loadTeamPrefs(userId) {
  const { data, error } = await supabase
    .from("team_notif_prefs")
    .select("team_slug, notif_type, enabled")
    .eq("user_id", userId);
  if (error) throw error;
  const map = {};
  for (const row of data ?? []) {
    map[row.team_slug] = map[row.team_slug] || {};
    map[row.team_slug][row.notif_type] = row.enabled;
  }
  return map;
}

async function setTeamPref(userId, team_slug, notif_type, enabled) {
  const { error } = await supabase
    .from("team_notif_prefs")
    .upsert({ user_id: userId, team_slug, notif_type, enabled }, { onConflict: "user_id,team_slug,notif_type" });
  if (error) throw error;
}

async function loadTvSync(userId) {
  const { data, error } = await supabase
    .from("user_push_prefs")
    .select("tv_sync_seconds")
    .eq("user_id", userId)
    .maybeSingle();
  if (error) throw error;
  return data?.tv_sync_seconds ?? 120;
}

async function setTvSync(userId, seconds) {
  const { error } = await supabase
    .from("user_push_prefs")
    .upsert({ user_id: userId, tv_sync_seconds: seconds }, { onConflict: "user_id" });
  if (error) throw error;
}

// ---------- panel ----------
export async function initNotificationsPanel(root) {
  if (!root) return;

  root.innerHTML = `
    <div class="notif-support-gate" hidden></div>
    <div class="notif-ios-hint" hidden>
      <strong>On iPhone:</strong> tap <em>Share → Add to Home Screen</em>, then open the site from the home-screen icon to enable notifications.
    </div>
    <div class="notif-device">
      <div class="notif-device-row">
        <div>
          <div class="notif-device-title">This device</div>
          <div class="notif-device-status" id="notif-device-status">—</div>
        </div>
        <button type="button" class="auth-submit notif-device-btn" id="notif-device-btn">Enable</button>
      </div>
    </div>

    <div class="notif-tvsync">
      <div class="notif-tvsync-label">TV sync delay</div>
      <div class="notif-tvsync-hint">Delays every notification so your phone doesn't spoil the broadcast.</div>
      <div class="radio-row notif-tvsync-row" id="notif-tvsync-row">
        ${TV_SYNC_OPTIONS.map(o => `
          <label><input type="radio" name="tvsync" value="${o.v}"><span>${o.label}</span></label>
        `).join("")}
      </div>
    </div>

    <div class="notif-teams">
      <div class="notif-teams-label">Your teams</div>
      <div class="notif-teams-hint">Toggle notification types per team. New follows default to Morning Lineup + Final on.</div>
      <div class="notif-teams-list" id="notif-teams-list"></div>
      <p class="settings-hint" id="notif-teams-empty" hidden>Follow a team above to configure notifications.</p>
    </div>

    <div class="auth-error notif-error" id="notif-error" hidden></div>
  `;

  const errBox = root.querySelector("#notif-error");
  const supportGate = root.querySelector(".notif-support-gate");
  const iosHint = root.querySelector(".notif-ios-hint");
  const deviceStatus = root.querySelector("#notif-device-status");
  const deviceBtn = root.querySelector("#notif-device-btn");
  const tvsyncRow = root.querySelector("#notif-tvsync-row");
  const teamsListEl = root.querySelector("#notif-teams-list");
  const teamsEmpty = root.querySelector("#notif-teams-empty");

  function showErr(msg) {
    errBox.hidden = false;
    errBox.textContent = msg;
  }
  function clearErr() {
    errBox.hidden = true;
    errBox.textContent = "";
  }

  if (!pushSupported()) {
    supportGate.hidden = false;
    supportGate.textContent = "Push notifications aren't supported in this browser. Try Chrome, Firefox, Edge, or Safari on iOS 16.4+ (installed to home screen).";
    deviceBtn.disabled = true;
    return;
  }

  const { ios, standalone } = isStandaloneIOS();
  if (ios && !standalone) {
    iosHint.hidden = false;
    deviceBtn.disabled = true;
  }

  const session = await getSession();
  if (!session) {
    supportGate.hidden = false;
    supportGate.textContent = "Sign in to manage notifications.";
    deviceBtn.disabled = true;
    return;
  }
  const userId = session.user.id;

  async function refreshDeviceRow() {
    const st = await getSubscriptionStatus();
    if (st.permission === "denied") {
      deviceStatus.textContent = "Blocked in browser settings";
      deviceBtn.textContent = "Enable";
      deviceBtn.disabled = true;
      return;
    }
    if (st.subscribed) {
      deviceStatus.textContent = "Notifications on for this device";
      deviceBtn.textContent = "Turn off";
      deviceBtn.disabled = false;
    } else {
      deviceStatus.textContent = "Not enabled on this device";
      deviceBtn.textContent = "Enable";
      deviceBtn.disabled = (ios && !standalone);
    }
  }

  deviceBtn.addEventListener("click", async () => {
    clearErr();
    deviceBtn.disabled = true;
    try {
      const st = await getSubscriptionStatus();
      if (st.subscribed) {
        await unsubscribeThisDevice();
      } else {
        await subscribeThisDevice();
      }
    } catch (e) {
      showErr(e.message || String(e));
    } finally {
      await refreshDeviceRow();
    }
  });

  // TV sync radio
  const currentTvSync = await loadTvSync(userId);
  tvsyncRow.querySelectorAll('input[name="tvsync"]').forEach((r) => {
    if (Number(r.value) === currentTvSync) r.checked = true;
    r.addEventListener("change", async () => {
      clearErr();
      try { await setTvSync(userId, Number(r.value)); }
      catch (e) { showErr(e.message || String(e)); }
    });
  });

  // Teams
  async function renderTeams() {
    const [followed, prefs] = await Promise.all([
      loadFollowedTeams(userId),
      loadTeamPrefs(userId),
    ]);
    if (followed.length === 0) {
      teamsEmpty.hidden = false;
      teamsListEl.innerHTML = "";
      return;
    }
    teamsEmpty.hidden = true;
    teamsListEl.innerHTML = followed.map((t) => {
      const slug = t.team_slug;
      const label = TEAM_LABELS[slug] || slug;
      const p = prefs[slug] || {};
      return `
        <details class="notif-team" data-slug="${slug}">
          <summary>
            <span class="notif-team-name">${label}</span>
            <span class="notif-team-count" data-count></span>
          </summary>
          <ul class="notif-team-types">
            ${NOTIF_TYPES.map((nt) => `
              <li>
                <label class="notif-type-row">
                  <input type="checkbox" data-type="${nt.key}" ${p[nt.key] ? "checked" : ""}>
                  <span class="notif-type-label">${nt.label}</span>
                  <span class="notif-type-hint">${nt.hint}</span>
                </label>
              </li>
            `).join("")}
          </ul>
        </details>
      `;
    }).join("");

    // Hook checkboxes + render the count badge for each team.
    teamsListEl.querySelectorAll(".notif-team").forEach((det) => {
      const slug = det.dataset.slug;
      const countEl = det.querySelector("[data-count]");
      function recount() {
        const on = det.querySelectorAll('input[type="checkbox"]:checked').length;
        countEl.textContent = on === 0 ? "" : `${on} on`;
      }
      recount();
      det.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
        cb.addEventListener("change", async () => {
          clearErr();
          try {
            await setTeamPref(userId, slug, cb.dataset.type, cb.checked);
            recount();
          } catch (e) {
            cb.checked = !cb.checked;
            showErr(e.message || String(e));
            recount();
          }
        });
      });
    });
  }

  await Promise.all([refreshDeviceRow(), renderTeams()]);

  // Re-render teams when the page's existing Follow form adds/removes a team.
  // Settings.js broadcasts via localStorage; we listen for the same signal.
  window.addEventListener("storage", (e) => {
    if (e.key === "ml-profile-updated") renderTeams().catch(() => {});
  });
  // Also listen for the same-tab custom event (settings.js fires a CustomEvent).
  document.addEventListener("ml:followed-teams-changed", () => {
    renderTeams().catch(() => {});
  });
}
