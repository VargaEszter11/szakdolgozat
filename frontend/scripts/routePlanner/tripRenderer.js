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

function transportLabel(transport) {
    if (!transport) return 'N/A';
    const key = String(transport).trim().toLowerCase();
    const label = window.i18n && window.i18n.t
        ? window.i18n.t(`plannedTrips.transportTypes.${key}`)
        : null;
    return label && !label.startsWith('plannedTrips.') ? label : transport;
}

function formatStopTransport(destination) {
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
    if (!city || !checkin || !checkout || checkin === checkout) return null;
    const params = new URLSearchParams({
        ss: [city, country].filter(Boolean).join(', '),
        checkin: checkin,
        checkout: checkout,
        group_adults: String(Math.max(1, parseInt(people, 10) || 1)),
        no_rooms: '1',
        group_children: '0'
    });
    return `https://www.booking.com/searchresults.html?${params.toString()}`;
}

export function displayResults(data, tripResults, resultsContainer, options = {}) {
    if (!data.draft_plan) {
        tripResults.innerHTML = '<p class="error-message">No trip plan was generated. Please try again.</p>';
        resultsContainer.style.display = 'block';
        bindRetryButton(tripResults, options.onRetry);
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
        : `${trip.tripLengthDays || 0} days`;
    const heading = (tripTitle && String(tripTitle).trim())
        || trip.startingPoint
        || 'Your Trip';

    let html = `
        <div class="trip-header">
            <h3>${escapeHtml(heading)}</h3>
            <span class="trip-length">${dateRange}</span>
        </div>
    `;

    if (Array.isArray(trip.requestedPlacesMissing) && trip.requestedPlacesMissing.length) {
        html += `
            <p class="error-message">
                Could not include these requested places with the current route data:
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
            const accommodationUrl = accommodationBookingUrl(
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
                    ? `<strong>${window.i18n.t('plannedTrips.dates')}:</strong> ${formatDate(destination.arrivalDate)} → ${formatDate(destination.departureDate)}`
                    : `<strong>${window.i18n.t('plannedTrips.days')}:</strong> ${destination.days}`}
                             | <strong>${window.i18n.t('plannedTrips.transport')}:</strong> ${escapeHtml(formatStopTransport(destination))}
                        </p>
                        ${destination.booking_url || accommodationUrl ? `
                            <div class="trip-stop-actions">
                                ${destination.booking_url ? `
                                    <a class="btn-add trip-stop-action-link" href="${escapeHtml(destination.booking_url)}" target="_blank" rel="noopener noreferrer">
                                        ${destination.flight_availability_verified ? window.i18n.t('plannedTrips.bookThisFlight') : window.i18n.t('plannedTrips.checkFlightAvailability')}
                                    </a>
                                ` : ''}
                                ${accommodationUrl ? `
                                    <a class="btn-add trip-stop-action-link" href="${escapeHtml(accommodationUrl)}" target="_blank" rel="noopener noreferrer">
                                        ${window.i18n.t('plannedTrips.findAccommodation')}
                                    </a>
                                ` : ''}
                            </div>
                        ` : ''}
                        ${destination.activities && destination.activities.length > 0 ? `
                            <div class="activities">
                                <strong>${window.i18n.t('plannedTrips.suggestedActivities')}:</strong>
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
    const t = window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t.bind(window.i18n) : null;
    const saveLabel = t ? t('planNewTrip.saveTrip') : 'Save Trip';
    const retryLabel = t ? t('planNewTrip.retryPlan') : 'Retry';
    html += `
        <div class="trip-actions">
            <button type="button" id="retryTripBtn" class="btn-add btn-add-outline">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <polyline points="23 4 23 10 17 10"/>
                    <polyline points="1 20 1 14 7 14"/>
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
                ${escapeHtml(retryLabel && !String(retryLabel).startsWith('planNewTrip.') ? retryLabel : 'Retry')}
            </button>
            <button type="button" id="saveTripBtn" class="btn-add">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                    <polyline points="17 21 17 13 7 13 7 21"/>
                    <polyline points="7 3 7 8 15 8"/>
                </svg>
                ${escapeHtml(saveLabel && !String(saveLabel).startsWith('planNewTrip.') ? saveLabel : 'Save Trip')}
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
    const userId = localStorage.getItem('user_id');
    if (!userId) {
        window.showError('Please log in to save trips.', function () {
            window.location.href = '../loginRegister/loginPage.html';
        });
        return;
    }

    const originalText = button.innerHTML;
    button.disabled = true;
    button.textContent = 'Saving...';

    try {
        const startDate = userStartDate ? new Date(userStartDate) : new Date();
        const endDate = userEndDate ? new Date(userEndDate) : new Date(startDate.getTime() + (trip.tripLengthDays || 0) * 86400000);

        const customTitle = options.tripTitle && String(options.tripTitle).trim();
        const tripData = {
            user_id: parseInt(userId),
            title: customTitle || trip.startingPoint || 'My Trip',
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0],
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
            throw new Error('Failed to create trip');
        }

        const createdTrip = await tripResponse.json();
        const tripId = createdTrip.id;

        if (trip.plan && Array.isArray(trip.plan)) {
            let currentDate = new Date(startDate.getTime());

            for (let i = 0; i < trip.plan.length; i++) {
                const destination = trip.plan[i];
                let arrivalStr, departureStr;

                if (destination.arrivalDate && destination.departureDate) {
                    arrivalStr = destination.arrivalDate;
                    departureStr = destination.departureDate;
                    currentDate = new Date(destination.departureDate);
                } else {
                    arrivalStr = currentDate.toISOString().split('T')[0];
                    currentDate.setDate(currentDate.getDate() + (destination.days || 1));
                    departureStr = currentDate.toISOString().split('T')[0];
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

                await fetch(base + '/api/trip-stops', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(stopData)
                });
            }
        }

        if (typeof options.onSaved === 'function') {
            options.onSaved();
        }

        if (typeof window.showModal === 'function') {
            window.showModal({
                title: (window.i18n && window.i18n.t('planNewTrip.saveTrip')) || 'Save Trip',
                message: (window.i18n && window.i18n.t('planNewTrip.savedMessage')) || 'Trip saved successfully.',
                type: 'success'
            });
        } else if (typeof window.showError === 'function') {
            // fallback: avoid leaving user without feedback
            console.info('Trip saved successfully.');
        }

    } catch (error) {
        console.error('Error saving trip:', error);
        window.showError('Failed to save trip: ' + error.message);
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

export function showError(message, details, tripResults, resultsContainer, options = {}) {
    const t = window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t.bind(window.i18n) : null;
    const retryLabel = t ? t('planNewTrip.retryPlan') : 'Retry';
    const retryText = retryLabel && !String(retryLabel).startsWith('planNewTrip.') ? retryLabel : 'Retry';
    const showRetry = typeof options.onRetry === 'function';
    tripResults.innerHTML = `
        <div class="error-message">
            <p><strong>Error:</strong> ${escapeHtml(message)}</p>
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
