document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('settingsForm');
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var savedMessageEl = document.getElementById('settingsSavedMessage');

    if (!form || !themeSelect || !languageSelect) {
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

    themeSelect.value = savedTheme;
    applyTheme(savedTheme);
    languageSelect.value = savedLanguage;
    applyLanguage(savedLanguage);

    themeSelect.addEventListener('change', function () {
        applyTheme(themeSelect.value);
    });

    languageSelect.addEventListener('change', function () {
        applyLanguage(languageSelect.value);
    });

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
            themeSelect.value = savedTheme;
            languageSelect.value = savedLanguage;
            applyTheme(savedTheme);
            applyLanguage(savedLanguage);
        });
    }
});