/* ============================================================
   Visual Reorder Modal — Self-contained module
   Depends on globals: shots, renderShots, showNotification,
   captureScroll, restoreScroll, escapeHtml, displayAssetLabel, Sortable
   ============================================================ */

let visualReorderSortable = null;
let visualThumbType = 'video';

function openVisualReorderModal() {
    captureScroll();

    const grid = document.getElementById('visual-reorder-grid');
    const filterInput = document.getElementById('visual-reorder-filter');
    if (!grid) return;

    grid.innerHTML = '';
    if (filterInput) filterInput.value = '';

    const activeShots = shots.filter(function(s) { return !s.archived; });

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

    return card;
}

function getThumbForType(shot, type) {
    var asset = shot[type];
    if (!asset || !asset.thumbnail) return null;
    return asset.thumbnail;
}

function switchVisualThumbType(type, btn) {
    visualThumbType = type;

    // Update active pill styling
    var pills = document.querySelectorAll('.visual-reorder-thumbnail-selector .pill-button');
    pills.forEach(function(b) {
        if (b === btn) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });

    // Rebuild all card thumbnails in-place
    var cards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
    cards.forEach(function(card) {
        var shotName = card.dataset.shotName;
        var shot = null;
        for (var i = 0; i < shots.length; i++) {
            if (shots[i].name === shotName) {
                shot = shots[i];
                break;
            }
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

function updateCardNumbers() {
    var cards = document.querySelectorAll('#visual-reorder-grid .visual-reorder-card');
    cards.forEach(function(card, i) {
        var numBadge = card.querySelector('.card-number');
        if (numBadge) {
            numBadge.textContent = '#' + (i + 1);
        }
    });
}

function closeVisualReorderModal() {
    var modal = document.getElementById('visual-reorder-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    if (visualReorderSortable) {
        visualReorderSortable.destroy();
        visualReorderSortable = null;
    }
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

// ---- Event wiring (runs after DOM ready) ----
document.addEventListener('DOMContentLoaded', function() {
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