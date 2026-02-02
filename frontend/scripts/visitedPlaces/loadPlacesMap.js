(function () {
  var STORAGE_KEY = 'visitedPlaces';
  var JSON_URL = '../../../dummy_places/places.json';
  var map;

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return months[d.getMonth()] + ' ' + d.getFullYear();
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

  function normalizePlace(item) {
    var placeName = item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.visitedDate || item.dateVisited || item.date;
    return {
      name: placeName.trim() || 'Unknown',
      country: country || '',
      displayName: name,
      dateVisited: formatDate(dateValue),
      description: item.description || item.notes || ''
    };
  }

  function getPlacesFromStorage() {
    var list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return list.map(normalizePlace);
  }

  async function geocodePlace(cityName, countryName) {
    var cacheKey = cityName + ',' + countryName;
    var cached = localStorage.getItem(cacheKey);
    if (cached) return JSON.parse(cached);

    var query = countryName ? cityName + ', ' + countryName : cityName;
    var url = 'https://nominatim.openstreetmap.org/search?format=json&q=' + encodeURIComponent(query);
    try {
      var response = await fetch(url, { headers: { 'Accept-Language': 'en' } });
      var results = await response.json();
      if (!results || results.length === 0) return null;

      var coords = { lat: parseFloat(results[0].lat), lon: parseFloat(results[0].lon) };
      localStorage.setItem(cacheKey, JSON.stringify(coords));
      return coords;
    } catch (err) {
      console.error('Geocoding error:', cityName, err);
      return null;
    }
  }

  async function loadCities(places, batchSize, delay) {
    batchSize = batchSize || 5;
    delay = delay || 500;
    var markerGroup = L.featureGroup();

    for (var i = 0; i < places.length; i += batchSize) {
      var batch = places.slice(i, i + batchSize);

      for (var j = 0; j < batch.length; j++) {
        var place = batch[j];
        var coords = await geocodePlace(place.name, place.country);
        if (coords) {
          var popupHtml = '<b>' + escapeHtml(place.displayName) + '</b><br>Visited: ' + escapeHtml(place.dateVisited) + '<br>' + escapeHtml(place.description);
          var marker = L.marker([coords.lat, coords.lon])
            .addTo(map)
            .bindPopup(popupHtml);
          markerGroup.addLayer(marker);
        } else {
          console.warn('City not found:', place.name);
        }
      }
      await new Promise(function (r) { setTimeout(r, delay); });
    }

    if (markerGroup.getLayers().length > 0) {
      map.fitBounds(markerGroup.getBounds().pad(0.2));
    }
  }

  async function initMap() {
    var mapEl = document.getElementById('map');
    if (!mapEl) return;

    await new Promise(function (r) { setTimeout(r, 50); });

    map = L.map('map').setView([20, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    setTimeout(function () {
      if (map) map.invalidateSize();
    }, 100);

    var places = [];
    try {
      var response = await fetch(JSON_URL);
      if (response.ok) {
        var data = await response.json();
        var list = data && data.places ? data.places : [];
        places = list.map(normalizePlace);
      }
    } catch (err) {
      console.warn('Could not load places.json for map, falling back to localStorage:', err);
    }
    if (places.length === 0) {
      places = getPlacesFromStorage();
    }

    await loadCities(places);
  }

  window.addEventListener('DOMContentLoaded', initMap);
})();
