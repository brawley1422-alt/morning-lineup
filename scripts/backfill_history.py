#!/usr/bin/env python3
"""
backfill_history.py — Fill in missing dates in history.json using the Anthropic API.
Generates 2-3 notable Cubs history events for each missing calendar date.

Usage:
  ANTHROPIC_API_KEY=sk-... python3 scripts/backfill_history.py

Outputs:
  - scripts/history_review.json  (new entries only, for manual review)
  - history.json                 (merged result — existing entries preserved)
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent
HISTORY_FILE = ROOT / "history.json"
REVIEW_FILE = Path(__file__).parent / "history_review.json"

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    sys.exit("error: ANTHROPIC_API_KEY env var not set")

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

# All 366 possible MM-DD keys (including leap day)
def all_dates():
    keys = []
    for month in range(1, 13):
        days = {1:31, 2:29, 3:31, 4:30, 5:31, 6:30,
                7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for day in range(1, days[month] + 1):
            keys.append(f"{month:02d}-{day:02d}")
    return keys

def call_claude(prompt):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    return resp["content"][0]["text"]

def parse_entries(text):
    """Parse Claude's response into [{year, text}] entries."""
    entries = []
    for line in text.strip().split("\n"):
        line = line.strip().lstrip("- ").lstrip("* ")
        if not line:
            continue
        # Expect format: YYYY: description
        if len(line) > 6 and line[4] in ":–-" and line[:4].isdigit():
            year = int(line[:4])
            desc = line[5:].strip().lstrip(":–- ").strip()
            if desc:
                entries.append({"year": year, "text": desc})
    return entries

def batch_prompt(date_keys):
    """Create a prompt for a batch of dates."""
    dates_str = ", ".join(date_keys)
    return f"""For each of the following calendar dates (MM-DD format), provide 2-3 notable events from Chicago Cubs baseball history. Include events from any era (1876-present). Focus on memorable games, milestones, trades, draft picks, World Series moments, no-hitters, records, debuts, retirements, and franchise-defining moments.

Format each entry as:
## MM-DD
- YYYY: One-sentence description of the event.

Be factually accurate. If a date has no well-known Cubs event, use a lesser-known but real event from Cubs history on or very near that date.

Dates: {dates_str}"""

def main():
    # Load existing history
    existing = {}
    if HISTORY_FILE.exists():
        existing = json.loads(HISTORY_FILE.read_text())

    all_keys = all_dates()
    missing = [k for k in all_keys if k not in existing]
    print(f"Existing: {len(existing)} dates")
    print(f"Missing:  {len(missing)} dates")

    if not missing:
        print("All dates covered!")
        return

    # Process in batches of 15
    new_entries = {}
    batch_size = 15
    total_batches = (len(missing) + batch_size - 1) // batch_size

    for i in range(0, len(missing), batch_size):
        batch = missing[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"\nBatch {batch_num}/{total_batches}: {batch[0]} - {batch[-1]}", flush=True)

        try:
            prompt = batch_prompt(batch)
            response = call_claude(prompt)

            # Parse response by date header
            current_key = None
            current_text = []
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("## ") and len(line) >= 7:
                    # Save previous
                    if current_key and current_text:
                        entries = parse_entries("\n".join(current_text))
                        if entries:
                            new_entries[current_key] = entries
                    current_key = line[3:].strip()
                    current_text = []
                elif current_key:
                    current_text.append(line)

            # Save last
            if current_key and current_text:
                entries = parse_entries("\n".join(current_text))
                if entries:
                    new_entries[current_key] = entries

            filled = sum(1 for k in batch if k in new_entries)
            print(f"  Got {filled}/{len(batch)} dates")

        except Exception as e:
            print(f"  Error: {e}")

        # Rate limit
        if i + batch_size < len(missing):
            time.sleep(1)

    # Save review file
    REVIEW_FILE.write_text(json.dumps(new_entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReview file: {REVIEW_FILE} ({len(new_entries)} new dates)")

    # Merge with existing
    merged = dict(existing)
    merged.update(new_entries)
    HISTORY_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Merged:     {HISTORY_FILE} ({len(merged)} total dates)")

if __name__ == "__main__":
    main()
