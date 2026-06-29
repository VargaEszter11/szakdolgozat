(function () {
  var NOMINATIM_DELAY_MS = 1100;
  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

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
    if (!transport) return 'N/A';
    var key = String(transport).trim().toLowerCase();
    var label = plannedTripsT('transportTypes.' + key, null);
    return label || transport;
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function nominatimGeocode(query) {
    if (!query || !String(query).trim()) return Promise.resolve(null);
    var url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({
      q: String(query).trim(),
      format: 'json',
      limit: '1'
    });
    return fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) { return Array.isArray(data) && data.length ? data[0] : null; })
      .catch(function () { return null; });
  }

  function labelForStop(stop) {
    var ord = stop.stop_order != null ? String(stop.stop_order) : '?';
    return ord + '. ' + (stop.place_name || '') + (stop.country ? ', ' + stop.country : '');
  }

  function buildAllRoutePoints(trip, orderedStops) {
    var points = [];
    var hadNetworkRequest = false;
    var chain = Promise.resolve();

    function beforeNetwork() {
      var p = hadNetworkRequest ? sleep(NOMINATIM_DELAY_MS) : Promise.resolve();
      hadNetworkRequest = true;
      return p;
    }

    if (trip.start_city && String(trip.start_city).trim()) {
      var startQuery = String(trip.start_city).trim();
      chain = chain
        .then(function () {
          return beforeNetwork().then(function () { return nominatimGeocode(startQuery); });
        })
        .then(function (hit) {
          if (hit) {
            points.push({
              lat: parseFloat(hit.lat),
              lng: parseFloat(hit.lon),
              label: plannedTripsT('mapStartCityLabel', 'Start') + ': ' + startQuery,
              kind: 'start',
              startCityName: startQuery
            });
          }
        });
    }

    for (var i = 0; i < orderedStops.length; i++) {
      (function (stop) {
        chain = chain.then(function () {
          var lat = stop.latitude;
          var lon = stop.longitude;
          if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
            points.push({ lat: lat, lng: lon, label: labelForStop(stop), kind: 'stop' });
            return undefined;
          }
          var q = (stop.place_name || '').trim();
          if (!q) return undefined;
          if (stop.country) q += ', ' + String(stop.country).trim();
          return beforeNetwork()
            .then(function () { return nominatimGeocode(q); })
            .then(function (hit) {
              if (hit) {
                points.push({
                  lat: parseFloat(hit.lat),
                  lng: parseFloat(hit.lon),
                  label: labelForStop(stop),
                  kind: 'stop'
                });
              }
            });
        });
      })(orderedStops[i]);
    }

    return chain.then(function () { return points; });
  }

  function renderTripMap(rootEl, mapEl, noteEl, section, points, showPartialNote) {
    section.classList.remove('hidden');
    var latlngs = points.map(function (p) { return [p.lat, p.lng]; });
    var accentHost = rootEl || document.querySelector('.shared-trip-view') || document.documentElement;
    var accent = getComputedStyle(accentHost).getPropertyValue('--pt-popup-accent').trim() || '#6366f1';
    var map = L.map(mapEl, { zoomControl: true, scrollWheelZoom: false });
    mapEl._leaflet_map = map;
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);
    if (latlngs.length >= 2) {
      L.polyline(latlngs, { color: accent, weight: 3, opacity: 0.92 }).addTo(map);
    }
    points.forEach(function (p) {
      L.circleMarker([p.lat, p.lng], {
        radius: p.kind === 'start' ? 11 : 8,
        color: p.kind === 'start' ? '#ffffff' : accent,
        weight: p.kind === 'start' ? 3 : 2,
        fillColor: p.kind === 'start' ? accent : '#ffffff',
        fillOpacity: 1
      }).addTo(map).bindPopup(p.label);
    });
    if (latlngs.length === 1) map.setView(latlngs[0], 6);
    else map.fitBounds(L.latLngBounds(latlngs), { padding: [28, 28], maxZoom: 12 });
    if (showPartialNote) {
      noteEl.textContent = plannedTripsT('mapPartialRoute', 'Some stops could not be located.');
      noteEl.classList.remove('hidden');
    }
    setTimeout(function () { if (mapEl._leaflet_map) mapEl._leaflet_map.invalidateSize(); }, 200);
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

      if (typeof L !== 'undefined') {
        var rootEl = document.getElementById('sharedTripContent');
        var mapEl = document.getElementById('sharedTripMap');
        var section = document.getElementById('sharedTripMapSection');
        var noteEl = document.getElementById('sharedTripMapNote');
        var points = await buildAllRoutePoints(trip, stops);
        if (points.length) {
          renderTripMap(rootEl, mapEl, noteEl, section, points, points.filter(function (p) { return p.kind === 'stop'; }).length < stops.length);
        }
      }
    } catch (err) {
      console.error(err);
      showError(plannedTripsT('sharedTripLoadError', 'Could not load shared trip.'));
    }
  }

  document.addEventListener('DOMContentLoaded', loadSharedTrip);
})();
