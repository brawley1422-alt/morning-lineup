"""Prompt templates for each mode and task. Each template module exports
a `build(...)` function returning a prompt string.

Unit 2 ships stub versions. Unit 3 replaces them with production-quality
prompts tuned for the Morning Lineup voice.
"""
from pressrow_writer.prompts import (
    chat_shadow_personas,
    chat_recurring_fans,
    chat_feuds,
)

CHAT_TASK_MAP = {
    "shadow_personas": chat_shadow_personas,
    "recurring_fans": chat_recurring_fans,
    "feuds": chat_feuds,
}


def build_chat_prompt(task: str, history: list, user_message: str, existing: dict) -> tuple:
    """Return (system_prompt, user_prompt) for a chat task.

    `history` is a list of {role, content} dicts (prior chat turns).
    `user_message` is the current user input.
    `existing` is the current state of the target config file.
    """
    module = CHAT_TASK_MAP.get(task)
    if not module:
        return ("", user_message)
    return module.build(history, user_message, existing)
