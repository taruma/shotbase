/* ============================================================
   Search Modal — Self-contained module
   Depends on globals: shots, escapeHtml (from main.js)
   ============================================================ */

let searchIndex = [];
let searchDebounceTimer = null;
let searchFocusedIndex = -1;  // Track keyboard-focused result item

// Filter state
let searchContentFilter = 'all';   // 'all', 'prompt', 'caption', 'notes'
let searchArchiveFilter = 'all';  // 'all', 'active', 'archived'

// ============================================================
// Build in-memory search index from the global shots array
// ============================================================
function buildSearchIndex() {
    if (typeof shots === 'undefined' || !Array.isArray(shots)) {
        searchIndex = [];
        return;
    }

    searchIndex = [];

    shots.forEach(function (shot) {
        var items = [];
        var isArchived = !!shot.archived;

        // First Image: prompt + caption
        if (shot.first_image) {
            var prompt = (shot.first_image.prompt || '').trim();
            var caption = (shot.first_image.caption || '').trim();
            if (prompt) items.push({ field: 'First Frame Prompt', text: prompt, badgeType: 'prompt', assetLabel: 'First Frame' });
            if (caption) items.push({ field: 'First Frame Caption', text: caption, badgeType: 'caption', assetLabel: 'First Frame' });
        }

        // Last Image: prompt + caption
        if (shot.last_image) {
            var prompt = (shot.last_image.prompt || '').trim();
            var caption = (shot.last_image.caption || '').trim();
            if (prompt) items.push({ field: 'Last Frame Prompt', text: prompt, badgeType: 'prompt', assetLabel: 'Last Frame' });
            if (caption) items.push({ field: 'Last Frame Caption', text: caption, badgeType: 'caption', assetLabel: 'Last Frame' });
        }

        // Video: prompt + caption
        if (shot.video) {
            var prompt = (shot.video.prompt || '').trim();
            var caption = (shot.video.caption || '').trim();
            if (prompt) items.push({ field: 'Video Prompt', text: prompt, badgeType: 'prompt', assetLabel: 'Video' });
            if (caption) items.push({ field: 'Video Caption', text: caption, badgeType: 'caption', assetLabel: 'Video' });
        }

        // Alt Video: prompt + caption
        if (shot.alt_video) {
            var prompt = (shot.alt_video.prompt || '').trim();
            var caption = (shot.alt_video.caption || '').trim();
            if (prompt) items.push({ field: 'Alt Video Prompt', text: prompt, badgeType: 'prompt', assetLabel: 'Alt Video' });
            if (caption) items.push({ field: 'Alt Video Caption', text: caption, badgeType: 'caption', assetLabel: 'Alt Video' });
        }

        // Notes
        var notes = (shot.notes || '').trim();
        if (notes) items.push({ field: 'Notes', text: notes, badgeType: 'notes-badge', assetLabel: '' });

        // Shot Name (always searchable)
        var shotName = shot.name || '';
        if (shotName) items.push({ field: 'Shot Name', text: shotName, badgeType: 'shot-name-badge', assetLabel: '' });

        // Display Name (always searchable)
        var displayName = (shot.display_name || '').trim();
        if (displayName) items.push({ field: 'Display Name', text: displayName, badgeType: 'display-name-badge', assetLabel: '' });

        if (items.length > 0) {
            searchIndex.push({
                shotName: shot.name,
                displayName: shot.display_name || '',
                archived: isArchived,
                items: items
            });
        }
    });
}

// ============================================================
// Modal open / close
// ============================================================
function openSearchModal() {
    buildSearchIndex();

    var input = document.getElementById('search-input');
    var results = document.getElementById('search-results');
    var stats = document.getElementById('search-stats');

    if (input) input.value = '';
    if (results) results.innerHTML = '<p class="search-placeholder">Type to search across all shots...</p>';
    if (stats) stats.textContent = '';

    var modal = document.getElementById('search-modal');
    if (modal) {
        modal.style.display = 'flex';
        // Focus the input after a tiny delay (modal becomes visible first)
        setTimeout(function () {
            if (input) input.focus();
        }, 100);
    }
}

function closeSearchModal() {
    var modal = document.getElementById('search-modal');
    if (modal) modal.style.display = 'none';

    var input = document.getElementById('search-input');
    if (input) input.value = '';

    // Reset filters to defaults
    searchContentFilter = 'all';
    searchArchiveFilter = 'all';

    resetFilterPills();

    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = null;
    }
}

// ============================================================
// Filter pill controls
// ============================================================
function setContentFilter(type, btn) {
    searchContentFilter = type;
    // Update active state on content filter pills
    var pills = document.querySelectorAll('#search-modal .search-filter-pill[data-content-filter]');
    for (var i = 0; i < pills.length; i++) {
        pills[i].classList.remove('active');
    }
    if (btn) btn.classList.add('active');
    // Re-run search
    triggerSearchRefresh();
}

function setArchiveFilter(type, btn) {
    searchArchiveFilter = type;
    // Update active state on archive filter pills
    var pills = document.querySelectorAll('#search-modal .search-filter-pill[data-archive-filter]');
    for (var i = 0; i < pills.length; i++) {
        pills[i].classList.remove('active');
    }
    if (btn) btn.classList.add('active');
    // Re-run search
    triggerSearchRefresh();
}

function resetFilterPills() {
    // Content: set 'all' active
    var contentPills = document.querySelectorAll('#search-modal .search-filter-pill[data-content-filter]');
    for (var i = 0; i < contentPills.length; i++) {
        contentPills[i].classList.toggle('active', contentPills[i].getAttribute('data-content-filter') === 'all');
    }
    // Archive: set 'all' active
    var archivePills = document.querySelectorAll('#search-modal .search-filter-pill[data-archive-filter]');
    for (var i = 0; i < archivePills.length; i++) {
        archivePills[i].classList.toggle('active', archivePills[i].getAttribute('data-archive-filter') === 'all');
    }
}

function triggerSearchRefresh() {
    var input = document.getElementById('search-input');
    if (input) {
        var data = performSearch(input.value);
        renderSearchResults(data);
    }
}

// ============================================================
// Search logic
// ============================================================
function performSearch(query) {
    var q = (query || '').trim().toLowerCase();

    if (!q || q.length === 0) {
        return { query: '', results: [] };
    }

    // Split query into tokens for multi-word AND search
    var tokens = q.split(/\s+/).filter(function (t) { return t.length > 0; });

    var allResults = [];

    // Search through the index
    searchIndex.forEach(function (entry) {
        var matches = [];

        // Apply archive filter
        if (searchArchiveFilter === 'active' && entry.archived) return;
        if (searchArchiveFilter === 'archived' && !entry.archived) return;

        entry.items.forEach(function (item) {
            // Apply content type filter (skip for shot/display name — always searchable)
            if (item.badgeType !== 'shot-name-badge' && item.badgeType !== 'display-name-badge') {
                if (searchContentFilter === 'prompt' && item.badgeType !== 'prompt') return;
                if (searchContentFilter === 'caption' && item.badgeType !== 'caption') return;
                if (searchContentFilter === 'notes' && item.badgeType !== 'notes-badge') return;
            }

            var text = item.text || '';
            var lowerText = text.toLowerCase();

            // All tokens must be found in the text (any order, any position)
            var allMatch = tokens.every(function (token) {
                return lowerText.indexOf(token) !== -1;
            });

            if (allMatch) {
                matches.push({
                    field: item.field,
                    text: text,
                    badgeType: item.badgeType,
                    assetLabel: item.assetLabel
                });
            }
        });

        if (matches.length > 0) {
            allResults.push({
                shotName: entry.shotName,
                displayName: entry.displayName,
                matches: matches,
                matchCount: matches.length
            });
        }
    });

    return { query: query, results: allResults };
}

// ============================================================
// Highlight matching text and build snippet
// ============================================================
function highlightSnippet(text, query) {
    if (!text || !query) return safeEscape(text);

    // Split query into tokens so each word gets highlighted individually
    var tokens = query.trim().split(/\s+/).filter(function (t) { return t.length > 0; });

    // Build array of match ranges: { start, end } in the raw escaped text
    var escaped = safeEscape(text);
    var lower = escaped.toLowerCase();
    var ranges = [];

    tokens.forEach(function (token) {
        var tokenLower = token.toLowerCase();
        var idx = 0;
        while (true) {
            idx = lower.indexOf(tokenLower, idx);
            if (idx === -1) break;
            // Avoid overlapping highlights
            var overlap = false;
            for (var r = 0; r < ranges.length; r++) {
                if (idx < ranges[r].end && idx + token.length > ranges[r].start) {
                    overlap = true;
                    break;
                }
            }
            if (!overlap) {
                ranges.push({ start: idx, end: idx + token.length });
            }
            idx++;
        }
    });

    // Sort ranges by start position
    ranges.sort(function (a, b) { return a.start - b.start; });

    // If no ranges, just return a short preview of the text
    if (ranges.length === 0) {
        return escaped.substring(0, 200);
    }

    // Center the snippet window around the first match
    var CONTEXT = 100;  // characters of context before/after the match
    var firstMatch = ranges[0].start;
    var windowStart = Math.max(0, firstMatch - CONTEXT);
    // Try to start at a word boundary (space or newline), cap backtrack to 40 chars
    var originalWindowStart = windowStart;
    var scanLimit = Math.max(0, windowStart - 40);
    while (windowStart > scanLimit && escaped.charAt(windowStart) !== ' ' && escaped.charAt(windowStart) !== '\n') {
        windowStart--;
    }
    // If no word boundary found in scan range, revert to original position
    if (windowStart <= scanLimit && escaped.charAt(windowStart) !== ' ' && escaped.charAt(windowStart) !== '\n') {
        windowStart = originalWindowStart;
    }
    var windowEnd = Math.min(escaped.length, firstMatch + CONTEXT + (ranges[0].end - ranges[0].start));
    // Extend to include nearby matches
    for (var i = 1; i < ranges.length; i++) {
        if (ranges[i].start < windowEnd + CONTEXT) {
            windowEnd = Math.min(escaped.length, ranges[i].end + CONTEXT);
        } else {
            break;
        }
    }

    var prefix = windowStart > 0 ? '…' : '';
    var suffix = windowEnd < escaped.length ? '…' : '';

    // Extract the window text
    var windowText = escaped.substring(windowStart, windowEnd);

    // Adjust ranges to be relative to windowStart
    var result = prefix;
    var lastIdx = 0;  // position within windowText
    for (var i = 0; i < ranges.length; i++) {
        var relStart = ranges[i].start - windowStart;
        var relEnd = ranges[i].end - windowStart;

        // Skip ranges outside the window
        if (relEnd < 0) continue;
        if (relStart >= windowText.length) break;

        // Clamp to window bounds
        relStart = Math.max(0, relStart);
        relEnd = Math.min(windowText.length, relEnd);

        if (relStart > lastIdx) {
            result += windowText.substring(lastIdx, relStart);
        }
        if (relEnd > relStart) {
            result += '<mark>' + windowText.substring(relStart, relEnd) + '</mark>';
        }
        lastIdx = relEnd;
    }
    result += windowText.substring(lastIdx);
    result += suffix;

    return result;
}

function safeEscape(str) {
    if (typeof escapeHtml === 'function') {
        return escapeHtml(str);
    }
    // Fallback inline escape
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ============================================================
// Keyboard navigation focus helper
// ============================================================
function updateSearchFocus(items, newIndex) {
    // Remove current focus
    for (var i = 0; i < items.length; i++) {
        items[i].classList.remove('keyboard-focus');
    }

    // Clamp to valid range
    if (newIndex < 0) {
        newIndex = items.length - 1;
    } else if (newIndex >= items.length) {
        newIndex = 0;
    }

    searchFocusedIndex = newIndex;

    // Apply focus to target
    if (newIndex >= 0 && newIndex < items.length) {
        items[newIndex].classList.add('keyboard-focus');
        // Scroll the focused item into view within the results container
        items[newIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
}

// ============================================================
// Render results
// ============================================================
function renderSearchResults(data) {
    var resultsEl = document.getElementById('search-results');
    var statsEl = document.getElementById('search-stats');

    if (!resultsEl) return;

    var query = data.query || '';
    var results = data.results || [];

    if (!query || query.length === 0) {
        resultsEl.innerHTML = '<p class="search-placeholder">Type to search across all shots...</p>';
        if (statsEl) statsEl.textContent = '';
        return;
    }

    if (results.length === 0) {
        resultsEl.innerHTML = '<p class="search-no-results">No matches found for "<strong>' + safeEscape(query) + '</strong>"</p>';
        if (statsEl) statsEl.textContent = '0 results';
        return;
    }

    // Build stats
    var totalMatches = results.reduce(function (sum, r) { return sum + r.matchCount; }, 0);
    if (statsEl) {
        statsEl.textContent = totalMatches + ' match' + (totalMatches !== 1 ? 'es' : '') +
            ' across ' + results.length + ' shot' + (results.length !== 1 ? 's' : '');
    }

    // Reset keyboard focus when new results are rendered
    searchFocusedIndex = -1;

    // Build HTML
    var html = '<ul class="search-results-list">';

    results.forEach(function (shotResult) {
        var displayPart = shotResult.displayName
            ? '<span class="search-shot-display">' + safeEscape(shotResult.displayName) + '</span>'
            : '';

        html += '<li class="search-shot-group">';
        html += '<div class="search-shot-header search-clickable" onclick="scrollToShot(\'' + safeEscape(shotResult.shotName).replace(/'/g, "\\'") + '\'); closeSearchModal();">';
        html += '<span class="search-shot-name">' + safeEscape(shotResult.shotName) + '</span>';
        html += displayPart;
        html += '<span class="search-match-count">' + shotResult.matchCount + ' match' + (shotResult.matchCount !== 1 ? 'es' : '') + '</span>';
        html += '</div>';

        html += '<ul class="search-match-items">';
        shotResult.matches.forEach(function (match) {
            var labelSuffix = match.assetLabel ? ' <span class="asset-label">(' + safeEscape(match.assetLabel) + ')</span>' : '';

            html += '<li class="search-match-item search-clickable" onclick="scrollToShot(\'' + safeEscape(shotResult.shotName).replace(/'/g, "\\'") + '\'); closeSearchModal();">';
            html += '<div class="search-match-line">';
            html += '<span class="search-match-badge ' + match.badgeType + '">' + safeEscape(match.field) + labelSuffix + '</span>';
            html += '<span class="search-snippet">' + highlightSnippet(match.text, query) + '</span>';
            html += '</div>';
            html += '</li>';
        });
        html += '</ul>';

        html += '</li>';
    });

    html += '</ul>';
    resultsEl.innerHTML = html;
}

// ============================================================
// Scroll to shot in the main grid
// ============================================================
function scrollToShot(shotName) {
    if (!shotName) return;

    // Shot rows have id="shot-row-SH###"
    var target = document.getElementById('shot-row-' + shotName);

    // Fallback: search by shot name text in .shot-name elements
    if (!target) {
        var shotNameEls = document.querySelectorAll('.shot-name');
        for (var i = 0; i < shotNameEls.length; i++) {
            var row = shotNameEls[i].closest('.shot-row');
            if (row) {
                var nameEl = row.querySelector('.shot-name');
                if (nameEl) {
                    var text = nameEl.textContent.trim();
                    // shot-name div may contain shot-code span too, check if it includes the shot name
                    var codeEl = row.querySelector('.shot-code');
                    if (codeEl && codeEl.textContent.trim() === '(' + shotName + ')') {
                        target = row;
                        break;
                    }
                    if (!codeEl && text === shotName) {
                        target = row;
                        break;
                    }
                }
            }
        }
    }

    if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Briefly highlight the shot card
        target.style.transition = 'box-shadow 0.3s ease';
        target.style.boxShadow = '0 0 20px rgba(240, 160, 64, 0.5)';
        setTimeout(function () {
            target.style.boxShadow = '';
        }, 1500);
    }
}

// ============================================================
// Event bindings (DOMContentLoaded)
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('search-input');

    if (input) {
        input.addEventListener('input', function () {
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer);
            }
            searchDebounceTimer = setTimeout(function () {
                var data = performSearch(input.value);
                renderSearchResults(data);
            }, 200);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeSearchModal();
                return;
            }

            // Keyboard navigation: ArrowDown / ArrowUp / Enter
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
                var items = document.querySelectorAll('#search-results .search-clickable');
                if (items.length === 0) return;

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    updateSearchFocus(items, searchFocusedIndex + 1);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    // If nothing is focused, select the last item
                    var nextIdx = searchFocusedIndex >= 0 ? searchFocusedIndex - 1 : items.length - 1;
                    updateSearchFocus(items, nextIdx);
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    if (searchFocusedIndex >= 0 && searchFocusedIndex < items.length) {
                        items[searchFocusedIndex].click();
                    }
                }
            }
        });
    }

    // Close modal when clicking outside the content
    var searchModal = document.getElementById('search-modal');
    if (searchModal) {
        searchModal.addEventListener('click', function (e) {
            if (e.target === searchModal) {
                closeSearchModal();
            }
        });
    }

    // Global keyboard shortcut: Ctrl+Shift+F / Cmd+Shift+F to open search
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') {
            e.preventDefault();
            openSearchModal();
        }
    });
});