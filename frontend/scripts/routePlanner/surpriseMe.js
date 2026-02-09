const API_BASE_URL = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('randomTripForm');
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form values
        const startingCity = document.getElementById('startingCity').value.trim();
        const budget = parseInt(document.getElementById('budget').value);
        const travelLength = parseInt(document.getElementById('travelLength').value);
        const preferencesInput = document.getElementById('preferences').value.trim();
        
        // Parse preferences (comma-separated)
        const preferences = preferencesInput 
            ? preferencesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        // Show loading state
        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            // Call the API
            const response = await fetch(`${API_BASE_URL}/generate_travel_plans/random`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    startingPoint: startingCity,
                    budget: budget,
                    travelLength: travelLength,
                    preferences: preferences
                })
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('API Response:', data);

            // Display results
            displayResults(data);

        } catch (error) {
            console.error('Error generating trip:', error);
            tripResults.innerHTML = `
                <div class="error-message">
                    <p><strong>Error:</strong> Failed to generate trip. Please try again.</p>
                    <p class="error-details">${error.message}</p>
                </div>
            `;
            resultsContainer.style.display = 'block';
        } finally {
            // Hide loading state
            loadingState.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = `
                <svg class="icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                Generate Random Trip
            `;
        }
    });
});

function displayResults(data) {
    const tripResults = document.getElementById('tripResults');
    const resultsContainer = document.getElementById('resultsContainer');

    if (!data.draft_plan) {
        tripResults.innerHTML = '<p class="error-message">No trip plan was generated. Please try again.</p>';
        resultsContainer.style.display = 'block';
        return;
    }

    let html = '';

    // Check if we have multiple trips (random endpoint returns multiple options)
    if (data.draft_plan.selected_trip) {
        // Selected trip + all options
        html += renderSelectedTrip(data.draft_plan.selected_trip, data.validation);
        
        if (data.draft_plan.all_trips && data.draft_plan.all_trips.length > 1) {
            html += '<h4 class="other-options-title">Other Options:</h4>';
            data.draft_plan.all_trips.forEach((trip, index) => {
                if (index > 0) { // Skip the first one (selected trip)
                    const validation = data.draft_plan.validations?.[index];
                    html += renderTripOption(trip, index, validation);
                }
            });
        }
    } else if (data.draft_plan.trips) {
        // Multiple trips without selection
        data.draft_plan.trips.forEach((trip, index) => {
            html += renderTripOption(trip, index);
        });
    } else {
        // Single trip
        html += renderTripDetails(data.draft_plan, data.validation);
    }

    tripResults.innerHTML = html;
    resultsContainer.style.display = 'block';
}

function renderSelectedTrip(trip, validation) {
    return `
        <div class="trip-card selected-trip">
            <div class="trip-badge">Best Match</div>
            ${renderTripDetails(trip, validation)}
        </div>
    `;
}

function renderTripOption(trip, index, validation) {
    return `
        <div class="trip-card trip-option">
            <h4 class="trip-option-title">Option ${index + 1}</h4>
            ${renderTripDetails(trip, validation)}
        </div>
    `;
}

function renderTripDetails(trip, validation) {
    let html = `
        <div class="trip-header">
            <h3>${trip.startingPoint || 'Your Trip'}</h3>
            <span class="trip-length">${trip.tripLengthDays || 0} days</span>
        </div>
    `;

    // Validation info
    if (validation) {
        const statusClass = validation.valid ? 'valid' : 'invalid';
        html += `
            <div class="validation-info ${statusClass}">
                <p><strong>Status:</strong> ${validation.valid ? '✓ Within Budget' : '✗ Over Budget'}</p>
                <p><strong>Estimated Cost:</strong> €${validation.total_price || 0}</p>
                <p><strong>Score:</strong> ${validation.score || 0}/100</p>
                ${validation.reason ? `<p class="validation-reason">${validation.reason}</p>` : ''}
            </div>
        `;
    }

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
