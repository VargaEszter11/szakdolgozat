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
    var placeName = item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.visitedDate || item.dateVisited || item.date;
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
      container.innerHTML = '<p class="travel-logs-empty muted">No travels yet. <a href="visitedPlaces/add_new_place.html">Add your first place</a>.</p>';
      return;
    }

    container.innerHTML = lastTwo.map(renderLogCard).join('');
  }

  function loadTravelLog() {
    var container = document.getElementById('mainTravelLogs');
    if (!container) return;

    fetch(JSON_URL)
      .then(function (res) {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then(function (data) {
        var list = data && data.places ? data.places : [];
        var places = list.map(normalizePlace);
        render(places);
      })
      .catch(function (err) {
        console.warn('Could not load places.json for travel log, falling back to localStorage:', err);
        render(getPlacesFromStorage());
      });
  }

  document.addEventListener('DOMContentLoaded', loadTravelLog);
})();
