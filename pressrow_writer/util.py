"""Small helpers ported from docs/future/pressrow.py — handle generation,
initial extraction, timestamp normalization, JSON extraction from LLM output.
"""
import json
import re


def make_handle(name: str) -> str:
    """'Tony Gedeski' → 'tony_gedeski'"""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def make_initials(name: str) -> str:
    """'Beatrice Bee Vittorini' → 'BV' (first + last)"""
    parts = re.sub(r"['\"]", "", name).split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return parts[0][0].upper() if parts else "?"


def strip_thinking(text: str) -> str:
    """Remove qwen-style <think>...</think> blocks from LLM output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_json(raw: str):
    """Try to extract a JSON value from raw LLM output, handling markdown
    fences and leading/trailing prose. Returns the parsed value or None."""
    if not raw:
        return None
    raw = raw.strip()
    # Strip markdown fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence_match:
        raw = fence_match.group(1).strip()
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try finding the first JSON-ish substring
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        i = raw.find(start_char)
        j = raw.rfind(end_char)
        if i != -1 and j > i:
            try:
                return json.loads(raw[i : j + 1])
            except json.JSONDecodeError:
                continue
    return None


def extract_json_blocks(raw: str):
    """Find all fenced ```json``` blocks in a string. Returns a list of
    parsed values. Used by Chat mode to detect committable entries in
    Claude responses."""
    if not raw:
        return []
    blocks = []
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", raw):
        parsed = extract_json(match.group(1))
        if parsed is not None:
            blocks.append(parsed)
    return blocks
