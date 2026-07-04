/* ============================================================
   Modal Behavior — Centralized click-outside + Escape handlers
   Applies to all .modal elements automatically.
   Close functions must be globally accessible (window scope).
   ============================================================ */

// Registry: modal element ID → close function
var _modalCloseMap = {
    'create-project-modal': closeCreateProjectModal,
    'prompt-modal': closePromptModal,
    'reorder-modal': closeReorderModal,
    'search-modal': closeSearchModal,
    'visual-reorder-modal': closeVisualReorderModal,
    'project-info-modal': closeProjectInfoModal,
    'export-modal': closeExportModal,
    'video-modal': closeVideoModal,
    'image-modal': closeImageModal,
    'audio-modal': closeAudioModal
};

// Click outside modal content → close
document.addEventListener('click', function (e) {
    var modalId, modal, closeFn;
    for (modalId in _modalCloseMap) {
        if (!_modalCloseMap.hasOwnProperty(modalId)) continue;
        modal = document.getElementById(modalId);
        closeFn = _modalCloseMap[modalId];
        if (modal && closeFn && modal.style.display === 'flex' && e.target === modal) {
            closeFn();
            return;
        }
    }
});

// Escape key → close
document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var modalId, modal, closeFn;
    for (modalId in _modalCloseMap) {
        if (!_modalCloseMap.hasOwnProperty(modalId)) continue;
        modal = document.getElementById(modalId);
        closeFn = _modalCloseMap[modalId];
        if (modal && closeFn && modal.style.display === 'flex') {
            closeFn();
            return;
        }
    }
});