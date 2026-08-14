export function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function t(key, fallback) {
  if (window.i18n && window.i18n.t) {
    var v = window.i18n.t(key);
    if (v && v !== key) return v;
  }
  return fallback != null ? fallback : key;
}

export function tpl(template, vars) {
  return String(template || '').replace(/\{\{(\w+)\}\}/g, function (_, key) {
    return vars[key] != null ? String(vars[key]) : '';
  });
}

export function cssVar(name, fallback) {
  try {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  } catch (e) {
    return fallback;
  }
}

export function formatDate(value) {
  if (!value) return '—';
  var d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  var lang = localStorage.getItem('language') || 'en';
  var locale = lang === 'hu' ? 'hu-HU' : lang === 'de' ? 'de-DE' : 'en-GB';
  return d.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
}

export function formatVisitDates(startValue, endValue) {
  if (!startValue && !endValue) return '—';
  var startIso = String(startValue || '').trim().slice(0, 10);
  var endIso = String(endValue || '').trim().slice(0, 10);
  if (startIso && endIso && startIso !== endIso) {
    return formatDate(startIso) + ' – ' + formatDate(endIso);
  }
  return formatDate(startIso || endIso);
}

export function fetchJson(url) {
  return fetch(url).then(function (res) {
    if (!res.ok) {
      if (res.status === 404) return [];
      throw new Error('HTTP ' + res.status);
    }
    return res.json();
  });
}
