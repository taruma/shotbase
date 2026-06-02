let currentProject = null;
let shots = [];
let savedScrollY = 0;
let savedRowId = null;
let tocObserver = null;
const NEW_SHOT_DROP_TEXT = 'Drop an asset here to create a new shot.';
document.documentElement.style.setProperty('--new-shot-drop-text', `'${NEW_SHOT_DROP_TEXT}'`);

// Auto-resize notes textareas to fit content (no scrollbars)
function autoResize(textarea) {
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Resize all notes textareas (e.g. after grid becomes visible)
function autoResizeAllNotes() {
    document.querySelectorAll('.notes-input').forEach(autoResize);
}

// Wire auto-resize to all current and future .notes-input elements
document.addEventListener('input', (e) => {
    if (e.target && e.target.classList && e.target.classList.contains('notes-input')) {
        autoResize(e.target);
    }
});

// Theme functions
function applyTheme(theme) {
    document.body.classList.toggle('light', theme === 'light');
    localStorage.setItem('theme', theme);
    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.textContent = theme === 'light' ? '☀️' : '🌙';
    }
}

// Menu functions

async function browseFolder() {
    try {
        const response = await fetch('/api/system/browse-folder');
        const result = await response.json();

        if (result.success) {
            if (result.warning) {
                showNotification(result.warning, 'warning');
                // Show manual path fallback when native dialog isn't available
                toggleManualPath();
            }
            return result.data.path;
        } else {
            showNotification(result.error || 'Failed to open folder dialog', 'error');
            return null;
        }
    } catch (error) {
        console.error("Error browsing folder:", error);
        showNotification("Failed to open folder dialog", "error");
        return null;
    }
}

async function openProjectDialog() {
    const folderPath = await browseFolder();
    if (!folderPath) return;

    try {
        const response = await fetch('/api/project/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: folderPath })
        });

        const result = await response.json();

        if (result.success) {
            currentProject = result.data;
            showMainInterface();
            loadShots();
            showNotification(`Opened project "${result.data.name}"`);
        } else {
            showNotification(result.error || 'Failed to open project', 'error');
        }
    } catch (error) {
        console.error("Error loading project:", error);
        showNotification("Unexpected error loading project", "error");
    }
}

async function openRecentProject(projectPath) {
    try {
        const response = await fetch('/api/project/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: projectPath })
        });

        const result = await response.json();

        if (result.success) {
            currentProject = result.data;
            showMainInterface();
            loadShots();
            showNotification(`Opened project "${result.data.name}"`);
        } else {
            showNotification(result.error || 'Failed to open project', 'error');
        }
    } catch (error) {
        console.error("Error loading project:", error);
        showNotification("Unexpected error loading project", "error");
    }
}

async function loadProjectFromManualPath() {
    const input = document.getElementById('manual-path-input');
    const path = input.value.trim();

    if (!path) {
        showNotification("Please enter a full path to a project folder.", "error");
        return;
    }

    try {
        const response = await fetch('/api/project/open', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });

        const result = await response.json();

        if (result.success) {
            currentProject = result.data;
            showMainInterface();
            loadShots();
            showNotification(`Opened project "${result.data.name}"`);
        } else {
            showNotification(result.error || 'Failed to open project', 'error');
        }
    } catch (error) {
        console.error("Error loading project:", error);
        showNotification("Unexpected error loading project", "error");
    }
}

function toggleManualPath() {
    const fallback = document.getElementById('manual-path-fallback');
    const toggle = document.getElementById('manual-path-toggle');
    const showing = (fallback.style.display === 'none' || !fallback.style.display);
    fallback.style.display = showing ? 'flex' : 'none';
    if (toggle) toggle.setAttribute('aria-expanded', showing ? 'true' : 'false');
    if (showing) {
        const input = document.getElementById('manual-path-input');
        if (input) {
            input.focus();
            input.select();
        }
    }
}

async function browseProjectLocation() {
    const folderPath = await browseFolder();
    if (folderPath) {
        document.getElementById('new-project-location').value = folderPath;
    }
}

async function openCreateProjectModal() {
    document.getElementById('new-project-name').value = '';

    // Get the last project location and set it as default
    try {
        const response = await fetch('/api/project/last-location');
        const result = await response.json();

        if (result.success && result.data.path) {
            document.getElementById('new-project-location').value = result.data.path;
        } else {
            document.getElementById('new-project-location').value = '';
        }
    } catch (error) {
        console.error('Error fetching last project location:', error);
        document.getElementById('new-project-location').value = '';
    }

    document.getElementById('create-project-modal').style.display = 'flex';
    document.getElementById('new-project-name').focus();

    // Add Enter key listeners for better UX
    const nameInput = document.getElementById('new-project-name');
    const locationInput = document.getElementById('new-project-location');

    const handleEnter = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            confirmCreateProject();
            // Remove listeners after use
            nameInput.removeEventListener('keydown', handleEnter);
            locationInput.removeEventListener('keydown', handleEnter);
        }
    };

    nameInput.addEventListener('keydown', handleEnter);
    locationInput.addEventListener('keydown', handleEnter);
}

function closeCreateProjectModal() {
    document.getElementById('create-project-modal').style.display = 'none';
}

async function confirmCreateProject() {
    const locationPath = document.getElementById('new-project-location').value.trim();
    const projectName = document.getElementById('new-project-name').value.trim();

    if (!locationPath) {
        showNotification("Please select a location for the project.", "error");
        return;
    }
    if (!projectName) {
        showNotification("Please enter a project name.", "error");
        return;
    }

    try {
        const response = await fetch('/api/project/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: locationPath, name: projectName })
        });

        const result = await response.json();

        if (result.success) {
            currentProject = result.data;
            closeCreateProjectModal();
            showMainInterface();
            loadShots();
            showNotification(`Created project "${result.data.name}"`);
        } else {
            showNotification(result.error || 'Failed to create project', 'error');
        }
    } catch (error) {
        console.error('Error creating project:', error);
        showNotification('Unexpected error creating project', 'error');
    }
}


// Initialize app
document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', handlePromptButtonClick);
    const saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved);
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        const next = document.body.classList.contains('light') ? 'dark' : 'light';
        applyTheme(next);
    });
    createTocUI(); // Inject TOC panel and toggle button
    window.addEventListener('resize', positionToc); // Re-position on resize
    checkForProject();
    initTooltips(); // Initialize tooltip functionality
});

function handlePromptButtonClick(event) {
    const btn = event.target.closest('.prompt-button');
    if (!btn) {
        return;
    }
    event.stopPropagation();
    const shot = btn.dataset.shot;
    const type = btn.dataset.type;

    // For image/video we set data-current-version and data-max-version.
    // For lipsync we still have only data-version; treat it as both current and max.
    let currentVersion = btn.dataset.currentVersion ? parseInt(btn.dataset.currentVersion, 10) : undefined;
    let maxVersion = btn.dataset.maxVersion ? parseInt(btn.dataset.maxVersion, 10) : undefined;

    if (currentVersion == null || Number.isNaN(currentVersion)) {
        const v = parseInt(btn.dataset.version, 10);
        currentVersion = Number.isNaN(v) ? 1 : v;
    }
    if (maxVersion == null || Number.isNaN(maxVersion)) {
        const v = parseInt(btn.dataset.version, 10);
        maxVersion = Number.isNaN(v) ? currentVersion : v;
    }

    openPromptModal(shot, type, currentVersion, maxVersion);
}

async function checkForProject() {
    // Check if we're already in a project (e.g., after refresh)
    const isInProject = sessionStorage.getItem('inProject') === 'true';

    if (isInProject) {
        // We're already in a project, so just reload the shots
        // But first we need to get the current project data
        try {
            const response = await fetch('/api/project/current');
            const result = await response.json();

            if (result.success && result.data) {
                currentProject = result.data;
                showMainInterface();
                loadShots();
            } else {
                showSetupScreen();
                sessionStorage.removeItem('inProject');
            }
        } catch (error) {
            console.error('Error checking project:', error);
            showSetupScreen();
            sessionStorage.removeItem('inProject');
        }
    } else {
        // On first load, don't auto-load recent project - show setup screen
        showSetupScreen();
    }
}

function showSetupScreen() {
    document.getElementById('setup-screen').style.display = 'flex';
    document.getElementById('main-interface').style.display = 'none';
    loadRecentProjects();
    // Clear flag to indicate we're not in a project
    sessionStorage.removeItem('inProject');
}

async function loadRecentProjects() {
    try {
        const response = await fetch('/api/project/recent');
        const result = await response.json();

        const recentSection = document.getElementById('recent-projects-section');
        const recentList = document.getElementById('recent-projects-list');

        if (result.success && result.data && result.data.length > 0) {
            recentSection.style.display = 'block';
            recentList.innerHTML = '';

            result.data.forEach(project => {
                const projectItem = document.createElement('div');
                projectItem.className = 'recent-project-item';
                projectItem.innerHTML = `
                            <div class="recent-project-info">
                                <div class="recent-project-name">${escapeHtml(project.name)}</div>
<div class="recent-project-path" title="${escapeHtml(project.path)}">${escapeHtml(project.path)}</div>
                            </div>
                            <button class="dark-button" data-project-path="${project.path}">Open</button>
                        `;
                // Add event listener to the button to avoid escaping issues with onclick attribute
                const openButton = projectItem.querySelector('button');
                openButton.addEventListener('click', function () {
                    openRecentProject(this.getAttribute('data-project-path'));
                });
                recentList.appendChild(projectItem);
            });
        } else {
            recentSection.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading recent projects:', error);
        document.getElementById('recent-projects-section').style.display = 'none';
    }
}

function updateProjectHeader(info, fallbackName) {
    const titleEl = document.getElementById('project-title-text');
    const versionEl = document.getElementById('project-version');
    const subtitleEl = document.getElementById('project-subtitle');
    if (!titleEl || !versionEl || !subtitleEl) return;

    const title = (info && info.title) ? info.title : (fallbackName || 'Untitled Project');
    const version = (info && info.version) ? `v${info.version}` : '';
    const subtitle = (info && info.short_description) ? info.short_description : '';

    titleEl.textContent = title;
    versionEl.textContent = version;
    subtitleEl.textContent = subtitle;

    // Hide version element if no version
    versionEl.style.display = version ? 'inline' : 'none';
    // Hide subtitle row if empty
    subtitleEl.style.display = subtitle ? 'block' : 'none';
}

function showMainInterface() {
    document.getElementById('setup-screen').style.display = 'none';
    document.getElementById('main-interface').style.display = 'block';
    updateProjectHeader(currentProject.info || {}, currentProject.name);
    const input = document.getElementById('manual-path-input');
    if (input && currentProject && currentProject.path) {
        input.value = currentProject.path;
    }
    // Set flag to indicate we're in a project
    sessionStorage.setItem('inProject', 'true');
}

async function loadShots(rowId = null) {
    captureScroll(rowId);
    document.getElementById('loading').style.display = 'block';
    document.getElementById('shot-grid').style.display = 'none';

    try {
        const response = await fetch('/api/shots');
        const result = await response.json();

        if (result.success) {
            shots = result.data;
            renderShots();
            document.getElementById('loading').style.display = 'none';
            document.getElementById('shot-grid').style.display = 'block';
            // Ensure layout is visible before measuring scrollHeight
            requestAnimationFrame(() => requestAnimationFrame(autoResizeAllNotes));
            restoreScroll();
        } else {
            showNotification(result.error || 'Failed to load shots', 'error');
        }
    } catch (error) {
        console.error('Error loading shots:', error);
        showNotification('Error loading shots', 'error');
        document.getElementById('loading').style.display = 'none';
    }
}

// --- Table of Shots (TOC) Functions ---

function createTocUI() {
    const headerControls = document.querySelector('.header-controls');
    if (!headerControls) return;

    // Create TOC toggle button
    const tocToggle = document.createElement('button');
    tocToggle.id = 'toc-toggle';
    tocToggle.className = 'dark-button icon-button';
    tocToggle.title = 'Toggle Table of Shots';
    tocToggle.setAttribute('aria-label', 'Toggle Table of Shots');
    tocToggle.setAttribute('aria-controls', 'shot-toc');
    tocToggle.setAttribute('aria-expanded', 'false');
    tocToggle.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>';
    tocToggle.addEventListener('click', toggleTocPanel);
    headerControls.appendChild(tocToggle);

    // Create TOC panel container
    const tocPanel = document.createElement('aside');
    tocPanel.id = 'shot-toc';
    tocPanel.className = 'shot-toc';
    tocPanel.setAttribute('role', 'navigation');
    tocPanel.setAttribute('aria-label', 'Table of Shots');
    document.body.appendChild(tocPanel);

    // Initial positioning and mode
    positionToc();
}

function positionToc() {
    const toc = document.getElementById('shot-toc');
    const grid = document.querySelector('.shot-grid');
    const header = document.querySelector('.header');

    if (!toc || !grid) return;

    const gridRect = grid.getBoundingClientRect();
    const headerHeight = header ? header.offsetHeight : 0;
    const topOffset = Math.max(20, headerHeight + 10);
    const availableWidth = window.innerWidth - gridRect.right - 32;

    // Determine mode: docked or drawer
    if (availableWidth >= 260) {
        toc.classList.remove('mode-drawer');
        toc.classList.add('mode-docked');
        toc.style.top = `${topOffset}px`;
        toc.style.bottom = '16px';
        toc.style.display = localStorage.getItem('tocOpen') === 'false' ? 'none' : 'block';
    } else {
        toc.classList.remove('mode-docked');
        toc.classList.add('mode-drawer');
        toc.style.display = 'none'; // Hidden by default in drawer mode
    }
}

function toggleTocPanel() {
    const toc = document.getElementById('shot-toc');
    const toggle = document.getElementById('toc-toggle');
    if (!toc || !toggle) return;

    const isOpen = toc.classList.contains('mode-drawer') ?
        toc.classList.contains('open') :
        toc.style.display !== 'none';

    if (isOpen) {
        toc.classList.remove('open');
        toc.style.display = 'none';
        toggle.setAttribute('aria-expanded', 'false');
        localStorage.setItem('tocOpen', 'false');
    } else {
        toc.classList.add('open');
        toc.style.display = 'block';
        toggle.setAttribute('aria-expanded', 'true');
        localStorage.setItem('tocOpen', 'true');
    }
}

function renderTOC() {
    const toc = document.getElementById('shot-toc');
    if (!toc) return;

    const activeShots = shots.filter(s => !s.archived);
    const archivedShots = shots.filter(s => s.archived);

    // Clear and rebuild
    toc.innerHTML = `
                <div class="toc-header">
                    <span>Table of Shots</span>
                    <button class="dark-button icon-button" onclick="toggleTocPanel()" aria-label="Close TOC">&times;</button>
                </div>
                <input type="text" class="toc-filter" placeholder="Filter shots..." oninput="filterTocItems(this.value)">
                <div class="toc-section">
                    <div class="toc-section-title">Active Shots (${activeShots.length})</div>
                    <ul class="toc-list" id="toc-active-list"></ul>
                </div>
            `;

    const activeList = document.getElementById('toc-active-list');
    activeShots.forEach(shot => {
        const item = document.createElement('li');
        item.className = 'toc-item';
        item.innerHTML = shot.display_name
            ? `<span class="shot-display-name">${escapeHtml(shot.display_name)}</span> <span class="shot-code">(${shot.name})</span>`
            : shot.name;
        item.dataset.target = `shot-row-${shot.name}`;
        item.addEventListener('click', () => scrollToShot(shot.name));
        activeList.appendChild(item);
    });

    if (archivedShots.length > 0) {
        const archivedSection = document.createElement('div');
        archivedSection.className = 'toc-section';
        archivedSection.innerHTML = `
                    <div class="toc-section-title">Archived Shots (${archivedShots.length})</div>
                    <ul class="toc-list" id="toc-archived-list"></ul>
                `;
        toc.appendChild(archivedSection);

        const archivedList = document.getElementById('toc-archived-list');
        archivedShots.forEach(shot => {
            const item = document.createElement('li');
            item.className = 'toc-item archived';
            item.innerHTML = shot.display_name
                ? `<span class="shot-display-name">${escapeHtml(shot.display_name)}</span> <span class="shot-code">(${shot.name})</span>`
                : shot.name;
            item.dataset.target = `shot-row-${shot.name}`;
            item.addEventListener('click', () => scrollToShot(shot.name));
            archivedList.appendChild(item);
        });
    }

    // Set up IntersectionObserver to highlight active item
    setupTocObserver();
}

function filterTocItems(query) {
    const items = document.querySelectorAll('.toc-item');
    query = query.toLowerCase();
    items.forEach(item => {
        const match = item.textContent.toLowerCase().includes(query);
        item.style.display = match ? 'block' : 'none';
    });
}

function scrollToShot(shotName) {
    const targetId = `shot-row-${shotName}`;
    const el = document.getElementById(targetId);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Flash highlight
        el.style.transition = 'background 0.5s';
        el.style.background = '#3a3a5a';
        setTimeout(() => {
            el.style.background = '';
        }, 1000);
    }
    // Close drawer if in drawer mode
    const toc = document.getElementById('shot-toc');
    if (toc.classList.contains('mode-drawer')) {
        toggleTocPanel();
    }
}

function setupTocObserver() {
    if (tocObserver) {
        tocObserver.disconnect();
    }

    tocObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const targetId = entry.target.id;
            const tocItem = document.querySelector(`.toc-item[data-target="${targetId}"]`);
            if (tocItem) {
                tocItem.classList.toggle('active', entry.isIntersecting);
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.shot-row').forEach(row => {
        tocObserver.observe(row);
    });
}

function renderShots() {
    const shotList = document.getElementById("shot-list");
    shotList.innerHTML = "";

    const activeShots = shots.filter(s => !s.archived);
    const archivedShots = shots.filter(s => s.archived);

    // Active section container
    const activeContainer = document.createElement("div");
    activeContainer.id = "active-shot-list";

    // Create drop zones for active section
    const finalDropZone = document.createElement("div");
    finalDropZone.className = "drop-between-rows final-drop new-shot-drop-zone";
    finalDropZone.addEventListener("dragover", handleRowDragOver);
    finalDropZone.addEventListener("drop", handleRowDrop);
    finalDropZone.addEventListener("dragleave", handleRowDragLeave);
    const finalBtn = document.createElement("button");
    finalBtn.className = "green-button new-shot-btn inline-new-shot-btn";
    finalBtn.textContent = "New Shot +";
    finalBtn.addEventListener("click", () => {
        addNewShotAfter(finalDropZone.getAttribute("data-after-shot"));
    });
    finalDropZone.appendChild(finalBtn);

    const firstDropZone = document.createElement("div");
    firstDropZone.className = "drop-between-rows first-drop";
    firstDropZone.setAttribute("data-after-shot", "");
    firstDropZone.addEventListener("dragover", handleRowDragOver);
    firstDropZone.addEventListener("drop", handleRowDrop);
    firstDropZone.addEventListener("dragleave", handleRowDragLeave);
    const firstBtn = document.createElement("button");
    firstBtn.className = "green-button new-shot-btn inline-new-shot-btn";
    firstBtn.textContent = "New Shot +";
    firstBtn.addEventListener("click", () => {
        addNewShotAfter(firstDropZone.getAttribute("data-after-shot"));
    });
    firstDropZone.appendChild(firstBtn);

    if (activeShots.length === 0) {
        finalDropZone.classList.add("empty-state");
        finalDropZone.setAttribute("data-after-shot", "");
        activeContainer.appendChild(finalDropZone);
    } else {
        activeContainer.appendChild(firstDropZone);

        activeShots.forEach((shot, index) => {
            const shotRow = createShotRow(shot);
            activeContainer.appendChild(shotRow);

            if (index < activeShots.length - 1) {
                const dropBetween = document.createElement("div");
                dropBetween.className = "drop-between-rows";
                dropBetween.setAttribute("data-after-shot", shot.name);
                dropBetween.addEventListener("dragover", handleRowDragOver);
                dropBetween.addEventListener("drop", handleRowDrop);
                dropBetween.addEventListener("dragleave", handleRowDragLeave);
                const btn = document.createElement("button");
                btn.className = "green-button new-shot-btn inline-new-shot-btn";
                btn.textContent = "New Shot +";
                btn.addEventListener("click", () => {
                    addNewShotAfter(dropBetween.getAttribute("data-after-shot"));
                });
                dropBetween.appendChild(btn);
                activeContainer.appendChild(dropBetween);
            }
        });

        finalDropZone.setAttribute("data-after-shot", activeShots[activeShots.length - 1].name);
        activeContainer.appendChild(finalDropZone);
    }

    shotList.appendChild(activeContainer);

    // Archived section (collapsible)
    if (archivedShots.length > 0) {
        const archivedSection = document.createElement("div");
        archivedSection.id = "archived-section";
        archivedSection.className = "archived-section";

        // Check localStorage for saved state, default to closed
        const isArchivedOpen = localStorage.getItem('archivedOpen') === 'true';
        if (isArchivedOpen) {
            archivedSection.classList.add('open');
        }

        // Create header with toggle button
        const archivedHeader = document.createElement("button");
        archivedHeader.className = "archived-header";
        archivedHeader.setAttribute('aria-expanded', isArchivedOpen ? 'true' : 'false');
        archivedHeader.setAttribute('aria-controls', 'archived-shot-list');
        archivedHeader.innerHTML = `
                    <span class="chevron" aria-hidden="true">${isArchivedOpen ? '▾' : '▸'}</span>
                    <span>Archived</span>
                    <span class="count">(${archivedShots.length})</span>
                `;

        archivedHeader.addEventListener('click', toggleArchivedSection);

        // Create content container
        const archivedContainer = document.createElement("div");
        archivedContainer.id = "archived-shot-list";
        archivedContainer.className = "archived-content";
        archivedContainer.style.display = isArchivedOpen ? 'block' : 'none';

        archivedShots.forEach(shot => {
            const row = createShotRow(shot);
            archivedContainer.appendChild(row);
        });

        archivedSection.appendChild(archivedHeader);
        archivedSection.appendChild(archivedContainer);
        shotList.appendChild(archivedSection);
    }

    // Initialize auto-resize for all existing .notes-input elements
    document.querySelectorAll('.notes-input').forEach(autoResize);
    restoreScroll();
    initSortable();

    // Render and update TOC
    renderTOC();
    positionToc(); // Re-calculate position in case grid changed

    // Reinitialize tooltips after rendering
    setTimeout(initTooltips, 100);
}

function toggleArchivedSection() {
    const archivedSection = document.getElementById('archived-section');
    const archivedContent = document.getElementById('archived-shot-list');
    const archivedHeader = this;
    const chevron = archivedHeader.querySelector('.chevron');

    const isOpen = archivedSection.classList.toggle('open');
    archivedContent.style.display = isOpen ? 'block' : 'none';
    archivedHeader.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    chevron.textContent = isOpen ? '▾' : '▸';

    // Persist state to localStorage
    localStorage.setItem('archivedOpen', isOpen ? 'true' : 'false');
}

function initSortable() {
    const activeList = document.getElementById('active-shot-list');
    if (!activeList) return;

    new Sortable(activeList, {
        animation: 150,
        handle: '.shot-name',
        onEnd: async function (evt) {
            const shotOrder = Array.from(activeList.children)
                .filter(child => child.classList.contains('shot-row'))
                .map(child => child.id.replace('shot-row-', ''));

            try {
                const response = await fetch('/api/shots/reorder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ shot_order: shotOrder })
                });
                const result = await response.json();
                if (result.success) {
                    showNotification('Shot order saved');
                    // Re-sync the local shots array with the new order
                    shots.sort((a, b) => shotOrder.indexOf(a.name) - shotOrder.indexOf(b.name));
                    // Update the TOC to reflect the new shot order
                    renderTOC();
                } else {
                    showNotification(result.error || 'Failed to save order', 'error');
                }
            } catch (error) {
                console.error('Error saving shot order:', error);
                showNotification('Error saving shot order', 'error');
            }
        }
    });
}

// Helper to safely escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function createShotRow(shot) {
    const row = document.createElement('div');
    row.className = 'shot-row' + (shot.archived ? ' archived' : '');
    row.id = `shot-row-${shot.name}`;

    const actionLabel = shot.archived ? 'Unarchive' : 'Archive';
    const actionNext = shot.archived ? false : true;

    const labelText = shot.display_name
        ? `${escapeHtml(shot.display_name)}<div class="shot-code">(${shot.name})</div>`
        : shot.name;

    row.innerHTML = `
                <div class="action-cell">
                    <button class="icon-btn" title="${actionLabel}" aria-label="${actionLabel}" onclick="event.stopPropagation(); archiveShot('${shot.name}', ${actionNext})">
                        ${shot.archived
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="7 14 12 9 17 14"></polyline><line x1="12" y1="9" x2="12" y2="21"></line><rect x="3" y="3" width="18" height="6" rx="2"></rect></svg>'
            : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line><rect x="3" y="15" width="18" height="6" rx="2"></rect></svg>'}
                    </button>
                </div>
                <div class="shot-name" onclick="editDisplayName(this, '${shot.name}')">${labelText}</div>
                ${createDropZone(shot, 'first_image')}
                ${createDropZone(shot, 'last_image')}
                ${createDropZone(shot, 'video')}
                ${createDropZone(shot, 'alt_video')}
                ${'' /* createLipsyncZone(shot) */}
                <div class="notes-cell">
                    <textarea class="notes-input" 
                              placeholder="Add notes..." 
                              onchange="saveNotes('${shot.name}', this.value)"
                              onblur="saveNotes('${shot.name}', this.value)">${shot.notes || ''}</textarea>
                </div>
            `;

    // Set data attribute for display name to avoid quote issues in onclick
    row.querySelector('.shot-name').dataset.displayName = shot.display_name || '';

    return row;
}

function displayAssetLabel(type) {
    switch (type) {
        case 'first_image': return 'First Frame';
        case 'last_image': return 'Last Frame';
        case 'video': return 'Video';
        case 'alt_video': return 'Alt Video';
        default:
            return type.charAt(0).toUpperCase() + type.slice(1);
    }
}

function createDropZone(shot, type) {
    const file = shot[type];
    const currentVersion = (file && (file.current_version || file.max_version)) || 0;
    const maxVersion = (file && file.max_version) || 0;
    const hasFile = maxVersion > 0 || currentVersion > 0;

    if (hasFile) {
        const isVideo = type === 'video' || type === 'alt_video';
        const thumbnailUrl = file.thumbnail ? `${file.thumbnail}?v=${Date.now()}` : null;

        let mediaHtml;
        if (isVideo) {
            const videoStyle = thumbnailUrl ?
                `background-image: url('${thumbnailUrl}'); background-size: cover; background-position: center;` :
                'background: #404040;';
            mediaHtml = `<div class="preview-thumbnail video-thumbnail" style="${videoStyle}" onclick="playVideo('${shot.name}', '${shot.display_name || ''}')"></div>`;
        } else {
            mediaHtml = thumbnailUrl ?
                `<img class="preview-thumbnail" src="${thumbnailUrl}" alt="${displayAssetLabel(type)} thumbnail" onclick="showImage('${shot.name}', '${shot.display_name || ''}', '${type}')">` :
                `<div class="preview-thumbnail placeholder"></div>`;
        }

        const hasMultipleVersions = maxVersion > 1;
        const badgeClass = hasMultipleVersions ? 'version-badge multiple-versions' : 'version-badge';
        
        return `
                    <div class="drop-zone with-caption"
                         ondragover="handleDragOver(event, '${type}')"
                         ondrop="handleDrop(event, '${shot.name}', '${type}')"
                         ondragleave="handleDragLeave(event)">
                        <div class="file-preview">
                            ${mediaHtml}

                            <div class="${badgeClass}"
                                 title="Click to cycle version${hasMultipleVersions ? ' (multiple versions available)' : ''}"
                                 onclick="cycleAssetVersion('${shot.name}', '${type}')">v${String(currentVersion).padStart(3, '0')}</div>
                            <button class="prompt-button"
                                    title="View and edit prompt"
                                    data-shot="${shot.name}"
                                    data-type="${type}"
                                    data-current-version="${currentVersion}"
                                    data-max-version="${maxVersion}">P</button>
                        </div>
                        <input class="asset-caption-input"
                               type="text"
                               placeholder="Add text..."
                               value="${file.caption ? String(file.caption).replace(/&/g, '&').replace(/"/g, '"').replace(/</g, '<').replace(/>/g, '>') : ''}"
                               onblur="saveCaption('${shot.name}', '${type}', this.value)"
                               onchange="saveCaption('${shot.name}', '${type}', this.value)" />
                    </div>
                `;
    } else {
        return `
                    <div class="drop-zone empty"
                         onclick="openFileDialog('${shot.name}', '${type}')"
                         ondragover="handleDragOver(event, '${type}')"
                         ondrop="handleDrop(event, '${shot.name}', '${type}')"
                         ondragleave="handleDragLeave(event)">
                        <div class="drop-placeholder">
                            <div class="text">Add ${displayAssetLabel(type)}</div>
                        </div>
                    </div>
                `;
    }
}

function createLipsyncZone(shot) {
    const parts = ['driver', 'target', 'result'];
    let html = '<div class="lipsync-cell">';
    for (const part of parts) {
        const file = shot.lipsync[part];
        const hasFile = file.version > 0;
        const label = part.charAt(0).toUpperCase() + part.slice(1);
        if (hasFile) {
            const thumbnailUrl = file.thumbnail ? `${file.thumbnail}?v=${Date.now()}` : null;
            const thumbnailStyle = thumbnailUrl ?
                `background-image: url('${thumbnailUrl}'); background-size: cover; background-position: center;` :
                'background: #404040;';
            html += `
                        <div class="drop-zone lipsync-drop" ondragover="handleDragOver(event, '${part}')" ondrop="handleDrop(event, '${shot.name}', '${part}')" ondragleave="handleDragLeave(event)">
                            <div class="file-preview lipsync-preview">
                                <div class="preview-thumbnail lipsync-thumbnail" data-label="${label}" style="${thumbnailStyle}"></div>
                                <div class="version-badge">v${String(file.version).padStart(3, '0')}</div>
                                <button class="prompt-button" title="View and edit prompt"
                                        data-shot="${shot.name}"
                                        data-type="${part}"
                                        data-version="${file.version}">P</button>
                            </div>
                        </div>`;
        } else {
            html += `
                        <div class="drop-zone lipsync-drop empty" ondragover="handleDragOver(event, '${part}')" ondrop="handleDrop(event, '${shot.name}', '${part}')" ondragleave="handleDragLeave(event)">
                            <div class="drop-placeholder">
                                <div class="text">${label}</div>
                            </div>
                        </div>`;
        }
    }
    html += '</div>';
    return html;
}

async function addNewShot() {
    try {
        const response = await fetch('/api/shots', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            // Force reload shots from server to ensure fresh data including notes
            loadShots(`shot-row-${result.data.name}`);
            showNotification(`Shot ${result.data.name} created`);
        } else {
            showNotification(result.error || 'Failed to create shot', 'error');
        }
    } catch (error) {
        console.error('Error creating shot:', error);
        showNotification('Error creating shot', 'error');
    }
}

async function addNewShotAfter(afterShot) {
    try {
        const response = await fetch('/api/shots/create-between', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ after_shot: afterShot || null })
        });

        const result = await response.json();

        if (result.success) {
            // Force reload shots from server to ensure fresh data including notes
            loadShots(`shot-row-${result.data.name}`);
            showNotification(`Shot ${result.data.name} created`);
        } else {
            showNotification(result.error || 'Failed to create shot', 'error');
        }
    } catch (error) {
        console.error('Error creating shot:', error);
        showNotification('Error creating shot', 'error');
    }
}

// Drag and drop handlers
function handleDragOver(event, fileType) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

async function handleDrop(event, shotName, expectedType) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');

    const files = event.dataTransfer.files;
    if (files.length === 0) {
        showNotification('No files dropped', 'error');
        return;
    }

    const file = files[0];
    await uploadFile(file, shotName, expectedType);
}

async function uploadFile(file, shotName, fileType) {
    // Find the target drop zone for loading state
    const row = document.getElementById(`shot-row-${shotName}`);
    if (!row) {
        showNotification('Shot not found', 'error');
        return;
    }
    let dropZoneIndex;
    if (fileType === 'first_image') dropZoneIndex = 2;
    else if (fileType === 'last_image') dropZoneIndex = 3;
    else if (fileType === 'video') dropZoneIndex = 4;
    else if (fileType === 'alt_video') dropZoneIndex = 5;
    else return; // Invalid type
    const dropZone = row.children[dropZoneIndex];
    if (!dropZone || !dropZone.classList.contains('drop-zone')) {
        showNotification('Drop zone not found', 'error');
        return;
    }

    // Compute wasEmpty before mutation
    const shotIdx = shots.findIndex(s => s.name === shotName);
    const wasEmpty = shotIdx === -1 || !(shots[shotIdx][fileType] && ((shots[shotIdx][fileType].max_version || 0) > 0 || (shots[shotIdx][fileType].current_version || 0) > 0));

    // Add loading state
    dropZone.classList.add('uploading');
    showNotification('Uploading file...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('shot_name', shotName);
    formData.append('file_type', fileType);

    try {
        const response = await fetch('/api/shots/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            if (shotIdx !== -1) {
                const shot = shots[shotIdx];
                let asset = shot[fileType] || {};
                asset.file = result.data.final_path;
                asset.thumbnail = result.data.thumbnail;
                asset.current_version = result.data.version;
                asset.max_version = Math.max(asset.max_version || 0, result.data.version);
                shot[fileType] = asset;

                // Optionally fetch prompt for tooltip
                if (asset.current_version > 0) {
                    try {
                        const promptResp = await fetch(`/api/shots/prompt?shot_name=${encodeURIComponent(shotName)}&asset_type=${fileType}&version=${asset.current_version}`);
                        const promptData = await promptResp.json();
                        if (promptData.success) {
                            asset.prompt = promptData.data || '';
                        }
                    } catch (promptErr) {
                        console.warn('Failed to fetch prompt:', promptErr);
                    }
                }

                // Update UI for this drop zone
                if (wasEmpty) {
                    // Was empty: replace entire drop zone
                    replaceDropZoneForShot(shotName, fileType, shot);
                } else {
                    // Already had file: update existing
                    updateDropZoneForShot(shotName, fileType, shot);
                }

                showNotification(`${file.name} uploaded successfully!`);
            } else {
                showNotification('Shot data not found', 'error');
            }
        } else {
            showNotification(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showNotification('Upload failed', 'error');
    } finally {
        // Remove loading state (re-select in case replaced)
        const row2 = document.getElementById(`shot-row-${shotName}`);
        const dz = row2 ? row2.children[dropZoneIndex] : dropZone;
        if (dz && dz.classList.contains('uploading')) {
            dz.classList.remove('uploading');
        }
    }
}

async function cycleAssetVersion(shotName, assetType) {
    const shot = shots.find(s => s.name === shotName);
    if (!shot || !shot[assetType]) return;

    const info = shot[assetType];
    const maxV = info.max_version || 0;
    if (maxV < 1) return;

    const curr = info.current_version || maxV;
    const next = (curr % maxV) + 1;

    try {
        showNotification('Switching version...');
        const response = await fetch('/api/shots/promote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shot_name: shotName, asset_type: assetType, version: next })
        });
        const result = await response.json();
        if (result.success) {
            const updated = result.data;
            const idx = shots.findIndex(s => s.name === shotName);
            if (idx !== -1) {
                shots[idx] = updated;
            }

            // Update only the specific drop zone instead of full render
            updateDropZoneForShot(shotName, assetType, updated);
        } else {
            showNotification(result.error || 'Failed to switch version', 'error');
        }
    } catch (error) {
        console.error('Promote failed:', error);
        showNotification('Failed to switch version', 'error');
    }
}

// Helper function to update a specific drop zone
function updateDropZoneForShot(shotName, assetType, shotData) {
    const assetInfo = shotData[assetType];
    if (!assetInfo) return;

    // Find the specific drop zone for this shot and asset type
    const shotRow = document.getElementById(`shot-row-${shotName}`);
    if (!shotRow) return;

    // Get the drop zone based on asset type - they appear in specific order after action-cell:
    // [0] action-cell, [1] shot-name, [2] first_image, [3] last_image, [4] video, [5] alt_video, [6] notes
    let dropZone = null;
    if (assetType === 'first_image') {
        dropZone = shotRow.children[2]; // first child after action and name
    } else if (assetType === 'last_image') {
        dropZone = shotRow.children[3];
    } else if (assetType === 'video') {
        dropZone = shotRow.children[4];
    } else if (assetType === 'alt_video') {
        dropZone = shotRow.children[5];
    }

    if (!dropZone || !dropZone.classList.contains('drop-zone')) return;

    // Update the version badge
    const versionBadge = dropZone.querySelector('.version-badge');
    if (versionBadge) {
        versionBadge.textContent = `v${String(assetInfo.current_version).padStart(3, '0')}`;
    }

    // Update the thumbnail
    const filePreview = dropZone.querySelector('.file-preview');
    if (filePreview) {
        const thumbnailContainer = filePreview.querySelector('.preview-thumbnail, .video-thumbnail');
        if (thumbnailContainer && assetInfo.thumbnail) {
            // Force thumbnail refresh by adding timestamp parameter
            const newThumbnailUrl = `${assetInfo.thumbnail}?v=${Date.now()}`;
            if (thumbnailContainer.tagName.toLowerCase() === 'img') {
                thumbnailContainer.src = newThumbnailUrl;
            } else {
                // For video thumbnails (div with background-image)
                thumbnailContainer.style.backgroundImage = `url('${newThumbnailUrl}')`;
            }
        }
    }

    // Update the prompt button data attributes
    const promptButton = dropZone.querySelector('.prompt-button');
    if (promptButton) {
        promptButton.setAttribute('data-current-version', assetInfo.current_version);
        promptButton.setAttribute('data-max-version', assetInfo.max_version);
    }

    // Update caption input if present
    const captionInput = dropZone.querySelector('.asset-caption-input');
    if (captionInput && assetInfo.caption !== undefined) {
        captionInput.value = assetInfo.caption || '';
    }
}

// Helper to replace an empty drop zone with filled markup
function replaceDropZoneForShot(shotName, assetType, shotData) {
    const shotRow = document.getElementById(`shot-row-${shotName}`);
    if (!shotRow) return;

    let dropZoneIndex;
    if (assetType === 'first_image') dropZoneIndex = 2;
    else if (assetType === 'last_image') dropZoneIndex = 3;
    else if (assetType === 'video') dropZoneIndex = 4;
    else if (assetType === 'alt_video') dropZoneIndex = 5;
    else return;

    const oldDropZone = shotRow.children[dropZoneIndex];
    if (!oldDropZone || !oldDropZone.classList.contains('drop-zone')) return;

    // Generate new HTML for the drop zone
    const newHtml = createDropZone(shotData, assetType);

    // Replace the old drop zone
    oldDropZone.outerHTML = newHtml;

    // Reinitialize tooltips after DOM replacement
    setTimeout(initTooltips, 0);
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');

    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function captureScroll(rowId = null) {
    savedScrollY = window.pageYOffset;
    savedRowId = rowId;
}

function restoreScroll() {
    if (savedRowId) {
        const el = document.getElementById(savedRowId);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            savedRowId = null;
            return;
        }
    }
    window.scrollTo({ top: savedScrollY });
    savedRowId = null;
}

// Drag and drop handlers for rows
function handleRowDragOver(event) {
    event.preventDefault();

    // Some browsers do not populate `dataTransfer.files` during
    // `dragover`, so check the types list instead. If it includes
    // "Files", we assume a file is being dragged and show the marker.
    const types = event.dataTransfer.types;
    if (types && Array.from(types).includes('Files')) {
        event.currentTarget.classList.add('drag-over', 'new-shot-drop-zone');
    }
}

function handleRowDragLeave(event) {
    event.currentTarget.classList.remove('drag-over', 'new-shot-drop-zone');
}

async function handleRowDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over', 'new-shot-drop-zone');

    const files = event.dataTransfer.files;
    if (files.length === 0) return;

    const afterShot = event.currentTarget.getAttribute('data-after-shot');

    try {
        // Create new shot
        const response = await fetch('/api/shots/create-between', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                after_shot: afterShot || null
            })
        });

        const result = await response.json();

        if (result.success) {
            const newShot = result.data;
            showNotification(`Shot ${newShot.name} created`);

            // Insert new shot into local state and render before upload
            const insertIndex = afterShot ? shots.findIndex(s => s.name === afterShot) + 1 : 0;
            shots.splice(insertIndex, 0, newShot);
            captureScroll(`shot-row-${newShot.name}`);
            renderShots();
            restoreScroll();

            // Upload the file to the new shot
            const file = files[0];
            const fileType = getFileType(file.name);

            if (fileType) {
                await uploadFile(file, newShot.name, fileType);
            } else {
                showNotification('Unsupported file type', 'error');
                // No need for loadShots since we already rendered the new row
            }
        } else {
            showNotification(result.error || 'Failed to create shot', 'error');
        }
    } catch (error) {
        console.error('Error creating shot:', error);
        showNotification('Error creating shot', 'error');
    }
}

function getFileType(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    const imageExts = ['jpg', 'jpeg', 'png', 'webp'];
    const videoExts = ['mp4', 'mov'];

    if (imageExts.includes(ext)) return 'first_image'; // default image target
    if (videoExts.includes(ext)) return 'video';
    return null;
}

function openFileDialog(shotName, fileType) {
    const input = document.createElement('input');
    input.type = 'file';
    if (fileType === 'first_image' || fileType === 'last_image' || fileType === 'image') {
        input.accept = 'image/*';
    } else if (fileType === 'video' || fileType === 'alt_video') {
        input.accept = 'video/*';
    }
    input.style.display = 'none';
    input.addEventListener('change', () => {
        if (input.files && input.files[0]) {
            uploadFile(input.files[0], shotName, fileType);
        }
        input.remove();
    });
    document.body.appendChild(input);
    input.click();
}

async function saveNotes(shotName, notes) {
    try {
        const response = await fetch('/api/shots/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                shot_name: shotName,
                notes: notes
            })
        });

        const result = await response.json();

        if (!result.success) {
            showNotification(result.error || 'Failed to save notes', 'error');
        }
        // Don't show success notification for notes to avoid spam
    } catch (error) {
        console.error('Error saving notes:', error);
        showNotification('Error saving notes', 'error');
    }
}

async function saveCaption(shotName, assetType, caption) {
    try {
        const response = await fetch('/api/shots/caption', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                shot_name: shotName,
                asset_type: assetType,
                caption: caption
            })
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to save caption', 'error');
        }
    } catch (error) {
        console.error('Error saving caption:', error);
        showNotification('Error saving caption', 'error');
    }
}

function editShotName(element, currentName) {
    const newName = prompt('Enter new shot name', currentName);
    if (!newName || newName === currentName) {
        return;
    }
    renameShot(currentName, newName);
}

async function renameShot(oldName, newName) {
    try {
        const response = await fetch('/api/shots/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        });
        const result = await response.json();
        if (result.success) {
            showNotification(`Renamed to ${newName}`);
            loadShots(`shot-row-${newName}`);
        } else {
            showNotification(result.error || 'Rename failed', 'error');
        }
    } catch (error) {
        console.error('Rename failed:', error);
        showNotification('Rename failed', 'error');
    }
}

async function saveDisplayName(shotName, displayName) {
    try {
        const response = await fetch('/api/shots/display-name', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shot_name: shotName, display_name: displayName })
        });
        const result = await response.json();
        if (result.success) {
            showNotification(`Display name updated`);
            const idx = shots.findIndex(s => s.name === shotName);
            if (idx !== -1) {
                shots[idx] = result.data;
            }
            captureScroll(`shot-row-${shotName}`);
            renderShots();
            restoreScroll();
        } else {
            showNotification(result.error || 'Failed to update display name', 'error');
        }
    } catch (e) {
        console.error('Save display name failed:', e);
        showNotification('Failed to update display name', 'error');
    }
}

// Expose globally for inline onclick
window.saveDisplayName = saveDisplayName;

function editDisplayName(element, shotName) {
    const currentDisplayName = element.dataset.displayName || '';
    const newDisplayName = prompt('Enter display name (leave empty to show only SHXXX)', currentDisplayName);
    if (newDisplayName === null || newDisplayName === currentDisplayName) {
        return;
    }
    // Update data attribute immediately for UI consistency
    element.dataset.displayName = newDisplayName;
    saveDisplayName(shotName, newDisplayName);
}

// Expose globally for inline onclick
window.editDisplayName = editDisplayName;

async function archiveShot(shotName, archived) {
    try {
        const response = await fetch('/api/shots/archive', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shot_name: shotName, archived })
        });
        const result = await response.json();
        if (result.success) {
            showNotification(archived ? `Archived ${shotName}` : `Unarchived ${shotName}`);
            const idx = shots.findIndex(s => s.name === shotName);
            if (idx !== -1) {
                shots[idx] = result.data;
            }
            captureScroll(`shot-row-${shotName}`);
            renderShots();
            restoreScroll();
        } else {
            showNotification(result.error || 'Failed to update archive state', 'error');
        }
    } catch (e) {
        console.error('Archive toggle failed:', e);
        showNotification('Failed to update archive state', 'error');
    }
}

async function revealFile(relPath) {
    try {
        const response = await fetch('/api/shots/reveal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: relPath })
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to reveal file', 'error');
        }
    } catch (e) {
        console.error("Reveal failed:", e);
        showNotification('Reveal failed', 'error');
    }
}

async function fetchPrompt(shotName, assetType, version) {
    try {
        const resp = await fetch(`/api/shots/prompt?shot_name=${encodeURIComponent(shotName)}&asset_type=${assetType}&version=${version}`);
        const data = await resp.json();
        if (data.success) {
            return data.data || '';
        }
    } catch (e) {
        console.error('Failed to load prompt:', e);
    }
    return '';
}

function buildVersionDropdown(versions, currentVersion) {
    const btn = document.getElementById('version-dropdown-btn');
    const menu = document.getElementById('version-dropdown-menu');
    menu.innerHTML = '';
    versions.sort((a, b) => b - a); // descending
    versions.forEach(v => {
        const item = document.createElement('div');
        item.className = 'dropdown-item';
        item.dataset.version = v;
        item.textContent = `v${String(v).padStart(3, '0')}`;
        item.onclick = () => selectPromptVersion(v);
        menu.appendChild(item);
    });
    btn.textContent = `v${String(currentVersion).padStart(3, '0')} \u25BE`;
}

function toggleVersionDropdown() {
    const menu = document.getElementById('version-dropdown-menu');
    menu.classList.toggle('show');
}

async function selectPromptVersion(v) {
    const modal = document.getElementById('prompt-modal');
    const shotName = modal.dataset.shot;
    const assetType = modal.dataset.type;
    const prevVersion = parseInt(modal.dataset.version, 10);
    if (prevVersion && prevVersion !== v) {
        const prevPromptText = document.getElementById('prompt-text').value;
        try {
            await fetch('/api/shots/prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shot_name: shotName,
                    asset_type: assetType,
                    version: prevVersion,
                    prompt: prevPromptText
                })
            });
        } catch (e) {
            console.error('Auto-save failed:', e);
        }
    }
    modal.dataset.version = v;
    const versions = JSON.parse(modal.dataset.versions || '[]');
    buildVersionDropdown(versions, v);
    let prompt = await fetchPrompt(shotName, assetType, v);

    const copyBtn = document.getElementById('copy-prompt-btn');
    copyBtn.style.display = 'none';
    modal.dataset.prevPrompt = '';

    if (!prompt && v === parseInt(modal.dataset.assetVersion, 10)) {
        const prevPrompt = await fetchPrompt(shotName, assetType, v - 1);
        if (prevPrompt) {
            modal.dataset.prevPrompt = prevPrompt;
            copyBtn.style.display = 'inline-block';
        }
    }
    document.getElementById('prompt-text').value = prompt;
    toggleVersionDropdown();
}

async function openPromptModal(shotName, assetType, currentVersion, maxVersion) {
    const modal = document.getElementById('prompt-modal');
    modal.dataset.shot = shotName;
    modal.dataset.type = assetType;

    const typeLabel = displayAssetLabel(assetType);
    document.getElementById('prompt-modal-title').textContent = `${shotName} ${typeLabel} Prompt`;
    const versions = Array.from({ length: maxVersion }, (_, i) => i + 1);
    modal.dataset.versions = JSON.stringify(versions);
    modal.dataset.assetVersion = currentVersion;
    buildVersionDropdown(versions, currentVersion);

    let prompt = await fetchPrompt(shotName, assetType, currentVersion);
    const copyBtn = document.getElementById('copy-prompt-btn');
    copyBtn.style.display = 'none';
    modal.dataset.prevPrompt = '';

    if (!prompt && currentVersion > 1) {
        const prevPrompt = await fetchPrompt(shotName, assetType, currentVersion - 1);
        if (prevPrompt) {
            modal.dataset.prevPrompt = prevPrompt;
            copyBtn.style.display = 'inline-block';
        }
    }
    modal.dataset.version = currentVersion;
    document.getElementById('prompt-text').value = prompt;

    modal.style.display = 'flex';
    document.getElementById('prompt-text').focus();
}

function closePromptModal() {
    document.getElementById('prompt-modal').style.display = 'none';
}
function copyToNewPromptVersion() {
    const modal = document.getElementById('prompt-modal');
    const prevPrompt = modal.dataset.prevPrompt || '';
    if (prevPrompt) {
        document.getElementById('prompt-text').value = prevPrompt;
    }
    document.getElementById('copy-prompt-btn').style.display = 'none';
}

async function savePrompt() {
    const modal = document.getElementById('prompt-modal');
    const shotName = modal.dataset.shot;
    const assetType = modal.dataset.type;
    const version = modal.dataset.version;
    const promptText = document.getElementById('prompt-text').value;
    try {
        const response = await fetch('/api/shots/prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shot_name: shotName, asset_type: assetType, version: parseInt(version, 10), prompt: promptText })
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to save prompt', 'error');
        } else {
            const shot = shots.find(s => s.name === shotName);
            if (shot) {
                if (assetType === 'first_image' || assetType === 'last_image' || assetType === 'image' || assetType === 'video') {
                    const key = assetType === 'image' ? 'first_image' : assetType; // legacy map
                    if (shot[key]) {
                        shot[key].prompt = promptText;
                    }
                } else if (shot.lipsync && shot.lipsync[assetType]) {
                    shot.lipsync[assetType].prompt = promptText;
                }
            }
        }
    } catch (e) {
        console.error('Error saving prompt:', e);
        showNotification('Error saving prompt', 'error');
    }
    closePromptModal();
}

async function openShotsFolder() {
    if (!currentProject) {
        showNotification('No project open', 'error');
        return;
    }
    try {
        const response = await fetch('/api/shots/open-folder', {
            method: 'POST'
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to open folder', 'error');
        }
    } catch (e) {
        console.error('Open folder failed:', e);
        showNotification('Failed to open folder', 'error');
    }
}

// Reorder Modal Functions
let reorderSortable = null;

function openReorderModal() {
    const modal = document.getElementById('reorder-modal');
    const list = document.getElementById('reorder-list');
    const filter = document.getElementById('reorder-filter');

    if (!modal || !list) return;

    // Capture current scroll position before opening modal
    captureScroll();

    // Clear previous content
    list.innerHTML = '';
    filter.value = '';

    // Get active shots
    const activeShots = shots.filter(s => !s.archived);

    if (activeShots.length === 0) {
        list.innerHTML = '<li class="reorder-item empty">No active shots to reorder</li>';
    } else {
        // Create list items
        activeShots.forEach((shot, index) => {
            const item = document.createElement('li');
            item.className = 'reorder-item';
            item.dataset.name = shot.name;
            item.innerHTML = `
                <span class="badge">${index + 1}</span>
                ${shot.display_name ? `${escapeHtml(shot.display_name)} <span class="shot-code">(${shot.name})</span>` : shot.name}
            `;
            list.appendChild(item);
        });

        // Initialize Sortable
        if (reorderSortable) {
            reorderSortable.destroy();
        }
        reorderSortable = new Sortable(list, {
            animation: 150,
            ghostClass: 'reorder-ghost',
            chosenClass: 'reorder-chosen',
            dragClass: 'reorder-drag'
        });
    }

    // Show modal
    modal.style.display = 'flex';
}

function closeReorderModal() {
    const modal = document.getElementById('reorder-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function saveReorder() {
    const list = document.getElementById('reorder-list');
    if (!list) return;

    const items = Array.from(list.querySelectorAll('.reorder-item:not(.empty)'));
    if (items.length === 0) {
        closeReorderModal();
        return;
    }

    const activeOrdered = items.map(item => item.dataset.name);
    const archived = shots.filter(s => s.archived).map(s => s.name);
    const shot_order = activeOrdered.concat(archived);

    try {
        const response = await fetch('/api/shots/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ shot_order: shot_order })
        });

        const result = await response.json();

        if (result.success) {
            // Update local shots array to match new order
            shots.sort((a, b) => shot_order.indexOf(a.name) - shot_order.indexOf(b.name));
            renderShots();
            closeReorderModal();
            showNotification('Shot order saved');
        } else {
            showNotification(result.error || 'Failed to save order', 'error');
        }
    } catch (error) {
        console.error('Error saving shot order:', error);
        showNotification('Error saving shot order', 'error');
    }
}

// Filter functionality for reorder modal
document.addEventListener('DOMContentLoaded', function () {
    const filter = document.getElementById('reorder-filter');
    if (filter) {
        filter.addEventListener('input', function () {
            const query = this.value.toLowerCase();
            const items = document.querySelectorAll('#reorder-list .reorder-item:not(.empty)');

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? 'flex' : 'none';
            });
        });
    }

    // Close modal when clicking outside
    document.addEventListener('click', function (event) {
        const modal = document.getElementById('reorder-modal');
        if (modal && event.target === modal) {
            closeReorderModal();
        }
    });

    // Back to Top Button functionality
    const backToTopButton = document.getElementById('backToTop');

    if (backToTopButton) {
        // Show/hide button based on scroll position
        window.addEventListener('scroll', function () {
            if (window.pageYOffset > 300) {
                backToTopButton.classList.add('show');
            } else {
                backToTopButton.classList.remove('show');
            }
        });

        // Scroll to top when clicked
        backToTopButton.addEventListener('click', function () {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        // Also hide button when at the very top
        window.addEventListener('scroll', function () {
            if (window.pageYOffset === 0) {
                backToTopButton.classList.remove('show');
            }
        });
    }
});

// Tooltip functionality
function initTooltips() {
    // Create tooltip element if it doesn't exist
    let tooltip = document.getElementById('prompt-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'prompt-tooltip';
        tooltip.className = 'tooltip';
        document.body.appendChild(tooltip);
    }

    // Add event listeners for mouse enter/leave on preview thumbnails
    document.addEventListener('mouseover', function (e) {
        const thumbnail = e.target.closest('.preview-thumbnail, .video-thumbnail');
        if (!thumbnail) return;

        // Get the closest drop zone to find prompt data
        const dropZone = thumbnail.closest('.drop-zone');
        if (!dropZone) return;

        // Extract shot name and type from the drop zone
        const filePreview = dropZone.querySelector('.file-preview');
        if (!filePreview) return;

        const promptButton = filePreview.querySelector('.prompt-button');
        if (!promptButton) return;

        const shotName = promptButton.dataset.shot;
        const assetType = promptButton.dataset.type;
        const currentVersion = promptButton.dataset.currentVersion;

        if (!shotName || !assetType || !currentVersion) return;

        // Find the shot object to get the prompt
        const shot = shots.find(s => s.name === shotName);
        if (!shot || !shot[assetType] || !shot[assetType].prompt) return;

        const prompt = shot[assetType].prompt;
        if (!prompt.trim()) return;

        // Set tooltip content
        tooltip.textContent = prompt;

        // Show tooltip
        tooltip.classList.add('show');

        // Position tooltip near the mouse
        positionTooltip(tooltip, e);
    });

    document.addEventListener('mouseout', function (e) {
        const thumbnail = e.target.closest('.preview-thumbnail, .video-thumbnail');
        if (thumbnail) {
            const tooltip = document.getElementById('prompt-tooltip');
            if (tooltip) {
                tooltip.classList.remove('show');
            }
        }
    });

    document.addEventListener('mousemove', function (e) {
        const thumbnail = e.target.closest('.preview-thumbnail, .video-thumbnail');
        if (thumbnail) {
            const tooltip = document.getElementById('prompt-tooltip');
            if (tooltip && tooltip.classList.contains('show')) {
                positionTooltip(tooltip, e);
            }
        }
    });
}

function positionTooltip(tooltip, event) {
    const padding = 10;
    // Account for page scroll position to position tooltip correctly
    const x = event.clientX + window.scrollX + padding;
    const y = event.clientY + window.scrollY + padding;

    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';

    // Check if tooltip goes off screen and adjust if needed
    const rect = tooltip.getBoundingClientRect();
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    if (rect.right > windowWidth) {
        tooltip.style.left = (event.clientX + window.scrollX - rect.width - padding) + 'px';
    }

    if (rect.bottom > windowHeight) {
        tooltip.style.top = (event.clientY + window.scrollY - rect.height - padding) + 'px';
    }
}

// Project Information Modal Functions
async function openProjectInfoModal() {
    const modal = document.getElementById('project-info-modal');
    if (!modal) return;

    try {
        // Fetch project information
        const response = await fetch('/api/project/info');
        const result = await response.json();

        if (result.success) {
            // Populate the modal with project info
            document.getElementById('project-info-title').value = result.data.title || '';
            document.getElementById('project-info-short-description').value = result.data.short_description || '';
            document.getElementById('project-info-version').value = result.data.version || '1.0.0';
            document.getElementById('project-info-notes').value = result.data.notes || result.data.description || '';
            document.getElementById('project-info-tags').value = result.data.tags ? result.data.tags.join(', ') : '';
            document.getElementById('project-info-created').value = result.data.created ? new Date(result.data.created).toLocaleString() : '';
            document.getElementById('project-info-updated').value = result.data.updated ? new Date(result.data.updated).toLocaleString() : '';

            // Show modal
            modal.style.display = 'flex';
        } else {
            showNotification(result.error || 'Failed to load project information', 'error');
        }
    } catch (error) {
        console.error('Error loading project info:', error);
        showNotification('Error loading project information', 'error');
    }
}

function closeProjectInfoModal() {
    const modal = document.getElementById('project-info-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function saveProjectInfo() {
    const title = document.getElementById('project-info-title').value.trim();
    const short_description = document.getElementById('project-info-short-description').value.trim();
    const version = document.getElementById('project-info-version').value.trim();
    const notes = document.getElementById('project-info-notes').value.trim();
    const tagsInput = document.getElementById('project-info-tags').value.trim();

    // Parse tags (split by comma and trim whitespace)
    const tags = tagsInput ?
        tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0)
        : [];

    // Prepare project info object
    const projectInfo = {
        title: title || (currentProject && typeof currentProject === 'object' && currentProject.name ? currentProject.name : 'Untitled Project'), // Use project name as default title if none provided
        short_description: short_description,
        version: version || '1.0.0',
        notes: notes,
        tags: tags
    };

    try {
        const response = await fetch('/api/project/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectInfo)
        });

        const result = await response.json();

        if (result.success) {
            showNotification('Project information saved successfully');
            closeProjectInfoModal();

            // Update the project header with saved values
            updateProjectHeader(result.data || {}, currentProject && currentProject.name);
            // Keep local cache coherent
            if (currentProject) currentProject.info = result.data;
        } else {
            showNotification(result.error || 'Failed to save project information', 'error');
        }
    } catch (error) {
        console.error('Error saving project info:', error);
        showNotification('Error saving project information', 'error');
    }
}

// Export Modal Functions
function openExportModal() {
    document.getElementById('export-modal').style.display = 'flex';
    document.getElementById('export-name').value = '';
    document.getElementById('export-type').value = 'all';
    document.getElementById('include-display-in-filename').checked = true;
}

function closeExportModal() {
    document.getElementById('export-modal').style.display = 'none';
}

async function confirmExport() {
    const exportName = document.getElementById('export-name').value.trim();
    const exportImages = document.getElementById('export-images').checked;
    const exportVideos = document.getElementById('export-videos').checked;
    const includeDisplay = document.getElementById('include-display-in-filename').checked;
    const includeMetadata = document.getElementById('include-metadata').checked;

    // Determine export type based on checkbox states
    let exportType;
    if (exportImages && exportVideos) {
        exportType = 'all';
    } else if (exportImages) {
        exportType = 'images';
    } else if (exportVideos) {
        exportType = 'videos';
    } else {
        showNotification('Please select at least one export option (Images or Videos)', 'error');
        return;
    }

    try {
        const response = await fetch('/api/shots/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                export_name: exportName || null,
                export_type: exportType,
                include_display_in_filename: includeDisplay,
                include_metadata: includeMetadata
            })
        });

        const result = await response.json();

        if (result.success) {
            closeExportModal();
            showNotification(`Export created successfully at: ${result.export_path}`);
        } else {
            showNotification(result.error || 'Export failed', 'error');
        }
    } catch (error) {
        console.error('Export failed:', error);
        showNotification('Export failed', 'error');
    }
}

// Video Playback Functions
let currentVideoShotIndex = -1;

// Image Navigation Functions
let currentImageShotIndex = -1;
let currentImageAssetType = '';

function playVideo(shotName, displayName) {
    const shot = shots.find(s => s.name === shotName);
    if (!shot || !shot.video || !shot.video.file) {
        showNotification('No video available for this shot', 'error');
        return;
    }

    // Find the current shot index in the active shots array
    const activeShots = shots.filter(s => !s.archived && s.video && s.video.file);
    currentVideoShotIndex = activeShots.findIndex(s => s.name === shotName);

    const videoUrl = `/api/shots/video/${shotName}?v=${Date.now()}`;
    const videoPlayer = document.getElementById('video-player');
    const videoModalTitle = document.getElementById('video-modal-title');
    const videoVersion = document.getElementById('video-version');
    const videoPrompt = document.getElementById('video-prompt');

    // Set video source
    videoPlayer.src = videoUrl;

    // Set modal title and version
    if (displayName) {
        videoModalTitle.innerHTML = `${escapeHtml(displayName)}<br><span style="font-size: 14px; opacity: 0.7; font-weight: normal;">(${shotName})</span>`;
    } else {
        videoModalTitle.textContent = shotName;
    }

    videoVersion.textContent = String(shot.video.current_version).padStart(3, '0');

    // Set prompt text if available
    if (shot.video.prompt) {
        videoPrompt.textContent = shot.video.prompt;
        videoPrompt.style.display = 'block';
    } else {
        videoPrompt.textContent = '';
        videoPrompt.style.display = 'none';
    }

    // Show modal
    document.getElementById('video-modal').style.display = 'flex';

    // Add keyboard navigation listeners
    document.addEventListener('keydown', handleVideoModalKeydown);

    // Load and play video
    videoPlayer.load();
    videoPlayer.play().catch(e => {
        console.log('Autoplay prevented:', e);
    });
}

function navigateToNextShot() {
    const activeShots = shots.filter(s => !s.archived && s.video && s.video.file);
    if (activeShots.length === 0 || currentVideoShotIndex === -1) return;

    const nextIndex = (currentVideoShotIndex + 1) % activeShots.length;
    const nextShot = activeShots[nextIndex];
    
    if (nextShot) {
        playVideo(nextShot.name, nextShot.display_name || '');
    }
}

function navigateToPreviousShot() {
    const activeShots = shots.filter(s => !s.archived && s.video && s.video.file);
    if (activeShots.length === 0 || currentVideoShotIndex === -1) return;

    const prevIndex = (currentVideoShotIndex - 1 + activeShots.length) % activeShots.length;
    const prevShot = activeShots[prevIndex];
    
    if (prevShot) {
        playVideo(prevShot.name, prevShot.display_name || '');
    }
}

function handleVideoModalKeydown(event) {
    // Only handle arrow keys when video modal is open
    const videoModal = document.getElementById('video-modal');
    if (videoModal.style.display !== 'flex') return;

    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            navigateToPreviousShot();
            break;
        case 'ArrowRight':
            event.preventDefault();
            navigateToNextShot();
            break;
    }
}

function closeVideoModal() {
    const videoModal = document.getElementById('video-modal');
    const videoPlayer = document.getElementById('video-player');

    videoModal.style.display = 'none';
    videoPlayer.pause();
    videoPlayer.currentTime = 0;
    videoPlayer.src = '';

    // Remove keyboard navigation listeners
    document.removeEventListener('keydown', handleVideoModalKeydown);
}

// Image View Functions
function showImage(shotName, displayName, assetType) {
    const shot = shots.find(s => s.name === shotName);
    if (!shot || !shot[assetType] || !shot[assetType].file) {
        showNotification('No image available for this shot', 'error');
        return;
    }

    // Find the current shot index in the active shots array for this specific asset type
    const activeShots = shots.filter(s => !s.archived && s[assetType] && s[assetType].file);
    currentImageShotIndex = activeShots.findIndex(s => s.name === shotName);
    currentImageAssetType = assetType;

    const imageUrl = `/api/shots/image/${shotName}/${assetType}?v=${Date.now()}`;
    const imageDisplay = document.getElementById('image-display');
    const imageModalTitle = document.getElementById('image-modal-title');
    const imageVersion = document.getElementById('image-version');
    const imagePrompt = document.getElementById('image-prompt');

    // Set image source
    imageDisplay.src = imageUrl;

    // Set modal title and version
    const typeLabel = displayAssetLabel(assetType);
    if (displayName) {
        imageModalTitle.innerHTML = `${escapeHtml(displayName)} ${typeLabel}<br><span style="font-size: 14px; opacity: 0.7; font-weight: normal;">(${shotName})</span>`;
    } else {
        imageModalTitle.textContent = `${shotName} ${typeLabel}`;
    }

    imageVersion.textContent = String(shot[assetType].current_version).padStart(3, '0');

    // Set prompt text if available
    if (shot[assetType].prompt) {
        imagePrompt.textContent = shot[assetType].prompt;
        imagePrompt.style.display = 'block';
    } else {
        imagePrompt.textContent = '';
        imagePrompt.style.display = 'none';
    }

    // Show modal
    document.getElementById('image-modal').style.display = 'flex';

    // Add keyboard navigation listeners
    document.addEventListener('keydown', handleImageModalKeydown);
}

function navigateToNextImage() {
    const activeShots = shots.filter(s => !s.archived && s[currentImageAssetType] && s[currentImageAssetType].file);
    if (activeShots.length === 0 || currentImageShotIndex === -1) return;

    const nextIndex = (currentImageShotIndex + 1) % activeShots.length;
    const nextShot = activeShots[nextIndex];
    
    if (nextShot) {
        showImage(nextShot.name, nextShot.display_name || '', currentImageAssetType);
    }
}

function navigateToPreviousImage() {
    const activeShots = shots.filter(s => !s.archived && s[currentImageAssetType] && s[currentImageAssetType].file);
    if (activeShots.length === 0 || currentImageShotIndex === -1) return;

    const prevIndex = (currentImageShotIndex - 1 + activeShots.length) % activeShots.length;
    const prevShot = activeShots[prevIndex];
    
    if (prevShot) {
        showImage(prevShot.name, prevShot.display_name || '', currentImageAssetType);
    }
}

function handleImageModalKeydown(event) {
    // Only handle arrow keys when image modal is open
    const imageModal = document.getElementById('image-modal');
    if (imageModal.style.display !== 'flex') return;

    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            navigateToPreviousImage();
            break;
        case 'ArrowRight':
            event.preventDefault();
            navigateToNextImage();
            break;
    }
}

function closeImageModal() {
    const imageModal = document.getElementById('image-modal');
    const imageDisplay = document.getElementById('image-display');

    imageModal.style.display = 'none';
    imageDisplay.src = '';

    // Remove keyboard navigation listeners
    document.removeEventListener('keydown', handleImageModalKeydown);
}

// Close video modal when clicking outside
document.addEventListener('click', function (event) {
    const videoModal = document.getElementById('video-modal');
    if (event.target === videoModal) {
        closeVideoModal();
    }
});

// Close video modal with Escape key
document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
        const videoModal = document.getElementById('video-modal');
        const imageModal = document.getElementById('image-modal');
        if (videoModal.style.display === 'flex') {
            closeVideoModal();
        } else if (imageModal.style.display === 'flex') {
            closeImageModal();
        }
    }
});

// Close image modal when clicking outside
document.addEventListener('click', function (event) {
    const imageModal = document.getElementById('image-modal');
    if (event.target === imageModal) {
        closeImageModal();
    }
});

// Expose image functions globally
window.showImage = showImage;
window.closeImageModal = closeImageModal;
window.navigateToNextImage = navigateToNextImage;
window.navigateToPreviousImage = navigateToPreviousImage;

// Expose functions globally
window.openProjectInfoModal = openProjectInfoModal;
window.closeProjectInfoModal = closeProjectInfoModal;
window.saveProjectInfo = saveProjectInfo;
window.openReorderModal = openReorderModal;
window.closeReorderModal = closeReorderModal;
window.saveReorder = saveReorder;
window.openExportModal = openExportModal;
window.closeExportModal = closeExportModal;
window.confirmExport = confirmExport;
window.playVideo = playVideo;
window.closeVideoModal = closeVideoModal;
