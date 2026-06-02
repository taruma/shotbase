import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

UPLOAD_FOLDER = os.environ.get('SHOTBUDDY_UPLOAD_FOLDER', 'uploads')
PROJECTS_FILE = 'projects.json'
MAX_RECENT_PROJECTS = 6
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov'}

# Central thumbnail cache location. Stored inside the application's static
# directory so thumbnails persist across projects. The cache is cleared when
# switching projects or the page is refreshed.
THUMBNAIL_CACHE_DIR = BASE_DIR / "static" / "thumbnails"

# Default thumbnail resolution (width, height)
THUMBNAIL_SIZE = (240, 180)

def get_project_thumbnail_cache_dir(project_path):
    """
    Return the per-project thumbnail cache directory:
      <project_path>/.shotbuddy/thumbnails

    Ensures the directory exists.
    """
    p = Path(project_path) / ".shotbuddy" / "thumbnails"
    p.mkdir(parents=True, exist_ok=True)
    return p
