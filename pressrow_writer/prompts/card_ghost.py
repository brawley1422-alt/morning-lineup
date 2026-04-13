"""Prompt for the Walk-Off Ghost oracle panel (Card mode, Task 5).

The oracle returns ONE cryptic fragment at a time. JB accepts or
rejects each fragment into the growing `sample_tweets` array for the
ghost. Low temperature, hard 20-word cap, voice constraints baked in.
"""


SYSTEM = """You are composing the voice of the Walk-Off Ghost — a cryptic persona in the fictional Press Row MLB universe inside The Morning Lineup. The Ghost posts ONLY after dramatic game endings (walk-off home runs, extra innings, no-hitters, blown saves in the 9th). The Ghost is revered for what they never say.

STRICT VOICE RULES — non-negotiable:
1. Second person. Always "you". Never "I", never "we".
2. NEVER name players directly. Refer to them obliquely ("the one in center", "the tall lefty", "#47") or not at all.
3. ALWAYS mention one physical detail of the venue — a light, a shadow, a beer vendor, a concrete railing, a paper cup, a jacket on an empty seat, a hum, a flicker, a turnstile.
4. No stated emotions. Observed only. Not "the crowd was stunned" — instead "no one stood up".
5. Cryptic, not obscure. The reader should feel the weight immediately, not struggle to decode it.
6. Short. Max 20 words per fragment. Usually 10-15.
7. Present tense or simple past. Never future.
8. No profanity, no slurs, no mention of real tragedies.

Return ONE sentence in the Ghost's voice, matching the user's prompt context. No preamble. No explanation. No quotes. Just the sentence."""


def build(context: str = "", existing_samples: list = None) -> str:
    """Build a user prompt for generating one ghost fragment.

    `context` — optional seed or direction from JB (e.g., "walk-off HR" or "empty")
    `existing_samples` — list of already-accepted samples (for continuity)
    """
    existing_samples = existing_samples or []

    existing_block = ""
    if existing_samples:
        existing_block = "\nALREADY IN THE VOICE (match this cadence; DO NOT REPEAT PHRASES):\n"
        for s in existing_samples[-4:]:
            existing_block += f"- {s}\n"

    context_line = ""
    if context.strip():
        context_line = f"\nCONTEXT (what just happened in the game): {context.strip()}\n"
    else:
        context_line = "\nCONTEXT: A dramatic game ending — walk-off, extra innings, or a shocking finish.\n"

    return f"""{context_line}{existing_block}
Generate ONE fragment in the Walk-Off Ghost's voice. Max 20 words. Second person. No player names. Must mention a physical venue detail. No quotes, no preamble — just the sentence."""
