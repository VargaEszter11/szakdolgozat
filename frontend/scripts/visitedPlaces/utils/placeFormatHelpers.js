(function (global) {
  'use strict';

  var DEFAULT_IMAGE = '/pictures/placeholder.png';
  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function t(key, fallback) {
    if (global.i18n && global.i18n.t) {
      var v = global.i18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
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

  function tpl(template, vars) {
    if (!template || typeof template !== 'string') return '';
    return template.replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  function toIsoDateInput(value) {
    if (!value) return '';
    var s = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
    var d = new Date(s);
    if (isNaN(d.getTime())) return '';
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
  }

  function formatVisitDates(startValue, endValue) {
    var startIso = toIsoDateInput(startValue);
    var endIso = toIsoDateInput(endValue);
    if (!startIso && !endIso) return '—';
    if (startIso && endIso && startIso !== endIso) {
      return formatDate(startIso) + ' – ' + formatDate(endIso);
    }
    return formatDate(startIso || endIso);
  }

  function formatRatingDisplay(rating) {
    if (rating == null || rating === '') return '—';
    var n = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    return String(n) + '/5';
  }

  // Normalize FastAPI error body to a readable string
  function responseDetail(res) {
    return res.json().catch(function () { return null; }).then(function (j) {
      if (!j) return 'HTTP ' + res.status;
      var d = j.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) {
        return d.map(function (e) {
          if (typeof e === 'string') return e;
          return (e.msg || '') + (e.loc ? ' (' + e.loc.join('.') + ')' : '');
        }).filter(Boolean).join('; ') || ('HTTP ' + res.status);
      }
      if (d != null && typeof d === 'object') return JSON.stringify(d);
      return res.statusText || ('HTTP ' + res.status);
    });
  }

  function fetchPlaceImages(placeId) {
    return fetch('/api/visited-places/' + placeId + '/images')
      .then(function (res) {
        return res.ok ? res.json() : [];
      })
      .catch(function () {
        return [];
      });
  }

  function starsHtml(rating) {
    rating = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    var html = '';
    for (var i = 1; i <= 5; i++) {
      var filled = i <= rating ? ' place-star-filled' : '';
      html += '<span class="place-star' + filled + '" aria-hidden="true">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
        '</span>';
    }
    return html;
  }

  function countryLabel(value) {
    if (global.Countries && global.Countries.displayName) {
      return global.Countries.displayName(value);
    }
    return String(value || '').trim();
  }

  function formatPlaceTitle(placeName, country) {
    if (global.Countries && global.Countries.formatPlace) {
      return global.Countries.formatPlace(placeName, country);
    }
    var city = String(placeName || '').trim();
    var c = countryLabel(country);
    if (!city) return c || t('visitedPlaces.unnamedPlace', 'Unnamed place');
    return c ? city + ', ' + c : city;
  }

  // Map API place
  function normalizePlace(item, index) {
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = formatPlaceTitle(placeName, country);
    if (!name.trim()) name = t('visitedPlaces.unnamedPlace', 'Unnamed place');
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var endDateValue = item.end_date || item.endDate || item.visitedEndDate;
    var d = dateValue ? new Date(dateValue) : null;
    var endD = endDateValue ? new Date(endDateValue) : null;
    var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
    if (endD && !isNaN(endD.getTime()) && endD.getTime() > dateSortKey) {
      dateSortKey = endD.getTime();
    }
    var rawDescription = item.description || item.notes || '';
    var rawPhotoPath = item.photo_path != null && item.photo_path !== '' ? String(item.photo_path) : null;
    return {
      id: item.id != null && item.id !== '' ? item.id : (placeName + '-' + (dateValue || '') + '-' + index),
      name: name,
      place_name: placeName,
      country: country,
      date: formatVisitDates(dateValue, endDateValue),
      dateIso: toIsoDateInput(dateValue),
      endDateIso: toIsoDateInput(endDateValue),
      dateSortKey: dateSortKey,
      rating: item.rating != null ? item.rating : 0,
      description: rawDescription,
      photo_path: rawPhotoPath,
      image: item.image || item.photo_path || DEFAULT_IMAGE,
      coordinates: item.coordinates || null,
      latitude: item.latitude != null ? item.latitude : null,
      longitude: item.longitude != null ? item.longitude : null
    };
  }

  // Gallery URLs
  function collectPhotoUrls(place, images) {
    var urls = [];
    var seen = {};
    function add(u) {
      if (!u || typeof u !== 'string') return;
      if (seen[u]) return;
      seen[u] = true;
      urls.push(u);
    }
    (images || []).forEach(function (im) {
      add(im.image_path);
    });
    if (place && place.photo_path) add(place.photo_path);
    return urls;
  }

  global.PlaceFormatHelpers = {
    DEFAULT_IMAGE: DEFAULT_IMAGE,
    t: t,
    escapeHtml: escapeHtml,
    tpl: tpl,
    toIsoDateInput: toIsoDateInput,
    formatDate: formatDate,
    formatVisitDates: formatVisitDates,
    formatRatingDisplay: formatRatingDisplay,
    responseDetail: responseDetail,
    fetchPlaceImages: fetchPlaceImages,
    starsHtml: starsHtml,
    countryLabel: countryLabel,
    formatPlaceTitle: formatPlaceTitle,
    normalizePlace: normalizePlace,
    collectPhotoUrls: collectPhotoUrls
  };
})(window);
