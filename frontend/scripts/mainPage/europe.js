/** App ISO codes match GeoJSON / flagcdn (KZ for Kazakhstan). */
export var ISO_TO_GEO = {};
export var GEO_TO_APP = {};

export function getEuropeIsoList() {
  if (window.Countries && Array.isArray(window.Countries.EUROPE_ISO_LIST)) {
    return window.Countries.EUROPE_ISO_LIST;
  }
  return [];
}

export function getEuropeTotal() {
  return getEuropeIsoList().length;
}

function europeSet() {
  var set = {};
  getEuropeIsoList().forEach(function (iso) {
    set[iso] = 1;
  });
  return set;
}

export function resolveEuropeIso(country) {
  if (window.Countries && window.Countries.europeIso) {
    return window.Countries.europeIso(country);
  }
  var europe = europeSet();
  var raw = String(country || '').trim().toUpperCase();
  if (raw === 'UK') raw = 'GB';
  if (raw.length === 2 && europe[raw]) return raw;
  return null;
}

export function resolveAnyIso(country) {
  var eu = resolveEuropeIso(country);
  if (eu) return eu;
  if (window.Countries && window.Countries.normalizeCode) {
    var n = window.Countries.normalizeCode(country);
    if (n && n.length === 2) return n.toUpperCase();
  }
  var raw = String(country || '').trim().toUpperCase();
  if (raw === 'UK') return 'GB';
  if (raw.length === 2 && /^[A-Z]{2}$/.test(raw)) return raw;
  return null;
}

export function getVisitedEuropeanCountries(places) {
  var visited = {};
  places.forEach(function (place) {
    if (place.europeIso) visited[place.europeIso] = true;
  });
  return visited;
}

export function featureIso(feature) {
  var p = (feature && feature.properties) || {};
  var raw = String(
    p['ISO3166-1-Alpha-2'] ||
    p.ISO_A2 ||
    p.iso_a2 ||
    p.ISO2 ||
    p.iso2 ||
    ''
  )
    .trim()
    .toUpperCase();

  if (!raw || raw === '-99' || raw === 'NULL') {
    var a3 = String(
      p['ISO3166-1-Alpha-3'] || p.ISO_A3 || p.iso_a3 || ''
    )
      .trim()
      .toUpperCase();
    if (a3 === 'FRA') raw = 'FR';
    else if (a3 === 'NOR') raw = 'NO';
  }

  if (!raw || raw === '-99' || raw === 'NULL') {
    var name = String(p.name || p.NAME || p.ADMIN || '')
      .trim()
      .toLowerCase();
    if (name === 'france') raw = 'FR';
    else if (name === 'norway') raw = 'NO';
  }

  if (!raw || raw === '-99' || raw === 'NULL') return '';
  if (raw === 'UK') return 'GB';
  return raw;
}

export function appIsoFromGeo(geoIso) {
  if (!geoIso) return null;
  if (GEO_TO_APP[geoIso]) return GEO_TO_APP[geoIso];
  return geoIso;
}

export function geoIsoFromApp(appIso) {
  if (!appIso) return null;
  return ISO_TO_GEO[appIso] || appIso;
}

export function isEuropeFeature(feature) {
  var geo = featureIso(feature);
  if (!geo) return false;
  var europe = europeSet();
  var app = appIsoFromGeo(geo);
  return !!(europe[app] || europe[geo]);
}
