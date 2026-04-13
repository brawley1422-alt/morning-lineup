"""Prompt template for the batch obsession generator (Task 1 pre-seeding)."""


SYSTEM = """You are writing character-specific obsession candidates for Press Row, a fictional MLB beat-writer universe inside The Morning Lineup.

Each beat writer gets 2-3 "load-bearing obsessions" — narrow, petty, specific things they pivot back to. A writer with obsessions becomes recognizable across days.

TONE GUARDRAILS:
- Specific, not vague. "Hates analytics" is generic. "Thinks every closer should throw 80% sliders and the rest of the league is wrong" is an obsession.
- Load-bearing. The writer should pivot to it even when it's not directly relevant.
- In character. A Straight Beat writer's obsessions are stat-based grievances. An Optimist's are unironic beliefs in virtues nobody else sees. A Pessimist's are all-caps grudges against ownership or management.
- Avoid real players by name. Obsessions are about patterns or concepts, not "hates Jon Lester". Players come and go.
- Petty, not heavy. "Still mad about 2003" is good. Family, health, real trauma — not what this is.
- Different from signature phrase. Obsessions are topics; signature phrases are catchphrases. Don't repeat the phrase as an obsession.

You will be asked for 9 candidates per writer. Generate more variety than you'd naturally want — some should feel slightly too narrow, some slightly too broad, some perfectly tuned. The human will curate."""


def build(writer: dict) -> str:
    """Build the user prompt for a single writer's candidate batch."""
    name = writer.get("name", "Unknown")
    role = writer.get("role", "")
    team_name = writer.get("team_name", "")
    backstory = writer.get("backstory", "")
    phrase = writer.get("signature_phrase", "")
    sample = writer.get("voice_sample", "")

    return f"""Generate 9 candidate obsessions for this writer.

WRITER
Name: {name}
Role: {role}
Team: {team_name}
Backstory: {backstory}
Signature phrase: "{phrase}"
Voice sample: "{sample}"

Generate 9 candidates as a single JSON array. Each candidate is an object with:
- "topic": a short phrase naming what the obsession is about (e.g., "bullpen usage", "Wrigley ivy", "the 2003 trade")
- "angle": one sentence capturing their specific take on it (e.g., "thinks Counsell over-manages every reliever by 30%")
- "trigger_phrases": a list of 2-4 short phrases that, if mentioned in a game context, should remind the writer of this obsession

Variety matters. Include a mix of:
- 3 "stat-grievance" obsessions (for Straight Beat) or "narrative grudge" (for Pessimist) or "quiet belief" (for Optimist)
- 3 obsessions about patterns across seasons (historical, pet theories, decade-long grudges)
- 3 weird/specific obsessions (something nobody else would care about — physical details of the ballpark, umpire tendencies, small organizational quirks)

Return ONLY a valid JSON array of 9 objects. No prose before or after. No markdown fences."""
