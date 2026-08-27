var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
        return new Date(dateStr).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

function escapeHtml(str) {
    if (str == null || str === '') return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function plannedTripsLabel(key, fallback) {
    if (window.TripDisplayHelper && typeof window.TripDisplayHelper.plannedTripsT === 'function') {
        const v = window.TripDisplayHelper.plannedTripsT(key, fallback);
        return v != null ? v : fallback;
    }
    if (window.i18n && typeof window.i18n.t === 'function') {
        const v = window.i18n.t('plannedTrips.' + key);
        if (v && String(v).indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
}

export function planNewTripT(key, fallback, vars) {
    let text = fallback;
    if (window.i18n && typeof window.i18n.t === 'function') {
        const v = window.i18n.t('planNewTrip.' + key);
        if (v && !String(v).startsWith('planNewTrip.')) text = v;
    }
    if (vars) {
        Object.keys(vars).forEach(function (k) {
            text = text.replace(new RegExp('\\{\\{' + k + '\\}\\}', 'g'), String(vars[k]));
        });
    }
    return text;
}

// Map known English API error details to localized planner strings
export function localizePlannerErrorDetail(detail) {
    if (detail == null || detail === '') return detail;
    const s = String(detail);
    if (/add at least one place/i.test(s) || /travel log/i.test(s)) {
        return planNewTripT(
            'manualPlacesRequired',
            'Add at least one place in the field above, or turn on using your travel log from the database.'
        );
    }
    if (/end date must be after/i.test(s)) {
        return planNewTripT('endDateAfterStart', 'End date must be after start date.');
    }
    return detail;
}

function transportLabel(transport) {
    return window.TripDisplayHelper
        ? window.TripDisplayHelper.transportLabel(transport)
        : (transport || 'N/A');
}

function formatStopTransport(destination) {
    // Hub airport names (access_city) appear in the label only — not as the visit city.
    const t = window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t.bind(window.i18n) : null;
    function tpl(key, fallback) {
        if (!t) return fallback;
        const value = t('plannedTrips.' + key);
        return value && !String(value).startsWith('plannedTrips.') ? value : fallback;
    }
    const thenJoin = tpl('transportThenJoin', ', then ');

    const parts = [];
    const depLocal = destination.departure_local_transport || destination.departureLocalTransport;
    const depAccess = destination.departure_access_city || destination.departureAccessCity;
    if (depLocal && depAccess) {
        parts.push(
            tpl('transportHubDeparture', '{local} to {access}')
                .replace('{local}', transportLabel(depLocal))
                .replace('{access}', depAccess)
        );
    }

    const mainRaw = destination.transportFromPreviousCity || destination.transport_from_last;
    const main = transportLabel(mainRaw);
    const local = destination.local_transport || destination.localTransport;
    const access = destination.access_city || destination.accessCity;
    const isReturn = !!(destination.is_return_home || destination.isReturnHome);

    if (local && access) {
        parts.push(
            tpl('transportWithLocalTransfer', '{main}, then {local} from {access}')
                .replace('{main}', main)
                .replace('{local}', transportLabel(local))
                .replace('{access}', access)
        );
    } else if (access && isReturn) {
        parts.push(
            tpl('transportGroundFromHub', '{main} from {access}')
                .replace('{main}', main)
                .replace('{access}', access)
        );
    } else {
        parts.push(main);
    }

    return parts.filter(Boolean).join(thenJoin);
}

function accommodationBookingUrl(city, country, checkin, checkout, people) {
    return window.TripDisplayHelper
        ? window.TripDisplayHelper.accommodationBookingUrl(city, country, checkin, checkout, people)
        : null;
}

function hasPlanStops(trip) {
    return !!(trip && Array.isArray(trip.plan) && trip.plan.length > 0);
}

/** Parse YYYY-MM-DD at local noon — avoids UTC day shifts from Date/toISOString. */
function parseIsoLocal(iso) {
    const s = String(iso || '').trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
    const d = new Date(s + 'T12:00:00');
    return Number.isNaN(d.getTime()) ? null : d;
}

function formatIsoLocal(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function isoDateOnly(value) {
    const s = String(value || '').trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const d = parseIsoLocal(s.slice(0, 10));
    return d ? formatIsoLocal(d) : s.slice(0, 10);
}

function addDaysIso(iso, days) {
    const d = parseIsoLocal(iso);
    if (!d) return iso;
    d.setDate(d.getDate() + days);
    return formatIsoLocal(d);
}

function todayIsoLocal() {
    return formatIsoLocal(new Date());
}

export function displayResults(data, tripResults, resultsContainer, options = {}) {
    // Guard before rendering Save: backend may return an empty plan on edge cases.
    if (!data.draft_plan) {
        showError(planNewTripT('noPlanGenerated', 'No trip plan was generated. Please try again.'), null, tripResults, resultsContainer, options);
        return;
    }
    if (!hasPlanStops(data.draft_plan)) {
        showError(planNewTripT('planNoStops', 'This plan has no stops. Please try again.'), null, tripResults, resultsContainer, options);
        return;
    }

    const html = renderTripDetails(data.draft_plan, data.userPeople || 1, data.userTripTitle);

    tripResults.innerHTML = html;
    resultsContainer.style.display = 'block';

    const saveTripBtn = tripResults.querySelector('#saveTripBtn');
    if (saveTripBtn) {
        saveTripBtn.addEventListener('click', async () => {
            await saveTripToDatabase(
                data.draft_plan,
                saveTripBtn,
                data.userStartDate,
                data.userEndDate,
                data.userPeople,
                { onSaved: options.onSaved, tripTitle: data.userTripTitle }
            );
        });
    }
    bindRetryButton(tripResults, options.onRetry);
}

export function renderTripDetails(trip, people = 1, tripTitle = '') {
    const dateRange = trip.startDate && trip.endDate
        ? `${formatDate(trip.startDate)} — ${formatDate(trip.endDate)}`
        : planNewTripT('tripDays', '{{n}} days', { n: trip.tripLengthDays || 0 });
    const heading = (tripTitle && String(tripTitle).trim())
        || trip.startingPoint
        || planNewTripT('yourTrip', 'Your Trip');

    let html = `
        <div class="trip-header">
            <h3>${escapeHtml(heading)}</h3>
            <span class="trip-length">${dateRange}</span>
        </div>
    `;

    if (Array.isArray(trip.requestedPlacesMissing) && trip.requestedPlacesMissing.length) {
        html += `
            <p class="error-message">
                ${escapeHtml(planNewTripT('requestedPlacesMissing', 'Could not include these requested places with the current route data:'))}
                ${trip.requestedPlacesMissing.map(p => escapeHtml(p)).join(', ')}
            </p>
        `;
    }

    // Destinations
    if (trip.plan && Array.isArray(trip.plan)) {
        html += '<div class="trip-destinations">';
        trip.plan.forEach((destination, idx) => {
            const countryLabel =
                window.Countries && window.Countries.displayName
                    ? window.Countries.displayName(destination.country)
                    : destination.country;
            const cityLine = [destination.city, countryLabel]
                .map((part) => (part == null ? '' : String(part).trim()))
                .filter(Boolean)
                .map(escapeHtml)
                .join(', ');
            const accommodationUrl = window.TripDisplayHelper
                && typeof window.TripDisplayHelper.accommodationBookingUrlForStop === 'function'
                ? window.TripDisplayHelper.accommodationBookingUrlForStop(
                    destination,
                    countryLabel,
                    destination.arrivalDate,
                    destination.departureDate,
                    people
                )
                : accommodationBookingUrl(
                    destination.city,
                    countryLabel,
                    destination.arrivalDate,
                    destination.departureDate,
                    people
                );
            html += `
                <div class="destination-card">
                    <div class="destination-number">${idx + 1}</div>
                    <div class="destination-details">
                        <h4 class="destination-city">${cityLine}</h4>
                        <p class="destination-info">
                            ${destination.arrivalDate && destination.departureDate
                    ? `<strong>${escapeHtml(plannedTripsLabel('dates', 'Dates'))}:</strong> ${formatDate(destination.arrivalDate)} → ${formatDate(destination.departureDate)}`
                    : `<strong>${escapeHtml(plannedTripsLabel('days', 'Days'))}:</strong> ${destination.days}`}
                             | <strong>${escapeHtml(plannedTripsLabel('transport', 'Transport'))}:</strong> ${escapeHtml(formatStopTransport(destination))}
                        </p>
                        ${destination.booking_url || accommodationUrl ? `
                            <div class="trip-stop-actions">
                                ${destination.booking_url ? `
                                    <a class="btn-add trip-stop-action-link" href="${escapeHtml(destination.booking_url)}" target="_blank" rel="noopener noreferrer">
                                        ${escapeHtml(destination.flight_availability_verified
                        ? plannedTripsLabel('bookThisFlight', 'Book this flight')
                        : plannedTripsLabel('checkFlightAvailability', 'Check flight availability'))}
                                    </a>
                                ` : ''}
                                ${accommodationUrl ? `
                                    <a class="btn-add trip-stop-action-link" href="${escapeHtml(accommodationUrl)}" target="_blank" rel="noopener noreferrer">
                                        ${escapeHtml(plannedTripsLabel('findAccommodation', 'Find accommodation'))}
                                    </a>
                                ` : ''}
                            </div>
                        ` : ''}
                        ${destination.activities && destination.activities.length > 0 ? `
                            <div class="activities">
                                <strong>${escapeHtml(plannedTripsLabel('suggestedActivities', 'Suggested activities'))}:</strong>
                                <ul>
                                    ${destination.activities.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }

    // Save / retry actions
    const saveLabel = planNewTripT('saveTrip', 'Save Trip');
    const retryLabel = planNewTripT('retryPlan', 'Retry');
    html += `
        <div class="trip-actions">
            <button type="button" id="retryTripBtn" class="btn-add btn-add-outline">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <polyline points="23 4 23 10 17 10"/>
                    <polyline points="1 20 1 14 7 14"/>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                ${escapeHtml(retryLabel)}
            </button>
            <button type="button" id="saveTripBtn" class="btn-add">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                    <polyline points="17 21 17 13 7 13 7 21"/>
                    <polyline points="7 3 7 8 15 8"/>
                </svg>
                ${escapeHtml(saveLabel)}
            </button>
        </div>
    `;

    return html;
}

function bindRetryButton(root, onRetry) {
    const retryBtn = root && root.querySelector('#retryTripBtn');
    if (!retryBtn || typeof onRetry !== 'function') return;
    retryBtn.addEventListener('click', () => {
        onRetry();
    });
}

async function saveTripToDatabase(trip, button, userStartDate, userEndDate, userPeople, options = {}) {
    // Two-step save: trip shell, then stops. Failed stop POST rolls back the trip.
    const userId = localStorage.getItem('user_id');
    if (!userId) {
        window.showError(planNewTripT('loginToSave', 'Please log in to save trips.'), function () {
            window.location.href = '../loginRegister/loginPage.html';
        });
        return;
    }

    if (!hasPlanStops(trip)) {
        window.showError(planNewTripT('planNoStopsToSave', 'This plan has no stops to save.'));
        return;
    }

    const originalText = button.innerHTML;
    button.disabled = true;
    button.textContent = planNewTripT('savingTrip', 'Saving…');

    try {
        const startIso = isoDateOnly(userStartDate) || todayIsoLocal();
        const endIso = userEndDate
            ? isoDateOnly(userEndDate)
            : addDaysIso(startIso, trip.tripLengthDays || 0);

        const customTitle = options.tripTitle && String(options.tripTitle).trim();
        // user_id comes from the access token on the server — do not send it from the client.
        const tripData = {
            title: customTitle || trip.startingPoint || planNewTripT('myTrip', 'My Trip'),
            start_date: startIso,
            end_date: endIso,
            start_city: trip.startingPoint || null,
            people: userPeople || trip.people || 1
        };

        const base = window.API_BASE_URL || '';
        const tripResponse = await fetch(base + '/api/planned-trips', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(tripData)
        });

        if (!tripResponse.ok) {
            throw new Error(planNewTripT('createTripFailed', 'Failed to create trip'));
        }

        const createdTrip = await tripResponse.json();
        const tripId = createdTrip.id;

        if (trip.plan && Array.isArray(trip.plan)) {
            let currentIso = startIso;

            for (let i = 0; i < trip.plan.length; i++) {
                const destination = trip.plan[i];
                let arrivalStr, departureStr;

                if (destination.arrivalDate && destination.departureDate) {
                    arrivalStr = isoDateOnly(destination.arrivalDate);
                    departureStr = isoDateOnly(destination.departureDate);
                    currentIso = departureStr;
                } else {
                    arrivalStr = currentIso;
                    departureStr = addDaysIso(currentIso, destination.days || 1);
                    currentIso = departureStr;
                }

                const stopData = {
                    trip_id: tripId,
                    place_name: destination.city,
                    country: destination.country,
                    stop_order: i + 1,
                    arrival_date: arrivalStr,
                    departure_date: departureStr,
                    transport_from_last: formatStopTransport(destination),
                    activities: destination.activities ? destination.activities.join(', ') : null,
                    booking_url: destination.booking_url || null,
                    flight_availability_verified: destination.flight_availability_verified ?? null
                };

                const stopResponse = await fetch(base + '/api/trip-stops', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(stopData)
                });
                if (!stopResponse.ok) {
                    let rollbackFailed = false;
                    try {
                        const delRes = await fetch(base + '/api/planned-trips/' + tripId, { method: 'DELETE' });
                        rollbackFailed = !delRes.ok && delRes.status !== 404;
                    } catch (_) {
                        rollbackFailed = true;
                    }
                    let msg = planNewTripT('saveStopFailed', 'Failed to save stop {{n}} (HTTP {{status}})', {
                        n: i + 1,
                        status: stopResponse.status
                    });
                    if (rollbackFailed) {
                        msg += ' ' + planNewTripT(
                            'orphanTripHint',
                            'An empty trip may have been left in Planned Trips — delete it manually.'
                        );
                    }
                    throw new Error(msg);
                }
            }
        }

        if (typeof options.onSaved === 'function') {
            options.onSaved();
        }

        const goToPlannedTrips = function () {
            window.location.href = 'planned_trips.html';
        };

        if (typeof window.showModal === 'function') {
            window.showModal({
                title: planNewTripT('saveTrip', 'Save Trip'),
                message: planNewTripT('savedMessage', 'Trip saved successfully. You can find it under Planned Trips.'),
                type: 'success',
                onClose: goToPlannedTrips
            });
        } else {
            goToPlannedTrips();
        }

    } catch (error) {
        console.error('Error saving trip:', error);
        window.showError(planNewTripT('saveTripFailed', 'Failed to save trip: {{detail}}', {
            detail: error.message
        }));
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

export function showError(message, details, tripResults, resultsContainer, options = {}) {
    const retryText = planNewTripT('retryPlan', 'Retry');
    const errorLabel = planNewTripT('errorLabel', 'Error:');
    const showRetry = typeof options.onRetry === 'function';
    tripResults.innerHTML = `
        <div class="error-message">
            <p><strong>${escapeHtml(errorLabel)}</strong> ${escapeHtml(message)}</p>
            ${details ? `<p class="error-details">${escapeHtml(details)}</p>` : ''}
            ${showRetry ? `
                <div class="trip-actions trip-actions--error">
                    <button type="button" id="retryTripBtn" class="btn-add btn-add-outline">
                        ${escapeHtml(retryText)}
                    </button>
                </div>
            ` : ''}
        </div>
    `;
    resultsContainer.style.display = 'block';
    bindRetryButton(tripResults, options.onRetry);
}
