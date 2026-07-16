import re
import shutil
from datetime import datetime
from pathlib import Path

from app.services.project_manager import ProjectManager


class ExportService:
    """Handles asset export and metadata generation (MD & HTML)."""

    def __init__(self, shot_manager):
        """*shot_manager* must be a ``ShotManager`` instance (used for ``get_shot_info``)."""
        self._sm = shot_manager
        self.project_path = shot_manager.project_path

    def export_latest_assets(self, export_name=None, export_type='all',
                             include_display_in_filename=True, include_metadata=True,
                             export_format='md'):
        """Export latest assets for non-archived shots in custom order."""
        # Get non-archived shots in order
        non_archived_shots = [s for s in self._sm.get_shots() if not s['archived']]
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
            info = self._sm.get_shot_info(shot_name)

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

    # ------------------------------------------------------------------
    # Markdown export
    # ------------------------------------------------------------------

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
            info = self._sm.get_shot_info(shot_name)

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

    # ------------------------------------------------------------------
    # HTML export (delegates to html_exporter module)
    # ------------------------------------------------------------------

    def _write_html_export(self, export_dir, non_archived_shots, project_info, export_type, timestamp):
        """Write HTML export — delegates to ``html_exporter`` module."""
        from app.services.html_exporter import write_html_export as _do_export
        _do_export(self._sm, export_dir, non_archived_shots, project_info, export_type, timestamp)