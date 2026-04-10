// /settings — customize your morning paper.
//
// Reads current profile + followed_teams, renders the controls, and writes
// changes back to Supabase with a 500ms debounce. Cross-tab sync happens via
// the broadcast below (localStorage ping that /home listens for).

import { supabase, requireAuth, getProfile, signOut } from "../auth/session.js";

const SECTION_LABELS = {
  headline: "The Team",
  scouting: "Scouting Report",
  stretch: "The Stretch",
  pressbox: "The Pressbox",
  farm: "Down on the Farm",
  slate: "Today's Slate",
  division: "Division",
  around_league: "Around the League",
  history: "This Day in History",
  my_players: "My Players",
};

const ALL_TEAM_SLUGS = [
  "angels","astros","athletics","blue-jays","braves","brewers","cardinals",
  "cubs","dbacks","dodgers","giants","guardians","mariners","marlins","mets",
  "nationals","orioles","padres","phillies","pirates","rangers","rays","reds",
  "red-sox","rockies","royals","tigers","twins","white-sox","yankees",
];

const readerName = document.getElementById("reader-name");
const saveState = document.getElementById("save-state");
const displayNameInput = document.getElementById("display-name");
const sectionsList = document.getElementById("sections-list");
const teamsList = document.getElementById("teams-list");
const teamSelect = document.getElementById("team-select");
const followForm = document.getElementById("follow-form");
const densityRow = document.getElementById("density-row");
const themeRow = document.getElementById("theme-row");
const errorBox = document.getElementById("settings-error");
const signoutLink = document.getElementById("signout-link");
const playerSearchInput = document.getElementById("player-search-input");
const playerResults = document.getElementById("player-results");
const playersList = document.getElementById("players-list");

let state = {
  userId: null,
  profile: null,
  followed: [],
  players: [],
  teamConfigs: new Map(),
};

// ---------- save state indicator ----------
function setSaveState(kind) {
  saveState.className = kind;
  saveState.textContent = kind === "saving" ? "saving…" : kind === "saved" ? "saved" : kind === "error" ? "error" : "idle";
}

function showError(msg) {
  errorBox.hidden = false;
  errorBox.textContent = msg;
  setSaveState("error");
}
function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

// Broadcast a profile change so open /home tabs refetch.
function broadcastChange() {
  try {
    localStorage.setItem("ml-profile-updated", String(Date.now()));
  } catch {}
}

// ---------- debounced profile write ----------
let saveTimer = null;
let pendingPatch = {};
function queueProfilePatch(patch) {
  Object.assign(pendingPatch, patch);
  setSaveState("saving");
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(flushProfilePatch, 500);
}

async function flushProfilePatch() {
  if (!Object.keys(pendingPatch).length) return;
  const patch = pendingPatch;
  pendingPatch = {};
  clearError();
  const { error } = await supabase
    .from("profiles")
    .update(patch)
    .eq("id", state.userId);
  if (error) {
    showError(`Save failed: ${error.message}`);
    return;
  }
  Object.assign(state.profile, patch);
  setSaveState("saved");
  broadcastChange();
}

// ---------- team configs (for display names) ----------
async function getTeamConfig(slug) {
  if (state.teamConfigs.has(slug)) return state.teamConfigs.get(slug);
  try {
    const res = await fetch(`../teams/${slug}.json`);
    if (!res.ok) throw new Error(`${res.status}`);
    const cfg = await res.json();
    state.teamConfigs.set(slug, cfg);
    return cfg;
  } catch {
    return { name: slug, full_name: slug };
  }
}

// ---------- rendering ----------
function renderSectionsList() {
  const order = state.profile.section_order || [];
  const vis = state.profile.section_visibility || {};
  sectionsList.innerHTML = "";
  for (const key of order) {
    const li = document.createElement("li");
    li.dataset.key = key;
    li.innerHTML = `
      <span class="drag-handle">⋮⋮</span>
      <label>
        <input type="checkbox" ${vis[key] !== false ? "checked" : ""}>
        <span class="section-label">${SECTION_LABELS[key] || key}</span>
      </label>
    `;
    const cb = li.querySelector("input[type=checkbox]");
    cb.addEventListener("change", () => {
      const next = { ...(state.profile.section_visibility || {}) };
      next[key] = cb.checked;
      state.profile.section_visibility = next;
      queueProfilePatch({ section_visibility: next });
    });
    sectionsList.appendChild(li);
  }

  Sortable.create(sectionsList, {
    animation: 140,
    handle: ".drag-handle",
    ghostClass: "sortable-ghost",
    chosenClass: "sortable-chosen",
    onEnd: () => {
      const newOrder = Array.from(sectionsList.querySelectorAll("li")).map((el) => el.dataset.key);
      state.profile.section_order = newOrder;
      queueProfilePatch({ section_order: newOrder });
    },
  });
}

async function renderTeamsList() {
  teamsList.innerHTML = "";
  for (const fol of state.followed) {
    const cfg = await getTeamConfig(fol.team_slug);
    const li = document.createElement("li");
    li.dataset.slug = fol.team_slug;
    li.innerHTML = `
      <span class="drag-handle">⋮⋮</span>
      <span class="team-name">${cfg.full_name || cfg.name || fol.team_slug}</span>
      <button type="button" class="unfollow-btn" title="Unfollow">×</button>
    `;
    li.querySelector(".unfollow-btn").addEventListener("click", () => unfollowTeam(fol.team_slug));
    teamsList.appendChild(li);
  }

  Sortable.create(teamsList, {
    animation: 140,
    handle: ".drag-handle",
    ghostClass: "sortable-ghost",
    chosenClass: "sortable-chosen",
    onEnd: saveTeamOrder,
  });

  renderTeamSelect();
}

function renderTeamSelect() {
  const followedSet = new Set(state.followed.map((f) => f.team_slug));
  const available = ALL_TEAM_SLUGS.filter((s) => !followedSet.has(s));
  teamSelect.innerHTML = available.map((s) => `<option value="${s}">${s}</option>`).join("");
}

async function saveTeamOrder() {
  const slugs = Array.from(teamsList.querySelectorAll("li")).map((el) => el.dataset.slug);
  setSaveState("saving");
  clearError();
  // Rewrite positions in a single batch via upsert.
  const rows = slugs.map((slug, i) => ({
    user_id: state.userId,
    team_slug: slug,
    position: i,
  }));
  const { error } = await supabase.from("followed_teams").upsert(rows, { onConflict: "user_id,team_slug" });
  if (error) {
    showError(`Reorder failed: ${error.message}`);
    return;
  }
  state.followed = slugs.map((slug, i) => ({ team_slug: slug, position: i }));
  setSaveState("saved");
  broadcastChange();
}

async function followTeam(slug) {
  setSaveState("saving");
  clearError();
  const nextPos = state.followed.length;
  const { error } = await supabase.from("followed_teams").insert({
    user_id: state.userId,
    team_slug: slug,
    position: nextPos,
  });
  if (error) {
    showError(`Could not follow ${slug}: ${error.message}`);
    return;
  }
  state.followed.push({ team_slug: slug, position: nextPos });
  setSaveState("saved");
  broadcastChange();
  await renderTeamsList();
}

async function unfollowTeam(slug) {
  setSaveState("saving");
  clearError();
  const { error } = await supabase
    .from("followed_teams")
    .delete()
    .eq("user_id", state.userId)
    .eq("team_slug", slug);
  if (error) {
    showError(`Could not unfollow ${slug}: ${error.message}`);
    return;
  }
  state.followed = state.followed.filter((f) => f.team_slug !== slug);
  setSaveState("saved");
  broadcastChange();
  await renderTeamsList();
}

function renderRadios() {
  for (const input of densityRow.querySelectorAll("input")) {
    input.checked = input.value === (state.profile.density || "full");
    input.addEventListener("change", () => {
      if (!input.checked) return;
      state.profile.density = input.value;
      queueProfilePatch({ density: input.value });
    });
  }
  for (const input of themeRow.querySelectorAll("input")) {
    input.checked = input.value === (state.profile.theme || "dark");
    input.addEventListener("change", () => {
      if (!input.checked) return;
      state.profile.theme = input.value;
      queueProfilePatch({ theme: input.value });
      // Apply theme immediately on this page too.
      document.body.classList.toggle("theme-paper", input.value === "paper");
      document.body.classList.toggle("theme-dark", input.value === "dark");
    });
  }
}

function renderDisplayName() {
  displayNameInput.value = state.profile.display_name || "";
  let nameTimer = null;
  displayNameInput.addEventListener("input", () => {
    if (nameTimer) clearTimeout(nameTimer);
    setSaveState("saving");
    nameTimer = setTimeout(() => {
      const name = displayNameInput.value.trim() || null;
      state.profile.display_name = name;
      queueProfilePatch({ display_name: name });
      readerName.textContent = name || "—";
    }, 500);
  });
}

// ---------- player tracker ----------
async function loadFollowedPlayers() {
  const { data, error } = await supabase
    .from("followed_players")
    .select("mlbam_id, full_name, primary_position, mlb_team_abbr, position")
    .order("position", { ascending: true });
  if (error) throw error;
  return data || [];
}

let searchTimer = null;
function handlePlayerSearchInput() {
  const q = playerSearchInput.value.trim();
  if (searchTimer) clearTimeout(searchTimer);
  if (q.length < 2) {
    playerResults.innerHTML = "";
    return;
  }
  searchTimer = setTimeout(() => runPlayerSearch(q), 250);
}

async function runPlayerSearch(q) {
  try {
    // MLB Stats API person search. Active players only; current year.
    const url = `https://statsapi.mlb.com/api/v1/people/search?names=${encodeURIComponent(q)}&active=true`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`search ${res.status}`);
    const json = await res.json();
    const people = json.people || [];
    const followedSet = new Set(state.players.map((p) => p.mlbam_id));
    playerResults.innerHTML = "";
    for (const p of people.slice(0, 8)) {
      if (followedSet.has(p.id)) continue;
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="player-name">${p.fullName}</span>
        <span class="player-meta">${p.primaryPosition?.abbreviation || ""} · ${p.currentTeam?.name || "—"}</span>
        <button type="button" class="player-add">Add</button>
      `;
      li.querySelector(".player-add").addEventListener("click", () => addPlayer(p));
      playerResults.appendChild(li);
    }
    if (playerResults.children.length === 0) {
      playerResults.innerHTML = `<li class="player-empty">No matches.</li>`;
    }
  } catch (err) {
    playerResults.innerHTML = `<li class="player-empty">Search failed: ${err.message}</li>`;
  }
}

async function addPlayer(p) {
  setSaveState("saving");
  clearError();
  const nextPos = state.players.length;
  const row = {
    user_id: state.userId,
    mlbam_id: p.id,
    full_name: p.fullName,
    primary_position: p.primaryPosition?.abbreviation || null,
    mlb_team_id: p.currentTeam?.id || null,
    mlb_team_abbr: p.currentTeam?.abbreviation || p.currentTeam?.teamCode || null,
    position: nextPos,
  };
  const { error } = await supabase.from("followed_players").insert(row);
  if (error) {
    showError(`Could not add ${p.fullName}: ${error.message}`);
    return;
  }
  state.players.push({
    mlbam_id: row.mlbam_id,
    full_name: row.full_name,
    primary_position: row.primary_position,
    mlb_team_abbr: row.mlb_team_abbr,
    position: row.position,
  });
  setSaveState("saved");
  broadcastChange();
  playerSearchInput.value = "";
  playerResults.innerHTML = "";
  renderPlayersList();
}

async function removePlayer(mlbamId) {
  setSaveState("saving");
  clearError();
  const { error } = await supabase
    .from("followed_players")
    .delete()
    .eq("user_id", state.userId)
    .eq("mlbam_id", mlbamId);
  if (error) {
    showError(`Could not remove player: ${error.message}`);
    return;
  }
  state.players = state.players.filter((p) => p.mlbam_id !== mlbamId);
  setSaveState("saved");
  broadcastChange();
  renderPlayersList();
}

function renderPlayersList() {
  playersList.innerHTML = "";
  if (state.players.length === 0) {
    playersList.innerHTML = `<li class="player-empty">No players followed yet. Search above.</li>`;
    return;
  }
  for (const p of state.players) {
    const li = document.createElement("li");
    li.dataset.mlbamId = String(p.mlbam_id);
    const posTeam = [p.primary_position, p.mlb_team_abbr].filter(Boolean).join(" · ");
    li.innerHTML = `
      <span class="drag-handle">⋮⋮</span>
      <span class="team-name">${p.full_name}${posTeam ? ` <span class="player-meta">${posTeam}</span>` : ""}</span>
      <button type="button" class="unfollow-btn" title="Remove">×</button>
    `;
    li.querySelector(".unfollow-btn").addEventListener("click", () => removePlayer(p.mlbam_id));
    playersList.appendChild(li);
  }
  Sortable.create(playersList, {
    animation: 140,
    handle: ".drag-handle",
    ghostClass: "sortable-ghost",
    chosenClass: "sortable-chosen",
    onEnd: savePlayerOrder,
  });
}

async function savePlayerOrder() {
  const ids = Array.from(playersList.querySelectorAll("li[data-mlbam-id]")).map((el) => Number(el.dataset.mlbamId));
  setSaveState("saving");
  clearError();
  const rows = ids.map((mlbam_id, i) => {
    const existing = state.players.find((p) => p.mlbam_id === mlbam_id);
    return {
      user_id: state.userId,
      mlbam_id,
      full_name: existing?.full_name || "",
      primary_position: existing?.primary_position || null,
      mlb_team_abbr: existing?.mlb_team_abbr || null,
      position: i,
    };
  });
  const { error } = await supabase.from("followed_players").upsert(rows, { onConflict: "user_id,mlbam_id" });
  if (error) {
    showError(`Reorder failed: ${error.message}`);
    return;
  }
  state.players = ids.map((mlbam_id, i) => {
    const existing = state.players.find((p) => p.mlbam_id === mlbam_id);
    return { ...existing, position: i };
  });
  setSaveState("saved");
  broadcastChange();
}

// ---------- bootstrap ----------
async function loadFollowed() {
  const { data, error } = await supabase
    .from("followed_teams")
    .select("team_slug, position")
    .order("position", { ascending: true });
  if (error) throw error;
  return data || [];
}

async function init() {
  const auth = await requireAuth();
  if (!auth) return;
  state.userId = auth.session.user.id;
  state.profile = auth.profile || (await getProfile({ force: true }));
  if (!state.profile) {
    showError("Could not load your profile.");
    return;
  }
  readerName.textContent = state.profile.display_name || auth.session.user.email;

  // Apply current theme to the settings page itself so it matches.
  document.body.classList.toggle("theme-paper", state.profile.theme === "paper");
  document.body.classList.toggle("theme-dark", state.profile.theme !== "paper");

  state.followed = await loadFollowed();
  state.players = await loadFollowedPlayers();

  renderDisplayName();
  renderSectionsList();
  await renderTeamsList();
  renderPlayersList();
  playerSearchInput.addEventListener("input", handlePlayerSearchInput);
  renderRadios();
  setSaveState("idle");

  followForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const slug = teamSelect.value;
    if (slug) await followTeam(slug);
  });

  signoutLink.addEventListener("click", async (e) => {
    e.preventDefault();
    await signOut();
    window.location.href = "../auth/";
  });
}

init().catch((err) => {
  console.error("settings init failed", err);
  showError(err.message || "Something went wrong.");
});
