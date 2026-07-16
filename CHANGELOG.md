# Changelog

## v4.2.0 (July 16, 2026) - by Taruma Sakti

This minor release introduces a self-contained HTML gallery export with sidebar navigation, copy-to-clipboard buttons, Markdown-rendered project notes, styled tag pills, and a meta card. The CSS codebase has been modularized into five focused files, and the light-theme class has been migrated from `body.light-theme` to `.light`. The backend service layer has been decomposed from a monolithic `shot_manager.py` into a facade orchestrating five sub-service modules. Several UI polish items and fixes round out the release.

### Added
- **HTML Gallery Export**: New `html` export format alongside the existing Markdown default. The self-contained HTML page includes:
  - Fixed sidebar TOC with anchor-link navigation
  - Copy-to-clipboard buttons on all prompt blocks
  - Markdown-rendered project notes (bold, italic, code, lists, headings, fenced code)
  - Styled tag pills replacing comma-separated tags
  - Meta card with badges for version, shot count, export date, created, and updated timestamps
  - Lazy-loaded images (`loading="lazy"`, `decoding="async"`) on shot cards for faster rendering
  The export format is selected via the new `export_format` parameter on the existing export endpoint. HTML generation logic lives in a dedicated `app/services/html_exporter.py` module, extracted from `ShotManager` for single-responsibility adherence.
- **Prompt Tooltip Middle Truncation**: Long prompts in thumbnail tooltips now truncate with a styled scissors-emoji separator (── ✂ ──) when they exceed 750 characters. The new `truncateMiddle()` function breaks on word boundaries and preserves readable beginning and end portions. Tooltip CSS also updated to `pre-line` to preserve newline formatting.
- **Zebra Striping on Shot Rows**: Alternating background colors on even-indexed shot rows (`.even` class added in `renderShots()`) improve visual distinction between entries in the shot grid. Styled for both dark and light themes with appropriate hover states.
- **Recent Project Card Transitions**: Smooth `background`, `border-color`, and `transform` transitions on hover (`translateY(-1px)`) and active (`translateY(0)`) states for recent project items, with light-theme overrides.

### Changed
- **Recent Projects Grid Width**: The setup screen's recent project grid container (`.recent-projects-grid`) is now capped at `max-width: 700px` for a more centered, readable layout.

### Fixed
- **Edge Video Playback Unresponsive**: Removed `content-visibility: auto` from `.sb-shot` cards in the HTML export CSS. The CSS containment property caused `<video>` controls in off-screen shot cards to skip initialization in Microsoft Edge, requiring repeated clicks to become responsive. Chrome was less affected. The lazy-loading images alone provide sufficient performance for large exports.
- **Scroll Position on Setup Transition**: Added `window.scrollTo(0,0)` in `showMainInterface()` to reset scroll position when transitioning from the setup screen, preventing the page from appearing scrolled-down after project load.
- **Prompt Version Validation & JSON Error Standardization**: The prompt save endpoint now validates the `version` parameter as an integer and returns a 400 error if invalid. All error responses across thumbnail serving, video/image/audio serving, and prompt saving have been standardized from plain-text strings to structured `{"success": false, "error": "..."}` JSON with proper HTTP status codes.

### Refactored
- **Python Service Decomposition**: The monolithic `shot_manager.py` has been split into a facade orchestrator and five focused sub-service modules:
  - `shot_utils.py` — shot name validation, parsing, formatting, cache factory (`get_shot_manager`)
  - `shot_order.py` — `ShotOrderManager` for display order + archive JSON I/O
  - `metadata.py` — `ShotMetadata` for notes, captions, and display-name CRUD
  - `prompts.py` — `PromptStore` for prompt file path resolution, CRUD, and version listing
  - `export_service.py` — `ExportService` for asset export and MD/HTML generation
  The `ShotManager` class now serves as a facade with lazy-initialized sub-service properties, preserving full backward compatibility with all route handlers. Each extracted module follows the Single Responsibility Principle with focused public APIs.
- **Modular CSS Architecture**: The monolithic CSS has been split into five focused modules — `core.css` (reset, buttons, forms), `layout.css` (header, TOC, setup, footer), `shot-grid.css` (grid, rows, thumbnails, drag-and-drop), `modals.css` (all modal styles), and `main.css` (remaining primary styles). Light theme overrides were consolidated in `styles.css`. As part of this refactor, the theme class was migrated from `body.light-theme` to `.light` in `search-modal.css`, and missing focus styles (`.notes-input`, `.asset-caption-input`, `.toc-filter`) and hover styles (`.drop-zone.empty`) were added to the light theme.

### Documentation
- **AGENTS.md Updated**: Documented the new HTML gallery export feature (endpoint parameter, `html_exporter.py` module, side effects), the modular CSS file structure (file responsibilities, line counts, load order), the decomposed Python service architecture (facade pattern, sub-service responsibilities, dependency diagram), and bumped the project version to 4.2.0.

### AI Development Attribution
This release was developed with AI assistance using Deepseek V4 pro with Cline in Plan and Act mode. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version enhances export capabilities with a polished HTML gallery and improves both CSS and Python maintainability through modularization and service decomposition.

## v4.1.0 (July 4, 2026) - by Taruma Sakti

### Added
- **Copy Shot Order button** in the export modal: copies a numbered, ordered list of all active shots (with display names if set) to the clipboard. Useful as a quick reference when working in external editors (e.g. Premiere Pro) where only SHXXX filenames are visible. Output format: `01. SH001 — Opening Scene`.
- **Export modal two-row button layout**: utility actions (Open Exports Folder, Copy Shot Order) in the first row spaced evenly; primary actions (Export, Cancel) centered in the second row. Layout uses new `.export-utility-row` CSS class with `flex-direction: column` on `.export-actions`.
- **Visual Reorder Image Preview**: Preview mode in the visual reorder modal now supports images (first frame and last frame) in addition to videos. Clicking a thumbnail opens the appropriate viewer — image modal for frames, video modal for videos/alt videos. Arrow-key navigation cycles through the visual reorder card DOM order for both image and video types.
- **Audio Asset Support**: New `audio` asset type supporting `.mp3`, `.wav`, `.ogg`, `.flac`, `.aac`, and `.m4a` formats alongside existing images and videos. Includes a dedicated `latest_audio` directory with `serve_audio` playback route, versioned WIP storage in `shots/wip/SH###/audio/` (naming pattern `SH###_audio_v001.mp3`), promotion support via `ShotManager.set_current_version()` in `FileHandler.save_file()`, and an audio table in markdown export reports. The hidden audio DOM element is constrained to `max-height: 100px` with `overflow-y: auto` to prevent viewport overflow. Shot grid layout adjusted to accommodate the new audio column with playback controls.
- **Audio Export Support**: Audio checkbox added to the export dialog in `confirmExport()`. Multi-media selection logic triggers `all` export type when multiple media categories are chosen (e.g., images + audio). Error messaging updated to reference audio alongside images and videos.
- **Audio Search Indexing**: Audio prompts and captions are now indexed in `buildSearchIndex()` within the search modal, allowing users to find shots by their audio metadata. Matches existing search coverage for video and image prompt/caption fields.

### Fixed
- **Thumbnail Click Broken for Display Names with Quotes**: Fixed a bug where clicking a video or image thumbnail silently failed when the shot's display name contained a single quote (e.g., "Ocean's Secret"). The unescaped quote broke the inline JavaScript `onclick` handler, producing a syntax error that prevented the preview modal from opening. Display names are now escaped before interpolation into `onclick` attributes in `createDropZone`.
- **Unnecessary Page Rebuilds on Archive/Display Name Edit**: Removed full DOM re-renders from `archiveShot()` and `saveDisplayName()` that caused the entire shot grid to flash/repaint on every archive/unarchive or display name edit. These operations now update only the affected element directly — the archive button SVG icon flips instantly, and the display name text updates inline. Notification reminds users to press F5 to refresh layout after bulk archiving. All other operations (create, rename, upload, reorder, export) are unaffected.
- **Project Info Data Loss Prevention**: Replaced duplicated default-project-info creation in `ProjectManager.update_project_timestamp()` with a call to `load_project_info()` when the info file is missing. If loading an existing but malformed `project_info.json` fails, a warning is logged and the update is skipped instead of overwriting with defaults, preventing potential data loss.

### Changed
- **Notification Position**: Notifications moved from `top: 20px` to `bottom: 20px` with a `translateY(20px)` slide-up animation on show/hide, preventing overlap with the sticky header navigation bar.

### AI Development Attribution
This release was developed with AI assistance using Deepseek V4 pro with Cline in Plan and Act mode. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

## v4.0.1 (June 3, 2026) - by Taruma Sakti

### Removed
- **PNG Prompt Auto-Import**: Removed the `prompt_importer.py` module that attempted to extract embedded A1111/ComfyUI generation parameters from uploaded PNGs. The feature was untested and not part of the maintainer's workflow (prompts are pasted manually). The manual prompt saving endpoint (`POST /api/shots/prompt`) is unaffected.

## v4.0.0 (June 3, 2026) - by Taruma Sakti

This major release rebrands the project from Shotbuddy to **ShotBase**, introduces shot search and visual reorder modals, adds alternative video asset support, and delivers a refined UI with performance improvements across the board.

### Added
- **Shot Search Modal**: Full client-side search across all shots' prompts, captions, notes, shot names, and display names. Features multi-token search with highlighted snippets, keyboard navigation (arrow keys + Enter), Ctrl+Shift+F global shortcut, and click-to-scroll to the matching shot in the main grid. Includes content filter pills (All/Prompts/Captions/Notes) and archive status filter (All/Active/Archived), with shot and display names always searchable regardless of active filter.
- **Visual Reorder Modal**: Drag-and-drop shot sorting grid with 5 responsive columns. Cards display thumbnails, display names, and shot codes. Includes thumbnail type switching (video, alt video, first frame, last frame), a preview mode that plays the shot's video directly from the grid with contextual navigation, and an edit mode for inline display name editing.
- **Alternative Video Asset**: New `alt_video` asset type that can be used for any purpose such as reference video, upscaled footage, or additional video variants. Fully supported across upload, version management, prompt saving, thumbnail generation, video playback, export, and the visual reorder modal.
- **Dynamic Page Title**: Browser tab now displays the current project title and version, falling back to the app version on the setup screen.
- **Lazy Thumbnail Generation**: Thumbnails are now generated on-demand when first requested by the browser, rather than eagerly during shot listing. This reduces filesystem overhead and speeds up initial page loads.
- **Export Enhancements**: Display name column added to markdown export tables. Alt video assets included in exports and metadata. New "Open Exports Folder" button in the export modal for quick access. Loading state with disabled buttons during export for better user feedback.
- **Sticky Header**: Header now sticks to the top of the viewport on scroll for persistent access to controls.
- **TOC Collapsible Archived Section**: Toggle button with chevron to show/hide archived shots in the table of contents, with visibility state persisted across sessions. Styled for both light and dark themes.

### Changed
- **Setup Card Consolidation**: Project open, new, and manual path input controls moved from the top menu bar into the setup screen card. The separate menu bar and its associated layout logic were removed, simplifying the interface.
- **Recent Projects Expanded**: Limit increased from 3 to 6 projects with a wider settings modal and CSS grid layout. Project titles are now shown instead of directory names, and long paths are truncated to prevent layout overflow.
- **Shot Grid Layout**: Reduced column widths and adjusted spacing for a more compact, readable layout. Improved text wrapping and spacing on drop placeholder elements.
- **Export Modal Layout**: Simplified form layout with inline export type checkboxes, grouped sections, and the folder picker moved to the bottom action bar.

### Removed
- **Lipsync Asset Support**: Removed all lipsync-related code (`driver`, `target`, `result` asset types). This feature was never implemented end-to-end and had no UI surface area. Backend upload validation now rejects these file types, and the lipsync storage directory is no longer created in new shot folders.

### Fixed
- **Footer Layout**: Footer now stays at the bottom of the page regardless of content height.
- **Page Scroll Behind Modals**: Background scrolling now prevented when the visual reorder modal is open.
- **Local Notes Sync**: Shot notes update in the UI immediately before the API call completes, providing instant feedback.
- **TOC Visibility**: Table of contents panel now properly hidden when returning to the setup screen.
- **Alt Video Prompt Saving**: Prompt saving now correctly includes alt video assets.
- **Recent Projects Overflow**: Layout now handles long project paths with text truncation.
- **Search Snippet Accuracy**: Improved snippet windowing, highlight marker lengths, and character cap for more readable search results.

### Performance
- **Cached Version Scans**: Version detection results are now cached per shot and asset type, eliminating redundant filesystem scans. Legacy image fallback logic only runs when modern naming finds nothing.
- **Archived Shot Cache**: Archived status cached once per shot listing call instead of repeated disk reads.
- **Lazy Thumbnail Generation**: Defers thumbnail creation to first browser request, reducing initial page load work.

### Refactored
- **Modal Close Behavior Centralized**: Click-outside and Escape-key closing logic extracted from individual modules into a single centralized handler, reducing duplication and making modal behavior more maintainable.

### Documentation
- **AGENTS.md Expanded**: Added quick-reference table with current project state and a complete API endpoint reference covering all 24 endpoints.
- **QWEN.md Removed**: Superseded by the expanded AGENTS.md.

### AI Development Attribution
This release was developed with AI assistance using Deepseek V4 pro with Cline in Plan and Act mode. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version significantly enhances shot organization with searchable, filterable shot discovery, drag-and-drop visual reordering, expanded asset type support, and a polished, rebranded interface — all while improving performance through lazy generation and caching.

## v3.4.0 (October 27, 2025) - by Taruma Sakti

This minor release introduces enhanced navigation capabilities, improved shot management workflows, and refined user experience for media browsing and project organization.

### Added
- **Gap-Filling Shot Numbering System**: Implemented intelligent shot numbering that fills gaps in sequences rather than using fixed increments, starting from 1 instead of 10 and supporting up to 999 shots for more efficient organization.
- **Enhanced Drag-and-Drop UI**: Added grippy handle to reorder items with improved visual feedback, animations, and better spacing for more intuitive shot organization.
- **Video Loop Playback**: Added loop attribute to video player for continuous automatic replay, improving user experience by providing uninterrupted playback.
- **Video Modal Navigation**: Added navigation arrows and keyboard support (arrow keys) for browsing between shots in video modal without closing the interface.
- **Image Modal Navigation**: Added keyboard navigation and arrow buttons for seamless browsing between images in the modal interface.
- **Version Detection Improvements**: Enhanced shot manager to detect existing versions for accurate version tracking, preventing conflicts when assets already exist and showing orange badges when multiple versions are available.

### AI Development Attribution
This release was developed with AI assistance using Cline's Plan/Act workflow, powered by the Deepseek v3.1 model. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version enhances media browsing experience and shot organization efficiency while maintaining backward compatibility.

## v3.3.0 (October 6, 2025) - by Taruma Sakti

This minor release introduces enhanced media serving capabilities, improved UI responsiveness, and code quality refinements for better user experience and maintainability.

### Added
- **Image and Video Serving Endpoints**: Added new routes `/image/<shot_name>` and `/video/<shot_name>` to serve promoted media files from latest_images and latest_videos directories with proper validation and error handling.
- **Media Modal UI**: Enhanced modal interfaces for both images and videos with responsive design, light theme support, and improved user experience for viewing shot assets.
- **Cache-Busting Parameters**: Added timestamp query parameters to media URLs to prevent browser caching issues and ensure users always see the latest versions.
- **Shot Order Persistence Helpers**: Extracted shot order loading and saving into dedicated `_load_shot_order` and `_save_shot_order` methods with improved error handling and duplicate removal.

### Changed
- **CSS Restructuring**: Reorganized main stylesheet with improved organization and maintainability, including reordering and grouping related styles, removing duplicates, and consolidating similar rules.
- **Server Reload Integration**: Replaced local shot updates with server reloads after creating new shots to ensure UI displays fresh data including server-side additions.
- **TOC Auto-Refresh**: Enhanced Table of Contents to automatically update after saving shot order changes for better UI consistency.
- **Code Formatting**: Improved code readability by removing excessive leading whitespace and maintaining consistent formatting across the codebase.

### Fixed
- **Shot Order Integration**: Fixed shot order persistence when creating new shots between existing ones by integrating order management into `create_shot_between` method.

### AI Development Attribution
This release was developed with AI assistance using Cline's Plan/Act workflow, powered by the Grok-4-Fast, Deepseek v3.1, and GPT-5 model. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version enhances media viewing capabilities and code maintainability while improving overall user experience.

## v3.2.0 (September 26, 2025) - by Taruma Sakti

This minor release focuses on code quality improvements, security enhancements, and UI/UX refinements for file uploads and exports.

### Added
- **Ruff Linting Configuration**: Added Ruff linting setup with custom rules (line-length=120, target-version=py313, select=E,F,I,UP,S; ignore=E501,S603) to enforce code style and security standards.

### Changed
- **Server Configuration**: Bound the Flask server to localhost (127.0.0.1) for local-only access, improving security in development environments.
- **Import Organization**: Reorganized imports across the codebase for better structure and maintainability.

### Fixed
- **Linting and Security Issues**: Resolved Ruff violations including formatting, empty try-except blocks, and subprocess security warnings (suppressed S603 for trusted calls). Auto-fixed imports where possible.
- **Upload UI Enhancements** (fix #5): Added loading states and immediate UI updates in `uploadFile` for shots, reducing perceived latency during asset uploads.
- **Export Summary Details** (fix #4): Enhanced export summaries in `shot_manager` to include project metadata (e.g., title, version) for better context in exported files.

### AI Development Attribution
This release was developed with AI assistance using Cline's Plan/Act workflow, powered by the Grok-4-Fast model. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version improves development hygiene and user feedback loops without introducing breaking changes.

## v3.1.0 (September 25, 2025) - by Taruma Sakti

This minor release introduces enhancements for project management and macOS compatibility.

### Added
- **Project Created Timestamp Preservation**: Implemented functionality to preserve and backfill project creation timestamps using folder ctime (fix #1).
- **macOS Folder Browser Support**: Enhanced folder browser with macOS support and debug hooks (fix #2).

### AI Development Attribution
This release was developed with AI assistance using various tools including Qwen Code, GPT-5, Grok Code Fast 1, and Code Supernova, with primary workflow using Qwen Code initial development followed by refinement through Cline with GPT-5 and Code Supernova. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

## v3.0.0 (September 24, 2025) - by Taruma Sakti

This major release introduces comprehensive project information management, enhanced export capabilities, UI/UX refinements including improved theming, and performance optimizations. All changes maintain backward compatibility while modernizing the application for professional AI filmmaking workflows.

### Added
- **Project Location Memory**: Added functionality to store and retrieve the last project location used during project creation. This improves user experience by providing a default location in the UI. Changes include backend storage in ProjectManager, a new API endpoint for fetching the location, and frontend updates to prefill the project location input.
- **Light Theme Styles for Export Modal**: Added CSS rules for the light theme in the export modal, including header colors, borders, backgrounds, and checkbox styles to ensure visual consistency with the overall light theme design.
- **Project Version and Subtitle Display**: Enhanced project header to show version and subtitle alongside title. Added CSS styles for layout, typography, and light/dark theme support. Updated JavaScript to dynamically populate and hide elements based on project info. Modified HTML structure for better semantic organization. This improves user experience by providing more context about the current project directly in the interface.
- **Compact Project Info Modal**: Updated CSS to reduce padding, margins, and input sizes for a tighter layout. Changed short description from textarea to text input for brevity. Added inline styling for version field to align label and input horizontally. This improves user experience by making the modal less cluttered and more efficient to fill out.
- **Project Info Metadata Fields**: Introduced 'short_description' and 'notes' fields in project info defaults across creation, loading, and saving methods. Implemented backward compatibility by mirroring 'description' to 'notes' when 'notes' is empty. Updated frontend modal to display and edit 'short_description', 'notes', and 'version' fields for better project metadata management.
- **Automatic Project Timestamp Updates**: Added calls to `project_manager.update_project_timestamp()` after successful operations like shot creation, file uploads, saving notes, captions, prompts, renames, reorders, promotions, and archiving in `shot_routes.py`. This ensures project timestamps are updated to track recent changes accurately.
- **Enhanced Export Modal with Media Selection**: Added comprehensive CSS styles for export modal, including form layout, custom checkboxes, and button enhancements for improved UI consistency. Updated JavaScript logic in confirmExport to handle new image and video selection checkboxes, determining export type dynamically. Enhanced HTML template with new form elements for export options, enabling users to select specific media types for export.
- **Export Latest Assets Endpoint**: Added a new POST /export route that enables exporting the latest images and videos for non-archived shots in custom order. The endpoint accepts parameters for export name, type (images/videos/all), inclusion of display name in filenames, and metadata generation. Implemented the export_latest_assets method to handle the logic: create an export directory, sanitize filenames, copy assets with ordered prefixes, and optionally generate metadata. This feature improves asset management by providing a structured way to export project assets for external use or backup.
- **SVG Button Icons and Styles**: Updated UI buttons to use scalable SVG icons instead of emojis for better consistency and accessibility. Added new CSS classes for icon buttons in main.css and light theme overrides in styles.css. Replaced TOC toggle icon in main.js with SVG for uniformity.
- **Back to Menu Button in Header**: Added a 'Back to Menu' button to the project header for improved navigation.
- **Project Info Management System**: Added project information management with CRUD operations. Project routes now include loading and creating project info files, plus new endpoints for retrieving and updating project metadata. The project manager service now handles project info file operations including creation, loading, and saving with proper error handling. Project info includes title, description, tags, creation/update timestamps, and version information stored in project_info.json files within each project directory.
- **Prompt Tooltips on Thumbnails**: Introduced tooltip functionality to display prompt text when hovering over preview or video thumbnails. Added corresponding CSS styles for tooltips, initializes tooltips on DOMContentLoaded, and ensures tooltips are reinitialized after TOC rendering. Enhances user experience by providing quick access to prompt information.
- **App Version Display on Index Page**: Added a utility function to read the app version from pyproject.toml and updated the index route and template to display the version alongside the logo. This improves visibility of the current application version for users.
- **Back to Top Button**: Introduced a floating Back to Top button with CSS styling, JavaScript scroll behavior, and markup in index.html. The button appears after scrolling down and smoothly scrolls the page to the top when clicked.
- **Collapsible Archived Section**: Introduces a collapsible 'Archived' section in the shot list with persistent open/close state, updated styling for both dark and light themes, and improved accessibility.
- **Native Folder Picker**: Introduces a native folder picker endpoint using tkinter with a fallback to the user's home directory. Updates the frontend to support opening and creating projects via dialogs, adds recent projects display, and refines the setup and modal UI for improved usability. Also updates the Python version requirement to >=3.13.1 in documentation and pyproject.toml.
- **Python-dotenv Integration**: Added python-dotenv to dependencies and updated run.py to load environment variables from a .env file at startup. This enables configuration via environment variables for improved flexibility.
- **GitHub Funding Configuration**: Created FUNDING.yml file for GitHub sponsors support.

### Changed
- **Project Routes Refactoring**: Refactored the create_project function to delegate directory creation and state management to the project_manager service. This centralizes logic, ensures consistent handling of recent projects, and reduces code duplication for better maintainability.
- **Recent Projects Management**: Updated logic to ensure current project is always first in recent projects list, even if already present, by removing and re-inserting at index 0, then limiting to 3 items. Added timestamp update for last_scanned to record when the project was last accessed. Reduced the maximum number of recent projects stored from 5 to 3 to streamline the list.
- **Shot Display Styling**: Shot display names in the table of contents are now wrapped in a span with the 'shot-display-name' class and styled as bold for better visibility. CSS rules for '.shot-display-name' have been added to ensure consistent bold styling across themes.
- **Shot Grid Layout Improvements**: Reduced the 'Shot Name' column width and adjusted padding for better layout. Changed white-space handling to allow wrapping, and updated drag handle info styling and placement for improved readability in both CSS and HTML.
- **Shot Version Update Optimization**: Replaces full shot row re-rendering with a targeted update of the specific drop zone when switching asset versions. This improves UI performance and reduces unnecessary DOM updates by updating only the relevant elements (version badge, thumbnail, and prompt button) for the changed asset.
- **Project State Persistence**: Adds logic to track whether the user is currently in a project using sessionStorage. This prevents auto-loading the last project on first load and ensures the correct UI is shown after refreshes or navigation.
- **Event Handling Refactoring**: Replaces inline onclick attributes with data attributes and adds event listeners for better code maintainability and to avoid escaping issues.
- **Modal and UI Layout Improvements**: Refactors manual path input controls for better layout and usability, including a link-style toggle button. Updates modal button styles and spacing for consistency.

### Fixed
- **Light Mode Theming Issues**: Replace inline styles with CSS classes for better theme support. Add proper light theme overrides for labels and input fields. Make 'Created' and 'Last Updated' fields properly adapt to light mode. Improve form structure with semantic CSS classes. Ensure all form elements have proper visibility in both themes.
- **Light Mode Text Contrast**: Fixed light mode text contrast and implemented floating theme toggle.
- **Code Cleanup**: Deleted the empty .action-header selector from main.css as it was not providing any styles and is no longer needed.

### Documentation
- **AGENTS.md Update**: Rewrote AGENTS.md to serve as a comprehensive project context document, replacing the contributor guide with sections on project overview, key features, technology stack, development tooling, project structure, and build instructions.
- **QWEN.md Addition**: Introduced QWEN.md with an overview of the Shotbuddy project, including features, technology stack, project structure, setup instructions, configuration options, development conventions, and descriptions of key components.
- **uv Dependency Management Documentation**: Added a section detailing the use of `uv` as the primary tool for dependency management, script execution, and virtual environment handling. Updated instructions and notes throughout to emphasize avoiding direct use of `pip install` in favor of `uv` commands.

### Technical Updates
- **Performance Improvements**: Optimized caching and file handling mechanisms; targeted DOM updates for better UI responsiveness.
- **Python Version Requirement**: Updated to >=3.13.1 in documentation and pyproject.toml for native folder picker support.

### AI Development Attribution
This release was developed with AI assistance using various tools including Qwen Code, GPT-5, Grok Code Fast 1, and Code Supernova, with primary workflow using Qwen Code initial development followed by refinement through Cline with GPT-5 and Code Supernova. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version significantly enhances project organization, export capabilities, and user experience for professional AI filmmaking workflows.

## v2.1.0 (September 23, 2025) - by Taruma Sakti

This minor release introduces enhanced backend performance and new reordering capabilities for improved project management workflows. All changes maintain backward compatibility while providing better user experience for shot organization.

### Added
- **Enhanced Shot Reordering**: New modal interface with filtering and drag support for improved project organization workflow
- **Progressive Web App Support**: Added favicon and manifest files for better web app experience

### Changed
- **Backend Architecture**: Refactored thumbnail cache to per-project directories for improved performance and organization
- **Thumbnail Rendering**: Improved aspect ratio handling to preserve original image proportions
- **UI Polish**: Updated grid layout and header styles for better visual consistency

### Technical Updates
- **Performance**: Optimized file handling and caching mechanisms
- **Code Quality**: Enhanced service layer architecture and route handling

### AI Development Attribution
This release was developed with AI assistance using Cline's Plan/Act workflow, powered by a mix of GPT-5 and Qwen3 Coder models. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version focuses on backend improvements and enhanced user experience for shot management workflows.

## v2.0.0 (September 23, 2025) - by Taruma Sakti

This major release extends the original Shotbuddy v1.0.0 by Albert Bozesan with new features focused on enhanced navigation, asset management, and usability for AI filmmaking workflows. All changes are backward-compatible, preserving legacy single-image support while adding project-scoped metadata and modern UI elements.

### Added
- **Table of Shots (TOC) Panel**: Responsive side panel for project overviews in docked or drawer modes. Supports shot filtering, quick navigation, active/archived separation, and highlighting. Integrates with reordering and themes.

- **Drag-and-Drop Shot Reordering**: Reorder shots in the grid with persistent per-project saving. Inline insertion points with "New Shot +" buttons.

- **Shot Archiving**: Toggle shots to hide inactive ones from the main grid while retaining assets. Dedicated archived section with one-click restore.

- **Human-Readable Display Names**: Custom titles for shots (e.g., "Opening Scene" for SH010), editable in grid/TOC. Stored in project-scoped `meta.json` for multi-project support.

- **Action Column with Icon Buttons**: Leftmost grid column for quick actions like archive/unarchive, using accessible SVG icons and tooltips.

- **First/Last Image Variants**: Separate slots for opening/closing frames per shot. Independent versioning, prompts, thumbnails, and promotion; legacy images map to first variant.

- **Asset Version Promotion and Cycling**: Click version badges to cycle/promote finals. Supports images/videos; auto-updates thumbnails and markers for up to 999 versions.

- **Asset Captions**: Editable text under media previews (first/last images, videos). Auto-saves to per-shot `captions.json` for notes or feedback.

- **Auto-Resizing Notes**: Dynamic textarea expansion for shot notes, removing scrollbars for better editing.

- **Light/Dark Theme Toggle**: Header button to switch themes, persisted in localStorage. Full UI overrides for contrast and readability.

- **Refined Header and Menu Layout**: Container-based structure with improved spacing, shadows, and borders.

- **uv Dependency Management**: Support for uv and pyproject.toml for reproducible environments, replacing manual venv/pip setup.

- **Expanded Documentation**: Detailed README with feature guides and GIF demos (reordering, archiving, TOC, display names, versions, variants, captions, notes, themes). Comprehensive AGENTS.md contributor guide (setup, config, layout, PEP8, testing).

### Changed
- **Project-Scoped Metadata**: Shot meta (display names, captions) now stored per-project for robust multi-project handling. Removed legacy app-level files.

- **Footer and Attribution**: Updated index.html footer with maintainer credit, GitHub link, and Cline attribution. Dual copyright in LICENSE.txt (Taruma Sakti / Albert Bozesan).

- **README Structure**: New "New Features in This Fork" section with summarized enhancements and visuals. Updated pyproject.toml authors/URLs.

- **Cursor Styles and Interactions**: Default cursors for non-clickable thumbnails; removed unintended handlers. Pointer cursors for interactive elements.

### Technical Updates
- **API Endpoints**: Added `/reorder`, `/archive`, `/display-name`, `/caption`, `/promote` for new features.
- **File Structure**: New `.shot_order.json` and `.archived_shots.json` per project; image variants use `_first`/`_last` prefixes.
- **Dependencies**: Flask, Flask-CORS, Pillow via pyproject.toml/requirements.txt.
- **No Breaking Changes**: Legacy workflows intact.

### AI Development Attribution
This release was developed with AI assistance using Cline's Plan/Act workflow, powered by a mix of GPT-5 and Qwen3 Coder models. All generated changes were manually reviewed, tested, and refined by the maintainer, Taruma Sakti, to ensure quality and alignment with project goals.

This version streamlines storyboard management for larger projects. For full details and demos, see README.md.