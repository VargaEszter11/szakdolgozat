document.addEventListener('DOMContentLoaded', function () {
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var saveBtn = document.getElementById('saveSettings');
    var saveMessage = document.getElementById('saveMessage');

    var savedTheme = localStorage.getItem('theme') || 'light';
    var savedLanguage = localStorage.getItem('language') || 'en';

    themeSelect.value = savedTheme;
    languageSelect.value = savedLanguage;

    themeSelect.addEventListener('change', function () {
        applyTheme(themeSelect.value);
    });

    saveBtn.addEventListener('click', function () {
        localStorage.setItem('theme', themeSelect.value);
        localStorage.setItem('language', languageSelect.value);

        saveMessage.style.display = 'block';
        setTimeout(function () {
            saveMessage.style.display = 'none';
        }, 3000);
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
