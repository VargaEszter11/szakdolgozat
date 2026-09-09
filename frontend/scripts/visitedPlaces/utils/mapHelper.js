/**
 * Shared Leaflet map helpers: create map, OSM layer, markers with popups, polyline, fitBounds.
 * Use from loadPlacesMap, trip details modal, etc.
 */
(function (global) {
  var TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
  var TILE_ATTR = '© OpenStreetMap contributors';

  function createMap(containerEl, center, zoom) {
    if (!containerEl || typeof global.L === 'undefined') return null;
    var centerPoint = center && center.length === 2 ? center : [20, 0];
    var z = zoom != null ? zoom : 6;
    var map = global.L.map(containerEl).setView(centerPoint, z);
    global.L.tileLayer(TILE_URL, { attribution: TILE_ATTR }).addTo(map);
    return map;
  }

  function addMarker(map, lat, lon, popupContent) {
    if (!map || typeof global.L === 'undefined') return null;
    var m = global.L.marker([lat, lon]).addTo(map);
    if (popupContent) m.bindPopup(popupContent);
    return m;
  }

  function addMarkersWithPopups(map, points) {
    if (!map || !points || !points.length) return;
    for (var i = 0; i < points.length; i++) {
      var p = points[i];
      if (p.lat == null || p.lon == null) continue;
      addMarker(map, p.lat, p.lon, p.popupContent || p.label || null);
    }
  }

  function addPolyline(map, points, options) {
    if (!map || !points || points.length < 2 || typeof global.L === 'undefined') return;
    var latLngs = points.map(function (p) { return [p.lat, p.lon]; });
    var opts = options || { color: '#2563eb', weight: 3 };
    global.L.polyline(latLngs, opts).addTo(map);
  }

  function fitBounds(map, points, padding) {
    if (!map || !points || points.length === 0 || typeof global.L === 'undefined') return;
    var latLngs = points.map(function (p) { return [p.lat, p.lon]; });
    var pad = padding != null ? padding : [24, 24];
    map.fitBounds(latLngs, { padding: pad });
  }

  /**
   * Draw a route map: markers in order + polyline connecting them, then fit bounds.
   * points: array of { lat, lon, popupContent? }
   */
  function drawRouteMap(containerEl, points) {
    if (!points || points.length === 0) return null;
    var valid = points.filter(function (p) { return p.lat != null && p.lon != null; });
    if (valid.length === 0) return null;
    var map = createMap(containerEl, [valid[0].lat, valid[0].lon], 8);
    if (!map) return null;
    addMarkersWithPopups(map, valid);
    if (valid.length > 1) {
      addPolyline(map, valid);
      fitBounds(map, valid);
    }
    setTimeout(function () { if (map.invalidateSize) map.invalidateSize(); }, 100);
    return map;
  }

  global.MapHelper = {
    createMap: createMap,
    addMarker: addMarker,
    addMarkersWithPopups: addMarkersWithPopups,
    addPolyline: addPolyline,
    fitBounds: fitBounds,
    drawRouteMap: drawRouteMap
  };
})(typeof window !== 'undefined' ? window : this);
