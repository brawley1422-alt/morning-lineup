"""Derive task completion progress from the config files.

Single source of truth: the JSON files themselves. No separate state.
"""
from pressrow_writer import config_io


# Target counts per task (hardcoded — could move to a config later)
TASK_TARGETS = {
    "task1_obsessions": 90,      # 90 writers need ≥2 obsessions each
    "task2_shadow_personas": 30, # one per team
    "task3_recurring_fans": 15,  # target floor
    "task4_feuds": 10,           # initial seeds
    "task5_ghost": 1,            # single entry
}


def compute() -> dict:
    """Return a dict with done/total counts for each of the 5 tasks."""
    return {
        "task1": _compute_obsessions(),
        "task2": _compute_shadow_personas(),
        "task3": _compute_recurring_fans(),
        "task4": _compute_feuds(),
        "task5": _compute_ghost(),
    }


def _compute_obsessions() -> dict:
    data = config_io.load_obsessions()
    done = 0
    if isinstance(data, dict):
        for handle, obs in data.items():
            if isinstance(obs, list) and len(obs) >= 2:
                done += 1
    return {"done": done, "total": TASK_TARGETS["task1_obsessions"], "label": "writers obsessed"}


def _compute_shadow_personas() -> dict:
    data = config_io.load_shadow_personas()
    done = len(data) if isinstance(data, dict) else 0
    return {"done": done, "total": TASK_TARGETS["task2_shadow_personas"], "label": "shadow personas"}


def _compute_recurring_fans() -> dict:
    data = config_io.load_recurring_fans()
    done = 0
    if isinstance(data, list):
        done = sum(1 for f in data if isinstance(f, dict) and f.get("name"))
    return {"done": done, "total": TASK_TARGETS["task3_recurring_fans"], "label": "recurring fans"}


def _compute_feuds() -> dict:
    data = config_io.load_relationships()
    done = 0
    if isinstance(data, dict):
        feuds = data.get("feuds", [])
        if isinstance(feuds, list):
            done = len(feuds)
    return {"done": done, "total": TASK_TARGETS["task4_feuds"], "label": "feuds"}


def _compute_ghost() -> dict:
    data = config_io.load_cast()
    has_ghost = False
    if isinstance(data, dict):
        ghost = data.get("walkoff_ghost", {})
        if isinstance(ghost, dict) and ghost.get("voice"):
            has_ghost = True
    return {"done": 1 if has_ghost else 0, "total": 1, "label": "walk-off ghost"}
