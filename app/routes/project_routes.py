import logging
import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request

from app.config.constants import MAX_RECENT_PROJECTS
from app.services.shot_manager import clear_shot_manager_cache, get_shot_manager
from app.utils import get_app_version

logger = logging.getLogger(__name__)

project_bp = Blueprint('project', __name__)

@project_bp.route("/")
def index():
    version = get_app_version()
    return render_template("index.html", version=version)

@project_bp.route("/api/project/current")
def get_current_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if project:
            project_path = Path(project["path"])
            path_str = str(project_path)
            last_scanned = project_manager.projects.get("last_scanned", {}).get(path_str)
            folder_mtime = project_path.stat().st_mtime

            if (not last_scanned or
                    folder_mtime > datetime.fromisoformat(last_scanned).timestamp()):
                clear_shot_manager_cache()
                get_shot_manager(path_str).get_shots()
                project_manager.projects.setdefault("last_scanned", {})[path_str] = (
                    datetime.fromtimestamp(folder_mtime).isoformat()
                )
                project_manager.save_projects()
            return jsonify({"success": True, "data": project})
        return jsonify({"success": False, "error": "No current project"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/api/project/recent")
def get_recent_projects():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        recent_projects = []
        for project_path in project_manager.projects.get('recent_projects', []):
            p = Path(project_path)
            shots_dir = p / 'shots'
            if shots_dir.exists():
                created = datetime.fromtimestamp(p.stat().st_ctime).isoformat()
                recent_projects.append({
                    "name": p.name,
                    "path": str(p.resolve()),
                    "created": created,
                    "shots": []
                })
        return jsonify({"success": True, "data": recent_projects})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/api/project/open", methods=["POST"])
def open_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        project_path = data.get("path")
        if not project_path:
            return jsonify({"success": False, "error": "Project path required"}), 400
        from app.utils import sanitize_path
        project_path = sanitize_path(project_path).resolve()
        path_str = str(project_path)
        shots_dir = project_path / "shots"

        logger.debug("Received raw path from frontend: %s", request.get_json())
        logger.debug("Looking at path: %s", project_path)
        logger.debug("shots/ folder exists? %s", shots_dir.exists())

        if not shots_dir.exists():
            return jsonify({"success": False, "error": "No recognizable project structure"}), 400

        # Create project info file if it doesn't exist
        project_info = project_manager.load_project_info(project_path)

        project_data = {
            "name": project_path.name,
            "path": path_str,
            "created": datetime.fromtimestamp(project_path.stat().st_ctime).isoformat(),
            "info": project_info,
            "shots": []
        }

        # Ensure new folder layout exists
        (shots_dir / "wip").mkdir(parents=True, exist_ok=True)
        (shots_dir / "latest_images").mkdir(exist_ok=True)
        (shots_dir / "latest_videos").mkdir(exist_ok=True)

        # Update project manager state
        path_str = str(project_path)
        project_manager.projects['current_project'] = path_str

        # Always move the project to the front of recent projects
        recents = project_manager.projects.get('recent_projects', [])
        if path_str in recents:
            recents.remove(path_str)
        recents.insert(0, path_str)
        project_manager.projects['recent_projects'] = recents[:MAX_RECENT_PROJECTS]

        last_scanned = project_manager.projects.get('last_scanned', {}).get(path_str)
        folder_mtime = project_path.stat().st_mtime
        if (not last_scanned or
                folder_mtime > datetime.fromisoformat(last_scanned).timestamp()):
            clear_shot_manager_cache()
            shot_manager = get_shot_manager(path_str)
            shot_manager.get_shots()
            project_manager.projects.setdefault('last_scanned', {})[path_str] = (
                datetime.fromtimestamp(folder_mtime).isoformat()
            )
        project_manager.save_projects()

        return jsonify({"success": True, "data": project_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/create", methods=["POST"])
def create_project():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        project_name = data.get("name", "Untitled Project")
        selected_folder = data.get("path", ".")
        from app.utils import sanitize_path
        folder_path = sanitize_path(selected_folder).resolve()

        # Remember the location used for project creation
        project_manager.set_last_project_location(folder_path)

        # Create project via service (this handles recents correctly)
        project_info_obj = project_manager.create_project(folder_path, project_name)

        # Load project info for frontend (includes title, description, etc.)
        project_info = project_manager.load_project_info(project_info_obj["path"])

        project_data = {
            "name": project_name,
            "path": project_info_obj["path"],
            "created": project_info_obj["created"],
            "info": project_info,
            "shots": []
        }

        return jsonify({"success": True, "data": project_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/info", methods=["GET"])
def get_project_info():
    """Get project information for the current project"""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if project:
            return jsonify({"success": True, "data": project.get('info', {})})
        return jsonify({"success": False, "error": "No current project"}), 400
    except Exception as e:
        logger.error("Error in get_project_info: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/info", methods=["POST"])
def update_project_info():
    """Update project information for the current project"""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        data = request.get_json()
        
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400
        
        # Get the project path
        project_path = project['path']
        
        # Ensure project_path is a string (it might be a Path object)
        if hasattr(project_path, '__fspath__'):  # It's a Path-like object
            project_path = str(project_path)
        
        # Update project info
        updated_info = project_manager.save_project_info(project_path, data)
        
        return jsonify({"success": True, "data": updated_info})
    except Exception as e:
        logger.error("Error in update_project_info: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@project_bp.route("/api/project/last-location")
def get_last_project_location():
    """Get the last location used for project creation"""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        last_location = project_manager.get_last_project_location()
        return jsonify({"success": True, "data": {"path": last_location}})
    except Exception as e:
        logger.error("Error getting last project location: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500

@project_bp.route("/api/system/browse-folder")
def browse_folder():
    """Open a native folder picker dialog and return the selected path"""
    try:
        # Debug/test hooks (for testing fallback behavior on any OS)
        force_path = request.args.get("force_path")
        if force_path:
            return jsonify({"success": True, "data": {"path": force_path}})
        if request.args.get("force_warning") == "1":
            import os
            home_dir = os.path.expanduser("~")
            return jsonify({
                "success": True,
                "data": {"path": home_dir},
                "warning": "Native folder dialog not available. Defaulted to your home directory. You can manually edit the path."
            })
        if request.args.get("force_error") == "1":
            return jsonify({"success": False, "error": "Forced test error"}), 400

        # Try to use tkinter for native folder dialog first
        try:
            from tkinter import Tk, filedialog

            # Create and hide the root window
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)  # Bring dialog to front

            # Open folder dialog
            folder_path = filedialog.askdirectory(title="Select Project Folder")
            root.destroy()

            if not folder_path:
                return jsonify({"success": False, "error": "No folder selected"}), 400

            return jsonify({"success": True, "data": {"path": folder_path}})

        except ImportError:
            logger.info("Tkinter not available, trying alternative methods")
        except Exception as e:
            logger.warning("Tkinter failed: %s", e)

        # macOS fallback: AppleScript NSOpenPanel
        try:
            if sys.platform == "darwin":
                import shutil
                import subprocess
                script = 'POSIX path of (choose folder with prompt "Select Project Folder")'
                osascript_path = shutil.which("osascript")
                if osascript_path:
                    result = subprocess.run(
                        [osascript_path, "-e", script],
                        capture_output=True,
                        text=True,
                        check=True,
                        shell=False
                    )  # noqa: S603
                    folder_path = result.stdout.strip()
                    if folder_path:
                        return jsonify({"success": True, "data": {"path": folder_path}})
                    else:
                        return jsonify({"success": False, "error": "No folder selected"}), 400
                else:
                    raise FileNotFoundError("osascript not found")
        except Exception as e:
            logger.warning("AppleScript folder picker failed: %s", e)

        # Fallback: Return the user's home directory as a starting point
        # This allows the UI to show a sensible default and let the user manually edit the path
        import os
        home_dir = os.path.expanduser("~")
        return jsonify({
            "success": True,
            "data": {"path": home_dir},
            "warning": "Native folder dialog not available. Defaulted to your home directory. You can manually edit the path."
        })

    except Exception as e:
        logger.error("Error in browse_folder: %s", e)
        return jsonify({"success": False, "error": f"Failed to open folder dialog: {str(e)}"}), 500
