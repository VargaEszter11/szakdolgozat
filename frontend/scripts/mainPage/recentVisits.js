import { escapeHtml, t } from './helpers.js';
import { DEFAULT_IMAGE, placeImageUrl } from './places.js';

var MAX_RECENT = 3;

function renderLogCard(place) {
  var src = placeImageUrl(place);
  var fallback = DEFAULT_IMAGE;
  return (
    '<article class="travel-log-card main-recent-card" role="article">' +
    '<div class="log-image-wrapper">' +
    '<img src="' +
    escapeHtml(src) +
    '" alt="' +
    escapeHtml(place.name) +
    '" class="log-image" loading="lazy" ' +
    'onerror="this.onerror=null;this.src=\'' +
    escapeHtml(fallback) +
    '\';">' +
    '</div>' +
    '<div class="log-content">' +
    '<div class="log-header">' +
    '<div class="log-dest">' +
    '<h3 class="log-title">' +
    escapeHtml(place.name) +
    '</h3>' +
    '</div>' +
    '<span class="log-date">' +
    escapeHtml(place.date) +
    '</span>' +
    '</div>' +
    '<p class="log-notes">' +
    escapeHtml(place.description || t('mainPage.noNotes', 'No notes.')) +
    '</p>' +
    '</div>' +
    '</article>'
  );
}

export function renderRecentPlaces(places) {
  var container = document.getElementById('mainTravelLogs');
  if (!container) return;

  var sorted = places.slice().sort(function (a, b) {
    return (b.dateSortKey || 0) - (a.dateSortKey || 0);
  });
  var recent = sorted.slice(0, MAX_RECENT);

  if (recent.length === 0) {
    container.innerHTML =
      '<p class="travel-logs-empty muted">' +
      t('mainPage.noTravelsYet', 'No travels yet.') +
      ' <a href="visitedPlaces/add_new_place.html">' +
      t('visitedPlaces.addFirstPlace', 'Add your first place') +
      '</a>.</p>';
    return;
  }

  container.innerHTML = recent.map(renderLogCard).join('');
}
