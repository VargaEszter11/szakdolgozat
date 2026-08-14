import { escapeHtml, t } from './helpers.js';
import { getEuropeIsoList } from './europe.js';

function computeStats(places, tripCount) {
  var cities = {};
  var days = 0;
  places.forEach(function (p) {
    var city = String(p.place_name || '').trim().toLowerCase();
    if (city) cities[city] = true;
    days += p.daySpan || 0;
  });
  var europeList = getEuropeIsoList();
  var countries = europeList.filter(function (iso) {
    return places.some(function (p) {
      return p.europeIso === iso;
    });
  }).length;

  return {
    cities: Object.keys(cities).length,
    trips: tripCount || 0,
    countries: countries,
    days: days
  };
}

function statIcon(kind) {
  if (kind === 'cities') {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18"/><path d="M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6"/></svg>';
  }
  if (kind === 'trips') {
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">' +
      '<path d="M6.00391 10V5M11.0039 10V5M16.0039 10V5.5" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M5.01609 17C3.59614 17 2.88616 17 2.44503 16.5607C2.00391 16.1213 2.00391 15.4142 2.00391 14V8C2.00391 6.58579 2.00391 5.87868 2.44503 5.43934C2.88616 5 3.59614 5 5.01609 5H12.1005C15.5742 5 17.311 5 18.6402 5.70624C19.619 6.22633 20.4346 7.0055 20.9971 7.95786C21.7609 9.25111 21.8332 10.9794 21.9779 14.436C22.0168 15.3678 22.0363 15.8337 21.8542 16.1862C21.7204 16.4454 21.5135 16.6601 21.2591 16.8041C20.913 17 20.4449 17 19.5085 17H19.0039M9.00391 17H15.0039" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M7.00391 19C8.10848 19 9.00391 18.1046 9.00391 17C9.00391 15.8954 8.10848 15 7.00391 15C5.89934 15 5.00391 15.8954 5.00391 17C5.00391 18.1046 5.89934 19 7.00391 19Z"/>' +
      '<path d="M17.0039 19C18.1085 19 19.0039 18.1046 19.0039 17C19.0039 15.8954 18.1085 15 17.0039 15C15.8993 15 15.0039 15.8954 15.0039 17C15.0039 18.1046 15.8993 19 17.0039 19Z"/>' +
      '<path d="M1.99609 10.0009H15.3641C15.9911 10.0009 16.2041 10.3681 16.6841 10.9441C17.2361 11.4841 17.6093 11.8628 18.1241 11.9401C18.8441 12.0481 21.5081 11.9941 21.5081 11.9941" stroke-linecap="round"/>' +
      '</svg>'
    );
  }
  if (kind === 'countries') {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15 15 0 0 1 0 20"/><path d="M12 2a15 15 0 0 0 0 20"/></svg>';
  }
  return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>';
}

export function renderStats(places, tripCount) {
  var strip = document.getElementById('mainStatsStrip');
  if (!strip) return;

  var s = computeStats(places, tripCount);
  var items = [
    { key: 'cities', value: s.cities, label: t('mainPage.statCities', 'Cities'), icon: 'cities' },
    { key: 'trips', value: s.trips, label: t('mainPage.statTrips', 'Trips'), icon: 'trips' },
    {
      key: 'countries',
      value: s.countries,
      label: t('mainPage.statCountries', 'Countries'),
      icon: 'countries'
    },
    {
      key: 'days',
      value: s.days,
      label: t('mainPage.statDaysAbroad', 'Days abroad'),
      icon: 'days'
    }
  ];

  strip.hidden = false;
  strip.innerHTML = items
    .map(function (item) {
      return (
        '<div class="main-stat-card">' +
        '<div class="main-stat-icon" aria-hidden="true">' +
        statIcon(item.icon) +
        '</div>' +
        '<div class="main-stat-body">' +
        '<div class="main-stat-value">' +
        escapeHtml(String(item.value)) +
        '</div>' +
        '<div class="main-stat-label">' +
        escapeHtml(item.label) +
        '</div>' +
        '</div>' +
        '</div>'
      );
    })
    .join('');
}
