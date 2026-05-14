(function () {
  var DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80';

  function normalizeTrip(trip) {
    // Map API response fields to frontend fields
    // API provides: id, user_id, title, start_date, end_date, start_city, stops
    return {
      id: trip.id,
      destination: trip.title || 'Unknown destination',
      startDate: formatApiDate(trip.start_date),
      endDate: formatApiDate(trip.end_date),
      startDateSort: trip.start_date || null,
      stopCount: trip.stops ? trip.stops.length : 0,
      image: DEFAULT_IMAGE
    };
  }

  function stopsSummaryLine(n) {
    var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : null;
    if (n === 1) return t ? t('plannedTrips.stopsOne') : '1 stop';
    return t ? t('plannedTrips.stopsMany').replace(/\{\{n\}\}/g, String(n)) : (n + ' stops');
  }

  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function formatApiDate(dateStr) {
    if (!dateStr) return '—';
    try {
      var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
      return new Date(dateStr).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
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
      var apiUrl = '/api/users/' + userId + '/planned-trips';
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
      var response = await fetch('/api/planned-trips/' + id, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete trip: ' + response.status);
      }

      await render();
    } catch (error) {
      console.error('Error deleting trip:', error);
      showError('Failed to delete trip: ' + error.message);
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderCard(trip) {
    return (
      '<div class="travel-log-card planned-trip-card" data-id="' + trip.id + '">' +
      '<div class="log-image-wrapper">' +
      '<img src="' + escapeHtml(trip.image || '') + '" alt="' + escapeHtml(trip.destination) + '" class="log-image" onerror="this.src=\'' + escapeHtml(DEFAULT_IMAGE) + '\';">' +
      '</div>' +
      '<div class="log-content">' +
      '<div class="log-header">' +
      '<div class="log-dest">' +
      '<svg class="icon-pin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 21s-6-5.686-6-10a6 6 0 1 1 12 0c0 4.314-6 10-6 10z"/>' +
      '<circle cx="12" cy="11" r="2"/>' +
      '</svg>' +
      '<h3 class="log-title">' + escapeHtml(trip.destination) + '</h3>' +
      '</div>' +
      '<div class="visited-places-card-actions">' +
      '<button type="button" class="place-delete-btn trip-edit" data-id="' + trip.id + '" title="Edit" aria-label="Edit trip">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn trip-delete" data-id="' + trip.id + '" title="Delete" aria-label="Delete trip">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>' +
      '</button>' +
      '</div>' +
      '</div>' +
      '<div class="log-date">' + escapeHtml(trip.startDate) + ' – ' + escapeHtml(trip.endDate) + '</div>' +
      '<p class="log-notes">' + escapeHtml(stopsSummaryLine(trip.stopCount || 0)) + '</p>' +
      '</div>' +
      '</div>'
    );
  }

  function sortTripsByStartDate(trips) {
    return trips.slice().sort(function (a, b) {
      var tA = a.startDateSort ? new Date(a.startDateSort).getTime() : 0;
      var tB = b.startDateSort ? new Date(b.startDateSort).getTime() : 0;
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
  }

  function bindTripListActions() {
    var container = document.getElementById('tripCards');
    if (!container || container.dataset.tripListBound === '1') return;
    container.dataset.tripListBound = '1';
    container.addEventListener('click', function (e) {
      var delBtn = e.target.closest('.trip-delete');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        var did = parseInt(delBtn.getAttribute('data-id'), 10);
        if (Number.isNaN(did)) return;
        showConfirm('Delete this trip?', function () { deleteTrip(did); });
        return;
      }
      var editBtn = e.target.closest('.trip-edit');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        var eid = editBtn.getAttribute('data-id');
        if (eid) window.location.href = 'plan_new_trip.html?edit=' + eid;
        return;
      }
      var card = e.target.closest('.planned-trip-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) showTripDetails(cid);
      }
    });
  }

  function buildStopCard(stop) {
    var card = document.createElement('div');
    card.className = 'trip-stop-card';
    var num = document.createElement('div');
    num.className = 'trip-stop-number';
    num.textContent = stop.stop_order != null ? String(stop.stop_order) : '?';
    var details = document.createElement('div');
    details.className = 'trip-stop-details';
    var h4 = document.createElement('h4');
    h4.textContent = stop.place_name + (stop.country ? ', ' + stop.country : '');
    var info = document.createElement('div');
    info.className = 'trip-stop-info';
    if (stop.arrival_date) {
      var pArr = document.createElement('p');
      pArr.innerHTML = '<strong>Arrival:</strong> ' + formatApiDate(stop.arrival_date);
      info.appendChild(pArr);
    }
    if (stop.departure_date) {
      var pDep = document.createElement('p');
      pDep.innerHTML = '<strong>Departure:</strong> ' + formatApiDate(stop.departure_date);
      info.appendChild(pDep);
    }
    if (stop.transport_from_last) {
      var pTrans = document.createElement('p');
      pTrans.innerHTML = '<strong>Transport:</strong> ' + escapeHtml(stop.transport_from_last);
      info.appendChild(pTrans);
    }
    if (stop.activities) {
      var pAct = document.createElement('p');
      pAct.innerHTML = '<strong>Activities:</strong> ' + escapeHtml(stop.activities);
      info.appendChild(pAct);
    }
    if (stop.estimated_price != null) {
      var pPrice = document.createElement('p');
      pPrice.innerHTML = '<strong>Estimated Price:</strong> $' + escapeHtml(String(stop.estimated_price));
      info.appendChild(pPrice);
    }
    details.appendChild(h4);
    details.appendChild(info);
    card.appendChild(num);
    card.appendChild(details);
    return card;
  }

  async function showTripDetails(tripId) {
    try {
      var existing = document.querySelectorAll('.trip-details-modal-overlay');
      existing.forEach(function (el) { if (el.parentNode) el.parentNode.removeChild(el); });

      var response = await fetch('/api/planned-trips/' + tripId);
      if (!response.ok) throw new Error('Failed to load trip details');
      var trip = await response.json();

      var template = document.getElementById('tripDetailsModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var titleEl = modal.querySelector('#tripDetailsTitle');
      var startDateEl = modal.querySelector('#tripDetailsStartDate');
      var endDateEl = modal.querySelector('#tripDetailsEndDate');
      var startCityWrap = modal.querySelector('#tripDetailsStartCityWrap');
      var startCityEl = modal.querySelector('#tripDetailsStartCity');
      var stopsCountEl = modal.querySelector('#tripDetailsStopsCount');
      var stopsListEl = modal.querySelector('#tripDetailsStopsList');

      if (titleEl) titleEl.textContent = trip.title || '';
      if (startDateEl) startDateEl.textContent = formatApiDate(trip.start_date);
      if (endDateEl) endDateEl.textContent = formatApiDate(trip.end_date);
      if (trip.start_city) {
        if (startCityWrap) startCityWrap.classList.remove('hidden');
        if (startCityEl) startCityEl.textContent = trip.start_city;
      } else {
        if (startCityWrap) startCityWrap.classList.add('hidden');
      }

      var stops = (trip.stops || []).slice().sort(function (a, b) { return (a.stop_order || 0) - (b.stop_order || 0); });
      if (stopsCountEl) stopsCountEl.textContent = String(stops.length);
      if (stopsListEl) {
        stopsListEl.innerHTML = '';
        if (stops.length === 0) {
          var empty = document.createElement('p');
          empty.className = 'muted';
          empty.textContent = 'No stops added yet.';
          stopsListEl.appendChild(empty);
        } else {
          stops.forEach(function (stop) { stopsListEl.appendChild(buildStopCard(stop)); });
        }
      }

      var closeBtn = modal.querySelector('.trip-details-close');
      var modalBox = modal.querySelector('.trip-details-modal');

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        if (modal.parentNode) modal.parentNode.removeChild(modal);
      }

      if (closeBtn) closeBtn.addEventListener('click', removeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
      });
      if (modalBox) {
        modalBox.addEventListener('click', function (e) { e.stopPropagation(); });
      }
      function handleEsc(e) { if (e.key === 'Escape') removeModal(); }
      document.addEventListener('keydown', handleEsc);
    } catch (error) {
      console.error('Error loading trip details:', error);
      showError('Failed to load trip details: ' + error.message);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindTripListActions();
    render();
  });
})();
