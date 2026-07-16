import logging
from pathlib import Path

from PIL import Image

from app.config.constants import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_SIZE,
    get_project_thumbnail_cache_dir,
)
from app.services.shot_utils import validate_shot_name

logger = logging.getLogger(__name__)


class ShotManager:
    """Facade that orchestrates shot lifecycle, asset management, and export.

    Delegates order/archive I/O to ``ShotOrderManager``, metadata CRUD to
    ``ShotMetadata``, prompt I/O to ``PromptStore``, and export logic to
    ``ExportService``.
    """

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

        # ------------------------------------------------------------------
        # Sub-service instances (lazy — created on first access so that
        # route handlers that never touch certain features don't pay the
        # import cost).
        # ------------------------------------------------------------------
        self._order_mgr = None
        self._metadata = None
        self._prompts = None
        self._exporter = None

    # ------------------------------------------------------------------
    # Lazy sub-service accessors
    # ------------------------------------------------------------------

    @property
    def order(self):
        if self._order_mgr is None:
            from app.services.shot_order import ShotOrderManager
            self._order_mgr = ShotOrderManager(self.project_path)
        return self._order_mgr

    @property
    def metadata(self):
        if self._metadata is None:
            from app.services.metadata import ShotMetadata
            self._metadata = ShotMetadata(self.project_path)
        return self._metadata

    @property
    def prompts(self):
        if self._prompts is None:
            from app.services.prompts import PromptStore
            self._prompts = PromptStore(self.project_path)
        return self._prompts

    @property
    def exporter(self):
        if self._exporter is None:
            from app.services.export_service import ExportService
            self._exporter = ExportService(self)
        return self._exporter

    # ==================================================================
    # Shot order (delegated → ShotOrderManager)
    # ==================================================================

    def _load_shot_order(self):
        return self.order.load_shot_order()

    def _save_shot_order(self, names):
        return self.order.save_shot_order(names)

    def save_shot_order(self, shot_order):
        if not isinstance(shot_order, list):
            raise ValueError('Shot order must be a list')
        self.order.save_shot_order(shot_order)

    # ==================================================================
    # Archive (delegated → ShotOrderManager)
    # ==================================================================

    def _load_archived(self):
        return self.order.load_archived()

    def _save_archived(self, names):
        return self.order.save_archived(names)

    def archive_shot(self, shot_name, archived: bool):
        """Toggle archived state for a shot and return updated shot info."""
        self.order.toggle_archived(shot_name, archived)
        return self.get_shot_info(shot_name)

    # ==================================================================
    # Metadata — notes, captions, display name (delegated → ShotMetadata)
    # ==================================================================

    def load_meta(self, shot_name):
        return self.metadata.load_meta(shot_name)

    def save_display_name(self, shot_name, display_name):
        return self.metadata.save_display_name(shot_name, display_name)

    def save_shot_notes(self, shot_name, notes):
        return self.metadata.save_notes(shot_name, notes)

    def _captions_file(self, shot_name):
        return self.metadata._captions_file(shot_name)

    def load_captions(self, shot_name):
        return self.metadata.load_captions(shot_name)

    def save_caption(self, shot_name, asset_type, caption):
        return self.metadata.save_caption(shot_name, asset_type, caption)

    # ==================================================================
    # Prompts (delegated → PromptStore)
    # ==================================================================

    def _prompt_file_path(self, shot_name, asset_type, version):
        return self.prompts._prompt_file_path(shot_name, asset_type, version)

    def load_prompt(self, shot_name, asset_type, version):
        return self.prompts.load_prompt(shot_name, asset_type, version)

    def save_prompt(self, shot_name, asset_type, version, prompt):
        return self.prompts.save_prompt(shot_name, asset_type, version, prompt)

    def get_prompt_versions(self, shot_name, asset_type):
        return self.prompts.get_prompt_versions(shot_name, asset_type)

    # ==================================================================
    # Export (delegated → ExportService)
    # ==================================================================

    def export_latest_assets(self, export_name=None, export_type='all',
                             include_display_in_filename=True, include_metadata=True,
                             export_format='md'):
        return self.exporter.export_latest_assets(
            export_name=export_name,
            export_type=export_type,
            include_display_in_filename=include_display_in_filename,
            include_metadata=include_metadata,
            export_format=export_format,
        )

    def _write_md_export(self, export_dir, non_archived_shots, project_info, export_type, timestamp):
        return self.exporter._write_md_export(export_dir, non_archived_shots, project_info, export_type, timestamp)

    def _write_html_export(self, export_dir, non_archived_shots, project_info, export_type, timestamp):
        return self.exporter._write_html_export(export_dir, non_archived_shots, project_info, export_type, timestamp)

    # ==================================================================
    # Shot CRUD (still on ShotManager — orchestrates multiple sub-services)
    # ==================================================================

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
            names = self.order.load_archived()
            if old_name in names:
                names.discard(old_name)
                names.add(new_name)
                self.order.save_archived(names)
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
        
        ordered_names = self.order.load_shot_order()
        if ordered_names:
            dir_map = {d.name: d for d in shot_dirs}
            ordered_dirs = [dir_map[name] for name in ordered_names if name in dir_map]
            existing_ordered_names = {d.name for d in ordered_dirs}
            new_dirs = [d for d in shot_dirs if d.name not in existing_ordered_names]
            shot_dirs = ordered_dirs + sorted(new_dirs, key=lambda d: d.name)
        else:
            shot_dirs = sorted(shot_dirs, key=lambda d: d.name)

        # Cache archived set once so get_shot_info() doesn't re-read from disk per shot
        archived_names = self.order.load_archived()
        shots = [self.get_shot_info(shot_dir.name, archived_names=archived_names) for shot_dir in shot_dirs]
        return shots

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

        order_names = self.order.load_shot_order()
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

        self.order.save_shot_order(order_names)

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

    # ==================================================================
    # Asset discovery & versioning (still on ShotManager)
    # ==================================================================

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

    # ==================================================================
    # Asset promotion (still on ShotManager — orchestration logic)
    # ==================================================================

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

    # ==================================================================
    # Thumbnails (still on ShotManager — Pillow/ffmpeg logic)
    # ==================================================================

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

    # ==================================================================
    # get_shot_info — the main info builder (orchestrates all sub-services)
    # ==================================================================

    def get_shot_info(self, shot_name, archived_names=None):
        """Get information about a specific shot."""
        validate_shot_name(shot_name)
        shot_dir = self.wip_dir / shot_name

        # Load notes (delegated to metadata service)
        notes = self.metadata.load_notes(shot_name)

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
        first_prompt = self.prompts.load_prompt(shot_name, 'first_image', current_first_version) if current_first_version > 0 else ''

        current_last_version = self.get_current_version(shot_name, 'last_image', last_max_version)
        last_prompt = self.prompts.load_prompt(shot_name, 'last_image', current_last_version) if current_last_version > 0 else ''

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
            video_prompt = self.prompts.load_prompt(shot_name, 'video', current_video_version)

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
            alt_video_prompt = self.prompts.load_prompt(shot_name, 'alt_video', current_alt_video_version)

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
            audio_prompt = self.prompts.load_prompt(shot_name, 'audio', current_audio_version)

        captions = self.metadata.load_captions(shot_name)

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

        meta = self.metadata.load_meta(shot_name)
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
            'archived': (shot_name in (archived_names if archived_names is not None else self.order.load_archived()))
        }