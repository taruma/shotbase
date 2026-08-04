/* ============================================================
   Modals & Media Viewers — extracted from main.js
   Contains: Prompt modal, Reorder modal, Project info modal,
   Export modal, Video/Image/Audio viewers, Folder operations.
   Depends on globals from main.js: shots, currentProject,
   showNotification, escapeHtml, displayAssetLabel,
   captureScroll, renderShots, updateProjectHeader, updatePageTitle
   ============================================================ */

// ============================================================
// Prompt Modal Functions
// ============================================================

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
                if (assetType === 'first_image' || assetType === 'last_image' || assetType === 'image' || assetType === 'video' || assetType === 'alt_video' || assetType === 'audio') {
                    const key = assetType === 'image' ? 'first_image' : assetType; // legacy map
                    if (shot[key]) {
                        shot[key].prompt = promptText;
                    }
                }
            }
        }
    } catch (e) {
        console.error('Error saving prompt:', e);
        showNotification('Error saving prompt', 'error');
    }
    closePromptModal();
}

// ============================================================
// Folder Operations
// ============================================================

async function openExportsFolder() {
    try {
        const response = await fetch('/api/shots/open-exports-folder', {
            method: 'POST'
        });
        const result = await response.json();
        if (!result.success) {
            showNotification(result.error || 'Failed to open exports folder', 'error');
        }
    } catch (e) {
        console.error('Open exports folder failed:', e);
        showNotification('Failed to open exports folder', 'error');
    }
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

// ============================================================
// Reorder Modal Functions
// ============================================================

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

// ============================================================
// Project Information Modal Functions
// ============================================================

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
            if (currentProject) {
                currentProject.info = result.data;
                updatePageTitle(currentProject);
            }
        } else {
            showNotification(result.error || 'Failed to save project information', 'error');
        }
    } catch (error) {
        console.error('Error saving project info:', error);
        showNotification('Error saving project information', 'error');
    }
}

// ============================================================
// Export Modal Functions
// ============================================================

function openExportModal() {
    document.getElementById('export-modal').style.display = 'flex';
    document.getElementById('export-name').value = '';
    document.getElementById('export-type').value = 'all';
    document.getElementById('include-display-in-filename').checked = true;
}

function closeExportModal() {
    document.getElementById('export-modal').style.display = 'none';
    // Reset loading state in case modal was closed mid-export
    const exportBtn = document.getElementById('export-btn');
    const cancelBtn = document.getElementById('export-cancel-btn');
    const loadingEl = document.getElementById('export-loading');
    if (exportBtn) {
        exportBtn.disabled = false;
        exportBtn.textContent = 'Export';
    }
    if (cancelBtn) cancelBtn.disabled = false;
    if (loadingEl) loadingEl.style.display = 'none';
}

async function confirmExport() {
    const exportName = document.getElementById('export-name').value.trim();
    const exportImages = document.getElementById('export-images').checked;
    const exportVideos = document.getElementById('export-videos').checked;
    const exportAudio = document.getElementById('export-audio').checked;
    const includeDisplay = document.getElementById('include-display-in-filename').checked;
    const includeMetadata = document.getElementById('include-metadata').checked;
    const exportFormatEl = document.querySelector('input[name="export-format"]:checked');
    const exportFormat = exportFormatEl ? exportFormatEl.value : 'md';

    // Determine export type based on checkbox states
    let exportType;
    const selectedCount = (exportImages ? 1 : 0) + (exportVideos ? 1 : 0) + (exportAudio ? 1 : 0);
    if (selectedCount > 1) {
        exportType = 'all';
    } else if (exportImages) {
        exportType = 'images';
    } else if (exportVideos) {
        exportType = 'videos';
    } else if (exportAudio) {
        exportType = 'audio';
    } else {
        showNotification('Please select at least one export option (Images, Videos, or Audio)', 'error');
        return;
    }

    // Show loading state
    const exportBtn = document.getElementById('export-btn');
    const cancelBtn = document.getElementById('export-cancel-btn');
    const loadingEl = document.getElementById('export-loading');
    exportBtn.disabled = true;
    exportBtn.textContent = 'Exporting...';
    if (cancelBtn) cancelBtn.disabled = true;
    if (loadingEl) loadingEl.style.display = 'block';

    try {
        const response = await fetch('/api/shots/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                export_name: exportName || null,
                export_type: exportType,
                include_display_in_filename: includeDisplay,
                include_metadata: includeMetadata,
                export_format: exportFormat
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
    } finally {
        // Reset loading state
        exportBtn.disabled = false;
        exportBtn.textContent = 'Export';
        if (cancelBtn) cancelBtn.disabled = false;
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

function copyShotOrder() {
    const activeShots = shots.filter(s => !s.archived);
    if (activeShots.length === 0) {
        showNotification('No active shots to copy', 'error');
        return;
    }

    const lines = activeShots.map((shot, i) => {
        const num = String(i + 1).padStart(String(activeShots.length).length, '0');
        if (shot.display_name) {
            return `${num}. ${shot.name} — ${shot.display_name}`;
        }
        return `${num}. ${shot.name}`;
    });

    const text = lines.join('\n');

    navigator.clipboard.writeText(text).then(() => {
        showNotification(`Copied ${activeShots.length} shots to clipboard!`);
    }).catch(() => {
        // Fallback for browsers that don't support clipboard API
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showNotification(`Copied ${activeShots.length} shots to clipboard!`);
        } catch (e) {
            showNotification('Failed to copy to clipboard', 'error');
        }
        document.body.removeChild(textarea);
    });
}

// ============================================================
// Video Playback Functions
// ============================================================

let currentVideoShotIndex = -1;
let currentVideoAssetType = 'video';

// Image Navigation Functions
let currentImageShotIndex = -1;
let currentImageAssetType = '';

function playVideo(shotName, displayName, assetType) {
    assetType = assetType || 'video';
    const shot = shots.find(s => s.name === shotName);
    const asset = shot && shot[assetType];
    if (!asset || !asset.file) {
        showNotification(`No ${assetType === 'alt_video' ? 'alt ' : ''}video available for this shot`, 'error');
        return;
    }

    // Track which type we're viewing (for navigation)
    currentVideoAssetType = assetType;

    // Find the current shot index in the active shots array for this asset type
    const activeShots = shots.filter(s => !s.archived && s[assetType] && s[assetType].file);
    currentVideoShotIndex = activeShots.findIndex(s => s.name === shotName);

    const videoUrl = `/api/shots/video/${shotName}?type=${assetType}&v=${Date.now()}`;
    const videoPlayer = document.getElementById('video-player');
    const videoModalTitle = document.getElementById('video-modal-title');
    const videoVersion = document.getElementById('video-version');
    const videoPrompt = document.getElementById('video-prompt');

    // Set video source
    videoPlayer.src = videoUrl;

    // Set modal title and version
    const typeLabel = assetType === 'alt_video' ? 'Alt Video' : '';
    if (displayName) {
        videoModalTitle.innerHTML = `${escapeHtml(displayName)} ${typeLabel}<br><span style="font-size: 14px; opacity: 0.7; font-weight: normal;">(${shotName})</span>`;
    } else {
        videoModalTitle.textContent = `${shotName} ${typeLabel}`.trim();
    }

    videoVersion.textContent = String(asset.current_version).padStart(3, '0');

    // Set prompt text if available
    if (asset.prompt) {
        videoPrompt.textContent = asset.prompt;
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
    const assetType = currentVideoAssetType || 'video';
    const activeShots = shots.filter(s => !s.archived && s[assetType] && s[assetType].file);
    if (activeShots.length === 0 || currentVideoShotIndex === -1) return;

    const nextIndex = (currentVideoShotIndex + 1) % activeShots.length;
    const nextShot = activeShots[nextIndex];
    
    if (nextShot) {
        playVideo(nextShot.name, nextShot.display_name || '', assetType);
    }
}

function navigateToPreviousShot() {
    const assetType = currentVideoAssetType || 'video';
    const activeShots = shots.filter(s => !s.archived && s[assetType] && s[assetType].file);
    if (activeShots.length === 0 || currentVideoShotIndex === -1) return;

    const prevIndex = (currentVideoShotIndex - 1 + activeShots.length) % activeShots.length;
    const prevShot = activeShots[prevIndex];
    
    if (prevShot) {
        playVideo(prevShot.name, prevShot.display_name || '', assetType);
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

// ============================================================
// Image View Functions
// ============================================================

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

// ============================================================
// Audio Playback Functions
// ============================================================

let currentAudioShotIndex = -1;

function playAudio(shotName, displayName) {
    const shot = shots.find(s => s.name === shotName);
    const asset = shot && shot.audio;
    if (!asset || !asset.file) {
        showNotification('No audio available for this shot', 'error');
        return;
    }

    const activeShots = shots.filter(s => !s.archived && s.audio && s.audio.file);
    currentAudioShotIndex = activeShots.findIndex(s => s.name === shotName);

    const audioUrl = `/api/shots/audio/${shotName}?v=${Date.now()}`;
    const audioPlayer = document.getElementById('audio-player');
    const audioModalTitle = document.getElementById('audio-modal-title');
    const audioVersion = document.getElementById('audio-version');
    const audioPrompt = document.getElementById('audio-prompt');

    audioPlayer.src = audioUrl;

    if (displayName) {
        audioModalTitle.innerHTML = `${escapeHtml(displayName)} Audio<br><span style="font-size: 14px; opacity: 0.7; font-weight: normal;">(${shotName})</span>`;
    } else {
        audioModalTitle.textContent = `${shotName} Audio`;
    }

    audioVersion.textContent = String(asset.current_version).padStart(3, '0');

    if (asset.prompt) {
        audioPrompt.textContent = asset.prompt;
        audioPrompt.style.display = 'block';
    } else {
        audioPrompt.textContent = '';
        audioPrompt.style.display = 'none';
    }

    document.getElementById('audio-modal').style.display = 'flex';
    document.addEventListener('keydown', handleAudioModalKeydown);

    audioPlayer.load();
    audioPlayer.play().catch(e => {
        console.log('Audio autoplay prevented:', e);
    });
}

function navigateToNextAudio() {
    const activeShots = shots.filter(s => !s.archived && s.audio && s.audio.file);
    if (activeShots.length === 0 || currentAudioShotIndex === -1) return;
    const nextIndex = (currentAudioShotIndex + 1) % activeShots.length;
    const nextShot = activeShots[nextIndex];
    if (nextShot) {
        playAudio(nextShot.name, nextShot.display_name || '');
    }
}

function navigateToPreviousAudio() {
    const activeShots = shots.filter(s => !s.archived && s.audio && s.audio.file);
    if (activeShots.length === 0 || currentAudioShotIndex === -1) return;
    const prevIndex = (currentAudioShotIndex - 1 + activeShots.length) % activeShots.length;
    const prevShot = activeShots[prevIndex];
    if (prevShot) {
        playAudio(prevShot.name, prevShot.display_name || '');
    }
}

function handleAudioModalKeydown(event) {
    const audioModal = document.getElementById('audio-modal');
    if (audioModal.style.display !== 'flex') return;
    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            navigateToPreviousAudio();
            break;
        case 'ArrowRight':
            event.preventDefault();
            navigateToNextAudio();
            break;
    }
}

function closeAudioModal() {
    const audioModal = document.getElementById('audio-modal');
    const audioPlayer = document.getElementById('audio-player');
    audioModal.style.display = 'none';
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    audioPlayer.src = '';
    document.removeEventListener('keydown', handleAudioModalKeydown);
}

// ============================================================
// Global Exports
// ============================================================

// Expose image functions globally
window.showImage = showImage;
window.closeImageModal = closeImageModal;
window.navigateToNextImage = navigateToNextImage;
window.navigateToPreviousImage = navigateToPreviousImage;

// Expose audio functions globally
window.playAudio = playAudio;
window.closeAudioModal = closeAudioModal;
window.navigateToNextAudio = navigateToNextAudio;
window.navigateToPreviousAudio = navigateToPreviousAudio;

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