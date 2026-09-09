(function (global) {
  'use strict';

  function plannedTripsT(key, fallback) {
    if (global.i18n && typeof global.i18n.t === 'function') {
      var v = global.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
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

  var DU = global.TripDateUtils;
  var escapeHtml = DU ? DU.escapeHtml : function (s) { return s || ''; };
  var placeNamesMatch = DU ? DU.placeNamesMatch : function (a, b) { return a === b; };

  var H = global.TripMapHelper || null;
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
    if (global.TripDisplayHelper && typeof global.TripDisplayHelper.transportLabel === 'function') {
      return global.TripDisplayHelper.transportLabel(transport);
    }
    if (!transport) return 'N/A';
    var key = String(transport).trim().toLowerCase();
    var label = plannedTripsT('transportTypes.' + key, null);
    return label || transport;
  }

  function accommodationBookingUrl(city, country, checkin, checkout, people) {
    if (global.TripDisplayHelper && typeof global.TripDisplayHelper.accommodationBookingUrl === 'function') {
      return global.TripDisplayHelper.accommodationBookingUrl(city, country, checkin, checkout, people);
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

  function destroyPopups() {
    if (global.TripPopups && typeof global.TripPopups.destroyAll === 'function') {
      global.TripPopups.destroyAll();
    }
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
        pArr.innerHTML = '<strong>' + global.i18n.t('plannedTrips.arrival') + ':</strong> ' + formatApiDate(stop.arrival_date);
        info.appendChild(pArr);
      }
      if (stop.departure_date) {
        var pDep = document.createElement('p');
        pDep.innerHTML = '<strong>' + global.i18n.t('plannedTrips.departure') + ':</strong> ' + formatApiDate(stop.departure_date);
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
      var accommodationUrl = !isReturnHome && global.TripDisplayHelper
        && typeof global.TripDisplayHelper.accommodationBookingUrlForStop === 'function'
        ? global.TripDisplayHelper.accommodationBookingUrlForStop(
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
      pAct.innerHTML = '<strong>' + global.i18n.t('plannedTrips.activities') + ':</strong> ' + escapeHtml(stop.activities);
      info.appendChild(pAct);
    }
    details.appendChild(h4);
    details.appendChild(info);
    card.appendChild(num);
    card.appendChild(details);
    return card;
  }

  async function show(tripId) {
    try {
      destroyPopups();

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

      if (global.i18n && typeof global.i18n.applyToPage === 'function') {
        global.i18n.applyToPage(modal);
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

  global.TripDetailsModal = {
    show: show
  };
})(window);
