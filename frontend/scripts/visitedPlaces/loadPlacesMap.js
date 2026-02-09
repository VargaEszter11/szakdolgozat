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
      description: item.description || item.notes || '',
      coordinates: item.coordinates || null  // Include stored coordinates
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

    loadCities(places);
  }

  window.addEventListener('DOMContentLoaded', initMap);
})();
