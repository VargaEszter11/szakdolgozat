document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('settingsForm');
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var saveMessage = document.getElementById('saveMessage');

    var savedTheme = localStorage.getItem('theme') || 'light';
    var savedLanguage = localStorage.getItem('language') || 'en';

    themeSelect.value = savedTheme;
    languageSelect.value = savedLanguage;
    applyTheme(savedTheme);

    if (window.i18n) {
        window.i18n.setLanguage(savedLanguage);
        window.i18n.applyToPage();
    }

    themeSelect.addEventListener('change', function () {
        applyTheme(themeSelect.value);
    });

    function persistSettings() {
        localStorage.setItem('theme', themeSelect.value);
        var newLang = languageSelect.value;
        localStorage.setItem('language', newLang);

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

function applyTheme(theme) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else if (theme === 'auto') {
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
    }
}
