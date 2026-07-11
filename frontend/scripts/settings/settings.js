document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('settingsForm');
    var themeSelect = document.getElementById('themeSelect');
    var languageSelect = document.getElementById('languageSelect');
    var savedTheme = localStorage.getItem('theme') || 'dark';
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
        }
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        persistSettings();
    });

    function apiBase() {
        return typeof window.API_BASE_URL === 'string' ? window.API_BASE_URL : '';
    }

    function t(key) {
        return window.i18n && window.i18n.t ? window.i18n.t(key) : key;
    }

    function initLlmProviderPicker() {
        var wrap = document.getElementById('llmProviderChoices');
        var statusEl = document.getElementById('llmProviderStatus');
        if (!wrap) return;

        var uid = localStorage.getItem('user_id');
        if (!uid) {
            wrap.style.display = 'none';
            if (statusEl) {
                statusEl.hidden = false;
                statusEl.textContent = t('settings.aiLoginRequired');
            }
            return;
        }

        function setSelected(provider) {
            wrap.querySelectorAll('.settings-llm-btn').forEach(function (b) {
                var v = b.getAttribute('data-llm');
                b.classList.toggle('is-selected', v === provider);
            });
        }

        function showLlmStatus(key, isError) {
            if (!statusEl) return;
            statusEl.hidden = false;
            statusEl.textContent = t(key);
            statusEl.classList.toggle('settings-llm-status--error', !!isError);
            clearTimeout(showLlmStatus._t);
            showLlmStatus._t = setTimeout(function () {
                statusEl.hidden = true;
            }, 3200);
        }

        fetch(apiBase() + '/api/users/' + encodeURIComponent(uid))
            .then(function (res) {
                if (!res.ok) throw new Error('load');
                return res.json();
            })
            .then(function (user) {
                var p = user.preferred_llm_provider === 'ollama' ? 'ollama' : 'deepseek';
                setSelected(p);
            })
            .catch(function () {
                setSelected('deepseek');
            });

        wrap.addEventListener('click', function (e) {
            var btn = e.target.closest('.settings-llm-btn');
            if (!btn) return;
            var provider = btn.getAttribute('data-llm');
            if (!provider || (provider !== 'deepseek' && provider !== 'ollama')) return;

            setSelected(provider);

            fetch(apiBase() + '/api/users/' + encodeURIComponent(uid), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preferred_llm_provider: provider })
            })
                .then(function (res) {
                    if (!res.ok) throw new Error('save');
                    showLlmStatus('settings.aiSaved', false);
                    if (window.i18n) window.i18n.applyToPage(wrap);
                })
                .catch(function () {
                    showLlmStatus('settings.aiSaveFailed', true);
                });
        });
    }

    initLlmProviderPicker();
});
