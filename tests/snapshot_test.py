#!/usr/bin/env python3
"""Golden snapshot test for build.py.

Runs `build.py --team <slug> --fixture <input.json> --out-dir <tempdir>` as a
subprocess for each frozen team fixture, diffs the resulting HTML against the
committed expected HTML, and exits non-zero on any mismatch. Stdlib only.

No live API calls (frozen fixture). No LLM calls (committed lede cache in
data/lede-<slug>-<date>.txt short-circuits generate_lede at build.py:1368).

Re-bless after an intentional HTML change: see tests/README.md.
"""
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

CASES = [
    ("cubs",    FIXTURES / "cubs_2026_04_05_input.json",    FIXTURES / "cubs_2026_04_05_expected.html"),
    ("yankees", FIXTURES / "yankees_2026_04_05_input.json", FIXTURES / "yankees_2026_04_05_expected.html"),
]


def run_case(slug, fixture_input, fixture_expected):
    tempdir = Path(tempfile.mkdtemp(prefix=f"snap-{slug}-"))
    try:
        subprocess.run(
            [
                sys.executable,
                "build.py",
                "--team", slug,
                "--fixture", str(fixture_input),
                "--out-dir", str(tempdir),
            ],
            cwd=str(ROOT),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        actual_path = tempdir / slug / "index.html"
        if not actual_path.exists():
            print(f"FAIL [{slug}]: build.py did not write {actual_path}")
            return False
        actual = actual_path.read_text(encoding="utf-8")
        expected = fixture_expected.read_text(encoding="utf-8")
        if actual == expected:
            print(f"OK   [{slug}]: snapshot matches ({len(actual):,} chars)")
            return True
        print(f"FAIL [{slug}]: snapshot diverged from {fixture_expected.name}")
        diff = difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"expected/{slug}",
            tofile=f"actual/{slug}",
            n=3,
        )
        sys.stdout.writelines(diff)
        return False
    except subprocess.CalledProcessError as exc:
        print(f"FAIL [{slug}]: build.py subprocess exited {exc.returncode}")
        sys.stdout.write(exc.stdout.decode("utf-8", errors="replace"))
        sys.stderr.write(exc.stderr.decode("utf-8", errors="replace"))
        return False
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def main():
    results = [run_case(slug, inp, exp) for slug, inp, exp in CASES]
    if all(results):
        print(f"\nAll {len(results)} snapshots OK.")
        sys.exit(0)
    failed = sum(1 for r in results if not r)
    print(f"\n{failed}/{len(results)} snapshots FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()
