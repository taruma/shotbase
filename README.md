<div align="center">
  <img src="./logo_shotbuddyv3.png" alt="ShotBase Logo" width="100"/>
</div>

<h1 align="center">ShotBase</h1>

<h3 align="center">(previously ShotBuddy V3)</h3>

<p align="center">
  <strong>Your AI Filmmaking Asset Manager.</strong>
  <br />
  An open-source tool designed to manage, organize, and streamline your entire AI-driven image-to-video workflow.
</p>

<p align="center">
  <img alt="Latest Release" src="https://img.shields.io/github/v/release/taruma/shotbase"/>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"/>
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.13.1%2B-blue"/>
</p>

---

ShotBase takes the chaos out of AI filmmaking. Instead of juggling countless generated files in messy folders, ShotBase provides a structured, visual, and intuitive interface to build your stories shot by shot. This fork supercharges the original with powerful project management, advanced version control, and a modern user experience tailored for today's creative workflows.

<p align="center">
  <img src="https://github.com/user-attachments/assets/e7ce1616-8936-49e8-a3fa-45403cd92203" alt="ShotBase Main Interface with Table of Contents"/>
</p>

## ✨ Key Features

This version of ShotBase is packed with features designed to make your workflow faster and more organized.

### 🆕 What's New in v4
- **Shot Search** — Press Ctrl+Shift+F to search across all shots' prompts, captions, notes, and names. Filter by content type and archive status for quick shot discovery.
- **Visual Reorder Grid** — Drag-and-drop shot sorting with a responsive 5-column layout, thumbnail type switching, video preview, and inline display name editing.
- **Alternative Video Asset** — New `alt_video` type for storing reference footage, upscales, or any additional video variant alongside your main video.
- **Export Enhancements** — Display name columns now included in markdown exports, alt video assets exported, and a new "Open Exports Folder" button for quick access.
- **UI Polish** — Sticky header stays visible on scroll, browser tab shows dynamic project title, and the table of contents has a collapsible archived section.
- **Performance** — Thumbnails generated lazily on first request, and version scans cached per shot for faster page loads.

### 🚀 Streamlined Project Management

- **Comprehensive Project Dashboard**: Get a bird's-eye view of your entire project with the responsive **Table of Shots (TOC)** panel. Filter, navigate, and see active vs. archived shots at a glance.
- **Effortless Shot Reordering**: Simply drag and drop shots to rearrange your sequence. Your story's flow is always just a move away.
  ![Effortless Shot Reordering](https://github.com/user-attachments/assets/c327eb21-b52d-4163-be52-c5d1c3178bce)
- **Flexible Archiving & Naming**: Keep your main workspace clean by archiving inactive shots. Give shots human-readable names like "Opening Scene" instead of just `SH010` for better clarity.
  ![Custom Display Names and Archiving](https://github.com/user-attachments/assets/0d87067d-def9-4d4e-a140-ee1188288d42)
- **Detailed Project Info**: Manage metadata for each project, including title, version, description, and tags, all from an intuitive modal.
  ![Project Information Management](https://github.com/user-attachments/assets/4dd9a394-2110-42db-91f8-a333fbfd948c)

### 🖼️ Powerful Asset & Version Control

- **First & Last Frame Variants**: Manage distinct opening and closing frames for each shot, complete with their own versions, prompts, and thumbnails.
  ![First and Last Frame Variants](https://github.com/user-attachments/assets/4286dc1c-7df9-45f0-afd5-acbacf5255da)
- **Instant Prompt Previews**: No more digging for prompt details. Simply hover over a thumbnail to see the exact prompt used to generate it.
  ![Instant Prompt Previews](https://github.com/user-attachments/assets/816a40ec-000b-4f6f-807e-51dcd5b305f1)
- **Automatic File Organization**: Drag and drop your generated images or videos. ShotBase automatically versions them, archives old iterations in a `wip` folder, and keeps the latest version ready for your pipeline.

### 💡 Enhanced User Experience

- **Advanced Export Options**: Precisely select what you want to export. Choose between images, videos, or both, and even include metadata summaries for a complete project handoff.
  <img src="https://github.com/user-attachments/assets/d1c0f1bb-d897-464b-bd07-0ca8559d9900" alt="Advanced Export Modal" width="500"/>
- **Seamless Light/Dark Theme**: Switch between light and dark modes with a single click. Your preference is saved automatically for your next session.
  ![Light/Dark Theme Toggle](https://github.com/user-attachments/assets/ec2f3e5e-33a3-4200-89cc-eae3cf70f1c6)
- **And much more**: Enjoy features like dynamic note fields that expand as you type, integrated asset captions, quick access to recent projects, shot search with Ctrl+Shift+F, visual drag-and-drop reorder grid, alternative video asset support, and sticky header.

## 🔧 Installation

Get started with ShotBase in just a few steps. Using `uv` is recommended for its speed and efficiency.

1.  **Clone the Repository**
    *(We use a shallow clone to download faster)*
    ```bash
    git clone --depth 1 https://github.com/taruma/shotbase.git
    cd shotbuddy
    ```

2.  **Install Dependencies**

    *   **(Recommended) Using `uv`:**
        ```bash
        # Install uv if you haven't: https://docs.astral.sh/uv/
        uv sync
        ```
    *   **Using `venv` and `pip`:**
        ```bash
        python -m venv .venv
        source .venv/bin/activate  # On Windows: .venv\Scripts\activate
        pip install -r requirements.txt
        ```

3.  **Run the Server**
    ```bash
    # If using uv
    uv run run.py

    # If using venv and pip
    python run.py
    ```

4.  **Open Your Browser**
    Navigate to **http://127.0.0.1:5001** to start using ShotBase!

## 📁 How It Works: Project Folder Structure

ShotBase automatically creates and maintains a clean, predictable folder structure for every project. This ensures your assets are always organized and easy to find.

```
project_folder/
├── shots/
│   ├── latest_images/    # The current, "promoted" image for each shot (e.g., SH010.png)
│   ├── latest_videos/    # The current, "promoted" video for each shot (e.g., SH010.mp4)
│   └── wip/              # Work-in-progress and old versions are archived here
│       └── SH010/
│           ├── images/   # e.g., SH010_v001.png, SH010_v002.png
│           └── videos/   # e.g., SH010_v001.mp4
└── project_info.json     # Metadata like title, version, and notes
```

## 📜 Attribution and License

This project is a fork that significantly extends and modernizes the original work.

-   **Forked from** Shotbuddy by Albert Bozesan ([@albozes](https://github.com/albozes/shotbuddy)).
-   **Maintained and extended by** Taruma Sakti.
-   This project is licensed under the **MIT License**.

This project is developed with AI assistance. For detailed attribution, see the `CHANGELOG.md`.
