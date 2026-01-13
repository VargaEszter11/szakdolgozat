const map = L.map('map').setView([20, 0], 2);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

async function geocodePlace(cityName, countryName) {
  const cacheKey = `${cityName},${countryName}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) return JSON.parse(cached);

  const query = `${cityName}, ${countryName}`;
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`;
  try {
    const response = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    const results = await response.json();
    if (!results || results.length === 0) return null;

    const coords = { lat: parseFloat(results[0].lat), lon: parseFloat(results[0].lon) };
    localStorage.setItem(cacheKey, JSON.stringify(coords));
    return coords;
  } catch (err) {
    console.error('Geocoding error:', cityName, err);
    return null;
  }
}

async function loadCities(places, batchSize = 5, delay = 500) {
  const markerGroup = L.featureGroup();

  for (let i = 0; i < places.length; i += batchSize) {
    const batch = places.slice(i, i + batchSize);

    const results = await Promise.all(
      batch.map(async place => {
        const coords = await geocodePlace(place.name, place.country);
        if (coords) {
          const marker = L.marker([coords.lat, coords.lon])
            .addTo(map)
            .bindPopup(`
              <b>${place.name}, ${place.country}</b><br>
              Visited: ${place.dateVisited}<br>
              ${place.description}
            `);
          markerGroup.addLayer(marker);
        } else {
          console.warn('City not found:', place.name);
        }
      })
    );

    await new Promise(r => setTimeout(r, delay));
  }

  if (markerGroup.getLayers().length > 0) {
    map.fitBounds(markerGroup.getBounds().pad(0.2));
  }
}

async function initMap() {
  try {
    const response = await fetch('../../../dummy_places/places.json');
    const data = await response.json();
    const places = data.places;

    await loadCities(places);
  } catch (err) {
    console.error('Error loading places:', err);
  }
}

window.addEventListener('DOMContentLoaded', initMap);
