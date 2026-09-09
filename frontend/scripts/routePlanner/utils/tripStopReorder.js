(function (global) {
  'use strict';

  function plannedTripsT(key, fallback) {
    if (global.i18n && typeof global.i18n.t === 'function') {
      var v = global.i18n.t('plannedTrips.' + key);
      if (v && String(v).indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  function isReturnHomeRow(row) {
    return !!(row && row.getAttribute('data-return-home') === '1');
  }

  function buildDragHandle(isReturnHome) {
    if (isReturnHome) {
      var spacer = document.createElement('div');
      spacer.className = 'trip-stop-drag-handle trip-stop-drag-handle--spacer';
      spacer.setAttribute('aria-hidden', 'true');
      return spacer;
    }
    var handle = document.createElement('button');
    handle.type = 'button';
    handle.className = 'trip-stop-drag-handle';
    handle.setAttribute('data-i18n-aria-label', 'plannedTrips.editDragHandle');
    handle.setAttribute('aria-label', plannedTripsT('editDragHandle', 'Drag to reorder'));
    handle.innerHTML =
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">' +
      '<circle cx="8" cy="6" r="1.6"/><circle cx="16" cy="6" r="1.6"/>' +
      '<circle cx="8" cy="12" r="1.6"/><circle cx="16" cy="12" r="1.6"/>' +
      '<circle cx="8" cy="18" r="1.6"/><circle cx="16" cy="18" r="1.6"/>' +
      '</svg>';
    return handle;
  }

  /**
   * Pointer-based drag-to-reorder for the edit-stop list. The return-home row
   * (last stop, tied to the trip end date) is never draggable and always stays last.
   *
   * @param {HTMLElement} listEl - container of `.trip-stop-card` rows.
   * @param {Object} [options]
   * @param {Function} [options.onReorder] - called after a drop reorders the DOM.
   */
  function makeSortable(listEl, options) {
    if (!listEl || listEl._sortableBound) return;
    listEl._sortableBound = true;
    options = options || {};
    var onReorder = typeof options.onReorder === 'function' ? options.onReorder : null;

    function cards() {
      return Array.prototype.slice.call(listEl.querySelectorAll('.trip-stop-card'));
    }

    var drag = null;

    function onPointerDown(e) {
      var handle = e.target.closest('.trip-stop-drag-handle');
      if (!handle || handle.classList.contains('trip-stop-drag-handle--spacer')) return;
      var row = handle.closest('.trip-stop-card');
      if (!row || isReturnHomeRow(row)) return;
      e.preventDefault();

      var rect = row.getBoundingClientRect();
      var placeholder = document.createElement('div');
      placeholder.className = 'trip-stop-card trip-stop-card--placeholder';
      placeholder.style.height = rect.height + 'px';
      row.parentNode.insertBefore(placeholder, row.nextSibling);

      drag = {
        pointerId: e.pointerId,
        row: row,
        placeholder: placeholder,
        offsetY: e.clientY - rect.top
      };

      row.classList.add('trip-stop-card--dragging');
      row.style.width = rect.width + 'px';
      row.style.left = rect.left + 'px';
      row.style.top = rect.top + 'px';

      document.addEventListener('pointermove', onPointerMove);
      document.addEventListener('pointerup', onPointerUp);
      document.addEventListener('pointercancel', onPointerUp);
    }

    function onPointerMove(e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      drag.row.style.top = (e.clientY - drag.offsetY) + 'px';

      var droppable = cards().filter(function (c) {
        return c !== drag.row && c !== drag.placeholder && !isReturnHomeRow(c);
      });

      var insertBeforeEl = null;
      for (var i = 0; i < droppable.length; i++) {
        var r = droppable[i].getBoundingClientRect();
        var mid = r.top + r.height / 2;
        if (e.clientY < mid) {
          insertBeforeEl = droppable[i];
          break;
        }
      }
      if (!insertBeforeEl) {
        var homeRow = cards().filter(isReturnHomeRow)[0];
        insertBeforeEl = homeRow || null;
      }
      if (insertBeforeEl) {
        insertBeforeEl.parentNode.insertBefore(drag.placeholder, insertBeforeEl);
      } else {
        listEl.appendChild(drag.placeholder);
      }
    }

    function onPointerUp(e) {
      if (!drag || e.pointerId !== drag.pointerId) return;
      var row = drag.row;
      var placeholder = drag.placeholder;
      placeholder.parentNode.insertBefore(row, placeholder);
      placeholder.remove();

      row.classList.remove('trip-stop-card--dragging');
      row.style.width = '';
      row.style.left = '';
      row.style.top = '';

      document.removeEventListener('pointermove', onPointerMove);
      document.removeEventListener('pointerup', onPointerUp);
      document.removeEventListener('pointercancel', onPointerUp);
      drag = null;

      if (onReorder) onReorder(listEl);
    }

    listEl.addEventListener('pointerdown', onPointerDown);
  }

  global.TripStopReorder = {
    isReturnHomeRow: isReturnHomeRow,
    buildDragHandle: buildDragHandle,
    makeSortable: makeSortable
  };
})(window);
