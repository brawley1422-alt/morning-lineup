#!/usr/bin/env python3
"""
deploy.py — archive the currently-live index.html to archive/YYYY-MM-DD.html,
then replace index.html with the freshly-built local index.html.

Env: GITHUB_TOKEN (fine-grained PAT with Contents:RW on this repo).
Run AFTER build.py, from the folder containing the built index.html.
"""
import base64, json, os, sys, urllib.request, urllib.error, urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except (ImportError, KeyError):
    CT = timezone(timedelta(hours=-5))

OWNER = "brawley1422-alt"
REPO  = "morning-lineup"

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("error: GITHUB_TOKEN env var not set")

API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
HDR = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "morning-lineup-deploy/0.1",
}

def gh(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers=HDR)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

ROOT = Path(__file__).parent
today_iso = datetime.now(tz=CT).date().isoformat()
archive_name = (datetime.now(tz=CT).date() - timedelta(days=1)).isoformat()

# 1) deploy root index.html (landing page) if it exists
local_root = ROOT / "index.html"
if local_root.exists() and local_root.read_bytes():
    try:
        current = gh("GET", "/index.html")
        root_sha = current["sha"]
    except urllib.error.HTTPError:
        root_sha = None

    body = {
        "message": f"landing page {today_iso}",
        "content": base64.b64encode(local_root.read_bytes()).decode(),
    }
    if root_sha:
        body["sha"] = root_sha
    try:
        resp = gh("PUT", "/index.html", body)
        print(f"landing   → {resp['commit']['sha'][:7]} ({resp['content']['size']:,} bytes)")
    except urllib.error.HTTPError as e:
        print(f"warning: landing page deploy failed: {e.code}")

# 2) deploy all team pages
teams_dir = ROOT / "teams"
if teams_dir.is_dir():
    for cfg_file in sorted(teams_dir.glob("*.json")):
        slug = cfg_file.stem
        team_html = ROOT / slug / "index.html"
        if not team_html.exists():
            continue

        # get remote SHA if file already exists
        try:
            remote = gh("GET", f"/{slug}/index.html")
            sha = remote["sha"]
            # archive previous version
            archive_b64 = remote["content"].replace("\n", "")
            try:
                gh("PUT", f"/archive/{slug}/{archive_name}.html", {
                    "message": f"archive {slug} {archive_name}",
                    "content": archive_b64,
                })
                print(f"archived  → archive/{slug}/{archive_name}.html")
            except urllib.error.HTTPError as e:
                if e.code == 422:
                    print(f"archive/{slug}/{archive_name}.html already exists; skipping")
                else:
                    print(f"warning: archive {slug} failed: {e.code}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sha = None
            else:
                body = e.read().decode(errors="replace")
                print(f"error: {slug}/index.html GET failed: {e.code} {body}")
                continue
        except urllib.error.URLError as e:
            print(f"error: {slug}/index.html GET failed (network): {e.reason}")
            continue

        body = {
            "message": f"daily update {slug} {today_iso}",
            "content": base64.b64encode(team_html.read_bytes()).decode(),
        }
        if sha:
            body["sha"] = sha
        try:
            resp = gh("PUT", f"/{slug}/index.html", body)
            print(f"deployed  → {slug}/index.html ({resp['content']['size']:,} bytes)")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"error: {slug}/index.html PUT failed: {e.code} {body}")

# 3) push data ledger JSON if it exists
data_file = ROOT / "data" / f"{today_iso}.json"
if data_file.exists():
    data_b64 = base64.b64encode(data_file.read_bytes()).decode()
    data_path = f"/data/{today_iso}.json"
    try:
        gh("PUT", data_path, {
            "message": f"data ledger {today_iso}",
            "content": data_b64,
        })
        print(f"ledger    → data/{today_iso}.json")
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print(f"data/{today_iso}.json already exists; skipping")
        else:
            print(f"warning: data ledger push failed: {e.code}")

# 4) push static asset files (auth UI + config). These rarely change so we
#    GET current SHA first to allow in-place updates without 422 conflicts.
STATIC_ASSETS = [
    "sw.js",
    "config/supabase.js",
    "auth/index.html",
    "auth/reset.html",
    "auth/auth.css",
    "auth/auth.js",
    "auth/reset.js",
    "auth/session.js",
    "home/index.html",
    "home/home.js",
    "home/home.css",
    "settings/index.html",
    "settings/settings.js",
    "settings/settings.css",
]
for rel in STATIC_ASSETS:
    local = ROOT / rel
    if not local.exists():
        continue
    try:
        remote = gh("GET", f"/{rel}")
        sha = remote["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sha = None
        else:
            print(f"warning: {rel} GET failed: {e.code}")
            continue
    body = {
        "message": f"update {rel} {today_iso}",
        "content": base64.b64encode(local.read_bytes()).decode(),
    }
    if sha:
        body["sha"] = sha
    try:
        resp = gh("PUT", f"/{rel}", body)
        size = resp["content"]["size"]
        print(f"asset     → {rel} ({size:,} bytes)")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"warning: {rel} PUT failed: {e.code} {body}")

print(f"live      → https://{OWNER}.github.io/{REPO}/")
