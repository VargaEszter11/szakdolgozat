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

export function displayResults(data, tripResults, resultsContainer) {
    if (!data.draft_plan) {
        tripResults.innerHTML = '<p class="error-message">No trip plan was generated. Please try again.</p>';
        resultsContainer.style.display = 'block';
        return;
    }

    const html = renderTripDetails(data.draft_plan, data.validation);

    tripResults.innerHTML = html;
    resultsContainer.style.display = 'block';

    const saveTripBtn = tripResults.querySelector('#saveTripBtn');
    if (saveTripBtn) {
        saveTripBtn.addEventListener('click', async () => {
            await saveTripToDatabase(data.draft_plan, saveTripBtn, data.userStartDate, data.userEndDate);
        });
    }
}

export function renderTripDetails(trip, validation) {
    const dateRange = trip.startDate && trip.endDate
        ? `${formatDate(trip.startDate)} — ${formatDate(trip.endDate)}`
        : `${trip.tripLengthDays || 0} days`;
    let html = `
        <div class="trip-header">
            <h3>${trip.startingPoint || 'Your Trip'}</h3>
            <span class="trip-length">${dateRange}</span>
        </div>
    `;

    // Trip plan
    if (trip.plan && Array.isArray(trip.plan)) {
        html += '<div class="trip-destinations">';
        trip.plan.forEach((destination, idx) => {
            html += `
                <div class="destination-card">
                    <div class="destination-number">${idx + 1}</div>
                    <div class="destination-details">
                        <h4 class="destination-city">${destination.city}, ${destination.country}</h4>
                        <p class="destination-info">
                            ${destination.arrivalDate && destination.departureDate
                                ? `<strong>Dates:</strong> ${formatDate(destination.arrivalDate)} → ${formatDate(destination.departureDate)} (${destination.days} days)`
                                : `<strong>Days:</strong> ${destination.days}`}
                             | <strong>Transport:</strong> ${destination.transportFromPreviousCity || 'N/A'}
                            ${destination.iata ? ` | <strong>Airport:</strong> ${destination.iata}` : ''}
                        </p>
                        ${destination.activities && destination.activities.length > 0 ? `
                            <div class="activities">
                                <strong>Activities:</strong>
                                <ul>
                                    ${destination.activities.map(activity => `<li>${activity}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }

    // Save trip button
    html += `
        <div class="trip-actions" style="margin-top: 2rem; text-align: center;">
            <button id="saveTripBtn" class="btn-add" style="padding: 0.75rem 2rem;">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                    <polyline points="17 21 17 13 7 13 7 21"/>
                    <polyline points="7 3 7 8 15 8"/>
                </svg>
                Save Trip to My Trips
            </button>
        </div>
    `;

    return html;
}

async function saveTripToDatabase(trip, button, userStartDate, userEndDate) {
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

        const tripData = {
            user_id: parseInt(userId),
            title: trip.startingPoint || 'My Trip',
            start_date: startDate.toISOString().split('T')[0],
            end_date: endDate.toISOString().split('T')[0],
            start_city: trip.startingPoint || null
        };

        const tripResponse = await fetch('/api/planned-trips', {
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
                    transport_from_last: destination.transportFromPreviousCity || null,
                    activities: destination.activities ? destination.activities.join(', ') : null
                };

                await fetch('/api/trip-stops', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(stopData)
                });
            }
        }

        button.textContent = 'Saved ✓';
        button.style.backgroundColor = 'var(--success, #22c55e)';
        window.showSuccess('Trip saved successfully!', function () {
            window.location.href = 'planned_trips.html';
        });

    } catch (error) {
        console.error('Error saving trip:', error);
        window.showError('Failed to save trip: ' + error.message);
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

export function showError(message, details, tripResults, resultsContainer) {
    tripResults.innerHTML = `
        <div class="error-message">
            <p><strong>Error:</strong> ${message}</p>
            ${details ? `<p class="error-details">${details}</p>` : ''}
        </div>
    `;
    resultsContainer.style.display = 'block';
}
