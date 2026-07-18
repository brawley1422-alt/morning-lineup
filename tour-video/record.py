#!/usr/bin/env python3
"""Morning Lineup tour — newspaper-style walkthrough of the landing page +
a team edition (Cubs). One webm segment per beat; segments.json for assemble.py.

Adapted from the Card Radar tour kit. Morning Lineup twist: the site has 21
width media queries, so before applying the zoom-2 phone-fake we rewrite every
media rule's px breakpoints x2 via CSSOM — the 780px viewport then evaluates
queries exactly like a 390px phone would.
"""
import json
import sys
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
BASE = "http://localhost:8807"
LANDING = BASE + "/"
CUBS = BASE + "/cubs/"
VP = {"width": 780, "height": 1688}
REC = {"dir": str(HERE / "raw"), "size": {"width": 780, "height": 1688}}

# Fake Supabase session: auth-bounce.js only checks access_token + expires_at,
# and every real Supabase call fails closed (401 -> graceful fallbacks).
FAKE_SESSION = json.dumps({
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0b3VyIiwiZXhwIjo5OTk5OTk5OTk5fQ.tour",
    "token_type": "bearer", "expires_in": 3600, "expires_at": 9999999999,
    "refresh_token": "tour",
    "user": {"id": "00000000-0000-4000-8000-00000000f00d",
             "aud": "authenticated", "role": "authenticated",
             "email": "jb@morninglineup.app", "app_metadata": {"provider": "email"},
             "user_metadata": {}, "created_at": "2026-01-01T00:00:00Z"},
})

INIT_JS = f"""
localStorage.setItem("ml-auth", {json.dumps(FAKE_SESSION)});
localStorage.setItem("ml_aid", "tour-2026");
localStorage.setItem("ml_onboarded", "1");
localStorage.setItem("ml_team", "cubs");
localStorage.setItem("ml_visits", "40");
window.__heroTeamSlug = "cubs";
"""

# Two rewrites so the zoom-2 phone-fake renders like a real 390px phone:
# 1. double every px breakpoint (media queries evaluate against the 780 viewport)
# 2. pin vw-based font-sizes to their 390px-phone value (vw reads 780 here,
#    which would double again under zoom — clamp() midpoints blow up)
MEDIA_FIX_JS = """
() => {
  const fixRules = (rules) => {
    for (const r of rules) {
      if (r.media) {
        r.media.mediaText = r.media.mediaText.replace(
          /(\\d+(?:\\.\\d+)?)px/g, (m, n) => (parseFloat(n) * 2) + 'px');
      }
      if (r.style && r.style.fontSize && r.style.fontSize.includes('vw')) {
        r.style.fontSize = r.style.fontSize.replace(
          /(\\d+(?:\\.\\d+)?)vw/g, (m, n) => (parseFloat(n) * 3.9) + 'px');
      }
      if (r.cssRules) fixRules(r.cssRules);
    }
  };
  for (const ss of document.styleSheets) {
    let rules; try { rules = ss.cssRules } catch (e) { continue }
    if (rules) fixRules(rules);
  }
}
"""

TOUR_CSS = """
#tourbub{position:fixed;top:64px;left:50%;transform:translateX(-50%);transform-origin:50% 0;
 z-index:99999;pointer-events:none;background:#c9a24a;color:#0d0f14;border-radius:3px;
 padding:15px 20px;font:600 21px/1.35 'Oswald',sans-serif;letter-spacing:.02em;
 width:max-content;max-width:330px;text-align:center;
 box-shadow:0 12px 40px rgba(0,0,0,.65);opacity:0}
#tourbub:after{content:'';position:absolute;bottom:-12px;left:50%;margin-left:-12px;
 border:12px solid transparent;border-top-color:#c9a24a;border-bottom:0}
#tourbub.bot{top:auto;bottom:120px;transform-origin:50% 100%}
#tourbub.bot:after{bottom:auto;top:-12px;border-top:0;border-bottom:12px solid #c9a24a}
#tourbub.pop{animation:bubpop .42s cubic-bezier(.2,1.4,.4,1) forwards}
@keyframes bubpop{0%{opacity:0;transform:translateX(-50%) scale(.55)}
 70%{opacity:1;transform:translateX(-50%) scale(1.07)}
 100%{opacity:1;transform:translateX(-50%) scale(1)}}
#tourcard{position:fixed;top:0;left:0;width:390px;height:844px;z-index:100000;background:#0d0f14;display:flex;
 flex-direction:column;align-items:center;justify-content:center;gap:12px;
 opacity:0;transition:opacity .5s}
#tourcard.on{opacity:1}
#tourcard .rule{width:240px;border-top:1px solid #c9a24a;position:relative;height:5px}
#tourcard .rule:after{content:'';position:absolute;left:0;right:0;top:3px;
 border-top:1px solid rgba(201,162,74,.45)}
#tourcard .k{font-family:'Oswald',sans-serif;font-size:12px;color:#c9a24a;
 letter-spacing:.34em;text-transform:uppercase}
#tourcard .t{font-family:'Playfair Display',serif;font-weight:900;font-size:38px;
 color:#ece4d0;text-align:center;line-height:1.15;padding:0 20px}
#tourcard .t em{font-style:italic}
#tourcard .s{font-family:'Oswald',sans-serif;font-size:12px;color:#8f8875;
 letter-spacing:.26em;text-transform:uppercase;text-align:center;line-height:2.1;
 max-width:320px}
"""

PUNCH_JS = """
() => {
  const w = document.createElement('div'); w.id = 'zoomwrap';
  while (document.body.firstChild) w.appendChild(document.body.firstChild);
  document.body.appendChild(w);
  const Z = parseFloat(document.documentElement.style.zoom || '1');
  const LW = 780 / Z, LH = 1688 / Z;
  window.__f = () => {
    const p = document.createElement('div');
    p.style.cssText = 'position:absolute;left:0;top:0;width:100px;height:100px;visibility:hidden';
    document.getElementById('zoomwrap').appendChild(p);
    const f = p.getBoundingClientRect().width / 100;
    p.remove(); return f;
  };
  window.__zs = {tx: 0, ty: 0, s: 1};
  window.__punch = (sel, s, ms = 900) => {
    const z = document.getElementById('zoomwrap');
    z.style.transition = `transform ${ms}ms cubic-bezier(.4,0,.2,1)`;
    z.style.transformOrigin = '0 0';
    if (!sel) { window.__zs = {tx: 0, ty: 0, s: 1}; z.style.transform = 'none'; return; }
    const el = document.querySelector(sel); if (!el) return;
    const f = window.__f(), r = el.getBoundingClientRect(), st = window.__zs;
    const cx = (r.left + r.width / 2) / f, cy = (r.top + r.height / 2) / f;
    const bx = (cx - st.tx) / st.s, by = (cy - st.ty) / st.s;
    let tx = LW / 2 - bx * s, ty = LH / 2 - by * s;
    tx = Math.min(0, Math.max(LW * (1 - s), tx));
    ty = Math.min(0, Math.max(LH * (1 - s), ty));
    window.__zs = {tx, ty, s};
    // tx/ty are viewport-space (reference-kit math), but the wrapper's
    // transform-origin is the DOCUMENT top — on a long page punched at
    // scroll depth S, that misses by S*(s-1). Fold the scroll offset in
    // when applying; keep __zs viewport-space so chained punches still work.
    const dx = tx + (window.scrollX / f) * (1 - s);
    const dy = ty + (window.scrollY / f) * (1 - s);
    z.style.transform = `translate(${dx}px, ${dy}px) scale(${s})`;
  };
}
"""


def prep(page):
    page.evaluate(MEDIA_FIX_JS)
    page.evaluate("() => document.documentElement.style.zoom = 2")
    page.wait_for_timeout(150)
    page.add_style_tag(content=TOUR_CSS)
    page.evaluate(PUNCH_JS)   # wrap app first, THEN add overlays outside the wrap
    page.evaluate("() => { const b = document.createElement('div'); b.id = 'tourbub';"
                  " document.body.appendChild(b); }")


def say(page, text, pos="top", hold=0):
    page.evaluate("""([t, pos]) => { const b = document.getElementById('tourbub');
      b.classList.remove('pop'); void b.offsetWidth;
      b.classList.toggle('bot', pos === 'bot');
      b.textContent = t; b.classList.add('pop'); }""", [text, pos])
    if hold:
        page.wait_for_timeout(hold)


def hide_bubble(page):
    page.evaluate("() => document.getElementById('tourbub').classList.remove('pop')")


def punch(page, sel, scale=1.6, ms=900, settle=True):
    page.evaluate("([sel, s, ms]) => window.__punch(sel, s, ms)", [sel, scale, ms])
    if settle:
        page.wait_for_timeout(ms + 150)


def fullcard(page, kicker, title_html, sub):
    page.evaluate("""([k, t, s]) => {
      const d = document.createElement('div'); d.id = 'tourcard';
      d.innerHTML = `<div class="rule"></div><div class="k">${k}</div>
        <div class="t">${t}</div><div class="s">${s}</div><div class="rule"></div>`;
      document.body.appendChild(d); requestAnimationFrame(() => d.classList.add('on'));
    }""", [kicker, title_html, sub])


def scroll_into(page, sel, block="start"):
    """Instant scroll during pre — invisible, happens before the trim mark.
    Manual math: scrollIntoView(block:'center') miscenters under CSS zoom.
    Measured: rects, scrollY, and innerHeight all share the same visual px
    space here, so scroll explicitly with no unit conversion."""
    page.evaluate("""([sel, block]) => {
      const r = document.querySelector(sel).getBoundingClientRect();
      const y = window.scrollY + r.top;
      const target = block === 'center'
        ? y + r.height / 2 - window.innerHeight / 2
        : y - 16;
      window.scrollTo({top: Math.max(0, target), behavior: 'instant'});
    }""", [sel, block])
    page.wait_for_timeout(250)


def smooth_by(page, dy, ms=1100):
    page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", dy)
    page.wait_for_timeout(ms)


def open_section(page, sec_id):
    page.evaluate("id => document.getElementById(id).setAttribute('open','')", sec_id)


def freeze_live(page):
    """Stop live.js from shifting layout mid-beat. Cloning alone is not
    enough (measured: the banner still grew 621->962px during a beat — the
    section refresher re-renders by id), so also pin each mutable region's
    height and hide overflow: whatever re-renders inside, the outer box —
    and everything below it — cannot move."""
    page.evaluate("""() => {
      for (const id of ['live-game', 'scout', 'matchup']) {
        const el = document.getElementById(id);
        if (!el) continue;
        const clone = el.cloneNode(true);
        clone.style.height = el.offsetHeight + 'px';
        clone.style.overflow = 'hidden';
        el.replaceWith(clone);
      }
    }""")


def fix_greet(page):
    page.evaluate("""() => {
      const r = document.getElementById('greet-reader');
      if (r) r.textContent = 'JB.';
      const k = document.getElementById('kick-reader');
      if (k) k.textContent = 'JB';
    }""")


# ---- beats ----

def act_title(page):
    fullcard(page, "Est. 2024 · All 30 Clubs",
             "The Morning <em>Lineup</em>",
             "A daily paper<br>for your team")


def pre_landing(page):
    fix_greet(page)
    scroll_into(page, "#greet")


def act_landing(page):
    say(page, "Every team gets its own daily paper", "bot", 1900)
    say(page, "Standings and scores, live on page one", "bot")
    smooth_by(page, 520, 1400)
    page.wait_for_timeout(600)


def pre_pick(page):
    fix_greet(page)
    scroll_into(page, "#greet")


def act_pick(page):
    say(page, "Your team stays pinned up top", "bot")
    punch(page, "#your-team", 1.5, 900)
    page.wait_for_timeout(1100)
    say(page, "Tap in for today's edition", "bot", 900)
    punch(page, None, 1, 600)
    page.evaluate("() => document.getElementById('yt-card').click()")
    page.wait_for_timeout(150)


def pre_edition(page):
    freeze_live(page)


def act_edition(page):
    say(page, "The Cubs edition — printed overnight", "bot", 2000)
    say(page, "Vol. 3, No. 198 — new every single day", "bot")


def pre_box(page):
    freeze_live(page)
    scroll_into(page, ".game-result", "center")


def act_box(page):
    say(page, "The last game, boxed like the old papers", "bot", 1200)
    punch(page, ".linescore", 1.55, 900)
    page.wait_for_timeout(1600)
    punch(page, None, 1, 700)


def pre_stars(page):
    freeze_live(page)
    scroll_into(page, ".three-stars", "center")


def act_stars(page):
    say(page, "Three stars of the night, every night", "bot", 2000)
    say(page, "With the numbers that earned it", "bot")


def pre_scorecard(page):
    freeze_live(page)
    scroll_into(page, ".scorecard-expand", "center")


def act_scorecard(page):
    say(page, "Every game hides a full scorecard", "top", 700)
    page.click(".scorecard-expand summary")
    page.wait_for_timeout(1800)
    hide_bubble(page)
    page.evaluate("""() => document.querySelector('.scorecard-frame')
      .scrollIntoView({behavior: 'smooth', block: 'start'})""")
    page.wait_for_timeout(1100)
    say(page, "Every at-bat, inked", "bot")


def pre_scout(page):
    freeze_live(page)
    scroll_into(page, "#scout .pitch-card", "center")


def act_scout(page):
    say(page, "Tonight's matchup, scouted for you", "bot", 1200)
    punch(page, "#scout .pitch-card", 1.5, 900)
    page.wait_for_timeout(1500)
    punch(page, None, 1, 700)


def pre_farm(page):
    freeze_live(page)
    scroll_into(page, "#farm")


def act_farm(page):
    say(page, "Sections fold open like a real paper", "bot", 900)
    page.click("#farm summary")
    page.wait_for_timeout(1100)
    say(page, "The farm system, tracked nightly", "bot")
    smooth_by(page, 380, 1200)


def pre_slate(page):
    freeze_live(page)
    scroll_into(page, "#today")


def act_slate(page):
    say(page, "Tonight's full slate — every ballpark", "top", 1900)
    say(page, "Scores tick live while you read", "top")
    smooth_by(page, 420, 1300)


def pre_league(page):
    freeze_live(page)
    open_section(page, "league")
    page.wait_for_timeout(300)
    scroll_into(page, "#league")


def act_league(page):
    say(page, "Around the league in one scroll", "top", 1600)
    smooth_by(page, 560, 1500)


def act_outro(page):
    fullcard(page, "On the porch by 7 AM",
             "The Morning <em>Lineup</em>",
             "All 30 teams · every morning<br>Add it to your home screen")


# name, url, ready-selector, duration, pre, act
BEATS = [
    ("title",     LANDING, "#greet",                 2.6, None,          act_title),
    ("landing",   LANDING, "#your-team:not([hidden])", 5.2, pre_landing, act_landing),
    ("pick",      LANDING, "#your-team:not([hidden])", 4.6, pre_pick,    act_pick),
    ("edition",   CUBS,    "#team .linescore",       5.0, pre_edition,   act_edition),
    ("box",       CUBS,    "#team .linescore",       5.4, pre_box,       act_box),
    ("stars",     CUBS,    ".three-stars",           4.6, pre_stars,     act_stars),
    ("scorecard", CUBS,    ".scorecard-expand",      6.2, pre_scorecard, act_scorecard),
    ("scout",     CUBS,    "#scout .pitch-card",     5.2, pre_scout,     act_scout),
    ("farm",      CUBS,    "#farm",                  5.0, pre_farm,      act_farm),
    ("slate",     CUBS,    "#today",                 5.0, pre_slate,     act_slate),
    ("league",    CUBS,    "#league",                4.6, pre_league,    act_league),
    ("outro",     CUBS,    "#team .linescore",       3.6, None,          act_outro),
]


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    (HERE / "raw").mkdir(exist_ok=True)
    manifest = json.loads((HERE / "segments.json").read_text()) if only and (HERE / "segments.json").exists() else []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, url, ready, dur, pre, act in BEATS:
            if only and name != only:
                continue
            ctx = browser.new_context(
                viewport=VP, device_scale_factor=1,
                record_video_dir=REC["dir"], record_video_size=REC["size"])
            ctx.add_init_script(INIT_JS)
            page = ctx.new_page()
            t0 = perf_counter()
            page.goto(url)
            page.wait_for_selector(ready, timeout=20000)
            # settle: live.js banner render shifts layout on team pages
            page.wait_for_timeout(2200 if url == CUBS else 900)
            prep(page)
            if pre:
                pre(page)
            page.wait_for_timeout(300)
            trim = perf_counter() - t0
            tb = perf_counter()
            act(page)
            spent = perf_counter() - tb
            d = max(dur, spent + 0.6)     # never cut an action short
            left = d - spent
            if left > 0:
                page.wait_for_timeout(left * 1000)
            video = page.video
            ctx.close()
            Path(video.path()).rename(HERE / "raw" / f"{name}.webm")
            entry = {"name": name, "file": str(HERE / "raw" / f"{name}.webm"),
                     "trim": round(trim, 2), "dur": round(d, 2)}
            manifest = [m for m in manifest if m["name"] != name] + [entry]
            print(f"seg {name}: trim {trim:.2f}s dur {d:.2f}s", flush=True)
        browser.close()
    order = [b[0] for b in BEATS]
    manifest.sort(key=lambda m: order.index(m["name"]))
    (HERE / "segments.json").write_text(json.dumps(manifest, indent=1))
    print("manifest written", flush=True)


if __name__ == "__main__":
    sys.exit(main())
