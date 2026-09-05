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

  var H = window.TripMapHelper || null;
  // Thin wrappers so call sites stay readable; implementations live in shared helpers.
  function countryDisplay(value) {
    if (H && typeof H.countryDisplay === 'function') return H.countryDisplay(value);
    return value || '';
  }
  function placeDisplay(placeName, country) {
    if (H && typeof H.placeDisplay === 'function') return H.placeDisplay(placeName, country);
    return [placeName, country].filter(Boolean).join(', ');
  }
  function buildAllRoutePoints(trip, orderedStops) {
    if (H && typeof H.buildAllRoutePoints === 'function') {
      return H.buildAllRoutePoints(trip, orderedStops, plannedTripsT);
    }
    return Promise.resolve([]);
  }
  function destroyTripMap(mapEl) {
    if (H && typeof H.destroyTripMap === 'function') return H.destroyTripMap(mapEl);
  }
  function renderTripMap(accentHostEl, mapEl, noteEl, section, points, showPartialNote) {
    if (H && typeof H.renderTripMap === 'function') {
      return H.renderTripMap(accentHostEl, mapEl, noteEl, section, points, showPartialNote, plannedTripsT);
    }
  }

  function transportLabel(transport) {
    if (window.TripDisplayHelper && typeof window.TripDisplayHelper.transportLabel === 'function') {
      return window.TripDisplayHelper.transportLabel(transport);
    }
    if (!transport) return 'N/A';
    var key = String(transport).trim().toLowerCase();
    var label = plannedTripsT('transportTypes.' + key, null);
    return label || transport;
  }

  function accommodationBookingUrl(city, country, checkin, checkout, people) {
    if (window.TripDisplayHelper && typeof window.TripDisplayHelper.accommodationBookingUrl === 'function') {
      return window.TripDisplayHelper.accommodationBookingUrl(city, country, checkin, checkout, people);
    }
    if (!city || !checkin || !checkout || checkin === checkout) return null;
    var params = new URLSearchParams({
      ss: [city, country].filter(Boolean).join(', '),
      checkin: checkin,
      checkout: checkout,
      group_adults: String(Math.max(1, parseInt(people, 10) || 1)),
      no_rooms: '1',
      group_children: '0'
    });
    return 'https://www.booking.com/searchresults.html?' + params.toString();
  }

  function toDateInputValue(d) {
    if (!d) return '';
    var s = String(d);
    if (s.length >= 10) return s.slice(0, 10);
    return s;
  }

  function fromDateInputVal(v) {
    if (!v || !String(v).trim()) return null;
    return String(v).trim().slice(0, 10);
  }

  function trimOrNull(v) {
    if (v == null) return null;
    var t = String(v).trim();
    return t ? t : null;
  }

  // Trip details map (Leaflet via TripMapHelper)

  function destroyPlannedTripPopups() {
    document.querySelectorAll('.trip-details-modal-overlay').forEach(function (el) {
      var prevMap = el.querySelector('#tripDetailsMap');
      if (prevMap) destroyTripMap(prevMap);
      el.remove();
    });
  }

  // Resolve route points then draw the details-modal map
  function initTripDetailsMap(modal, trip, orderedStops) {
    var section = modal.querySelector('#tripDetailsMapSection');
    var mapEl = modal.querySelector('#tripDetailsMap');
    var noteEl = modal.querySelector('#tripDetailsMapNote');
    if (!section || !mapEl || !noteEl) return Promise.resolve();

    destroyTripMap(mapEl);

    function showMapUnavailable() {
      section.classList.remove('hidden');
      noteEl.classList.remove('hidden');
      noteEl.textContent = plannedTripsT(
        'mapUnavailable',
        'Map could not be loaded. Check your connection or try again later.'
      );
    }

    if (typeof L === 'undefined') {
      showMapUnavailable();
      return Promise.resolve();
    }

    var hasStart = Boolean(trip.start_city && String(trip.start_city).trim());
    if (!hasStart && orderedStops.length === 0) {
      section.classList.add('hidden');
      return Promise.resolve();
    }

    noteEl.classList.remove('hidden');
    noteEl.textContent = plannedTripsT('mapLoading', 'Locating cities on the map…');

    return buildAllRoutePoints(trip, orderedStops)
      .then(function (points) {
        noteEl.textContent = '';
        noteEl.classList.add('hidden');
        if (points.length === 0) {
          showMapUnavailable();
          return;
        }
        var startResolved = points.some(function (p) {
          return p.kind === 'start';
        });
        var resolvedStops = points.filter(function (p) {
          return p.kind === 'stop';
        }).length;
        var showPartial =
          resolvedStops < orderedStops.length || (hasStart && !startResolved);
        renderTripMap(modal, mapEl, noteEl, section, points, showPartial);
      })
      .catch(function (err) {
        console.error('Trip map:', err);
        showMapUnavailable();
      });
  }

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
  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

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

  function todayIsoLocal() {
    return window.DatePickers ? window.DatePickers.todayIso() : (function () {
      var now = new Date();
      var y = now.getFullYear();
      var m = String(now.getMonth() + 1).padStart(2, '0');
      var d = String(now.getDate()).padStart(2, '0');
      return y + '-' + m + '-' + d;
    })();
  }

  function dayAfterIsoLocal(isoDate) {
    return window.DatePickers ? window.DatePickers.dayAfterIso(isoDate) : null;
  }

  var editDatesSilent = false;

  function setEditDateFieldValue(input, iso) {
    if (!input) return;
    editDatesSilent = true;
    try {
      if (window.DatePickers) {
        window.DatePickers.setIso(input, iso, false);
      } else {
        var val = iso ? String(iso).slice(0, 10) : '';
        if (input._flatpickr) {
          if (val) {
            input._flatpickr.setDate(val, false);
            input.value = val;
          } else {
            input._flatpickr.clear();
            input.value = '';
          }
        } else {
          input.value = val;
        }
      }
    } finally {
      editDatesSilent = false;
    }
  }

  function destroyEditDatePickers(root) {
    if (window.DatePickers) window.DatePickers.destroyIn(root);
    else if (root) {
      var inputs = root.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i]._flatpickr) inputs[i]._flatpickr.destroy();
      }
    }
  }

  function attachEditDatePicker(input, options) {
    if (window.DatePickers) return window.DatePickers.attach(input, options || {});
    return null;
  }

  function readEditIsoDate(input) {
    if (window.DatePickers) return window.DatePickers.readIso(input);
    if (!input) return '';
    return String(input.value || '').trim().slice(0, 10);
  }

  function ensureEditEndAfterStart(startInput, endInput) {
    if (!startInput || !endInput) return;
    var today = todayIsoLocal();
    var start = readEditIsoDate(startInput);
    var minEnd = dayAfterIsoLocal(start) || dayAfterIsoLocal(today);
    if (!minEnd) return;
    if (endInput._flatpickr) endInput._flatpickr.set('minDate', minEnd);
    else endInput.setAttribute('min', minEnd);
    var end = readEditIsoDate(endInput);
    if (!end || end <= start) setEditDateFieldValue(endInput, minEnd);
  }

  function attachStopDatePickers(row) {
    if (!row || !window.DatePickers) return;
    var today = todayIsoLocal();
    var arrIn = row.querySelector('input[data-field="arrival_date"]');
    var depIn = row.querySelector('input[data-field="departure_date"]');
    var retIn = row.querySelector('input[data-field="return_date"]');

    function bubbleChange(el) {
      if (!el) return;
      try {
        el.dispatchEvent(new Event('change', { bubbles: true }));
      } catch (err) {
        /* ignore */
      }
    }

    // Arrival → departure: departure is at least the day after arrival.
    if (arrIn && depIn) {
      var bubbling = false;
      window.DatePickers.initLinked(arrIn, depIn, {
        forceFillEnd: true,
        allowSameDay: false,
        minDate: today,
        appendTo: document.body,
        isSilent: function () {
          return editDatesSilent || bubbling;
        },
        onStartChange: function () {
          // Arrival change already bubbles from flatpickr; notify cascade for filled departure.
          if (bubbling) return;
          bubbling = true;
          try {
            bubbleChange(depIn);
          } finally {
            bubbling = false;
          }
        }
      });
    } else {
      if (arrIn) attachEditDatePicker(arrIn, { minDate: today });
      if (depIn) attachEditDatePicker(depIn, { minDate: today });
    }
    if (retIn) {
      attachEditDatePicker(retIn, { minDate: today });
      if (!retIn._flatpickr) retIn.setAttribute('min', today);
    }
  }

  function initEditTripBoundDatePickers(startInput, endInput, hooks) {
    if (!startInput || !endInput) return null;
    hooks = hooks || {};
    if (!window.DatePickers) {
      console.error('DatePickers module missing');
      return null;
    }
    // Trip bounds: end must be after start; always autofill end when start changes.
    return window.DatePickers.initLinked(startInput, endInput, {
      forceFillEnd: true,
      allowSameDay: false,
      appendTo: document.body,
      isSilent: function () {
        return editDatesSilent;
      },
      onStartChange: function () {
        if (typeof hooks.onStartChange === 'function') hooks.onStartChange();
      },
      onEndChange: function () {
        if (typeof hooks.onEndChange === 'function') hooks.onEndChange();
      }
    });
  }

  // Past trip
  function isPastTrip(trip) {
    if (!trip || !trip.endDateSort) return false;
    return String(trip.endDateSort).slice(0, 10) < todayIsoLocal();
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
        if (!Number.isNaN(tid)) openTripEditModal(tid);
        return;
      }
      var shareBtn = e.target.closest('.trip-share');
      if (shareBtn) {
        e.preventDefault();
        e.stopPropagation();
        var sid = parseInt(shareBtn.getAttribute('data-id'), 10);
        if (!Number.isNaN(sid)) openShareModal(sid);
        return;
      }
      var card = e.target.closest('.planned-trip-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) showTripDetails(cid);
      }
    });
  }

  // Inline edit modal
  function renumberEditStops(listEl) {
    if (!listEl) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    for (var i = 0; i < rows.length; i++) {
      var b = rows[i].querySelector('.trip-stop-number');
      if (b) b.textContent = String(i + 1);
    }
  }

  // Date parsing and formatting
  function parseEditDay(s) {
    if (!s || String(s).length < 10) return null;
    var p = String(s).slice(0, 10).split('-');
    var y = parseInt(p[0], 10);
    var m = parseInt(p[1], 10) - 1;
    var d = parseInt(p[2], 10);
    if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
    var dt = new Date(Date.UTC(y, m, d));
    return isNaN(dt.getTime()) ? null : dt;
  }

  function fmtEditDay(dt) {
    if (!dt) return '';
    var mo = dt.getUTCMonth() + 1;
    var day = dt.getUTCDate();
    return dt.getUTCFullYear() + '-' + (mo < 10 ? '0' : '') + mo + '-' + (day < 10 ? '0' : '') + day;
  }

  function addEditDaysUTC(dt, n) {
    var x = new Date(dt.getTime());
    x.setUTCDate(x.getUTCDate() + n);
    return x;
  }

  function dayDiffSigned(a, b) {
    if (!a || !b) return 0;
    return Math.round((b.getTime() - a.getTime()) / 86400000);
  }

  function dayDiffNonNeg(a, b) {
    var ms = dayDiffSigned(a, b);
    return ms >= 0 ? ms : 0;
  }

  function placeNamesMatch(a, b) {
    var x = String(a || '').trim().toLowerCase();
    var y = String(b || '').trim().toLowerCase();
    return !!(x && y && x === y);
  }

  /** Last stop whose place matches the trip start city = return-home leg. */
  function isReturnHomeEditStop(stop, startCity, index, total) {
    if (index !== total - 1 || total < 1) return false;
    return placeNamesMatch(stop && stop.place_name, startCity);
  }

  function isReturnHomeEditRow(row) {
    return !!(row && row.getAttribute('data-return-home') === '1');
  }

  //Trip start follows first stop; end follows last destination departure.
  //Return-home shows a single date mirrored from trip end.
  function syncTripBoundsFromStops(listEl) {
    if (!listEl) return;
    var modalRoot = listEl.closest('.trip-details-modal-overlay');
    var tripStart = modalRoot ? modalRoot.querySelector('#editTripStartDate') : null;
    var tripEnd = modalRoot ? modalRoot.querySelector('#editTripEndDate') : null;
    if (!tripStart || !tripEnd) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    if (!rows.length) return;
    var first = rows[0];
    var fa = first.querySelector('[data-field="arrival_date"]');
    var fd = first.querySelector('[data-field="departure_date"]');
    var startVal = (fa && fa.value) ? fa.value : fd && fd.value ? fd.value : '';

    var endSource = rows[rows.length - 1];
    if (isReturnHomeEditRow(endSource) && rows.length >= 2) {
      endSource = rows[rows.length - 2];
    }
    var la = endSource.querySelector('[data-field="arrival_date"]');
    var ld = endSource.querySelector('[data-field="departure_date"]');
    var endVal = (ld && ld.value) ? ld.value : la && la.value ? la.value : '';

    if (startVal) setEditDateFieldValue(tripStart, String(startVal).slice(0, 10));
    if (endVal) setEditDateFieldValue(tripEnd, String(endVal).slice(0, 10));

    // Never leave end empty or on/before start after stop sync (plan-new-trip rule).
    ensureEditEndAfterStart(tripStart, tripEnd);

    // Keep linked flatpickr minDates in sync after stop-driven bound changes.
    var linked = modalRoot && modalRoot._tripDateLink;
    if (linked && typeof linked.sync === 'function') {
      linked.sync(tripStart.value || '', tripEnd.value || '');
    }

    var last = rows[rows.length - 1];
    if (isReturnHomeEditRow(last) && tripEnd.value) {
      var retIn = last.querySelector('[data-field="return_date"]');
      if (retIn) setEditDateFieldValue(retIn, tripEnd.value);
    }
  }

  //Slide every stop date by deltaDays so the itinerary stays consistent
  function shiftAllEditStopDates(listEl, deltaDays, skipBoundSync) {
    if (!listEl || !deltaDays) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    for (var i = 0; i < rows.length; i++) {
      var arrIn = rows[i].querySelector('[data-field="arrival_date"]');
      var depIn = rows[i].querySelector('[data-field="departure_date"]');
      if (arrIn && arrIn.value) {
        var arr = parseEditDay(arrIn.value);
        if (arr) setEditDateFieldValue(arrIn, fmtEditDay(addEditDaysUTC(arr, deltaDays)));
      }
      if (depIn && depIn.value) {
        var dep = parseEditDay(depIn.value);
        if (dep) setEditDateFieldValue(depIn, fmtEditDay(addEditDaysUTC(dep, deltaDays)));
      }
    }
    // When start-linking already set trip end, skip sync so it cannot overwrite the filled end.
    if (!skipBoundSync) syncTripBoundsFromStops(listEl);
  }

  function chainEditStopDates(listEl, fromIndex, skipBoundSync) {
    if (!listEl) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    if (rows.length <= 1) return;
    fromIndex = (typeof fromIndex === 'number' && fromIndex >= 1) ? fromIndex : 1;

    function parseDay(s) {
      return parseEditDay(s);
    }

    function fmt(dt) {
      return fmtEditDay(dt);
    }

    function addDaysUTC(dt, n) {
      return addEditDaysUTC(dt, n);
    }

    function dayDiff(a, b) {
      return dayDiffNonNeg(a, b);
    }

    var states = [];
    for (var i = 0; i < rows.length; i++) {
      var arrIn = rows[i].querySelector('[data-field="arrival_date"]');
      var depIn = rows[i].querySelector('[data-field="departure_date"]');
      states.push({
        arrIn: arrIn,
        depIn: depIn,
        arrStr: fromDateInputVal(arrIn && arrIn.value) || '',
        depStr: fromDateInputVal(depIn && depIn.value) || ''
      });
    }

    var out = [];
    for (var j = 0; j < states.length; j++) {
      out.push({ arrStr: states[j].arrStr, depStr: states[j].depStr });
    }

    for (var k = fromIndex; k < states.length; k++) {
      var prevOut = out[k - 1];
      var s = states[k];
      var prevExit = prevOut.depStr ? parseDay(prevOut.depStr) : (prevOut.arrStr ? parseDay(prevOut.arrStr) : null);
      if (!prevExit) continue;

      if (!s.arrStr && !s.depStr) continue;

      var oldArr = s.arrStr ? parseDay(s.arrStr) : null;
      var oldDep = s.depStr ? parseDay(s.depStr) : null;
      var newArr = prevExit;
      var newDepStr = '';

      if (oldArr && oldDep) {
        newDepStr = fmt(addDaysUTC(newArr, dayDiff(oldArr, oldDep)));
      } else if (oldDep && !oldArr) {
        var newDep = oldDep >= newArr ? oldDep : newArr;
        newDepStr = fmt(newDep);
      } else {
        newDepStr = '';
      }

      out[k].arrStr = fmt(newArr);
      out[k].depStr = newDepStr;

      var na = parseDay(out[k].arrStr);
      var nd = out[k].depStr ? parseDay(out[k].depStr) : null;
      if (na && nd && nd < na) {
        out[k].depStr = out[k].arrStr;
      }
    }

    for (var w = 0; w < states.length; w++) {
      if (states[w].arrIn) setEditDateFieldValue(states[w].arrIn, out[w].arrStr || '');
      if (states[w].depIn) setEditDateFieldValue(states[w].depIn, out[w].depStr || '');
    }
    if (!skipBoundSync) syncTripBoundsFromStops(listEl);
  }

  function buildEditStopRowEl(stop, options) {
    stop = stop || {};
    options = options || {};
    var isReturnHome = !!options.isReturnHome;
    var row = document.createElement('div');
    row.className = 'trip-stop-card';
    if (stop.id != null) row.setAttribute('data-stop-id', String(stop.id));
    if (isReturnHome) row.setAttribute('data-return-home', '1');

    var num = document.createElement('div');
    num.className = 'trip-stop-number';
    num.textContent = '1';

    var details = document.createElement('div');
    details.className = 'trip-stop-details';

    var actions = document.createElement('div');
    actions.className = 'trip-details-edit-stop-actions';

    var rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'btn-cancel';
    rm.setAttribute('data-i18n', 'plannedTrips.editRemoveStop');
    rm.textContent = plannedTripsT('editRemoveStop', 'Remove');
    actions.appendChild(rm);

    var grid = document.createElement('div');
    grid.className = 'trip-details-form-grid';

    function mkField(full, i18nSuffix, shortKey, fieldName, type, val, isTa) {
      var wrap = document.createElement('div');
      wrap.className = 'trip-details-form-field' + (full ? ' trip-details-form-field--full' : '');
      var lab = document.createElement('label');
      lab.setAttribute('data-i18n', 'plannedTrips.' + i18nSuffix);
      lab.textContent = plannedTripsT(shortKey, fieldName);
      var inp;
      if (isTa) {
        inp = document.createElement('textarea');
        inp.className = 'trip-details-textarea';
        inp.rows = 2;
      } else {
        inp = document.createElement('input');
        inp.className = 'trip-details-text-input';
        inp.type = type || 'text';
      }
      inp.setAttribute('data-field', fieldName);
      if (val != null && val !== '') inp.value = String(val);
      wrap.appendChild(lab);
      wrap.appendChild(inp);
      return wrap;
    }

    grid.appendChild(mkField(false, 'editFieldPlace', 'editFieldPlace', 'place_name', 'text', stop.place_name, false));
    var countryField = mkField(
      false,
      'editFieldCountry',
      'editFieldCountry',
      'country',
      'text',
      countryDisplay(stop.country) || stop.country,
      false
    );
    grid.appendChild(countryField);
    var countryInput = countryField.querySelector('[data-field="country"]');
    if (countryInput && window.Countries && window.Countries.mountAutocomplete) {
      if (stop.country) countryInput.dataset.countryCode = String(stop.country).trim().toUpperCase();
      window.Countries.mountAutocomplete(countryInput);
    }
    if (isReturnHome) {
      var returnDateVal =
        options.tripEndDate || stop.arrival_date || stop.departure_date || '';
      grid.appendChild(
        mkField(
          false,
          'editFieldReturnDate',
          'editFieldReturnDate',
          'return_date',
          'text',
          toDateInputValue(returnDateVal),
          false
        )
      );
    } else {
      grid.appendChild(mkField(false, 'editFieldArrival', 'editFieldArrival', 'arrival_date', 'text', toDateInputValue(stop.arrival_date), false));
      grid.appendChild(mkField(false, 'editFieldDeparture', 'editFieldDeparture', 'departure_date', 'text', toDateInputValue(stop.departure_date), false));
    }
    grid.appendChild(mkField(true, 'editFieldTransport', 'editFieldTransport', 'transport_from_last', 'text', stop.transport_from_last, false));
    if (!isReturnHome) {
      grid.appendChild(mkField(true, 'editFieldActivities', 'editFieldActivities', 'activities', null, stop.activities, true));
    }

    details.appendChild(actions);
    details.appendChild(grid);

    row.appendChild(num);
    row.appendChild(details);

    rm.addEventListener('click', function () {
      var listEl = row.closest('#editStopsList');
      row.remove();
      renumberEditStops(listEl);
      chainEditStopDates(listEl);
    });

    if (!options.skipDatePickers) attachStopDatePickers(row);
    return row;
  }

  function readStopRow(row, orderIndex, tripEndDate) {
    var placeIn = row.querySelector('[data-field="place_name"]');
    var place = placeIn && placeIn.value.trim();
    var countryIn = row.querySelector('[data-field="country"]');
    var transportIn = row.querySelector('[data-field="transport_from_last"]');
    var activitiesIn = row.querySelector('[data-field="activities"]');
    var arrIn = row.querySelector('[data-field="arrival_date"]');
    var depIn = row.querySelector('[data-field="departure_date"]');
    var retIn = row.querySelector('[data-field="return_date"]');
    var sid = row.getAttribute('data-stop-id');
    var isReturnHome = isReturnHomeEditRow(row);
    var endIso = isReturnHome
      ? fromDateInputVal(retIn && retIn.value) || fromDateInputVal(tripEndDate)
      : fromDateInputVal(tripEndDate);
    return {
      id: sid ? parseInt(sid, 10) : null,
      stop_order: orderIndex,
      place_name: place,
      country: trimOrNull(
        (window.Countries && window.Countries.getCode(countryIn)) ||
        (countryIn && countryIn.value)
      ),
      arrival_date: isReturnHome ? endIso : fromDateInputVal(arrIn && arrIn.value),
      departure_date: isReturnHome ? endIso : fromDateInputVal(depIn && depIn.value),
      transport_from_last: trimOrNull(transportIn && transportIn.value),
      activities: isReturnHome ? null : trimOrNull(activitiesIn && activitiesIn.value)
    };
  }

  async function saveTripEdits(tripId, modal, originalStopIds) {
    var titleIn = modal.querySelector('#editTripTitle');
    var saveBtn = modal.querySelector('#tripEditSaveBtn');
    var title = titleIn && titleIn.value.trim();
    if (!title) {
      showError(plannedTripsT('editTitleRequired', 'Trip title is required.'));
      return false;
    }

    var listEl = modal.querySelector('#editStopsList');
    var rows = listEl ? listEl.querySelectorAll('.trip-stop-card') : [];
    var endDateIn = modal.querySelector('#editTripEndDate');

    if (!rows.length) {
      showError(plannedTripsT('editStopsRequired', 'A trip must have at least one stop.'));
      return false;
    }

    var collected = [];
    var endPreview = fromDateInputVal(endDateIn && endDateIn.value);
    var lastRow = rows[rows.length - 1];
    if (isReturnHomeEditRow(lastRow)) {
      var retField = lastRow.querySelector('[data-field="return_date"]');
      if (retField && retField.value) {
        endPreview = fromDateInputVal(retField.value);
        if (endDateIn) setEditDateFieldValue(endDateIn, retField.value);
      }
    }
    for (var i = 0; i < rows.length; i++) {
      var data = readStopRow(rows[i], i + 1, endPreview);
      if (!data.place_name) {
        showError(plannedTripsT('editStopPlaceRequired', 'Each stop must have a place name.'));
        return false;
      }
      collected.push(data);
    }

    var startCityIn = modal.querySelector('#editTripStartCity');
    var startDateIn = modal.querySelector('#editTripStartDate');
    var peopleIn = modal.querySelector('#editTripPeople');
    var peopleParsed = peopleIn ? parseInt(peopleIn.value, 10) : NaN;
    if (!Number.isFinite(peopleParsed) || peopleParsed < 1) {
      showError(plannedTripsT('editPeopleInvalid', 'Travellers must be at least 1.'));
      return false;
    }

    var startDateVal = fromDateInputVal(startDateIn && startDateIn.value);
    var endDateVal = endPreview;
    if (!startDateVal || !endDateVal) {
      showError(plannedTripsT('editDatesRequired', 'Please select both start and end dates.'));
      return false;
    }
    if (startDateVal < todayIsoLocal()) {
      showError(plannedTripsT('editStartDateNotInPast', 'Start date cannot be before today.'));
      return false;
    }
    if (endDateVal <= startDateVal) {
      showError(plannedTripsT('editEndDateAfterStart', 'End date must be after start date.'));
      return false;
    }

    var tripBody = {
      title: title,
      start_city: trimOrNull(startCityIn && startCityIn.value),
      start_date: fromDateInputVal(startDateIn && startDateIn.value),
      end_date: endPreview,
      people: peopleParsed
    };

    // Last stop matching start city is return-home: pin dates to trip end.
    if (collected.length && tripBody.start_city && tripBody.end_date) {
      var last = collected[collected.length - 1];
      if (placeNamesMatch(last.place_name, tripBody.start_city)) {
        last.arrival_date = tripBody.end_date;
        last.departure_date = tripBody.end_date;
      }
    }

    if (saveBtn) saveBtn.disabled = true;

    try {
      var putRes = await fetch('/api/planned-trips/' + tripId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tripBody)
      });
      if (!putRes.ok) throw new Error('trip ' + putRes.status);

      var currentIds = collected
        .filter(function (c) {
          return c.id != null;
        })
        .map(function (c) {
          return c.id;
        });

      for (var j = 0; j < originalStopIds.length; j++) {
        var oid = originalStopIds[j];
        if (currentIds.indexOf(oid) === -1) {
          var delRes = await fetch('/api/trip-stops/' + oid, { method: 'DELETE' });
          if (!delRes.ok && delRes.status !== 404) throw new Error('delete stop ' + oid);
        }
      }

      for (var k = 0; k < collected.length; k++) {
        var c = collected[k];
        var body = {
          place_name: c.place_name,
          country: c.country,
          stop_order: c.stop_order,
          arrival_date: c.arrival_date,
          departure_date: c.departure_date,
          transport_from_last: c.transport_from_last,
          activities: c.activities
        };
        if (c.id) {
          var ur = await fetch('/api/trip-stops/' + c.id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          });
          if (!ur.ok) throw new Error('update stop ' + c.id);
        } else {
          var postBody = Object.assign({ trip_id: tripId }, body);
          var pr = await fetch('/api/trip-stops', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(postBody)
          });
          if (!pr.ok) throw new Error('create stop');
        }
      }

      await render();
      return true;
    } catch (e) {
      console.error('saveTripEdits', e);
      showError(plannedTripsT('editSaveError', 'Could not save changes.') + (e && e.message ? ' (' + e.message + ')' : ''));
      return false;
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  async function openTripEditModal(tripId) {
    try {
      destroyPlannedTripPopups();

      var response = await fetch('/api/planned-trips/' + tripId);
      if (!response.ok) throw new Error('load');
      var trip = await response.json();

      var template = document.getElementById('tripEditModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var stops = (trip.stops || [])
        .slice()
        .sort(function (a, b) {
          return (a.stop_order || 0) - (b.stop_order || 0);
        });
      var originalStopIds = stops
        .map(function (s) {
          return s.id;
        })
        .filter(function (id) {
          return id != null;
        });

      var titleIn = modal.querySelector('#editTripTitle');
      var startCityIn = modal.querySelector('#editTripStartCity');
      var startDateIn = modal.querySelector('#editTripStartDate');
      var endDateIn = modal.querySelector('#editTripEndDate');
      var peopleIn = modal.querySelector('#editTripPeople');
      var listEl = modal.querySelector('#editStopsList');
      if (titleIn) titleIn.value = trip.title || '';
      if (startCityIn) startCityIn.value = trip.start_city || '';
      var todayOpen = todayIsoLocal();
      var openStart = toDateInputValue(trip.start_date);
      var openEnd = toDateInputValue(trip.end_date);
      var openStartDelta = 0;
      if (openStart && openStart < todayOpen) {
        openStartDelta = dayDiffSigned(parseEditDay(openStart), parseEditDay(todayOpen));
        openStart = todayOpen;
      }
      var openMinEnd = dayAfterIsoLocal(openStart) || dayAfterIsoLocal(todayOpen);
      if (!openEnd || (openStart && openEnd <= openStart)) openEnd = openMinEnd || '';
      if (startDateIn) startDateIn.value = openStart;
      if (endDateIn) endDateIn.value = openEnd;
      if (peopleIn) {
        var peopleVal = parseInt(trip.people, 10);
        peopleIn.value = String(Number.isFinite(peopleVal) && peopleVal > 0 ? peopleVal : 1);
      }

      if (listEl) {
        listEl.innerHTML = '';
        stops.forEach(function (s, i) {
          listEl.appendChild(
            buildEditStopRowEl(s, {
              isReturnHome: isReturnHomeEditStop(s, trip.start_city, i, stops.length),
              tripEndDate: trip.end_date
            })
          );
        });
        renumberEditStops(listEl);
        if (openStartDelta) shiftAllEditStopDates(listEl, openStartDelta);
        function onEditStopsDateField(e) {
          if (editDatesSilent) return;
          var t = e.target;
          if (!t || !t.matches) return;
          if (t.matches('input[data-field="return_date"]')) {
            var oldEnd = parseEditDay(prevTripEnd);
            var newEnd = parseEditDay(t.value);
            var retDelta = dayDiffSigned(oldEnd, newEnd);
            if (endDateIn) setEditDateFieldValue(endDateIn, t.value || '');
            if (retDelta) shiftAllEditStopDates(listEl, retDelta);
            else syncTripBoundsFromStops(listEl);
            prevTripStart = startDateIn ? startDateIn.value : '';
            prevTripEnd = endDateIn ? endDateIn.value : '';
            return;
          }
          if (!t.matches('input[data-field="arrival_date"], input[data-field="departure_date"]')) return;
          var row = t.closest('.trip-stop-card');
          var rows = Array.prototype.slice.call(listEl.querySelectorAll('.trip-stop-card'));
          var idx = rows.indexOf(row);
          if (idx === -1) {
            syncTripBoundsFromStops(listEl);
            return;
          }
          // Cascade the edit forward onto later stops (chainEditStopDates also
          // syncs the trip start/end fields at the end, so no separate call needed).
          chainEditStopDates(listEl, idx + 1);
          prevTripStart = startDateIn ? startDateIn.value : '';
          prevTripEnd = endDateIn ? endDateIn.value : '';
        }
        listEl.addEventListener('change', onEditStopsDateField);
      }

      //Moving trip start/end slides every stop by the same delta so middle stops stay aligned (only updating first/last left them stale).
      var prevTripStart = startDateIn ? startDateIn.value : '';
      var prevTripEnd = endDateIn ? endDateIn.value : '';
      function applyEditStartBoundChange() {
        if (editDatesSilent) return;
        if (!listEl || !startDateIn) return;
        var rows = listEl.querySelectorAll('.trip-stop-card');
        if (!rows.length) return;
        var oldStart = parseEditDay(prevTripStart);
        var newStart = parseEditDay(startDateIn.value);
        var startDelta = dayDiffSigned(oldStart, newStart);
        // Never sync trip bounds from stops here — end is owned by start→end linking.
        if (startDelta) shiftAllEditStopDates(listEl, startDelta, true);
        else {
          var first = rows[0];
          var firstField = first.querySelector('[data-field="arrival_date"]') ||
            first.querySelector('[data-field="departure_date"]');
          if (firstField) setEditDateFieldValue(firstField, startDateIn.value);
          chainEditStopDates(listEl, 1, true);
        }
        prevTripStart = startDateIn.value || '';
        prevTripEnd = endDateIn ? endDateIn.value : '';
      }
      function applyEditEndBoundChange() {
        if (editDatesSilent) return;
        if (!listEl || !endDateIn) return;
        var rows = listEl.querySelectorAll('.trip-stop-card');
        if (!rows.length) return;
        var oldEnd = parseEditDay(prevTripEnd);
        var newEnd = parseEditDay(endDateIn.value);
        var endDelta = dayDiffSigned(oldEnd, newEnd);
        if (endDelta) {
          shiftAllEditStopDates(listEl, endDelta);
        } else {
          var endRow = rows[rows.length - 1];
          if (isReturnHomeEditRow(endRow) && rows.length >= 2) {
            endRow = rows[rows.length - 2];
          }
          var pinDep = endRow.querySelector('[data-field="departure_date"]');
          if (pinDep) setEditDateFieldValue(pinDep, endDateIn.value);
        }
        ensureEditEndAfterStart(startDateIn, endDateIn);
        prevTripStart = startDateIn ? startDateIn.value : '';
        prevTripEnd = endDateIn.value || '';
      }

      try {
        modal._tripDateLink = initEditTripBoundDatePickers(startDateIn, endDateIn, {
          onStartChange: applyEditStartBoundChange,
          onEndChange: applyEditEndBoundChange
        });
      } catch (err) {
        console.error('initEditTripBoundDatePickers', err);
      }

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(modal);
      }

      var closeBtn = modal.querySelector('.trip-details-close');
      if (closeBtn && window.i18n && typeof window.i18n.t === 'function') {
        closeBtn.setAttribute('aria-label', window.i18n.t('plannedTrips.editCloseAria'));
      } else if (closeBtn) {
        closeBtn.setAttribute('aria-label', 'Close');
      }

      var addBtn = modal.querySelector('#editAddStopBtn');
      if (addBtn && listEl) {
        addBtn.addEventListener('click', function () {
          var existing = listEl.querySelectorAll('.trip-stop-card');
          var last = existing.length ? existing[existing.length - 1] : null;
          var insertBefore = last && isReturnHomeEditRow(last) ? last : null;
          var prevRow = insertBefore
            ? existing.length >= 2
              ? existing[existing.length - 2]
              : null
            : last;

          // New stop arrival = previous stop's departure (end date).
          var prevDep = prevRow
            ? readEditIsoDate(prevRow.querySelector('[data-field="departure_date"]')) ||
              readEditIsoDate(prevRow.querySelector('[data-field="arrival_date"]')) ||
              readEditIsoDate(prevRow.querySelector('[data-field="return_date"]'))
            : '';
          var arrivalSeed =
            prevDep || readEditIsoDate(startDateIn) || todayIsoLocal();
          // Departure = day after arrival (trip stops are at least overnight).
          var departureSeed =
            window.DatePickers && window.DatePickers.dayAfterIso
              ? window.DatePickers.dayAfterIso(arrivalSeed)
              : window.DatePickers && window.DatePickers.minEndFromStart
                ? window.DatePickers.minEndFromStart(arrivalSeed, false)
                : arrivalSeed;

          var newRow = buildEditStopRowEl(
            {
              arrival_date: arrivalSeed,
              departure_date: departureSeed
            },
            { skipDatePickers: true }
          );

          if (insertBefore) listEl.insertBefore(newRow, insertBefore);
          else listEl.appendChild(newRow);
          renumberEditStops(listEl);
          attachStopDatePickers(newRow);
          syncTripBoundsFromStops(listEl);
          if (window.i18n && typeof window.i18n.applyToPage === 'function') {
            window.i18n.applyToPage(newRow);
          }
        });
      }

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        destroyEditDatePickers(modal);
        modal.remove();
      }

      var saveBtn = modal.querySelector('#tripEditSaveBtn');
      var cancelBtn = modal.querySelector('#tripEditCancelBtn');
      var modalBox = modal.querySelector('#tripEditModalBox');
      var origIdsCopy = originalStopIds.slice();

      if (saveBtn) {
        saveBtn.addEventListener('click', function () {
          saveTripEdits(tripId, modal, origIdsCopy).then(function (ok) {
            if (ok) removeModal();
          });
        });
      }
      if (cancelBtn) cancelBtn.addEventListener('click', removeModal);
      if (closeBtn) closeBtn.addEventListener('click', removeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
      });
      if (modalBox) {
        modalBox.addEventListener('click', function (e) {
          e.stopPropagation();
        });
      }
      function handleEsc(e) {
        if (e.key === 'Escape') removeModal();
      }
      document.addEventListener('keydown', handleEsc);
    } catch (err) {
      console.error('openTripEditModal', err);
      showError(plannedTripsT('editLoadError', 'Could not load trip for editing.'));
    }
  }

  // Trip details modal
  function buildStopCard(stop, people, isLastStop, isBooked, startCity) {
    var card = document.createElement('div');
    card.className = 'trip-stop-card';
    var num = document.createElement('div');
    num.className = 'trip-stop-number';
    num.textContent = stop.stop_order != null ? String(stop.stop_order) : '?';
    var details = document.createElement('div');
    details.className = 'trip-stop-details';
    var h4 = document.createElement('h4');
    h4.textContent = placeDisplay(stop.place_name, stop.country);
    var info = document.createElement('div');
    info.className = 'trip-stop-info';
    var isReturnHome = isLastStop && placeNamesMatch(stop.place_name, startCity);
    if (isReturnHome) {
      var pHome = document.createElement('p');
      pHome.className = 'muted';
      pHome.textContent = plannedTripsT('returnHomeStop', 'Return home');
      info.appendChild(pHome);
      var homeDate = stop.arrival_date || stop.departure_date;
      if (homeDate) {
        var pHomeDate = document.createElement('p');
        pHomeDate.innerHTML =
          '<strong>' +
          escapeHtml(plannedTripsT('editFieldReturnDate', 'Return date')) +
          ':</strong> ' +
          formatApiDate(homeDate);
        info.appendChild(pHomeDate);
      }
    } else {
      if (stop.arrival_date) {
        var pArr = document.createElement('p');
        pArr.innerHTML = '<strong>' + window.i18n.t('plannedTrips.arrival') + ':</strong> ' + formatApiDate(stop.arrival_date);
        info.appendChild(pArr);
      }
      if (stop.departure_date) {
        var pDep = document.createElement('p');
        pDep.innerHTML = '<strong>' + window.i18n.t('plannedTrips.departure') + ':</strong> ' + formatApiDate(stop.departure_date);
        info.appendChild(pDep);
      }
    }
    if (stop.transport_from_last) {
      var pTrans = document.createElement('p');
      pTrans.innerHTML = '<strong>' + escapeHtml(plannedTripsT('transport', 'Transport')) + ':</strong> ' + escapeHtml(transportLabel(stop.transport_from_last));
      info.appendChild(pTrans);
    }
    if (!isBooked) {
      var actions = document.createElement('div');
      actions.className = 'trip-stop-actions';
      var flightUrl = stop.booking_url || null;
      if (flightUrl) {
        var flightLinkText = stop.booking_url && stop.flight_availability_verified
          ? plannedTripsT('bookThisFlight', 'Book this flight')
          : plannedTripsT('checkFlightAvailability', 'Check flight availability');
        actions.innerHTML += '<a class="btn-add trip-stop-action-link" href="' + escapeHtml(flightUrl) + '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(flightLinkText) +
          '</a>';
      }
      // No accommodation on return-home last stop; TripDisplayHelper uses stop coords when saved.
      var accommodationUrl = !isReturnHome && window.TripDisplayHelper
        && typeof window.TripDisplayHelper.accommodationBookingUrlForStop === 'function'
        ? window.TripDisplayHelper.accommodationBookingUrlForStop(
          stop,
          countryDisplay(stop.country),
          stop.arrival_date,
          stop.departure_date,
          people
        )
        : accommodationBookingUrl(
          isReturnHome ? null : stop.place_name,
          countryDisplay(stop.country),
          stop.arrival_date,
          stop.departure_date,
          people
        );
      if (accommodationUrl) {
        actions.innerHTML += '<a class="btn-add trip-stop-action-link" href="' + escapeHtml(accommodationUrl) + '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(plannedTripsT('findAccommodation', 'Find accommodation')) +
          '</a>';
      }
      if (actions.children.length) {
        info.appendChild(actions);
      }
    }
    if (stop.activities && !isReturnHome) {
      var pAct = document.createElement('p');
      pAct.innerHTML = '<strong>' + window.i18n.t('plannedTrips.activities') + ':</strong> ' + escapeHtml(stop.activities);
      info.appendChild(pAct);
    }
    details.appendChild(h4);
    details.appendChild(info);
    card.appendChild(num);
    card.appendChild(details);
    return card;
  }

  async function showTripDetails(tripId) {
    try {
      destroyPlannedTripPopups();

      var response = await fetch('/api/planned-trips/' + tripId);
      if (!response.ok) throw new Error(plannedTripsT('loadDetailsFailed', 'Failed to load trip details'));
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
      var peopleEl = modal.querySelector('#tripDetailsPeople');
      var bookedEl = modal.querySelector('#tripDetailsBookedStatus');
      var startCityWrap = modal.querySelector('#tripDetailsStartCityWrap');
      var startCityEl = modal.querySelector('#tripDetailsStartCity');
      var stopsCountEl = modal.querySelector('#tripDetailsStopsCount');
      var stopsListEl = modal.querySelector('#tripDetailsStopsList');

      if (titleEl) titleEl.textContent = trip.title || '';
      if (startDateEl) startDateEl.textContent = formatApiDate(trip.start_date);
      if (endDateEl) endDateEl.textContent = formatApiDate(trip.end_date);
      if (peopleEl) peopleEl.textContent = String(trip.people || 1);
      if (bookedEl) bookedEl.textContent = trip.is_booked ? plannedTripsT('booked', 'Booked') : plannedTripsT('notBooked', 'Not booked');
      if (trip.start_city) {
        if (startCityWrap) startCityWrap.classList.remove('hidden');
        if (startCityEl) startCityEl.textContent = trip.start_city;
      } else {
        if (startCityWrap) startCityWrap.classList.add('hidden');
      }
      var sharedByWrap = modal.querySelector('#tripDetailsSharedByWrap');
      var sharedByEl = modal.querySelector('#tripDetailsSharedBy');
      var sharerName = trip.shared_from_username
        || (trip.shared_from_user_id ? ('#' + trip.shared_from_user_id) : '');
      if (sharerName) {
        if (sharedByWrap) sharedByWrap.classList.remove('hidden');
        if (sharedByEl) sharedByEl.textContent = sharerName;
      } else if (sharedByWrap) {
        sharedByWrap.classList.add('hidden');
      }

      var stops = (trip.stops || []).slice().sort(function (a, b) { return (a.stop_order || 0) - (b.stop_order || 0); });
      if (stopsCountEl) stopsCountEl.textContent = String(stops.length);
      if (stopsListEl) {
        stopsListEl.innerHTML = '';
        if (stops.length === 0) {
          var empty = document.createElement('p');
          empty.className = 'muted';
          empty.textContent = plannedTripsT('noStopsAdded', 'No stops added yet.');
          stopsListEl.appendChild(empty);
        } else {
          stops.forEach(function (stop, index) {
            stopsListEl.appendChild(buildStopCard(stop, trip.people || 1, index === stops.length - 1, !!trip.is_booked, trip.start_city));
          });
        }
      }

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(modal);
      }

      var mapEl = modal.querySelector('#tripDetailsMap');
      await initTripDetailsMap(modal, trip, stops);

      var closeBtn = modal.querySelector('.trip-details-close');
      var modalBox = modal.querySelector('.trip-details-modal');

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        if (mapEl) destroyTripMap(mapEl);
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
      showError(plannedTripsT('loadDetailsFailed', 'Failed to load trip details') + ': ' + error.message);
    }
  }

  // Sharing: public link + user-to-user invitation inbox
  function absoluteShareUrl(relativePath) {
    if (!relativePath) return '';
    if (/^https?:\/\//i.test(relativePath)) return relativePath;
    // Public /share page is served with the frontend origin
    var base = window.location.origin || '';
    if (relativePath.charAt(0) === '/') return base + relativePath;
    return base + '/' + relativePath;
  }

  async function createShareLink(tripId) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return null;
    var response = await fetch('/api/planned-trips/' + tripId + '/share-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: parseInt(userId, 10) })
    });
    if (!response.ok) throw new Error('share-link ' + response.status);
    return response.json();
  }

  async function sendTripShare(tripId, toUserId) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return false;
    var response = await fetch('/api/planned-trips/' + tripId + '/share', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_user_id: parseInt(userId, 10),
        to_user_id: parseInt(toUserId, 10)
      })
    });
    if (!response.ok) throw new Error('share ' + response.status);
    return true;
  }

  async function searchShareUsers(query) {
    var userId = localStorage.getItem('user_id');
    if (!userId || !query || !String(query).trim()) return [];
    var params = new URLSearchParams({
      search: String(query).trim(),
      exclude_user_id: userId,
      limit: '20'
    });
    var response = await fetch('/api/users?' + params.toString());
    if (!response.ok) return [];
    var data = await response.json();
    return Array.isArray(data) ? data : [];
  }

  async function openShareModal(tripId) {
    try {
      destroyPlannedTripPopups();
      var template = document.getElementById('tripShareModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var linkInput = modal.querySelector('#tripShareLinkInput');
      var copyBtn = modal.querySelector('#tripShareCopyBtn');
      var searchInput = modal.querySelector('#tripShareUserSearch');
      var resultsEl = modal.querySelector('#tripShareUserResults');
      var sendBtn = modal.querySelector('#tripShareSendBtn');
      var selectedUserId = null;

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(modal);
      }

      try {
        var linkData = await createShareLink(tripId);
        if (linkInput && linkData) {
          linkInput.value = absoluteShareUrl(linkData.share_url || '');
        }
      } catch (e) {
        console.error(e);
        showError(plannedTripsT('shareLinkError', 'Could not create share link.'));
      }

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        modal.remove();
      }

      if (copyBtn && linkInput) {
        copyBtn.addEventListener('click', function () {
          var url = linkInput.value;
          if (!url) return;
          function notifyCopied() {
            var msg = plannedTripsT('linkCopied', 'Link copied to clipboard.');
            if (typeof showModal === 'function') {
              showModal({ title: plannedTripsT('copyLink', 'Copy link'), message: msg, type: 'success' });
            } else {
              showError(msg);
            }
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(notifyCopied).catch(function () {
              linkInput.select();
              document.execCommand('copy');
              notifyCopied();
            });
          } else {
            linkInput.select();
            document.execCommand('copy');
            notifyCopied();
          }
        });
      }

      function renderUserResults(users) {
        if (!resultsEl) return;
        resultsEl.innerHTML = '';
        selectedUserId = null;
        if (sendBtn) sendBtn.disabled = true;
        users.forEach(function (user) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'trip-share-user-option';
          btn.textContent = user.username;
          btn.setAttribute('data-user-id', String(user.id));
          btn.addEventListener('click', function () {
            resultsEl.querySelectorAll('.trip-share-user-option').forEach(function (el) {
              el.classList.remove('selected');
            });
            btn.classList.add('selected');
            selectedUserId = user.id;
            if (sendBtn) sendBtn.disabled = false;
          });
          resultsEl.appendChild(btn);
        });
      }

      var searchTimer = null;
      if (searchInput) {
        searchInput.addEventListener('input', function () {
          clearTimeout(searchTimer);
          searchTimer = setTimeout(function () {
            searchShareUsers(searchInput.value).then(renderUserResults);
          }, 250);
        });
      }

      if (sendBtn) {
        sendBtn.addEventListener('click', async function () {
          if (!selectedUserId) return;
          sendBtn.disabled = true;
          try {
            await sendTripShare(tripId, selectedUserId);
            var sentMsg = plannedTripsT('shareSent', 'Trip share invitation sent.');
            if (typeof showModal === 'function') {
              showModal({ title: plannedTripsT('shareTrip', 'Share trip'), message: sentMsg, type: 'success' });
            } else {
              showError(sentMsg);
            }
            removeModal();
          } catch (e) {
            console.error(e);
            showError(plannedTripsT('shareSendError', 'Could not send trip share.'));
            sendBtn.disabled = false;
          }
        });
      }

      var closeBtn = modal.querySelector('.trip-details-close');
      var modalBox = modal.querySelector('#tripShareModalBox');
      if (closeBtn) closeBtn.addEventListener('click', removeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
      });
      if (modalBox) modalBox.addEventListener('click', function (e) { e.stopPropagation(); });
      function handleEsc(e) { if (e.key === 'Escape') removeModal(); }
      document.addEventListener('keydown', handleEsc);
    } catch (err) {
      console.error('openShareModal', err);
      showError(plannedTripsT('shareLinkError', 'Could not create share link.'));
    }
  }

  async function respondToShareInvitation(invitationId, action) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return;
    var response = await fetch('/api/trip-share-invitations/' + invitationId + '/' + action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: parseInt(userId, 10) })
    });
    if (!response.ok) throw new Error(action + ' ' + response.status);
  }

  async function loadShareInbox() {
    var userId = localStorage.getItem('user_id');
    var section = document.getElementById('shareInboxSection');
    var inbox = document.getElementById('shareInbox');
    if (!userId || !section || !inbox) return;

    try {
      var response = await fetch('/api/users/' + userId + '/trip-share-invitations?status=pending');
      if (!response.ok) {
        section.classList.add('hidden');
        return;
      }
      var invitations = await response.json();
      section.classList.remove('hidden');
      if (!Array.isArray(invitations) || invitations.length === 0) {
        inbox.innerHTML =
          '<p class="muted share-inbox-empty">' +
          escapeHtml(plannedTripsT('shareInboxEmpty', 'No pending trip invitations.')) +
          '</p>';
        return;
      }

      inbox.innerHTML = invitations.map(function (inv) {
        var title = inv.source_trip && inv.source_trip.title ? inv.source_trip.title : 'Trip';
        var sharer = inv.from_username
          || (inv.from_user_id != null ? ('#' + inv.from_user_id) : 'User');
        var fromLabel = plannedTripsT('shareFromUser', 'From {{user}}').replace('{{user}}', String(sharer));
        return (
          '<div class="share-inbox-card" data-invitation-id="' + inv.id + '">' +
          '<div><strong>' + escapeHtml(title) + '</strong><br><span class="muted">' + escapeHtml(fromLabel) + '</span></div>' +
          '<div class="share-inbox-card-actions">' +
          '<button type="button" class="btn-add share-accept" data-id="' + inv.id + '">' + escapeHtml(plannedTripsT('acceptShare', 'Accept')) + '</button>' +
          '<button type="button" class="btn-cancel share-decline" data-id="' + inv.id + '">' + escapeHtml(plannedTripsT('declineShare', 'Decline')) + '</button>' +
          '</div></div>'
        );
      }).join('');

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(section);
      }
    } catch (e) {
      console.error('loadShareInbox', e);
      section.classList.add('hidden');
    }
  }

  function bindShareInboxActions() {
    var inbox = document.getElementById('shareInbox');
    if (!inbox || inbox.dataset.shareInboxBound === '1') return;
    inbox.dataset.shareInboxBound = '1';
    inbox.addEventListener('click', function (e) {
      var acceptBtn = e.target.closest('.share-accept');
      var declineBtn = e.target.closest('.share-decline');
      var btn = acceptBtn || declineBtn;
      if (!btn) return;
      e.preventDefault();
      var id = parseInt(btn.getAttribute('data-id'), 10);
      if (Number.isNaN(id)) return;
      var action = acceptBtn ? 'accept' : 'decline';
      respondToShareInvitation(id, action)
        .then(function () {
          return Promise.all([loadShareInbox(), render()]);
        })
        .catch(function (err) {
          console.error(err);
          showError(plannedTripsT('shareSendError', 'Could not send trip share.'));
        });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    // List click handlers + share inbox
    bindTripListActions();
    bindShareInboxActions();
    loadShareInbox();
    render();
  });
})();
