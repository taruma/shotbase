import json
import logging
from pathlib import Path

from app.services.shot_utils import validate_shot_name

logger = logging.getLogger(__name__)


class ShotOrderManager:
    """Manages shot display order and archived state (pure JSON file I/O)."""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.order_file = self.shots_dir / '.shot_order.json'
        self.archive_file = self.shots_dir / '.archived_shots.json'

    # ------------------------------------------------------------------
    # Shot order
    # ------------------------------------------------------------------

    def load_shot_order(self):
        """Load shot order list from JSON file."""
        try:
            if self.order_file.exists():
                with self.order_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
        except Exception:
            logger.exception("Error loading shot order")
        return []

    def save_shot_order(self, names):
        """Persist shot order list to JSON file."""
        try:
            cleaned = []
            seen = set()
            for name in names:
                if isinstance(name, str) and name not in seen:
                    cleaned.append(name)
                    seen.add(name)
            self.shots_dir.mkdir(parents=True, exist_ok=True)
            with self.order_file.open('w', encoding='utf-8') as f:
                json.dump(cleaned, f)
        except Exception:
            logger.warning("Failed to save shot order file")

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def load_archived(self):
        """Load archived shot names from JSON file (returns a set)."""
        try:
            if self.archive_file.exists():
                with self.archive_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
        except Exception:
            logger.exception("Error loading archived shots")
        return set()

    def save_archived(self, names: set):
        """Persist archived shot names to JSON file."""
        try:
            self.shots_dir.mkdir(parents=True, exist_ok=True)
            with self.archive_file.open('w', encoding='utf-8') as f:
                json.dump(sorted(list(names)), f)
        except Exception:
            logger.warning("Failed to save archived shots file")

    def toggle_archived(self, shot_name, archived: bool):
        """Toggle archived state for a shot.

        Returns the updated set of archived shot names.
        Does NOT call get_shot_info — the caller (ShotManager) handles that.
        """
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")

        names = self.load_archived()
        if archived:
            names.add(shot_name)
        else:
            names.discard(shot_name)
        self.save_archived(names)
        return names

    def is_archived(self, shot_name, cached_archived_names=None):
        """Check whether a shot is archived."""
        if cached_archived_names is not None:
            return shot_name in cached_archived_names
        return shot_name in self.load_archived()