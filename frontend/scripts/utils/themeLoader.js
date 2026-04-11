(function () {
    var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    var autoListenerBound = false;

    function getEffectiveThemePreference() {
        var select = typeof document !== 'undefined' ? document.getElementById('themeSelect') : null;
        if (select && select.value) return select.value;
        return localStorage.getItem('theme') || 'light';
    }

    function resolveTheme(theme) {
        if (theme === 'dark') return 'dark';
        if (theme === 'auto') return mediaQuery.matches ? 'dark' : 'light';
        return 'light';
    }

    function applyResolved(resolved) {
        document.documentElement.setAttribute('data-theme', resolved);
    }

    /**
     * @param {string} theme - 'light' | 'dark' | 'auto'
     */
    function applyAppTheme(theme) {
        applyResolved(resolveTheme(theme));
    }

    function onAutoSchemeChange() {
        if (getEffectiveThemePreference() === 'auto') {
            applyResolved(resolveTheme('auto'));
        }
    }

    function bindThemeAutoListener() {
        if (autoListenerBound) return;
        autoListenerBound = true;
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', onAutoSchemeChange);
        } else if (mediaQuery.addListener) {
            mediaQuery.addListener(onAutoSchemeChange);
        }
    }

    var initial = localStorage.getItem('theme') || 'light';
    applyAppTheme(initial);
    if (initial === 'auto') {
        bindThemeAutoListener();
    }

    window.applyAppTheme = applyAppTheme;
    window.bindThemeAutoListener = bindThemeAutoListener;
})();
