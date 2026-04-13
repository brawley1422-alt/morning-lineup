"""Load the 90 writer personas from teams/*.json.

Returns enriched writer objects with team context for the UI to render.
"""
import json
from pathlib import Path

from pressrow_writer.config_io import REPO_ROOT
from pressrow_writer.util import make_handle, make_initials


TEAMS_DIR = REPO_ROOT / "teams"


def _role_key(role_label: str) -> str:
    label = (role_label or "").lower()
    if "straight" in label:
        return "straight_beat"
    if "optimist" in label:
        return "optimist"
    if "pessimist" in label:
        return "pessimist"
    return "other"


def load_all() -> dict:
    """Load every writer from teams/*.json. Returns dict keyed by handle.

    Each value has: name, handle, initials, team_slug, team_name, team_abbr,
    team_id, colors, role, role_key, backstory, signature_phrase, voice_sample.
    """
    writers = {}
    for cfg_path in sorted(TEAMS_DIR.glob("*.json")):
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        slug = cfg_path.stem
        team_name = cfg.get("name", slug.title())
        team_abbr = cfg.get("abbreviation", slug.upper()[:3])
        team_id = cfg.get("id", 0)
        colors = cfg.get("colors", {})

        for persona in cfg.get("columnists", []):
            name = persona.get("name", "")
            if not name:
                continue
            handle = make_handle(name)
            writers[handle] = {
                "name": name,
                "handle": handle,
                "initials": make_initials(name),
                "team_slug": slug,
                "team_name": team_name,
                "team_abbr": team_abbr,
                "team_id": team_id,
                "colors": colors,
                "role": persona.get("role", ""),
                "role_key": _role_key(persona.get("role", "")),
                "backstory": persona.get("backstory", ""),
                "signature_phrase": persona.get("signature_phrase", ""),
                "voice_sample": persona.get("voice_sample", ""),
            }
    return writers


def load_teams() -> list:
    """Load team metadata only (no writers). For UI left-rail rendering."""
    teams = []
    for cfg_path in sorted(TEAMS_DIR.glob("*.json")):
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        slug = cfg_path.stem
        teams.append({
            "slug": slug,
            "name": cfg.get("name", slug.title()),
            "full_name": cfg.get("full_name", ""),
            "abbreviation": cfg.get("abbreviation", slug.upper()[:3]),
            "team_id": cfg.get("id", 0),
            "division_name": cfg.get("division_name", ""),
            "colors": cfg.get("colors", {}),
        })
    return teams
