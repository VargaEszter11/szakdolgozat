(function () {
  var lastPlaces = [];

  var F = window.PlaceFormatHelpers;
  var t = F.t;
  var tpl = F.tpl;
  var escapeHtml = F.escapeHtml;
  var starsHtml = F.starsHtml;
  var normalizePlace = F.normalizePlace;

  // One place card HTML
  function renderCard(place) {
    return (
      '<div class="travel-log-card visited-place-card" data-id="' + escapeHtml(place.id) + '">' +

      '<div class="log-image-wrapper">' +
      '<img src="' + escapeHtml(place.image) + '" ' +
      'alt="' + escapeHtml(place.name) + '" ' +
      'class="log-image" ' +
      'onerror="this.src=\'' + escapeHtml(F.DEFAULT_IMAGE) + '\';">' +
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
      '<div class="place-stars" role="img" aria-label="' +
      escapeHtml(String(place.rating || 0) + ' / 5') +
      '">' + starsHtml(place.rating) + '</div>' +
      '<button type="button" class="place-edit-btn" data-id="' + escapeHtml(place.id) + '" title="' + escapeHtml(t('visitedPlaces.editPlace', 'Edit place')) + '" aria-label="' + escapeHtml(t('visitedPlaces.editPlace', 'Edit place')) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 20h9"/>' +
      '<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/>' +
      '</svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn" data-id="' + escapeHtml(place.id) + '" title="' + escapeHtml(t('visitedPlaces.deletePlace', 'Delete place')) + '" aria-label="' + escapeHtml(t('visitedPlaces.deletePlace', 'Delete place')) + '">' +
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
      escapeHtml(place.description || t('visitedPlaces.noDescription', 'No description.')) +
      '</p>' +

      '</div>' +
      '</div>'
    );
  }

  // List: click handlers, sort, render, fetch
  function bindPlaceCardActions() {
    var container = document.getElementById('placeCards');
    if (!container || container.dataset.placeActionsBound === '1') return;
    container.dataset.placeActionsBound = '1';
    container.addEventListener('click', function (e) {
      var editBtn = e.target.closest('.place-edit-btn');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        var editId = editBtn.getAttribute('data-id');
        window.PlaceEditModal.openEditPlaceModal(editId);
        return;
      }
      var delBtn = e.target.closest('.place-delete-btn');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        var raw = delBtn.getAttribute('data-id');
        var delId = parseInt(raw, 10);
        if (raw == null || String(raw).trim() === '' || Number.isNaN(delId)) {
          showError(t('visitedPlaces.deleteInvalid', 'Cannot delete this place.'));
          return;
        }
        showConfirm(t('visitedPlaces.deleteConfirm', 'Are you sure you want to delete this place?'), function () {
          window.PlaceEditModal.deletePlace(delId);
        });
        return;
      }
      var card = e.target.closest('.visited-place-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) window.PlaceDetailsModal.show(cid);
      }
    });
  }

  // Newest visit first
  function sortByVisitDate(places) {
    return places.slice().sort(function (a, b) {
      return (b.dateSortKey || 0) - (a.dateSortKey || 0);
    });
  }

  // Cards
  function render(places) {
    var container = document.getElementById('placeCards');
    var countEl = document.getElementById('placeCount');
    if (!container) {
      if (window.markAppReady) window.markAppReady();
      return;
    }

    var sorted = sortByVisitDate(places);
    lastPlaces = sorted;
    if (countEl) countEl.textContent = sorted.length;

    var tEmpty = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
    container.innerHTML = sorted.length
      ? sorted.map(renderCard).join('')
      : '<div class="place-cards-empty">' +
        '<p>' + (tEmpty('visitedPlaces.emptyText') || 'No places yet.') + '</p>' +
        '<a href="/places/new" class="btn-add">' +
        '<svg class="icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" ' +
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<circle cx="12" cy="12" r="10" />' +
        '<path d="M12 8v8" />' +
        '<path d="M8 12h8" />' +
        '</svg>' +
        '<span>' + (tEmpty('visitedPlaces.addFirstPlace') || 'Add your first place') + '</span>' +
        '</a>' +
        '</div>';
    if (window.markAppReady) window.markAppReady();
  }

  // Fetch user's places from API
  function loadPlaces() {
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      var container = document.getElementById('placeCards');
      if (container) {
        container.innerHTML = '<p class="place-cards-empty">' +
          tpl(t('visitedPlaces.loginRequiredHtml', 'Please log in to view your places. <a href="{{href}}">Log in here</a>.'), {
            href: '/login'
          }) +
          '</p>';
      }
      if (window.markAppReady) window.markAppReady();
      return Promise.resolve();
    }

    var apiUrl = '/api/visited-places';
    return fetch(apiUrl)
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
        var container = document.getElementById('placeCards');
        if (container) {
          container.innerHTML = '<p class="place-cards-empty">' +
            escapeHtml(t('visitedPlaces.loadFailed', 'Failed to load places. Please try again later.')) +
            '</p>';
        }
        if (window.markAppReady) window.markAppReady();
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.PlaceEditModal.init({
      getPlaces: function () { return lastPlaces; },
      refreshList: loadPlaces
    });
    bindPlaceCardActions();
    loadPlaces();
  });
})();
