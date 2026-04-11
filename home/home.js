// /home — the personalized merged briefing.
//
// Flow:
//   1. Check session. Logged out → render preview with CTA to /auth.
//   2. Load profile + followed_teams + team configs (in parallel).
//   3. For each followed team, fetch ../{slug}/index.html, parse with
//      DOMParser, extract the <section> blocks whose IDs correspond to
//      the user's section_order + section_visibility, wrap them in a
//      per-team block styled with the team's colors.
//   4. Apply density + theme body classes from profile.
//
// Section ID mapping — profile keys vs. static page markup:
//   profile key    → HTML id
//   headline       → team
//   scouting       → scout
//   stretch        → pulse
//   pressbox       → pressbox
//   farm           → farm
//   slate          → today
//   division       → div
//   around_league  → league
//   history        → history

import { supabase, getSession, getProfile, signOut, onAuthChange } from "../auth/session.js";

const SECTION_ID_MAP = {
  headline: "team",
  scouting: "scout",
  stretch: "pulse",
  pressbox: "pressbox",
  farm: "farm",
  slate: "today",
  division: "div",
  around_league: "league",
  history: "history",
};

const SECTION_LABELS = {
  headline: "The Team",
  scouting: "Scouting",
  stretch: "The Stretch",
  pressbox: "Pressbox",
  farm: "Farm",
  slate: "Slate",
  division: "Division",
  around_league: "Around the League",
  history: "History",
  my_players: "My Players",
};

const shell = document.getElementById("home-shell");
const readerName = document.getElementById("reader-name");
const followCount = document.getElementById("follow-count");
const todayStamp = document.getElementById("today-stamp");
const signoutLink = document.getElementById("signout-link");

// Cache extracted sections per team slug for the page lifetime.
const teamHtmlCache = new Map();
// Cache team config JSON per slug.
const teamConfigCache = new Map();
// Holds the list of all 30 team slugs for the picker.
let allTeamSlugs = null;

function stamp() {
  const d = new Date();
  const opts = { weekday: "long", month: "long", day: "numeric", year: "numeric" };
  todayStamp.textContent = d.toLocaleDateString("en-US", opts);
}
stamp();

function renderLoading(msg = "Loading your lineup…") {
  shell.innerHTML = `<div class="home-loading"><p>${msg}</p></div>`;
}
function renderError(msg) {
  shell.innerHTML = `<div class="home-error"><p>${msg}</p></div>`;
}

// Guest preview: let them pick one team, show sections 1-3 fully, blur the rest.
const GUEST_DEFAULT_SLUG = "cubs";
const GUEST_UNLOCKED_COUNT = 3; // first N sections in DEFAULT order render fully
const GUEST_SECTION_ORDER = [
  "headline", "scouting", "stretch", "pressbox", "farm",
  "slate", "division", "around_league", "history",
];

function getGuestTeam() {
  try {
    return localStorage.getItem("ml-guest-team") || GUEST_DEFAULT_SLUG;
  } catch {
    return GUEST_DEFAULT_SLUG;
  }
}
function setGuestTeam(slug) {
  try { localStorage.setItem("ml-guest-team", slug); } catch {}
}

function renderGuestTeamPicker(currentSlug) {
  const wrap = document.createElement("div");
  wrap.className = "guest-team-picker";
  wrap.innerHTML = `
    <label>
      <span>Previewing</span>
      <select id="guest-team-select"></select>
    </label>
  `;
  const select = wrap.querySelector("select");
  const slugs = [
    "angels","astros","athletics","blue-jays","braves","brewers","cardinals",
    "cubs","dbacks","dodgers","giants","guardians","mariners","marlins","mets",
    "nationals","orioles","padres","phillies","pirates","rangers","rays","reds",
    "red-sox","rockies","royals","tigers","twins","white-sox","yankees",
  ];
  for (const s of slugs) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    if (s === currentSlug) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => {
    setGuestTeam(select.value);
    renderHome();
  });
  return wrap;
}

function renderGuestCta(position) {
  const div = document.createElement("div");
  div.className = `home-guest-cta home-guest-cta-${position}`;
  if (position === "top") {
    div.innerHTML = `
      <div class="guest-cta-kicker">Guest Preview</div>
      <h2>This is just a taste.</h2>
      <p>You're seeing the top section from three featured teams. Create a free account to pick your own teams, choose your sections, drag them into any order, and add your fantasy players.</p>
      <div class="guest-cta-actions">
        <a href="../auth/" class="home-btn-primary">Create a free account</a>
        <a href="../auth/" class="home-btn-link">Already a member? Sign in</a>
      </div>
    `;
  } else {
    div.innerHTML = `
      <h2>Want the whole paper?</h2>
      <p>Nine sections per team. My Players tracker. Density and theme controls. All yours, free.</p>
      <div class="guest-cta-actions">
        <a href="../auth/" class="home-btn-primary">Claim your press pass</a>
      </div>
    `;
  }
  return div;
}

async function renderPreview() {
  readerName.textContent = "Guest";
  followCount.textContent = "preview";
  signoutLink.hidden = true;
  shell.innerHTML = "";

  // Apply default dark theme for the preview (no profile).
  document.body.classList.add("theme-dark");
  document.body.classList.remove("theme-paper");

  shell.appendChild(renderGuestCta("top"));

  const slug = getGuestTeam();
  shell.appendChild(renderGuestTeamPicker(slug));

  try {
    const [cfg, doc] = await Promise.all([getTeamConfig(slug), getTeamHtml(slug)]);
    const sections = [];
    for (let i = 0; i < GUEST_SECTION_ORDER.length; i++) {
      const key = GUEST_SECTION_ORDER[i];
      const htmlId = SECTION_ID_MAP[key];
      const node = extractSection(doc, htmlId);
      if (!node) continue;
      if (i >= GUEST_UNLOCKED_COUNT) {
        // Wrap locked sections in a blur shell with an unlock overlay.
        const locked = document.createElement("div");
        locked.className = "guest-locked";
        const inner = document.createElement("div");
        inner.className = "guest-locked-inner";
        inner.appendChild(node);
        locked.appendChild(inner);
        const overlay = document.createElement("div");
        overlay.className = "guest-locked-overlay";
        overlay.innerHTML = `
          <div class="guest-lock-icon">🔒</div>
          <div class="guest-lock-title">${SECTION_LABELS[key] || key}</div>
          <p>Sign up to unlock this section — and all nine, for every team.</p>
          <a href="../auth/" class="home-btn-primary">Claim your press pass</a>
        `;
        locked.appendChild(overlay);
        sections.push(locked);
      } else {
        sections.push(node);
      }
    }
    const block = renderTeamBlock(cfg, sections);
    const fullLink = block.querySelector("#full-link");
    if (fullLink) {
      fullLink.id = "";
      fullLink.setAttribute("href", `../${slug}/`);
    }

    // Columnists for guests: unblurred, always-visible, above the numbered
    // sections. This IS the wedge — guests taste the editorial voice before
    // they hit the paywall.
    const columnistsNode = extractColumnists(doc);
    if (columnistsNode) {
      const strip = block.querySelector(".team-strip");
      if (strip && strip.nextSibling) {
        block.insertBefore(columnistsNode, strip.nextSibling);
      } else {
        block.appendChild(columnistsNode);
      }
      shuffleColumnistsGrid(columnistsNode.querySelector(".columnists-grid"));
    }

    shell.appendChild(block);
  } catch (err) {
    console.warn(`guest preview ${slug} failed`, err);
    const errDiv = document.createElement("div");
    errDiv.className = "team-block-error";
    errDiv.textContent = `Could not load ${slug}: ${err.message}`;
    shell.appendChild(errDiv);
  }

  shell.appendChild(renderGuestCta("bottom"));
}

function renderEmpty() {
  shell.innerHTML = `
    <div class="home-empty">
      <h2>Pick your teams.</h2>
      <p>Follow at least one team to see your merged briefing. You can always change this later.</p>
    </div>
    <div class="team-picker" id="team-picker"></div>
  `;
  mountTeamPicker();
}

async function loadAllTeamSlugs() {
  if (allTeamSlugs) return allTeamSlugs;
  // There's no public manifest of all 30 teams. Hard-code the list — it changes
  // only when MLB adds or relocates a franchise. Keeps /home zero-fetch for
  // team discovery.
  allTeamSlugs = [
    "angels","astros","athletics","blue-jays","braves","brewers","cardinals",
    "cubs","dbacks","dodgers","giants","guardians","mariners","marlins","mets",
    "nationals","orioles","padres","phillies","pirates","rangers","rays","reds",
    "red-sox","rockies","royals","tigers","twins","white-sox","yankees",
  ];
  return allTeamSlugs;
}

async function getTeamConfig(slug) {
  if (teamConfigCache.has(slug)) return teamConfigCache.get(slug);
  const res = await fetch(`../teams/${slug}.json`);
  if (!res.ok) throw new Error(`team config ${slug} ${res.status}`);
  const cfg = await res.json();
  teamConfigCache.set(slug, cfg);
  return cfg;
}

async function getTeamHtml(slug) {
  if (teamHtmlCache.has(slug)) return teamHtmlCache.get(slug);
  const res = await fetch(`../${slug}/`, { cache: "default" });
  if (!res.ok) throw new Error(`team page ${slug} ${res.status}`);
  const text = await res.text();
  const doc = new DOMParser().parseFromString(text, "text/html");
  teamHtmlCache.set(slug, doc);
  return doc;
}

async function loadFollowedTeams() {
  const { data, error } = await supabase
    .from("followed_teams")
    .select("team_slug, position")
    .order("position", { ascending: true });
  if (error) throw error;
  return data || [];
}

async function addFollowedTeam(slug) {
  const session = await getSession();
  if (!session) return;
  const existing = await loadFollowedTeams();
  if (existing.find((f) => f.team_slug === slug)) return;
  const nextPos = existing.length;
  const { error } = await supabase.from("followed_teams").insert({
    user_id: session.user.id,
    team_slug: slug,
    position: nextPos,
  });
  if (error) {
    alert(`Could not follow ${slug}: ${error.message}`);
    return;
  }
  await renderHome();
}

async function removeFollowedTeam(slug) {
  const session = await getSession();
  if (!session) return;
  const { error } = await supabase
    .from("followed_teams")
    .delete()
    .eq("user_id", session.user.id)
    .eq("team_slug", slug);
  if (error) {
    alert(`Could not unfollow ${slug}: ${error.message}`);
    return;
  }
  await renderHome();
}

async function mountTeamPicker() {
  const picker = document.getElementById("team-picker");
  if (!picker) return;
  const [slugs, followed] = await Promise.all([
    loadAllTeamSlugs(),
    loadFollowedTeams(),
  ]);
  const followedSet = new Set(followed.map((f) => f.team_slug));
  const options = slugs
    .filter((s) => !followedSet.has(s))
    .map((s) => `<option value="${s}">${s}</option>`)
    .join("");
  const chips = followed
    .map(
      (f) => `
      <span class="chip">
        ${f.team_slug}
        <button type="button" data-slug="${f.team_slug}" title="Unfollow">×</button>
      </span>`,
    )
    .join("");

  picker.innerHTML = `
    <h3>Your Teams · Quick Pick</h3>
    <form id="follow-form">
      <select id="team-select">${options}</select>
      <button type="submit" class="home-btn-primary">Follow</button>
    </form>
    <div class="followed">${chips || "(no teams followed yet)"}</div>
  `;

  picker.querySelector("#follow-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const slug = picker.querySelector("#team-select").value;
    if (slug) await addFollowedTeam(slug);
  });
  picker.querySelectorAll(".chip button").forEach((btn) => {
    btn.addEventListener("click", () => removeFollowedTeam(btn.dataset.slug));
  });
}

function extractSection(doc, htmlId) {
  // Team pages wrap sections as <section id="X" open>. Clone the node so we
  // don't strip it from the source doc (cached for re-renders).
  const node = doc.querySelector(`section#${htmlId}`);
  if (!node) return null;
  return node.cloneNode(true);
}

function extractColumnists(doc) {
  // The columnists section sits above the numbered sections on every team
  // page. Clone the whole <section id="columnists"> block so we can mount it
  // in /home verbatim.
  const node = doc.querySelector("section#columnists");
  if (!node) return null;
  return node.cloneNode(true);
}

// Reshuffles the three <article class="column"> children of a grid in place.
// The inline <script> inside the cloned section does NOT re-execute on
// DOMParser append, so we manually invoke this after mounting.
function shuffleColumnistsGrid(gridEl) {
  if (!gridEl) return;
  const kids = Array.from(gridEl.children);
  for (let i = kids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [kids[i], kids[j]] = [kids[j], kids[i]];
  }
  kids.forEach((k) => gridEl.appendChild(k));
}

function renderTeamBlock(cfg, sectionsHtml) {
  const colors = cfg.colors || {};
  const block = document.createElement("div");
  block.className = "team-block";
  block.style.setProperty("--team-primary", colors.primary || "#0E3386");
  block.style.setProperty("--team-primary-hi", colors.primary_hi || "#2a56c4");
  block.style.setProperty("--team-accent", colors.accent || "#CC3433");
  block.style.setProperty("--team-accent-hi", colors.accent_hi || "#e8544f");

  const strip = document.createElement("header");
  strip.className = "team-strip";
  strip.innerHTML = `
    <h2 class="strip-name">${cfg.full_name || cfg.name || cfg.id}</h2>
    <div class="strip-meta">
      <span>${cfg.division_name || ""}</span>
      <a href="../${cfg.id === 112 ? "cubs" : ""}" id="full-link">Full page →</a>
    </div>
  `;
  // Fix the full-link slug: we don't have it on cfg directly, derive from the
  // config file we loaded. Caller passes slug via dataset.
  block.appendChild(strip);

  if (sectionsHtml.length === 0) {
    const msg = document.createElement("div");
    msg.className = "team-block-error";
    msg.textContent = "No visible sections for this team. Check your settings.";
    block.appendChild(msg);
  } else {
    for (const node of sectionsHtml) block.appendChild(node);
  }
  return block;
}

async function loadFollowedPlayers() {
  const { data, error } = await supabase
    .from("followed_players")
    .select("mlbam_id, full_name, primary_position, mlb_team_abbr, position")
    .order("position", { ascending: true });
  if (error) {
    console.warn("loadFollowedPlayers failed", error);
    return [];
  }
  return data || [];
}

// Fetch this season's hitting + pitching stats for a list of MLB player ids.
// Uses the MLB Stats API in one batched call.
async function fetchPlayerStats(mlbamIds) {
  if (!mlbamIds.length) return {};
  const ids = mlbamIds.join(",");
  const year = new Date().getFullYear();
  const url = `https://statsapi.mlb.com/api/v1/people?personIds=${ids}&hydrate=stats(group=[hitting,pitching],type=[season],season=${year})`;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`stats ${res.status}`);
    const json = await res.json();
    const out = {};
    for (const person of json.people || []) {
      const hitting = {}; const pitching = {};
      for (const group of person.stats || []) {
        const stat = group.splits?.[0]?.stat || {};
        if (group.group?.displayName === "hitting") Object.assign(hitting, stat);
        if (group.group?.displayName === "pitching") Object.assign(pitching, stat);
      }
      out[person.id] = { hitting, pitching };
    }
    return out;
  } catch (err) {
    console.warn("fetchPlayerStats failed", err);
    return {};
  }
}

function formatPlayerLine(player, stats) {
  const isPitcher = player.primary_position === "P" || player.primary_position === "TWP";
  if (isPitcher && stats?.pitching && Object.keys(stats.pitching).length) {
    const p = stats.pitching;
    return `${p.wins ?? 0}-${p.losses ?? 0} · ${p.era ?? "—"} ERA · ${p.strikeOuts ?? 0} K · ${p.inningsPitched ?? "0.0"} IP`;
  }
  if (stats?.hitting && Object.keys(stats.hitting).length) {
    const h = stats.hitting;
    return `${h.avg ?? "—"} / ${h.obp ?? "—"} / ${h.slg ?? "—"} · ${h.homeRuns ?? 0} HR · ${h.rbi ?? 0} RBI`;
  }
  return "No stats yet this season.";
}

const ABBR_TO_SLUG = {
  "LAA": "angels", "HOU": "astros", "ATH": "athletics", "TOR": "blue-jays",
  "ATL": "braves", "MIL": "brewers", "STL": "cardinals", "CHC": "cubs",
  "AZ": "dbacks", "ARI": "dbacks", "LAD": "dodgers", "SF": "giants",
  "SFG": "giants", "CLE": "guardians", "SEA": "mariners", "MIA": "marlins",
  "NYM": "mets", "WSH": "nationals", "WAS": "nationals", "BAL": "orioles",
  "SD": "padres", "SDP": "padres", "PHI": "phillies", "PIT": "pirates",
  "TEX": "rangers", "TB": "rays", "TBR": "rays", "BOS": "red-sox",
  "CIN": "reds", "COL": "rockies", "KC": "royals", "KCR": "royals",
  "DET": "tigers", "MIN": "twins", "CWS": "white-sox", "CHW": "white-sox",
  "NYY": "yankees",
};

function renderMyPlayersSection(players, statsMap) {
  const section = document.createElement("section");
  section.id = "my-players";
  section.className = "home-my-players";
  section.setAttribute("open", "");
  const heading = document.createElement("div");
  heading.className = "my-players-head";
  heading.innerHTML = `<h2>My Players</h2><span class="my-players-sub">Your fantasy roster</span>`;
  section.appendChild(heading);

  if (!players.length) {
    const empty = document.createElement("p");
    empty.className = "my-players-empty";
    empty.innerHTML = `No players followed yet. <a href="../settings/">Add some</a> in settings.`;
    section.appendChild(empty);
    return section;
  }

  const list = document.createElement("ul");
  list.className = "my-players-list";
  for (const p of players) {
    const li = document.createElement("li");
    const stats = statsMap[p.mlbam_id];
    const posTeam = [p.primary_position, p.mlb_team_abbr].filter(Boolean).join(" · ") || "—";
    const slug = ABBR_TO_SLUG[p.mlb_team_abbr] || "";
    const nameHtml = (p.mlbam_id && slug)
      ? `<player-card pid="${p.mlbam_id}" team="${slug}">${p.full_name}</player-card>`
      : p.full_name;
    li.innerHTML = `
      <div class="player-row-head">
        <span class="player-row-name">${nameHtml}</span>
        <span class="player-row-meta">${posTeam}</span>
      </div>
      <div class="player-row-stats">${formatPlayerLine(p, stats)}</div>
    `;
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}

function renderSectionMenu(profile) {
  const visibility = profile.section_visibility || {};
  const order = profile.section_order || [];
  const visible = order.filter((k) => visibility[k] !== false);
  if (!visible.length) return null;
  const nav = document.createElement("nav");
  nav.className = "home-toc";
  nav.setAttribute("aria-label", "Sections");
  const title = document.createElement("span");
  title.className = "home-toc-title";
  title.textContent = "Sections";
  nav.appendChild(title);
  const list = document.createElement("ul");
  for (let i = 0; i < visible.length; i++) {
    const key = visible[i];
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `#section-${key}`;
    a.innerHTML = `<span class="toc-num">${String(i + 1).padStart(2, "0")}</span><span class="toc-label">${SECTION_LABELS[key] || key}</span>`;
    li.appendChild(a);
    list.appendChild(li);
  }
  nav.appendChild(list);
  return nav;
}

async function renderMergedView(profile, followed) {
  shell.innerHTML = "";
  const visibility = profile.section_visibility || {};
  const order = profile.section_order || [];

  // Section menu at the top — mirrors the user's order + visibility.
  const menu = renderSectionMenu(profile);
  if (menu) shell.appendChild(menu);

  // Apply density + theme classes.
  document.body.classList.toggle("density-compact", profile.density === "compact");
  document.body.classList.toggle("density-full", profile.density !== "compact");
  document.body.classList.toggle("theme-paper", profile.theme === "paper");
  document.body.classList.toggle("theme-dark", profile.theme === "dark");

  // Load followed players and their stats up front (parallel with team HTML).
  // The "my_players" section renders client-side; all others come from static
  // team pages via DOMParser.
  const myPlayersVisible = visibility.my_players !== false && order.includes("my_players");
  let players = [];
  let playerStats = {};
  if (myPlayersVisible) {
    players = await loadFollowedPlayers();
    if (players.length) {
      playerStats = await fetchPlayerStats(players.map((p) => p.mlbam_id));
    }
  }

  // Track which section keys we've already anchored so #section-<key> in the
  // TOC points at the first occurrence across all teams.
  const anchored = new Set();

  // My Players is a cross-team section. If it appears before "headline" in
  // the user's section_order, render it above the team blocks. Otherwise
  // render it below them. (It's a single standalone block, not per-team.)
  const myPlayersIdx = order.indexOf("my_players");
  const headlineIdx = order.indexOf("headline");
  const myPlayersFirst = myPlayersVisible && myPlayersIdx !== -1 &&
    (headlineIdx === -1 || myPlayersIdx < headlineIdx);
  if (myPlayersFirst) {
    const mp = renderMyPlayersSection(players, playerStats);
    mp.id = "section-my_players";
    anchored.add("my_players");
    shell.appendChild(mp);
  }

  // Render each team in the user's followed-order.
  for (const fol of followed) {
    const slug = fol.team_slug;
    try {
      const [cfg, doc] = await Promise.all([getTeamConfig(slug), getTeamHtml(slug)]);
      const sections = [];
      for (const key of order) {
        if (visibility[key] === false) continue;
        if (key === "my_players") continue; // rendered above, not per-team
        const htmlId = SECTION_ID_MAP[key];
        if (!htmlId) continue;
        const node = extractSection(doc, htmlId);
        if (node) {
          // Tag any player-card elements with their source team so the
          // component loads the right players-<slug>.json from the home page.
          node.querySelectorAll("player-card").forEach((el) => {
            if (!el.getAttribute("team")) el.setAttribute("team", slug);
          });
          if (!anchored.has(key)) {
            node.id = `section-${key}`;
            anchored.add(key);
          }
          sections.push(node);
        }
      }
      const block = renderTeamBlock(cfg, sections);
      // Fix up the Full page → link to actually point to the team slug.
      const fullLink = block.querySelector("#full-link");
      if (fullLink) {
        fullLink.id = "";
        fullLink.setAttribute("href", `../${slug}/`);
      }

      // Wrap this team's Columnists block in a collapsed <details> and
      // prepend it to the team block so the columns sit above the numbered
      // sections. Summary text names all three writers for at-a-glance.
      const columnistsNode = extractColumnists(doc);
      if (columnistsNode) {
        const details = document.createElement("details");
        details.className = "home-columnists-wrap";
        const summary = document.createElement("summary");
        const names = Array.from(columnistsNode.querySelectorAll(".column-name"))
          .map((el) => el.textContent.trim())
          .filter(Boolean);
        summary.textContent = names.length
          ? `Columnists: ${names.join(", ")}`
          : "Columnists";
        details.appendChild(summary);
        details.appendChild(columnistsNode);
        // Insert after the team strip header but before the first numbered section
        const strip = block.querySelector(".team-strip");
        if (strip && strip.nextSibling) {
          block.insertBefore(details, strip.nextSibling);
        } else {
          block.appendChild(details);
        }
        // Re-run the shuffle since the inline <script> from the static page
        // does not execute on DOMParser clone+append.
        shuffleColumnistsGrid(columnistsNode.querySelector(".columnists-grid"));
      }

      shell.appendChild(block);
    } catch (err) {
      console.warn(`team ${slug} render failed`, err);
      const errDiv = document.createElement("div");
      errDiv.className = "team-block-error";
      errDiv.textContent = `Could not load ${slug}: ${err.message}`;
      shell.appendChild(errDiv);
    }
  }

  // If My Players is positioned after the team sections in the user's order,
  // render it below all team blocks.
  if (myPlayersVisible && !myPlayersFirst) {
    const mp = renderMyPlayersSection(players, playerStats);
    mp.id = "section-my_players";
    shell.appendChild(mp);
  }

  // Always append the quick picker at the bottom so users can add/remove teams
  // without leaving /home during Phase B. Unit 6 replaces this with settings.
  const picker = document.createElement("div");
  picker.className = "team-picker";
  picker.id = "team-picker";
  shell.appendChild(picker);
  mountTeamPicker();
}

async function renderHome() {
  renderLoading();
  try {
    const session = await getSession();
    if (!session) {
      await renderPreview();
      return;
    }
    const [profile, followed] = await Promise.all([getProfile({ force: true }), loadFollowedTeams()]);
    if (!profile) {
      renderError("Could not load profile.");
      return;
    }
    readerName.textContent = profile.display_name || session.user.email;
    followCount.textContent = `${followed.length} team${followed.length === 1 ? "" : "s"}`;
    signoutLink.hidden = false;

    if (followed.length === 0) {
      renderEmpty();
      return;
    }

    await renderMergedView(profile, followed);
  } catch (err) {
    console.error("renderHome failed", err);
    renderError(err.message || "Something went wrong loading your lineup.");
  }
}

signoutLink.addEventListener("click", async (e) => {
  e.preventDefault();
  await signOut();
  window.location.href = "../auth/";
});

onAuthChange((event) => {
  if (event === "SIGNED_OUT") window.location.href = "../auth/";
});

// Cross-tab sync: /settings pings localStorage after any profile change; this
// tab re-renders to pick up new visibility/order/density/theme.
window.addEventListener("storage", (e) => {
  if (e.key === "ml-profile-updated") renderHome();
});
// And refetch when the tab regains focus, in case storage events were missed.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") renderHome();
});

renderHome();
