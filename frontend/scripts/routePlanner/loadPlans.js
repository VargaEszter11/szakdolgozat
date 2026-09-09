(function () {
  // Display helpers
  function normalizeTrip(trip) {

    return {
      id: trip.id,
      destination: trip.title || 'Unknown destination',
      startDate: formatApiDate(trip.start_date),
      endDate: formatApiDate(trip.end_date),
      startDateSort: trip.start_date || null,
      endDateSort: trip.end_date || null,
      people: trip.people || 1,
      isBooked: !!trip.is_booked,
      stopCount: trip.stops ? trip.stops.length : 0,
      sharedFromUserId: trip.shared_from_user_id || null,
      sharedFromUsername: trip.shared_from_username || null
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

  function plannedTripsT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      var v = window.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  var DU = window.TripDateUtils;
  var escapeHtml = DU.escapeHtml;

  // Trip list API
  async function getTrips() {
    if (!localStorage.getItem('user_id')) {
      console.warn('No user_id found. User not logged in.');
      return [];
    }

    try {
      var response = await fetch('/api/planned-trips');

      if (!response.ok) {
        throw new Error('API request failed: ' + response.status);
      }

      var data = await response.json();
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
        throw new Error(plannedTripsT('deleteFailed', 'Failed to delete trip') + ': ' + response.status);
      }

      await render();
    } catch (error) {
      console.error('Error deleting trip:', error);
      showError(plannedTripsT('deleteFailed', 'Failed to delete trip') + ': ' + error.message);
    }
  }

  async function toggleTripBooked(id, isBooked) {
    try {
      var response = await fetch('/api/planned-trips/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_booked: !isBooked })
      });

      if (!response.ok) {
        throw new Error(plannedTripsT('updateFailed', 'Failed to update trip') + ': ' + response.status);
      }

      await render();
    } catch (error) {
      console.error('Error updating trip:', error);
      showError(plannedTripsT('bookedSaveError', 'Could not update booking status.'));
    }
  }

  // List rendering
  function renderCard(trip) {
    return (
      '<div class="travel-log-card planned-trip-card" data-id="' + trip.id + '">' +
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
      '<button type="button" class="place-delete-btn trip-booked" data-id="' + trip.id + '" data-booked="' + (trip.isBooked ? '1' : '0') + '" title="' + escapeHtml(trip.isBooked ? plannedTripsT('markNotBooked', 'Mark as not booked') : plannedTripsT('markBooked', 'Mark as booked')) + '" aria-label="' + escapeHtml(trip.isBooked ? plannedTripsT('markNotBooked', 'Mark as not booked') : plannedTripsT('markBooked', 'Mark as booked')) + '">' +
      (trip.isBooked
        ? '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>'
        : '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/><path d="m9 11 3 3L22 4"/></svg>') +
      '</button>' +
      '<button type="button" class="place-delete-btn trip-share" data-id="' + trip.id + '" title="' + escapeHtml(plannedTripsT('shareTrip', 'Share trip')) + '" aria-label="' + escapeHtml(plannedTripsT('shareTrip', 'Share trip')) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/></svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn trip-edit" data-id="' + trip.id + '" title="' + escapeHtml(plannedTripsT('editTripAria', 'Edit trip')) + '" aria-label="' + escapeHtml(plannedTripsT('editTripAria', 'Edit trip')) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn trip-delete" data-id="' + trip.id + '" title="' + escapeHtml(plannedTripsT('deleteTripAria', 'Delete trip')) + '" aria-label="' + escapeHtml(plannedTripsT('deleteTripAria', 'Delete trip')) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>' +
      '</button>' +
      '</div>' +
      '</div>' +
      '<div class="log-date">' + escapeHtml(trip.startDate) + ' – ' + escapeHtml(trip.endDate) + '</div>' +
      '<p class="log-notes">' + escapeHtml(stopsSummaryLine(trip.stopCount || 0)) + ' · ' + escapeHtml(plannedTripsT('people', 'People')) + ': ' + escapeHtml(trip.people || 1) + (trip.isBooked ? ' · ' + escapeHtml(plannedTripsT('booked', 'Booked')) : '') + (trip.sharedFromUsername ? ' · ' + escapeHtml(plannedTripsT('shareFromUser', 'From {{user}}').replace('{{user}}', trip.sharedFromUsername)) : '') + '</p>' +
      '</div>' +
      '</div>'
    );
  }

  // Past trip
  function isPastTrip(trip) {
    if (!trip || !trip.endDateSort) return false;
    return String(trip.endDateSort).slice(0, 10) < DU.todayIsoLocal();
  }

  function sortTripsByStartDate(trips, descending) {
    return trips.slice().sort(function (a, b) {
      var tA = a.startDateSort ? new Date(a.startDateSort).getTime() : 0;
      var tB = b.startDateSort ? new Date(b.startDateSort).getTime() : 0;
      return descending ? (tB - tA) : (tA - tB);
    });
  }

  async function render() {
    var upcomingSection = document.getElementById('upcomingTripsSection');
    var pastSection = document.getElementById('pastTripsSection');
    var upcomingContainer = document.getElementById('tripCards');
    var pastContainer = document.getElementById('pastTripCards');
    var emptyState = document.getElementById('emptyState');
    if (!upcomingContainer || !pastContainer || !emptyState || !upcomingSection || !pastSection) {
      if (window.markAppReady) window.markAppReady();
      return;
    }

    var trips = await getTrips();
    var upcoming = [];
    var past = [];
    trips.forEach(function (trip) {
      if (isPastTrip(trip)) past.push(trip);
      else upcoming.push(trip);
    });
    upcoming = sortTripsByStartDate(upcoming, false);
    past = sortTripsByStartDate(past, true);

    if (upcoming.length === 0 && past.length === 0) {
      upcomingSection.classList.add('hidden');
      pastSection.classList.add('hidden');
      upcomingContainer.innerHTML = '';
      pastContainer.innerHTML = '';
      emptyState.classList.remove('hidden');
      if (window.markAppReady) window.markAppReady();
      return;
    }

    emptyState.classList.add('hidden');

    if (upcoming.length) {
      upcomingSection.classList.remove('hidden');
      upcomingContainer.innerHTML = upcoming.map(renderCard).join('');
    } else {
      upcomingSection.classList.add('hidden');
      upcomingContainer.innerHTML = '';
    }

    if (past.length) {
      pastSection.classList.remove('hidden');
      pastContainer.innerHTML = past.map(renderCard).join('');
    } else {
      pastSection.classList.add('hidden');
      pastContainer.innerHTML = '';
    }

    if (window.i18n && typeof window.i18n.applyToPage === 'function') {
      window.i18n.applyToPage(document.getElementById('tripLists') || document.body);
    }
    if (window.markAppReady) window.markAppReady();
  }

  // Card buttons
  function bindTripListActions() {
    var root = document.getElementById('tripLists');
    if (!root || root.dataset.tripListBound === '1') return;
    root.dataset.tripListBound = '1';
    root.addEventListener('click', function (e) {
      var delBtn = e.target.closest('.trip-delete');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        var did = parseInt(delBtn.getAttribute('data-id'), 10);
        if (Number.isNaN(did)) return;
        showConfirm(plannedTripsT('deleteConfirm', 'Delete this trip?'), function () { deleteTrip(did); });
        return;
      }
      var bookedBtn = e.target.closest('.trip-booked');
      if (bookedBtn) {
        e.preventDefault();
        e.stopPropagation();
        var bid = parseInt(bookedBtn.getAttribute('data-id'), 10);
        if (Number.isNaN(bid)) return;
        toggleTripBooked(bid, bookedBtn.getAttribute('data-booked') === '1');
        return;
      }
      var editBtn = e.target.closest('.trip-edit');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        var eid = editBtn.getAttribute('data-id');
        var tid = eid ? parseInt(eid, 10) : NaN;
        if (!Number.isNaN(tid)) window.TripEditModal.open(tid);
        return;
      }
      var shareBtn = e.target.closest('.trip-share');
      if (shareBtn) {
        e.preventDefault();
        e.stopPropagation();
        var sid = parseInt(shareBtn.getAttribute('data-id'), 10);
        if (!Number.isNaN(sid)) window.TripSharing.openShareModal(sid);
        return;
      }
      var card = e.target.closest('.planned-trip-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) window.TripDetailsModal.show(cid);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    window.TripEditModal.init({ refreshList: render });
    window.TripSharing.init({ refreshList: render });

    // List click handlers + share inbox
    bindTripListActions();
    window.TripSharing.bindShareInboxActions();
    window.TripSharing.loadShareInbox();
    render();
  });
})();
