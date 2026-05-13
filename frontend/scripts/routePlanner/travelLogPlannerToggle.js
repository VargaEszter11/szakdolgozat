(function () {
  var CHECKBOX_ID = 'useTravelLogInPlanner';

  function apiBase() {
    return typeof window.API_BASE_URL === 'string' ? window.API_BASE_URL : '';
  }

  function getUserId() {
    return localStorage.getItem('user_id');
  }

  function syncCheckboxFromUser(user) {
    var cb = document.getElementById(CHECKBOX_ID);
    if (!cb || !user || typeof user.use_travel_log_in_planner !== 'boolean') return;
    cb.checked = user.use_travel_log_in_planner;
  }

  function persist(cb) {
    var uid = getUserId();
    if (!uid) return Promise.resolve();
    return fetch(apiBase() + '/api/users/' + encodeURIComponent(uid), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_travel_log_in_planner: cb.checked })
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var cb = document.getElementById(CHECKBOX_ID);
    if (!cb) return;

    var uid = getUserId();
    if (!uid) {
      cb.checked = true;
      return;
    }

    fetch(apiBase() + '/api/users/' + encodeURIComponent(uid))
      .then(function (res) {
        if (!res.ok) throw new Error('load user');
        return res.json();
      })
      .then(function (user) {
        syncCheckboxFromUser(user);
        if (typeof window.onTravelLogPlannerPrefLoaded === 'function') {
          window.onTravelLogPlannerPrefLoaded(user);
        }
      })
      .catch(function () {
        cb.checked = true;
      });

    cb.addEventListener('change', function () {
      var prev = !cb.checked;
      persist(cb)
        .then(function (res) {
          if (!res.ok) throw new Error('save');
        })
        .catch(function () {
          cb.checked = prev;
          var msg =
            window.i18n && window.i18n.t
              ? window.i18n.t('travelPlanner.saveFailed')
              : 'Could not save preference.';
          if (typeof window.showError === 'function') {
            window.showError(msg);
          } else {
            window.alert(msg);
          }
        });
      if (typeof window.onTravelLogPlannerPrefChanged === 'function') {
        window.onTravelLogPlannerPrefChanged(cb.checked);
      }
    });
  });
})();
