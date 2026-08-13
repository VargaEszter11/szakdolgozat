(function (global) {
  var SESSION_KEY = 'planner_generation_session_v1';
  var ENDPOINTS = {
    visited: '/generate_travel_plans/visited',
    unvisited: '/generate_travel_plans/unvisited',
    random: '/generate_travel_plans/random'
  };

  function apiBase() {
    return typeof global.API_BASE_URL === 'string' ? global.API_BASE_URL : '';
  }

  function isPlannerPage() {
    return /plan_new_trip\.html$/i.test(global.location.pathname || '');
  }

  function plannerPageUrl() {
    if (global.appShell && typeof global.appShell.pagePrefix === 'string') {
      return global.appShell.pagePrefix + 'routePlanner/plan_new_trip.html';
    }
    if (/\/routePlanner\//i.test(global.location.pathname || '')) {
      return 'plan_new_trip.html';
    }
    if (/\/(visitedPlaces|settings|loginRegister|admin)\//i.test(global.location.pathname || '')) {
      return '../routePlanner/plan_new_trip.html';
    }
    return 'routePlanner/plan_new_trip.html';
  }

  function load() {
    try {
      var raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (err) {
      return null;
    }
  }

  function save(patch) {
    var current = load() || {};
    var next = Object.assign({}, current, patch || {}, { updatedAt: Date.now() });
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
    } catch (err) {
      console.warn('Could not persist planner session:', err);
    }
    return next;
  }

  function clear() {
    try {
      sessionStorage.removeItem(SESSION_KEY);
    } catch (err) { /* ignore */ }
    dismissToast();
  }

  function t(key, fallback) {
    if (global.i18n && typeof global.i18n.t === 'function') {
      var value = global.i18n.t(key);
      if (value && String(value).indexOf('planNewTrip.') !== 0) return value;
    }
    return fallback;
  }

  function dismissToast() {
    var el = document.getElementById('plannerReadyToast');
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function clearReadyAttention() {
    dismissToast();
    save({ notifyPending: false });
  }

  function showReadyToast() {
    if (isPlannerPage()) {
      clearReadyAttention();
      return;
    }
    dismissToast();

    var toast = document.createElement('div');
    toast.id = 'plannerReadyToast';
    toast.className = 'planner-ready-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');

    var title = document.createElement('p');
    title.className = 'planner-ready-toast-title';
    title.textContent = t('planNewTrip.readyNotification', 'Your trip plan is ready');

    var actions = document.createElement('div');
    actions.className = 'planner-ready-toast-actions';

    var viewBtn = document.createElement('a');
    viewBtn.className = 'btn-add';
    viewBtn.href = plannerPageUrl();
    viewBtn.textContent = t('planNewTrip.viewPlan', 'View plan');
    viewBtn.addEventListener('click', function () {
      clearReadyAttention();
    });

    var dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.className = 'btn-add btn-add-outline';
    dismissBtn.textContent = t('planNewTrip.dismissNotification', 'Dismiss');
    dismissBtn.addEventListener('click', function () {
      dismissToast();
    });

    actions.appendChild(viewBtn);
    actions.appendChild(dismissBtn);
    toast.appendChild(title);
    toast.appendChild(actions);
    document.body.appendChild(toast);
  }

  async function resumeGenerationInBackground() {
    if (isPlannerPage()) return;
    if (global.__plannerGenerationRunning) return;

    var session = load();
    if (!session) return;

    if (session.status === 'ready' && session.notifyPending && session.resultData) {
      showReadyToast();
      return;
    }

    if (session.status !== 'generating' || !session.requestBody) return;

    var planType = session.selectedPlan || 'random';
    if (!ENDPOINTS[planType]) planType = 'random';

    global.__plannerGenerationRunning = true;
    try {
      var response = await fetch(apiBase() + ENDPOINTS[planType], {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(session.requestBody)
      });

      if (!response.ok) {
        var detail = 'HTTP ' + response.status;
        try {
          var errBody = await response.json();
          if (errBody && errBody.detail) {
            detail = typeof errBody.detail === 'string'
              ? errBody.detail
              : JSON.stringify(errBody.detail);
          }
        } catch (_) { /* keep */ }
        throw new Error(detail);
      }

      var data = await response.json();
      var body = session.requestBody || {};
      data.userStartDate = body.startDate || (session.form && session.form.startDate) || null;
      data.userEndDate = body.endDate || (session.form && session.form.endDate) || null;
      data.userPeople = body.people || Number(session.form && session.form.people) || 1;

      // User may have returned to the planner while this request finished.
      if (isPlannerPage()) {
        save({
          status: 'ready',
          resultData: data,
          errorMessage: null,
          errorDetails: null,
          notifyPending: false
        });
        return;
      }

      save({
        status: 'ready',
        resultData: data,
        errorMessage: null,
        errorDetails: null,
        notifyPending: true
      });
      showReadyToast();
    } catch (err) {
      console.error('Background trip generation failed:', err);
      save({
        status: 'error',
        resultData: null,
        errorMessage: 'Failed to generate trip. Please try again.',
        errorDetails: (err && err.message) || String(err),
        notifyPending: false
      });
    } finally {
      global.__plannerGenerationRunning = false;
    }
  }

  global.PlannerSession = {
    SESSION_KEY: SESSION_KEY,
    ENDPOINTS: ENDPOINTS,
    load: load,
    save: save,
    clear: clear,
    isPlannerPage: isPlannerPage,
    plannerPageUrl: plannerPageUrl,
    showReadyToast: showReadyToast,
    clearReadyAttention: clearReadyAttention,
    resumeGenerationInBackground: resumeGenerationInBackground
  };

  function boot() {
    resumeGenerationInBackground();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
