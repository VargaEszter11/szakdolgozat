import { displayResults, showError } from './tripRenderer.js';

const API_BASE_URL = '';

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('randomTripForm');
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const tripResults = document.getElementById('tripResults');
    const generateBtn = document.getElementById('generateBtn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const startingCity = document.getElementById('startingCity').value.trim();
        const budget = parseInt(document.getElementById('budget').value);
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const preferencesInput = document.getElementById('preferences').value.trim();
        
        // Parse preferences (comma-separated)
        const preferences = preferencesInput 
            ? preferencesInput.split(',').map(p => p.trim()).filter(p => p)
            : [];

        // Show loading state
        loadingState.style.display = 'block';
        resultsContainer.style.display = 'none';
        generateBtn.disabled = true;
        const originalBtnContent = generateBtn.innerHTML;
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
                    startDate: startDate,
                    endDate: endDate,
                    preferences: preferences
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
