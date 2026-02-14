(function () {
  var STORAGE_KEY = 'visitedPlaces';
  var LAST_N = 2;
  var JSON_URL = '../../../dummy_places/places.json';

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function normalizePlace(item) {
    // API response uses: place_name, country, date, description
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var d = dateValue ? new Date(dateValue) : null;
    var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
    return {
      name: name,
      date: formatDate(dateValue),
      dateSortKey: dateSortKey,
      description: item.description || item.notes || ''
    };
  }

  function renderLogCard(place) {
    return (
      '<article class="log-card">' +
      '<div class="log-header">' +
      '<div class="log-dest">' +
      '<svg class="icon icon-pin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>' +
      '<h3 class="log-title">' + escapeHtml(place.name) + '</h3>' +
      '</div>' +
      '<span class="log-date">' + escapeHtml(place.date) + '</span>' +
      '</div>' +
      '<p class="log-notes">' + escapeHtml(place.description || 'No notes.') + '</p>' +
      '</article>'
    );
  }

  function getPlacesFromStorage() {
    var list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return list.map(normalizePlace);
  }

  function render(places) {
    var container = document.getElementById('mainTravelLogs');
    if (!container) return;

    places.sort(function (a, b) { return (a.dateSortKey || 0) - (b.dateSortKey || 0); });
    var lastTwo = places.slice(-LAST_N);

    if (lastTwo.length === 0) {
      var msg = (window.i18n && window.i18n.t('mainPage.noTravelsYet')) || 'No travels yet. <a href="visitedPlaces/add_new_place.html">Add your first place</a>.';
      container.innerHTML = '<p class="travel-logs-empty muted">' + msg + '</p>';
      return;
    }

    container.innerHTML = lastTwo.map(renderLogCard).join('');
  }

  function loadTravelLog() {
    var container = document.getElementById('mainTravelLogs');
    if (!container) return;

    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.warn('No user_id found. User not logged in.');
      var msg = 'Please <a href="pages/loginRegister/loginPage.html">log in</a> to see your travel log.';
      container.innerHTML = '<p class="travel-logs-empty muted">' + msg + '</p>';
      return;
    }

    var apiUrl = 'http://localhost:8000/api/users/' + userId + '/visited-places';
    fetch(apiUrl)
      .then(function (res) {
        if (!res.ok) {
          if (res.status === 404) {
            // No places found for this user
            render([]);
            return null;
          }
          throw new Error('API request failed: ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (data === null) return; // Already handled 404
        // API returns array of visited places directly
        var list = Array.isArray(data) ? data : [];
        var places = list.map(normalizePlace);
        render(places);
      })
      .catch(function (err) {
        console.error('Failed to load travel log from API:', err);
        var msg = 'Failed to load travel log. Please try again later.';
        container.innerHTML = '<p class="travel-logs-empty muted">' + msg + '</p>';
      });
  }

  document.addEventListener('DOMContentLoaded', loadTravelLog);
})();
