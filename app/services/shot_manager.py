import json
import logging
import re
from pathlib import Path

from PIL import Image

from app.config.constants import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_SIZE,
    get_project_thumbnail_cache_dir,
)
from app.services.project_manager import ProjectManager

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


class ShotManager:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.latest_images_dir = self.shots_dir / 'latest_images'
        self.latest_videos_dir = self.shots_dir / 'latest_videos'
        self.legacy_dir = self.project_path / '_legacy'
        self.order_file = self.shots_dir / '.shot_order.json'
        self.archive_file = self.shots_dir / '.archived_shots.json'

        self.latest_audio_dir = self.shots_dir / 'latest_audio'

        self.wip_dir.mkdir(parents=True, exist_ok=True)
        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)
        self.latest_audio_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_cache_dir = get_project_thumbnail_cache_dir(self.project_path)
        self._version_scan_cache = {}  # (shot_name, asset_type) -> max_version

    def _load_shot_order(self):
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

    def _save_shot_order(self, names):
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

    def _load_archived(self):
        """Load archived shot names from JSON file."""
        import json
        try:
            if self.archive_file.exists():
                with self.archive_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
        except Exception:
            logger.exception("Error loading archived shots")
        return set()

    def _save_archived(self, names: set):
        """Persist archived shot names to JSON file."""
        import json
        try:
            self.shots_dir.mkdir(parents=True, exist_ok=True)
            with self.archive_file.open('w', encoding='utf-8') as f:
                json.dump(sorted(list(names)), f)
        except Exception:
            logger.warning("Failed to save archived shots file")

    def archive_shot(self, shot_name, archived: bool):
        """Toggle archived state for a shot and return updated shot info."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")

        names = self._load_archived()
        if archived:
            names.add(shot_name)
        else:
            names.discard(shot_name)
        self._save_archived(names)
        return self.get_shot_info(shot_name)

    @staticmethod
    def _normalize_path(path):
        """Return a POSIX-style absolute path string or ``None``."""
        if not path:
            return None
        return str(Path(path).resolve()).replace("\\", "/")

    def rename_shot(self, old_name, new_name):
        """Rename a shot and all associated files."""
        validate_shot_name(old_name)
        validate_shot_name(new_name)
        old_dir = self.wip_dir / old_name
        new_dir = self.wip_dir / new_name

        if not old_dir.exists():
            raise ValueError(f"Shot {old_name} does not exist")
        if new_dir.exists():
            raise ValueError(f"Shot {new_name} already exists")

        old_dir.rename(new_dir)

        for sub in ["images", "videos", "audio"]:
            d = new_dir / sub
            if d.exists():
                # Legacy pattern (e.g., SH001_v001.png) and new image patterns (e.g., SH001_first_v001.png)
                for f in d.glob(f"{old_name}_v*.*"):
                    f.rename(d / f.name.replace(old_name, new_name, 1))
                for f in d.glob(f"{old_name}_*_v*.*"):
                    f.rename(d / f.name.replace(old_name, new_name, 1))

        for ext in ALLOWED_IMAGE_EXTENSIONS:
            # Legacy single-image final
            src = self.latest_images_dir / f"{old_name}{ext}"
            if src.exists():
                src.rename(self.latest_images_dir / f"{new_name}{ext}")
            # New first/last finals
            src_first = self.latest_images_dir / f"{old_name}_first{ext}"
            if src_first.exists():
                src_first.rename(self.latest_images_dir / f"{new_name}_first{ext}")
            src_last = self.latest_images_dir / f"{old_name}_last{ext}"
            if src_last.exists():
                src_last.rename(self.latest_images_dir / f"{new_name}_last{ext}")
        # Rename image version markers if present
        img_marker = self.latest_images_dir / f"{old_name}.version"
        if img_marker.exists():
            img_marker.rename(self.latest_images_dir / f"{new_name}.version")
        img_marker_first = self.latest_images_dir / f"{old_name}_first.version"
        if img_marker_first.exists():
            img_marker_first.rename(self.latest_images_dir / f"{new_name}_first.version")
        img_marker_last = self.latest_images_dir / f"{old_name}_last.version"
        if img_marker_last.exists():
            img_marker_last.rename(self.latest_images_dir / f"{new_name}_last.version")

        for ext in ALLOWED_VIDEO_EXTENSIONS:
            src = self.latest_videos_dir / f"{old_name}{ext}"
            if src.exists():
                src.rename(self.latest_videos_dir / f"{new_name}{ext}")
            alt_src = self.latest_videos_dir / f"{old_name}_alt{ext}"
            if alt_src.exists():
                alt_src.rename(self.latest_videos_dir / f"{new_name}_alt{ext}")
        # Rename video version markers if present
        vid_marker = self.latest_videos_dir / f"{old_name}.version"
        if vid_marker.exists():
            vid_marker.rename(self.latest_videos_dir / f"{new_name}.version")
        alt_vid_marker = self.latest_videos_dir / f"{old_name}_alt.version"
        if alt_vid_marker.exists():
            alt_vid_marker.rename(self.latest_videos_dir / f"{new_name}_alt.version")

        # Rename audio files and markers
        for ext in ALLOWED_AUDIO_EXTENSIONS:
            audio_src = self.latest_audio_dir / f"{old_name}_audio{ext}"
            if audio_src.exists():
                audio_src.rename(self.latest_audio_dir / f"{new_name}_audio{ext}")
        audio_marker = self.latest_audio_dir / f"{old_name}_audio.version"
        if audio_marker.exists():
            audio_marker.rename(self.latest_audio_dir / f"{new_name}_audio.version")

        if self.thumbnail_cache_dir.exists():
            for thumb in self.thumbnail_cache_dir.glob(f"{old_name}_*_thumb.jpg"):
                thumb.rename(self.thumbnail_cache_dir / thumb.name.replace(old_name, new_name, 1))
            for vthumb in self.thumbnail_cache_dir.glob(f"{old_name}_*_vthumb.jpg"):
                vthumb.rename(self.thumbnail_cache_dir / vthumb.name.replace(old_name, new_name, 1))

        # Preserve archived state across rename
        try:
            names = self._load_archived()
            if old_name in names:
                names.discard(old_name)
                names.add(new_name)
                self._save_archived(names)
        except Exception:
            logger.exception("Error updating archived state during rename")

        return self.get_shot_info(new_name)

    def create_shot_structure(self, shot_name):
        """Create folder structure for a shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name
        shot_dir.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        (shot_dir / 'images').mkdir(exist_ok=True)
        (shot_dir / 'videos').mkdir(exist_ok=True)
        (shot_dir / 'audio').mkdir(exist_ok=True)

        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)
        self.latest_audio_dir.mkdir(parents=True, exist_ok=True)

        return shot_dir

    def get_next_shot_number(self):
        """Get next available shot number, filling gaps first."""
        existing_shots = []
        if self.wip_dir.exists():
            for shot_dir in self.wip_dir.iterdir():
                if shot_dir.is_dir() and shot_dir.name.startswith('SH'):
                    try:
                        # Only consider top-level shots (no underscores)
                        if '_' not in shot_dir.name:
                            existing_shots.append(int(shot_dir.name[2:]))
                    except ValueError:
                        continue
        
        if not existing_shots:
            return 1
        
        # Find first available gap starting from 1
        for i in range(1, 1000):
            if i not in existing_shots:
                return i
        
        # If no gaps found (all 999 numbers used), raise error
        raise ValueError("No available shot numbers (maximum 999 reached)")

    def get_shots(self):
        """Get all shots in the project."""
        if not self.wip_dir.exists():
            return []

        shot_dirs = [d for d in self.wip_dir.iterdir() if d.is_dir() and d.name.startswith('SH')]
        
        ordered_names = self._load_shot_order()
        if ordered_names:
            dir_map = {d.name: d for d in shot_dirs}
            ordered_dirs = [dir_map[name] for name in ordered_names if name in dir_map]
            existing_ordered_names = {d.name for d in ordered_dirs}
            new_dirs = [d for d in shot_dirs if d.name not in existing_ordered_names]
            shot_dirs = ordered_dirs + sorted(new_dirs, key=lambda d: d.name)
        else:
            shot_dirs = sorted(shot_dirs, key=lambda d: d.name)

        # Cache archived set once so get_shot_info() doesn't re-read from disk per shot
        archived_names = self._load_archived()
        shots = [self.get_shot_info(shot_dir.name, archived_names=archived_names) for shot_dir in shot_dirs]
        return shots

    def save_shot_order(self, shot_order):
        """Save the order of shots."""
        if not isinstance(shot_order, list):
            raise ValueError('Shot order must be a list')
        self._save_shot_order(shot_order)

    def create_shot_between(self, after_shot=None):
        """Create a new shot between existing shots.

        Parameters
        ----------
        after_shot : str or None
            Name of the shot after which the new shot should be inserted. If
            ``None`` the new shot is inserted before the first existing one.

        Returns
        -------
        dict
            Shot information for the newly created shot.
        """

        if after_shot:
            validate_shot_name(after_shot)

        existing = [s["name"] for s in self.get_shots()]

        if not after_shot:
            # Insert before the first shot using gap-filling
            shot_name = f"SH{self.get_next_shot_number():03d}"
        else:
            base_shot = after_shot.split('_')[0]

            if '_' in after_shot:
                # After a sub-shot: simply append a new sub-shot for the same base
                shot_name = self._create_subshot_name(base_shot, existing)
            else:
                # For top-level shots, use gap-filling
                shot_name = f"SH{self.get_next_shot_number():03d}"

        validate_shot_name(shot_name)
        if shot_name in existing:
            raise ValueError(f"Shot {shot_name} already exists")

        self.create_shot_structure(shot_name)

        order_names = self._load_shot_order()
        if order_names:
            existing_order_set = set(order_names)
            for name in existing:
                if name not in existing_order_set:
                    order_names.append(name)
        else:
            order_names = existing[:]

        order_names = [name for name in order_names if name != shot_name]

        if not after_shot:
            order_names.insert(0, shot_name)
        else:
            try:
                idx = order_names.index(after_shot)
                order_names.insert(idx + 1, shot_name)
            except ValueError:
                order_names.append(shot_name)

        if not order_names:
            order_names = [shot_name]

        self._save_shot_order(order_names)

        return self.get_shot_info(shot_name)

    def _create_subshot_name(self, base_shot, existing):
        """Return a new sub-shot name under ``base_shot``.

        ``base_shot`` should be a top-level shot name (no underscore).  The new
        name will use a three-digit sub-shot number starting at ``050`` and
        increasing in steps of 10.  Only a single underscore level is allowed.
        """

        if '_' in base_shot:
            raise ValueError('Nested sub-shots are not supported')

        prefix = base_shot + '_'
        sub_numbers = []
        for name in existing:
            if name.startswith(prefix) and '_' not in name[len(prefix):]:
                try:
                    sub_numbers.append(int(name.split('_')[1]))
                except ValueError:
                    continue

        next_num = (max(sub_numbers) + 10) if sub_numbers else 50
        if next_num > 999:
            raise ValueError('No available sub-shot numbers')

        return f"{base_shot}_{next_num:03d}"

    def load_meta(self, shot_name):
        """Load meta dict for a shot from project path, with fallback to app-level."""
        validate_shot_name(shot_name)
        project_path = getattr(self, 'project_path', None)
        if project_path:
            path = _project_meta_file(project_path, shot_name)
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
        project_path = getattr(self, 'project_path', None)
        if not project_path:
            raise ValueError("Project path not set")
        path = _project_meta_file(project_path, shot_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('w', encoding='utf-8') as f:
                json.dump({"display_name": display_name}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save display name: {str(e)}")

    @staticmethod
    def _thumbnail_url(asset_path, shot_name, is_video=False):
        """Compute thumbnail URL without generating the file (lazy).

        Returns the URL path that the thumbnail *would* have, based solely on
        the source asset stem and shot name.  Actual generation is deferred to
        the first request through ``/api/shots/thumbnail/``.
        """
        if not asset_path:
            return None
        p = Path(asset_path)
        suffix = "_vthumb" if is_video else "_thumb"
        return f"/api/shots/thumbnail/{shot_name}_{p.stem}{suffix}.jpg"

    def get_shot_info(self, shot_name, archived_names=None):
        """Get information about a specific shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name

        # Load notes
        notes = ''
        notes_file = shot_dir / 'notes.txt'
        if notes_file.exists():
            try:
                with open(notes_file, encoding='utf-8') as f:
                    notes = f.read().strip()
            except Exception:
                logger.exception("Error loading shot notes")


        # First/Last images
        # New naming for first frame
        first_image_path, first_max_version = self._get_latest_asset(
            self.latest_images_dir, shot_dir / 'images',
            f'{shot_name}_first', ALLOWED_IMAGE_EXTENSIONS
        )
        # Only fall back to legacy naming if modern '_first' naming found nothing
        if not first_image_path and first_max_version == 0:
            legacy_image_path, legacy_max_version = self._get_latest_asset(
                self.latest_images_dir, shot_dir / 'images',
                shot_name, ALLOWED_IMAGE_EXTENSIONS
            )
            if legacy_image_path or legacy_max_version > 0:
                first_image_path = legacy_image_path
                first_max_version = legacy_max_version

        # New naming for last frame
        last_image_path, last_max_version = self._get_latest_asset(
            self.latest_images_dir, shot_dir / 'images',
            f'{shot_name}_last', ALLOWED_IMAGE_EXTENSIONS
        )

        # Detect existing versions if max_version seems inaccurate (cached per ShotManager instance)
        if first_max_version == 0:
            cache_key = (shot_name, 'first_image')
            if cache_key in self._version_scan_cache:
                detected_first_versions = self._version_scan_cache[cache_key]
            else:
                detected_first_versions = self._detect_existing_versions(shot_name, 'first_image')
                self._version_scan_cache[cache_key] = detected_first_versions
            first_max_version = max(first_max_version, detected_first_versions)

        if last_max_version == 0:
            cache_key = (shot_name, 'last_image')
            if cache_key in self._version_scan_cache:
                detected_last_versions = self._version_scan_cache[cache_key]
            else:
                detected_last_versions = self._detect_existing_versions(shot_name, 'last_image')
                self._version_scan_cache[cache_key] = detected_last_versions
            last_max_version = max(last_max_version, detected_last_versions)

        first_image_path = self._normalize_path(first_image_path)
        last_image_path = self._normalize_path(last_image_path)

        current_first_version = self.get_current_version(shot_name, 'first_image', first_max_version)
        first_prompt = self.load_prompt(shot_name, 'first_image', current_first_version) if current_first_version > 0 else ''

        current_last_version = self.get_current_version(shot_name, 'last_image', last_max_version)
        last_prompt = self.load_prompt(shot_name, 'last_image', current_last_version) if current_last_version > 0 else ''

        # Latest video
        latest_video, max_video_version = self._get_latest_asset(
            self.latest_videos_dir, shot_dir / 'videos',
            shot_name, ALLOWED_VIDEO_EXTENSIONS
        )
        
        # Detect existing video versions if max_version seems inaccurate (cached per ShotManager instance)
        if max_video_version == 0:
            cache_key = (shot_name, 'video')
            if cache_key in self._version_scan_cache:
                detected_video_versions = self._version_scan_cache[cache_key]
            else:
                detected_video_versions = self._detect_existing_versions(shot_name, 'video')
                self._version_scan_cache[cache_key] = detected_video_versions
            max_video_version = max(max_video_version, detected_video_versions)
            
        latest_video = self._normalize_path(latest_video)
        current_video_version = self.get_current_version(shot_name, 'video', max_video_version)
        video_prompt = ''
        if current_video_version > 0:
            video_prompt = self.load_prompt(shot_name, 'video', current_video_version)

        # Alt video
        latest_alt_video, max_alt_video_version = self._get_latest_asset(
            self.latest_videos_dir, shot_dir / 'videos',
            f'{shot_name}_alt', ALLOWED_VIDEO_EXTENSIONS
        )
        
        if max_alt_video_version == 0:
            cache_key = (shot_name, 'alt_video')
            if cache_key in self._version_scan_cache:
                detected_alt_video_versions = self._version_scan_cache[cache_key]
            else:
                detected_alt_video_versions = self._detect_existing_versions(shot_name, 'alt_video')
                self._version_scan_cache[cache_key] = detected_alt_video_versions
            max_alt_video_version = max(max_alt_video_version, detected_alt_video_versions)
            
        latest_alt_video = self._normalize_path(latest_alt_video)
        current_alt_video_version = self.get_current_version(shot_name, 'alt_video', max_alt_video_version)
        alt_video_prompt = ''
        if current_alt_video_version > 0:
            alt_video_prompt = self.load_prompt(shot_name, 'alt_video', current_alt_video_version)

        # Thumbnails — lazy: compute URL path only; generation deferred to first browser request
        first_thumb = self._thumbnail_url(first_image_path, shot_name, is_video=False) if first_image_path else None
        last_thumb = self._thumbnail_url(last_image_path, shot_name, is_video=False) if last_image_path else None
        video_thumb = self._thumbnail_url(latest_video, shot_name, is_video=True) if latest_video else None
        alt_video_thumb = self._thumbnail_url(latest_alt_video, f"{shot_name}_alt", is_video=True) if latest_alt_video else None

        # Audio
        latest_audio, max_audio_version = self._get_latest_asset(
            self.latest_audio_dir, shot_dir / 'audio',
            f'{shot_name}_audio', ALLOWED_AUDIO_EXTENSIONS
        )

        if max_audio_version == 0:
            cache_key = (shot_name, 'audio')
            if cache_key in self._version_scan_cache:
                detected_audio_versions = self._version_scan_cache[cache_key]
            else:
                detected_audio_versions = self._detect_existing_versions(shot_name, 'audio')
                self._version_scan_cache[cache_key] = detected_audio_versions
            max_audio_version = max(max_audio_version, detected_audio_versions)

        latest_audio = self._normalize_path(latest_audio)
        current_audio_version = self.get_current_version(shot_name, 'audio', max_audio_version)
        audio_prompt = ''
        if current_audio_version > 0:
            audio_prompt = self.load_prompt(shot_name, 'audio', current_audio_version)

        captions = self.load_captions(shot_name)

        # Compose response with backward-compatible 'image' alias pointing to first_image
        first_image_dict = {
            'file': first_image_path,
            'current_version': current_first_version,
            'max_version': first_max_version,
            'thumbnail': first_thumb,
            'prompt': first_prompt,
            'caption': captions.get('first_image', ''),
        }
        last_image_dict = {
            'file': last_image_path,
            'current_version': current_last_version,
            'max_version': last_max_version,
            'thumbnail': last_thumb,
            'prompt': last_prompt,
            'caption': captions.get('last_image', ''),
        }

        meta = self.load_meta(shot_name)
        return {
            'name': shot_name,
            'display_name': meta.get('display_name', ''),
            'notes': notes,
            'first_image': first_image_dict,
            'last_image': last_image_dict,
            'image': first_image_dict,  # backward compatibility
            'video': {
                'file': latest_video,
                'current_version': current_video_version,
                'max_version': max_video_version,
                'thumbnail': video_thumb,
                'prompt': video_prompt,
                'caption': captions.get('video', ''),
            },
            'alt_video': {
                'file': latest_alt_video,
                'current_version': current_alt_video_version,
                'max_version': max_alt_video_version,
                'thumbnail': alt_video_thumb,
                'prompt': alt_video_prompt,
                'caption': captions.get('alt_video', ''),
            },
            'audio': {
                'file': latest_audio,
                'current_version': current_audio_version,
                'max_version': max_audio_version,
                'thumbnail': None,  # Audio has no visual thumbnail
                'prompt': audio_prompt,
                'caption': captions.get('audio', ''),
            },
            'archived': (shot_name in (archived_names if archived_names is not None else self._load_archived()))
        }


    def _get_latest_asset(self, final_dir, wip_dir, shot_name, extensions):
        """Helper for finding the latest final or highest versioned WIP asset."""
        latest_final = None
        if final_dir.exists():
            for ext in extensions:
                candidate = final_dir / f'{shot_name}{ext}'
                if candidate.exists():
                    latest_final = str(candidate)
                    break

        version = 0
        if wip_dir.exists():
            wip_files = []
            for ext in extensions:
                wip_files.extend(wip_dir.glob(f'{shot_name}_v*{ext}'))

            versions = []
            for f in wip_files:
                try:
                    version_str = f.stem.split('_v')[1]
                    versions.append(int(version_str))
                except (IndexError, ValueError):
                    continue

            if versions:
                version = max(versions)

        return latest_final, version

    def _detect_existing_versions(self, shot_name, asset_type):
        """Detect existing versions by scanning the file system for a specific asset type."""
        shot_dir = self.wip_dir / shot_name
        
        if asset_type == 'first_image':
            wip_dir = shot_dir / 'images'
            patterns = [
                f'{shot_name}_first_v*.*',  # new naming
                f'{shot_name}_v*.*'         # legacy naming (for first image)
            ]
        elif asset_type == 'last_image':
            wip_dir = shot_dir / 'images'
            patterns = [f'{shot_name}_last_v*.*']
        elif asset_type == 'video':
            wip_dir = shot_dir / 'videos'
            patterns = [f'{shot_name}_v*.*']
        elif asset_type == 'alt_video':
            wip_dir = shot_dir / 'videos'
            patterns = [f'{shot_name}_alt_v*.*']
        elif asset_type == 'audio':
            wip_dir = shot_dir / 'audio'
            patterns = [f'{shot_name}_audio_v*.*']
        else:
            return 0  # Unsupported asset type

        if not wip_dir.exists():
            return 0

        versions = set()
        for pattern in patterns:
            for f in wip_dir.glob(pattern):
                try:
                    # Extract version number from filename
                    stem = f.stem
                    if '_v' not in stem:
                        continue
                    version_str = stem.split('_v')[1]
                    # Handle cases where there might be additional underscores
                    version_num = int(version_str.split('_')[0])
                    versions.add(version_num)
                except (IndexError, ValueError):
                    continue

        return max(versions) if versions else 0

    def _version_marker_path(self, asset_type, shot_name):
        if asset_type == 'image':
            # Legacy single-image marker (pre-split)
            return self.latest_images_dir / f"{shot_name}.version"
        elif asset_type == 'first_image':
            return self.latest_images_dir / f"{shot_name}_first.version"
        elif asset_type == 'last_image':
            return self.latest_images_dir / f"{shot_name}_last.version"
        elif asset_type == 'video':
            return self.latest_videos_dir / f"{shot_name}.version"
        elif asset_type == 'alt_video':
            return self.latest_videos_dir / f"{shot_name}_alt.version"
        elif asset_type == 'audio':
            return self.latest_audio_dir / f"{shot_name}_audio.version"
        else:
            raise ValueError('Invalid asset type')

    def get_current_version(self, shot_name, asset_type, max_version):
        """Read the currently promoted version from a marker file. Fallback to max_version."""
        def _read_marker(p):
            try:
                if p.exists():
                    v = int(p.read_text(encoding='utf-8').strip())
                    if max_version == 0:
                        return v
                    if 1 <= v <= max_version:
                        return v
            except Exception:
                logger.exception("Error reading version marker")
            return None

        marker = self._version_marker_path(asset_type, shot_name)
        v = _read_marker(marker)
        if v is not None:
            return v

        # Backward-compatibility: first_image falls back to legacy 'image' marker
        if asset_type == 'first_image':
            legacy_marker = self._version_marker_path('image', shot_name)
            v = _read_marker(legacy_marker)
            if v is not None:
                return v

        return max_version

    def set_current_version(self, shot_name, asset_type, version):
        """Persist the currently promoted version to a marker file."""
        marker = self._version_marker_path(asset_type, shot_name)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(int(version)), encoding='utf-8')

    def promote_asset(self, shot_name, asset_type, version):
        """Promote a specific WIP version to be the current final for image variants/video."""
        validate_shot_name(shot_name)
        if asset_type not in {'image', 'first_image', 'last_image', 'video', 'alt_video', 'audio'}:
            raise ValueError('Invalid asset type')

        shot_dir = self.wip_dir / shot_name

        import shutil as _shutil

        if asset_type in {'image', 'first_image', 'last_image'}:
            slot = 'first' if asset_type in {'image', 'first_image'} else 'last'
            wip_dir = shot_dir / 'images'
            if not wip_dir.exists():
                raise ValueError(f"No image WIP directory for shot {shot_name}")

            # Find source: prefer new naming, then legacy (for first slot)
            src = None
            for ext in ALLOWED_IMAGE_EXTENSIONS:
                candidate = wip_dir / f'{shot_name}_{slot}_v{int(version):03d}{ext}'
                if candidate.exists():
                    src = candidate
                    break
            if src is None and slot == 'first':
                for ext in ALLOWED_IMAGE_EXTENSIONS:
                    legacy = wip_dir / f'{shot_name}_v{int(version):03d}{ext}'
                    if legacy.exists():
                        src = legacy
                        break
            if src is None:
                raise ValueError(f"Version v{int(version):03d} not found for {shot_name} {asset_type}")

            final_dir = self.latest_images_dir
            final_dir.mkdir(parents=True, exist_ok=True)

            # Remove existing finals for this slot
            for existing in final_dir.glob(f"{shot_name}_{slot}.*"):
                try:
                    existing.unlink()
                except Exception:
                    logger.exception("Error unlinking existing final image")

            final_path = final_dir / f"{shot_name}_{slot}{src.suffix}"
            _shutil.copy2(str(src), str(final_path))

            # Update marker and regenerate thumbnail
            self.set_current_version(shot_name, 'first_image' if slot == 'first' else 'last_image', int(version))
            try:
                final_stem = Path(final_path).stem
                thumb_filename = f"{shot_name}_{final_stem}_thumb.jpg"
                old_thumb = self.thumbnail_cache_dir / thumb_filename
                if old_thumb.exists():
                    old_thumb.unlink()
            except Exception:
                logger.exception("Error unlinking old image thumbnail")

            _ = self.get_thumbnail_path(final_path, shot_name)
            return self._normalize_path(final_path)

        # Audio
        if asset_type == 'audio':
            return self.promote_audio_asset(shot_name, int(version))

        # Video & Alt Video
        wip_dir = shot_dir / 'videos'
        if not wip_dir.exists():
            raise ValueError(f"No video WIP directory for shot {shot_name}")

        is_alt = (asset_type == 'alt_video')
        base_prefix = f'{shot_name}_alt' if is_alt else shot_name

        src = None
        for ext in ALLOWED_VIDEO_EXTENSIONS:
            candidate = wip_dir / f'{base_prefix}_v{int(version):03d}{ext}'
            if candidate.exists():
                src = candidate
                break
        if not src:
            raise ValueError(f"Version v{int(version):03d} not found for {shot_name} {asset_type}")

        final_dir = self.latest_videos_dir
        final_dir.mkdir(parents=True, exist_ok=True)

        for existing in final_dir.glob(f"{base_prefix}.*"):
            try:
                existing.unlink()
            except Exception:
                logger.exception("Error unlinking existing final video")

        final_path = final_dir / f"{base_prefix}{src.suffix}"
        _shutil.copy2(str(src), str(final_path))

        self.set_current_version(shot_name, asset_type, int(version))
        try:
            final_stem = Path(final_path).stem
            thumb_filename = f"{base_prefix}_{final_stem}_vthumb.jpg"
            old_thumb = self.thumbnail_cache_dir / thumb_filename
            if old_thumb.exists():
                old_thumb.unlink()
        except Exception:
            logger.exception("Error unlinking old video thumbnail")

        _ = self.get_video_thumbnail_path(final_path, base_prefix)
        return self._normalize_path(final_path)

    def promote_audio_asset(self, shot_name, version):
        """Promote a specific audio WIP version to be the current final."""
        import shutil as _shutil

        shot_dir = self.wip_dir / shot_name
        wip_dir = shot_dir / 'audio'
        if not wip_dir.exists():
            raise ValueError(f"No audio WIP directory for shot {shot_name}")

        base_prefix = f'{shot_name}_audio'

        src = None
        for ext in ALLOWED_AUDIO_EXTENSIONS:
            candidate = wip_dir / f'{base_prefix}_v{int(version):03d}{ext}'
            if candidate.exists():
                src = candidate
                break
        if not src:
            raise ValueError(f"Version v{int(version):03d} not found for {shot_name} audio")

        final_dir = self.latest_audio_dir
        final_dir.mkdir(parents=True, exist_ok=True)

        for existing in final_dir.glob(f"{base_prefix}.*"):
            try:
                existing.unlink()
            except Exception:
                logger.exception("Error unlinking existing final audio")

        final_path = final_dir / f"{base_prefix}{src.suffix}"
        _shutil.copy2(str(src), str(final_path))

        self.set_current_version(shot_name, 'audio', int(version))
        return self._normalize_path(final_path)

    def save_shot_notes(self, shot_name, notes):
        """Save notes for a shot."""
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

    def _captions_file(self, shot_name):
        """Return path to the captions JSON for a shot."""
        return (self.wip_dir / shot_name) / 'captions.json'

    def load_captions(self, shot_name):
        """Load captions dict for a shot."""
        validate_shot_name(shot_name)
        path = self._captions_file(shot_name)
        try:
            import json
            if path.exists():
                with path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            logger.exception("Error loading shot captions")
        return {}

    def save_caption(self, shot_name, asset_type, caption):
        """Persist caption text for given asset type for a shot."""
        validate_shot_name(shot_name)
        if asset_type not in {'first_image', 'last_image', 'video', 'alt_video', 'audio'}:
            raise ValueError('Invalid asset type')
        shot_dir = self.wip_dir / shot_name
        if not shot_dir.exists():
            raise ValueError(f"Shot {shot_name} does not exist")
        captions = self.load_captions(shot_name)
        captions[asset_type] = caption or ''
        try:
            import json
            with self._captions_file(shot_name).open('w', encoding='utf-8') as f:
                json.dump(captions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save caption: {str(e)}")

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

    def load_prompt(self, shot_name, asset_type, version):
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
        """Save prompt for a specific asset version."""
        validate_shot_name(shot_name)
        path = self._prompt_file_path(shot_name, asset_type, version)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(prompt)
        except Exception as e:
            raise ValueError(f"Failed to save prompt: {str(e)}")

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

    def _generate_thumbnail_on_demand(self, thumb_filename):
        """Ensure a thumbnail exists and is fresh.

        Called by ``serve_thumbnail`` to generate or refresh the thumbnail
        for the given filename.  Parses the filename to reconstruct the
        source asset path, then delegates to ``get_thumbnail_path`` or
        ``get_video_thumbnail_path``.  Those methods already compare
        source-vs-thumb mtimes internally, so stale thumbs for replaced
        assets are automatically regenerated.
        """
        stem = Path(thumb_filename).stem  # e.g. "SH001_SH001_first_thumb" or "SH001_SH001_vthumb"

        is_video = stem.endswith("_vthumb")
        if is_video:
            stem = stem[:-len("_vthumb")]   # "SH001_SH001"
        else:
            if stem.endswith("_thumb"):
                stem = stem[:-len("_thumb")]  # "SH001_SH001_first"

        # stem is now "{shot_name}_{asset_stem}" where asset_stem may
        # be just the shot name (promoted video / legacy image), or
        # "{shot_name}_first", "{shot_name}_last", "{shot_name}_alt", etc.
        shot_name = stem.split("_", 1)[0]

        # Locate the source file by scanning the project directories
        shot_dir = self.wip_dir / shot_name

        # Try in latest dirs first, then WIP
        search_dirs = []
        if is_video:
            search_dirs = [
                self.latest_videos_dir,
                shot_dir / "videos",
            ]
        else:
            search_dirs = [
                self.latest_images_dir,
                shot_dir / "images",
            ]

        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.iterdir():
                if not f.is_file():
                    continue
                expected_thumb = f"{shot_name}_{f.stem}_vthumb.jpg" if is_video else f"{shot_name}_{f.stem}_thumb.jpg"
                if expected_thumb == thumb_filename:
                    if is_video:
                        self.get_video_thumbnail_path(f, shot_name)
                    else:
                        self.get_thumbnail_path(f, shot_name)
                    return

    def get_thumbnail_path(self, image_path, shot_name):
        """Return (and create if necessary) the thumbnail for an image."""
        if not image_path:
            return None

        image_path = Path(image_path)
        thumb_filename = f"{shot_name}_{image_path.stem}_thumb.jpg"
        thumb_path = self.thumbnail_cache_dir / thumb_filename

        try:
            if thumb_path.exists() and thumb_path.stat().st_mtime >= image_path.stat().st_mtime:
                return f"/api/shots/thumbnail/{thumb_filename}"
        except Exception:
            logger.exception("Error checking thumbnail timestamp")
        try:
            self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
            with Image.open(image_path) as img:
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (64, 64, 64))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = background
                img.save(str(thumb_path), "JPEG", quality=85)
        except Exception as e:
            logger.warning("Error creating thumbnail: %s", e)
            return None

        return f"/api/shots/thumbnail/{thumb_filename}"

    def get_video_thumbnail_path(self, video_path, shot_name):
        """Return (and create if necessary) the thumbnail for a video."""
        if not video_path:
            return None

        import shutil as _shutil
        import subprocess

        video_path = Path(video_path)
        if not video_path.exists():
            logger.warning("Video file does not exist: %s", video_path)
            return None
        thumb_filename = f"{shot_name}_{video_path.stem}_vthumb.jpg"
        thumb_path = self.thumbnail_cache_dir / thumb_filename

        if thumb_path.exists() and thumb_path.stat().st_mtime >= video_path.stat().st_mtime:
            return f"/api/shots/thumbnail/{thumb_filename}"
        if not thumb_path.exists():
            ffmpeg = _shutil.which("ffmpeg")
            if not ffmpeg:
                logger.warning("ffmpeg not found; skipping video thumbnail for %s", video_path)
                return None
            try:
                self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = thumb_path.with_suffix(".tmp.jpg")
                cmd = [ffmpeg, "-y", "-i", str(video_path), "-frames:v", "1", str(tmp_path)]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)  # noqa: S603
                with Image.open(tmp_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    if img.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", img.size, (64, 64, 64))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                        img = background
                    img.save(str(thumb_path), "JPEG", quality=85)
                tmp_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Error creating video thumbnail: %s", e)
                return None

        return f"/api/shots/thumbnail/{thumb_filename}"

    def export_latest_assets(self, export_name=None, export_type='all', include_display_in_filename=True, include_metadata=True, export_format='md'):
        """Export latest assets for non-archived shots in custom order."""
        import re
        import shutil
        from datetime import datetime

        # Get non-archived shots in order
        non_archived_shots = [s for s in self.get_shots() if not s['archived']]
        if not non_archived_shots:
            raise ValueError("No non-archived shots found")

        # Load project information
        project_manager = ProjectManager()
        project_info = project_manager.load_project_info(self.project_path)

        # Create export directory
        exports_root = self.project_path / 'exports'
        exports_root.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir_name = export_name or f'export_{timestamp}'
        export_dir = exports_root / export_dir_name
        export_dir.mkdir(exist_ok=True)

        # Sanitize filename helper
        def sanitize_filename(name):
            return re.sub(r'[<>:\"/\\|?*]', '_', str(name))[:50] or ''

        # Process each shot in order (copy asset files)
        for order, shot in enumerate(non_archived_shots, start=1):
            shot_name = shot['name']
            display_name = shot['display_name'] or ''
            display_suffix = f"_{sanitize_filename(display_name)}" if include_display_in_filename and display_name else ''

            # Get shot info
            info = self.get_shot_info(shot_name)

            # Images
            if 'images' in export_type or export_type == 'all':
                images_dir = export_dir / 'images'
                images_dir.mkdir(exist_ok=True)

                # First image
                if info['first_image']['file']:
                    src = Path(info['first_image']['file'])
                    if src.exists():
                        ext = src.suffix
                        dst = images_dir / f"{order:03d}_{shot_name}{display_suffix}_first{ext}"
                        shutil.copy2(src, dst)

                # Last image
                if info['last_image']['file']:
                    src = Path(info['last_image']['file'])
                    if src.exists():
                        ext = src.suffix
                        dst = images_dir / f"{order:03d}_{shot_name}{display_suffix}_last{ext}"
                        shutil.copy2(src, dst)

            # Videos
            if 'videos' in export_type or export_type == 'all':
                videos_dir = export_dir / 'videos'
                videos_dir.mkdir(exist_ok=True)

                if info['video']['file']:
                    src = Path(info['video']['file'])
                    if src.exists():
                        ext = src.suffix
                        dst = videos_dir / f"{order:03d}_{shot_name}{display_suffix}{ext}"
                        shutil.copy2(src, dst)

                if info['alt_video']['file']:
                    src = Path(info['alt_video']['file'])
                    if src.exists():
                        ext = src.suffix
                        dst = videos_dir / f"{order:03d}_{shot_name}{display_suffix}_alt{ext}"
                        shutil.copy2(src, dst)

            # Audio
            if 'audio' in export_type or export_type == 'all':
                audio_dir = export_dir / 'audio'
                audio_dir.mkdir(exist_ok=True)

                if info['audio']['file']:
                    src = Path(info['audio']['file'])
                    if src.exists():
                        ext = src.suffix
                        dst = audio_dir / f"{order:03d}_{shot_name}{display_suffix}_audio{ext}"
                        shutil.copy2(src, dst)

        # Generate metadata if requested
        if include_metadata:
            if export_format == 'html':
                self._write_html_export(export_dir, non_archived_shots, project_info, export_type, timestamp)
            else:
                self._write_md_export(export_dir, non_archived_shots, project_info, export_type, timestamp)

        return str(export_dir)

    def _write_md_export(self, export_dir, non_archived_shots, project_info, export_type, timestamp):
        """Write markdown export summary."""
        # Collect data for tables and notes
        first_data = []
        last_data = []
        video_data = []
        alt_video_data = []
        audio_data = []
        notes_list = []

        for order, shot in enumerate(non_archived_shots, start=1):
            shot_name = shot['name']
            display_name = shot['display_name'] or ''
            info = self.get_shot_info(shot_name)

            # First Frame
            if ('images' in export_type or export_type == 'all') and (info['first_image']['caption'] or info['first_image']['prompt']):
                first_data.append((order, shot_name, display_name, info['first_image']['caption'], info['first_image']['prompt']))

            # Last Frame
            if ('images' in export_type or export_type == 'all') and (info['last_image']['caption'] or info['last_image']['prompt']):
                last_data.append((order, shot_name, display_name, info['last_image']['caption'], info['last_image']['prompt']))

            # Video
            if ('videos' in export_type or export_type == 'all') and (info['video']['caption'] or info['video']['prompt']):
                video_data.append((order, shot_name, display_name, info['video']['caption'], info['video']['prompt']))

            # Alt Video
            if ('videos' in export_type or export_type == 'all') and (info['alt_video']['caption'] or info['alt_video']['prompt']):
                alt_video_data.append((order, shot_name, display_name, info['alt_video']['caption'], info['alt_video']['prompt']))

            # Audio
            if ('audio' in export_type or export_type == 'all') and (info['audio']['caption'] or info['audio']['prompt']):
                audio_data.append((order, shot_name, display_name, info['audio']['caption'], info['audio']['prompt']))

            # Notes
            if info['notes'].strip():
                notes_list.append((order, shot_name, display_name, info['notes']))

        # Build MD content
        md_lines = [
            f"# {project_info.get('title', self.project_path.name)}",
            "",
            "## Project Information",
        ]

        # Add bullet points for non-empty project fields
        if project_info.get('short_description'):
            md_lines.append(f"- **Short Description:** {project_info.get('short_description')}")

        if project_info.get('notes'):
            md_lines.append(f"- **Project Notes:** {project_info.get('notes')}")

        if project_info.get('tags'):
            md_lines.append(f"- **Tags:** {', '.join(project_info.get('tags'))}")

        md_lines.extend([
            "",
            f"**Export Date:** {timestamp}",
            f"**Export Type:** {export_type}",
            ""
        ])

        # First Frame table
        if first_data:
            md_lines.extend([
                "## First Frame",
                "| Order | Shot Name | Display Name | Captions | Prompts |",
                "|-------|-----------|--------------|----------|---------|"
            ])
            for order, name, display_name, caption, prompt in first_data:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {caption.replace('|', '\\|').replace('\n', '<br>')} | {prompt.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Last Frame table
        if last_data:
            md_lines.extend([
                "## Last Frame",
                "| Order | Shot Name | Display Name | Captions | Prompts |",
                "|-------|-----------|--------------|----------|---------|"
            ])
            for order, name, display_name, caption, prompt in last_data:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {caption.replace('|', '\\|').replace('\n', '<br>')} | {prompt.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Video table
        if video_data:
            md_lines.extend([
                "## Video",
                "| Order | Shot Name | Display Name | Captions | Prompts |",
                "|-------|-----------|--------------|----------|---------|"
            ])
            for order, name, display_name, caption, prompt in video_data:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {caption.replace('|', '\\|').replace('\n', '<br>')} | {prompt.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Alt Video table
        if alt_video_data:
            md_lines.extend([
                "## Alt Video",
                "| Order | Shot Name | Display Name | Captions | Prompts |",
                "|-------|-----------|--------------|----------|---------|"
            ])
            for order, name, display_name, caption, prompt in alt_video_data:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {caption.replace('|', '\\|').replace('\n', '<br>')} | {prompt.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Audio table
        if audio_data:
            md_lines.extend([
                "## Audio",
                "| Order | Shot Name | Display Name | Captions | Prompts |",
                "|-------|-----------|--------------|----------|---------|"
            ])
            for order, name, display_name, caption, prompt in audio_data:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {caption.replace('|', '\\|').replace('\n', '<br>')} | {prompt.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Notes table
        if notes_list:
            md_lines.extend([
                "## Notes",
                "| Order | Shot Name | Display Name | Notes |",
                "|-------|-----------|--------------|-------|"
            ])
            for order, name, display_name, notes in notes_list:
                md_lines.append(f"| {order:03d} | {name} | {display_name} | {notes.replace('|', '\\|').replace('\n', '<br>')} |")
            md_lines.append("")

        # Write MD file
        md_path = export_dir / "export_summary.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

    def _write_html_export(self, export_dir, non_archived_shots, project_info, export_type, timestamp):
        """Write HTML export with shot-centric gallery layout."""
        import html as _html
        import re
        from datetime import datetime as dt

        def esc(text):
            """Escape text for HTML content (not attributes)."""
            if not text:
                return ''
            return _html.escape(str(text))

        def sanitize_filename(name):
            return re.sub(r'[<>:\"/\\\\|?*]', '_', str(name))[:50] or ''

        def _md_to_html(text):
            """Convert basic Markdown to HTML (bold, italic, code, lists, headings, fenced code)."""
            if not text:
                return ''
            # Escape HTML first
            t = _html.escape(text)
            # Fenced code blocks (```...```)
            t = re.sub(r'```\n?(.*?)\n?```', r'<pre><code>\1</code></pre>', t, flags=re.DOTALL)
            # Inline code
            t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
            # Bold
            t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
            # Italic
            t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
            # Unordered list items
            t = re.sub(r'(?:^|\n)- (.+)', r'\n<li>\1</li>', t)
            # Wrap consecutive <li> in <ul>
            t = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', t)
            # Headings
            t = re.sub(r'^### (.+)$', r'<h4>\1</h4>', t, flags=re.MULTILINE)
            t = re.sub(r'^## (.+)$', r'<h3>\1</h3>', t, flags=re.MULTILINE)
            t = re.sub(r'^# (.+)$', r'<h3>\1</h3>', t, flags=re.MULTILINE)
            # Blank-line paragraph breaks
            paragraphs = t.split('\n\n')
            processed = []
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if p.startswith('<ul>') or p.startswith('<pre>') or p.startswith('<h'):
                    processed.append(p)
                else:
                    # Replace single newlines with <br> within paragraphs
                    p = p.replace('\n', '<br>\n')
                    processed.append(f'<p>{p}</p>')
            return '\n'.join(processed)

        # Build asset info per shot (reuse patterns but organized per-shot)
        shot_assets = []
        for order, shot in enumerate(non_archived_shots, start=1):
            shot_name = shot['name']
            display_name = shot['display_name'] or ''
            info = self.get_shot_info(shot_name)
            display_suffix = f"_{sanitize_filename(display_name)}" if display_name else ''

            has_first = False
            has_last = False
            has_video = False
            has_alt = False
            has_audio = False
            has_notes = bool(info['notes'].strip())

            # Determine exported filenames (same pattern as file copy phase)
            if 'images' in export_type or export_type == 'all':
                if info['first_image']['file']:
                    src = Path(info['first_image']['file'])
                    if src.exists():
                        has_first = True
                if info['last_image']['file']:
                    src = Path(info['last_image']['file'])
                    if src.exists():
                        has_last = True

            if 'videos' in export_type or export_type == 'all':
                if info['video']['file']:
                    src = Path(info['video']['file'])
                    if src.exists():
                        has_video = True
                if info['alt_video']['file']:
                    src = Path(info['alt_video']['file'])
                    if src.exists():
                        has_alt = True

            if 'audio' in export_type or export_type == 'all':
                if info['audio']['file']:
                    src = Path(info['audio']['file'])
                    if src.exists():
                        has_audio = True

            shot_assets.append({
                'order': order,
                'name': shot_name,
                'display_name': display_name,
                'display_suffix': display_suffix,
                'info': info,
                'has_first': has_first,
                'has_last': has_last,
                'has_video': has_video,
                'has_alt': has_alt,
                'has_audio': has_audio,
                'has_notes': has_notes,
            })

        # --- Build HTML ---
        lines = []
        lines.append('<!DOCTYPE html>')
        lines.append('<html lang="en">')
        lines.append('<head>')
        lines.append('<meta charset="UTF-8">')
        lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        title = esc(project_info.get('title', self.project_path.name))
        lines.append(f'<title>{title} — Export</title>')
        lines.append('<style>')
        lines.append(self._html_export_css())
        lines.append('</style>')
        lines.append('</head>')
        lines.append('<body>')

        # --- Sidebar TOC ---
        lines.append('<aside class="sb-sidebar" id="sidebar">')
        lines.append('<div class="sb-sidebar-title">Contents</div>')
        lines.append('<ul class="sb-sidebar-list">')
        for sa in shot_assets:
            label = f"{sa['name']} &middot; {esc(sa['display_name'])}" if sa['display_name'] else sa['name']
            lines.append(f'<li><a href="#shot-{sa["order"]:03d}">{label}</a></li>')
        lines.append('</ul>')
        lines.append('</aside>')

        # --- Main content area ---
        lines.append('<div class="sb-content">')

        # Header
        lines.append('<header class="sb-header">')
        lines.append(f'<h1>{title}</h1>')
        if project_info.get('short_description'):
            lines.append(f'<p class="sb-subtitle">{esc(project_info.get("short_description"))}</p>')
        lines.append('<div class="sb-meta">')
        if project_info.get('tags'):
            tags = ', '.join(project_info.get('tags', []))
            lines.append(f'<span>Tags: {esc(tags)}</span>')
        if project_info.get('version'):
            lines.append(f'<span>Version: {esc(project_info.get("version"))}</span>')
        lines.append(f'<span>Exported: {timestamp}</span>')
        lines.append(f'<span>Shots: {len(shot_assets)}</span>')
        if project_info.get('created'):
            lines.append(f'<span>Created: {esc(project_info.get("created"))}</span>')
        if project_info.get('updated'):
            lines.append(f'<span>Updated: {esc(project_info.get("updated"))}</span>')
        lines.append('</div>')

        # Project notes (Markdown rendered)
        if project_info.get('notes'):
            lines.append('<div class="sb-project-notes">')
            lines.append(_md_to_html(project_info.get('notes', '')))
            lines.append('</div>')

        lines.append('</header>')

        # Shot cards
        lines.append('<main class="sb-main">')
        for sa in shot_assets:
            info = sa['info']
            order = sa['order']
            name = sa['name']
            display_name = sa['display_name']
            display_suffix = sa['display_suffix']
            heading = f"#{order:03d}  {name}"
            if display_name:
                heading += f" — {esc(display_name)}"

            lines.append(f'<section class="sb-shot" id="shot-{order:03d}">')
            lines.append(f'<h2 class="sb-shot-heading">{heading}</h2>')

            # --- Images section ---
            if sa['has_first'] or sa['has_last']:
                lines.append('<div class="sb-section">')
                lines.append('<h3 class="sb-section-title">🖼️ Images</h3>')
                lines.append('<div class="sb-two-col">')

                # First frame
                lines.append('<div class="sb-asset">')
                lines.append('<h4>First Frame</h4>')
                if sa['has_first']:
                    src = Path(info['first_image']['file'])
                    ext = src.suffix
                    first_rel = f"images/{order:03d}_{name}{display_suffix}_first{ext}"
                    lines.append(f'<a href="{first_rel}" target="_blank"><img src="{first_rel}" alt="First frame" class="sb-img"></a>')
                if info['first_image'].get('caption'):
                    lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {esc(info["first_image"]["caption"])}</p>')
                if info['first_image'].get('prompt'):
                    lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{esc(info["first_image"]["prompt"])}</pre></div>')
                lines.append('</div>')

                # Last frame
                lines.append('<div class="sb-asset">')
                lines.append('<h4>Last Frame</h4>')
                if sa['has_last']:
                    src = Path(info['last_image']['file'])
                    ext = src.suffix
                    last_rel = f"images/{order:03d}_{name}{display_suffix}_last{ext}"
                    lines.append(f'<a href="{last_rel}" target="_blank"><img src="{last_rel}" alt="Last frame" class="sb-img"></a>')
                if info['last_image'].get('caption'):
                    lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {esc(info["last_image"]["caption"])}</p>')
                if info['last_image'].get('prompt'):
                    lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{esc(info["last_image"]["prompt"])}</pre></div>')
                lines.append('</div>')

                lines.append('</div>')  # .sb-two-col
                lines.append('</div>')  # .sb-section

            # --- Videos section ---
            if sa['has_video'] or sa['has_alt']:
                lines.append('<div class="sb-section">')
                lines.append('<h3 class="sb-section-title">🎬 Videos</h3>')
                lines.append('<div class="sb-two-col">')

                # Video
                lines.append('<div class="sb-asset">')
                lines.append('<h4>Video</h4>')
                if sa['has_video']:
                    src = Path(info['video']['file'])
                    ext = src.suffix
                    vid_rel = f"videos/{order:03d}_{name}{display_suffix}{ext}"
                    mime = 'video/mp4' if ext.lower() == '.mp4' else 'video/webm' if ext.lower() == '.webm' else 'video/mp4'
                    lines.append(f'<video controls class="sb-video"><source src="{vid_rel}" type="{mime}"></video>')
                if info['video'].get('caption'):
                    lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {esc(info["video"]["caption"])}</p>')
                if info['video'].get('prompt'):
                    lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{esc(info["video"]["prompt"])}</pre></div>')
                lines.append('</div>')

                # Alt Video
                lines.append('<div class="sb-asset">')
                lines.append('<h4>Alt Video</h4>')
                if sa['has_alt']:
                    src = Path(info['alt_video']['file'])
                    ext = src.suffix
                    alt_rel = f"videos/{order:03d}_{name}{display_suffix}_alt{ext}"
                    mime = 'video/mp4' if ext.lower() == '.mp4' else 'video/webm' if ext.lower() == '.webm' else 'video/mp4'
                    lines.append(f'<video controls class="sb-video"><source src="{alt_rel}" type="{mime}"></video>')
                if info['alt_video'].get('caption'):
                    lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {esc(info["alt_video"]["caption"])}</p>')
                if info['alt_video'].get('prompt'):
                    lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{esc(info["alt_video"]["prompt"])}</pre></div>')
                lines.append('</div>')

                lines.append('</div>')  # .sb-two-col
                lines.append('</div>')  # .sb-section

            # --- Audio section ---
            if sa['has_audio']:
                lines.append('<div class="sb-section">')
                lines.append('<h3 class="sb-section-title">🔊 Audio</h3>')
                lines.append('<div class="sb-audio-row">')
                src = Path(info['audio']['file'])
                ext = src.suffix
                aud_rel = f"audio/{order:03d}_{name}{display_suffix}_audio{ext}"
                mime_map = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.flac': 'audio/flac', '.aac': 'audio/aac', '.m4a': 'audio/mp4'}
                mime = mime_map.get(ext.lower(), 'audio/mpeg')
                lines.append(f'<audio controls class="sb-audio"><source src="{aud_rel}" type="{mime}"></audio>')
                if info['audio'].get('caption') or info['audio'].get('prompt'):
                    lines.append('<div class="sb-audio-info">')
                    if info['audio'].get('caption'):
                        lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {esc(info["audio"]["caption"])}</p>')
                    if info['audio'].get('prompt'):
                        lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{esc(info["audio"]["prompt"])}</pre></div>')
                    lines.append('</div>')
                lines.append('</div>')  # .sb-audio-row
                lines.append('</div>')  # .sb-section

            # --- Notes section ---
            if sa['has_notes']:
                lines.append('<div class="sb-section">')
                lines.append('<h3 class="sb-section-title">📝 Notes</h3>')
                lines.append(f'<div class="sb-notes">{esc(info["notes"])}</div>')
                lines.append('</div>')

            lines.append('</section>')  # .sb-shot

        lines.append('</main>')

        # Footer
        try:
            from app.utils import get_app_version
            app_version = get_app_version()
        except Exception:
            app_version = '4.1.0'
        lines.append('<footer class="sb-footer">')
        lines.append(f'<p>Generated by ShotBase v{app_version}</p>')
        lines.append('</footer>')

        lines.append('</div>')  # .sb-content

        # Copy prompt script
        lines.append('<script>')
        lines.append('function copyPrompt(btn) {')
        lines.append('  var pre = btn.closest(".sb-prompt").querySelector("pre");')
        lines.append('  navigator.clipboard.writeText(pre.textContent).then(function() {')
        lines.append('    btn.textContent = "✓ Copied!";')
        lines.append('    setTimeout(function() { btn.textContent = "📋 Copy"; }, 2000);')
        lines.append('  }).catch(function() {')
        lines.append('    btn.textContent = "Failed";')
        lines.append('    setTimeout(function() { btn.textContent = "📋 Copy"; }, 2000);')
        lines.append('  });')
        lines.append('}')
        lines.append('</script>')

        lines.append('</body>')
        lines.append('</html>')

        # Write HTML file
        html_path = export_dir / "export_summary.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _html_export_css(self):
        """Return embedded CSS for HTML export."""
        return """\
/* ShotBase HTML Export Styles */
:root {
  --bg: #1a1a2e;
  --card-bg: #222244;
  --text: #e0e0e0;
  --text-muted: #999;
  --accent: #5b8def;
  --border: #333366;
  --prompt-bg: #1a1a30;
  --img-bg: #0d0d1a;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
}

.sb-header {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px 24px;
  text-align: center;
  border-bottom: 1px solid var(--border);
}

.sb-header h1 {
  font-size: 2em;
  margin-bottom: 8px;
  color: #fff;
}

.sb-subtitle {
  color: var(--text-muted);
  margin-bottom: 12px;
}

.sb-meta {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
  font-size: 0.85em;
  color: var(--text-muted);
}

/* Sidebar TOC */
.sb-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 220px;
  height: 100vh;
  background: var(--card-bg);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  z-index: 200;
  padding: 16px 0;
}

.sb-sidebar-title {
  font-size: 0.75em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  padding: 0 16px 10px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}

.sb-sidebar-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sb-sidebar-list li {
  padding: 0;
}

.sb-sidebar-list a {
  display: block;
  padding: 6px 16px;
  color: var(--text);
  text-decoration: none;
  font-size: 0.8em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s;
  border-left: 3px solid transparent;
}

.sb-sidebar-list a:hover {
  background: rgba(91, 141, 239, 0.15);
  border-left-color: var(--accent);
  color: #fff;
}

/* Content area (offset by sidebar) */
.sb-content {
  margin-left: 220px;
}

/* Main content */
.sb-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 60px;
}

/* Shot card */
.sb-shot {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 28px 24px;
  margin-bottom: 32px;
}

.sb-shot-heading {
  font-size: 1.35em;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  color: #fff;
}

/* Section */
.sb-section {
  margin-bottom: 24px;
}

.sb-section:last-child {
  margin-bottom: 0;
}

.sb-section-title {
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--accent);
  margin-bottom: 14px;
}

/* Two column layout */
.sb-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* Single asset block */
.sb-asset h4 {
  font-size: 0.85em;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 600;
}

.sb-img {
  display: block;
  max-width: 100%;
  max-height: 400px;
  border-radius: 6px;
  background: var(--img-bg);
  object-fit: contain;
}

.sb-video {
  display: block;
  width: 100%;
  max-height: 400px;
  border-radius: 6px;
  background: #000;
}

.sb-caption {
  margin-top: 8px;
  font-size: 0.9em;
  color: var(--text);
}

.sb-prompt {
  margin-top: 8px;
}

.sb-prompt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sb-prompt strong {
  font-size: 0.85em;
  color: var(--text-muted);
}

.sb-copy-btn {
  background: var(--border);
  color: var(--text-muted);
  border: none;
  border-radius: 3px;
  padding: 2px 8px;
  font-size: 0.75em;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.sb-copy-btn:hover {
  background: var(--accent);
  color: #fff;
}

.sb-prompt pre {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.82em;
  line-height: 1.5;
  color: #ccc;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

/* Audio */
.sb-audio-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.sb-audio {
  flex-shrink: 0;
  min-width: 280px;
}

.sb-audio-info {
  flex: 1;
  min-width: 200px;
}

/* Project notes (rendered Markdown) */
.sb-project-notes {
  max-width: 800px;
  margin: 20px auto 0;
  text-align: left;
  font-size: 0.9em;
  color: var(--text);
  line-height: 1.6;
}

.sb-project-notes p {
  margin-bottom: 10px;
}

.sb-project-notes ul {
  margin: 8px 0 12px 24px;
}

.sb-project-notes li {
  margin-bottom: 4px;
}

.sb-project-notes h3, .sb-project-notes h4 {
  color: var(--accent);
  margin: 16px 0 8px;
  font-size: 1.05em;
}

.sb-project-notes code {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
}

.sb-project-notes pre {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  overflow-x: auto;
  margin: 10px 0;
}

.sb-project-notes pre code {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.85em;
}

.sb-project-notes strong {
  color: #fff;
}

/* Notes (shot-level) */
.sb-notes {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 16px;
  white-space: pre-wrap;
  font-size: 0.9em;
  color: var(--text);
}

/* Footer */
.sb-footer {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.8em;
  border-top: 1px solid var(--border);
}

/* Responsive */
@media (max-width: 768px) {
  .sb-two-col {
    grid-template-columns: 1fr;
  }
  .sb-audio-row {
    flex-direction: column;
  }
  .sb-shot {
    padding: 16px 12px;
  }
}
"""

def get_shot_manager(project_path, cache=None):
    """Retrieve a cached ``ShotManager`` for the given path."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.setdefault('SHOT_MANAGER_CACHE', {})

    path_key = str(Path(project_path).resolve())
    if path_key not in cache:
        cache[path_key] = ShotManager(path_key)
    return cache[path_key]


def clear_shot_manager_cache(cache=None):
    """Clear cached ``ShotManager`` instances."""
    from flask import current_app

    if cache is None:
        cache = current_app.config.get('SHOT_MANAGER_CACHE')

    if cache is not None:
        cache.clear()