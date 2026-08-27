(function () {
  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };
  var H = window.TripMapHelper;

  function plannedTripsT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      var v = window.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  function formatApiDate(dateStr) {
    if (!dateStr) return '—';
    try {
      var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
      return new Date(dateStr).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function transportLabel(transport) {
    return window.TripDisplayHelper
      ? window.TripDisplayHelper.transportLabel(transport)
      : (transport || 'N/A');
  }

  function placeDisplay(placeName, country) {
    return H.placeDisplay(placeName, country);
  }

  function buildAllRoutePoints(trip, orderedStops) {
    return H.buildAllRoutePoints(trip, orderedStops, plannedTripsT);
  }

  function renderTripMap(rootEl, mapEl, noteEl, section, points, showPartialNote) {
    return H.renderTripMap(rootEl, mapEl, noteEl, section, points, showPartialNote, plannedTripsT);
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
    h4.textContent = placeDisplay(stop.place_name, stop.country);
    var info = document.createElement('div');
    info.className = 'trip-stop-info';
    if (stop.arrival_date) {
      var pArr = document.createElement('p');
      pArr.innerHTML = '<strong>' + escapeHtml(plannedTripsT('arrival', 'Arrival')) + ':</strong> ' + escapeHtml(formatApiDate(stop.arrival_date));
      info.appendChild(pArr);
    }
    if (stop.departure_date) {
      var pDep = document.createElement('p');
      pDep.innerHTML = '<strong>' + escapeHtml(plannedTripsT('departure', 'Departure')) + ':</strong> ' + escapeHtml(formatApiDate(stop.departure_date));
      info.appendChild(pDep);
    }
    if (stop.transport_from_last) {
      var pTrans = document.createElement('p');
      pTrans.innerHTML = '<strong>' + escapeHtml(plannedTripsT('transport', 'Transport')) + ':</strong> ' + escapeHtml(transportLabel(stop.transport_from_last));
      info.appendChild(pTrans);
    }
    if (stop.activities) {
      var pAct = document.createElement('p');
      pAct.innerHTML = '<strong>' + escapeHtml(plannedTripsT('activities', 'Activities')) + ':</strong> ' + escapeHtml(stop.activities);
      info.appendChild(pAct);
    }
    details.appendChild(h4);
    details.appendChild(info);
    card.appendChild(num);
    card.appendChild(details);
    return card;
  }

  function showError(message) {
    var errBox = document.getElementById('sharedTripError');
    var errText = document.getElementById('sharedTripErrorText');
    var content = document.getElementById('sharedTripContent');
    if (content) content.classList.add('hidden');
    if (errText) errText.textContent = message;
    if (errBox) errBox.classList.remove('hidden');
  }

  //Share token
  function getTokenFromUrl() {
    try {
      return new URLSearchParams(window.location.search).get('token') || '';
    } catch (e) {
      return '';
    }
  }

  async function loadSharedTrip() {
    var token = getTokenFromUrl().trim();
    if (!token) {
      showError(plannedTripsT('sharedTripMissingToken', 'Missing share link token.'));
      return;
    }

    try {
      var response = await fetch('/api/shared-trips/' + encodeURIComponent(token));
      if (!response.ok) {
        showError(plannedTripsT('sharedTripNotFound', 'This shared trip link is invalid or has expired.'));
        return;
      }
      var trip = await response.json();
      document.getElementById('sharedTripTitle').textContent = trip.title || plannedTripsT('sharedTripTitle', 'Shared itinerary');
      document.getElementById('sharedStartDate').textContent = formatApiDate(trip.start_date);
      document.getElementById('sharedEndDate').textContent = formatApiDate(trip.end_date);
      document.getElementById('sharedPeople').textContent = String(trip.people || 1);
      if (trip.start_city) {
        document.getElementById('sharedStartCityWrap').classList.remove('hidden');
        document.getElementById('sharedStartCity').textContent = trip.start_city;
      }
      var stops = (trip.stops || []).slice().sort(function (a, b) {
        return (a.stop_order || 0) - (b.stop_order || 0);
      });
      document.getElementById('sharedStopsCount').textContent = String(stops.length);
      var listEl = document.getElementById('sharedStopsList');
      listEl.innerHTML = '';
      if (!stops.length) {
        var empty = document.createElement('p');
        empty.className = 'muted';
        empty.textContent = plannedTripsT('noStopsAdded', 'No stops added yet.');
        listEl.appendChild(empty);
      } else {
        stops.forEach(function (stop) {
          listEl.appendChild(buildStopCard(stop));
        });
      }

      document.getElementById('sharedTripContent').classList.remove('hidden');
      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(document.body);
      }

      // Prefer stored start/stop coordinates from the API
      if (typeof L !== 'undefined') {
        var rootEl = document.getElementById('sharedTripContent');
        var mapEl = document.getElementById('sharedTripMap');
        var section = document.getElementById('sharedTripMapSection');
        var noteEl = document.getElementById('sharedTripMapNote');
        var points = await buildAllRoutePoints(trip, stops);
        if (points.length) {
          renderTripMap(rootEl, mapEl, noteEl, section, points, points.filter(function (p) { return p.kind === 'stop'; }).length < stops.length);
        } else if (section && noteEl) {
          section.classList.remove('hidden');
          noteEl.classList.remove('hidden');
          noteEl.textContent = plannedTripsT(
            'mapUnavailable',
            'Map could not be loaded. Check your connection or try again later.'
          );
        }
      } else {
        var mapSection = document.getElementById('sharedTripMapSection');
        var mapNote = document.getElementById('sharedTripMapNote');
        if (mapSection && mapNote) {
          mapSection.classList.remove('hidden');
          mapNote.classList.remove('hidden');
          mapNote.textContent = plannedTripsT(
            'mapUnavailable',
            'Map could not be loaded. Check your connection or try again later.'
          );
        }
      }
    } catch (err) {
      console.error(err);
      showError(plannedTripsT('sharedTripLoadError', 'Could not load shared trip.'));
    }
  }

  document.addEventListener('DOMContentLoaded', loadSharedTrip);
})();
