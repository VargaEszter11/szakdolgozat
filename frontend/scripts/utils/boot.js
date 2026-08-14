(function () {
  var t = localStorage.getItem('theme') || 'dark';
  var resolved =
    t === 'auto'
      ? matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : t === 'dark'
        ? 'dark'
        : 'light';
  document.documentElement.setAttribute('data-theme', resolved);

  var lang = localStorage.getItem('language') || 'en';
  var full = lang === 'hu' ? 'hu-HU' : lang === 'de' ? 'de-DE' : 'en-GB';
  document.documentElement.setAttribute('lang', full);
})();

window.markAppReady = function () {
  document.documentElement.classList.add('app-ready');
};

setTimeout(function () {
  if (window.markAppReady) window.markAppReady();
}, 8000);
