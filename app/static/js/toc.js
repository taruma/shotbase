/* ============================================================
   Table of Shots (TOC) — Panel module
   Depends on globals: shots, escapeHtml (from main.js)
   ============================================================ */

let tocObserver = null;

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

        const isTocArchivedOpen = localStorage.getItem('tocArchivedOpen') === 'true';

        const archivedHeader = document.createElement('button');
        archivedHeader.className = 'toc-archived-header';
        archivedHeader.innerHTML = `
            <span class="chevron" aria-hidden="true">${isTocArchivedOpen ? '▾' : '▸'}</span>
            <span>Archived Shots</span>
            <span class="count">(${archivedShots.length})</span>
        `;
        archivedHeader.addEventListener('click', toggleTocArchivedSection);

        const archivedList = document.createElement('ul');
        archivedList.className = 'toc-list';
        archivedList.id = 'toc-archived-list';
        archivedList.style.display = isTocArchivedOpen ? 'block' : 'none';

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

        archivedSection.appendChild(archivedHeader);
        archivedSection.appendChild(archivedList);
        toc.appendChild(archivedSection);
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

function toggleTocArchivedSection() {
    const archivedHeader = this;
    const archivedList = document.getElementById('toc-archived-list');
    const chevron = archivedHeader.querySelector('.chevron');

    const isOpen = archivedList.style.display !== 'none';
    archivedList.style.display = isOpen ? 'none' : 'block';
    chevron.textContent = isOpen ? '▸' : '▾';

    // Persist state to localStorage
    localStorage.setItem('tocArchivedOpen', isOpen ? 'false' : 'true');
}