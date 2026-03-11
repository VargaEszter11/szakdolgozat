(function () {
  var FORMAT_MAP = {
    en: 'd/m/Y',
    hu: 'Y. m. d.',
    de: 'd.m.Y'
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (typeof flatpickr === 'undefined') return;

    var lang = localStorage.getItem('language') || 'en';
    var altFormat = FORMAT_MAP[lang] || 'd/m/Y';
    var localeObj = (lang !== 'en' && flatpickr.l10ns[lang]) ? flatpickr.l10ns[lang] : null;

    var dateInputs = document.querySelectorAll('input[type="date"]');
    for (var i = 0; i < dateInputs.length; i++) {
      dateInputs[i].type = 'text';
      var opts = {
        dateFormat: 'Y-m-d',
        altInput: true,
        altFormat: altFormat,
        allowInput: true
      };
      if (localeObj) opts.locale = localeObj;
      flatpickr(dateInputs[i], opts);
    }
  });
})();
