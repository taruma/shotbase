# ShotBase Project Context

## Quick Reference (Current State)

| Item | Value |
|---|---|
| **Version** | 4.0.0 |
| **Git Branch** | `main` |
| **Python Requirement** | ≥3.13.1 |
| **Default Host:Port** | 127.0.0.1:5001 |
| **Package Manager** | `uv` (do NOT use `pip install`) |
| **Linter** | ruff (config in pyproject.toml, line-length=120) |

---

## Project Overview
ShotBase is an application for managing AI-generated media assets including images, videos, prompts, and project notes. It supports structured organization, versioning, and annotation of generated stills and videos. The application provides a web interface for creating, managing, and organizing shots with drag-and-drop functionality.

Key features include:
- Shot management with versioned stills and videos
- Automatic organization of latest versions
- Prompt documentation and version history
- Shot reordering and archiving
- Display names for shots
- Asset promotion and captioning
- Thumbnail generation for images and videos (lazy, on-demand)
- First/last frame image variants per shot
- Alternative video asset (alt_video) for reference, upscales, or additional video variants
- Shot search modal with multi-token search, content/archive filters, and keyboard navigation
- Visual reorder modal with drag-and-drop grid, thumbnail switching, preview, and inline editing
- Project info management (title, version, description, tags)
- Export with metadata to markdown (including display name columns)
- Light/dark theme toggle
- Native folder picker for project creation
- Media modals with keyboard navigation (arrows)
- Gap-filling shot numbering (1–999)
- Sticky header on scroll
- Dynamic page title with project info and app version
- Collapsible archived section in TOC

---

## Technology Stack
- **Backend**: Python 3.13.1+, Flask
- **Frontend**: HTML/CSS/JavaScript (served by Flask)
- **Dependencies**: flask, flask-cors, pillow, python-dotenv
- **Build Tool**: uv (package manager and virtual environment tool)

---

## Development Tooling
This project uses `uv` as the primary tool for all Python development tasks including dependency management, running scripts, and virtual environment handling. 

**Important**: Avoid using `pip install` directly. Instead, use `uv` commands for all dependency management:
- Use `uv add package_name` to add new dependencies
- Use `uv remove package_name` to remove dependencies
- Use `uv sync` to install all project dependencies
- Use `uv run script_name.py` to run Python scripts

---

## Project Structure
```
shotbuddy/
├── app/                    # Main application code
│   ├── __init__.py         # Flask app factory
│   ├── utils.py            # Path sanitization, version reader
│   ├── routes/            # API routes (project_routes.py, shot_routes.py)
│   ├── services/          # Business logic
│   │   ├── shot_manager.py     # Core shot operations
│   │   ├── project_manager.py  # Project state, recent projects, info CRUD
│   │   ├── file_handler.py     # Uploads and asset processing
│   │   └── prompt_importer.py  # PNG metadata prompt extraction (A1111/ComfyUI)
│   ├── config/            # Configuration (constants.py)
│   └── static/            # Static assets
│       ├── css/           # main.css, styles.css, search-modal.css, visual-reorder.css
│       ├── js/            # main.js, search-modal.js, visual-reorder.js, modal-behavior.js
│       └── icons/         # Favicons, PWA manifest, folder icon
├── shots/                  # Project data directory (created per project)
│   ├── wip/               # Work-in-progress shot folders
│   ├── latest_images/     # Latest image versions
│   └── latest_videos/     # Latest video versions (regular, alt)
├── exports/               # Export output directory
├── run.py                 # Application entry point
├── shotbuddy.cfg          # Server configuration
├── pyproject.toml         # Project metadata and dependencies
├── requirements.txt       # Legacy dependencies list
└── uploads/               # Temporary upload directory
```

---

## Building and Running

### Prerequisites
- Python 3.13.1 or newer
- uv package manager

### Installation
1. Install uv: https://docs.astral.sh/uv/
2. Clone the repository
3. Create environment and install dependencies:
   ```bash
   uv sync
   ```
   
**Note**: This project uses `uv` for all dependency management. Do not use `pip install` directly as it may cause dependency conflicts or inconsistencies.

### Running the Application
1. Start the development server:
   ```bash
   uv run run.py
   ```
2. Open browser at http://127.0.0.1:5001/ (default)

### Configuration
Server settings can be configured in `shotbuddy.cfg`:
```ini
[server]
host = 0.0.0.0
port = 5001
```

Environment variables can override config file settings:
- `SHOTBUDDY_UPLOAD_FOLDER` - Upload directory (default: `uploads`)
- `SHOTBUDDY_HOST` - Server host (default: `127.0.0.1`)
- `SHOTBUDDY_PORT` - Server port (default: `5001`)
- `SHOTBUDDY_DEBUG` - Enable Flask debug mode (set to `1`)

---

## Development Conventions
- Uses Flask blueprints for route organization
- Project-scoped data management with ShotManager service
- JSON-based API responses with success/error structure
- Thumbnail caching in project-specific directories with lazy (on-demand) generation
- Version detection results cached per shot/asset type for performance
- Version-controlled shot naming scheme (SH### or SH###_###)
- Asset versioning with _v### suffix
- All development tasks should use `uv` as the primary tool for dependency management and script execution

---

## Key Components
- **ShotManager**: Core service for shot operations, file management, version tracking, thumbnail generation, and metadata handling
- **ProjectManager**: Handles project state, recent projects (up to 6), and current project tracking
- **FileHandler**: Manages file uploads and asset processing for all asset types including alt_video
- **Routes**: REST API endpoints for project and shot operations

---

## Full API Endpoint Reference

### Project Routes (Blueprint: `/`, in `app/routes/project_routes.py`)

| Method | Path | Params/Body | Purpose |
|---|---|---|---|
| GET | `/` | — | Serves SPA `index.html` with app version |
| GET | `/api/project/current` | — | Returns current project info; auto-detects stale cache and rescans |
| GET | `/api/project/recent` | — | Returns list of up to 6 recent projects with project titles |
| POST | `/api/project/open` | `{path}` | Opens an existing project by path |
| POST | `/api/project/create` | `{name, path}` | Creates new project folder + project_info.json |
| GET | `/api/project/info` | — | Returns project_info.json contents |
| POST | `/api/project/info` | `{title, description, ...}` | Updates project info; auto-merges with existing, preserves `created` |
| GET | `/api/project/last-location` | — | Returns last folder used for project creation |
| GET | `/api/system/browse-folder` | optional: `?force_path=` `?force_warning=1` `?force_error=1` | Opens native folder picker (tkinter → AppleScript → home fallback) |

### Shot Routes (Blueprint: `/api/shots`, in `app/routes/shot_routes.py`)

| Method | Path | Params/Body | Purpose |
|---|---|---|---|
| GET | `/api/shots/` | — | Get all shots with full info (ordered) |
| POST | `/api/shots/` | — | Create new shot with gap-filling number |
| POST | `/api/shots/upload` | Form: `file`, `shot_name`, `file_type` | Upload image/video; file_type: `image`/`first_image`/`last_image`/`video`/`alt_video` |
| POST | `/api/shots/notes` | `{shot_name, notes}` | Save shot notes (notes.txt) |
| POST | `/api/shots/caption` | `{shot_name, asset_type, caption}` | Save caption (first_image/last_image/video/alt_video) |
| POST | `/api/shots/prompt` | `{shot_name, asset_type, version, prompt}` | Save prompt for a specific asset version |
| GET | `/api/shots/prompt` | `?shot_name=&asset_type=&version=` | Get prompt for specific asset version |
| GET | `/api/shots/prompt_versions` | `?shot_name=&asset_type=` | List all versions that have prompts |
| POST | `/api/shots/rename` | `{old_name, new_name}` | Rename shot + all associated files (including alt_video) |
| POST | `/api/shots/reorder` | `{shot_order: [...]}` | Persist shot order list |
| POST | `/api/shots/create-between` | `{after_shot}` | Create shot after given shot (or at top if null) |
| GET | `/api/shots/thumbnail/<filepath>` | — | Serve thumbnail with strong caching + ETag; generates on-the-fly if missing (lazy) |
| POST | `/api/shots/reveal` | `{path}` | Reveal file in OS file browser (Explorer/Finder) |
| POST | `/api/shots/open-folder` | — | Open current project's shots folder |
| POST | `/api/shots/open-exports-folder` | — | Open current project's exports folder (creates if missing) |
| POST | `/api/shots/promote` | `{shot_name, asset_type, version}` | Promote a WIP version to latest |
| POST | `/api/shots/archive` | `{shot_name, archived: bool}` | Toggle archived state |
| POST | `/api/shots/export` | `{export_name, export_type, include_display_in_filename, include_metadata}` | Export latest assets + optional metadata.md with display name columns |
| GET | `/api/shots/video/<shot_name>` | optional: `?type=video` (default) or `?type=alt_video` | Serve promoted video file |
| GET | `/api/shots/image/<shot_name>/<asset_type>` | — | Serve promoted image (first_image/last_image) |
| POST | `/api/shots/display-name` | `{shot_name, display_name}` | Set human-readable display name |

### Request/Response Conventions
- **Success**: `{"success": true, "data": ...}`
- **Error**: `{"success": false, "error": "message"}`, HTTP 400/500
- **Paths**: All file paths are normalized to POSIX-style forward slashes via `_normalize_path()`
- **Timestamps**: ISO 8601 format throughout
- **Backward compat**: `image` asset type maps to `first_image` everywhere; legacy single-image finals still supported

---

## Data Flow & Architecture

### Request Lifecycle
1. Flask receives request → Blueprint route handler
2. Route gets `ProjectManager` from `current_app.config['PROJECT_MANAGER']`
3. Route gets `ShotManager` from cache via `get_shot_manager(project_path)`
4. Service performs filesystem operations + metadata reads/writes
5. Returns JSON response

### Service Dependencies
```
project_routes.py ──→ ProjectManager (singleton, per-app)
                          │
shot_routes.py ──→ get_shot_manager(path) ──→ ShotManager (cached per project path)
                          │                         │
                     FileHandler ────→ ShotManager   │
                          │                         │
                     prompt_importer.py              │
                     (extract_prompt_from_png)       │
                                                     │
                                          ┌──────────┘
                                          ├── Pillow (thumbnails, lazy generation)
                                          ├── ffmpeg (video thumbs, optional)
                                          ├── tkinter (folder picker)
                                          └── subprocess (reveal/open-folder/open-exports)
```

### Side Effects of Common Operations
- **Creating a shot**: creates `shots/wip/SH###/` with `images/`, `videos/` subdirs; creates shot order entry; updates project timestamp
- **Uploading an asset**: saves to `wip/SH###/images/` or `videos/` with version suffix; copies to `latest_images/` or `latest_videos/`; lazy thumbnail URL computed (generated on first request); extracts PNG prompts; updates version marker
- **Promoting an asset**: copies WIP version → latest dir; updates `.version` marker; thumbnail regenerated on next request
- **Archiving a shot**: toggles entry in `.archived_shots.json`

---

## Per-Project File Schema Reference

Every project directory contains these files (under `shots/`):

### `project_info.json` (project root)
```json
{
  "title": "Project Name",
  "description": "",
  "short_description": "",
  "notes": "",
  "tags": [],
  "created": "ISO-8601",
  "updated": "ISO-8601",
  "version": "1.0.0"
}
```
- `description` is mirrored from `notes` for backward compatibility
- `created` is preserved from folder ctime and never overwritten
- `updated` auto-refreshes on every mutation

### `shots/.shot_order.json`
```json
["SH001", "SH003", "SH002"]
```
- Flat list of shot names in display order
- Loaded/saved via `_load_shot_order()` / `_save_shot_order()`
- De-duplicated on save

### `shots/.archived_shots.json`
```json
["SH005", "SH010"]
```
- Sorted list of archived shot names
- Loaded on every `get_shots()` call; cached once per call for performance

### `shots/wip/SH###/meta.json`
```json
{"display_name": "Opening Scene"}
```
- Per-shot metadata; currently only stores `display_name`

### `shots/wip/SH###/captions.json`
```json
{"first_image": "Opening frame caption", "last_image": "", "video": "Main shot clip", "alt_video": ""}
```
- Keys: `first_image`, `last_image`, `video`, `alt_video`

### `shots/wip/SH###/notes.txt`
- Plain text file, read/written as-is

### `shots/wip/SH###/images/` (WIP image files)
- Naming: `SH###_first_v001.png`, `SH###_last_v002.jpg`, or legacy `SH###_v001.png`
- Prompt files: `SH###_first_v001_image_prompt.txt`, `SH###_last_v001_image_prompt.txt`

### `shots/wip/SH###/videos/` (WIP video files)
- Regular video: `SH###_v001.mp4`
- Alt video: `SH###_alt_v001.mp4`
- Prompt files: `SH###_v001_video_prompt.txt`, `SH###_alt_v001_video_prompt.txt`

### `shots/latest_images/`
- Promoted finals: `SH###_first.png`, `SH###_last.jpg` (or legacy `SH###.png`)
- Version markers: `SH###_first.version`, `SH###_last.version`, `SH###.version` (legacy)
- Each `.version` file contains a single integer

### `shots/latest_videos/`
- Promoted finals: `SH###.mp4` (regular), `SH###_alt.mp4` (alt)
- Version markers: `SH###.version`, `SH###_alt.version`
- Each `.version` file contains a single integer

### `.shotbuddy/thumbnails/` (per-project cache)
- Image thumbs: `SH###_SH###_first_thumb.jpg`
- Video thumbs: `SH###_SH###_vthumb.jpg` (regular), `SH###_SH###_alt_vthumb.jpg` (alt)
- Generated lazily on first request, cached indefinitely

---

## Shot Naming & Versioning Rules

### Shot Names
- Pattern: `^SH\d{3}(?:_\d{3})?$`
- Examples: `SH001`, `SH042`, `SH001_050`
- `SH000` is explicitly forbidden
- Only one underscore level allowed (no `SH001_050_100`)
- Function parsers: `validate_shot_name()`, `_parse_shot_parts()`, `_format_shot_parts()`

### Gap-Filling Numbering
- `get_next_shot_number()` scans existing top-level shots (no underscore)
- Returns lowest available number 1–999
- Fills gaps before appending to the end

### Sub-Shot Numbering
- Base + `_###` where `###` starts at 050 and increments by 10
- e.g., `SH001_050`, `SH001_060`, `SH001_070`
- Created via `create_shot_between()` with `after_shot` having an underscore

### Asset Versioning
- WIP files: `SH###_v001.png`, `SH###_first_v003.jpg`, `SH###_last_v002.png`, `SH###_alt_v001.mp4`
- `_v###` suffix with 3-digit zero-padded version
- `FileHandler.get_next_version()` scans for max existing version + 1
- `ShotManager._detect_existing_versions()` scans filesystem to correct version counts; results cached per shot/asset type

### First/Last Image Variants
- `first_image` = first frame (maps to `_first` suffix in filenames)
- `last_image` = last frame (maps to `_last` suffix in filenames)
- `image` is a legacy alias for `first_image` (backward compat)
- Route handlers map `image` → `first_image` canonically

### Alternate Video Asset
- `alt_video` = alternative video asset (maps to `_alt` suffix in filenames)
- Purpose: reference video, upscaled footage, or any additional video variant
- Stored alongside regular videos in `shots/wip/SH###/videos/` and `shots/latest_videos/`
- Fully supported across upload, version management, prompt saving, thumbnail generation, playback (via `?type=alt_video`), captioning, export, and visual reorder

---

## Frontend Architecture

### Structure
- **Single SPA**: `app/templates/index.html` — one Jinja2 template, `{{ version }}` injected
- **CSS**: `app/static/css/main.css` (primary styles, dark theme default), `app/static/css/styles.css` (light theme overrides), `app/static/css/search-modal.css` (search modal styles), `app/static/css/visual-reorder.css` (visual reorder grid styles)
- **JavaScript**: 
  - `app/static/js/main.js` — monolithic SPA core: shot grid, TOC, upload, export, modals, drag-and-drop, theme toggle
  - `app/static/js/search-modal.js` — client-side search with in-memory index, multi-token matching, filter pills, keyboard nav
  - `app/static/js/visual-reorder.js` — drag-and-drop shot sorting grid, thumbnail switching, preview/edit modes
  - `app/static/js/modal-behavior.js` — centralized click-outside and Escape-key handling for all modals

### JavaScript Architecture
Key patterns:
- Theme toggle: persists preference in `localStorage` under `shotbuddy-theme`, toggles `.light-theme` on `<body>`
- Project state: uses `sessionStorage` to track whether user is in a project
- Event delegation: uses `data-*` attributes instead of inline `onclick` handlers
- TOC (Table of Contents): side panel rendered dynamically, supports filter/search, persists open/close state, collapsible archived section
- File upload: uses `FormData` with `file`, `shot_name`, `file_type` fields; shows loading states
- Cache busting: appends `?t=timestamp` to media URLs
- Modals: image/video viewers with keyboard arrow navigation; export modal with media type checkboxes; search modal with Ctrl+Shift+F shortcut; visual reorder modal with SortableJS
- Drag-and-drop: custom implementation for shot reordering with grip handle; SortableJS for visual reorder grid
- Dynamic page title: browser tab updates with project info and app version on screen transitions

### CSS Organization
- `main.css`: base layout, dark theme, shot grid, TOC panel, modals, tooltips, buttons, sticky header, drag-drop
- `styles.css`: light theme overrides only (loaded after main.css)
- `search-modal.css`: search modal layout, filter pills, snippet styling, keyboard focus
- `visual-reorder.css`: responsive 5-column grid, cards, thumbnail selectors, preview/edit mode styles

---

## Common Development Tasks

### Adding a New API Endpoint
1. Add route handler in `app/routes/shot_routes.py` or `project_routes.py`
2. If it needs shot data, get `ShotManager` via `get_shot_manager(project["path"])`
3. If it modifies data, call `project_manager.update_project_timestamp(project["path"])` after success
4. Return `jsonify({"success": True, "data": ...})` or `jsonify({"success": False, "error": "..."})` with appropriate HTTP code
5. Add the endpoint to the table in this AGENTS.md

### Adding a New Shot Asset Variant
1. Add allowed extensions check in `FileHandler.save_file()` if needed
2. Add canonical type mapping if aliasing (like `image` → `first_image`)
3. Add naming conventions and file patterns in `ShotManager` (detection, versioning, thumbnail, prompt paths)
4. Add prompt file path logic in `ShotManager._prompt_file_path()`
5. Add caption type validation in `ShotManager.save_caption()` if needed
6. Add version marker path in `ShotManager._version_marker_path()`
7. Add to `get_shot_info()` response dict with file, versions, thumbnail, prompt, caption
8. Add to `_rename_shot_files()` if the asset has rename logic
9. Add to `export_latest_assets()` if the asset should be exportable
10. Add to the frontend shot card rendering in `main.js`
11. Reference: `alt_video` (added in v4.0.0) is the most recent example — follow its patterns

### Adding a UI Component
1. Add HTML structure to `app/templates/index.html`
2. Add styles to the appropriate CSS file (new component-specific file or `main.css`) + light overrides in `styles.css`
3. Add JavaScript logic to the appropriate JS file (new component-specific file or `main.js`)
4. Use `data-*` attributes for event binding (follow existing pattern)
5. Register modal close behavior in `modal-behavior.js` if adding a new modal
6. Test in both light and dark themes

### Working with Dependencies
- **Adding**: `uv add package_name`
- **Removing**: `uv remove package_name`
- **Syncing**: `uv sync`
- **Running scripts**: `uv run script.py`
- Never use `pip install` directly

---

## Known Limitations & Gotchas

- **ffmpeg is optional**: video thumbnails silently fail if ffmpeg is not on PATH
- **tkinter for folder picker**: may not be available in headless environments; falls back to home directory with a warning
- **No database**: all state is in JSON files on disk; concurrent writes are not handled
- **Shot manager caching**: `ShotManager` instances are cached per project path in Flask app config; cache is cleared when project folder mtime changes
- **Legacy backward compat**: `image` → `first_image` mapping exists everywhere; old single-image finals are still recognized
- **Single-threaded Flask**: development server only; not for production deployment
- **Path normalization**: All paths internally use `/` (POSIX) via `_normalize_path()` regardless of OS
- **Sub-shot limit**: sub-shot numbers max at 999; only increments by 10 starting at 050
- **Main shot limit**: 999 shots max (gap-filling from 1–999)
- **Recent projects limit**: 6 max
- **Thumbnail size**: hardcoded to 240×180 in `constants.py`
- **Version detection**: `_detect_existing_versions()` scans filesystem to correct inaccurate version counts; runs when `max_version == 0`; results cached per shot/asset type for performance
- **Lazy thumbnails**: thumbnails are URL-computed eagerly but file-generated only on first HTTP request; this means `get_shot_info()` no longer blocks on thumbnail creation
- **Browser auto-open**: `run.py` spawns a daemon thread that waits for the server to be ready, then opens the default browser
- **Ruff ignores**: line-length (E501) and subprocess untrusted input (S603) are suppressed in pyproject.toml