(function () {
  var STORAGE_KEY = 'visitedPlaces';
  var JSON_URL = '../../../dummy_places/places.json';
  var map;

  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long' });
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
    // API response uses: place_name, country, date, description, latitude, longitude
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    
    // Build coordinates object from latitude/longitude fields
    var coordinates = null;
    if (item.latitude != null && item.longitude != null) {
      coordinates = {
        lat: parseFloat(item.latitude),
        lon: parseFloat(item.longitude)
      };
    }
    
    return {
      name: placeName.trim() || 'Unknown',
      country: country || '',
      displayName: name,
      dateVisited: formatDate(dateValue),
      description: item.description || item.notes || '',
      coordinates: coordinates
    };
  }

  function getPlacesFromStorage() {
    var list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    return list.map(normalizePlace);
  }

  function loadCities(places) {
    var markerGroup = L.featureGroup();

    for (var i = 0; i < places.length; i++) {
      var place = places[i];
      
      // Only use stored coordinates
      if (place.coordinates && place.coordinates.lat && place.coordinates.lon) {
        var coords = place.coordinates;
        var popupHtml = '<b>' + escapeHtml(place.displayName) + '</b><br>Visited: ' + escapeHtml(place.dateVisited) + '<br>' + escapeHtml(place.description);
        var marker = L.marker([coords.lat, coords.lon])
          .addTo(map)
          .bindPopup(popupHtml);
        markerGroup.addLayer(marker);
      } else {
        console.warn('Place has no coordinates:', place.name);
      }
    }

    if (markerGroup.getLayers().length > 0) {
      map.fitBounds(markerGroup.getBounds().pad(0.2));
    }
  }

  async function initMap() {
    var mapEl = document.getElementById('map');
    if (!mapEl) return;

    map = L.map('map').setView([20, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    setTimeout(function () {
      if (map) map.invalidateSize();
    }, 100);

    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.warn('No user_id found. User not logged in.');
      return;
    }

    var places = [];
    try {
      var apiUrl = '/api/users/' + userId + '/visited-places';
      var response = await fetch(apiUrl);
      if (response.ok) {
        var data = await response.json();
        console.log('Raw API data:', data);
        // API returns array of visited places directly
        var list = Array.isArray(data) ? data : [];
        places = list.map(normalizePlace);
        console.log('Normalized places:', places);
        console.log('Places with coordinates:', places.filter(function(p) { return p.coordinates; }).length);
      } else if (response.status === 404) {
        console.log('No places found for this user.');
        places = [];
      } else {
        throw new Error('API request failed: ' + response.status);
      }
    } catch (err) {
      console.error('Failed to load visited places from API:', err);
      places = [];
    }

    console.log('Loading cities on map. Total places:', places.length);
    loadCities(places);
  }

  window.addEventListener('DOMContentLoaded', initMap);
})();
