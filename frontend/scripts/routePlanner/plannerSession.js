(function (global) {
  var SESSION_KEY = 'planner_generation_session_v1'; var ENDPOINTS = {
    visited: '/generate_travel_plans/visited',
    unvisited: '/generate_travel_plans/unvisited',
    random: '/generate_travel_plans/random'
  };

  function apiBase() {
    return typeof global.API_BASE_URL === 'string' ? global.API_BASE_URL : '';
  }

  function isPlannerPage() {
    return /\/trips\/new\/?$/i.test(global.location.pathname || '');
  }

  function plannerPageUrl() {
    return '/trips/new';
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

  function localizeDetail(detail) {
    if (detail == null || detail === '') return detail;
    var s = String(detail);
    if (/add at least one place/i.test(s) || /travel log/i.test(s)) {
      return t(
        'planNewTrip.manualPlacesRequired',
        'Add at least one place in the field above, or turn on using your travel log from the database.'
      );
    }
    if (/end date must be after/i.test(s)) {
      return t('planNewTrip.endDateAfterStart', 'End date must be after start date.');
    }
    return detail;
  }

  function isActiveGenerationSession(session, expectedId) {
    if (!session || session.status !== 'generating') return false;
    if (session.generationId != null && session.generationId !== expectedId) return false;
    return true;
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
    // Land on the results block at the bottom of the planner page.
    viewBtn.href = plannerPageUrl() + '#resultsContainer';
    viewBtn.textContent = t('planNewTrip.viewPlan', 'View plan');
    viewBtn.addEventListener('click', function () {
      clearReadyAttention();
    });

    var dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.className = 'btn-add btn-add-outline';
    dismissBtn.textContent = t('planNewTrip.dismissNotification', 'Dismiss');
    dismissBtn.addEventListener('click', function () {
      clearReadyAttention();
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
    var generationId = session.generationId || Date.now();

    if (!isActiveGenerationSession(load(), generationId)) return;

    var abortController = typeof AbortController !== 'undefined' ? new AbortController() : null;
    global.__plannerBackgroundAbort = abortController;

    global.__plannerGenerationRunning = true;
    try {
      var fetchOpts = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(session.requestBody)
      };
      if (abortController) fetchOpts.signal = abortController.signal;

      var response = await fetch(apiBase() + ENDPOINTS[planType], fetchOpts);

      if (!isActiveGenerationSession(load(), generationId)) return;

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

      if (!isActiveGenerationSession(load(), generationId)) return;

      var body = session.requestBody || {};
      data.userStartDate = body.startDate || (session.form && session.form.startDate) || null;
      data.userEndDate = body.endDate || (session.form && session.form.endDate) || null;
      data.userPeople = body.people || Number(session.form && session.form.people) || 1;
      data.userTripTitle = (session.form && session.form.tripTitle) || '';

      var latest = load();
      if (!isActiveGenerationSession(latest, generationId)) {
        return;
      }

      // User may have returned to the planner while this request finished
      if (isPlannerPage()) {
        save({
          status: 'ready',
          resultData: data,
          generationId: generationId,
          errorMessage: null,
          errorDetails: null,
          notifyPending: false
        });
        return;
      }

      save({
        status: 'ready',
        resultData: data,
        generationId: generationId,
        errorMessage: null,
        errorDetails: null,
        notifyPending: true
      });
      showReadyToast();
    } catch (err) {
      if (err && (err.name === 'AbortError' || err.code === 20)) {
        return;
      }
      console.error('Background trip generation failed:', err);
      var latestErr = load();
      if (!isActiveGenerationSession(latestErr, generationId)) {
        return;
      }
      save({
        status: 'error',
        resultData: null,
        generationId: generationId,
        errorMessage: t('planNewTrip.generateFailed', 'Failed to generate trip. Please try again.'),
        errorDetails: localizeDetail((err && err.message) || String(err)),
        notifyPending: false
      });
    } finally {
      if (global.__plannerBackgroundAbort === abortController) {
        global.__plannerBackgroundAbort = null;
      }
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
