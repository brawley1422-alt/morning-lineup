"""Prompt for anchor + variants regeneration (Swipe mode).

When JB anchors one obsession he loves, this prompt asks Sonnet to
generate 2 more obsessions for the same writer in the SAME register,
cadence, and voice — but on different topics. Taste radiates outward.
"""


SYSTEM = """You are writing matching obsessions for Press Row, a fictional MLB beat-writer universe.

The user just anchored one obsession they LOVE for a specific writer. Your job is to generate 2 more obsessions for the SAME writer that match the anchor's register, cadence, punctuation, and voice — but cover DIFFERENT topics. Do not copy the anchor. Radiate outward from it.

Match exactly:
- Sentence length and rhythm
- Vocabulary register (formal/informal, old-school/modern)
- Level of specificity (narrow vs broad)
- Tone (bitter/wry/earnest/etc.)

Change:
- The topic itself
- The specific numbers or references

Return ONLY a valid JSON array of exactly 2 obsession objects. No prose, no markdown fences."""


def build(writer: dict, anchor: dict) -> str:
    """Build the user prompt for anchor-variants regeneration."""
    name = writer.get("name", "Unknown")
    role = writer.get("role", "")
    team_name = writer.get("team_name", "")
    backstory = writer.get("backstory", "")
    phrase = writer.get("signature_phrase", "")
    sample = writer.get("voice_sample", "")

    anchor_topic = anchor.get("topic", "")
    anchor_angle = anchor.get("angle", "")

    return f"""WRITER
Name: {name}
Role: {role}
Team: {team_name}
Backstory: {backstory}
Signature phrase: "{phrase}"
Voice sample: "{sample}"

ANCHOR OBSESSION (this is perfectly tuned — match its voice):
Topic: {anchor_topic}
Angle: {anchor_angle}

Generate 2 new obsessions for this writer. Same voice and cadence as the anchor. Different topics.

Schema per obsession:
- "topic": short phrase naming what it's about
- "angle": one sentence capturing their specific take
- "trigger_phrases": list of 2-4 short phrases

Return ONLY a JSON array of 2 objects. No prose. No markdown fences."""
