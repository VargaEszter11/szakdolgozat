import { displayResults, showError } from './tripRenderer.js';

const API_BASE_URL = 'http://localhost:8000';

//next: add visited/unvisited places as default values, date selection

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('visitedPlanForm');
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const startingCity = document.getElementById('startingCity').value.trim();
        const budget = parseInt(document.getElementById('budget').value);
        const travelLength = parseInt(document.getElementById('travelLength').value);
        const preferencesInput = document.getElementById('preferences').value.trim();
        const visitedPlacesInput = document.getElementById('visitedPlaces').value.trim();

        const preferences = preferencesInput
            ? preferencesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        const visitedPlaces = visitedPlacesInput
            ? visitedPlacesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        if (visitedPlaces.length === 0) {
            alert('Please enter at least one visited place.');
            return;
        }

        // Show loading state
        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        const originalBtnContent = generateBtn.innerHTML;
        generateBtn.textContent = 'Generating...';

        try {
            // Call the API
            const response = await fetch(`${API_BASE_URL}/generate_travel_plans/visited`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    startingPoint: startingCity,
                    budget: budget,
                    travelLength: travelLength,
                    preferences: preferences,
                    visitedPlaces: visitedPlaces
                })
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('API Response:', data);

            // Display results
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
