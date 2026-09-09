(function (global) {
  'use strict';

  var DEFAULT_MESSAGE =
    'Password must be at least 8 characters and include an uppercase letter, ' +
    'a lowercase letter, a number, and a special character.';

  function isStrong(password) {
    var value = String(password || '');
    if (value.length < 8) return false;
    if (!/[A-Z]/.test(value)) return false;
    if (!/[a-z]/.test(value)) return false;
    if (!/[0-9]/.test(value)) return false;
    if (!/[^A-Za-z0-9]/.test(value)) return false;
    return true;
  }

  function message(i18nKey) {
    if (window.i18n && typeof window.i18n.t === 'function' && i18nKey) {
      var translated = window.i18n.t(i18nKey);
      if (translated && translated !== i18nKey) return translated;
    }
    return DEFAULT_MESSAGE;
  }

  global.PasswordPolicy = {
    isStrong: isStrong,
    message: message,
    defaultMessage: DEFAULT_MESSAGE
  };
})(window);
