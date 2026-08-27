(function () {
  var CHECKBOX_ID = 'useTravelLogInPlanner';
  var STORAGE_KEY = 'useTravelLogInPlanner';

  function syncCheckboxFromStorage() {
    var cb = document.getElementById(CHECKBOX_ID);
    if (!cb) return;
    var saved = localStorage.getItem(STORAGE_KEY);
    cb.checked = saved == null ? true : saved === '1';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var cb = document.getElementById(CHECKBOX_ID);
    if (!cb) return;

    syncCheckboxFromStorage();

    // Defer so ES modules (planNewTrip.js) can register hooks first.
    setTimeout(function () {
      if (typeof window.onTravelLogPlannerPrefLoaded === 'function') {
        window.onTravelLogPlannerPrefLoaded(cb.checked);
      }
    }, 0);

    cb.addEventListener('change', function () {
      localStorage.setItem(STORAGE_KEY, cb.checked ? '1' : '0');
      if (typeof window.onTravelLogPlannerPrefChanged === 'function') {
        window.onTravelLogPlannerPrefChanged(cb.checked);
      }
    });
  });
})();
