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

  var boot = document.currentScript;
  if (boot && boot.src && typeof window.displayNameInitials !== 'function') {
    var src = boot.src.replace(/boot\.js(\?.*)?$/, 'displayName.js');
    document.write('<script src="' + src + '"><\/script>');
  }
})();

window.markAppReady = function () {
  document.documentElement.classList.add('app-ready');
};

setTimeout(function () {
  if (window.markAppReady) window.markAppReady();
}, 8000);
