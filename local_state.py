"""Saves the app's parameters and costs to a local, git-ignored folder.

The folder defaults to `.local/` next to this file; set NPV_STATE_DIR to use
another one (the tests do).
"""

import json
import math
import os
from pathlib import Path

STATE_FILE = "state.json"


def state_path() -> Path:
    folder = os.environ.get("NPV_STATE_DIR") or Path(__file__).parent / ".local"
    return Path(folder) / STATE_FILE


def _clean(value):
    """JSON-safe value: NaN and None become null, numpy scalars become Python ones."""
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def load_state() -> dict:
    """The saved state, or {} if there is none or it can't be read."""
    try:
        state = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def save_state(params: dict, costs: list[dict]) -> dict:
    """Write params and cost rows if they changed since the last save; returns what is on disk."""
    state = {
        "params": {k: _clean(v) for k, v in params.items()},
        "costs": [{k: _clean(v) for k, v in row.items()} for row in costs],
    }
    if load_state() != state:
        path = state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    return state
