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

  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long' });
  }

  function starsHtml(placeId, rating) {
    rating = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    var html = '';
    for (var i = 1; i <= 5; i++) {
      var filled = i <= rating ? ' place-star-filled' : '';
      html += '<button type="button" class="place-star-btn' + filled + '" data-place-id="' +
        escapeHtml(placeId) + '" data-value="' + i + '" aria-label="Rate ' + i + ' out of 5 stars">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
        '</button>';
    }
    return html;
  }

  function normalizePlace(item, index) {
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
      coordinates: item.coordinates || null
    };
  }

  function renderCard(place) {
    return (
      '<div class="travel-log-card" data-id="' + escapeHtml(place.id) + '">' +

      '<div class="log-image-wrapper">' +
      '<img src="' + escapeHtml(place.image) + '" ' +
      'alt="' + escapeHtml(place.name) + '" ' +
      'class="log-image" ' +
      'onerror="this.src=\'' + escapeHtml(DEFAULT_IMAGE) + '\';">' +
      '</div>' +

      '<div class="log-content">' +

      '<div class="log-header">' +

      '<div class="log-dest">' +
      '<svg class="icon-pin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 21s-6-5.686-6-10a6 6 0 1 1 12 0c0 4.314-6 10-6 10z"/>' +
      '<circle cx="12" cy="11" r="2"/>' +
      '</svg>' +
      '<h3 class="log-title">' + escapeHtml(place.name) + '</h3>' +
      '</div>' +

      '<div class="visited-places-card-actions">' +
      '<div class="place-stars" role="group" aria-label="Rating">' + starsHtml(place.id, place.rating) + '</div>' +
      '<button type="button" class="place-delete-btn" data-id="' + escapeHtml(place.id) + '" title="Delete" aria-label="Delete place">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M3 6h18"/>' +
      '<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>' +
      '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>' +
      '<line x1="10" x2="10" y1="11" y2="17"/>' +
      '<line x1="14" x2="14" y1="11" y2="17"/>' +
      '</svg>' +
      '</button>' +
      '</div>' +

      '</div>' +

      '<div class="log-date">' + escapeHtml(place.date) + '</div>' +

      '<p class="log-notes">' +
      escapeHtml(place.description || 'No description.') +
      '</p>' +

      '</div>' +
      '</div>'
    );
  }

  function deletePlace(id) {
    fetch('/api/visited-places/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to delete: ' + res.status);
        loadPlaces();
      })
      .catch(function (err) {
        console.error('Error deleting place:', err);
        showError('Failed to delete place. Please try again.');
      });
  }

  function updateRating(placeId, rating) {
    fetch('/api/visited-places/' + placeId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating: rating })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to update rating: ' + res.status);
        return res.json();
      })
      .then(function () {
        loadPlaces();
      })
      .catch(function (err) {
        console.error('Error updating rating:', err);
        showError('Failed to update rating. Please try again.');
      });
  }

  function bindPlaceCardActions() {
    var container = document.getElementById('placeCards');
    if (!container || container.dataset.placeActionsBound === '1') return;
    container.dataset.placeActionsBound = '1';
    container.addEventListener('click', function (e) {
      var delBtn = e.target.closest('.place-delete-btn');
      if (delBtn) {
        e.preventDefault();
        var delId = parseInt(delBtn.getAttribute('data-id'), 10);
        if (isNaN(delId)) {
          showError('Cannot delete this place.');
          return;
        }
        showConfirm('Are you sure you want to delete this place?', function () {
          deletePlace(delId);
        });
        return;
      }
      var starBtn = e.target.closest('.place-star-btn');
      if (starBtn) {
        e.preventDefault();
        var pid = parseInt(starBtn.getAttribute('data-place-id'), 10);
        var val = parseInt(starBtn.getAttribute('data-value'), 10);
        if (isNaN(pid) || isNaN(val)) return;
        updateRating(pid, val);
      }
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
  }

  function loadPlaces() {
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.error('No user_id found. Please log in.');
      var container = document.getElementById('placeCards');
      if (container) {
        container.innerHTML = '<p class="place-cards-empty">Please log in to view your places. <a href="../loginRegister/loginPage.html">Log in here</a>.</p>';
      }
      return;
    }

    var apiUrl = '/api/users/' + userId + '/visited-places';
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

  document.addEventListener('DOMContentLoaded', function () {
    bindPlaceCardActions();
    loadPlaces();
  });
})();
