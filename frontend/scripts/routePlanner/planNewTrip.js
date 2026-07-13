import { displayResults, showError } from './tripRenderer.js';

const API_BASE_URL = window.API_BASE_URL || '';

const ENDPOINTS = {
    visited: '/generate_travel_plans/visited',
    unvisited: '/generate_travel_plans/unvisited',
    random: '/generate_travel_plans/random'
};

let selectedPlan = 'random';
let savedVisitedPlaces = [];

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

function initDatePickers() {
    if (typeof flatpickr === 'undefined') return;

    const LOCALE_MAP = { hu: 'hu', de: 'de' };
    const lang = localStorage.getItem('language') || 'en';
    const fpLocale = LOCALE_MAP[lang] || 'default';

    const opts = {
        dateFormat: 'Y-m-d',
        locale: fpLocale,
        disableMobile: true
    };

    flatpickr('#startDate', opts);
    flatpickr('#endDate', opts);
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

    window.onTravelLogPlannerPrefChanged = () => refreshPlannerDbHints();
    window.onTravelLogPlannerPrefLoaded = () => refreshPlannerDbHints();

    planCards.forEach(card => {
        card.addEventListener('click', () => {
            planCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedPlan = card.dataset.plan;
            updatePlacesField();
        });
    });

    updatePlacesField();
    loadSavedPlaces();
    loadHomeCity();
    const dbToggle = document.getElementById('useTravelLogInPlanner');
    if (dbToggle) {
        dbToggle.addEventListener('change', () => refreshPlannerDbHints());
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

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
        if (endDate <= startDate) {
            showError('End date must be after start date.', '', tripResults, resultsContainer);
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

        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        const originalBtnContent = generateBtn.innerHTML;
        generateBtn.textContent = window.i18n ? window.i18n.t('planNewTrip.generating') : 'Generating...';

        try {
            const response = await fetch(`${API_BASE_URL}${ENDPOINTS[selectedPlan]}`, {
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
            data.userStartDate = startDate;
            data.userEndDate = endDate;
            data.userPeople = people;
            displayResults(data, tripResults, resultsContainer);

        } catch (error) {
            console.error('Error generating trip:', error);
            showError('Failed to generate trip. Please try again.', error.message, tripResults, resultsContainer);
        } finally {
            loadingState.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalBtnContent;
        }
    });
});
