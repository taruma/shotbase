import logging
from pathlib import Path

from app.services.shot_utils import validate_shot_name

logger = logging.getLogger(__name__)


class PromptStore:
    """CRUD for per-version prompt text files."""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.wip_dir = self.project_path / 'shots' / 'wip'

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _prompt_file_path(self, shot_name, asset_type, version):
        """Return the path to the prompt file for a specific asset version."""
        shot_dir = self.wip_dir / shot_name
        if asset_type in {'image', 'first_image'}:
            base_dir = shot_dir / 'images'
            if asset_type == 'image':
                filename = f'{shot_name}_v{version:03d}_image_prompt.txt'
            else:
                filename = f'{shot_name}_first_v{version:03d}_image_prompt.txt'
        elif asset_type == 'last_image':
            base_dir = shot_dir / 'images'
            filename = f'{shot_name}_last_v{version:03d}_image_prompt.txt'
        elif asset_type == 'video':
            base_dir = shot_dir / 'videos'
            filename = f'{shot_name}_v{version:03d}_video_prompt.txt'
        elif asset_type == 'alt_video':
            base_dir = shot_dir / 'videos'
            filename = f'{shot_name}_alt_v{version:03d}_video_prompt.txt'
        elif asset_type == 'audio':
            base_dir = shot_dir / 'audio'
            filename = f'{shot_name}_audio_v{version:03d}_audio_prompt.txt'
        else:
            raise ValueError('Invalid asset type')
        return base_dir / filename

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load_prompt(self, shot_name, asset_type, version):
        """Load prompt text for a specific asset version."""
        path = self._prompt_file_path(shot_name, asset_type, version)
        if path.exists():
            try:
                with open(path, encoding='utf-8') as f:
                    return f.read().strip()
            except Exception:
                return ''
        # Backward-compatibility: if first_image not found, try legacy 'image'
        if asset_type == 'first_image':
            legacy_path = self._prompt_file_path(shot_name, 'image', version)
            if legacy_path.exists():
                try:
                    with open(legacy_path, encoding='utf-8') as f:
                        return f.read().strip()
                except Exception:
                    return ''
        return ''

    def save_prompt(self, shot_name, asset_type, version, prompt):
        """Save prompt text for a specific asset version."""
        validate_shot_name(shot_name)
        path = self._prompt_file_path(shot_name, asset_type, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(prompt)
        except Exception as e:
            raise ValueError(f"Failed to save prompt: {str(e)}")

    # ------------------------------------------------------------------
    # Version listing
    # ------------------------------------------------------------------

    def get_prompt_versions(self, shot_name, asset_type):
        """Return a sorted list of prompt versions for the given asset."""
        shot_dir = self.wip_dir / shot_name

        patterns = []
        base_dir = None
        if asset_type in {'image', 'first_image'}:
            base_dir = shot_dir / 'images'
            patterns = [
                f'{shot_name}_v*_image_prompt.txt',          # legacy
                f'{shot_name}_first_v*_image_prompt.txt'     # new first
            ]
        elif asset_type == 'last_image':
            base_dir = shot_dir / 'images'
            patterns = [f'{shot_name}_last_v*_image_prompt.txt']
        elif asset_type == 'video':
            base_dir = shot_dir / 'videos'
            patterns = [f'{shot_name}_v*_video_prompt.txt']
        elif asset_type == 'alt_video':
            base_dir = shot_dir / 'videos'
            patterns = [f'{shot_name}_alt_v*_video_prompt.txt']
        elif asset_type == 'audio':
            base_dir = shot_dir / 'audio'
            patterns = [f'{shot_name}_audio_v*_audio_prompt.txt']
        else:
            raise ValueError('Invalid asset type')

        versions = set()
        if base_dir and base_dir.exists():
            for pattern in patterns:
                for f in base_dir.glob(pattern):
                    stem = f.stem
                    if '_v' not in stem:
                        continue
                    try:
                        part = stem.split('_v')[1]
                        ver_str = part.split('_')[0]
                        versions.add(int(ver_str))
                    except (IndexError, ValueError):
                        continue
        return sorted(versions)