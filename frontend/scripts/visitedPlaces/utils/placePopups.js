(function (global) {
  'use strict';

  // Shared by the edit/details modals so opening one closes any other.
  function closeOverlay(overlay) {
    if (!overlay) return;
    if (overlay._startPicker) {
      try { overlay._startPicker.destroy(); } catch (e) { /* ignore */ }
      overlay._startPicker = null;
    }
    if (overlay._endPicker) {
      try { overlay._endPicker.destroy(); } catch (e) { /* ignore */ }
      overlay._endPicker = null;
    }
    if (overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  }

  function closeAll() {
    document.querySelectorAll('.visited-place-details-overlay, .edit-place-modal-overlay').forEach(function (el) {
      closeOverlay(el);
    });
  }

  global.PlacePopups = {
    closeOverlay: closeOverlay,
    closeAll: closeAll
  };
})(window);
