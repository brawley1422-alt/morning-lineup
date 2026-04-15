#!/usr/bin/env python3
"""One-shot: generate 30 per-team OG preview cards + a landing fallback.

Output: icons/og-{slug}.png (1200x630), one per team, plus icons/og-default.png.
Rendering: headless Chromium with an HTML template. Team colors + Playfair
masthead + a newspaper dateline strip. No logos; typography carries the
whole composition.

Run manually when:
  - A new team config is added
  - Colors or branding change
  - The template needs a visual refresh

Output is static and committed to the repo — the morning cron does NOT call
this. Runtime cost is ~30 seconds for all 30 cards.
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEAMS = ROOT / "teams"
OUT = ROOT / "icons"
CHROME = Path.home() / ".cache/ms-playwright/chromium-1217/chrome-linux64/chrome"

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Oswald:wght@400;600;700&family=Playfair+Display:ital,wght@0,900;1,900&display=swap" rel="stylesheet">
<style>
@page { size: 1200px 630px; margin: 0; }
html, body { margin: 0; padding: 0; width: 1200px; height: 630px; overflow: hidden; }
body {
  background: linear-gradient(135deg, __PRIMARY__ 0%, __PRIMARY_HI__ 60%, #0d0f14 140%);
  color: #ece4d0;
  font-family: "Playfair Display", Georgia, serif;
  position: relative;
  -webkit-font-smoothing: antialiased;
}
/* paper noise overlay */
body::before {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
  opacity: .08; mix-blend-mode: overlay;
}
/* red accent bar top */
.accent-bar {
  position: absolute; top: 0; left: 0; right: 0; height: 10px;
  background: linear-gradient(90deg, transparent 0%, __ACCENT__ 20%, __ACCENT_HI__ 50%, __ACCENT__ 80%, transparent 100%);
}
.accent-bar-bottom {
  position: absolute; bottom: 0; left: 0; right: 0; height: 6px;
  background: linear-gradient(90deg, transparent 0%, __ACCENT__ 30%, __ACCENT_HI__ 50%, __ACCENT__ 70%, transparent 100%);
}
.frame {
  position: relative; z-index: 1;
  padding: 52px 64px;
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.dateline {
  font-family: "IBM Plex Mono", monospace;
  font-size: 14px;
  letter-spacing: .26em;
  text-transform: uppercase;
  color: #c9bfa6;
  border-top: 2px double #ece4d0;
  border-bottom: 1px solid #ece4d0;
  padding: 10px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.dateline .vol { color: #c9a24a; }
.hero h1 {
  font-size: 152px;
  font-style: italic;
  font-weight: 900;
  line-height: .88;
  letter-spacing: -.015em;
  margin: 0 0 12px;
  color: #ece4d0;
  text-shadow: 0 3px 0 rgba(0,0,0,.35);
}
.hero h1 .the {
  display: block;
  font-size: 36px;
  font-style: normal;
  font-weight: 600;
  letter-spacing: .42em;
  color: #c9a24a;
  margin-bottom: 8px;
  text-transform: uppercase;
  font-family: "Oswald", sans-serif;
}
.subtitle {
  font-family: "Oswald", sans-serif;
  font-size: 26px;
  text-transform: uppercase;
  letter-spacing: .18em;
  color: #c9bfa6;
  font-weight: 500;
  margin-top: 12px;
}
.subtitle .sep { color: __ACCENT_HI__; margin: 0 14px; }
.footline {
  font-family: "IBM Plex Mono", monospace;
  font-size: 13px;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: #8b836d;
  border-top: 1px solid rgba(236,228,208,.3);
  padding-top: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.footline .brand { color: #c9a24a; }
</style></head><body>
<div class="accent-bar"></div>
<div class="frame">
  <div class="dateline">
    <span>The Morning Lineup</span>
    <span class="vol">Vol. III &middot; Daily Edition</span>
    <span>__ABBR__</span>
  </div>
  <div class="hero">
    <h1><span class="the">The</span>__NAME__</h1>
    <div class="subtitle">Last Night<span class="sep">&middot;</span>Today<span class="sep">&middot;</span>Every Angle</div>
  </div>
  <div class="footline">
    <span>morning-lineup &middot; <span class="brand">daily briefing</span></span>
    <span>__FULL_NAME__</span>
  </div>
</div>
<div class="accent-bar-bottom"></div>
</body></html>
"""


def render_card(template_html: str, out_path: Path):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(template_html)
        tmp = Path(f.name)
    try:
        subprocess.run(
            [
                str(CHROME),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--window-size=1200,630",
                f"--screenshot={out_path}",
                "--virtual-time-budget=4000",
                f"file://{tmp}",
            ],
            check=True,
            capture_output=True,
        )
    finally:
        tmp.unlink(missing_ok=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Per-team cards
    team_files = sorted(TEAMS.glob("*.json"))
    for tf in team_files:
        slug = tf.stem
        cfg = json.loads(tf.read_text())
        colors = cfg["colors"]
        html = (
            TEMPLATE
            .replace("__PRIMARY__", colors["primary"])
            .replace("__PRIMARY_HI__", colors["primary_hi"])
            .replace("__ACCENT__", colors["accent"])
            .replace("__ACCENT_HI__", colors["accent_hi"])
            .replace("__NAME__", cfg["name"])
            .replace("__FULL_NAME__", cfg["full_name"])
            .replace("__ABBR__", cfg["abbreviation"])
        )
        out = OUT / f"og-{slug}.png"
        render_card(html, out)
        print(f"  wrote {out.name}")

    # Default (landing) card — team-agnostic
    default_html = (
        TEMPLATE
        .replace("__PRIMARY__", "#0E3386")
        .replace("__PRIMARY_HI__", "#2a56c4")
        .replace("__ACCENT__", "#c9a24a")
        .replace("__ACCENT_HI__", "#e6bf62")
        .replace("__NAME__", "Morning Lineup")
        .replace("__FULL_NAME__", "All 30 Teams · Daily")
        .replace("__ABBR__", "MLB")
    )
    # Landing uses slightly different hero — but we re-use the same template.
    render_card(default_html, OUT / "og-default.png")
    print("  wrote og-default.png")

    print(f"\n{len(team_files) + 1} cards generated")


if __name__ == "__main__":
    main()
