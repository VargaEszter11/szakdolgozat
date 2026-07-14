(function () {
  var MAX_RECENT = 3;

  var EUROPE_ISO_LIST = [
    'AL', 'AD', 'AT', 'BE', 'BA', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU',
    'IS', 'IE', 'IT', 'XK', 'LV', 'LI', 'LT', 'LU', 'MT', 'MD', 'MC', 'ME', 'NL', 'MK', 'NO', 'PL',
    'PT', 'RO', 'RU', 'SM', 'RS', 'SK', 'SI', 'ES', 'SE', 'CH', 'GB', 'TR', 'UA', 'BY', 'VA'
  ];

  var EUROPE = {};
  EUROPE_ISO_LIST.forEach(function (iso) { EUROPE[iso] = 1; });

  var NAME_TO_ISO = {
    albania: 'AL', andorra: 'AD', austria: 'AT', belgium: 'BE', bosnia: 'BA',
    'bosnia and herzegovina': 'BA', bulgaria: 'BG', croatia: 'HR', cyprus: 'CY',
    'czech republic': 'CZ', czechia: 'CZ', denmark: 'DK', estonia: 'EE',
    finland: 'FI', france: 'FR', germany: 'DE', greece: 'GR', hungary: 'HU',
    iceland: 'IS', ireland: 'IE', italy: 'IT', kosovo: 'XK', latvia: 'LV',
    liechtenstein: 'LI', lithuania: 'LT', luxembourg: 'LU', malta: 'MT',
    moldova: 'MD', monaco: 'MC', montenegro: 'ME', netherlands: 'NL',
    'north macedonia': 'MK', macedonia: 'MK', norway: 'NO', poland: 'PL',
    portugal: 'PT', romania: 'RO', russia: 'RU', 'san marino': 'SM', serbia: 'RS',
    slovakia: 'SK', slovenia: 'SI', spain: 'ES', sweden: 'SE', switzerland: 'CH',
    'united kingdom': 'GB', uk: 'GB', england: 'GB', scotland: 'GB', wales: 'GB',
    turkey: 'TR', ukraine: 'UA', belarus: 'BY', vatican: 'VA',
    magyarorszag: 'HU', deutschland: 'DE', osterreich: 'AT', schweiz: 'CH',
    spanien: 'ES', italien: 'IT', frankreich: 'FR', polen: 'PL', ungarn: 'HU',
    niederlande: 'NL', belgien: 'BE', schweden: 'SE', norwegen: 'NO',
    finnland: 'FI', irland: 'IE', bulgarien: 'BG', serbien: 'RS', kroatien: 'HR',
    slowakei: 'SK', slowenien: 'SI', tschechien: 'CZ', griechenland: 'GR',
    grossbritannien: 'GB', turkei: 'TR', island: 'IS'
  };

  var EUROPE_TOTAL = EUROPE_ISO_LIST.length;

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function t(key, fallback) {
    if (window.i18n && window.i18n.t) {
      var v = window.i18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
  }

  function tpl(template, vars) {
    return String(template || '').replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return String(value);
    var lang = localStorage.getItem('language') || 'en';
    var locale = lang === 'hu' ? 'hu-HU' : lang === 'de' ? 'de-DE' : 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
  }

  function formatVisitDates(startValue, endValue) {
    if (!startValue && !endValue) return '—';
    var startIso = String(startValue || '').trim().slice(0, 10);
    var endIso = String(endValue || '').trim().slice(0, 10);
    if (startIso && endIso && startIso !== endIso) {
      return formatDate(startIso) + ' – ' + formatDate(endIso);
    }
    return formatDate(startIso || endIso);
  }

  function normalizeCountryKey(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function resolveEuropeIso(country) {
    var raw = String(country || '').trim();
    if (!raw) return null;

    var upper = raw.toUpperCase();
    if (upper.length === 2 && EUROPE[upper]) {
      return upper === 'UK' ? 'GB' : upper;
    }

    var key = normalizeCountryKey(raw);
    if (NAME_TO_ISO[key]) return NAME_TO_ISO[key];

    var keys = Object.keys(NAME_TO_ISO);
    for (var i = 0; i < keys.length; i++) {
      if (key.indexOf(keys[i]) >= 0 || keys[i].indexOf(key) >= 0) {
        return NAME_TO_ISO[keys[i]];
      }
    }

    return null;
  }

  function normalizePlace(item) {
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = placeName + (country ? ', ' + country : '');
    if (!name.trim()) name = 'Unnamed place';

    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var endDateValue = item.end_date || item.endDate || item.visitedEndDate;
    var d = dateValue ? new Date(dateValue) : null;
    var endD = endDateValue ? new Date(endDateValue) : null;
    var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
    if (endD && !isNaN(endD.getTime()) && endD.getTime() > dateSortKey) {
      dateSortKey = endD.getTime();
    }

    return {
      name: name,
      country: country,
      europeIso: resolveEuropeIso(country),
      date: formatVisitDates(dateValue, endDateValue),
      dateSortKey: dateSortKey,
      description: item.description || item.notes || ''
    };
  }

  function getVisitedEuropeanCountries(places) {
    var visited = {};
    places.forEach(function (place) {
      if (place.europeIso) visited[place.europeIso] = true;
    });
    return visited;
  }

  function piePoint(cx, cy, r, angleDeg) {
    var rad = (angleDeg - 90) * Math.PI / 180;
    return {
      x: +(cx + r * Math.cos(rad)).toFixed(2),
      y: +(cy + r * Math.sin(rad)).toFixed(2)
    };
  }

  function pieSlice(cx, cy, r, startDeg, endDeg) {
    if (endDeg - startDeg >= 359.999) {
      return 'M' + cx + ' ' + cy + ' m-' + r + ',0 a' + r + ',' + r +
        ' 0 1,1 ' + (r * 2) + ',0 a' + r + ',' + r + ' 0 1,1 -' + (r * 2) + ',0';
    }
    var start = piePoint(cx, cy, r, startDeg);
    var end = piePoint(cx, cy, r, endDeg);
    var large = (endDeg - startDeg) > 180 ? 1 : 0;
    return 'M' + cx + ' ' + cy + ' L' + start.x + ' ' + start.y +
      ' A' + r + ' ' + r + ' 0 ' + large + ' 1 ' + end.x + ' ' + end.y + ' Z';
  }

  function renderEuropeChart(places) {
    var chartEl = document.getElementById('mainEuropeChart');
    var summaryEl = document.getElementById('mainEuropeChartSummary');
    if (!chartEl) return;

    var visitedMap = getVisitedEuropeanCountries(places);
    var visitedCount = EUROPE_ISO_LIST.filter(function (iso) {
      return visitedMap[iso];
    }).length;
    var visitedRatio = EUROPE_TOTAL > 0 ? visitedCount / EUROPE_TOTAL : 0;

    if (summaryEl) {
      summaryEl.hidden = false;
      summaryEl.textContent = tpl(
        t('mainPage.europeCountriesCount', '{{visited}} of {{total}} European countries'),
        { visited: visitedCount, total: EUROPE_TOTAL }
      );
    }

    var centerLabel = visitedCount + ' / ' + EUROPE_TOTAL;

    var chartAria = escapeHtml(tpl(
      t('mainPage.europeCountriesCount', '{{visited}} of {{total}} European countries'),
      { visited: visitedCount, total: EUROPE_TOTAL }
    ));

    var size = 200;
    var cx = size / 2;
    var cy = size / 2;
    var r = 88;
    var visitedAngle = visitedRatio * 360;
    var paths = '<circle class="main-europe-chart-slice main-europe-chart-slice--unvisited" cx="' +
      cx + '" cy="' + cy + '" r="' + r + '"></circle>';

    if (visitedCount > 0 && visitedAngle < 360) {
      paths += '<path class="main-europe-chart-slice main-europe-chart-slice--visited" d="' +
        pieSlice(cx, cy, r, 0, visitedAngle) + '"></path>';
    } else if (visitedCount >= EUROPE_TOTAL) {
      paths += '<circle class="main-europe-chart-slice main-europe-chart-slice--visited" cx="' +
        cx + '" cy="' + cy + '" r="' + r + '"></circle>';
    }

    paths += '<circle class="main-europe-chart-outline" cx="' + cx + '" cy="' + cy +
      '" r="' + r + '"></circle>';

    chartEl.innerHTML =
      '<div class="main-europe-chart-wrap">' +
      '<div class="main-europe-chart-pie-outer" role="img" aria-label="' + chartAria + '">' +
      '<svg class="main-europe-chart-svg" viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
      paths +
      '</svg>' +
      '<span class="main-europe-chart-center-label">' + centerLabel + '</span>' +
      '</div>' +
      '<div class="main-europe-chart-legend-key">' +
      '<span><span class="main-europe-chart-swatch main-europe-chart-swatch--visited"></span>' +
      escapeHtml(t('mainPage.europeChartVisited', 'Visited')) + '</span>' +
      '<span><span class="main-europe-chart-swatch main-europe-chart-swatch--unvisited"></span>' +
      escapeHtml(t('mainPage.europeChartNotVisited', 'Not visited yet')) + '</span>' +
      '</div>' +
      '</div>';
  }

  function renderLogCard(place) {
    return (
      '<article class="travel-log-card" role="article">' +
      '<div class="log-header">' +
      '<div class="log-dest">' +
      '<svg class="icon icon-pin" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>' +
      '<h3 class="log-title">' + escapeHtml(place.name) + '</h3>' +
      '</div>' +
      '<span class="log-date">' + escapeHtml(place.date) + '</span>' +
      '</div>' +
      '<p class="log-notes">' + escapeHtml(place.description || 'No notes.') + '</p>' +
      '</article>'
    );
  }

  function renderRecentPlaces(places) {
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
        t('visitedPlaces.addFirstPlace', 'Add your first place') + '</a>.</p>';
      return;
    }

    container.innerHTML = recent.map(renderLogCard).join('');
  }

  function render(places) {
    renderRecentPlaces(places);
    renderEuropeChart(places);
    if (window.i18n && window.i18n.applyToPage) window.i18n.applyToPage();
  }

  function showMessageInBoth(msgHtml) {
    var container = document.getElementById('mainTravelLogs');
    var chartEl = document.getElementById('mainEuropeChart');
    var summaryEl = document.getElementById('mainEuropeChartSummary');
    if (container) container.innerHTML = '<p class="travel-logs-empty muted">' + msgHtml + '</p>';
    if (chartEl) chartEl.innerHTML = '';
    if (summaryEl) summaryEl.hidden = true;
    if (window.i18n && window.i18n.applyToPage) window.i18n.applyToPage();
  }

  function loadTravelLog() {
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      showMessageInBoth('Please <a href="loginRegister/loginPage.html">log in</a> to see your travel log.');
      return;
    }

    fetch('/api/users/' + encodeURIComponent(userId) + '/visited-places')
      .then(function (res) {
        if (!res.ok) {
          if (res.status === 404) return [];
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        var list = Array.isArray(data) ? data : [];
        render(list.map(normalizePlace));
      })
      .catch(function (err) {
        console.error('Failed to load travel log:', err);
        showMessageInBoth('Failed to load travel log. Please try again later.');
      });
  }

  document.addEventListener('DOMContentLoaded', loadTravelLog);
})();
