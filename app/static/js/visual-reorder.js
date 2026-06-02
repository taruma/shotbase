/* ============================================================
   Visual Reorder Modal — Self-contained module
   Depends on globals: shots, renderShots, showNotification,
   captureScroll, restoreScroll, escapeHtml, displayAssetLabel, Sortable,
   playVideo, closeVideoModal, handleVideoModalKeydown (from main.js)
   ============================================================ */

let visualReorderSortable = null;
let visualThumbType = 'video';
let previewMode = false;
let editMode = false;
let visualCurrentShotName = null;
let visualCurrentAssetType = 'video';
let _savedNavigateNext = null;
let _savedNavigatePrev = null;

// ============================================================
// Preview toggle — injects button into thumbnail selector row
// ============================================================

function ensurePreviewToggleBtn() {
    if (document.getElementById('visual-preview-toggle')) return;

    var selector = document.querySelector('#visual-reorder-modal .visual-reorder-thumbnail-selector');
    if (!selector) return;

    // Separator to visually distinguish from thumb type pills
    var sep = document.createElement('span');
    sep.className = 'thumbnail-selector-separator';
    sep.setAttribute('aria-hidden', 'true');
    selector.appendChild(sep);

    var btn = document.createElement('button');
    btn.id = 'visual-preview-toggle';
    btn.className = 'preview-toggle-btn';
    btn.textContent = '▶ Preview';
    btn.title = 'Toggle video preview mode';
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        togglePreviewMode();
    });
    selector.appendChild(btn);
}

function ensureEditToggleBtn() {
    if (document.getElementById('visual-edit-toggle')) return;

    var selector = document.querySelector('#visual-reorder-modal .visual-reorder-thumbnail-selector');
    if (!selector) return;

    var btn = document.createElement('button');
    btn.id = 'visual-edit-toggle';
    btn.className = 'edit-toggle-btn';
    btn.textContent = '✏️ Edit';
    btn.title = 'Toggle edit display name mode';
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleEditMode();
    });
    selector.appendChild(btn);
}

function togglePreviewMode() {
    previewMode = !previewMode;

    var btn = document.getElementById('visual-preview-toggle');
    var grid = document.getElementById('visual-reorder-grid');

    if (previewMode) {
        // Turn off edit mode if active
        if (editMode) {
            editMode = false;
            var etBtn = document.getElementById('visual-edit-toggle');
            if (etBtn) etBtn.classList.remove('active');
            if (grid) grid.classList.remove('edit-mode');
        }

        if (btn) {
            btn.textContent = '■ Preview';
            btn.classList.add('active');
        }
        if (grid) grid.classList.add('preview-mode');

        // Save and override navigation functions
        if (window.navigateToNextShot) {
            _savedNavigateNext = window.navigateToNextShot;
            window.navigateToNextShot = visualNavigateNext;
        }
        if (window.navigateToPreviousShot) {
            _savedNavigatePrev = window.navigateToPreviousShot;
            window.navigateToPreviousShot = visualNavigatePrev;
        }
    } else {
        if (btn) {
            btn.textContent = '▶ Preview';
            btn.classList.remove('active');
        }
        if (grid) grid.classList.remove('preview-mode');

        // Restore original navigation functions
        restoreNavigationOverrides();
    }
}

function toggleEditMode() {
    editMode = !editMode;

    var btn = document.getElementById('visual-edit-toggle');
    var grid = document.getElementById('visual-reorder-grid');

    if (editMode) {
        // Turn off preview if active
        if (previewMode) {
            togglePreviewMode();
        }
        if (btn) btn.classList.add('active');
        if (grid) grid.classList.add('edit-mode');
    } else {
        if (btn) btn.classList.remove('active');
        if (grid) grid.classList.remove('edit-mode');
    }
}

function restoreNavigationOverrides() {
    if (_savedNavigateNext) {
        window.navigateToNextShot = _savedNavigateNext;
        _savedNavigateNext = null;
    }
    if (_savedNavigatePrev) {
        window.navigateToPreviousShot = _savedNavigatePrev;
        _savedNavigatePrev = null;
    }
}

// ============================================================
// Modal open/close
// ============================================================

function openVisualReorderModal() {
    captureScroll();

    var grid = document.getElementById('visual-reorder-grid');
    var filterInput = document.getElementById('visual-reorder-filter');
    if (!grid) return;

    // Reset preview and edit state
    previewMode = false;
    editMode = false;
    visualCurrentShotName = null;
    visualCurrentAssetType = 'video';
    restoreNavigationOverrides();
    if (grid) grid.classList.remove('preview-mode');
    if (grid) grid.classList.remove('edit-mode');
    var ptBtn = document.getElementById('visual-preview-toggle');
    if (ptBtn) {
        ptBtn.textContent = '▶ Preview';
        ptBtn.classList.remove('active');
    }
    var etBtn = document.getElementById('visual-edit-toggle');
    if (etBtn) {
        etBtn.classList.remove('active');
    }

    grid.innerHTML = '';
    if (filterInput) filterInput.value = '';

    var activeShots = shots.filter(function(s) { return !s.archived; });

    if (activeShots.length === 0) {
        grid.innerHTML = '<div class="visual-reorder-grid-empty">No active shots to reorder</div>';
    } else {
        activeShots.forEach(function(shot, index) {
            grid.appendChild(createVisualCard(shot, index + 1));
        });
        initVisualSortable();
    }

    // Reset thumbnail selector to default (video)
    visualThumbType = 'video';
    var pills = document.querySelectorAll('.visual-reorder-thumbnail-selector .pill-button');
    pills.forEach(function(btn) {
        if (btn.dataset.thumbType === 'video') {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Ensure preview and edit toggle buttons exist
    ensurePreviewToggleBtn();
    ensureEditToggleBtn();

    document.body.style.overflow = 'hidden';
    document.getElementById('visual-reorder-modal').style.display = 'flex';
}

function createVisualCard(shot, orderNum) {
    var card = document.createElement('div');
    card.className = 'visual-reorder-card';
    card.dataset.shotName = shot.name;

    // Build thumbnail
    var thumbUrl = getThumbForType(shot, visualThumbType);
    var thumbHTML;
    if (thumbUrl) {
        thumbHTML = '<img src="' + thumbUrl + '?v=' + Date.now() + '" alt="thumbnail" loading="lazy">';
    } else {
        var label = displayAssetLabel(visualThumbType);
        thumbHTML = '<div class="card-thumb-placeholder">No ' + label.toLowerCase() + '</div>';
    }

    // Build label area
    var displayName = shot.display_name || '';
    var nameHTML = '';
    if (displayName) {
        nameHTML = '<div class="card-display-name" title="' + escapeHtml(displayName) + '">' + escapeHtml(displayName) + '</div>';
    }
    var codeHTML = '<div class="card-shot-code">' + escapeHtml(shot.name) + '</div>';

    card.innerHTML =
        '<span class="card-number">#' + orderNum + '</span>' +
        '<div class="card-thumb-wrapper">' + thumbHTML + '</div>' +
        '<div class="card-info">' +
            nameHTML +
            codeHTML +
        '</div>';

    // Thumbnail click → play video (only when preview mode is ON)
    var wrapper = card.querySelector('.card-thumb-wrapper');
    if (wrapper) {
        wrapper.addEventListener('click', function(e) {
            if (!previewMode) return;
            e.stopPropagation();
            var shotName = card.dataset.shotName;
            var shot = null;
            for (var i = 0; i < shots.length; i++) {
                if (shots[i].name === shotName) { shot = shots[i]; break; }
            }
            if (!shot) return;
            visualPlayCardVideo(shot);
        });
    }

    // Card info click → edit display name (only when edit mode is ON)
    var info = card.querySelector('.card-info');
    if (info) {
        info.addEventListener('click', function(e) {
            if (!editMode) return;
            e.stopPropagation();
            var shotName = card.dataset.shotName;
            var shot = null;
            for (var i = 0; i < shots.length; i++) {
                if (shots[i].name === shotName) { shot = shots[i]; break; }
            }
            if (!shot) return;
            var currentName = shot.display_name || '';
            var newName = prompt('Edit display name for ' + shotName + ':', currentName);
            if (newName === null || newName === currentName) return;
            // Update shots array
            shot.display_name = newName;
            // Update card info HTML
            var dnHTML = newName ? '<div class="card-display-name" title="' + escapeHtml(newName) + '">' + escapeHtml(newName) + '</div>' : '';
            info.innerHTML = dnHTML + '<div class="card-shot-code">' + escapeHtml(shotName) + '</div>';
            // Persist via existing API
            if (typeof window.saveDisplayName === 'function') {
                window.saveDisplayName(shotName, newName);
            }
        });
    }

    return card;
}

// ============================================================
// Thumbnail type switching
// ============================================================

function getThumbForType(shot, type) {
    var asset = shot[type];
    if (!asset || !asset.thumbnail) return null;
    return asset.thumbnail;
}

function switchVisualThumbType(type, btn) {
    visualThumbType = type;

    var pills = document.querySelectorAll('.visual-reorder-thumbnail-selector .pill-button');
    pills.forEach(function(b) {
        if (b === btn) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });

    var cards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
    cards.forEach(function(card) {
        var shotName = card.dataset.shotName;
        var shot = null;
        for (var i = 0; i < shots.length; i++) {
            if (shots[i].name === shotName) { shot = shots[i]; break; }
        }
        if (!shot) return;

        var thumbUrl = getThumbForType(shot, type);
        var wrapper = card.querySelector('.card-thumb-wrapper');
        if (!wrapper) return;

        if (thumbUrl) {
            wrapper.innerHTML = '<img src="' + thumbUrl + '?v=' + Date.now() + '" alt="thumbnail" loading="lazy">';
        } else {
            var label = displayAssetLabel(type);
            wrapper.innerHTML = '<div class="card-thumb-placeholder">No ' + label.toLowerCase() + '</div>';
        }
    });
}

// ============================================================
// SortableJS
// ============================================================

function initVisualSortable() {
    var grid = document.getElementById('visual-reorder-grid');
    if (!grid) return;

    if (visualReorderSortable) {
        visualReorderSortable.destroy();
        visualReorderSortable = null;
    }

    visualReorderSortable = new Sortable(grid, {
        animation: 150,
        ghostClass: 'visual-reorder-ghost',
        chosenClass: 'visual-reorder-chosen',
        dragClass: 'visual-reorder-drag'
    });
}

// ============================================================
// Save and close
// ============================================================

function closeVisualReorderModal() {
    var modal = document.getElementById('visual-reorder-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    if (visualReorderSortable) {
        visualReorderSortable.destroy();
        visualReorderSortable = null;
    }
    // Clean up preview and edit state
    previewMode = false;
    editMode = false;
    visualCurrentShotName = null;
    restoreNavigationOverrides();
    var grid = document.getElementById('visual-reorder-grid');
    if (grid) grid.classList.remove('preview-mode');
    if (grid) grid.classList.remove('edit-mode');
    var etBtn = document.getElementById('visual-edit-toggle');
    if (etBtn) {
        etBtn.classList.remove('active');
    }
    // Restore body scroll
    document.body.style.overflow = '';
}

function saveVisualReorder() {
    var cards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
    if (cards.length === 0) {
        closeVisualReorderModal();
        return;
    }

    var activeOrdered = [];
    cards.forEach(function(c) {
        activeOrdered.push(c.dataset.shotName);
    });

    var archived = [];
    shots.forEach(function(s) {
        if (s.archived) archived.push(s.name);
    });

    var shotOrder = activeOrdered.concat(archived);

    fetch('/api/shots/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shot_order: shotOrder })
    })
    .then(function(resp) { return resp.json(); })
    .then(function(result) {
        if (result.success) {
            shots.sort(function(a, b) {
                return shotOrder.indexOf(a.name) - shotOrder.indexOf(b.name);
            });
            renderShots();
            closeVisualReorderModal();
            showNotification('Shot order saved');
        } else {
            showNotification(result.error || 'Failed to save order', 'error');
        }
    })
    .catch(function(e) {
        console.error('Visual reorder save failed:', e);
        showNotification('Error saving shot order', 'error');
    });
}

// ============================================================
// Preview/Playback — uses existing video modal (playVideo from main.js)
// Navigation follows visual reorder card DOM order
// ============================================================

function getVisibleVisualCards() {
    var allCards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
    var visible = [];
    allCards.forEach(function(card) {
        if (card.style.display !== 'none') {
            visible.push(card);
        }
    });
    return visible;
}

// Determine which asset type to play based on current thumbnail type.
// 'video' and 'alt_video' map to themselves; image types default to 'video'.
function _getPlayType() {
    if (visualThumbType === 'alt_video') return 'alt_video';
    return 'video';
}

function visualPlayCardVideo(shot) {
    var playType = _getPlayType();
    visualCurrentShotName = shot.name;
    visualCurrentAssetType = playType;

    var asset = shot[playType];
    if (!asset || !asset.file) {
        var label = playType === 'alt_video' ? 'alt ' : '';
        showNotification('No ' + label + 'video available for ' + shot.name, 'error');
        return;
    }

    if (typeof window.playVideo === 'function') {
        window.playVideo(shot.name, shot.display_name || '', playType);
    }
}

function visualNavigateNext() {
    var cards = getVisibleVisualCards();
    if (cards.length === 0) return;
    var playType = _getPlayType();

    var idx = -1;
    for (var i = 0; i < cards.length; i++) {
        if (cards[i].dataset.shotName === visualCurrentShotName) {
            idx = i;
            break;
        }
    }
    if (idx === -1) return;

    for (var j = 1; j <= cards.length; j++) {
        var nextIdx = (idx + j) % cards.length;
        var nextName = cards[nextIdx].dataset.shotName;
        var nextShot = null;
        for (var k = 0; k < shots.length; k++) {
            if (shots[k].name === nextName) { nextShot = shots[k]; break; }
        }
        if (nextShot && nextShot[playType] && nextShot[playType].file) {
            visualCurrentShotName = nextName;
            window.playVideo(nextName, nextShot.display_name || '', playType);
            return;
        }
    }
}

function visualNavigatePrev() {
    var cards = getVisibleVisualCards();
    if (cards.length === 0) return;
    var playType = _getPlayType();

    var idx = -1;
    for (var i = 0; i < cards.length; i++) {
        if (cards[i].dataset.shotName === visualCurrentShotName) {
            idx = i;
            break;
        }
    }
    if (idx === -1) return;

    for (var j = 1; j <= cards.length; j++) {
        var prevIdx = (idx - j + cards.length) % cards.length;
        var prevName = cards[prevIdx].dataset.shotName;
        var prevShot = null;
        for (var k = 0; k < shots.length; k++) {
            if (shots[k].name === prevName) { prevShot = shots[k]; break; }
        }
        if (prevShot && prevShot[playType] && prevShot[playType].file) {
            visualCurrentShotName = prevName;
            window.playVideo(prevName, prevShot.display_name || '', playType);
            return;
        }
    }
}

// ============================================================
// Event wiring (runs after DOM ready)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    ensurePreviewToggleBtn();
    ensureEditToggleBtn();

    // Filter input
    var filter = document.getElementById('visual-reorder-filter');
    if (filter) {
        filter.addEventListener('input', function() {
            var q = this.value.toLowerCase();
            var cards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
            cards.forEach(function(card) {
                var displayNameEl = card.querySelector('.card-display-name');
                var codeEl = card.querySelector('.card-shot-code');
                var text = (displayNameEl ? displayNameEl.textContent : '') +
                           (codeEl ? codeEl.textContent : '');
                card.style.display = text.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
            });
        });
    }

    // Click outside modal to close
    document.addEventListener('click', function(e) {
        var modal = document.getElementById('visual-reorder-modal');
        if (modal && e.target === modal) {
            closeVisualReorderModal();
        }
    });

    // Escape key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var modal = document.getElementById('visual-reorder-modal');
            if (modal && modal.style.display === 'flex') {
                closeVisualReorderModal();
            }
        }
    });
});

// Expose to global scope
window.openVisualReorderModal = openVisualReorderModal;
window.closeVisualReorderModal = closeVisualReorderModal;
window.saveVisualReorder = saveVisualReorder;
window.switchVisualThumbType = switchVisualThumbType;
window.togglePreviewMode = togglePreviewMode;
window.toggleEditMode = toggleEditMode;
