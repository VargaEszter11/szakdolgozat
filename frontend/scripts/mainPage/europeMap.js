import { cssVar, escapeHtml, t, tpl } from './helpers.js';
import {
  appIsoFromGeo,
  featureIso,
  getEuropeIsoList,
  getEuropeTotal,
  getVisitedEuropeanCountries,
  isEuropeFeature,
  resolveEuropeIso
} from './europe.js';
import { renderDiagram } from './europeDiagram.js';

var GEOJSON_URL =
  'https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson';

var HOME_GEOCODE_CACHE_KEY = 'planventure.homeCountryGeocode.v1';

var europeMap = null;
var europeLayer = null;
var homeOutlineLayer = null;
var geoJsonCache = null;
var lastVisitedMap = {};
var lastHomeIso = null;

var EUROPE_FOCUS_BOUNDS = [
  [34, -25],
  [66, 34]
];

function foldQuery(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function readHomeGeocodeCache(userId, query) {
  try {
    var raw = localStorage.getItem(HOME_GEOCODE_CACHE_KEY);
    if (!raw) return null;
    var parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    if (String(parsed.userId || '') !== String(userId || '')) return null;
    if (foldQuery(parsed.query) !== foldQuery(query)) return null;
    var code = String(parsed.countryCode || '')
      .trim()
      .toUpperCase();
    if (!code) return null;
    return { countryCode: code, query: parsed.query };
  } catch (e) {
    return null;
  }
}

function writeHomeGeocodeCache(userId, query, countryCode) {
  try {
    localStorage.setItem(
      HOME_GEOCODE_CACHE_KEY,
      JSON.stringify({
        userId: String(userId || ''),
        query: String(query || '').trim(),
        countryCode: String(countryCode || '')
          .trim()
          .toUpperCase(),
        cachedAt: Date.now()
      })
    );
  } catch (e) {
    /* ignore quota / private mode */
  }
}

function countryCodeFromNominatimHit(hit) {
  if (!hit) return '';
  var fromAddress =
    hit.address && (hit.address.country_code || hit.address.country_code_iso3166);
  var raw = String(fromAddress || '').trim().toUpperCase();
  if (!raw && hit.address && hit.address.country) {
    raw = resolveEuropeIso(hit.address.country) || '';
  }
  if (raw === 'UK') raw = 'GB';
  return raw;
}

function nominatimHomeCity(query) {
  if (window.TripMapHelper && typeof window.TripMapHelper.nominatimGeocode === 'function') {
    return window.TripMapHelper.nominatimGeocode(query, {
      addressdetails: true,
      featuretype: 'city'
    });
  }
  var url =
    'https://nominatim.openstreetmap.org/search?' +
    new URLSearchParams({
      q: String(query).trim(),
      format: 'json',
      limit: '1',
      addressdetails: '1',
      featuretype: 'city'
    });
  return fetch(url, { headers: { Accept: 'application/json' } })
    .then(function (res) {
      return res.ok ? res.json() : null;
    })
    .then(function (data) {
      return Array.isArray(data) && data.length ? data[0] : null;
    })
    .catch(function () {
      return null;
    });
}

function resolveHomeCountryIso(homeCity, userId) {
  var query = String(homeCity || '').trim();
  if (!query) return Promise.resolve(null);

  var cached = readHomeGeocodeCache(userId, query);
  if (cached && cached.countryCode) {
    return Promise.resolve(resolveEuropeIso(cached.countryCode) || cached.countryCode);
  }

  return nominatimHomeCity(query).then(function (hit) {
    var code = countryCodeFromNominatimHit(hit);
    if (!code) return null;
    writeHomeGeocodeCache(userId, query, code);
    return resolveEuropeIso(code) || code;
  });
}

function isHomeFeature(feature) {
  if (!lastHomeIso) return false;
  var geo = featureIso(feature);
  var app = appIsoFromGeo(geo);
  return app === lastHomeIso || geo === lastHomeIso;
}

function countryStyle(feature) {
  var geo = featureIso(feature);
  var app = appIsoFromGeo(geo);
  var visited = !!(lastVisitedMap[app] || lastVisitedMap[geo]);
  var accent = cssVar('--color-accent', '#DEBE56');
  var pageBg = cssVar('--color-page-bg', '#16161D');
  return {
    fillColor: visited ? accent : pageBg,
    weight: visited ? 1.35 : 1.1,
    color: visited
      ? cssVar('--color-accent-hover', '#e5c96a')
      : cssVar('--color-surface', '#2F2E2E'),
    fillOpacity: visited ? 1 : 0.92,
    opacity: 1,
    lineJoin: 'round',
    lineCap: 'round'
  };
}

function homeOutlineStyle() {
  return {
    fill: false,
    fillOpacity: 0,
    stroke: true,
    color: cssVar('--color-text', '#ffffff'),
    weight: 2.25,
    opacity: 1,
    lineJoin: 'round',
    lineCap: 'round',
    interactive: false
  };
}

function clearHomeOutline() {
  if (homeOutlineLayer && europeMap) {
    try {
      europeMap.removeLayer(homeOutlineLayer);
    } catch (e) {
      /* ignore */
    }
  }
  homeOutlineLayer = null;
}

function applyHomeOutline(features) {
  clearHomeOutline();
  var map = europeMap;
  if (!map || !lastHomeIso || !features || !features.length) return;

  var homeFeatures = features.filter(isHomeFeature);
  if (!homeFeatures.length) return;

  homeOutlineLayer = window.L.geoJSON(
    { type: 'FeatureCollection', features: homeFeatures },
    {
      style: homeOutlineStyle,
      interactive: false
    }
  ).addTo(map);

  try {
    homeOutlineLayer.bringToFront();
  } catch (e) {
    /* ignore */
  }
}

export function destroyEuropeMap() {
  clearHomeOutline();
  if (europeMap) {
    try {
      europeMap.remove();
    } catch (e) {
      /* ignore */
    }
    europeMap = null;
    europeLayer = null;
  }
  lastHomeIso = null;
}

function ensureEuropeMap() {
  var mapEl = document.getElementById('mainEuropeMap');
  if (!mapEl || typeof window.L === 'undefined') return null;
  if (europeMap) return europeMap;

  europeMap = window.L.map(mapEl, {
    zoomControl: false,
    attributionControl: false,
    scrollWheelZoom: false,
    dragging: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    touchZoom: false,
    tap: false,
    trackResize: true
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
  clearHomeOutline();

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
      var tip = String(name || geo);
      if (isHomeFeature(feature)) {
        tip =
          tpl(t('mainPage.homeCountryTooltip', 'Home · {{country}}'), {
            country: tip
          }) ||
          'Home · ' + tip;
      }
      layer.bindTooltip(tip, {
        sticky: true,
        direction: 'top',
        opacity: 0.95
      });
      layer.on('click', function (e) {
        if (window.L && window.L.DomEvent) {
          window.L.DomEvent.preventDefault(e);
          window.L.DomEvent.stopPropagation(e);
        }
      });
    }
  }).addTo(map);

  applyHomeOutline(filtered.features);

  try {
    map.fitBounds(window.L.latLngBounds(EUROPE_FOCUS_BOUNDS), {
      padding: [4, 4],
      maxZoom: 7
    });
  } catch (e) {
    /* ignore */
  }

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

/**
 * @param {Array} places
 * @param {{ homeCity?: string, userId?: string }} [options]
 */
export function renderEuropeCoverage(places, options) {
  options = options || {};
  var summaryEl = document.getElementById('mainEuropeChartSummary');
  var mapEl = document.getElementById('mainEuropeMap');

  lastVisitedMap = getVisitedEuropeanCountries(places);
  lastHomeIso = null;

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

  var homeCity = String(options.homeCity || '').trim();
  var userId = options.userId || localStorage.getItem('user_id') || '';

  Promise.all([
    loadGeoJson(),
    homeCity
      ? resolveHomeCountryIso(homeCity, userId).catch(function () {
        return null;
      })
      : Promise.resolve(null)
  ])
    .then(function (results) {
      var data = results[0];
      var homeIso = results[1];
      if (homeIso && resolveEuropeIso(homeIso)) {
        lastHomeIso = resolveEuropeIso(homeIso);
      } else if (homeIso && europeList.indexOf(homeIso) >= 0) {
        lastHomeIso = homeIso;
      } else {
        lastHomeIso = null;
      }
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
