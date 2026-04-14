/*
 * player-card.js — Morning Lineup flip-card web component.
 *
 * Wraps a known player name with <player-card pid="691718">Pete Crow-Armstrong</player-card>
 * and opens a Topps-style flip card overlay on click. Data is loaded lazily
 * from ../data/players-cubs.json on first click (cached for the session).
 *
 * Phase 1: Cubs only. See docs/plans/2026-04-11-001-feat-player-cards-cubs-mvp-plan.md
 */
(function () {
  if (customElements.get("player-card")) return;

  const DEFAULT_SLUG =
    (document.body && document.body.dataset && document.body.dataset.team) || "cubs";
  const _cacheBySlug = {};
  const _promiseBySlug = {};

  function loadData(slug) {
    const s = slug || DEFAULT_SLUG;
    if (_cacheBySlug[s]) return Promise.resolve(_cacheBySlug[s]);
    if (_promiseBySlug[s]) return _promiseBySlug[s];
    const url = "../data/players-" + s + ".json";
    _promiseBySlug[s] = fetch(url, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        _cacheBySlug[s] = j || { players: {} };
        return _cacheBySlug[s];
      })
      .catch(() => {
        _cacheBySlug[s] = { players: {} };
        return _cacheBySlug[s];
      });
    return _promiseBySlug[s];
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtDec(v, d) {
    if (v === null || v === undefined || v === "" || v === "-") return "—";
    const n = typeof v === "number" ? v : parseFloat(v);
    if (isNaN(n)) return String(v);
    return n.toFixed(d != null ? d : 3).replace(/^0\./, ".");
  }

  function formatShortDate(iso) {
    if (!iso) return "?";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    } catch (e) { return iso; }
  }

  function formatGameTime(iso) {
    if (!iso) return "first pitch";
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    } catch (e) { return iso; }
  }

  function pick(obj, keys) {
    for (const k of keys) {
      if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== "") return obj[k];
    }
    return null;
  }

  function interpColor(t) {
    // Navy → Cubs red gradient. t in [0,1].
    if (t == null || isNaN(t)) return "#b3a98a";
    const cold = [14, 51, 134];
    const hot = [200, 16, 46];
    const r = Math.round(cold[0] + (hot[0] - cold[0]) * t);
    const g = Math.round(cold[1] + (hot[1] - cold[1]) * t);
    const b = Math.round(cold[2] + (hot[2] - cold[2]) * t);
    return `rgb(${r}, ${g}, ${b})`;
  }

  function injectStylesOnce() {
    if (document.getElementById("player-card-styles")) return;
    const style = document.createElement("style");
    style.id = "player-card-styles";
    style.textContent = STYLES;
    document.head.appendChild(style);
  }

  function renderSparkline(games, isPitcher) {
    const W = 220, H = 36, PAD_X = 4, PAD_Y = 4;
    if (!games || games.length === 0) {
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="pc-spark-svg"><text x="${W/2}" y="${H/2 + 4}" text-anchor="middle" fill="#8a7e60" font-family="serif" font-style="italic" font-size="11">no recent games</text></svg>`;
    }
    const valid = games.filter((g) => g && g.value != null);
    if (valid.length === 0) {
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="pc-spark-svg"><text x="${W/2}" y="${H/2 + 4}" text-anchor="middle" fill="#8a7e60" font-family="serif" font-style="italic" font-size="11">no recent games</text></svg>`;
    }
    // Y-axis: hitters use OPS scale (0..1.5 typical), pitchers use GameScore (0..100)
    const yMin = isPitcher ? 0 : 0;
    const yMax = isPitcher ? 100 : Math.max(1.5, ...valid.map((g) => g.value));
    const yRange = yMax - yMin || 1;
    const innerW = W - PAD_X * 2;
    const innerH = H - PAD_Y * 2;
    // X positions evenly spaced across the actual game count
    const n = games.length;
    const points = [];
    games.forEach((g, i) => {
      if (g && g.value != null) {
        const x = PAD_X + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW);
        const y = PAD_Y + innerH - ((g.value - yMin) / yRange) * innerH;
        points.push({ x, y, val: g.value, date: g.date });
      }
    });
    if (points.length === 0) return "";
    const path = points.map((pt, i) => (i === 0 ? "M" : "L") + pt.x.toFixed(1) + "," + pt.y.toFixed(1)).join(" ");
    // Baseline reference line at the threshold (hot/cold midline)
    const midVal = isPitcher ? 50 : 0.700;
    const midY = PAD_Y + innerH - ((midVal - yMin) / yRange) * innerH;
    // Last point dot — emphasize the most recent game
    const last = points[points.length - 1];
    const dots = points.map((pt) =>
      `<circle cx="${pt.x.toFixed(1)}" cy="${pt.y.toFixed(1)}" r="1.6" fill="#c9a24a" opacity="0.7"/>`
    ).join("");
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="pc-spark-svg">
      <line x1="0" y1="${midY.toFixed(1)}" x2="${W}" y2="${midY.toFixed(1)}" stroke="#8a7e60" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.5"/>
      <path d="${path}" fill="none" stroke="#c8102e" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      ${dots}
      <circle cx="${last.x.toFixed(1)}" cy="${last.y.toFixed(1)}" r="2.6" fill="#c8102e" stroke="#f4ecd8" stroke-width="0.8"/>
    </svg>`;
  }

  const STYLES = `
    player-card {
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .pc-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(10, 8, 6, 0.72);
      backdrop-filter: blur(6px);
      -webkit-backdrop-filter: blur(6px);
      z-index: 9998;
      display: grid;
      place-items: center;
      padding: 2rem 1rem;
      animation: pc-fadein 0.35s ease-out;
    }
    @keyframes pc-fadein {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    .pc-wrap {
      perspective: 1600px;
      width: min(360px, 92vw);
      aspect-ratio: 5 / 7;
      position: relative;
      z-index: 9999;
    }
    .pc-card {
      position: relative;
      width: 100%;
      height: 100%;
      transform-style: preserve-3d;
      transition: transform 0.95s cubic-bezier(0.22, 1, 0.36, 1);
      cursor: pointer;
      animation: pc-pull 0.75s cubic-bezier(0.22, 1, 0.36, 1) backwards;
    }
    .pc-card.flipped { transform: rotateY(180deg); }
    @keyframes pc-pull {
      from { opacity: 0; transform: translateY(60px) rotate(-10deg) scale(0.88); }
      to   { opacity: 1; transform: translateY(0) rotate(-0.5deg) scale(1); }
    }
    .pc-face {
      position: absolute;
      inset: 0;
      -webkit-backface-visibility: hidden;
      backface-visibility: hidden;
      transform: rotateY(0deg) translateZ(0.1px);
      background: #f4ecd8;
      border-radius: 6px;
      overflow: hidden;
      box-shadow:
        0 1px 0 rgba(0,0,0,0.35),
        0 4px 10px rgba(0,0,0,0.2),
        0 24px 48px rgba(0,0,0,0.5),
        inset 0 0 0 1px rgba(0,0,0,0.15);
      font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace;
      color: #1a1a1a;
    }
    .pc-face::after {
      content: "";
      position: absolute;
      inset: 0;
      background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85'/></filter><rect width='140' height='140' filter='url(%23n)' opacity='0.35'/></svg>");
      mix-blend-mode: multiply;
      opacity: 0.4;
      pointer-events: none;
      z-index: 5;
    }
    .pc-front {
      padding: 12px;
      background: linear-gradient(135deg, #f4ecd8 0%, #ead9b4 100%);
    }
    .pc-front-inner {
      position: relative;
      height: 100%;
      border: 2px solid #1a1a1a;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .pc-banner {
      position: absolute;
      top: 14px;
      left: -10px;
      background: #c8102e;
      color: #f4ecd8;
      font-family: "Oswald", "Anton", sans-serif;
      font-size: 0.74rem;
      letter-spacing: 0.14em;
      padding: 0.38rem 1.1rem 0.38rem 0.95rem;
      transform: rotate(-4deg);
      z-index: 4;
      box-shadow: 2px 2px 0 #1a1a1a;
      text-transform: uppercase;
      font-weight: 700;
    }
    .pc-banner::before { content: "★ "; }
    .pc-photo {
      position: relative;
      flex: 1.1;
      background: radial-gradient(ellipse 110% 85% at 50% 35%, #e85a70 0%, #c8102e 45%, #6a0818 100%);
      overflow: hidden;
      border-bottom: 2px solid #1a1a1a;
    }
    .pc-photo::before {
      content: "C";
      position: absolute;
      left: 50%;
      top: 52%;
      transform: translate(-50%, -50%);
      font-family: "Oswald", "Anton", sans-serif;
      font-size: 22rem;
      line-height: 0.78;
      color: rgba(255, 255, 255, 0.09);
      letter-spacing: -0.06em;
      z-index: 1;
      user-select: none;
      font-weight: 700;
    }
    .pc-photo img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 28%;
      filter: grayscale(0.25) contrast(1.08) brightness(1) saturate(1.1);
      z-index: 2;
    }
    .pc-photo::after {
      content: "";
      position: absolute;
      inset: 0;
      background-image: radial-gradient(circle, rgba(0,0,0,0.3) 0.8px, transparent 1.2px);
      background-size: 4px 4px;
      mix-blend-mode: multiply;
      z-index: 3;
      pointer-events: none;
    }
    .pc-jersey {
      position: absolute;
      top: 8px;
      right: 10px;
      font-family: "Oswald", "Anton", sans-serif;
      color: #f4ecd8;
      font-size: 3.4rem;
      line-height: 0.8;
      letter-spacing: -0.04em;
      text-shadow: 3px 3px 0 #1a1a1a;
      z-index: 3;
      font-weight: 700;
    }
    .pc-pos {
      position: absolute;
      bottom: 10px;
      left: 10px;
      background: #0e3386;
      color: #f4ecd8;
      font-family: "Oswald", "Anton", sans-serif;
      letter-spacing: 0.12em;
      font-size: 0.95rem;
      padding: 0.32rem 0.65rem;
      border: 2px solid #f4ecd8;
      box-shadow: 3px 3px 0 #1a1a1a;
      z-index: 3;
      font-weight: 700;
    }
    .pc-info {
      background: #f4ecd8;
      padding: 9px 11px 8px;
      position: relative;
      z-index: 2;
    }
    .pc-team-line {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.58rem;
      letter-spacing: 0.22em;
      color: #c8102e;
      text-transform: uppercase;
      font-weight: 700;
      display: flex;
      justify-content: space-between;
      border-bottom: 1px solid #1a1a1a;
      padding-bottom: 4px;
      margin-bottom: 6px;
    }
    .pc-team-line span:last-child { color: #5a544a; }
    .pc-name {
      font-family: "Oswald", "Anton", sans-serif;
      font-size: 1.55rem;
      line-height: 0.9;
      letter-spacing: 0.01em;
      text-transform: uppercase;
      color: #1a1a1a;
      font-weight: 700;
    }
    .pc-name small {
      display: block;
      font-family: "Playfair Display", serif;
      font-style: italic;
      font-size: 0.75rem;
      letter-spacing: 0;
      text-transform: none;
      color: #5a544a;
      margin-top: 5px;
      font-weight: 400;
    }
    .pc-slash {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      margin-top: 8px;
      border: 2px solid #1a1a1a;
      background: #ead9b4;
    }
    .pc-slash > div {
      padding: 5px 0 4px;
      text-align: center;
      border-right: 1px solid #1a1a1a;
    }
    .pc-slash > div:last-child { border-right: none; }
    .pc-slash label {
      display: block;
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.5rem;
      letter-spacing: 0.15em;
      color: #5a544a;
      text-transform: uppercase;
    }
    .pc-slash strong {
      display: block;
      font-family: "Oswald", sans-serif;
      font-size: 1.15rem;
      color: #1a1a1a;
      letter-spacing: 0.02em;
      margin-top: 1px;
    }
    .pc-temp {
      margin-top: 9px;
      padding-bottom: 4px;
    }
    .pc-temp-label {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.52rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: #1a1a1a;
      margin-bottom: 4px;
    }
    .pc-temp-label strong {
      color: #c8102e;
      font-size: 0.6rem;
    }
    .pc-temp-bar {
      display: grid;
      grid-template-columns: repeat(15, 1fr);
      gap: 2px;
      height: 14px;
    }
    .pc-temp-bar span {
      border: 1px solid #1a1a1a;
    }
    .pc-spark {
      background: rgba(13, 15, 20, 0.04);
      border: 1px solid #1a1a1a;
      padding: 2px 4px;
      height: 38px;
      box-sizing: border-box;
    }
    .pc-spark-svg {
      display: block;
      width: 100%;
      height: 100%;
    }

    /* ── Phase 2: prediction tile + scoreboard + touches ─────────────── */
    .pc-pred {
      background: linear-gradient(180deg, #0d1530, #060a1a);
      border: 1px solid #c9a24a;
      border-radius: 3px;
      padding: 12px 14px 10px;
      margin: 14px 0 10px;
      color: #f4ecd8;
      box-shadow: inset 0 0 0 1px rgba(232,200,120,.18);
    }
    .pc-pred-q {
      font-family: "Playfair Display", Georgia, serif;
      font-style: italic;
      font-size: 0.95rem;
      line-height: 1.2;
      margin-bottom: 10px;
      color: #f4ecd8;
    }
    .pc-pred-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 6px;
    }
    .pc-pred-btn {
      background: transparent;
      border: 1.5px solid #c9a24a;
      color: #f0d57a;
      font-family: "Oswald", sans-serif;
      font-weight: 700;
      font-size: 0.85rem;
      letter-spacing: 0.18em;
      padding: 8px 0;
      cursor: pointer;
      transition: all 0.18s;
      border-radius: 2px;
    }
    .pc-pred-btn:hover {
      background: rgba(232,200,120,.12);
      color: #f4ecd8;
    }
    .pc-pred-btn.active {
      background: #c9a24a;
      color: #060a1a;
    }
    .pc-pred-meta {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.55rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #c9a24a;
      text-align: center;
    }
    .pc-pred-locked .pc-pred-locked-tag {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.6rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: #c9a24a;
      text-align: center;
      padding: 6px 0 2px;
    }
    .pc-pred-resolved.win { border-color: #4ea341; }
    .pc-pred-resolved.loss { border-color: #c8102e; opacity: 0.85; }
    .pc-pred-resolved.push { border-color: #5a5750; }
    .pc-pred-result {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.65rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #f4ecd8;
      text-align: center;
      padding-top: 4px;
    }

    .pc-scoreboard {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      padding: 6px 12px;
      background: rgba(13, 15, 20, 0.04);
      border-left: 2px solid #c9a24a;
      margin-bottom: 12px;
      font-family: "IBM Plex Mono", monospace;
    }
    .pc-sb-label {
      font-size: 0.55rem;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: #5a5750;
    }
    .pc-sb-record {
      font-family: "Playfair Display", Georgia, serif;
      font-style: italic;
      font-size: 1.1rem;
      color: #c8102e;
    }
    .pc-sb-streak {
      font-size: 0.6rem;
      color: #5a5750;
    }
    .pc-sb-empty {
      font-style: italic;
      font-size: 0.7rem;
      color: #5a5750;
      justify-content: center;
      border-left-color: #5a5750;
    }

    .pc-touches {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.55rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #5a5750;
      text-align: center;
      padding: 8px 0 4px;
      border-top: 1px dashed rgba(13,15,20,.15);
      margin-top: 8px;
    }
    .pc-rail {
      background: #1a1a1a;
      color: #f4ecd8;
      padding: 5px 10px;
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.5rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .pc-rail em { color: #c8102e; font-style: normal; }
    .pc-back {
      transform: rotateY(180deg) translateZ(0.1px);
      padding: 12px;
      background: linear-gradient(180deg, #f4ecd8 0%, #ead9b4 100%);
    }
    .pc-back-inner {
      border: 2px solid #1a1a1a;
      height: 100%;
      padding: 11px 12px;
      display: flex;
      flex-direction: column;
      gap: 9px;
    }
    .pc-back-head {
      border-bottom: 3px double #1a1a1a;
      padding-bottom: 7px;
    }
    .pc-back-head .lbl {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.5rem;
      letter-spacing: 0.2em;
      color: #c8102e;
      text-transform: uppercase;
      font-weight: 700;
    }
    .pc-back-head h2 {
      font-family: "Oswald", sans-serif;
      font-size: 1.3rem;
      letter-spacing: 0.01em;
      line-height: 1;
      margin: 2px 0 0 0;
      font-weight: 700;
    }
    .pc-back-head p {
      font-family: "Playfair Display", serif;
      font-style: italic;
      font-size: 0.68rem;
      color: #5a544a;
      margin: 3px 0 0 0;
    }
    .pc-table {
      width: 100%;
      border-collapse: collapse;
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.55rem;
    }
    .pc-table thead th {
      background: #1a1a1a;
      color: #f4ecd8;
      padding: 3px 1px;
      font-weight: 500;
      letter-spacing: 0.05em;
      text-align: center;
    }
    .pc-table tbody td {
      padding: 3px 1px;
      text-align: center;
      border-bottom: 1px dashed rgba(0, 0, 0, 0.28);
    }
    .pc-table tbody tr:last-child td {
      border-bottom: 2px solid #1a1a1a;
      font-weight: 700;
      background: rgba(200, 16, 46, 0.1);
    }
    .pc-adv-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      border-bottom: 1px solid #1a1a1a;
      padding-bottom: 4px;
      margin-bottom: 6px;
    }
    .pc-adv-head h3 {
      font-family: "Oswald", sans-serif;
      font-size: 0.9rem;
      letter-spacing: 0.04em;
      color: #c8102e;
      margin: 0;
      font-weight: 700;
    }
    .pc-adv-head span {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.48rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: #5a544a;
    }
    .pc-adv-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 12px;
    }
    .pc-metric { display: flex; flex-direction: column; gap: 3px; }
    .pc-metric-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
    }
    .pc-metric-label {
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.52rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .pc-metric-value {
      font-family: "Oswald", sans-serif;
      font-size: 0.95rem;
      font-weight: 700;
    }
    .pc-metric-bar {
      height: 5px;
      background: #d6c9a8;
      border: 1px solid #1a1a1a;
      position: relative;
      overflow: hidden;
    }
    .pc-metric-bar i {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      background: #c8102e;
    }
    .pc-footnote {
      margin-top: auto;
      font-family: "Playfair Display", serif;
      font-style: italic;
      font-size: 0.72rem;
      line-height: 1.42;
      color: #1a1a1a;
      border-top: 1px solid #1a1a1a;
      padding-top: 7px;
    }
    .pc-footnote .sig {
      display: block;
      text-align: right;
      font-size: 0.55rem;
      color: #5a544a;
      font-style: normal;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-top: 4px;
      font-family: "IBM Plex Mono", monospace;
    }
    .pc-close {
      position: fixed;
      top: 1.25rem;
      right: 1.25rem;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #f4ecd8;
      color: #1a1a1a;
      border: 2px solid #1a1a1a;
      font-family: "Oswald", sans-serif;
      font-size: 1.2rem;
      font-weight: 700;
      cursor: pointer;
      z-index: 10000;
      box-shadow: 2px 2px 0 #1a1a1a;
    }
    .pc-stub {
      background: #f4ecd8;
      border: 2px solid #1a1a1a;
      padding: 1.5rem 1.75rem;
      max-width: min(340px, 90vw);
      box-shadow: 6px 6px 0 #1a1a1a;
      font-family: "Playfair Display", serif;
    }
    .pc-stub h3 {
      font-family: "Oswald", sans-serif;
      font-size: 1.3rem;
      text-transform: uppercase;
      margin: 0 0 0.5rem 0;
    }
    .pc-stub p {
      font-size: 0.85rem;
      color: #5a544a;
      font-style: italic;
      margin: 0;
    }
  `;

  function renderFront(p, teamName) {
    const name = esc(p.name || "Unknown");
    const parts = name.split(/\s+/);
    const firstLine = parts.slice(0, -1).join(" ");
    const lastLine = parts[parts.length - 1];
    const nameHtml = firstLine
      ? `${firstLine}<br>${lastLine}`
      : lastLine;
    const isPitcher = (p.role === "pitcher");
    const s = p.season || {};
    let slash;
    if (isPitcher) {
      slash = `
        <div><label>ERA</label><strong>${esc(pick(s, ["era"]) || "—")}</strong></div>
        <div><label>W-L</label><strong>${esc(pick(s, ["wins"]) || 0)}-${esc(pick(s, ["losses"]) || 0)}</strong></div>
        <div><label>WHIP</label><strong>${fmtDec(pick(s, ["whip"]), 2)}</strong></div>
      `;
    } else {
      slash = `
        <div><label>AVG</label><strong>${fmtDec(pick(s, ["avg"]))}</strong></div>
        <div><label>OBP</label><strong>${fmtDec(pick(s, ["obp"]))}</strong></div>
        <div><label>SLG</label><strong>${fmtDec(pick(s, ["slg"]))}</strong></div>
      `;
    }
    const last10 = p.last_10_games || [];
    const sparkSvg = renderSparkline(last10, isPitcher);
    const valid = last10.filter((g) => g && g.value != null).map((g) => g.value);
    let label = "—";
    if (valid.length >= 3) {
      const recent = valid.slice(-3);
      const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
      if (isPitcher) {
        label = avg > 60 ? "Hot" : avg < 35 ? "Cold" : "Even";
      } else {
        label = avg > 0.85 ? "Hot" : avg < 0.55 ? "Cold" : "Even";
      }
    }
    const age = p.age ? `${p.age} yrs` : "";
    const handed = [p.bats, p.throws].filter(Boolean).join(" · ");
    const height = p.height || "";
    const bioLine = [age, p.position || "", `#${p.jersey || "?"}`].filter(Boolean).join(" — ");
    const teamLineRight = [handed, height].filter(Boolean).join(" · ");

    return `
      <div class="pc-face pc-front">
        <div class="pc-front-inner">
          <div class="pc-banner">${esc(teamName || "MLB")}</div>
          <div class="pc-photo">
            <img src="${esc(p.headshot_url || "")}" alt="${name}" onerror="this.style.display='none'">
            <div class="pc-jersey">${esc(p.jersey || "")}</div>
            <div class="pc-pos">${esc(p.position || "")}</div>
          </div>
          <div class="pc-info">
            <div class="pc-team-line">
              <span>Season ${esc(new Date().getFullYear())}</span>
              <span>${esc(teamLineRight)}</span>
            </div>
            <div class="pc-name">
              ${nameHtml}
              <small>${esc(bioLine)}</small>
            </div>
            <div class="pc-slash">${slash}</div>
            <div class="pc-temp">
              <div class="pc-temp-label">
                <span>Last 10 Games · ${isPitcher ? "GameScore" : "OPS"}</span>
                <strong>${label}</strong>
              </div>
              <div class="pc-spark">${sparkSvg}</div>
            </div>
          </div>
          <div class="pc-rail">
            <span>№ ${esc(String(p.jersey || "00").padStart(3, "0"))} / 40M</span>
            <em>FLIP →</em>
            <span>ML · ${new Date().getFullYear()}</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderBack(p, teamName) {
    const career = (p.career || []).slice(-4);
    const isPitcher = (p.role === "pitcher");
    let tableHead, rowsHtml;
    if (isPitcher) {
      tableHead = `<tr><th>YR</th><th>W</th><th>L</th><th>ERA</th><th>IP</th><th>K</th><th>BB</th><th>WHIP</th></tr>`;
      rowsHtml = career
        .map((c) => {
          const st = c.stat || {};
          return `<tr>
            <td>${esc(c.year)}</td>
            <td>${esc(st.wins || 0)}</td>
            <td>${esc(st.losses || 0)}</td>
            <td>${esc(st.era || "—")}</td>
            <td>${esc(st.inningsPitched || "—")}</td>
            <td>${esc(st.strikeOuts || 0)}</td>
            <td>${esc(st.baseOnBalls || 0)}</td>
            <td>${esc(st.whip || "—")}</td>
          </tr>`;
        })
        .join("");
    } else {
      tableHead = `<tr><th>YR</th><th>G</th><th>AB</th><th>R</th><th>H</th><th>HR</th><th>RBI</th><th>SB</th><th>AVG</th></tr>`;
      rowsHtml = career
        .map((c) => {
          const st = c.stat || {};
          return `<tr>
            <td>${esc(c.year)}</td>
            <td>${esc(st.gamesPlayed || 0)}</td>
            <td>${esc(st.atBats || 0)}</td>
            <td>${esc(st.runs || 0)}</td>
            <td>${esc(st.hits || 0)}</td>
            <td>${esc(st.homeRuns || 0)}</td>
            <td>${esc(st.rbi || 0)}</td>
            <td>${esc(st.stolenBases || 0)}</td>
            <td>${esc(st.avg || "—")}</td>
          </tr>`;
        })
        .join("");
    }
    if (!rowsHtml) {
      rowsHtml = `<tr><td colspan="9" style="text-align:center;color:#5a544a;font-style:italic;padding:12px">No career data available</td></tr>`;
    }

    const s = p.season || {};
    // Savant advanced stats (populated by build.py fetch_savant_leaderboards)
    const adv = p.advanced || {};
    const advH = adv.hitter || {};
    const advP = adv.pitcher || {};
    const hasSavant = !!(Object.keys(advH).length || Object.keys(advP).length);

    // Map raw Savant values to a 0-100 bar fill. Anchors roughly: 20th to
    // 90th percentile across qualified players. Returns 0 for unknown.
    function savantPct(kind, raw) {
      if (raw == null || raw === "") return 0;
      const num = parseFloat(String(raw).replace(/[^\d.\-]/g, ""));
      if (!isFinite(num)) return 0;
      const clamp = (n) => Math.max(0, Math.min(100, n));
      switch (kind) {
        case "xwoba":  return clamp(((num - 0.270) / 0.130) * 100);
        case "xera":   return clamp(((6.0 - num) / 4.0) * 100);
        case "whiff":  return clamp(((num - 15) / 20) * 100);
        case "brl":    return clamp((num / 20) * 100);
        default:       return 0;
      }
    }

    let metrics;
    if (isPitcher) {
      metrics = [
        { label: "ERA+", val: pick(s, ["eraPlus"]) || "—", pct: 0 },
        { label: "xERA", val: advP.xera || "—",            pct: savantPct("xera", advP.xera) },
        { label: "K/9",  val: fmtDec(pick(s, ["strikeoutsPer9Inn"]), 1), pct: 0 },
        { label: "BB/9", val: fmtDec(pick(s, ["walksPer9Inn"]), 1),      pct: 0 },
        { label: "WHIP", val: fmtDec(pick(s, ["whip"]), 2),              pct: 0 },
        { label: "Whf%", val: advP.whiff_percent ? `${advP.whiff_percent}%` : "—", pct: savantPct("whiff", advP.whiff_percent) },
      ];
    } else {
      metrics = [
        { label: "OPS+",    val: pick(s, ["opsPlus"]) || "—", pct: 0 },
        { label: "xwOBA",   val: advH.xwoba || "—",           pct: savantPct("xwoba", advH.xwoba) },
        { label: "Barrel%", val: advH.brl_percent ? `${advH.brl_percent}%` : "—", pct: savantPct("brl", advH.brl_percent) },
        { label: "HardHit%", val: "—",                         pct: 0 },
        { label: "Sprint",  val: "—",                          pct: 0 },
        { label: "Whf%",    val: advH.whiff_percent ? `${advH.whiff_percent}%` : "—", pct: savantPct("whiff", advH.whiff_percent) },
      ];
    }
    const metricHtml = metrics
      .map((m) => `
        <div class="pc-metric">
          <div class="pc-metric-top">
            <span class="pc-metric-label">${esc(m.label)}</span>
            <span class="pc-metric-value">${esc(m.val)}</span>
          </div>
          <div class="pc-metric-bar"><i style="width:${m.pct}%"></i></div>
        </div>
      `)
      .join("");

    const born = [p.birth_city, p.birth_state || p.birth_country].filter(Boolean).join(", ");
    const subline = `${p.position || ""} · Bats/Throws ${[p.bats, p.throws].filter(Boolean).join("/")}${born ? " · " + born : ""}`;

    // Phase 2: prediction tile + scoreboard + reader touches
    const RS = window.MorningLineupReaderState;
    const pid = p.id;
    const isFollowed = RS && pid && RS.isFollowed(pid);
    let predictionHtml = "";
    let scoreboardHtml = "";
    let touchesHtml = "";

    if (RS && pid) {
      const touches = RS.getTouches(pid);
      if (touches && touches.openCount > 0) {
        const firstSeen = touches.firstSeen ? formatShortDate(touches.firstSeen) : "today";
        const countLabel = touches.openCount === 1 ? "first visit" : `opened ${touches.openCount} times`;
        touchesHtml = `<div class="pc-touches">${countLabel} · first seen ${firstSeen}</div>`;
      }
    }

    if (isFollowed && p.prediction && p.prediction.question_text) {
      const stored = RS.getPrediction(pid);
      const today = new Date().toISOString().slice(0, 10);
      const isToday = stored && stored.date === today;
      const locked = isToday && RS.isPickLocked(pid);
      const resolved = isToday && stored && stored.resolvedAt;

      if (resolved) {
        const resultClass = stored.result === "WIN" ? "win" : stored.result === "LOSS" ? "loss" : "push";
        const resultLabel = stored.result === "WIN" ? "✓ You called it" : stored.result === "LOSS" ? "✗ Missed" : "— Push";
        predictionHtml = `
          <div class="pc-pred pc-pred-resolved ${resultClass}">
            <div class="pc-pred-q">${esc(p.prediction.question_text)}</div>
            <div class="pc-pred-result">
              You picked <strong>${esc(stored.pick)}</strong> · ${resultLabel}
            </div>
          </div>`;
      } else if (locked) {
        const pickedLabel = stored.pick ? `Locked: ${stored.pick}` : "Locked";
        predictionHtml = `
          <div class="pc-pred pc-pred-locked">
            <div class="pc-pred-q">${esc(p.prediction.question_text)}</div>
            <div class="pc-pred-locked-tag">🔒 ${pickedLabel} · resolves tomorrow</div>
          </div>`;
      } else {
        const myPick = isToday && stored ? stored.pick : null;
        const yesActive = myPick === "YES" ? "active" : "";
        const noActive = myPick === "NO" ? "active" : "";
        const lockNote = p.next_game_time ? `locks at ${formatGameTime(p.next_game_time)}` : "locks at first pitch";
        predictionHtml = `
          <div class="pc-pred">
            <div class="pc-pred-q">${esc(p.prediction.question_text)}</div>
            <div class="pc-pred-actions">
              <button type="button" class="pc-pred-btn ${yesActive}" data-pick="YES" data-pid="${esc(pid)}">YES</button>
              <button type="button" class="pc-pred-btn ${noActive}" data-pick="NO" data-pid="${esc(pid)}">NO</button>
            </div>
            <div class="pc-pred-meta">${myPick ? `picked ${myPick} · ` : ""}${lockNote}</div>
          </div>`;
      }

      // Per-player scoreboard
      const sb = RS.getScoreboardForPlayer(pid);
      if (sb && sb.total > 0) {
        scoreboardHtml = `
          <div class="pc-scoreboard">
            <span class="pc-sb-label">Your record</span>
            <strong class="pc-sb-record">${sb.record}</strong>
            <span class="pc-sb-streak">${sb.total} pick${sb.total === 1 ? "" : "s"}</span>
          </div>`;
      } else {
        scoreboardHtml = `<div class="pc-scoreboard pc-sb-empty">No picks yet — be the first to call it</div>`;
      }
    }

    return `
      <div class="pc-face pc-back">
        <div class="pc-back-inner">
          <div class="pc-back-head">
            <div class="lbl">No. ${esc(String(p.jersey || "00").padStart(3, "0"))} — ${esc(teamName || "MLB")}</div>
            <h2>${esc(p.last_name || "")}${p.first_name ? ", " + esc(p.first_name) : ""}</h2>
            <p>${esc(subline)}</p>
          </div>

          ${predictionHtml}
          ${scoreboardHtml}

          <table class="pc-table">
            <thead>${tableHead}</thead>
            <tbody>${rowsHtml}</tbody>
          </table>

          <div class="pc-advanced">
            <div class="pc-adv-head">
              <h3>Advanced · ${new Date().getFullYear()}</h3>
              <span>${hasSavant ? "MLB API · Savant" : "MLB API"}</span>
            </div>
            <div class="pc-adv-grid">${metricHtml}</div>
          </div>

          ${touchesHtml}

          <div class="pc-footnote">
            ${isPitcher ? "Starting pitcher. Statcast expected stats via Baseball Savant." : "Today's starting lineup. Statcast expected stats via Baseball Savant."}
            <span class="sig">— The Morning Lineup</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderStub(name, teamName) {
    return `
      <div class="pc-stub">
        <h3>${esc(name)}</h3>
        <p>${esc(teamName || "MLB")} · Card coming soon</p>
      </div>
    `;
  }

  function openOverlay(pid, displayName, slug) {
    injectStylesOnce();
    const backdrop = document.createElement("div");
    backdrop.className = "pc-backdrop";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");

    const closeBtn = document.createElement("button");
    closeBtn.className = "pc-close";
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "Close player card");
    closeBtn.textContent = "×";
    backdrop.appendChild(closeBtn);

    const wrap = document.createElement("div");
    wrap.className = "pc-wrap";
    backdrop.appendChild(wrap);

    function close() {
      document.removeEventListener("keydown", onKey);
      backdrop.remove();
    }
    function onKey(e) {
      if (e.key === "Escape") close();
      if (e.key.toLowerCase() === "f") {
        const card = wrap.querySelector(".pc-card");
        if (card) card.classList.toggle("flipped");
      }
    }
    document.addEventListener("keydown", onKey);
    closeBtn.addEventListener("click", close);
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });

    document.body.appendChild(backdrop);

    loadData(slug).then((data) => {
      const teamName = (data && data.team_full_name) || "MLB";
      const rec = data.players ? data.players[String(pid)] : null;
      if (!rec) {
        wrap.innerHTML = renderStub(displayName || pid, teamName);
        return;
      }
      const card = document.createElement("div");
      card.className = "pc-card";
      card.innerHTML = renderFront(rec, teamName) + renderBack(rec, teamName);
      wrap.appendChild(card);
      wireCardInteractions(card, rec, teamName);
      if (window.MorningLineupReaderState && rec.id) {
        try { window.MorningLineupReaderState.touch(rec.id); } catch (e) {}
      }
    });
  }

  // Wire the click-to-flip behavior plus prediction-button taps that should
  // not bubble up to the flip handler. Re-rendering the back after a pick is
  // simpler than diffing — the back's HTML is small.
  function wireCardInteractions(card, rec, teamName) {
    card.addEventListener("click", function (e) {
      // Don't flip if a prediction button was clicked
      if (e.target && e.target.closest && e.target.closest(".pc-pred-btn")) {
        return;
      }
      e.stopPropagation();
      card.classList.toggle("flipped");
    });

    // Delegate prediction button taps
    card.addEventListener("click", function (e) {
      if (!e.target || !e.target.closest) return;
      const btn = e.target.closest(".pc-pred-btn");
      if (!btn) return;
      e.stopPropagation();
      const RS = window.MorningLineupReaderState;
      if (!RS) return;
      const pick = btn.getAttribute("data-pick");
      const pid = btn.getAttribute("data-pid");
      if (!pid || !pick || !rec.prediction) return;
      const ok = RS.makePick(pid, pick, {
        question_text: rec.prediction.question_text,
        resolution_rule: rec.prediction.resolution_rule,
        role_tag: rec.prediction.role_tag,
        context_tag: rec.prediction.context_tag,
        gameTime: rec.next_game_time,
      });
      if (!ok) return;
      // Re-render only the back face
      const backFace = card.querySelector(".pc-back");
      if (backFace) {
        const newBack = renderBack(rec, teamName);
        const tmp = document.createElement("div");
        tmp.innerHTML = newBack;
        const newFace = tmp.firstElementChild;
        if (newFace) backFace.replaceWith(newFace);
      }
    });
  }

  class PlayerCard extends HTMLElement {
    connectedCallback() {
      if (this._wired) return;
      this._wired = true;
      this.style.display = "inline";
      this.addEventListener("click", this._onClick.bind(this));
      this.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._onClick(e);
        }
      });
      this.setAttribute("role", "button");
      this.setAttribute("tabindex", "0");
    }
    _onClick(e) {
      e.stopPropagation();
      const pid = this.getAttribute("pid");
      const display = this.textContent.trim();
      const slug = this.getAttribute("team") || undefined;
      if (!pid) return;
      openOverlay(pid, display, slug);
    }
  }

  customElements.define("player-card", PlayerCard);

  // Expose render API for inline use (e.g. binder/grid layouts that want
  // a real card embedded in the page rather than the click-to-open modal).
  window.MorningLineupPC = {
    loadData: loadData,
    renderFront: renderFront,
    renderBack: renderBack,
    renderStub: renderStub,
    injectStyles: injectStylesOnce,
    seedCache: function (slug, data) {
      _cacheBySlug[slug] = data;
    },
    mountInline: function (container, pid, slug) {
      injectStylesOnce();
      return loadData(slug).then(function (data) {
        var teamName = (data && data.team_full_name) || "MLB";
        var rec = data.players ? data.players[String(pid)] : null;
        container.innerHTML = "";
        var wrap = document.createElement("div");
        wrap.className = "pc-wrap";
        var card = document.createElement("div");
        card.className = "pc-card";
        if (rec) {
          card.innerHTML = renderFront(rec, teamName) + renderBack(rec, teamName);
          wireCardInteractions(card, rec, teamName);
          if (window.MorningLineupReaderState && rec.id) {
            try { window.MorningLineupReaderState.touch(rec.id); } catch (e) {}
          }
        } else {
          card.innerHTML = renderStub(pid, teamName);
          card.addEventListener("click", function (e) {
            e.stopPropagation();
            card.classList.toggle("flipped");
          });
        }
        wrap.appendChild(card);
        container.appendChild(wrap);
        return card;
      });
    },
  };

  // Deep link: #p/PID auto-opens that player's card on load.
  function openFromHash() {
    const m = /^#p\/(\d+)$/.exec(location.hash || "");
    if (!m) return;
    const pid = m[1];
    const match = document.querySelector('player-card[pid="' + pid + '"]');
    const name = match ? match.textContent.trim() : pid;
    const slug = match ? (match.getAttribute("team") || undefined) : undefined;
    openOverlay(pid, name, slug);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", openFromHash);
  } else {
    openFromHash();
  }
  window.addEventListener("hashchange", openFromHash);
})();
