import json
import logging
from pathlib import Path

from app.services.shot_utils import _project_meta_file, load_meta, validate_shot_name

logger = logging.getLogger(__name__)


class ShotMetadata:
    """CRUD for per-shot notes, captions, and display-name metadata."""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.wip_dir = self.project_path / 'shots' / 'wip'

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def load_notes(self, shot_name):
        """Read the notes.txt for a shot (returns a string)."""
        notes_file = self.wip_dir / shot_name / 'notes.txt'
        if notes_file.exists():
            try:
                with open(notes_file, encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                logger.exception("Error loading shot notes")
        return ''

    def save_notes(self, shot_name, notes):
        """Persist notes text for a shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")

        notes_file = shot_dir / 'notes.txt'
        try:
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write(notes)
        except Exception as e:
            raise ValueError(f"Failed to save notes: {str(e)}")

    # ------------------------------------------------------------------
    # Captions
    # ------------------------------------------------------------------

    def _captions_file(self, shot_name):
        """Return path to the captions JSON for a shot."""
        return (self.wip_dir / shot_name) / 'captions.json'

    def load_captions(self, shot_name):
        """Load captions dict for a shot."""
        validate_shot_name(shot_name)
        path = self._captions_file(shot_name)
        try:
            if path.exists():
                with path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            logger.exception("Error loading shot captions")
        return {}

    def save_caption(self, shot_name, asset_type, caption):
        """Persist caption text for a given asset type for a shot."""
        validate_shot_name(shot_name)
        if asset_type not in {'first_image', 'last_image', 'video', 'alt_video', 'audio'}:
            raise ValueError('Invalid asset type')
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")
        captions = self.load_captions(shot_name)
        captions[asset_type] = caption or ''
        try:
            with self._captions_file(shot_name).open('w', encoding='utf-8') as f:
                json.dump(captions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save caption: {str(e)}")

    # ------------------------------------------------------------------
    # Meta (display name)
    # ------------------------------------------------------------------

    def load_meta(self, shot_name):
        """Load meta dict for a shot from project path, with fallback to app-level."""
        validate_shot_name(shot_name)
        path = _project_meta_file(self.project_path, shot_name)
        try:
            if path.exists():
                with path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            logger.exception("Error loading project meta")
        # Fallback to app-level meta (for legacy data)
        return load_meta(shot_name)

    def save_display_name(self, shot_name, display_name):
        """Persist display name for a shot in project path."""
        validate_shot_name(shot_name)
        path = _project_meta_file(self.project_path, shot_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('w', encoding='utf-8') as f:
                json.dump({"display_name": display_name}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save display name: {str(e)}")