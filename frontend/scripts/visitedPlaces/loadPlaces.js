//next: reduce redundant API calls

(function () {
  var STORAGE_KEY = 'visitedPlaces';
  var DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80';

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

  function starsHtml(rating) {
    rating = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    var html = '';
    for (var i = 0; i < 5; i++) {
      var filled = i < rating ? ' place-star-filled' : '';
      html += '<span class="place-star' + filled + '" aria-hidden="true">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
        '</span>';
    }
    return html;
  }

  function normalizePlace(item, index) {
    // API response uses: place_name, country, date, rating, description
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var d = dateValue ? new Date(dateValue) : null;
    var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
    return {
      id: item.id || (placeName + '-' + (dateValue || '') + '-' + index),
      name: name,
      date: formatDate(dateValue),
      dateSortKey: dateSortKey,
      rating: item.rating != null ? item.rating : 5,
      description: item.description || item.notes || '',
      image: item.image || DEFAULT_IMAGE,
      coordinates: item.coordinates || null  // Include coordinates if available
    };
  }

  function renderCard(place) {
    return (
      '<div class="place-card card" data-id="' + escapeHtml(place.id) + '">' +
      '<div class="place-card-image-wrap">' +
      '<img src="' + escapeHtml(place.image) + '" alt="' + escapeHtml(place.name) + '" class="place-card-image" onerror="this.src=\'' + escapeHtml(DEFAULT_IMAGE) + '\';">' +
      '</div>' +
      '<div class="place-card-content">' +
      '<div class="place-card-header">' +
      '<div class="place-card-name">' +
      '<svg class="icon icon-pin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>' +
      '<h2 class="place-card-title">' + escapeHtml(place.name) + '</h2>' +
      '</div>' +
      '<div style="display:flex;align-items:center;gap:8px;">' +
      '<div class="place-stars">' + starsHtml(place.rating) + '</div>' +
      '<button type="button" class="place-delete-btn" data-id="' + escapeHtml(place.id) + '" aria-label="Delete" title="Delete place">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>' +
      '</button>' +
      '</div>' +
      '</div>' +
      '<div class="place-card-date">' +
      '<svg class="icon icon-cal" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>' +
      '<span>' + escapeHtml(place.date) + '</span>' +
      '</div>' +
      '<p class="place-card-description">' + escapeHtml(place.description || 'No description.') + '</p>' +
      '</div>' +
      '</div>'
    );
  }

  function deletePlace(id) {
    fetch('http://localhost:8000/api/visited-places/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to delete: ' + res.status);
        loadPlaces();
      })
      .catch(function (err) {
        console.error('Error deleting place:', err);
        showError('Failed to delete place. Please try again.');
      });
  }

  function getPlacesFromStorage() {
    var list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return list.map(function (item, index) {
      var p = normalizePlace(item, index);
      if (!p.id || String(p.id).indexOf('-') === -1) p.id = 'place-' + index;
      return p;
    });
  }

  function sortByVisitDate(places) {
    return places.slice().sort(function (a, b) {
      return (b.dateSortKey || 0) - (a.dateSortKey || 0);
    });
  }

  function render(places) {
    var container = document.getElementById('placeCards');
    var countEl = document.getElementById('placeCount');
    if (!container) return;

    var sorted = sortByVisitDate(places);
    if (countEl) countEl.textContent = sorted.length;

    var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
    var emptyHtml = (t('visitedPlaces.emptyText') || 'No places yet.') + ' <a href="add_new_place.html">' + (t('visitedPlaces.addFirstPlace') || 'Add your first place') + '</a>.';
    container.innerHTML = sorted.length
      ? sorted.map(renderCard).join('')
      : '<p class="place-cards-empty">' + emptyHtml + '</p>';

    container.querySelectorAll('.place-delete-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-id'), 10);
        showConfirm('Are you sure you want to delete this place?', function () {
          deletePlace(id);
        });
      });
    });
  }

  function loadPlaces() {
    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.error('No user_id found. Please log in.');
      var container = document.getElementById('placeCards');
      if (container) {
        container.innerHTML = '<p class="place-cards-empty">Please log in to view your places. <a href="../loginRegister/loginPage.html">Log in here</a>.</p>';
      }
      return;
    }

    var apiUrl = 'http://localhost:8000/api/users/' + userId + '/visited-places';
    fetch(apiUrl)
      .then(function (res) {
        if (!res.ok) {
          if (res.status === 404) {
            render([]);
            return null;
          }
          throw new Error('API request failed: ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (data === null) return;
        var list = Array.isArray(data) ? data : [];
        var places = list.map(function (item, index) {
          return normalizePlace(item, index);
        });
        render(places);
      })
      .catch(function (err) {
        console.error('Failed to load visited places from API:', err);
        var container = document.getElementById('placeCards');
        if (container) {
          container.innerHTML = '<p class="place-cards-empty">Failed to load places. Please try again later.</p>';
        }
      });
  }

  document.addEventListener('DOMContentLoaded', loadPlaces);
})();
