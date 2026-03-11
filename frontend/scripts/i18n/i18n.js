(function () {
  var STORAGE_KEY = 'language';
  var DEFAULT_LANG = 'en';
  var FULL_LOCALE = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function getTranslations() {
    return window.I18N_TRANSLATIONS || {};
  }

  function getLanguage() {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_LANG;
  }

  function setLanguage(locale) {
    var translations = getTranslations();
    if (!translations[locale]) locale = DEFAULT_LANG;
    localStorage.setItem(STORAGE_KEY, locale);
    var fullLocale = FULL_LOCALE[locale] || locale;
    if (document.documentElement) {
      document.documentElement.setAttribute('lang', fullLocale);
    }
    return locale;
  }

  function t(key) {
    var translations = getTranslations();
    var lang = getLanguage();
    var map = translations[lang] || translations[DEFAULT_LANG] || {};
    var parts = key.split('.');
    for (var i = 0; i < parts.length; i++) {
      map = map[parts[i]];
      if (map === undefined) return key;
    }
    return typeof map === 'string' ? map : key;
  }

  function applyToPage(root) {
    root = root || document;
    var nodes = root.querySelectorAll ? root.querySelectorAll('[data-i18n]') : [];
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-i18n');
      if (key) {
        var val = t(key);
        if (val.indexOf('<') !== -1) {
          nodes[i].innerHTML = val;
        } else {
          nodes[i].textContent = val;
        }
      }
    }
    var placeholders = root.querySelectorAll ? root.querySelectorAll('[data-i18n-placeholder]') : [];
    for (var j = 0; j < placeholders.length; j++) {
      var phKey = placeholders[j].getAttribute('data-i18n-placeholder');
      if (phKey) placeholders[j].placeholder = t(phKey);
    }
    var titles = root.querySelectorAll ? root.querySelectorAll('[data-i18n-title]') : [];
    for (var k = 0; k < titles.length; k++) {
      var titleKey = titles[k].getAttribute('data-i18n-title');
      if (titleKey) titles[k].setAttribute('title', t(titleKey));
    }
  }

  window.i18n = {
    getLanguage: getLanguage,
    setLanguage: setLanguage,
    t: t,
    applyToPage: applyToPage
  };

  document.addEventListener('DOMContentLoaded', function () {
    setLanguage(getLanguage());
    applyToPage();
  });
})();
