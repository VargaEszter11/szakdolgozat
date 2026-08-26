import { displayResults, showError } from './tripRenderer.js';

const API_BASE_URL = window.API_BASE_URL || '';

function plannerSessionApi() {
    return window.PlannerSession || null;
}

function loadPlannerSession() {
    const api = plannerSessionApi();
    if (api) return api.load();
    try {
        const raw = sessionStorage.getItem('planner_generation_session_v1');
        return raw ? JSON.parse(raw) : null;
    } catch (err) {
        return null;
    }
}

function savePlannerSession(patch) {
    const api = plannerSessionApi();
    if (api) return api.save(patch);
    try {
        const current = loadPlannerSession() || {};
        sessionStorage.setItem(
            'planner_generation_session_v1',
            JSON.stringify({ ...current, ...patch, updatedAt: Date.now() })
        );
    } catch (err) {
        console.warn('Could not persist planner session:', err);
    }
}

function clearPlannerSession() {
    const api = plannerSessionApi();
    if (api) {
        api.clear();
        return;
    }
    try {
        sessionStorage.removeItem('planner_generation_session_v1');
    } catch (err) { /* ignore */ }
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
    generationInFlight = false;
    clearPlannerSession();
    resetPlannerFormFields();
    clearPlannerResults();
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) generateBtn.disabled = false;
}

const ENDPOINTS = {
    visited: '/generate_travel_plans/visited',
    unvisited: '/generate_travel_plans/unvisited',
    random: '/generate_travel_plans/random'
};

let selectedPlan = 'random';
let savedVisitedPlaces = [];
let generationInFlight = false;

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
                const t = window.i18n ? window.i18n.t.bind(window.i18n) : (k, f) => f;
                showError(
                    t('planNewTrip.homeCityRequired', 'Type a starting city first, then click again to save it as your home city.'),
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
        } finally {
            btn.disabled = false;
        }
    });
}

async function loadSavedPlaces() {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/users/${userId}/visited-places`);
        if (res.ok) {
            const places = await res.json();
            if (Array.isArray(places) && places.length > 0) {
                savedVisitedPlaces = [...new Set(
                    places.map(p => {
                        const name = p.place_name || '';
                        const country = p.country || '';
                        return country ? `${name}, ${country}` : name;
                    }).filter(n => n)
                )];
            }
        }
    } catch (err) {
        console.warn('Could not load visited places:', err);
    }
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
            endDatePicker.set('minDate', dateStr);
            const endVal = endDatePicker.input.value || '';
            if (!endVal || endVal < dateStr) {
                endDatePicker.setDate(dateStr, true);
            }
            endDatePicker.jumpToDate(dateStr, true);
        }
    });

    syncLinkedDatePickers(
        startDatePicker && startDatePicker.input ? startDatePicker.input.value : '',
        endDatePicker && endDatePicker.input ? endDatePicker.input.value : ''
    );
}

function syncLinkedDatePickers(startValue, endValue) {
    const start = (startValue || '').trim();
    const end = (endValue || '').trim();

    if (startDatePicker) {
        if (start) {
            startDatePicker.setDate(start, false);
            startDatePicker.jumpToDate(start, true);
        } else {
            startDatePicker.clear();
        }
    }

    if (endDatePicker) {
        if (start) endDatePicker.set('minDate', start);
        else endDatePicker.set('minDate', null);

        const resolvedEnd = end && (!start || end >= start) ? end : (start || '');
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

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('tripPlanForm');
    trackFilledInputs();
    initDatePickers();
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');
    const planCards = document.querySelectorAll('.route-option-card');

    if (!form || !generateBtn) return;

    const retryGeneration = () => {
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
        } else {
            form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
    };

    const resultOptions = () => ({
        onRetry: retryGeneration,
        onSaved: () => {
            resetPlannerUi();
        },
        onCancel: () => {
            resetPlannerUi();
        }
    });

    async function runGeneration(planType, body, meta) {
        if (generationInFlight) return;
        generationInFlight = true;

        savePlannerSession({
            status: 'generating',
            selectedPlan: planType,
            form: readFormSnapshot(),
            requestBody: body,
            resultData: null,
            errorMessage: null,
            errorDetails: null,
            notifyPending: false
        });

        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        const originalBtnContent = generateBtn.innerHTML;
        generateBtn.textContent = window.i18n ? window.i18n.t('planNewTrip.generating') : 'Generating...';

        try {
            const response = await fetch(`${API_BASE_URL}${ENDPOINTS[planType]}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

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

            savePlannerSession({
                status: 'ready',
                selectedPlan: planType,
                form: readFormSnapshot(),
                requestBody: body,
                resultData: data,
                errorMessage: null,
                errorDetails: null,
                notifyPending: false
            });

            displayResults(data, tripResults, resultsContainer, resultOptions());
        } catch (error) {
            console.error('Error generating trip:', error);
            savePlannerSession({
                status: 'error',
                selectedPlan: planType,
                form: readFormSnapshot(),
                requestBody: body,
                resultData: null,
                errorMessage: 'Failed to generate trip. Please try again.',
                errorDetails: error.message,
                notifyPending: false
            });
            showError(
                'Failed to generate trip. Please try again.',
                error.message,
                tripResults,
                resultsContainer,
                resultOptions()
            );
        } finally {
            generationInFlight = false;
            loadingState.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalBtnContent;
        }
    }

    window.onTravelLogPlannerPrefChanged = () => {
        refreshPlannerDbHints();
        persistFormOnly();
    };
    window.onTravelLogPlannerPrefLoaded = () => refreshPlannerDbHints();

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

    const dbToggle = document.getElementById('useTravelLogInPlanner');
    if (dbToggle) {
        dbToggle.addEventListener('change', () => {
            refreshPlannerDbHints();
            persistFormOnly();
        });
    }

    updatePlacesField();
    await Promise.all([loadSavedPlaces(), loadHomeCity()]);

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
        } else if (session.status === 'error') {
            showError(
                session.errorMessage || 'Failed to generate trip. Please try again.',
                session.errorDetails || '',
                tripResults,
                resultsContainer,
                resultOptions()
            );
        } else if (session.status === 'generating' && session.requestBody) {
            // Page was left mid-request; resume with the same payload.
            await runGeneration(session.selectedPlan || selectedPlan, session.requestBody, {
                startDate: session.requestBody.startDate || session.form?.startDate,
                endDate: session.requestBody.endDate || session.form?.endDate,
                people: session.requestBody.people || Number(session.form?.people) || 1,
                tripTitle: (session.form && session.form.tripTitle) || ''
            });
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const tripTitle = (document.getElementById('tripTitle')?.value || '').trim();
        const startingCity = document.getElementById('startingCity').value.trim();
        const preferredTransport = document.getElementById('preferredTransport').value.trim();
        const peopleRaw = (document.getElementById('people').value || '').trim();
        const peopleParsed = peopleRaw === '' ? NaN : parseInt(peopleRaw, 10);
        const people = Number.isFinite(peopleParsed) && peopleParsed > 0 ? peopleParsed : 1;
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const preferencesInput = document.getElementById('preferences').value.trim();

        if (!startDate || !endDate) {
            showError('Please select both start and end dates.', '', tripResults, resultsContainer);
            return;
        }
        if (endDate < startDate) {
            showError('End date must be on or after start date.', '', tripResults, resultsContainer);
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

        const plannerUid = localStorage.getItem('user_id');
        if (plannerUid) {
            const p = parseInt(plannerUid, 10);
            if (!Number.isNaN(p)) {
                body.plannerUserId = p;
            }
        }

        const placesInput = (document.getElementById('placesList')?.value || '').trim();
        const manualPlaces = placesInput
            ? placesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        const useDb = useTravelLogFromDb();

        if (selectedPlan === 'visited') {
            const fromDb = useDb ? savedVisitedPlaces : [];
            body.visitedPlaces = fromDb;
            body.extraPlaces = manualPlaces;
            if (!body.visitedPlaces.length && !body.extraPlaces.length) {
                const msg = window.i18n && window.i18n.t
                    ? window.i18n.t('planNewTrip.manualPlacesRequired')
                    : 'Add at least one place below, or turn on using your travel log from the database.';
                showError(msg, '', tripResults, resultsContainer);
                return;
            }
        } else if (selectedPlan === 'unvisited') {
            body.additionalExclusions = manualPlaces;
            if (useDb) {
                const uid = localStorage.getItem('user_id');
                if (!uid) {
                    const msg = window.i18n && window.i18n.t
                        ? window.i18n.t('planNewTrip.unvisitedRequiresLogin')
                        : 'Please log in. Unvisited trips load your saved places on the server to exclude them.';
                    showError(msg, '', tripResults, resultsContainer);
                    return;
                }
                const parsed = parseInt(uid, 10);
                if (Number.isNaN(parsed)) {
                    showError('Invalid user session.', '', tripResults, resultsContainer);
                    return;
                }
                body.userId = parsed;
            }
        }

        await runGeneration(selectedPlan, body, { startDate, endDate, people, tripTitle });
    });
});
