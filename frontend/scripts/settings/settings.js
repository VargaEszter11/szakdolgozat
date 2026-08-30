document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('settingsForm');
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var savedMessageEl = document.getElementById('settingsSavedMessage');

    if (!form || !themeSelect || !languageSelect || !window.Dropdown) {
        return;
    }

    var savedTheme = localStorage.getItem('theme') || 'dark';
    var savedLanguage = localStorage.getItem('language') || 'en';
    var autoListenerBound = false;

    function applyTheme(theme) {
        if (window.applyAppTheme) {
            window.applyAppTheme(theme);
        }
        if (theme === 'auto' && window.bindThemeAutoListener && !autoListenerBound) {
            window.bindThemeAutoListener();
            autoListenerBound = true;
        }
    }

    function applyLanguage(language) {
        if (window.i18n) {
            window.i18n.setLanguage(language);
            window.i18n.applyToPage();
        }
    }

    var themeWrap = themeSelect.closest('.app-dropdown');
    var languageWrap = languageSelect.closest('.app-dropdown');

    var themeWidget = window.Dropdown.mountSelect(themeWrap, { onChange: applyTheme });
    var languageWidget = window.Dropdown.mountSelect(languageWrap, {
        onChange: function (lang) {
            applyLanguage(lang);
            if (themeWidget) themeWidget.refreshLabel();
            if (languageWidget) languageWidget.refreshLabel();
        }
    });

    if (themeWidget) themeWidget.setValue(savedTheme);
    if (languageWidget) languageWidget.setValue(savedLanguage);
    applyTheme(savedTheme);
    applyLanguage(savedLanguage);
    if (themeWidget) themeWidget.refreshLabel();
    if (languageWidget) languageWidget.refreshLabel();

    function persistSettings() {
        savedTheme = themeSelect.value;
        savedLanguage = languageSelect.value;
        localStorage.setItem('theme', savedTheme);
        localStorage.setItem('language', savedLanguage);
    }

    var savedMessageTimer = null;

    function showSavedMessage() {
        if (!savedMessageEl) return;
        savedMessageEl.hidden = false;
        clearTimeout(savedMessageTimer);
        savedMessageTimer = setTimeout(function () {
            savedMessageEl.hidden = true;
        }, 4000);
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        persistSettings();
        showSavedMessage();
    });

    var cancelBtn = document.getElementById('cancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
            if (themeWidget) themeWidget.setValue(savedTheme);
            if (languageWidget) languageWidget.setValue(savedLanguage);
            applyTheme(savedTheme);
            applyLanguage(savedLanguage);
            if (themeWidget) themeWidget.refreshLabel();
            if (languageWidget) languageWidget.refreshLabel();
        });
    }
});
