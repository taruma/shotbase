import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from app.config.constants import get_project_thumbnail_cache_dir
from app.services.file_handler import FileHandler
from app.services.shot_manager import get_shot_manager

shot_bp = Blueprint('shot', __name__)

@shot_bp.route("/", strict_slashes=False, methods=["GET"])
def get_shots():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shots = shot_manager.get_shots()
        return jsonify({"success": True, "data": shots})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/", methods=["POST"])
def create_shot():
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        next_number = shot_manager.get_next_shot_number()
        shot_name = f"SH{next_number:03d}"

        shot_manager.create_shot_structure(shot_name)
        shot_info = shot_manager.get_shot_info(shot_name)

        # Update project timestamp after successful shot creation
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": shot_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files.get('file')
        shot_name = request.form.get('shot_name')
        file_type = request.form.get('file_type')

        if not file or not shot_name or not file_type:
            return jsonify({"success": False, "error": "Missing required parameters"}), 400
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        file_handler = FileHandler(project['path'])
        result = file_handler.save_file(file, shot_name, file_type)

        # Update project timestamp after successful file upload
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": result})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/notes", methods=["POST"])
def save_shot_notes():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        notes = data.get("notes", "")

        if not shot_name:
            return jsonify({"success": False, "error": "Shot name required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_shot_notes(shot_name, notes)

        # Update project timestamp after successful notes save
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/caption", methods=["POST"])
def save_caption():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        caption = data.get("caption", "")

        if not shot_name or not asset_type:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_caption(shot_name, asset_type, caption)

        # Update project timestamp after successful caption save
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt", methods=["POST"])
def save_shot_prompt():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")
        prompt = data.get("prompt", "")

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_prompt(shot_name, asset_type, int(version), prompt)

        # Update project timestamp after successful prompt save
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt", methods=["GET"])
def get_shot_prompt():
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        version = request.args.get("version", type=int)

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        prompt = shot_manager.load_prompt(shot_name, asset_type, version)

        return jsonify({"success": True, "data": prompt})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/prompt_versions")
@shot_bp.route("/prompt-versions")
def get_prompt_versions():
    try:
        shot_name = request.args.get("shot_name")
        asset_type = request.args.get("asset_type")
        if not shot_name or not asset_type:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        versions = shot_manager.get_prompt_versions(shot_name, asset_type)
        return jsonify({"success": True, "data": versions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/rename", methods=["POST"])
def rename_shot():
    try:
        data = request.get_json()
        old_name = data.get("old_name")
        new_name = data.get("new_name")
        if not old_name or not new_name:
            return jsonify({"success": False, "error": "Old and new names required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.rename_shot(old_name, new_name)

        # Update project timestamp after successful shot rename
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/reorder", methods=["POST"])
def reorder_shots():
    try:
        data = request.get_json()
        shot_order = data.get("shot_order")

        if shot_order is None:
            return jsonify({"success": False, "error": "Shot order required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.save_shot_order(shot_order)

        # Update project timestamp after successful shot reorder
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/create-between", methods=["POST"])
def create_shot_between():
    try:
        data = request.get_json()
        after_shot = data.get("after_shot")

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.create_shot_between(after_shot)

        # Update project timestamp after successful shot creation
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/thumbnail/<path:filepath>")
def serve_thumbnail(filepath):
    """Serve a thumbnail from the current project's cache directory."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return "No current project", 400

        thumb_dir = get_project_thumbnail_cache_dir(project["path"]).resolve()
        thumb_path = (thumb_dir / Path(filepath).name).resolve()

        if not str(thumb_path).startswith(str(thumb_dir)):
            return "Invalid path", 400

        if thumb_path.is_file():
            resp = send_file(str(thumb_path))
            # Add strong caching headers
            mtime = thumb_path.stat().st_mtime
            resp.last_modified = datetime.fromtimestamp(mtime)
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            # Support conditional requests
            resp.add_etag()
            resp.make_conditional(request)
            return resp
        return "File not found", 404
    except Exception as e:
        return str(e), 500

@shot_bp.route("/reveal", methods=["POST"])
def reveal_file():
    try:
        data = request.get_json()
        rel_path = data.get("path")
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        file_path = Path(rel_path)
        if not file_path.is_absolute():
            file_path = (Path(project["path"]) / file_path).resolve()
        else:
            file_path = file_path.resolve()

        if not file_path.exists():
            return jsonify({"success": False, "error": f"File does not exist: {file_path}"}), 404

        if platform.system() == "Windows":
            explorer_path = shutil.which("explorer")
            if explorer_path:
                subprocess.Popen([explorer_path, '/select,', str(file_path)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("explorer not found")
        elif platform.system() == "Darwin":
            open_path = shutil.which("open")
            if open_path:
                subprocess.Popen([open_path, '-R', str(file_path)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("open not found")
        else:
            xdg_path = shutil.which("xdg-open")
            if xdg_path:
                subprocess.Popen([xdg_path, str(file_path.parent)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("xdg-open not found")

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shot_bp.route("/open-folder", methods=["POST"])
def open_shots_folder():
    """Open the current project's shots folder in the file browser."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shots_path = Path(project["path"]) / "shots"
        if not shots_path.exists():
            return jsonify({"success": False, "error": "Shots folder missing"}), 404

        if platform.system() == "Windows":
            explorer_path = shutil.which("explorer")
            if explorer_path:
                subprocess.Popen([explorer_path, str(shots_path)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("explorer not found")
        elif platform.system() == "Darwin":
            open_path = shutil.which("open")
            if open_path:
                subprocess.Popen([open_path, str(shots_path)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("open not found")
        else:
            xdg_path = shutil.which("xdg-open")
            if xdg_path:
                subprocess.Popen([xdg_path, str(shots_path)], shell=False)  # noqa: S603
            else:
                raise FileNotFoundError("xdg-open not found")

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shot_bp.route("/promote", methods=["POST"])
def promote_asset():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        asset_type = data.get("asset_type")
        version = data.get("version")

        if not shot_name or not asset_type or version is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_manager.promote_asset(shot_name, asset_type, int(version))
        shot_info = shot_manager.get_shot_info(shot_name)

        # Update project timestamp after successful asset promotion
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/archive", methods=["POST"])
def archive_shot():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        archived = data.get("archived")

        if not shot_name or archived is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.archive_shot(shot_name, bool(archived))

        # Update project timestamp after successful archive toggle
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": shot_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shot_bp.route("/export", methods=["POST"])
def export_latest_assets():
    try:
        data = request.get_json()
        export_name = data.get("export_name")
        export_type = data.get("export_type", "all")
        include_display_in_filename = data.get("include_display_in_filename", True)
        include_metadata = data.get("include_metadata", True)

        if export_type not in ['images', 'videos', 'all']:
            return jsonify({"success": False, "error": "Invalid export_type"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        shot_manager = get_shot_manager(project["path"])
        export_path = shot_manager.export_latest_assets(
            export_name=export_name,
            export_type=export_type,
            include_display_in_filename=include_display_in_filename,
            include_metadata=include_metadata
        )

        return jsonify({"success": True, "export_path": export_path})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@shot_bp.route("/video/<shot_name>")
def serve_video(shot_name):
    """Serve the promoted video file for a shot from latest_videos directory."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return "No current project", 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.get_shot_info(shot_name)
        
        # Support type query param for alt_video
        asset_type = request.args.get('type', 'video')
        if asset_type not in ('video', 'alt_video'):
            return "Invalid video type", 400
        
        # Get the promoted video file path
        video_path = shot_info[asset_type]['file']
        if not video_path:
            return f"No {asset_type} found for this shot", 404
            
        video_file = Path(video_path)
        if not video_file.exists():
            return "Video file not found", 404
            
        # Serve the video file with proper headers
        resp = send_file(str(video_file))
        resp.headers["Content-Disposition"] = f'inline; filename="{video_file.name}"'
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception as e:
        return str(e), 500

@shot_bp.route("/image/<shot_name>/<asset_type>")
def serve_image(shot_name, asset_type):
    """Serve the promoted image file for a shot from latest_images directory."""
    try:
        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return "No current project", 400

        shot_manager = get_shot_manager(project["path"])
        shot_info = shot_manager.get_shot_info(shot_name)
        
        # Validate asset type
        if asset_type not in ['first_image', 'last_image']:
            return "Invalid asset type", 400
            
        # Get the promoted image file path
        image_path = shot_info[asset_type]['file']
        if not image_path:
            return f"No {asset_type} found for this shot", 404
            
        image_file = Path(image_path)
        if not image_file.exists():
            return "Image file not found", 404
            
        # Serve the image file with proper headers
        resp = send_file(str(image_file))
        resp.headers["Content-Disposition"] = f'inline; filename="{image_file.name}"'
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp
    except Exception as e:
        return str(e), 500

@shot_bp.route("/display-name", methods=["POST"])
def set_display_name():
    try:
        data = request.get_json()
        shot_name = data.get("shot_name")
        display_name = data.get("display_name", "")

        if not shot_name:
            return jsonify({"success": False, "error": "Shot name required"}), 400

        project_manager = current_app.config['PROJECT_MANAGER']
        project = project_manager.get_current_project()
        if not project:
            return jsonify({"success": False, "error": "No current project"}), 400

        # Validate shot exists
        shot_manager = get_shot_manager(project["path"])
        shot_manager.get_shot_info(shot_name)  # Will raise if not found

        shot_manager.save_display_name(shot_name, display_name)
        updated_info = shot_manager.get_shot_info(shot_name)

        # Update project timestamp after successful display name save
        project_manager.update_project_timestamp(project["path"])

        return jsonify({"success": True, "data": updated_info})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
