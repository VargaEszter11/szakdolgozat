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
    ['KZ', 'Kazakhstan', ['kazahsztan', 'kazahstan', 'kazahsztán']],
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
    var terms = [fold(name), fold(code)].concat(aliases.map(fold));
    NAME_TO_CODE[fold(name)] = code;
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
    return '';
  }

  /** Autocomplete only: map a typed country name/alias to ISO-2. Not used when reading stored places. */
  function codeFromTypedName(value) {
    var code = normalizeCode(value);
    if (code) return code;
    return NAME_TO_CODE[fold(value)] || '';
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
    var unnamed = 'Unnamed place';
    if (global.i18n && typeof global.i18n.t === 'function') {
      var v = global.i18n.t('visitedPlaces.unnamedPlace');
      if (v && v !== 'visitedPlaces.unnamedPlace') unnamed = v;
    }
    if (!city) return label || unnamed;
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

  function mountAutocomplete(input, options) {
    options = options || {};
    if (!input || input.dataset.countryAutocomplete === '1') return input;
    if (!global.Dropdown || typeof global.Dropdown.mountAutocomplete !== 'function') {
      return input;
    }

    input.dataset.countryAutocomplete = '1';

    var initial =
      normalizeCode(input.dataset.countryCode || '') ||
      normalizeCode(input.value) ||
      codeFromTypedName(input.value) ||
      '';

    global.Dropdown.mountAutocomplete(input, {
      clearOnClose: true,
      initialValue: initial,
      getDisplay: function (code) {
        return localizedName(code) || CODE_TO_NAME[code] || code;
      },
      getItems: function (query) {
        return search(query, options.limit || 8).map(function (item) {
          return { value: item.code, label: item.name, code: item.code };
        });
      },
      resolveValue: function (text) {
        var code = codeFromTypedName(text);
        if (!code) return null;
        return {
          value: code,
          label: localizedName(code) || CODE_TO_NAME[code] || code
        };
      },
      onChange: function (code, label) {
        input.dataset.countryCode = code || '';
        if (typeof options.onChange === 'function') options.onChange(code, label);
      }
    });

    if (initial) input.dataset.countryCode = initial;

    input.addEventListener('input', function () {
      input.dataset.countryCode =
        codeFromTypedName(input.value) ||
        normalizeCode(input.dataset.dropdownValue) ||
        '';
    });

    function syncLanguage() {
      var code =
        normalizeCode(input.dataset.countryCode) ||
        normalizeCode(input.dataset.dropdownValue) ||
        codeFromTypedName(input.value);
      if (!code) return;
      input.dataset.countryCode = code;
      var label = localizedName(code) || CODE_TO_NAME[code] || code;
      if (input._dropdownApi) input._dropdownApi.setValue(code, label);
      else input.value = label;
      if (input._dropdownApi && typeof input._dropdownApi.refresh === 'function') {
        var wrap = input._dropdownApi.wrap;
        var list = wrap && wrap.querySelector('.' + global.Dropdown.CLS.list);
        if (list && !list.hidden) input._dropdownApi.refresh();
      }
    }

    input._countrySyncLanguage = syncLanguage;
    return input;
  }

  function getCode(input) {
    if (!input) return '';
    return (
      normalizeCode(input.dataset.countryCode) ||
      normalizeCode(input.dataset.dropdownValue) ||
      codeFromTypedName(input.value) ||
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
