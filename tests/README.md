# Snapshot tests

Golden byte-identical snapshot harness for `build.py`. Python stdlib only (no pytest, no third-party libraries).

## Run

```bash
python3 tests/snapshot_test.py
```

Exits 0 if Cubs and Yankees both render byte-identically against the committed expected HTML. Exits non-zero with a unified diff otherwise.

The test is fully offline: it passes a frozen JSON fixture via `--fixture` (bypassing `load_all()`'s live API calls) and relies on committed lede cache files at `data/lede-<slug>-2026-04-05.txt` to short-circuit `generate_lede()` (bypassing Ollama and the Anthropic API fallback).

## What's in `fixtures/`

| File | Purpose |
|------|---------|
| `cubs_2026_04_05_input.json` | Frozen `load_all()` output for Cubs, dates pinned to 2026-04-05 |
| `cubs_2026_04_05_expected.html` | Blessed reference HTML for Cubs |
| `yankees_2026_04_05_input.json` | Frozen `load_all()` output for Yankees, dates pinned to 2026-04-05 |
| `yankees_2026_04_05_expected.html` | Blessed reference HTML for Yankees |

Two teams on purpose — Cubs is the cron default (`build.py:34`) and the highest-risk regression target; Yankees exercises a different division, colors, and `CFG['rivals']` lookup that Cubs-only testing would miss.

## Re-blessing after an intentional HTML change

If you make an intentional change that alters the rendered HTML, the snapshot test will fail. To re-bless:

```bash
# 1. Re-render both teams against the frozen fixtures into a scratch dir
rm -rf /tmp/snap-bless
python3 build.py --team cubs    --fixture tests/fixtures/cubs_2026_04_05_input.json    --out-dir /tmp/snap-bless
python3 build.py --team yankees --fixture tests/fixtures/yankees_2026_04_05_input.json --out-dir /tmp/snap-bless

# 2. Eyeball the new HTML to make sure it looks right
less /tmp/snap-bless/cubs/index.html
less /tmp/snap-bless/yankees/index.html

# 3. Copy the new blessed output back into fixtures
cp /tmp/snap-bless/cubs/index.html    tests/fixtures/cubs_2026_04_05_expected.html
cp /tmp/snap-bless/yankees/index.html tests/fixtures/yankees_2026_04_05_expected.html

# 4. Confirm the test now passes
python3 tests/snapshot_test.py
```

Commit the updated `expected.html` files with the change that caused the diff — reviewers should see the rendering delta in the same PR as the code change.

## Re-capturing the input fixtures (rare)

Only needed if `load_all()`'s return shape changes or the existing fixtures become stale:

```bash
python3 build.py --team cubs    --capture-fixture tests/fixtures/cubs_2026_04_05_input.json
python3 build.py --team yankees --capture-fixture tests/fixtures/yankees_2026_04_05_input.json
```

Then manually pin `today`, `yest`, and (if present) `cubs_game_date` in both JSONs to `2026-04-05` / `2026-04-04` / `2026-04-05` so they match the committed lede cache files in `data/`. Then re-bless per the steps above.

## New flags added to `build.py`

- `--fixture <path>` — load the data dict from a frozen JSON fixture instead of calling `load_all()`. Skips `save_data_ledger`.
- `--out-dir <path>` — override the destination directory. Output goes to `<path>/<slug>/index.html`.
- `--capture-fixture <path>` — call `load_all()` and write the result to `<path>` as JSON, then exit. Used for fixture bootstrap.

All three flags are inert when not passed — the default `python3 build.py --team cubs` invocation used by the morning cron is unchanged.
