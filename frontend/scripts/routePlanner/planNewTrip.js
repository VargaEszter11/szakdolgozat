import {
    displayResults,
    showError,
    planNewTripT,
    localizePlannerErrorDetail,
    createEmptyStopFeedback,
    syncStopFeedbackFromCards
} from './tripRenderer.js';

const API_BASE_URL = window.API_BASE_URL || '';

function plannerSessionApi() {
    return window.PlannerSession || null;
}

function loadPlannerSession() {
    return window.PlannerSession ? window.PlannerSession.load() : null;
}
function savePlannerSession(patch) {
    if (window.PlannerSession) return window.PlannerSession.save(patch);
}
function clearPlannerSession() {
    if (window.PlannerSession) window.PlannerSession.clear();
}

function clearPlannerResults() {
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    if (loadingState) loadingState.style.display = 'none';
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (tripResults) tripResults.innerHTML = '';
}

function resetPlannerFormFields() {
    const setEmpty = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = '';
        el.classList.remove('has-value');
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    };

    setEmpty('startingCity');
    setEmpty('preferences');
    setEmpty('placesList');
    setEmpty('tripTitle');

    const people = document.getElementById('people');
    if (people) {
        people.value = '1';
        people.classList.add('has-value');
        people.dispatchEvent(new Event('input', { bubbles: true }));
        people.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const transport = document.getElementById('preferredTransport');
    if (transport) {
        transport.value = 'allModes';
        transport.classList.add('has-value');
        transport.dispatchEvent(new Event('change', { bubbles: true }));
    }

    if (startDatePicker) startDatePicker.clear();
    else setEmpty('startDate');
    if (endDatePicker) {
        endDatePicker.set('minDate', null);
        endDatePicker.clear();
    } else {
        setEmpty('endDate');
    }

    document.querySelectorAll('.add-place-form .form-input').forEach((input) => {
        input.classList.toggle('has-value', !!String(input.value || '').trim());
    });
}

function resetPlannerUi() {
    if (activeGenerationAbort) {
        try { activeGenerationAbort.abort(); } catch (_) { }
        activeGenerationAbort = null;
    }
    if (window.__plannerBackgroundAbort) {
        try { window.__plannerBackgroundAbort.abort(); } catch (_) { }
        window.__plannerBackgroundAbort = null;
    }
    generationInFlight = false;
    window.__plannerGenerationRunning = false;
    clearPlannerSession();
    resetPlannerFormFields();
    clearPlannerResults();
    selectPlanType('random');
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) generateBtn.disabled = false;
}

const ENDPOINTS = {
    visited: '/generate_travel_plans/visited',
    unvisited: '/generate_travel_plans/unvisited',
    random: '/generate_travel_plans/random'
};

let selectedPlan = 'random';
let generationInFlight = false;
let activeGenerationAbort = null;

function useTravelLogFromDb() {
    const el = document.getElementById('useTravelLogInPlanner');
    return !el || el.checked;
}

function refreshPlannerDbHints() {
    const hint = document.querySelector('#placesGroup small.muted');
    if (!hint) return;
    const t = window.i18n ? window.i18n.t.bind(window.i18n) : (k) => k;
    const useDb = useTravelLogFromDb();
    if (selectedPlan === 'visited') {
        hint.textContent = useDb ? t('planNewTrip.placesHint') : t('planNewTrip.placesHintVisitedNoDb');
    } else if (selectedPlan === 'unvisited') {
        hint.textContent = useDb ? t('planNewTrip.placesHintUnvisited') : t('planNewTrip.placesHintUnvisitedNoDb');
    } else {
        hint.textContent = '';
    }
}

let homeCity = '';

function homeCityButtonLabel() {
    const t = window.i18n ? window.i18n.t.bind(window.i18n) : (k, f) => f;
    const key = homeCity ? 'planNewTrip.useHomeCity' : 'planNewTrip.setHomeCity';
    const fallback = homeCity ? 'Use my home city' : 'Set as my home city';
    return { key, text: t(key, fallback) };
}

function refreshHomeCityButton() {
    const btn = document.getElementById('useHomeCityBtn');
    if (!btn) return;
    const label = btn.querySelector('span');
    if (!label) return;
    const { key, text } = homeCityButtonLabel();
    label.setAttribute('data-i18n', key);
    label.textContent = text;
}

async function userHasSavedVisitedPlaces(userId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/users/${userId}/visited-places`);
        if (!res.ok) return null;
        const places = await res.json();
        return Array.isArray(places) && places.length > 0;
    } catch (err) {
        console.warn('Could not check saved visited places:', err);
        return null;
    }
}

async function saveHomeCity(userId, city) {
    const res = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ home_city: city })
    });
    if (!res.ok) throw new Error('save home city ' + res.status);
    return res.json();
}

async function loadHomeCity() {
    const userId = localStorage.getItem('user_id');
    const btn = document.getElementById('useHomeCityBtn');
    if (!userId || !btn) return;

    try {
        const res = await fetch(`${API_BASE_URL}/api/users/${userId}`);
        if (res.ok) {
            const user = await res.json();
            homeCity = (user.home_city || '').trim();
        }
    } catch (err) {
        console.warn('Could not load home city:', err);
    }

    btn.hidden = false;
    refreshHomeCityButton();

    btn.addEventListener('click', async () => {
        const input = document.getElementById('startingCity');
        if (!input) return;

        // Already have a home city saved: one click fills the field.
        if (homeCity) {
            input.value = homeCity;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            return;
        }

        // No home city yet: save whatever is currently typed as Starting
        // City, then immediately use it — same click both sets and uses it.
        const cityToSave = input.value.trim();
        if (!cityToSave) {
            input.focus();
            const tripResults = document.getElementById('tripResults');
            const resultsContainer = document.getElementById('resultsContainer');
            if (tripResults && resultsContainer) {
                showError(
                    planNewTripT('homeCityRequired', 'Type a starting city first, then click again to save it as your home city.'),
                    '',
                    tripResults,
                    resultsContainer
                );
            }
            return;
        }

        btn.disabled = true;
        try {
            const updated = await saveHomeCity(userId, cityToSave);
            homeCity = (updated.home_city || '').trim();
            refreshHomeCityButton();
        } catch (err) {
            console.warn('Could not save home city:', err);
            const tripResults = document.getElementById('tripResults');
            const resultsContainer = document.getElementById('resultsContainer');
            const msg = planNewTripT('homeCitySaveFailed', 'Could not save home city. Please try again.');
            if (tripResults && resultsContainer) {
                showError(msg, (err && err.message) || '', tripResults, resultsContainer);
            } else if (typeof window.showError === 'function') {
                window.showError(msg);
            }
        } finally {
            btn.disabled = false;
        }
    });
}

function patchStalePlannerSession(session) {
    if (!session || session.status !== 'generating' || !session.requestBody) {
        return session;
    }
    const formWantsDb = session.form?.useTravelLog !== false;
    const body = session.requestBody;
    if (!formWantsDb || body.userId != null) {
        return session;
    }
    const plan = session.selectedPlan;
    if (plan !== 'visited' && plan !== 'unvisited') {
        return session;
    }
    const uid = localStorage.getItem('user_id');
    const parsed = uid ? parseInt(uid, 10) : NaN;
    if (!Number.isFinite(parsed)) {
        return session;
    }
    body.userId = parsed;
    savePlannerSession({ requestBody: body });
    session.requestBody = body;
    return session;
}

function updatePlacesField() {
    const placesGroup = document.getElementById('placesGroup');
    if (!placesGroup) return;

    if (selectedPlan === 'random') {
        placesGroup.style.display = 'none';
        return;
    }

    placesGroup.style.display = '';

    const t = window.i18n ? window.i18n.t.bind(window.i18n) : (k) => k;
    const label = placesGroup.querySelector('.form-label');
    const input = placesGroup.querySelector('.form-input');

    if (selectedPlan === 'unvisited') {
        if (label) label.textContent = t('planNewTrip.placesLabelUnvisited');
    } else {
        if (label) label.textContent = t('planNewTrip.placesLabel');
    }

    if (input) input.placeholder = t('planNewTrip.placesPlaceholder');
    refreshPlannerDbHints();
}

function trackFilledInputs() {
    document.querySelectorAll('.add-place-form .form-input').forEach(input => {
        function toggle() {
            input.classList.toggle('has-value', !!input.value);
        }
        input.addEventListener('input', toggle);
        input.addEventListener('change', toggle);
        toggle();
    });
}

let startDatePicker = null;
let endDatePicker = null;

function initDatePickers() {
    if (typeof flatpickr === 'undefined') return;

    const LOCALE_MAP = { hu: 'hu', de: 'de' };
    const lang = localStorage.getItem('language') || 'en';
    const fpLocale = LOCALE_MAP[lang] || 'default';

    const opts = {
        dateFormat: 'Y-m-d',
        locale: fpLocale,
        disableMobile: true,
        onOpen: function (selectedDates, dateStr, instance) {
            const jumpTo = dateStr || (instance.input && instance.input.value) || '';
            if (jumpTo) instance.jumpToDate(jumpTo, false);
        }
    };

    endDatePicker = flatpickr('#endDate', opts);
    startDatePicker = flatpickr('#startDate', {
        ...opts,
        onChange: function (selectedDates, dateStr) {
            if (!dateStr || !endDatePicker) return;
            const minEnd = dayAfterIso(dateStr);
            if (minEnd) endDatePicker.set('minDate', minEnd);
            const endVal = endDatePicker.input.value || '';
            if (!endVal || endVal <= dateStr) {
                endDatePicker.setDate(minEnd, true);
            }
            endDatePicker.jumpToDate(minEnd || dateStr, true);
        }
    });

    syncLinkedDatePickers(
        startDatePicker && startDatePicker.input ? startDatePicker.input.value : '',
        endDatePicker && endDatePicker.input ? endDatePicker.input.value : ''
    );
}

function dayAfterIso(isoDate) {
    if (!isoDate) return null;
    const d = new Date(String(isoDate).trim() + 'T12:00:00');
    if (Number.isNaN(d.getTime())) return null;
    d.setDate(d.getDate() + 1);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function syncLinkedDatePickers(startValue, endValue) {
    const start = (startValue || '').trim();
    const end = (endValue || '').trim();
    const minEnd = dayAfterIso(start);

    if (startDatePicker) {
        if (start) {
            startDatePicker.setDate(start, false);
            startDatePicker.jumpToDate(start, true);
        } else {
            startDatePicker.clear();
        }
    }

    if (endDatePicker) {
        if (minEnd) endDatePicker.set('minDate', minEnd);
        else endDatePicker.set('minDate', null);

        // End must be strictly after start (planner cannot do same-day trips).
        const resolvedEnd = end && (!start || end > start) ? end : (minEnd || '');
        if (resolvedEnd) {
            endDatePicker.setDate(resolvedEnd, false);
            endDatePicker.jumpToDate(resolvedEnd, true);
        } else {
            endDatePicker.clear();
        }
    }
}

function readFormSnapshot() {
    return {
        tripTitle: document.getElementById('tripTitle')?.value || '',
        startingCity: document.getElementById('startingCity')?.value || '',
        startDate: document.getElementById('startDate')?.value || '',
        endDate: document.getElementById('endDate')?.value || '',
        people: document.getElementById('people')?.value || '1',
        preferredTransport: document.getElementById('preferredTransport')?.value || 'allModes',
        preferences: document.getElementById('preferences')?.value || '',
        placesList: document.getElementById('placesList')?.value || '',
        useTravelLog: useTravelLogFromDb()
    };
}

function applyFormSnapshot(form) {
    if (!form) return;
    const setVal = (id, value) => {
        const el = document.getElementById(id);
        if (!el || value == null) return;
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    setVal('tripTitle', form.tripTitle);
    setVal('startingCity', form.startingCity);
    setVal('people', form.people);
    setVal('preferredTransport', form.preferredTransport);
    setVal('preferences', form.preferences);
    setVal('placesList', form.placesList);
    syncLinkedDatePickers(form.startDate, form.endDate);
    const dbToggle = document.getElementById('useTravelLogInPlanner');
    if (dbToggle && typeof form.useTravelLog === 'boolean') {
        dbToggle.checked = form.useTravelLog;
    }
}

function selectPlanType(plan) {
    selectedPlan = plan || 'random';
    document.querySelectorAll('.route-option-card').forEach((card) => {
        card.classList.toggle('selected', card.dataset.plan === selectedPlan);
    });
    updatePlacesField();
}

function persistFormOnly() {
    savePlannerSession({
        selectedPlan,
        form: readFormSnapshot()
    });
}

function scrollPlannerResultsIntoView() {
    const target =
        document.getElementById('resultsContainer') ||
        document.getElementById('tripResults');
    if (!target) return;
    // Wait a frame so the results block is visible before scrolling.
    requestAnimationFrame(function () {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    // Register before any await so the travel-log toggle hook can find them.
    window.onTravelLogPlannerPrefChanged = () => {
        refreshPlannerDbHints();
        persistFormOnly();
    };
    window.onTravelLogPlannerPrefLoaded = () => refreshPlannerDbHints();

    const form = document.getElementById('tripPlanForm');
    trackFilledInputs();
    initDatePickers();
    refreshPlannerDbHints();
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');
    const planCards = document.querySelectorAll('.route-option-card');

    if (!form || !generateBtn) return;

    let submittingViaRetry = false;

    const retryGeneration = () => {
        submittingViaRetry = true;
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
        } else {
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
    };

    const resultOptions = () => {
        const session = loadPlannerSession();
        return {
            onRetry: retryGeneration,
            stopFeedback: (session && session.stopFeedback) || createEmptyStopFeedback(),
            onFeedbackChange: () => {
                const sessionNow = loadPlannerSession() || {};
                const synced = syncStopFeedbackFromCards(
                    sessionNow.stopFeedback || createEmptyStopFeedback(),
                    tripResults
                );
                savePlannerSession({ stopFeedback: synced });
            },
            onSaved: () => {
                // Clear planner session before redirect to planned trips.
                clearPlannerSession();
            },
        };
    };

    async function runGeneration(planType, body, meta) {
        if (generationInFlight || window.__plannerGenerationRunning) return;
        generationInFlight = true;
        window.__plannerGenerationRunning = true;

        if (window.__plannerBackgroundAbort) {
            try { window.__plannerBackgroundAbort.abort(); } catch (_) { /* ignore */ }
            window.__plannerBackgroundAbort = null;
        }

        if (activeGenerationAbort) {
            try { activeGenerationAbort.abort(); } catch (_) { /* ignore */ }
        }
        activeGenerationAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
        const generationId = Date.now();

        savePlannerSession({
            status: 'generating',
            selectedPlan: planType,
            form: readFormSnapshot(),
            requestBody: body,
            generationId: generationId,
            resultData: null,
            errorMessage: null,
            errorDetails: null,
            notifyPending: false
        });

        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        const originalBtnContent = generateBtn.innerHTML;
        generateBtn.textContent = planNewTripT('generating', 'Generating...');

        try {
            const fetchOpts = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            };
            if (activeGenerationAbort) fetchOpts.signal = activeGenerationAbort.signal;

            const response = await fetch(`${API_BASE_URL}${ENDPOINTS[planType]}`, fetchOpts);

            if (!response.ok) {
                let detail = `HTTP ${response.status}`;
                try {
                    const errBody = await response.json();
                    if (errBody.detail) {
                        detail = typeof errBody.detail === 'string'
                            ? errBody.detail
                            : JSON.stringify(errBody.detail);
                    }
                } catch (_) { /* keep detail */ }
                throw new Error(detail);
            }

            const data = await response.json();
            data.userStartDate = meta.startDate;
            data.userEndDate = meta.endDate;
            data.userPeople = meta.people;
            data.userTripTitle = meta.tripTitle || '';

            // Ignore stale responses if a newer generation was started.
            const latest = loadPlannerSession();
            if (!latest || latest.status !== 'generating' || latest.generationId !== generationId) {
                return;
            }

            savePlannerSession({
                status: 'ready',
                selectedPlan: planType,
                form: readFormSnapshot(),
                requestBody: body,
                generationId: generationId,
                resultData: data,
                errorMessage: null,
                errorDetails: null,
                notifyPending: false
            });

            displayResults(data, tripResults, resultsContainer, resultOptions());
            scrollPlannerResultsIntoView();
        } catch (error) {
            // Leaving the page aborts the fetch so background resume can take over — do not mark error.
            if (error && (error.name === 'AbortError' || error.code === 20)) {
                return;
            }
            console.error('Error generating trip:', error);
            const latest = loadPlannerSession();
            if (latest && latest.generationId && latest.generationId !== generationId) {
                return;
            }
            savePlannerSession({
                status: 'error',
                selectedPlan: planType,
                form: readFormSnapshot(),
                requestBody: body,
                generationId: generationId,
                resultData: null,
                errorMessage: planNewTripT('generateFailed', 'Failed to generate trip. Please try again.'),
                errorDetails: localizePlannerErrorDetail(error.message),
                notifyPending: false
            });
            showError(
                planNewTripT('generateFailed', 'Failed to generate trip. Please try again.'),
                localizePlannerErrorDetail(error.message),
                tripResults,
                resultsContainer,
                resultOptions()
            );
        } finally {
            generationInFlight = false;
            window.__plannerGenerationRunning = false;
            loadingState.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalBtnContent;
        }
    }

    /** Wait for a background (or other-tab) generation to leave status=generating. */
    function waitForPlannerSessionSettled(timeoutMs) {
        const limit = typeof timeoutMs === 'number' ? timeoutMs : 10 * 60 * 1000;
        const started = Date.now();
        return new Promise((resolve) => {
            const tick = () => {
                const s = loadPlannerSession();
                if (!s || s.status === 'ready' || s.status === 'error') {
                    resolve({ session: s, timedOut: false });
                    return;
                }
                if (Date.now() - started > limit) {
                    resolve({ session: s, timedOut: true });
                    return;
                }
                setTimeout(tick, 400);
            };
            tick();
        });
    }

    async function resumeOrAwaitGeneration(session) {
        const meta = {
            startDate: session.requestBody.startDate || session.form?.startDate,
            endDate: session.requestBody.endDate || session.form?.endDate,
            people: session.requestBody.people || Number(session.form?.people) || 1,
            tripTitle: (session.form && session.form.tripTitle) || ''
        };
        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;

        // Background fetch still running (user navigated away mid-request) — do not start a duplicate.
        if (window.__plannerGenerationRunning) {
            const waitResult = await waitForPlannerSessionSettled();
            const settled = waitResult.session;
            loadingState.style.display = 'none';
            generateBtn.disabled = false;

            if (waitResult.timedOut && settled && settled.status === 'generating') {
                const timeoutMsg = planNewTripT('generationTimedOut', 'Trip generation is taking too long. Please try again.');
                savePlannerSession({
                    status: 'error',
                    errorMessage: timeoutMsg,
                    errorDetails: null,
                    notifyPending: false
                });
                showError(timeoutMsg, '', tripResults, resultsContainer, resultOptions());
                return;
            }

            if (settled && settled.status === 'ready' && settled.resultData && settled.resultData.draft_plan) {
                if (!settled.resultData.userTripTitle && settled.form && settled.form.tripTitle) {
                    settled.resultData.userTripTitle = settled.form.tripTitle;
                }
                if (plannerSessionApi() && typeof plannerSessionApi().clearReadyAttention === 'function') {
                    plannerSessionApi().clearReadyAttention();
                }
                displayResults(settled.resultData, tripResults, resultsContainer, resultOptions());
                scrollPlannerResultsIntoView();
            } else if (settled && settled.status === 'error') {
                showError(
                    settled.errorMessage || planNewTripT('generateFailed', 'Failed to generate trip. Please try again.'),
                    localizePlannerErrorDetail(settled.errorDetails || ''),
                    tripResults,
                    resultsContainer,
                    resultOptions()
                );
            }
            return;
        }

        await runGeneration(session.selectedPlan || selectedPlan, session.requestBody, meta);
    }

    planCards.forEach(card => {
        card.addEventListener('click', () => {
            selectPlanType(card.dataset.plan);
            persistFormOnly();
        });
    });

    form.addEventListener('change', persistFormOnly);
    form.addEventListener('input', persistFormOnly);

    const cancelBtn = form.querySelector('.btn-cancel');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            resetPlannerUi();
        });
    }

    updatePlacesField();
    await loadHomeCity();

    const session = loadPlannerSession();
    if (session) {
        if (session.selectedPlan) selectPlanType(session.selectedPlan);
        if (session.form) applyFormSnapshot(session.form);
        refreshPlannerDbHints();

        if (session.status === 'ready' && session.resultData && session.resultData.draft_plan) {
            if (!session.resultData.userTripTitle && session.form && session.form.tripTitle) {
                session.resultData.userTripTitle = session.form.tripTitle;
            }
            if (plannerSessionApi() && typeof plannerSessionApi().clearReadyAttention === 'function') {
                plannerSessionApi().clearReadyAttention();
            } else {
                savePlannerSession({ notifyPending: false });
            }
            displayResults(session.resultData, tripResults, resultsContainer, resultOptions());
            // Toast "View plan" links to #resultsContainer — scroll to the itinerary.
            if ((window.location.hash || '') === '#resultsContainer') {
                scrollPlannerResultsIntoView();
            }
        } else if (session.status === 'error') {
            showError(
                session.errorMessage || planNewTripT('generateFailed', 'Failed to generate trip. Please try again.'),
                localizePlannerErrorDetail(session.errorDetails || ''),
                tripResults,
                resultsContainer,
                resultOptions()
            );
        } else if (session.status === 'generating' && session.requestBody) {
            // Resume or wait for an in-flight background request (avoid a second LLM call).
            await resumeOrAwaitGeneration(patchStalePlannerSession(session));
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const viaRetry = submittingViaRetry;
        submittingViaRetry = false;

        const tripTitle = (document.getElementById('tripTitle')?.value || '').trim();
        const startingCity = document.getElementById('startingCity').value.trim();
        const preferredTransport = document.getElementById('preferredTransport').value.trim();
        const peopleRaw = (document.getElementById('people').value || '').trim();
        const peopleParsed = peopleRaw === '' ? NaN : parseInt(peopleRaw, 10);
        const people = Number.isFinite(peopleParsed) && peopleParsed > 0 ? peopleParsed : 1;
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const preferencesInput = document.getElementById('preferences').value.trim();

        if (!startingCity) {
            showError(planNewTripT('startingCityRequired', 'Please enter a starting city.'), '', tripResults, resultsContainer);
            return;
        }
        if (!startDate || !endDate) {
            showError(planNewTripT('datesRequired', 'Please select both start and end dates.'), '', tripResults, resultsContainer);
            return;
        }
        if (endDate <= startDate) {
            showError(planNewTripT('endDateAfterStart', 'End date must be after start date.'), '', tripResults, resultsContainer);
            return;
        }

        const preferences = preferencesInput
            ? preferencesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        const body = {
            startingPoint: startingCity,
            startDate: startDate,
            endDate: endDate,
            people: people,
            preferences: preferences,
            language: localStorage.getItem('language') || 'en'
        };

        if (preferredTransport) {
            body.preferredTransport = preferredTransport;
        }

        const placesInput = (document.getElementById('placesList')?.value || '').trim();
        const manualPlaces = placesInput
            ? placesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        const useDb = useTravelLogFromDb();

        if (selectedPlan === 'visited') {
            body.visitedPlaces = [];
            body.extraPlaces = manualPlaces;
            if (useDb) {
                const uid = localStorage.getItem('user_id');
                if (!uid) {
                    showError(
                        planNewTripT('visitedRequiresLogin', 'Please log in. Visited trips load your saved places on the server.'),
                        '',
                        tripResults,
                        resultsContainer
                    );
                    return;
                }
                const parsed = parseInt(uid, 10);
                if (Number.isNaN(parsed)) {
                    showError(planNewTripT('invalidSession', 'Invalid user session.'), '', tripResults, resultsContainer);
                    return;
                }
                body.userId = parsed;
                if (!manualPlaces.length) {
                    const hasSavedPlaces = await userHasSavedVisitedPlaces(uid);
                    if (hasSavedPlaces === false) {
                        showError(
                            planNewTripT('manualPlacesRequired', 'Add at least one place in the field above, or turn on using your travel log from the database.'),
                            '',
                            tripResults,
                            resultsContainer
                        );
                        return;
                    }
                }
            } else if (!manualPlaces.length) {
                showError(
                    planNewTripT('manualPlacesRequired', 'Add at least one place below, or turn on using your travel log from the database.'),
                    '',
                    tripResults,
                    resultsContainer
                );
                return;
            }
        } else if (selectedPlan === 'unvisited') {
            body.additionalExclusions = manualPlaces;
            // Opt-in: only send userId when DB travel-log exclusions are enabled.
            if (useDb) {
                const uid = localStorage.getItem('user_id');
                if (!uid) {
                    showError(
                        planNewTripT('unvisitedRequiresLogin', 'Please log in. Unvisited trips load your saved places on the server to exclude them.'),
                        '',
                        tripResults,
                        resultsContainer
                    );
                    return;
                }
                const parsed = parseInt(uid, 10);
                if (Number.isNaN(parsed)) {
                    showError(planNewTripT('invalidSession', 'Invalid user session.'), '', tripResults, resultsContainer);
                    return;
                }
                body.userId = parsed;
            }
        }

        let stopFeedback = createEmptyStopFeedback();
        if (viaRetry) {
            const session = loadPlannerSession() || {};
            stopFeedback = syncStopFeedbackFromCards(
                session.stopFeedback || createEmptyStopFeedback(),
                tripResults
            );
            savePlannerSession({ stopFeedback });
        } else {
            savePlannerSession({ stopFeedback: createEmptyStopFeedback() });
        }
        if (stopFeedback.likedPlaces.length) body.likedPlaces = stopFeedback.likedPlaces;
        if (stopFeedback.dislikedPlaces.length) body.dislikedPlaces = stopFeedback.dislikedPlaces;

        await runGeneration(selectedPlan, body, { startDate, endDate, people, tripTitle });
    });

    // Hand off to background resume on other pages: abort local fetch without marking error.
    window.addEventListener('pagehide', () => {
        if (activeGenerationAbort) {
            try { activeGenerationAbort.abort(); } catch (_) { /* ignore */ }
        }
    });
});
