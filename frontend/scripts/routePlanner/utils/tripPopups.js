(function (global) {
  'use strict';

  // Shared by the details/edit/share modals so opening one closes any other.
  function destroyAll() {
    document.querySelectorAll('.trip-details-modal-overlay').forEach(function (el) {
      var prevMap = el.querySelector('#tripDetailsMap');
      if (prevMap && global.TripMapHelper && typeof global.TripMapHelper.destroyTripMap === 'function') {
        global.TripMapHelper.destroyTripMap(prevMap);
      }
      el.remove();
    });
  }

  global.TripPopups = {
    destroyAll: destroyAll
  };
})(window);
