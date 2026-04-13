"""LLM helper with Anthropic → Ollama fallback.

Ported from sections/columnists.py:142-191 with defaults flipped to
prefer Anthropic first (quality > speed for one-time authoring).

Stdlib only — uses urllib.request directly.
"""
import json
import os
import urllib.request

from pressrow_writer.util import strip_thinking


def call(
    prompt: str,
    *,
    max_tokens: int = 1024,
    prefer: str = "anthropic",
    timeout_anthropic: int = 60,
    timeout_ollama: int = 120,
    min_chars: int = 20,
    system: str = None,
) -> str:
    """Call an LLM, returning the response text or '' on total failure.

    Tries `prefer` provider first, falls back to the other. Returns empty
    string if both fail or the response is shorter than min_chars.
    """
    providers = ["anthropic", "ollama"] if prefer == "anthropic" else ["ollama", "anthropic"]
    for p in providers:
        if p == "anthropic":
            text = _try_anthropic(prompt, max_tokens, timeout_anthropic, system)
        else:
            text = _try_ollama(prompt, max_tokens, timeout_ollama, system)
        if text and len(text) >= min_chars:
            return text
    return ""


def _try_anthropic(prompt: str, max_tokens: int, timeout: int, system: str = None) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""
    body_data = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body_data["system"] = system
    try:
        body = json.dumps(body_data).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
        return resp["content"][0]["text"].strip()
    except Exception as e:
        print(f"  [llm] Anthropic failed: {e}", flush=True)
    return ""


def _try_ollama(prompt: str, max_tokens: int, timeout: int, system: str = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        body = json.dumps(
            {
                "model": "qwen3:8b-q4_K_M",
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.8, "num_predict": max_tokens},
            }
        ).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
        text = resp.get("message", {}).get("content", "").strip()
        return strip_thinking(text)
    except Exception as e:
        print(f"  [llm] Ollama failed: {e}", flush=True)
    return ""


def available() -> dict:
    """Report which providers appear to be configured. Used by the UI
    to show degraded-mode warnings."""
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "ollama": True,  # Can't cheaply check; assume present
    }
