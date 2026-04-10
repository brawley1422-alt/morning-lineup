#!/usr/bin/env python3
"""
merge_columnists.py — one-time migration that folds the approved persona
draft into every team's JSON config.

Reads:   docs/brainstorms/2026-04-10-columnist-personas-draft.json
Writes:  teams/{slug}.json  (adds top-level "columnists" array)

Idempotent by default: skips teams that already have a "columnists" key.
Pass --force to overwrite.

Exits non-zero if any team is missing from the draft or has the wrong
number of personas (must be exactly 3: straight_beat, optimist, pessimist).
"""
import argparse
import json
import sys
from pathlib import Path

ROLES = ("straight_beat", "optimist", "pessimist")
ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "docs" / "brainstorms" / "2026-04-10-columnist-personas-draft.json"
TEAMS_DIR = ROOT / "teams"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing columnists arrays.")
    args = parser.parse_args()

    if not DRAFT.exists():
        sys.exit(f"error: persona draft not found at {DRAFT}")

    draft = json.loads(DRAFT.read_text(encoding="utf-8"))

    team_files = sorted(TEAMS_DIR.glob("*.json"))
    if not team_files:
        sys.exit(f"error: no team configs found in {TEAMS_DIR}")

    written = 0
    skipped = 0
    errors = []

    for tf in team_files:
        slug = tf.stem
        if slug not in draft:
            errors.append(f"{slug}: missing from persona draft")
            continue

        team_personas = draft[slug]
        persona_list = []
        for role_key in ROLES:
            persona = team_personas.get(role_key)
            if not persona:
                errors.append(f"{slug}: missing role {role_key}")
                persona_list = None
                break
            # Strip any extra keys, keep only the canonical shape.
            persona_list.append({
                "name": persona["name"],
                "role": persona["role"],
                "backstory": persona["backstory"],
                "signature_phrase": persona["signature_phrase"],
                "voice_sample": persona["voice_sample"],
            })
        if persona_list is None:
            continue

        cfg = json.loads(tf.read_text(encoding="utf-8"))
        if "columnists" in cfg and not args.force:
            skipped += 1
            continue

        cfg["columnists"] = persona_list
        tf.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written += 1
        print(f"  merged → {slug}")

    print(f"\ndone: {written} written, {skipped} skipped"
          + (f", {len(errors)} errors" if errors else ""))

    if errors:
        for e in errors:
            print(f"  ! {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
