#!/usr/bin/env python3
"""
deploy.py — archive the currently-live index.html to archive/YYYY-MM-DD.html,
then replace index.html with the freshly-built local index.html.

Env: GITHUB_TOKEN (fine-grained PAT with Contents:RW on this repo).
Run AFTER build.py, from the folder containing the built index.html.
"""
import base64, json, os, sys, urllib.request, urllib.error
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

# 1) read live index.html → content + sha
current = gh("GET", "/index.html")
archive_name = (datetime.now(tz=CT).date() - timedelta(days=1)).isoformat()

# 2) archive it (content is already base64 from GitHub)
try:
    gh("PUT", f"/archive/{archive_name}.html", {
        "message": f"archive {archive_name} briefing",
        "content": current["content"].replace("\n", ""),
    })
    print(f"archived → archive/{archive_name}.html")
except urllib.error.HTTPError as e:
    if e.code == 422:
        print(f"archive/{archive_name}.html already exists; skipping")
    else:
        body = e.read().decode(errors="replace")
        sys.exit(f"archive PUT failed: {e.code} {body}")

# 3) read new local index.html, PUT with current sha
local = Path(__file__).parent / "index.html"
if not local.exists():
    sys.exit(f"error: {local} not found — did build.py run?")
html_bytes = local.read_bytes()
if not html_bytes:
    sys.exit(f"error: {local} is empty")
new_b64 = base64.b64encode(html_bytes).decode()

try:
    resp = gh("PUT", "/index.html", {
        "message": f"daily update {date.today().isoformat()}",
        "content": new_b64,
        "sha": current["sha"],
    })
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")
    sys.exit(f"index.html PUT failed: {e.code} {body}")

print(f"deployed  → {resp['commit']['sha'][:7]} ({resp['content']['size']:,} bytes)")
print(f"live      → https://{OWNER}.github.io/{REPO}/")
