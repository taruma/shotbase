"""HTML export writer for shot-centric gallery pages.

Extracted from ``ShotManager`` to keep the service module focused on
shot data management.  The single entry point is ``write_html_export()``.
"""

import html as _html
import re
from datetime import datetime
from pathlib import Path


# ── embedded CSS ──────────────────────────────────────────────────────────
CSS = """\
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
  max-width: 900px;
  margin: 0 auto;
  padding: 48px 24px 32px;
  text-align: center;
  border-bottom: 1px solid var(--border);
}

.sb-title {
  font-size: 2.4em;
  font-weight: 700;
  margin-bottom: 6px;
  color: #fff;
  letter-spacing: -0.3px;
}

.sb-subtitle {
  color: var(--text-muted);
  font-style: italic;
  font-size: 1.05em;
  margin-bottom: 20px;
}

/* Tag pills */
.sb-tags {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.sb-tag {
  display: inline-block;
  background: rgba(91, 141, 239, 0.15);
  color: var(--accent);
  border: 1px solid rgba(91, 141, 239, 0.3);
  border-radius: 20px;
  padding: 3px 14px;
  font-size: 0.78em;
  font-weight: 500;
}

/* Meta card with badges */
.sb-meta-card {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 20px;
  font-size: 0.82em;
  color: var(--text-muted);
  margin-bottom: 0;
}

.sb-meta-badge {
  white-space: nowrap;
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
  content-visibility: auto;
  contain-intrinsic-size: auto 500px;
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

/* Project notes card */
.sb-project-notes {
  max-width: 800px;
  margin: 24px auto 0;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.sb-project-notes-label {
  background: var(--card-bg);
  padding: 10px 16px;
  font-size: 0.8em;
  font-weight: 600;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border);
}

.sb-project-notes-body {
  padding: 16px 20px;
  font-size: 0.9em;
  color: var(--text);
  line-height: 1.6;
}

.sb-project-notes-body p {
  margin-bottom: 10px;
}

.sb-project-notes-body ul {
  margin: 8px 0 12px 24px;
}

.sb-project-notes-body li {
  margin-bottom: 4px;
}

.sb-project-notes-body h3, .sb-project-notes-body h4 {
  color: var(--accent);
  margin: 16px 0 8px;
  font-size: 1.05em;
}

.sb-project-notes-body code {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 0.9em;
}

.sb-project-notes-body pre {
  background: var(--prompt-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  overflow-x: auto;
  margin: 10px 0;
}

.sb-project-notes-body pre code {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.85em;
}

.sb-project-notes-body strong {
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


# ── helpers ────────────────────────────────────────────────────────────────

def _esc(text):
    """Escape text for HTML content (not attributes)."""
    if not text:
        return ''
    return _html.escape(str(text))


def _sanitize_filename(name):
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


def _fmt_date(val):
    """Return a human-readable date string from an ISO or timestamp value."""
    if not val:
        return ''
    try:
        d = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
    except Exception:
        return ''
    return d.strftime('%b %d, %Y')


# ── main entry point ───────────────────────────────────────────────────────

# Audio MIME type lookup
_AUDIO_MIME_MAP = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.aac': 'audio/aac',
    '.m4a': 'audio/mp4',
}


def write_html_export(shot_manager, export_dir, non_archived_shots, project_info, export_type, timestamp):
    """Write a self-contained HTML gallery to ``export_dir/export_summary.html``.

    Parameters
    ----------
    shot_manager : ShotManager
        Used to call ``get_shot_info()`` on demand.
    export_dir : Path
        Already-created export directory.
    non_archived_shots : list[dict]
        Shot summary dicts (from ``ShotManager.get_shots()``).
    project_info : dict
        Contents of ``project_info.json``.
    export_type : str
        ``'images'``, ``'videos'``, ``'audio'``, or ``'all'``.
    timestamp : str
        ISO-formatted timestamp.
    """

    # --- Build asset info per shot ---
    shot_assets = []
    for order, shot in enumerate(non_archived_shots, start=1):
        shot_name = shot['name']
        display_name = shot['display_name'] or ''
        info = shot_manager.get_shot_info(shot_name)
        display_suffix = f"_{_sanitize_filename(display_name)}" if display_name else ''

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
    title = _esc(project_info.get('title', Path(export_dir).parent.parent.name))
    lines.append(f'<title>{title} — Export</title>')
    lines.append('<style>')
    lines.append(CSS)
    lines.append('</style>')
    lines.append('</head>')
    lines.append('<body>')

    # --- Sidebar TOC ---
    lines.append('<aside class="sb-sidebar" id="sidebar">')
    lines.append('<div class="sb-sidebar-title">Contents</div>')
    lines.append('<ul class="sb-sidebar-list">')
    for sa in shot_assets:
        label = f"{sa['name']} &middot; {_esc(sa['display_name'])}" if sa['display_name'] else sa['name']
        lines.append(f'<li><a href="#shot-{sa["order"]:03d}">{label}</a></li>')
    lines.append('</ul>')
    lines.append('</aside>')

    # --- Main content area ---
    lines.append('<div class="sb-content">')

    # Header
    lines.append('<header class="sb-header">')
    lines.append(f'<h1 class="sb-title">{title}</h1>')
    if project_info.get('short_description'):
        lines.append(f'<p class="sb-subtitle">{_esc(project_info.get("short_description"))}</p>')

    # Tag pills
    if project_info.get('tags'):
        lines.append('<div class="sb-tags">')
        for tag in project_info.get('tags', []):
            lines.append(f'<span class="sb-tag">{_esc(tag.strip())}</span>')
        lines.append('</div>')

    # Meta card
    lines.append('<div class="sb-meta-card">')
    meta_items = []
    if project_info.get('version'):
        meta_items.append(f'<span class="sb-meta-badge">v{_esc(project_info.get("version"))}</span>')
    meta_items.append(f'<span class="sb-meta-badge">{len(shot_assets)} shots</span>')
    meta_items.append(f'<span class="sb-meta-badge">Exported {_fmt_date(timestamp)}</span>')
    if project_info.get('created'):
        created_str = _fmt_date(project_info.get('created'))
        if created_str:
            meta_items.append(f'<span class="sb-meta-badge">Created {created_str}</span>')
    if project_info.get('updated'):
        updated_str = _fmt_date(project_info.get('updated'))
        if updated_str:
            meta_items.append(f'<span class="sb-meta-badge">Updated {updated_str}</span>')
    lines.append(' · '.join(meta_items))
    lines.append('</div>')

    # Project notes (Markdown rendered)
    if project_info.get('notes'):
        lines.append('<div class="sb-project-notes">')
        lines.append('<div class="sb-project-notes-label">📋 Project Notes</div>')
        lines.append('<div class="sb-project-notes-body">')
        lines.append(_md_to_html(project_info.get('notes', '')))
        lines.append('</div>')
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
            heading += f" — {_esc(display_name)}"

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
                lines.append(f'<a href="{first_rel}" target="_blank"><img src="{first_rel}" alt="First frame" class="sb-img" loading="lazy" decoding="async"></a>')
            if info['first_image'].get('caption'):
                lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {_esc(info["first_image"]["caption"])}</p>')
            if info['first_image'].get('prompt'):
                lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{_esc(info["first_image"]["prompt"])}</pre></div>')
            lines.append('</div>')

            # Last frame
            lines.append('<div class="sb-asset">')
            lines.append('<h4>Last Frame</h4>')
            if sa['has_last']:
                src = Path(info['last_image']['file'])
                ext = src.suffix
                last_rel = f"images/{order:03d}_{name}{display_suffix}_last{ext}"
                lines.append(f'<a href="{last_rel}" target="_blank"><img src="{last_rel}" alt="Last frame" class="sb-img" loading="lazy" decoding="async"></a>')
            if info['last_image'].get('caption'):
                lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {_esc(info["last_image"]["caption"])}</p>')
            if info['last_image'].get('prompt'):
                lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{_esc(info["last_image"]["prompt"])}</pre></div>')
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
                lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {_esc(info["video"]["caption"])}</p>')
            if info['video'].get('prompt'):
                lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{_esc(info["video"]["prompt"])}</pre></div>')
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
                lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {_esc(info["alt_video"]["caption"])}</p>')
            if info['alt_video'].get('prompt'):
                lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{_esc(info["alt_video"]["prompt"])}</pre></div>')
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
            mime = _AUDIO_MIME_MAP.get(ext.lower(), 'audio/mpeg')
            lines.append(f'<audio controls class="sb-audio"><source src="{aud_rel}" type="{mime}"></audio>')
            if info['audio'].get('caption') or info['audio'].get('prompt'):
                lines.append('<div class="sb-audio-info">')
                if info['audio'].get('caption'):
                    lines.append(f'<p class="sb-caption"><strong>Caption:</strong> {_esc(info["audio"]["caption"])}</p>')
                if info['audio'].get('prompt'):
                    lines.append(f'<div class="sb-prompt"><div class="sb-prompt-header"><strong>Prompt:</strong><button class="sb-copy-btn" onclick="copyPrompt(this)">📋 Copy</button></div><pre>{_esc(info["audio"]["prompt"])}</pre></div>')
                lines.append('</div>')
            lines.append('</div>')  # .sb-audio-row
            lines.append('</div>')  # .sb-section

        # --- Notes section ---
        if sa['has_notes']:
            lines.append('<div class="sb-section">')
            lines.append('<h3 class="sb-section-title">📝 Notes</h3>')
            lines.append(f'<div class="sb-notes">{_esc(info["notes"])}</div>')
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