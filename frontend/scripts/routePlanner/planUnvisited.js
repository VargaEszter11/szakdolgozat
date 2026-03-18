import { displayResults, showError } from './tripRenderer.js';

const API_BASE_URL = window.API_BASE_URL || '';

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('unvisitedPlanForm');
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');
    // Fetch visited places from database to exclude automatically on submit
    let savedVisitedPlaces = [];
    const userId = localStorage.getItem('user_id');
    if (userId) {
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

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const startingCity = document.getElementById('startingCity').value.trim();
        const budget = parseInt(document.getElementById('budget').value);
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const preferencesInput = document.getElementById('preferences').value.trim();
        const visitedPlacesInput = document.getElementById('visitedPlaces').value.trim();

        const preferences = preferencesInput
            ? preferencesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        const manualPlaces = visitedPlacesInput
            ? visitedPlacesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];
        const visitedPlaces = [...new Set([...savedVisitedPlaces, ...manualPlaces])];

        if (!startDate || !endDate) {
            showError('Please select both start and end dates.', '', tripResults, resultsContainer);
            return;
        }
        if (endDate <= startDate) {
            showError('End date must be after start date.', '', tripResults, resultsContainer);
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
            const response = await fetch(`${API_BASE_URL}/generate_travel_plans/unvisited`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    startingPoint: startingCity,
                    budget: budget,
                    startDate: startDate,
                    endDate: endDate,
                    preferences: preferences,
                    visitedPlaces: visitedPlaces,
                    language: localStorage.getItem('language') || 'en'
                })
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('API Response:', data);

            data.userStartDate = startDate;
            data.userEndDate = endDate;
            displayResults(data, tripResults, resultsContainer);

        } catch (error) {
            console.error('Error generating trip:', error);
            showError('Failed to generate trip. Please try again.', error.message, tripResults, resultsContainer);
        } finally {
            // Hide loading state
            loadingState.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalBtnContent;
        }
    });
});
