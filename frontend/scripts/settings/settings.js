document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('settingsForm');
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var saveMessage = document.getElementById('saveMessage');

    var savedTheme = localStorage.getItem('theme') || 'light';
    var savedLanguage = localStorage.getItem('language') || 'en';

    themeSelect.value = savedTheme;
    languageSelect.value = savedLanguage;

    if (window.applyAppTheme) {
        window.applyAppTheme(savedTheme);
    }
    if (savedTheme === 'auto' && window.bindThemeAutoListener) {
        window.bindThemeAutoListener();
    }

    if (window.i18n) {
        window.i18n.setLanguage(savedLanguage);
        window.i18n.applyToPage();
    }

    themeSelect.addEventListener('change', function () {
        if (window.applyAppTheme) {
            window.applyAppTheme(themeSelect.value);
        }
        if (themeSelect.value === 'auto' && window.bindThemeAutoListener) {
            window.bindThemeAutoListener();
        }
    });

    function persistSettings() {
        localStorage.setItem('theme', themeSelect.value);
        var newLang = languageSelect.value;
        localStorage.setItem('language', newLang);

        if (window.applyAppTheme) {
            window.applyAppTheme(themeSelect.value);
        }
        if (themeSelect.value === 'auto' && window.bindThemeAutoListener) {
            window.bindThemeAutoListener();
        }

        if (window.i18n) {
            window.i18n.setLanguage(newLang);
            window.i18n.applyToPage();
            saveMessage.textContent = window.i18n.t('settings.savedMessage');
        }
        saveMessage.hidden = false;
        setTimeout(function () {
            saveMessage.hidden = true;
        }, 3000);
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        persistSettings();
    });
});
