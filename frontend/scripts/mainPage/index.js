import { fetchJson, t, tpl } from './helpers.js';
import { normalizePlace } from './places.js';
import { renderRecentPlaces } from './recentVisits.js';
import { renderStats } from './stats.js';
import { destroyEuropeMap, renderEuropeCoverage } from './europeMap.js';

function reveal() {
  if (window.markAppReady) window.markAppReady();
}

function render(places, tripCount, homeCity) {
  renderStats(places, tripCount);
  renderRecentPlaces(places);
  renderEuropeCoverage(places, {
    homeCity: homeCity || '',
    userId: localStorage.getItem('user_id') || ''
  });
  if (window.i18n && window.i18n.applyToPage) window.i18n.applyToPage();
  reveal();
}

function showMessageInBoth(msgHtml) {
  var container = document.getElementById('mainTravelLogs');
  var strip = document.getElementById('mainStatsStrip');
  var diagramEl = document.getElementById('mainEuropeDiagram');
  var mapEl = document.getElementById('mainEuropeMap');
  var summaryEl = document.getElementById('mainEuropeChartSummary');
  if (strip) {
    strip.hidden = true;
    strip.innerHTML = '';
  }
  if (container) container.innerHTML = '<p class="travel-logs-empty muted">' + msgHtml + '</p>';
  destroyEuropeMap();
  if (diagramEl) diagramEl.innerHTML = '';
  if (mapEl) mapEl.innerHTML = '';
  if (summaryEl) summaryEl.hidden = true;
  if (window.i18n && window.i18n.applyToPage) window.i18n.applyToPage();
  reveal();
}

function loadTravelLog() {
  var userId = localStorage.getItem('user_id');
  if (!userId) {
    showMessageInBoth(
      tpl(t('mainPage.loginRequired', 'Please <a href="{{href}}">log in</a> to see your travel log.'), {
        href: '/login'
      })
    );
    return;
  }

  var uid = encodeURIComponent(userId);
  Promise.all([
    fetchJson('/api/users/' + uid + '/visited-places'),
    fetchJson('/api/planned-trips').catch(function () {
      return [];
    }),
    fetch('/api/users/' + uid)
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .catch(function () {
        return null;
      })
  ])
    .then(function (results) {
      var placesRaw = Array.isArray(results[0]) ? results[0] : [];
      var tripsRaw = Array.isArray(results[1]) ? results[1] : [];
      var user = results[2] && typeof results[2] === 'object' ? results[2] : null;
      var homeCity = user && user.home_city ? String(user.home_city).trim() : '';
      render(placesRaw.map(normalizePlace), tripsRaw.length, homeCity);
    })
    .catch(function (err) {
      console.error('Failed to load travel log:', err);
      showMessageInBoth(
        t('mainPage.loadFailed', 'Failed to load travel log. Please try again later.')
      );
    });
}

function startWhenLeafletReady() {
  if (typeof window.L === 'undefined') {
    setTimeout(startWhenLeafletReady, 30);
    return;
  }
  loadTravelLog();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startWhenLeafletReady);
} else {
  startWhenLeafletReady();
}

document.addEventListener('app:languagechange', function () {
  var strip = document.getElementById('mainStatsStrip');
  if (strip && !strip.hidden && strip.children.length) {
    loadTravelLog();
  }
});
