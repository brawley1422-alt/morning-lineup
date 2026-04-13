"""Batch obsession generator for Task 1 — pre-generates ~9 candidate
obsessions per writer (810 total) via Sonnet (falling back to Ollama),
writes them to pressrow_writer/state/batch_obsessions.json for Swipe
mode to consume.

Sequential to keep things simple and rate-limit friendly. Individual
writer failures don't halt the run. Takes ~15-25 minutes for all 90
writers against Sonnet, longer against Ollama.
"""
import json
import sys
import time

from pressrow_writer import config_io, llm, writers
from pressrow_writer.prompts.batch_obsessions import SYSTEM, build as build_prompt
from pressrow_writer.util import extract_json


def main(argv=None):
    argv = argv or sys.argv[1:]
    # Simple flags: --limit N to only generate for the first N writers (testing)
    limit = None
    prefer = "anthropic"
    for i, a in enumerate(argv):
        if a == "--limit" and i + 1 < len(argv):
            try:
                limit = int(argv[i + 1])
            except ValueError:
                pass
        elif a == "--ollama":
            prefer = "ollama"

    config_io.ensure_dirs()
    all_writers = writers.load_all()
    handles = sorted(all_writers.keys())
    if limit:
        handles = handles[:limit]

    total = len(handles)
    print(f"[batch] generating candidates for {total} writers (prefer={prefer})")
    print(f"[batch] writing to: {config_io.batch_obsessions_path()}")
    if prefer == "anthropic" and not llm.available()["anthropic"]:
        print("[batch] WARNING: ANTHROPIC_API_KEY not set — will use Ollama only")

    candidates = []
    failures = []
    start_time = time.time()

    for i, handle in enumerate(handles, start=1):
        writer = all_writers[handle]
        elapsed = time.time() - start_time
        eta = (elapsed / i * (total - i)) if i > 0 else 0
        print(
            f"[batch] {i:>3}/{total} · {writer['name']:<35} "
            f"({writer['team_abbr']}) · {elapsed:5.0f}s elapsed · ~{eta:5.0f}s left",
            flush=True,
        )

        prompt = build_prompt(writer)
        raw = llm.call(
            prompt,
            system=SYSTEM,
            max_tokens=2048,
            prefer=prefer,
            timeout_anthropic=60,
            timeout_ollama=240,
            min_chars=50,
        )

        if not raw:
            failures.append((handle, "llm call failed"))
            continue

        parsed = extract_json(raw)
        if not isinstance(parsed, list):
            failures.append((handle, f"non-list output ({type(parsed).__name__})"))
            continue

        valid_count = 0
        for c in parsed:
            if not isinstance(c, dict):
                continue
            topic = str(c.get("topic", "")).strip()
            angle = str(c.get("angle", "")).strip()
            if not topic or not angle:
                continue
            trigger_phrases = c.get("trigger_phrases", [])
            if not isinstance(trigger_phrases, list):
                trigger_phrases = []
            candidates.append(
                {
                    "writer_handle": handle,
                    "candidate": {
                        "topic": topic,
                        "angle": angle,
                        "trigger_phrases": [str(t) for t in trigger_phrases][:6],
                    },
                    "seen": False,
                    "accepted": False,
                }
            )
            valid_count += 1

        if valid_count == 0:
            failures.append((handle, "no valid candidates extracted"))

        # Incremental save every 10 writers so a crash doesn't lose everything
        if i % 10 == 0:
            config_io.atomic_write(config_io.batch_obsessions_path(), candidates)

    # Final save
    config_io.atomic_write(config_io.batch_obsessions_path(), candidates)

    total_time = time.time() - start_time
    print(f"\n[batch] done in {total_time:.0f}s")
    print(f"[batch] {len(candidates)} candidates generated across {total - len(failures)}/{total} writers")
    if failures:
        print(f"[batch] {len(failures)} failures:")
        for handle, reason in failures:
            print(f"  - {handle}: {reason}")
    print(f"[batch] written to: {config_io.batch_obsessions_path()}")
    print(f"[batch] run `python3 -m pressrow_writer serve` to swipe")
