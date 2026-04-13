"""Atomic JSON file I/O for writing to pressrow/config/*.json.

Uses temp-file-then-rename for atomic writes — if anything crashes mid-write,
the original file is untouched.
"""
import json
import os
from pathlib import Path


# Resolve repo root relative to this file.
# pressrow_writer/config_io.py → repo root is one level up.
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "pressrow" / "config"
STATE_DIR = REPO_ROOT / "pressrow_writer" / "state"


def ensure_dirs():
    """Create config and state directories if they don't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default=None):
    """Read a JSON file, returning `default` if missing or malformed."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def atomic_write(path: Path, data) -> None:
    """Write JSON to `path` atomically. Uses temp-file-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp_path, path)


# ─── Convenience loaders for each config file ──────────────────────────────


def obsessions_path():
    return CONFIG_DIR / "obsessions.json"


def shadow_personas_path():
    return CONFIG_DIR / "shadow_personas.json"


def recurring_fans_path():
    return CONFIG_DIR / "recurring_fans.json"


def relationships_path():
    return CONFIG_DIR / "relationships.json"


def cast_path():
    return CONFIG_DIR / "cast.json"


def batch_obsessions_path():
    return STATE_DIR / "batch_obsessions.json"


def load_obsessions():
    return read_json(obsessions_path(), default={})


def load_shadow_personas():
    return read_json(shadow_personas_path(), default={})


def load_recurring_fans():
    return read_json(recurring_fans_path(), default=[])


def load_relationships():
    return read_json(relationships_path(), default={"feuds": []})


def load_cast():
    return read_json(cast_path(), default={})


def load_batch_obsessions():
    return read_json(batch_obsessions_path(), default=[])
