(function () {
  var map;
  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  // i18n helpers
  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      var v = window.i18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
  }

  function tpl(template, vars) {
    if (!template || typeof template !== 'string') return '';
    return template.replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  // date / HTML helpers
  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
  }

  function formatVisitDates(startValue, endValue) {
    if (!startValue && !endValue) return '—';
    var startIso = String(startValue || '').trim().slice(0, 10);
    var endIso = String(endValue || '').trim().slice(0, 10);
    if (startIso && endIso && startIso !== endIso) {
      return formatDate(startIso) + ' – ' + formatDate(endIso);
    }
    return formatDate(startIso || endIso);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Status line under the map
  function setMapStatus(text) {
    var el = document.getElementById('mapStatus');
    if (!el) return;
    if (!text) {
      el.hidden = true;
      el.textContent = '';
      return;
    }
    el.hidden = false;
    el.textContent = text;
  }

  // Normalize API place
  function normalizePlace(item) {
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name =
      window.Countries && window.Countries.formatPlace
        ? window.Countries.formatPlace(placeName, country)
        : placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = t('visitedPlaces.unnamedPlace', 'Unnamed place');
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var endDateValue = item.end_date || item.endDate || item.visitedEndDate;

    var coordinates = null;
    if (item.latitude != null && item.longitude != null) {
      coordinates = {
        lat: parseFloat(item.latitude),
        lon: parseFloat(item.longitude)
      };
    }

    return {
      name: placeName.trim() || t('visitedPlaces.unnamedPlace', 'Unnamed place'),
      country: country || '',
      displayName: name,
      dateVisited: formatVisitDates(dateValue, endDateValue),
      description: item.description || item.notes || '',
      coordinates: coordinates
    };
  }

  // Place markers
  function loadCities(places) {
    var visitedLabel = t('visitedPlaces.mapVisitedLabel', 'Visited:');
    var points = [];

    for (var i = 0; i < places.length; i++) {
      var place = places[i];

      // Skip places without coordinates
      if (place.coordinates && place.coordinates.lat && place.coordinates.lon) {
        var coords = place.coordinates;
        var popupHtml =
          '<b>' + escapeHtml(place.displayName) + '</b><br>' +
          escapeHtml(visitedLabel) + ' ' + escapeHtml(place.dateVisited);
        if (place.description) {
          popupHtml += '<br>' + escapeHtml(place.description);
        }
        points.push({
          lat: coords.lat,
          lon: coords.lon,
          popupContent: popupHtml
        });
      }
    }

    if (window.MapHelper) {
      MapHelper.addMarkersWithPopups(map, points);
      if (points.length === 1) {
        // Single marker: Europe overview instead of street-level zoom
        var EUROPE_BOUNDS = [[34, -25], [66, 34]];
        map.fitBounds(EUROPE_BOUNDS, { padding: [24, 24] });
      } else if (points.length > 1) {
        MapHelper.fitBounds(map, points);
      }
    }

    var shown = points.length;
    var total = places.length;

    if (total === 0) {
      setMapStatus(t('visitedPlaces.mapEmpty', 'No places to show on the map yet.'));
    } else if (shown < total) {
      setMapStatus(
        tpl(t('visitedPlaces.mapNoCoordinates', '{{shown}} of {{total}} places have coordinates and are shown on the map.'), {
          shown: shown,
          total: total
        })
      );
    } else {
      setMapStatus(null);
    }
  }

  // Create map, fetch places, draw markers
  async function initMap() {
    var mapEl = document.getElementById('map');
    if (!mapEl) return;

    if (window.MapHelper) {
      map = MapHelper.createMap(mapEl, [20, 0], 2);
    } else if (typeof L !== 'undefined') {
      map = L.map(mapEl).setView([20, 0], 2);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(map);
    }
    if (!map) return;

    setTimeout(function () {
      if (map) map.invalidateSize();
    }, 100);

    var userId = localStorage.getItem('user_id');
    if (!userId) {
      setMapStatus(t('visitedPlaces.mapLoadFailed', 'Could not load places for the map.'));
      if (window.markAppReady) window.markAppReady();
      return;
    }

    var places = [];
    try {
      var apiUrl = '/api/users/' + userId + '/visited-places';
      var response = await fetch(apiUrl);
      if (response.ok) {
        var data = await response.json();
        var list = Array.isArray(data) ? data : [];
        places = list.map(normalizePlace);
      } else if (response.status === 404) {
        places = [];
      } else {
        throw new Error('API request failed: ' + response.status);
      }
    } catch (err) {
      setMapStatus(t('visitedPlaces.mapLoadFailed', 'Could not load places for the map.'));
      if (window.markAppReady) window.markAppReady();
      return;
    }

    loadCities(places);
    if (window.markAppReady) window.markAppReady();
  }

  window.addEventListener('DOMContentLoaded', initMap);
})();
