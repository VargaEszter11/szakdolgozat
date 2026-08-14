import { cssVar, escapeHtml, t, tpl } from './helpers.js';
import {
  appIsoFromGeo,
  featureIso,
  getEuropeIsoList,
  getEuropeTotal,
  getVisitedEuropeanCountries,
  isEuropeFeature
} from './europe.js';
import { renderDiagram } from './europeDiagram.js';

var GEOJSON_URL =
  'https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson';

var europeMap = null;
var europeLayer = null;
var geoJsonCache = null;
var lastVisitedMap = {};

var EUROPE_FOCUS_BOUNDS = [
  [34, -25],
  [66, 34]
];

function countryStyle(feature) {
  var geo = featureIso(feature);
  var app = appIsoFromGeo(geo);
  var visited = !!(lastVisitedMap[app] || lastVisitedMap[geo]);
  var accent = cssVar('--color-accent', '#DEBE56');
  var pageBg = cssVar('--color-page-bg', '#16161D');
  return {
    fillColor: visited ? accent : pageBg,
    weight: visited ? 1.35 : 1.1,
    color: visited ? cssVar('--color-accent-hover', '#e5c96a') : cssVar('--color-surface', '#2F2E2E'),
    fillOpacity: visited ? 1 : 0.92,
    opacity: 1
  };
}

export function destroyEuropeMap() {
  if (europeMap) {
    try {
      europeMap.remove();
    } catch (e) { /* ignore */ }
    europeMap = null;
    europeLayer = null;
  }
}

function ensureEuropeMap() {
  var mapEl = document.getElementById('mainEuropeMap');
  if (!mapEl || typeof window.L === 'undefined') return null;
  if (europeMap) return europeMap;

  europeMap = window.L.map(mapEl, {
    zoomControl: false,
    attributionControl: false,
    scrollWheelZoom: false,
    dragging: true,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false
  });
  europeMap.fitBounds(window.L.latLngBounds(EUROPE_FOCUS_BOUNDS), {
    padding: [6, 6],
    maxZoom: 6.5
  });
  return europeMap;
}

function applyGeoJson(geojson) {
  var map = ensureEuropeMap();
  if (!map || !geojson) return;

  var filtered = {
    type: 'FeatureCollection',
    features: (geojson.features || []).filter(isEuropeFeature)
  };

  if (europeLayer) {
    map.removeLayer(europeLayer);
    europeLayer = null;
  }

  europeLayer = window.L.geoJSON(filtered, {
    style: countryStyle,
    onEachFeature: function (feature, layer) {
      var geo = featureIso(feature);
      var app = appIsoFromGeo(geo);
      var name =
        (window.Countries && window.Countries.displayName
          ? window.Countries.displayName(app || geo)
          : null) ||
        (feature.properties && (feature.properties.name || feature.properties.NAME)) ||
        geo;
      layer.bindTooltip(String(name || geo), {
        sticky: true,
        direction: 'top',
        opacity: 0.95
      });
    }
  }).addTo(map);

  try {
    map.fitBounds(window.L.latLngBounds(EUROPE_FOCUS_BOUNDS), {
      padding: [4, 4],
      maxZoom: 7
    });
  } catch (e) { /* ignore */ }

  setTimeout(function () {
    if (europeMap) europeMap.invalidateSize();
  }, 80);
}

function loadGeoJson() {
  if (geoJsonCache) {
    return Promise.resolve(geoJsonCache);
  }
  return fetch(GEOJSON_URL)
    .then(function (res) {
      if (!res.ok) throw new Error('geojson ' + res.status);
      return res.json();
    })
    .then(function (data) {
      geoJsonCache = data;
      return data;
    });
}

export function renderEuropeCoverage(places) {
  var summaryEl = document.getElementById('mainEuropeChartSummary');
  var mapEl = document.getElementById('mainEuropeMap');

  lastVisitedMap = getVisitedEuropeanCountries(places);
  var europeList = getEuropeIsoList();
  var europeTotal = getEuropeTotal();
  var visitedCount = europeList.filter(function (iso) {
    return lastVisitedMap[iso];
  }).length;
  var visitedRatio = europeTotal > 0 ? visitedCount / europeTotal : 0;

  if (summaryEl) {
    summaryEl.hidden = false;
    summaryEl.textContent = tpl(
      t('mainPage.europeCountriesCount', '{{visited}} of {{total}} European countries'),
      { visited: visitedCount, total: europeTotal }
    );
  }

  var chartAria = escapeHtml(
    tpl(t('mainPage.europeCountriesCount', '{{visited}} of {{total}} European countries'), {
      visited: visitedCount,
      total: europeTotal
    })
  );

  renderDiagram(visitedCount, visitedRatio, chartAria);

  if (!mapEl) return;

  if (typeof window.L === 'undefined') {
    mapEl.innerHTML =
      '<p class="muted main-europe-map-fallback">' +
      escapeHtml(t('mainPage.mapUnavailable', 'Map could not be loaded.')) +
      '</p>';
    return;
  }

  loadGeoJson()
    .then(function (data) {
      applyGeoJson(data);
    })
    .catch(function (err) {
      console.error('Europe map GeoJSON failed:', err);
      mapEl.innerHTML =
        '<p class="muted main-europe-map-fallback">' +
        escapeHtml(t('mainPage.mapUnavailable', 'Map could not be loaded.')) +
        '</p>';
    });
}
