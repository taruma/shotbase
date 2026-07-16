import logging
import shutil
from pathlib import Path

from PIL import Image

from app.config.constants import (
    ALLOWED_AUDIO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    THUMBNAIL_SIZE,
    get_project_thumbnail_cache_dir,
)
from app.services.shot_utils import get_shot_manager

logger = logging.getLogger(__name__)


class FileHandler:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.shots_dir = self.project_path / 'shots'
        self.wip_dir = self.shots_dir / 'wip'
        self.latest_images_dir = self.shots_dir / 'latest_images'
        self.latest_videos_dir = self.shots_dir / 'latest_videos'
        self.latest_audio_dir = self.shots_dir / 'latest_audio'

        self.wip_dir.mkdir(parents=True, exist_ok=True)
        self.latest_images_dir.mkdir(parents=True, exist_ok=True)
        self.latest_videos_dir.mkdir(parents=True, exist_ok=True)
        self.latest_audio_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_cache_dir = get_project_thumbnail_cache_dir(self.project_path)

    def clear_thumbnail_cache(self):
        """Remove all files from the thumbnail cache."""
        if not self.thumbnail_cache_dir.exists():
            self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
            return

        for thumb in self.thumbnail_cache_dir.iterdir():
            if thumb.is_file():
                try:
                    thumb.unlink()
                except Exception as e:
                    logger.warning("Could not delete thumbnail %s: %s", thumb, e)

    def save_file(self, file, shot_name, file_type):
        """Save uploaded file with proper versioning"""
        shot_dir = self.wip_dir / shot_name
        file_ext = Path(file.filename).suffix.lower()

        # Normalize/validate file type and extension
        is_image_type = file_type in {'image', 'first_image', 'last_image'}
        is_video_type = file_type in {'video', 'alt_video'}
        is_audio_type = file_type == 'audio'

        if is_image_type and file_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError(f"Invalid image format. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}")
        if is_video_type and file_ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError(f"Invalid video format. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")
        if is_audio_type and file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise ValueError(f"Invalid audio format. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

        if not (is_image_type or is_video_type or is_audio_type):
            raise ValueError("Invalid file_type")

        if not shot_dir.exists():
            get_shot_manager(self.project_path).create_shot_structure(shot_name)

        manager = get_shot_manager(self.project_path)

        if is_image_type:
            # Map legacy 'image' to 'first_image'
            canonical_type = 'first_image' if file_type in {'image', 'first_image'} else 'last_image'
            slot = 'first' if canonical_type == 'first_image' else 'last'
            wip_dir = shot_dir / 'images'
            base = f'{shot_name}_{slot}'
            version = self.get_next_version(wip_dir, base, file_ext)

            wip_filename = f'{base}_v{version:03d}{file_ext}'
            wip_path = wip_dir / wip_filename
            file.save(str(wip_path))

            final_dir = self.latest_images_dir
            final_path = final_dir / f'{base}{file_ext}'

            # Remove existing finals only for this slot (first/last)
            for existing_file in final_dir.glob(f'{base}.*'):
                if existing_file != wip_path:
                    existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))

            # Update current version marker so UI shows the promoted version correctly
            try:
                manager.set_current_version(shot_name, canonical_type, version)
            except Exception as e:
                logger.warning("Failed to set current version marker: %s", e)

            # Thumbnails for images
            thumbnail_path = self.create_thumbnail(str(final_path), shot_name)

        elif is_video_type:
            wip_dir = shot_dir / 'videos'
            base = f'{shot_name}_alt' if file_type == 'alt_video' else shot_name
            version = self.get_next_version(wip_dir, base, file_ext)

            wip_filename = f'{base}_v{version:03d}{file_ext}'
            wip_path = wip_dir / wip_filename
            file.save(str(wip_path))

            final_dir = self.latest_videos_dir
            final_path = final_dir / f'{base}{file_ext}'

            for existing_file in final_dir.glob(f'{base}.*'):
                if existing_file != wip_path:
                    existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))
            # Update current version marker so UI shows the promoted version correctly
            try:
                manager.set_current_version(shot_name, file_type, version)
            except Exception as e:
                logger.warning("Failed to set current version marker: %s", e)

            # Thumbnails for videos
            thumbnail_path = self.create_video_thumbnail(str(final_path), base)

        elif is_audio_type:
            wip_dir = shot_dir / 'audio'
            wip_dir.mkdir(exist_ok=True)
            base = f'{shot_name}_audio'
            version = self.get_next_version(wip_dir, base, file_ext)

            wip_filename = f'{base}_v{version:03d}{file_ext}'
            wip_path = wip_dir / wip_filename
            file.save(str(wip_path))

            final_dir = self.latest_audio_dir
            final_path = final_dir / f'{base}{file_ext}'

            for existing_file in final_dir.glob(f'{base}.*'):
                if existing_file != wip_path:
                    existing_file.unlink()

            shutil.copy2(str(wip_path), str(final_path))
            # Update current version marker so UI shows the promoted version correctly
            try:
                manager.set_current_version(shot_name, file_type, version)
            except Exception as e:
                logger.warning("Failed to set current version marker: %s", e)

            thumbnail_path = None  # No thumbnail for audio

        return {
            'wip_path': str(wip_path).replace('\\', '/'),
            'final_path': str(final_path).replace('\\', '/'),
            'version': version,
            'thumbnail': f"/api/shots/thumbnail/{Path(thumbnail_path).name}" if thumbnail_path else None
        }

    def get_next_version(self, wip_dir, base_name, file_ext):
        if not wip_dir.exists():
            return 1

        wip_dir_str = str(wip_dir)
        if 'audio' in wip_dir_str:
            allowed_extensions = ALLOWED_AUDIO_EXTENSIONS
        elif 'image' in wip_dir_str:
            allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
        else:
            allowed_extensions = ALLOWED_VIDEO_EXTENSIONS

        existing_files = []
        for ext in allowed_extensions:
            existing_files.extend(wip_dir.glob(f'{base_name}_v*{ext}'))

        if not existing_files:
            return 1

        versions = []
        for f in existing_files:
            try:
                version_str = f.stem.split('_v')[1]
                versions.append(int(version_str))
            except (IndexError, ValueError):
                continue

        return max(versions) + 1 if versions else 1

    def create_thumbnail(self, image_path, shot_name, size=THUMBNAIL_SIZE):
        """Create thumbnail for image and save it to the central cache"""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)

                # Unique thumbnail name
                image_path = Path(image_path)
                thumb_filename = f"{shot_name}_{image_path.stem}_thumb.jpg"
                thumb_path = self.thumbnail_cache_dir / thumb_filename

                if thumb_path.exists():
                    thumb_path.unlink()

                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (64, 64, 64))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = background

                img.save(str(thumb_path), 'JPEG', quality=85)
                return str(thumb_path)

        except Exception as e:
            logger.warning("Error creating thumbnail: %s", e)
            return None

    def create_video_thumbnail(self, video_path, shot_name, size=THUMBNAIL_SIZE):
        """Extract the first frame of ``video_path`` and save it as a thumbnail."""
        try:
            import shutil as _shutil
            import subprocess

            video_path = Path(video_path)
            if not video_path.exists():
                logger.warning("Video file does not exist: %s", video_path)
                return None
            thumb_filename = f"{shot_name}_{video_path.stem}_vthumb.jpg"
            thumb_path = self.thumbnail_cache_dir / thumb_filename

            ffmpeg = _shutil.which("ffmpeg")
            if not ffmpeg:
                logger.warning("ffmpeg not found; skipping video thumbnail for %s", video_path)
                return None

            self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = thumb_path.with_suffix(".tmp.jpg")

            cmd = [ffmpeg, "-y", "-i", str(video_path), "-frames:v", "1", str(tmp_path)]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)  # noqa: S603

            with Image.open(tmp_path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (64, 64, 64))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                    img = background
                img.save(str(thumb_path), "JPEG", quality=85)

            tmp_path.unlink(missing_ok=True)
            return str(thumb_path)
        except Exception as e:
            logger.warning("Error creating video thumbnail: %s", e)
            return None
