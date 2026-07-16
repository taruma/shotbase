import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Shot names may optionally contain a single underscore followed by another
# three-digit number (e.g. ``SH001_050``).  Deeper nesting with multiple
# underscores is not allowed.
SHOT_NAME_RE = re.compile(r"^SH\d{3}(?:_\d{3})?$")


def validate_shot_name(name):
    if not SHOT_NAME_RE.match(name):
        raise ValueError(f"Invalid shot name: {name}")
    if name == "SH000":
        raise ValueError("Invalid shot name: SH000")


def _parse_shot_parts(name):
    """Return the numeric segments for a shot name."""
    return [int(p) for p in name[2:].split("_")]


def _format_shot_parts(parts):
    """Format numeric segments back into a shot name."""
    base = f"SH{parts[0]:03d}"
    for p in parts[1:]:
        base += f"_{p:03d}"
    return base


def _meta_file(shot_name):
    """Return path to the meta JSON for a shot."""
    return Path("shots") / "wip" / shot_name / "meta.json"


def _project_meta_file(project_path, shot_name):
    """Return path to the project-scoped meta JSON for a shot."""
    return Path(project_path) / "shots" / "wip" / shot_name / "meta.json"


def load_meta(shot_name):
    """Load meta dict for a shot."""
    validate_shot_name(shot_name)
    path = _meta_file(shot_name)
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        logger.exception("Error loading shot meta")
    return {}


def save_display_name(shot_name, display_name):
    """Persist display name for a shot."""
    validate_shot_name(shot_name)
    path = _meta_file(shot_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('w', encoding='utf-8') as f:
            json.dump({"display_name": display_name}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ValueError(f"Failed to save display name: {str(e)}")


def get_shot_manager(project_path, cache=None):
    """Retrieve a cached ``ShotManager`` for the given path."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.setdefault('SHOT_MANAGER_CACHE', {})

    path_key = str(Path(project_path).resolve())
    if path_key not in cache:
        from app.services.shot_manager import ShotManager
        cache[path_key] = ShotManager(path_key)
    return cache[path_key]


def clear_shot_manager_cache(cache=None):
    """Clear cached ``ShotManager`` instances."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.get('SHOT_MANAGER_CACHE')

    if cache is not None:
        cache.clear()