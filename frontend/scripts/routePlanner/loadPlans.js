(function () {
  function normalizeTrip(trip) {
    // Map API response fields to frontend fields
    // API provides: id, user_id, title, start_date, end_date, start_city, stops
    return {
      id: trip.id,
      destination: trip.title || 'Unknown destination',
      startDate: formatApiDate(trip.start_date),
      endDate: formatApiDate(trip.end_date),
      travelers: trip.stops ? trip.stops.length : 0, // Estimate from stops count
      status: 'Planning', // Default status (can be enhanced later)
      budget: '—', // Not in API yet
      accommodation: '—', // Not in API yet
      image: 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80' // Default image
    };
  }

  function formatApiDate(dateStr) {
    if (!dateStr) return '—';
    try {
      var d = new Date(dateStr);
      var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
      return months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
    } catch (e) {
      return dateStr;
    }
  }

  async function getTrips() {
    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.warn('No user_id found. User not logged in.');
      return [];
    }

    try {
      var apiUrl = 'http://localhost:8000/api/users/' + userId + '/planned-trips';
      var response = await fetch(apiUrl);
      
      if (!response.ok) {
        if (response.status === 404) {
          // No trips found for this user
          return [];
        }
        throw new Error('API request failed: ' + response.status);
      }

      var data = await response.json();
      // API returns array of planned trips directly
      var list = Array.isArray(data) ? data : [];
      return list.map(normalizeTrip);
    } catch (error) {
      console.error('Failed to load planned trips from API:', error);
      return [];
    }
  }

  async function deleteTrip(id) {
    try {
      var response = await fetch('http://localhost:8000/api/planned-trips/' + id, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete trip: ' + response.status);
      }

      alert('Trip deleted successfully');
      await render();
    } catch (error) {
      console.error('Error deleting trip:', error);
      alert('Failed to delete trip: ' + error.message);
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderCard(trip) {
    var statusClass = trip.status === 'Confirmed' ? 'trip-status trip-status-confirmed' : 'trip-status trip-status-planning';
    return (
      '<div class="trip-card card" data-id="' + trip.id + '">' +
      '<div class="trip-card-grid">' +
      '<div class="trip-card-image-wrap">' +
      '<img src="' + escapeHtml(trip.image || '') + '" alt="' + escapeHtml(trip.destination) + '" class="trip-card-image" onerror="this.style.background=\'var(--bg)\';this.src=\'\';">' +
      '<span class="' + statusClass + '">' + escapeHtml(trip.status) + '</span>' +
      '</div>' +
      '<div class="trip-card-content">' +
      '<div class="trip-card-header">' +
      '<div>' +
      '<div class="trip-card-dest">' +
      '<svg class="icon icon-pin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>' +
      '<h2 class="trip-card-title">' + escapeHtml(trip.destination) + '</h2>' +
      '</div>' +
      '<div class="trip-card-dates">' +
      '<svg class="icon icon-cal" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>' +
      '<span>' + escapeHtml(trip.startDate) + ' - ' + escapeHtml(trip.endDate) + '</span>' +
      '</div>' +
      '</div>' +
      '<div class="trip-card-actions">' +
      '<button type="button" class="trip-btn-icon trip-edit" data-id="' + trip.id + '" aria-label="Edit"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg></button>' +
      '<button type="button" class="trip-btn-icon trip-delete" data-id="' + trip.id + '" aria-label="Delete"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg></button>' +
      '</div>' +
      '</div>' +
      '<div class="trip-card-meta">' +
      '<div class="trip-meta-item">' +
      '<svg class="trip-meta-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>' +
      '<span class="trip-meta-label">Travelers</span>' +
      '<p class="trip-meta-value">' + (trip.travelers || 0) + ' people</p>' +
      '</div>' +
      '<div class="trip-meta-item">' +
      '<span class="trip-meta-label">Budget</span>' +
      '<p class="trip-meta-value">' + escapeHtml(trip.budget || '—') + '</p>' +
      '</div>' +
      '<div class="trip-meta-item">' +
      '<span class="trip-meta-label">Stay</span>' +
      '<p class="trip-meta-value">' + escapeHtml(trip.accommodation || '—') + '</p>' +
      '</div>' +
      '</div>' +
      '<div class="trip-card-buttons">' +
      '<a href="#" class="btn-trip btn-trip-primary">' + (window.i18n && window.i18n.t ? window.i18n.t('plannedTrips.viewDetails') : 'View Details') + '</a>' +
      '<button type="button" class="btn-trip btn-trip-secondary">' + (window.i18n && window.i18n.t ? window.i18n.t('plannedTrips.shareItinerary') : 'Share Itinerary') + '</button>' +
      '</div>' +
      '</div>' +
      '</div>' +
      '</div>'
    );
  }

  function sortTripsByStartDate(trips) {
    return trips.slice().sort(function (a, b) {
      var tA = a.startDate ? new Date(a.startDate).getTime() : 0;
      var tB = b.startDate ? new Date(b.startDate).getTime() : 0;
      return tA - tB;
    });
  }

  async function render() {
    var container = document.getElementById('tripCards');
    var emptyState = document.getElementById('emptyState');
    if (!container || !emptyState) return;

    var trips = await getTrips();
    var sortedTrips = sortTripsByStartDate(trips);
    
    if (sortedTrips.length === 0) {
      container.classList.add('hidden');
      emptyState.classList.remove('hidden');
      return;
    }

    emptyState.classList.add('hidden');
    container.classList.remove('hidden');
    container.innerHTML = sortedTrips.map(renderCard).join('');

    container.querySelectorAll('.trip-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-id'), 10);
        if (confirm('Delete this trip?')) deleteTrip(id);
      });
    });

    container.querySelectorAll('.trip-edit').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        window.location.href = 'plan_new_trip.html?edit=' + id;
      });
    });
  }

  document.addEventListener('DOMContentLoaded', render);
})();
