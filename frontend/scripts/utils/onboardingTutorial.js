(function () {
  if (window.__onboardingTutorialInit) return;
  window.__onboardingTutorialInit = true;

  var PENDING_KEY = 'pending_tutorial';
  var DONE_KEY = 'tutorial_completed';
  var STEP_KEY = 'tutorial_step';
  var LANG_READY_KEY = 'tutorial_language_ready';
  var PAD = 8;
  var FADE_MS = 220;
  var HOLE_MS = 320;

  var tour = null;
  var languagePrompt = null;

  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      var value = window.i18n.t(key);
      if (value && value !== key) return value;
    }
    return fallback;
  }

  function stepDefs() {
    return [
      {
        title: t('tutorial.welcomeTitle', 'Welcome to TravelApp'),
        body: t(
          'tutorial.welcomeBody',
          'TravelApp is your personal travel diary and automatic trip planner for Europe. You log places you have already visited and set a few preferences — then the app plans the trip for you (it is not a collaborative planner you build stop by stop).\n\nThis tour walks through the main screens step by step. You can skip anytime if you prefer to explore on your own.'
        ),
        page: /main_page\.html/,
        goto: '/pages/main_page.html',
        selectors: [],
        mode: 'next',
      },
      {
        title: t('tutorial.homeLogTitle', 'Your travel log'),
        body: t(
          'tutorial.homeLogBody',
          'Home is your dashboard. Recent visited places appear as cards so you can reopen notes and photos quickly.\n\nFurther down, the Europe chart shows which countries you have already visited. It updates automatically as you add more places, giving you a clear picture of your coverage.'
        ),
        page: /main_page\.html/,
        goto: '/pages/main_page.html',
        selectors: ['#mainTravelLogs', '.main-page-panel', '.main-page-home-content-inner'],
        mode: 'next',
      },
      {
        title: t('tutorial.addPlaceTitle', 'Add a visited place'),
        body: t(
          'tutorial.addPlaceBody',
          'Start by logging cities and towns you have already been to. Each saved place feeds your visited list, the Europe chart, the map, and the trip planner.\n\nClick the highlighted Add button to open the form and create your first entry.'
        ),
        page: /main_page\.html/,
        goto: '/pages/main_page.html',
        selectors: [
          '.main-page-home-content-header a.btn-add',
          'a.btn-add[href*="add_new_place"]',
          '[data-sidebar-id="addNewPlace"]',
        ],
        mode: 'click',
        fallbackGoto: '/pages/visitedPlaces/add_new_place.html',
      },
      {
        title: t('tutorial.addFormTitle', 'Fill in the place details'),
        body: t(
          'tutorial.addFormBody',
          'Enter the place name and choose the country from the suggestions so names stay consistent. Set a start date, and optionally an end date for multi-day stays.\n\nYou can rate the visit with stars, write a short description, and attach photos. After you save, the place shows up on Home, Visited Places, and the map.'
        ),
        page: /add_new_place\.html/,
        goto: '/pages/visitedPlaces/add_new_place.html',
        selectors: ['#addPlaceForm', '.add-place-card'],
        mode: 'next',
      },
      {
        title: t('tutorial.visitedTitle', 'Browse visited places'),
        body: t(
          'tutorial.visitedBody',
          'Visited Places is the full list of everywhere you have logged, usually newest first.\n\nOpen a card to read details, notes, and photos. Use the pencil icon to edit name, country, dates, rating, description, or photos — or delete a place you no longer need.'
        ),
        page: /visited_places\.html/,
        goto: '/pages/visitedPlaces/visited_places.html',
        selectors: ['.visited-places-header-actions', '#placeCards', '.visited-places-page'],
        mode: 'next',
      },
      {
        title: t('tutorial.mapTitle', 'Map view'),
        body: t(
          'tutorial.mapBody',
          'Map View plots every logged stop on a geographic map so you can see clusters, routes, and gaps at a glance.\n\nUse it when deciding where to travel next, or to revisit a region you already know well.'
        ),
        page: /visited_places\.html|places_map_view\.html/,
        goto: '/pages/visitedPlaces/visited_places.html',
        selectors: ['a.btn-trip[href*="places_map_view"]', 'a[href*="places_map_view"]'],
        mode: 'next',
      },
      {
        title: t('tutorial.planTitle', 'Plan a new trip'),
        body: t(
          'tutorial.planBody',
          'When you want a new itinerary, open Plan New Trip from the sidebar (or an Add button that links to the planner).\n\nImportant: the app plans the trip for you. You choose the mode and constraints; it generates the full day-by-day route with transport and activities — you do not assemble the itinerary together with the app.'
        ),
        page: /^(?!.*plan_new_trip\.html).*$/,
        goto: null,
        selectors: ['[data-sidebar-id="planNewTrip"]', 'a.btn-add[href*="plan_new_trip"]'],
        mode: 'click',
        fallbackGoto: '/pages/routePlanner/plan_new_trip.html',
      },
      {
        title: t('tutorial.modesTitle', 'Choose a planning mode'),
        body: t(
          'tutorial.modesBody',
          'First choose how destinations should be selected:\n\n• Visited — build a trip around places you already logged.\n• Unvisited — discover new cities while avoiding ones you already visited.\n• Random — let the app invent a surprise itinerary.\n\nPick the mode that matches your goal, then continue with the form below.'
        ),
        page: /plan_new_trip\.html/,
        goto: '/pages/routePlanner/plan_new_trip.html',
        selectors: ['#planTypeOptions', '.route-planner-options'],
        mode: 'next',
      },
      {
        title: t('tutorial.formTitle', 'Set trip details'),
        body: t(
          'tutorial.formBody',
          'Set your starting city, trip dates, number of travelers, and preferred transport (for example train and bus, or options that include flights). Optional notes help tailor the result.\n\nThen generate the trip: the app creates the complete plan for you. Review what it produced, save it to Planned Trips, and edit later if needed.'
        ),
        page: /plan_new_trip\.html/,
        goto: '/pages/routePlanner/plan_new_trip.html',
        selectors: ['#tripPlanForm', '.add-place-card'],
        mode: 'next',
      },
      {
        title: t('tutorial.plannedTitle', 'Planned trips & sharing'),
        body: t(
          'tutorial.plannedBody',
          'Saved itineraries live under Planned Trips. Open a trip to review stops, adjust details, follow booking links, and keep track of what you have arranged.\n\nYou can share a trip with a public link or invite another TravelApp user. Incoming invitations appear in the share inbox on this page.'
        ),
        page: /planned_trips\.html/,
        goto: '/pages/routePlanner/planned_trips.html',
        selectors: ['#tripCards', '#shareInboxSection', '.main-page-home-content-inner'],
        mode: 'next',
      },
      {
        title: t('tutorial.profileTitle', 'Profile & settings'),
        body: t(
          'tutorial.profileBody',
          'Your profile menu is in the top bar for account-related actions.\n\nIn Settings you can switch light, dark, or auto theme, change the interface language (English, Hungarian, or German), and choose which AI assistant should generate your trip plans.'
        ),
        page: /.*/,
        selectors: ['.main-header-profile', '[data-sidebar-id="settings"]'],
        mode: 'next',
      },
      {
        title: t('tutorial.doneTitle', 'You are ready'),
        body: t(
          'tutorial.doneBody',
          'That is the core loop: log places you visit → browse them on the list and map → let the app plan a trip for you → save and share the result.\n\nAdd a few real places when you can — automatic planning and the Europe chart become much more useful with your own history. Happy travels!'
        ),
        page: /.*/,
        selectors: [],
        mode: 'finish',
      },
    ];
  }

  function totalSteps() {
    return stepDefs().length;
  }

  function getStep() {
    var n = parseInt(localStorage.getItem(STEP_KEY) || '1', 10);
    if (isNaN(n) || n < 1) return 1;
    var max = totalSteps();
    if (n > max) return max;
    return n;
  }

  function setStep(n) {
    localStorage.setItem(STEP_KEY, String(n));
  }

  function markDone() {
    localStorage.setItem(DONE_KEY, '1');
    localStorage.removeItem(PENDING_KEY);
    localStorage.removeItem(STEP_KEY);
    localStorage.removeItem(LANG_READY_KEY);
  }

  function needsLanguagePrompt() {
    if (localStorage.getItem(LANG_READY_KEY) === '1') return false;
    return getStep() <= 1;
  }

  function currentLanguage() {
    if (window.i18n && typeof window.i18n.getLanguage === 'function') {
      return window.i18n.getLanguage();
    }
    return localStorage.getItem('language') || 'en';
  }

  function applyLanguage(locale) {
    if (window.i18n && typeof window.i18n.setLanguage === 'function') {
      window.i18n.setLanguage(locale);
      if (typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage();
      }
      return;
    }
    localStorage.setItem('language', locale);
  }

  function destroyLanguagePrompt() {
    if (!languagePrompt) return;
    document.body.classList.remove('tutorial-tour-active');
    if (languagePrompt.root && languagePrompt.root.parentNode) {
      languagePrompt.root.parentNode.removeChild(languagePrompt.root);
    }
    languagePrompt = null;
  }

  function showLanguagePrompt() {
    if (languagePrompt || tour) return;

    var root = document.createElement('div');
    root.className = 'tutorial-tour-root tutorial-lang-prompt-root';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'tutorial-lang-title');

    var backdrop = document.createElement('div');
    backdrop.className = 'tutorial-tour-backdrop';

    var card = document.createElement('div');
    card.className = 'tutorial-lang-prompt';

    var title = document.createElement('h2');
    title.id = 'tutorial-lang-title';
    title.className = 'tutorial-lang-prompt-title';

    var message = document.createElement('p');
    message.className = 'tutorial-lang-prompt-message';

    var choices = document.createElement('div');
    choices.className = 'tutorial-lang-choices';
    choices.setAttribute('role', 'radiogroup');
    choices.setAttribute('aria-labelledby', 'tutorial-lang-title');

    var langs = [
      { code: 'en', label: 'English' },
      { code: 'hu', label: 'Magyar' },
      { code: 'de', label: 'Deutsch' }
    ];
    var selected = currentLanguage();
    if (selected !== 'en' && selected !== 'hu' && selected !== 'de') selected = 'en';

    function refreshCopy() {
      title.textContent = t('tutorial.chooseLanguageTitle', 'Choose your language');
      message.textContent = t(
        'tutorial.chooseLanguageBody',
        'Pick the language for the app and this tour. You can change it later in Settings.'
      );
      startBtn.textContent = t('tutorial.startTour', 'Start tour');
      skipBtn.textContent = t('tutorial.skip', 'Skip tour');
    }

    langs.forEach(function (lang) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className =
        'tutorial-lang-choice' + (lang.code === selected ? ' is-selected' : '');
      btn.setAttribute('role', 'radio');
      btn.setAttribute('aria-checked', lang.code === selected ? 'true' : 'false');
      btn.setAttribute('data-lang', lang.code);
      btn.textContent = lang.label;
      btn.addEventListener('click', function () {
        selected = lang.code;
        applyLanguage(selected);
        choices.querySelectorAll('.tutorial-lang-choice').forEach(function (el) {
          var on = el.getAttribute('data-lang') === selected;
          el.classList.toggle('is-selected', on);
          el.setAttribute('aria-checked', on ? 'true' : 'false');
        });
        refreshCopy();
      });
      choices.appendChild(btn);
    });

    var actions = document.createElement('div');
    actions.className = 'tutorial-lang-prompt-actions';

    var skipBtn = document.createElement('button');
    skipBtn.type = 'button';
    skipBtn.className = 'custom-modal-btn custom-modal-btn-secondary';

    var startBtn = document.createElement('button');
    startBtn.type = 'button';
    startBtn.className = 'custom-modal-btn custom-modal-btn-primary';

    actions.appendChild(skipBtn);
    actions.appendChild(startBtn);

    card.appendChild(title);
    card.appendChild(message);
    card.appendChild(choices);
    card.appendChild(actions);

    root.appendChild(backdrop);
    root.appendChild(card);
    document.body.appendChild(root);
    document.body.classList.add('tutorial-tour-active');

    languagePrompt = { root: root };

    refreshCopy();
    applyLanguage(selected);

    skipBtn.addEventListener('click', function (e) {
      e.preventDefault();
      applyLanguage(selected);
      localStorage.setItem(LANG_READY_KEY, '1');
      markDone();
      destroyLanguagePrompt();
    });

    startBtn.addEventListener('click', function (e) {
      e.preventDefault();
      applyLanguage(selected);
      localStorage.setItem(LANG_READY_KEY, '1');
      setStep(1);
      destroyLanguagePrompt();
      showTour();
    });

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        root.classList.add('is-visible');
      });
    });
  }

  function forceFromQuery() {
    try {
      var params = new URLSearchParams(location.search || '');
      if (params.get('tutorial') !== '1') return;
      localStorage.removeItem(DONE_KEY);
      localStorage.removeItem(LANG_READY_KEY);
      localStorage.setItem(PENDING_KEY, '1');
      localStorage.setItem(STEP_KEY, '1');
      params.delete('tutorial');
      var next =
        location.pathname + (params.toString() ? '?' + params.toString() : '') + (location.hash || '');
      window.history.replaceState({}, '', next);
    } catch (e) {
      /* ignore */
    }
  }

  var queryForced = false;
  function isActive() {
    if (!queryForced) {
      forceFromQuery();
      queryForced = true;
    }
    if (!localStorage.getItem('user_id') || !localStorage.getItem('access_token')) return false;
    var pending = String(localStorage.getItem(PENDING_KEY) || '').trim();
    if (pending !== '1') return false;
    if (localStorage.getItem(DONE_KEY) === '1') localStorage.removeItem(DONE_KEY);
    if (!localStorage.getItem(STEP_KEY)) setStep(1);
    return true;
  }

  function findTarget(selectors) {
    if (!selectors || !selectors.length) return null;
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el) return el;
    }
    return null;
  }

  function openDrawerIfNeeded(target) {
    if (!target || !target.closest || !target.closest('#app-sidebar')) return;
    if (window.matchMedia && window.matchMedia('(min-width: 769px)').matches) return;
    document.body.classList.add('nav-drawer-open');
    var toggle = document.getElementById('app-menu-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
  }

  function elevate(el) {
    if (!el) return;
    var node = el;
    while (node && node !== document.body) {
      node.classList.add('tutorial-elevated');
      try {
        var pos = window.getComputedStyle(node).position;
        if (pos === 'static') node.classList.add('tutorial-elevated-relative');
      } catch (e) {
        node.classList.add('tutorial-elevated-relative');
      }
      node = node.parentElement;
    }
    el.classList.add('tutorial-target-active');
  }

  function clearElevate() {
    var nodes = document.querySelectorAll(
      '.tutorial-elevated, .tutorial-elevated-relative, .tutorial-target-active'
    );
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].classList.remove(
        'tutorial-elevated',
        'tutorial-elevated-relative',
        'tutorial-target-active'
      );
    }
  }

  function advanceTo(stepNum) {
    var next = stepNum + 1;
    if (next > totalSteps()) {
      markDone();
      return null;
    }
    setStep(next);
    localStorage.setItem(PENDING_KEY, '1');
    return next;
  }

  function ensureCorrectPage(step) {
    if (!step.page || step.page.test(location.pathname || '')) return true;
    if (step.goto) {
      window.location.href = step.goto;
      return false;
    }
    return true;
  }

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function wait(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, prefersReducedMotion() ? 0 : ms);
    });
  }

  function createTourShell() {
    var root = document.createElement('div');
    root.className = 'tutorial-tour-root';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');

    var backdrop = document.createElement('div');
    backdrop.className = 'tutorial-tour-backdrop';

    var hole = document.createElement('div');
    hole.className = 'tutorial-tour-hole is-hidden';

    var tip = document.createElement('div');
    tip.className = 'tutorial-tour-tip tutorial-tour-tip--dock';

    var meta = document.createElement('div');
    meta.className = 'tutorial-tour-meta';

    var progress = document.createElement('div');
    progress.className = 'tutorial-progress';
    progress.setAttribute('aria-hidden', 'true');

    var counter = document.createElement('span');
    counter.className = 'tutorial-tour-counter';

    meta.appendChild(progress);
    meta.appendChild(counter);

    var bodyWrap = document.createElement('div');
    bodyWrap.className = 'tutorial-tour-body';

    var title = document.createElement('h3');
    title.className = 'tutorial-tour-title';

    var message = document.createElement('p');
    message.className = 'tutorial-tour-message';

    var hint = document.createElement('p');
    hint.className = 'tutorial-tour-hint';

    bodyWrap.appendChild(title);
    bodyWrap.appendChild(message);
    bodyWrap.appendChild(hint);

    var actions = document.createElement('div');
    actions.className = 'tutorial-tour-actions';

    var skipBtn = document.createElement('button');
    skipBtn.type = 'button';
    skipBtn.className = 'custom-modal-btn custom-modal-btn-secondary';
    skipBtn.textContent = t('tutorial.skip', 'Skip tour');

    var primaryBtn = document.createElement('button');
    primaryBtn.type = 'button';
    primaryBtn.className = 'custom-modal-btn custom-modal-btn-primary';

    actions.appendChild(skipBtn);
    actions.appendChild(primaryBtn);

    tip.appendChild(meta);
    tip.appendChild(bodyWrap);
    tip.appendChild(actions);

    root.appendChild(backdrop);
    root.appendChild(hole);
    document.body.appendChild(root);
    document.body.appendChild(tip);
    document.body.classList.add('tutorial-tour-active');

    return {
      root: root,
      backdrop: backdrop,
      hole: hole,
      tip: tip,
      progress: progress,
      counter: counter,
      title: title,
      message: message,
      hint: hint,
      skipBtn: skipBtn,
      primaryBtn: primaryBtn,
      target: null,
      stepNum: 0,
      mode: 'next',
      transitioning: false,
      onTargetClick: null,
      onKey: null,
      onResize: null,
    };
  }

  function layoutHole(ui) {
    if (!ui.target || ui.hole.classList.contains('is-hidden')) return;
    var r = ui.target.getBoundingClientRect();
    ui.hole.style.top = Math.max(0, r.top - PAD) + 'px';
    ui.hole.style.left = Math.max(0, r.left - PAD) + 'px';
    ui.hole.style.width = Math.max(0, r.width + PAD * 2) + 'px';
    ui.hole.style.height = Math.max(0, r.height + PAD * 2) + 'px';
  }

  function bindTarget(ui, target, mode) {
    if (ui.target && ui.onTargetClick) {
      ui.target.removeEventListener('click', ui.onTargetClick, true);
    }
    ui.target = target;
    ui.onTargetClick = null;
    if (mode === 'click' && target) {
      ui.onTargetClick = function () {
        if (ui.transitioning) return;
        var next = advanceTo(ui.stepNum);
        var href = target.getAttribute && target.getAttribute('href');
        if (!href) {
          transitionToStep(next);
        } else {
          ui.tip.classList.add('is-leaving');
          ui.root.classList.add('is-leaving');
        }
      };
      target.addEventListener('click', ui.onTargetClick, true);
    }
  }

  function applyStepContent(ui, stepNum, step, target, mode, animateIn) {
    var list = stepDefs();
    ui.stepNum = stepNum;
    ui.mode = mode;

    ui.progress.innerHTML = '';
    for (var i = 0; i < list.length; i++) {
      var dot = document.createElement('span');
      dot.className = 'tutorial-progress-dot' + (i === stepNum - 1 ? ' is-active' : '');
      ui.progress.appendChild(dot);
    }
    ui.counter.textContent = stepNum + ' / ' + list.length;
    ui.title.textContent = step.title;
    ui.message.textContent = step.body;

    if (mode === 'click' && target) {
      ui.hint.hidden = false;
      ui.hint.textContent = t('tutorial.hintClick', 'Click the highlighted control to continue.');
    } else if (mode === 'finish') {
      ui.hint.hidden = true;
      ui.hint.textContent = '';
    } else {
      ui.hint.hidden = false;
      ui.hint.textContent = t('tutorial.hintNext', 'Press Next when you are ready.');
    }

    ui.primaryBtn.textContent =
      mode === 'finish' ? t('tutorial.finish', 'Get started') : t('tutorial.next', 'Next');

    clearElevate();
    bindTarget(ui, target, mode);
    openDrawerIfNeeded(target);
    if (target) {
      elevate(target);
      ui.hole.classList.remove('is-hidden');
      try {
        target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
      } catch (err) {
        /* ignore */
      }
      requestAnimationFrame(function () {
        layoutHole(ui);
        setTimeout(function () {
          layoutHole(ui);
        }, HOLE_MS);
      });
    } else {
      ui.hole.classList.add('is-hidden');
    }

    if (animateIn) {
      ui.tip.classList.remove('is-leaving');
      ui.tip.classList.add('is-entering');
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          ui.tip.classList.remove('is-entering');
        });
      });
    }
  }

  function destroyTour(ui) {
    if (!ui) return;
    window.removeEventListener('resize', ui.onResize);
    window.removeEventListener('scroll', ui.onResize, true);
    document.removeEventListener('keydown', ui.onKey, true);
    if (ui.target && ui.onTargetClick) {
      ui.target.removeEventListener('click', ui.onTargetClick, true);
    }
    clearElevate();
    document.body.classList.remove('tutorial-tour-active');
    if (ui.root.parentNode) ui.root.parentNode.removeChild(ui.root);
    if (ui.tip.parentNode) ui.tip.parentNode.removeChild(ui.tip);
    if (tour === ui) tour = null;
  }

  async function fadeOutTour(ui) {
    if (!ui) return;
    ui.tip.classList.add('is-leaving');
    ui.root.classList.add('is-leaving');
    await wait(FADE_MS);
  }

  async function finishTour(ui) {
    if (!ui || ui.transitioning) return;
    ui.transitioning = true;
    markDone();
    await fadeOutTour(ui);
    destroyTour(ui);
  }

  async function transitionToStep(nextStepNum) {
    var ui = tour;
    if (!ui || ui.transitioning) return;
    if (nextStepNum === null) {
      await finishTour(ui);
      return;
    }

    ui.transitioning = true;
    var list = stepDefs();
    var nextStep = list[nextStepNum - 1];
    if (!nextStep) {
      markDone();
      await fadeOutTour(ui);
      destroyTour(ui);
      return;
    }

    var needsNav =
      nextStep.goto && nextStep.page && !nextStep.page.test(location.pathname || '');

    ui.tip.classList.add('is-leaving');
    await wait(FADE_MS);

    if (needsNav) {
      ui.root.classList.add('is-leaving');
      await wait(120);
      window.location.href = nextStep.goto;
      return;
    }

    clearElevate();
    if (ui.target && ui.onTargetClick) {
      ui.target.removeEventListener('click', ui.onTargetClick, true);
      ui.target = null;
      ui.onTargetClick = null;
    }

    var target = findTarget(nextStep.selectors);
    openDrawerIfNeeded(target);
    if (!target) target = findTarget(nextStep.selectors);
    var mode = nextStep.mode;

    applyStepContent(ui, nextStepNum, nextStep, target, mode, true);
    ui.transitioning = false;
  }

  function showTour() {
    if (tour) return;
    if (!isActive()) return;

    var stepNum = getStep();
    var list = stepDefs();
    var step = list[stepNum - 1];
    if (!step) {
      markDone();
      return;
    }
    if (!ensureCorrectPage(step)) return;

    var target = findTarget(step.selectors);
    openDrawerIfNeeded(target);
    if (!target) target = findTarget(step.selectors);
    var mode = step.mode;

    var ui = createTourShell();
    tour = ui;

    ui.onResize = function () {
      layoutHole(ui);
    };
    ui.onKey = function (e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        finishTour(ui);
      }
    };

    ui.skipBtn.addEventListener('click', function (e) {
      e.preventDefault();
      finishTour(ui);
    });

    ui.primaryBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (ui.transitioning) return;

      if (ui.mode === 'finish') {
        finishTour(ui);
        return;
      }

      if (ui.mode === 'click') {
        var href =
          (ui.target && ui.target.getAttribute && ui.target.getAttribute('href')) ||
          stepDefs()[ui.stepNum - 1].fallbackGoto ||
          stepDefs()[ui.stepNum - 1].goto;
        var next = advanceTo(ui.stepNum);
        if (href) {
          ui.transitioning = true;
          ui.tip.classList.add('is-leaving');
          ui.root.classList.add('is-leaving');
          setTimeout(function () {
            window.location.href = href;
          }, FADE_MS);
          return;
        }
        transitionToStep(next);
        return;
      }

      var nextStep = advanceTo(ui.stepNum);
      transitionToStep(nextStep);
    });

    window.addEventListener('resize', ui.onResize);
    window.addEventListener('scroll', ui.onResize, true);
    document.addEventListener('keydown', ui.onKey, true);

    ui.root.classList.add('is-entering');
    ui.tip.classList.add('is-entering');
    applyStepContent(ui, stepNum, step, target, mode, false);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        ui.root.classList.remove('is-entering');
        ui.tip.classList.remove('is-entering');
      });
    });
  }

  function startWhenReady(attempt) {
    attempt = attempt || 0;
    var sidebar = document.getElementById('app-sidebar');
    var ready = !sidebar || sidebar.children.length > 0;
    if (!ready && attempt < 40) {
      setTimeout(function () {
        startWhenReady(attempt + 1);
      }, 50);
      return;
    }
    beginTutorialFlow();
  }

  function beginTutorialFlow() {
    if (!isActive()) return;
    if (needsLanguagePrompt()) {
      showLanguagePrompt();
      return;
    }
    showTour();
  }

  function boot() {
    try {
      startWhenReady(0);
    } catch (err) {
      console.error('[tutorial] boot failed', err);
    }
  }

  window.resetTravelTutorial = function () {
    localStorage.removeItem(DONE_KEY);
    localStorage.removeItem(LANG_READY_KEY);
    localStorage.setItem(PENDING_KEY, '1');
    localStorage.setItem(STEP_KEY, '1');
    if (tour) destroyTour(tour);
    destroyLanguagePrompt();
    var orphanRoot = document.querySelector('.tutorial-tour-root');
    if (orphanRoot) orphanRoot.remove();
    var orphanTip = document.querySelector('.tutorial-tour-tip');
    if (orphanTip) orphanTip.remove();
    document.body.classList.remove('tutorial-tour-active');
    clearElevate();
    if (!/main_page\.html/.test(location.pathname || '')) {
      window.location.href = '/pages/main_page.html?tutorial=1';
      return;
    }
    beginTutorialFlow();
  };

  window.startTravelTutorial = beginTutorialFlow;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    setTimeout(boot, 0);
  }
})();
