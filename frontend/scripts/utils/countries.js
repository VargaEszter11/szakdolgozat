(function (global) {
  var ROWS = [
    ['AL', 'Albania', ['albania', 'albánia', 'albanien']],
    ['AD', 'Andorra'],
    ['AM', 'Armenia', ['armenia', 'örményország', 'ormenyorszag']],
    ['AT', 'Austria', ['osterreich', 'österreich', 'ausztria']],
    ['AZ', 'Azerbaijan', ['azerbaijan']],
    ['BY', 'Belarus', ['weissrussland', 'weißrussland', 'belarus', 'feherorosz', 'fehérorosz']],
    ['BE', 'Belgium', ['belgien', 'belgium', 'belgique', 'belgie']],
    ['BA', 'Bosnia and Herzegovina', ['bosnia', 'bosnien', 'bosznia', 'bosznia-hercegovina']],
    ['BG', 'Bulgaria', ['bulgarien', 'bulgaria', 'bulgária']],
    ['HR', 'Croatia', ['kroatien', 'horvatorszag', 'horvátország', 'croatia']],
    ['CY', 'Cyprus', ['zypern', 'ciprus']],
    ['CZ', 'Czechia', ['czech republic', 'tschechien', 'cseh', 'csehorszag', 'csehország']],
    ['DK', 'Denmark', ['danemark', 'dänemark', 'dania', 'dánia']],
    ['EE', 'Estonia', ['estland', 'esztorszag', 'észtország']],
    ['FI', 'Finland', ['finnland', 'finnorszag', 'finnország']],
    ['FR', 'France', ['frankreich', 'francia', 'franciaorszag', 'franciaország']],
    ['GE', 'Georgia', ['georgia', 'grúzia', 'gruzie', 'gruzia']],
    ['DE', 'Germany', ['deutschland', 'nemetorszag', 'németország']],
    ['GR', 'Greece', ['griechenland', 'gorogorszag', 'görögország']],
    ['HU', 'Hungary', ['magyarorszag', 'magyarország', 'ungarn']],
    ['IS', 'Iceland', ['island', 'izland', 'ízland']],
    ['IE', 'Ireland', ['irland', 'irorszag', 'írország']],
    ['IT', 'Italy', ['italien', 'italia', 'olaszorszag', 'olaszország']],
    ['KA', 'Kazakhstan', ['kazahsztan', 'kazahstan', 'kazahsztán']],
    ['XK', 'Kosovo', ['koszovo', 'koszovó']],
    ['LV', 'Latvia', ['lettland', 'lettorszag', 'lettország']],
    ['LI', 'Liechtenstein'],
    ['LT', 'Lithuania', ['litauen', 'litvania', 'litvánia']],
    ['LU', 'Luxembourg', ['luxemburg']],
    ['MT', 'Malta', ['málta']],
    ['MD', 'Moldova', ['moldawien', 'moldova']],
    ['MC', 'Monaco'],
    ['ME', 'Montenegro', ['crna gora', 'montenegró']],
    ['NL', 'Netherlands', ['holland', 'hollandia', 'niederlande', 'the netherlands']],
    ['MK', 'North Macedonia', ['macedonia', 'mazedonien', 'eszak-macedonia', 'észak-macedónia', 'macedónia']],
    ['NO', 'Norway', ['norwegen', 'norvegia', 'norvégia']],
    ['PL', 'Poland', ['polen', 'lengyelorszag', 'lengyelország']],
    ['PT', 'Portugal', ['portugalia', 'portugália']],
    ['RO', 'Romania', ['rumänien', 'rumanien', 'romania', 'románia']],
    ['RU', 'Russia', ['russia', 'oroszország', 'oroszorszag']],
    ['SM', 'San Marino'],
    ['RS', 'Serbia', ['serbien', 'szerbia']],
    ['SK', 'Slovakia', ['slowakei', 'szlovakia', 'szlovákia']],
    ['SI', 'Slovenia', ['slowenien', 'szlovenia', 'szlovénia']],
    ['ES', 'Spain', ['spanien', 'espana', 'españa', 'spanyolorszag', 'spanyolország']],
    ['SE', 'Sweden', ['schweden', 'svedorszag', 'svédország']],
    ['CH', 'Switzerland', ['schweiz', 'suisse', 'svizzera', 'svajc', 'svájc']],
    ['TR', 'Turkey', ['türkei', 'turkey', 'törökország', 'torokorszag']],
    ['UA', 'Ukraine', ['ukraine', 'ukrajna']],
    ['GB', 'United Kingdom', ['uk', 'great britain', 'england', 'scotland', 'wales', 'grossbritannien', 'nagy-britannia', 'egyesult kiralysag', 'egyesült királyság', 'anglia']],
    ['VA', 'Vatican City', ['vatican', 'holy see', 'vatikan', 'vatikanvaros', 'vatikánváros']],
  ];

  // Europe chart / region filters — derived from ROWS (do not maintain separately).
  var EUROPE_ISO_LIST = ROWS.map(function (row) { return row[0]; });
  var FULL_LOCALE = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };
  var INDEX_LANGS = ['en', 'hu', 'de'];

  var CODE_TO_NAME = {};
  var NAME_TO_CODE = {};
  var SEARCH_INDEX = [];
  var displayNamesCache = {};

  function fold(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[-_]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function appLang() {
    if (window.i18n && typeof window.i18n.getLanguage === 'function') {
      return window.i18n.getLanguage() || 'en';
    }
    try {
      return localStorage.getItem('language') || 'en';
    } catch (e) {
      return 'en';
    }
  }

  function appLocale() {
    var lang = appLang();
    return FULL_LOCALE[lang] || lang || 'en';
  }

  function regionDisplayNames(locale) {
    if (displayNamesCache[locale]) return displayNamesCache[locale];
    try {
      if (typeof Intl !== 'undefined' && Intl.DisplayNames) {
        displayNamesCache[locale] = new Intl.DisplayNames([locale], { type: 'region' });
        return displayNamesCache[locale];
      }
    } catch (e) { /* fall through */ }
    displayNamesCache[locale] = null;
    return null;
  }

  function localizedName(code) {
    if (!code || !CODE_TO_NAME[code]) return '';
    var dn = regionDisplayNames(appLocale());
    if (dn) {
      try {
        var name = dn.of(code);
        if (name && name !== code) return name;
      } catch (e) { /* fall through */ }
    }
    return CODE_TO_NAME[code];
  }

  function intlNamesForCode(code) {
    var names = [];
    INDEX_LANGS.forEach(function (lang) {
      var dn = regionDisplayNames(FULL_LOCALE[lang] || lang);
      if (!dn) return;
      try {
        var name = dn.of(code);
        if (name && name !== code) names.push(name);
      } catch (e) { /* ignore */ }
    });
    return names;
  }

  ROWS.forEach(function (row) {
    var code = row[0];
    var name = row[1];
    var aliases = row[2] || [];
    CODE_TO_NAME[code] = name;
    NAME_TO_CODE[fold(name)] = code;
    var terms = [fold(name), fold(code)].concat(aliases.map(fold));
    aliases.forEach(function (alias) {
      NAME_TO_CODE[fold(alias)] = code;
    });
    intlNamesForCode(code).forEach(function (localized) {
      var folded = fold(localized);
      if (!folded) return;
      terms.push(folded);
      if (!NAME_TO_CODE[folded]) NAME_TO_CODE[folded] = code;
    });
    SEARCH_INDEX.push({ code: code, name: name, terms: terms });
  });

  var EUROPE = {};
  EUROPE_ISO_LIST.forEach(function (iso) {
    EUROPE[iso] = 1;
  });

  function normalizeCode(value) {
    var raw = String(value || '').trim();
    if (!raw) return '';
    var upper = raw.toUpperCase();
    if (upper === 'UK') upper = 'GB';
    if (upper.length === 2 && /^[A-Z]{2}$/.test(upper)) {
      return CODE_TO_NAME[upper] ? upper : '';
    }
    var key = fold(raw);
    if (NAME_TO_CODE[key]) return NAME_TO_CODE[key];
    for (var i = 0; i < SEARCH_INDEX.length; i++) {
      var entry = SEARCH_INDEX[i];
      for (var j = 0; j < entry.terms.length; j++) {
        var term = entry.terms[j];
        if (term.length >= 4 && (key.indexOf(term) >= 0 || term.indexOf(key) >= 0)) {
          return entry.code;
        }
      }
    }
    return '';
  }

  function displayName(value) {
    var raw = String(value || '').trim();
    if (!raw) return '';
    var code = normalizeCode(raw);
    if (code && CODE_TO_NAME[code]) return localizedName(code);
    return raw;
  }

  function formatPlace(placeName, country) {
    var city = String(placeName || '').trim();
    var label = displayName(country);
    if (!city) return label || 'Unnamed place';
    return label ? city + ', ' + label : city;
  }

  function isEurope(value) {
    var code = normalizeCode(value);
    return !!(code && EUROPE[code]);
  }

  function europeIso(value) {
    var code = normalizeCode(value);
    return code && EUROPE[code] ? code : null;
  }

  function search(query, limit) {
    limit = limit == null ? 8 : limit;
    var locale = appLocale();
    var q = fold(query);
    if (!q) {
      return SEARCH_INDEX
        .map(function (e) {
          return { code: e.code, name: localizedName(e.code) };
        })
        .sort(function (a, b) {
          return a.name.localeCompare(b.name, locale);
        });
    }
    var scored = [];
    for (var i = 0; i < SEARCH_INDEX.length; i++) {
      var entry = SEARCH_INDEX[i];
      var label = localizedName(entry.code);
      var best = 0;
      for (var j = 0; j < entry.terms.length; j++) {
        var term = entry.terms[j];
        if (term === q) best = Math.max(best, 100);
        else if (term.indexOf(q) === 0) best = Math.max(best, 80 - term.length);
        else if (term.indexOf(q) >= 0) best = Math.max(best, 40);
      }
      if (best > 0) scored.push({ score: best, code: entry.code, name: label });
    }
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.name.localeCompare(b.name, locale);
    });
    var matches = scored.map(function (e) {
      return { code: e.code, name: e.name };
    });
    return limit > 0 ? matches.slice(0, limit) : matches;
  }

  function closeList(wrap) {
    var list = wrap && wrap.querySelector('.country-autocomplete-list');
    if (list) {
      list.hidden = true;
      list.innerHTML = '';
    }
  }

  function mountAutocomplete(input, options) {
    options = options || {};
    if (!input || input.dataset.countryAutocomplete === '1') return input;
    if (!input.parentNode) return input;

    var wrap = document.createElement('div');
    wrap.className = 'country-autocomplete';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.dataset.countryAutocomplete = '1';
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');

    var list = document.createElement('ul');
    list.className = 'country-autocomplete-list';
    list.hidden = true;
    list.setAttribute('role', 'listbox');
    wrap.appendChild(list);

    var activeIndex = -1;

    function setValueFromCode(code) {
      if (!code) {
        input.dataset.countryCode = '';
        return;
      }
      input.dataset.countryCode = code;
      input.value = localizedName(code) || CODE_TO_NAME[code] || code;
      if (typeof options.onChange === 'function') options.onChange(code, input.value);
    }

    function syncLanguage() {
      var code = normalizeCode(input.dataset.countryCode) || normalizeCode(input.value);
      if (code) setValueFromCode(code);
      if (!list.hidden) refresh();
    }

    input._countrySyncLanguage = syncLanguage;

    var initial = normalizeCode(input.value) || normalizeCode(input.dataset.countryCode || '');
    if (initial) setValueFromCode(initial);

    function renderSuggestions(items) {
      list.innerHTML = '';
      activeIndex = -1;
      if (!items.length) {
        closeList(wrap);
        input.setAttribute('aria-expanded', 'false');
        return;
      }
      items.forEach(function (item, idx) {
        var li = document.createElement('li');
        li.className = 'country-autocomplete-option';
        li.setAttribute('role', 'option');
        li.dataset.code = item.code;
        li.id = (input.id || 'country') + '-opt-' + idx;
        li.innerHTML =
          '<span class="country-autocomplete-name"></span>' +
          '<span class="country-autocomplete-code"></span>';
        li.querySelector('.country-autocomplete-name').textContent = item.name;
        li.querySelector('.country-autocomplete-code').textContent = item.code;
        li.addEventListener('mousedown', function (e) {
          e.preventDefault();
          setValueFromCode(item.code);
          closeList(wrap);
          input.setAttribute('aria-expanded', 'false');
        });
        list.appendChild(li);
      });
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    function refresh() {
      renderSuggestions(search(input.value, options.limit || 8));
    }

    function commitTyped() {
      var code = normalizeCode(input.value);
      if (code) setValueFromCode(code);
      else input.dataset.countryCode = '';
      closeList(wrap);
      input.setAttribute('aria-expanded', 'false');
    }

    input.addEventListener('input', function () {
      input.dataset.countryCode = normalizeCode(input.value) || '';
      refresh();
    });
    input.addEventListener('focus', function () {
      refresh();
    });
    input.addEventListener('blur', function () {
      setTimeout(function () {
        commitTyped();
      }, 120);
    });
    input.addEventListener('keydown', function (e) {
      var optionsEls = list.querySelectorAll('.country-autocomplete-option');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (list.hidden) refresh();
        activeIndex = Math.min(activeIndex + 1, optionsEls.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
      } else if (e.key === 'Enter') {
        if (!list.hidden && activeIndex >= 0 && optionsEls[activeIndex]) {
          e.preventDefault();
          setValueFromCode(optionsEls[activeIndex].dataset.code);
          closeList(wrap);
        } else {
          commitTyped();
        }
        return;
      } else if (e.key === 'Escape') {
        closeList(wrap);
        return;
      } else {
        return;
      }
      for (var i = 0; i < optionsEls.length; i++) {
        optionsEls[i].classList.toggle('is-active', i === activeIndex);
      }
      if (optionsEls[activeIndex]) {
        input.setAttribute('aria-activedescendant', optionsEls[activeIndex].id);
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) closeList(wrap);
    });

    return input;
  }

  function getCode(input) {
    if (!input) return '';
    return (
      normalizeCode(input.dataset.countryCode) ||
      normalizeCode(input.value) ||
      ''
    );
  }

  function refreshLocalizedInputs() {
    var inputs = document.querySelectorAll('[data-country-autocomplete="1"]');
    for (var i = 0; i < inputs.length; i++) {
      if (typeof inputs[i]._countrySyncLanguage === 'function') {
        inputs[i]._countrySyncLanguage();
      }
    }
  }

  document.addEventListener('app:languagechange', refreshLocalizedInputs);

  global.Countries = {
    normalizeCode: normalizeCode,
    displayName: displayName,
    localizedName: localizedName,
    formatPlace: formatPlace,
    isEurope: isEurope,
    europeIso: europeIso,
    search: search,
    mountAutocomplete: mountAutocomplete,
    getCode: getCode,
    refreshLocalizedInputs: refreshLocalizedInputs,
    EUROPE_ISO_LIST: EUROPE_ISO_LIST,
    CODE_TO_NAME: CODE_TO_NAME
  };
})(window);
