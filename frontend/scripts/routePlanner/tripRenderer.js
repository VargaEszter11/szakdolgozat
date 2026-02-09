export function displayResults(data, tripResults, resultsContainer) {
    if (!data.draft_plan) {
        tripResults.innerHTML = '<p class="error-message">No trip plan was generated. Please try again.</p>';
        resultsContainer.style.display = 'block';
        return;
    }

    const html = renderTripDetails(data.draft_plan, data.validation);

    tripResults.innerHTML = html;
    resultsContainer.style.display = 'block';
}

export function renderTripDetails(trip, validation) {
    let html = `
        <div class="trip-header">
            <h3>${trip.startingPoint || 'Your Trip'}</h3>
            <span class="trip-length">${trip.tripLengthDays || 0} days</span>
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
                            <strong>Days:</strong> ${destination.days} | 
                            <strong>Transport:</strong> ${destination.transportFromPreviousCity || 'N/A'}
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

    return html;
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
