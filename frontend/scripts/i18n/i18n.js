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

    try {
      document.dispatchEvent(
        new CustomEvent('app:languagechange', { detail: { language: locale } })
      );
    } catch (e) { /* ignore */ }

    return locale;
  }

  // Nested key + fallback support
  function resolveKey(obj, key) {
    var parts = key.split('.');
    var result = obj;

    for (var i = 0; i < parts.length; i++) {
      result = result?.[parts[i]];
      if (result === undefined) return undefined;
    }

    return result;
  }

  function t(key) {
    var translations = getTranslations();
    var lang = getLanguage();

    // try current language
    var value = resolveKey(translations[lang], key);

    // fallback to EN if missing
    if (value === undefined) {
      value = resolveKey(translations[DEFAULT_LANG], key);
    }

    return typeof value === 'string' ? value : key;
  }

  function applyToPage(root) {
    root = root || document;

    var nodes = root.querySelectorAll('[data-i18n]');
    nodes.forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (!key) return;

      var val = t(key);

      if (val.includes('<')) {
        el.innerHTML = val;
      } else {
        el.textContent = val;
      }
    });

    var placeholders = root.querySelectorAll('[data-i18n-placeholder]');
    placeholders.forEach(function (el) {
      var key = el.getAttribute('data-i18n-placeholder');
      if (key) el.placeholder = t(key);
    });

    var titles = root.querySelectorAll('[data-i18n-title]');
    titles.forEach(function (el) {
      var key = el.getAttribute('data-i18n-title');
      if (key) el.setAttribute('title', t(key));
    });
  }

  // expose globally so other scripts can re-run it
  window.i18n = {
    getLanguage: getLanguage,
    setLanguage: setLanguage,
    t: t,
    applyToPage: applyToPage
  };

  function initI18n() {
    setLanguage(getLanguage());
    applyToPage();

    // Pages without sidebarHeader never call appShell.init()
    if (!window.appShell) {
      document.documentElement.classList.add('app-ready');
    }

    setTimeout(function () {
      applyToPage();
    }, 50);
  }

  // DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n);
  } else {
    initI18n();
  }

  // Also after full page load
  window.addEventListener('load', () => applyToPage());

})();