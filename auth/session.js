// Shared session + Supabase client for every page that needs auth state.
// Import `supabase` for a single shared client, or the helpers below.
//
//   import { supabase, requireAuth, getProfile, onAuthChange } from "../auth/session.js";
//
// getSession()       → current session or null, never throws
// getProfile()       → user's profiles row; creates a default if missing; cached per page load
// requireAuth(path)  → returns {session, profile} or redirects to the auth page
// onAuthChange(cb)   → subscribes to auth state changes (signin, signout, token refresh, cross-tab)

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.103.0";
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "../config/supabase.js";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
    storageKey: "ml-auth",
  },
});

// Resolve the auth page URL relative to wherever the caller is running from.
// Pages under /home/, /settings/, /scorecard/ all sit one directory above the repo root.
function authUrl() {
  return new URL("../auth/index.html", document.baseURI).toString();
}

export async function getSession() {
  const { data, error } = await supabase.auth.getSession();
  if (error) return null;
  return data?.session || null;
}

let _profileCache = null;
let _profileUserId = null;

const DEFAULT_SECTION_VISIBILITY = {
  headline: true,
  scouting: true,
  stretch: true,
  pressbox: true,
  farm: true,
  slate: true,
  division: true,
  around_league: true,
  history: true,
  my_players: true,
};
const DEFAULT_SECTION_ORDER = [
  "headline", "scouting", "stretch", "pressbox", "farm",
  "slate", "division", "around_league", "history", "my_players",
];

// Merge any missing default keys into an existing profile so new sections
// appear automatically for users who signed up before the section existed.
function backfillDefaults(profile) {
  const vis = { ...DEFAULT_SECTION_VISIBILITY, ...(profile.section_visibility || {}) };
  const order = Array.isArray(profile.section_order) ? [...profile.section_order] : [];
  for (const key of DEFAULT_SECTION_ORDER) {
    if (!order.includes(key)) order.push(key);
  }
  profile.section_visibility = vis;
  profile.section_order = order;
  return profile;
}

export async function getProfile({ force = false } = {}) {
  const session = await getSession();
  if (!session) {
    _profileCache = null;
    _profileUserId = null;
    return null;
  }
  if (!force && _profileCache && _profileUserId === session.user.id) {
    return _profileCache;
  }

  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", session.user.id)
    .maybeSingle();

  if (error) {
    console.warn("getProfile: select failed", error);
    return null;
  }

  if (data) {
    backfillDefaults(data);
    _profileCache = data;
    _profileUserId = session.user.id;
    return data;
  }

  // No profile row yet — the auth trigger should have created one, but if it
  // didn't (older signup path, trigger failure), create a default so the page
  // can continue rendering.
  const fallback = {
    id: session.user.id,
    display_name: session.user.email?.split("@")[0] || null,
    section_visibility: DEFAULT_SECTION_VISIBILITY,
    section_order: DEFAULT_SECTION_ORDER,
    density: "full",
    theme: "dark",
  };
  const { data: inserted, error: insertErr } = await supabase
    .from("profiles")
    .insert(fallback)
    .select()
    .maybeSingle();
  if (insertErr) {
    console.warn("getProfile: fallback insert failed", insertErr);
    return fallback;
  }
  _profileCache = inserted || fallback;
  _profileUserId = session.user.id;
  return _profileCache;
}

export async function requireAuth() {
  const session = await getSession();
  if (!session) {
    window.location.href = authUrl();
    return null;
  }
  const profile = await getProfile();
  return { session, profile };
}

export function onAuthChange(callback) {
  const { data } = supabase.auth.onAuthStateChange((event, session) => {
    // Invalidate profile cache on any auth state change.
    if (!session || (_profileUserId && session.user.id !== _profileUserId)) {
      _profileCache = null;
      _profileUserId = null;
    }
    try {
      callback(event, session);
    } catch (err) {
      console.warn("onAuthChange callback threw", err);
    }
  });
  return () => data?.subscription?.unsubscribe();
}

export async function signOut() {
  _profileCache = null;
  _profileUserId = null;
  await supabase.auth.signOut();
}
