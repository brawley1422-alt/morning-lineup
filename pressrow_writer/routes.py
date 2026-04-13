"""API route handlers. Pure functions that take a parsed request and
return (status_code, content_type, body_bytes).

The server dispatches path prefixes to these handlers.
"""
import json
from pathlib import Path

from pressrow_writer import config_io, llm, progress, writers
from pressrow_writer import prompts
from pressrow_writer.util import extract_json_blocks


STATIC_DIR = Path(__file__).resolve().parent / "static"


# ─── static file serving ──────────────────────────────────────────────────


def serve_static(path: str):
    """Serve a file from pressrow_writer/static/.

    `path` is the URL path without the /static/ prefix.
    """
    if not path or ".." in path:
        return (404, "text/plain", b"not found")
    file_path = STATIC_DIR / path
    if not file_path.exists() or not file_path.is_file():
        return (404, "text/plain", b"not found")
    content_type = _content_type_for(file_path.suffix)
    return (200, content_type, file_path.read_bytes())


def serve_index():
    """Serve the single-page app shell."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return (500, "text/plain", b"index.html not found")
    return (200, "text/html; charset=utf-8", index.read_bytes())


def _content_type_for(suffix: str) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".ico": "image/x-icon",
    }.get(suffix.lower(), "application/octet-stream")


# ─── API handlers ──────────────────────────────────────────────────────────


def _json_response(data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return (status, "application/json; charset=utf-8", body)


def api_progress(request_body=None):
    return _json_response(progress.compute())


def api_writers(request_body=None):
    return _json_response(writers.load_all())


def api_teams(request_body=None):
    return _json_response(writers.load_teams())


def api_llm_status(request_body=None):
    return _json_response(llm.available())


# ─── Chat API ──────────────────────────────────────────────────────────────


# Maps UI task slugs to their current-state loader + prompt task key
_CHAT_TASK_CONFIG = {
    "shadow_personas": {
        "loader": config_io.load_shadow_personas,
        "prompt_task": "shadow_personas",
    },
    "recurring_fans": {
        "loader": config_io.load_recurring_fans,
        "prompt_task": "recurring_fans",
    },
    "feuds": {
        "loader": config_io.load_relationships,
        "prompt_task": "feuds",
    },
}


def api_chat_message(request_body):
    """POST /api/chat/message — generate a chat response.

    Expects body: {task, history, user_message}
    Returns: {response, committable: [parsed JSON blocks]}
    """
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)

    task = request_body.get("task", "")
    history = request_body.get("history", [])
    user_message = request_body.get("user_message", "").strip()

    if task not in _CHAT_TASK_CONFIG:
        return _json_response({"error": f"unknown task: {task}"}, status=400)
    if not user_message:
        return _json_response({"error": "empty user_message"}, status=400)

    existing = _CHAT_TASK_CONFIG[task]["loader"]()
    system_prompt, user_prompt = prompts.build_chat_prompt(
        _CHAT_TASK_CONFIG[task]["prompt_task"],
        history,
        user_message,
        existing,
    )

    response_text = llm.call(
        user_prompt,
        system=system_prompt,
        max_tokens=2048,
        prefer="anthropic",
        min_chars=20,
        timeout_ollama=180,
    )

    if not response_text:
        return _json_response(
            {"error": "LLM call failed. Check ANTHROPIC_API_KEY or Ollama."},
            status=503,
        )

    committable = extract_json_blocks(response_text)
    return _json_response(
        {
            "response": response_text,
            "committable": committable,
        }
    )


def api_chat_commit(task_type: str, request_body):
    """POST /api/chat/commit/{shadow_personas|recurring_fans|feuds}

    Atomically writes the entry to its target config file. Returns
    {ok: true, progress: {...}} on success.
    """
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)

    entry = request_body.get("entry")
    replace = bool(request_body.get("replace", False))

    if not isinstance(entry, dict):
        return _json_response({"error": "missing or invalid 'entry' object"}, status=400)

    if task_type == "shadow_personas":
        result = _commit_shadow_persona(entry, replace)
    elif task_type == "recurring_fans":
        result = _commit_recurring_fan(entry, replace)
    elif task_type == "feuds":
        result = _commit_feud(entry, replace)
    else:
        return _json_response({"error": f"unknown task_type: {task_type}"}, status=400)

    status, payload = result
    if status == 200:
        payload["progress"] = progress.compute()
    return _json_response(payload, status=status)


def _commit_shadow_persona(entry: dict, replace: bool):
    team_slug = entry.get("team_slug", "").strip()
    if not team_slug:
        return (400, {"error": "shadow persona requires 'team_slug'"})
    required = ("name", "handle", "monomaniac_topic", "voice")
    missing = [f for f in required if not entry.get(f)]
    if missing:
        return (400, {"error": f"missing required fields: {missing}"})

    existing = config_io.load_shadow_personas()
    if not isinstance(existing, dict):
        existing = {}

    if team_slug in existing and not replace:
        return (
            409,
            {
                "error": f"shadow persona for '{team_slug}' already exists",
                "existing": existing[team_slug],
                "hint": "pass replace: true to overwrite",
            },
        )

    existing[team_slug] = entry
    config_io.atomic_write(config_io.shadow_personas_path(), existing)
    return (200, {"ok": True, "committed": entry})


def _commit_recurring_fan(entry: dict, replace: bool):
    name = entry.get("name", "").strip()
    if not name:
        return (400, {"error": "recurring fan requires 'name'"})
    if not entry.get("voice"):
        return (400, {"error": "recurring fan requires 'voice'"})

    existing = config_io.load_recurring_fans()
    if not isinstance(existing, list):
        existing = []

    dupe_index = None
    for i, f in enumerate(existing):
        if isinstance(f, dict) and f.get("name", "").strip().lower() == name.lower():
            dupe_index = i
            break

    if dupe_index is not None:
        if not replace:
            return (
                409,
                {
                    "error": f"recurring fan '{name}' already exists",
                    "existing": existing[dupe_index],
                    "hint": "pass replace: true to overwrite",
                },
            )
        existing[dupe_index] = entry
    else:
        existing.append(entry)

    config_io.atomic_write(config_io.recurring_fans_path(), existing)
    return (200, {"ok": True, "committed": entry})


def _commit_feud(entry: dict, replace: bool):
    feud_id = entry.get("id", "").strip()
    if not feud_id:
        return (400, {"error": "feud requires 'id'"})
    writers_field = entry.get("writers")
    if not isinstance(writers_field, list) or len(writers_field) != 2:
        return (400, {"error": "feud requires 'writers' list of 2 handles"})
    if not entry.get("origin"):
        return (400, {"error": "feud requires 'origin' object"})

    existing = config_io.load_relationships()
    if not isinstance(existing, dict):
        existing = {"feuds": []}
    feuds = existing.get("feuds", [])
    if not isinstance(feuds, list):
        feuds = []

    dupe_index = None
    for i, f in enumerate(feuds):
        if isinstance(f, dict) and f.get("id") == feud_id:
            dupe_index = i
            break

    if dupe_index is not None:
        if not replace:
            return (
                409,
                {
                    "error": f"feud '{feud_id}' already exists",
                    "existing": feuds[dupe_index],
                    "hint": "pass replace: true to overwrite",
                },
            )
        feuds[dupe_index] = entry
    else:
        feuds.append(entry)

    existing["feuds"] = feuds
    config_io.atomic_write(config_io.relationships_path(), existing)
    return (200, {"ok": True, "committed": entry})


# ─── Swipe API ─────────────────────────────────────────────────────────────


def _load_batch():
    """Load the batch obsession candidates, returning [] if missing."""
    data = config_io.load_batch_obsessions()
    if not isinstance(data, list):
        return []
    return data


def _save_batch(data):
    config_io.atomic_write(config_io.batch_obsessions_path(), data)


def _writer_obsession_count(handle: str) -> int:
    """How many committed obsessions exist for a writer."""
    obsessions = config_io.load_obsessions()
    if not isinstance(obsessions, dict):
        return 0
    entry = obsessions.get(handle, [])
    if not isinstance(entry, list):
        return 0
    return len(entry)


def _commit_obsession_for_writer(handle: str, obsession: dict, replace_all: bool = False):
    """Append an obsession to a writer's entry in obsessions.json.
    Creates the entry if missing. If replace_all is True, overwrites the
    full list with just this obsession (used by Anchor flow)."""
    obsessions = config_io.load_obsessions()
    if not isinstance(obsessions, dict):
        obsessions = {}
    if replace_all or handle not in obsessions:
        obsessions[handle] = []
    if not isinstance(obsessions[handle], list):
        obsessions[handle] = []
    obsessions[handle].append(obsession)
    config_io.atomic_write(config_io.obsessions_path(), obsessions)


def api_swipe_next(request_body=None):
    """GET /api/swipe/next — return the next unseen candidate, or a
    completion signal if the deck is empty.

    Response: {candidate: {...}, writer: {...}, remaining_for_writer: N,
               total_remaining: N} or {done: true}
    """
    batch = _load_batch()
    if not batch:
        return _json_response({
            "error": "No candidates yet. Run `python3 -m pressrow_writer batch` first.",
            "needs_batch": True,
        }, status=404)

    all_writers = writers.load_all()

    # Find the first unseen candidate whose writer still has fewer than 3 obsessions
    for i, c in enumerate(batch):
        if c.get("seen"):
            continue
        handle = c.get("writer_handle")
        if not handle or handle not in all_writers:
            # Unknown writer — mark seen to prevent infinite skip
            c["seen"] = True
            continue
        # Skip if writer is already fully obsessed (≥3 committed)
        if _writer_obsession_count(handle) >= 3:
            c["seen"] = True
            continue

        # Count remaining unseen for this writer
        remaining_for_writer = sum(
            1 for b in batch
            if b.get("writer_handle") == handle and not b.get("seen")
        )
        total_remaining = sum(1 for b in batch if not b.get("seen"))

        # Save any changes (from skips above)
        _save_batch(batch)

        return _json_response({
            "index": i,
            "candidate": c["candidate"],
            "writer": all_writers[handle],
            "writer_handle": handle,
            "current_obsession_count": _writer_obsession_count(handle),
            "remaining_for_writer": remaining_for_writer,
            "total_remaining": total_remaining,
        })

    # Nothing left
    _save_batch(batch)
    return _json_response({"done": True})


def api_swipe_accept(request_body):
    """POST /api/swipe/accept — commit a candidate to obsessions.json.

    Body: {index}
    """
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)

    index = request_body.get("index")
    if not isinstance(index, int):
        return _json_response({"error": "missing 'index'"}, status=400)

    batch = _load_batch()
    if index < 0 or index >= len(batch):
        return _json_response({"error": "index out of range"}, status=400)

    entry = batch[index]
    if entry.get("seen"):
        return _json_response({"error": "candidate already seen"}, status=409)

    handle = entry.get("writer_handle")
    candidate = entry.get("candidate", {})
    if not handle or not candidate:
        return _json_response({"error": "malformed batch entry"}, status=500)

    _commit_obsession_for_writer(handle, candidate)

    batch[index]["seen"] = True
    batch[index]["accepted"] = True
    _save_batch(batch)

    return _json_response({
        "ok": True,
        "progress": progress.compute(),
    })


def api_swipe_reject(request_body):
    """POST /api/swipe/reject — mark a candidate seen without committing."""
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)
    index = request_body.get("index")
    if not isinstance(index, int):
        return _json_response({"error": "missing 'index'"}, status=400)

    batch = _load_batch()
    if index < 0 or index >= len(batch):
        return _json_response({"error": "index out of range"}, status=400)

    batch[index]["seen"] = True
    batch[index]["accepted"] = False
    _save_batch(batch)

    return _json_response({"ok": True, "progress": progress.compute()})


def api_swipe_anchor(request_body):
    """POST /api/swipe/anchor — commit the anchor, generate 2 variants
    in matching voice, commit those too, and mark all other unseen
    candidates for the same writer as seen.

    Body: {index}
    """
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)
    index = request_body.get("index")
    if not isinstance(index, int):
        return _json_response({"error": "missing 'index'"}, status=400)

    batch = _load_batch()
    if index < 0 or index >= len(batch):
        return _json_response({"error": "index out of range"}, status=400)

    entry = batch[index]
    if entry.get("seen"):
        return _json_response({"error": "candidate already seen"}, status=409)

    handle = entry.get("writer_handle")
    anchor = entry.get("candidate", {})
    if not handle or not anchor:
        return _json_response({"error": "malformed batch entry"}, status=500)

    all_writers = writers.load_all()
    writer = all_writers.get(handle)
    if not writer:
        return _json_response({"error": f"unknown writer: {handle}"}, status=500)

    # Replace all existing obsessions for this writer with a fresh list
    # starting from the anchor (anchor is always obsession #1 in the new set)
    _commit_obsession_for_writer(handle, anchor, replace_all=True)

    # Generate 2 variants
    from pressrow_writer.prompts import anchor_variants
    from pressrow_writer.util import extract_json

    variant_prompt = anchor_variants.build(writer, anchor)
    raw = llm.call(
        variant_prompt,
        system=anchor_variants.SYSTEM,
        max_tokens=1024,
        prefer="anthropic",
        timeout_ollama=180,
        min_chars=20,
    )

    variants = []
    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, list):
            for v in parsed:
                if not isinstance(v, dict):
                    continue
                topic = str(v.get("topic", "")).strip()
                angle = str(v.get("angle", "")).strip()
                if not topic or not angle:
                    continue
                triggers = v.get("trigger_phrases", [])
                if not isinstance(triggers, list):
                    triggers = []
                variants.append({
                    "topic": topic,
                    "angle": angle,
                    "trigger_phrases": [str(t) for t in triggers][:6],
                })
                if len(variants) >= 2:
                    break

    for v in variants:
        _commit_obsession_for_writer(handle, v)

    # Mark the anchor and all other unseen candidates for this writer as seen
    for i, b in enumerate(batch):
        if b.get("writer_handle") == handle and not b.get("seen"):
            batch[i]["seen"] = True
            batch[i]["accepted"] = (i == index)
    _save_batch(batch)

    return _json_response({
        "ok": True,
        "anchor": anchor,
        "variants": variants,
        "variants_count": len(variants),
        "progress": progress.compute(),
    })


# ─── Card API ──────────────────────────────────────────────────────────────


def api_card_ghost(request_body=None):
    """GET /api/card/ghost — return the current ghost state (if any)."""
    cast = config_io.load_cast()
    ghost = cast.get("walkoff_ghost") if isinstance(cast, dict) else None
    return _json_response({"ghost": ghost or {}})


def api_card_ghost_oracle(request_body):
    """POST /api/card/ghost/oracle — generate one cryptic fragment.

    Body: {context?: str, existing_samples?: list}
    """
    if not isinstance(request_body, dict):
        request_body = {}
    context = str(request_body.get("context", "")).strip()
    existing_samples = request_body.get("existing_samples", [])
    if not isinstance(existing_samples, list):
        existing_samples = []

    from pressrow_writer.prompts import card_ghost
    prompt = card_ghost.build(context, existing_samples)

    fragment = llm.call(
        prompt,
        system=card_ghost.SYSTEM,
        max_tokens=1024,
        prefer="anthropic",
        timeout_ollama=180,
        min_chars=8,
    )

    if not fragment:
        return _json_response(
            {"error": "Oracle is silent. Check ANTHROPIC_API_KEY or Ollama."},
            status=503,
        )

    # Strip surrounding quotes if the model added them
    fragment = fragment.strip().strip('"').strip("'").strip()
    # Enforce single-sentence max ~25 words
    words = fragment.split()
    if len(words) > 25:
        fragment = " ".join(words[:25])

    return _json_response({"fragment": fragment})


def api_card_ghost_commit(request_body):
    """POST /api/card/ghost/commit — save the ghost persona to cast.json.

    Body: {name, handle, voice, sample_tweets}
    """
    if not isinstance(request_body, dict):
        return _json_response({"error": "invalid body"}, status=400)

    name = str(request_body.get("name", "")).strip()
    voice = str(request_body.get("voice", "")).strip()
    sample_tweets = request_body.get("sample_tweets", [])

    if not name:
        return _json_response({"error": "ghost requires 'name'"}, status=400)
    if not voice:
        return _json_response({"error": "ghost requires 'voice'"}, status=400)
    if not isinstance(sample_tweets, list) or len(sample_tweets) < 1:
        return _json_response({"error": "ghost requires at least 1 sample tweet"}, status=400)

    from pressrow_writer.util import make_handle
    handle = request_body.get("handle") or make_handle(name)

    cast = config_io.load_cast()
    if not isinstance(cast, dict):
        cast = {}

    cast["walkoff_ghost"] = {
        "name": name,
        "handle": handle,
        "voice": voice,
        "sample_tweets": [str(s) for s in sample_tweets],
    }
    config_io.atomic_write(config_io.cast_path(), cast)

    return _json_response({
        "ok": True,
        "ghost": cast["walkoff_ghost"],
        "progress": progress.compute(),
    })
