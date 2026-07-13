document.addEventListener('DOMContentLoaded', function () {
    var userId = localStorage.getItem('user_id');
    var form = document.getElementById('editProfileForm');
    var usernameInput = document.getElementById('profileUsername');
    var emailInput = document.getElementById('profileEmail');
    var homeCityInput = document.getElementById('profileHomeCity');
    var newPasswordInput = document.getElementById('profileNewPassword');
    var confirmPasswordInput = document.getElementById('profileConfirmPassword');
    var errorEl = document.getElementById('editProfileError');
    var saveBtn = document.getElementById('saveProfileBtn');

    function hideMessages() {
        errorEl.hidden = true;
    }

    function showError(text) {
        hideMessages();
        errorEl.textContent = text;
        errorEl.hidden = false;
    }

    function formatApiDetail(detail) {
        if (detail == null) return '';
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) {
            return detail
                .map(function (item) {
                    if (item && item.msg) return item.msg;
                    return String(item);
                })
                .join(' ');
        }
        return String(detail);
    }

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === 'function') {
            return window.i18n.t(key);
        }
        return fallback;
    }

    if (!userId || !form) {
        return;
    }

    fetch('/api/users/' + encodeURIComponent(userId))
        .then(function (res) {
            if (!res.ok) throw new Error('load');
            return res.json();
        })
        .then(function (data) {
            if (usernameInput) usernameInput.value = data.username || '';
            if (emailInput) emailInput.value = data.email || '';
            if (homeCityInput) homeCityInput.value = data.home_city || '';
        })
        .catch(function () {
            showError(t('editProfile.errorLoad', 'Could not load your profile.'));
        });

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        hideMessages();

        var username = (usernameInput && usernameInput.value) ? usernameInput.value.trim() : '';
        var email = (emailInput && emailInput.value) ? emailInput.value.trim() : '';
        var newPw = (newPasswordInput && newPasswordInput.value) ? newPasswordInput.value : '';
        var confirmPw = (confirmPasswordInput && confirmPasswordInput.value) ? confirmPasswordInput.value : '';

        if (!username || !email) {
            showError(t('editProfile.validationRequired', 'Username and email are required.'));
            return;
        }

        if (newPw || confirmPw) {
            if (!newPw || !confirmPw) {
                showError(t('editProfile.passwordBoth', 'Enter and confirm your new password.'));
                return;
            }
            if (newPw.length < 6) {
                showError(t('editProfile.passwordTooShort', 'Password must be at least 6 characters.'));
                return;
            }
            if (newPw !== confirmPw) {
                showError(t('editProfile.passwordMismatch', 'New passwords do not match.'));
                return;
            }
        }

        var homeCity = (homeCityInput && homeCityInput.value) ? homeCityInput.value.trim() : '';

        var payload = { username: username, email: email, home_city: homeCity };
        if (newPw) {
            payload.password = newPw;
        }

        if (saveBtn) saveBtn.disabled = true;

        fetch('/api/users/' + encodeURIComponent(userId), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(function (res) {
                return res.json().then(
                    function (body) {
                        return { ok: res.ok, status: res.status, body: body };
                    },
                    function () {
                        return { ok: res.ok, status: res.status, body: {} };
                    }
                );
            })
            .then(function (result) {
                if (result.ok) {
                    localStorage.setItem('username', result.body.username || username);
                    if (newPasswordInput) newPasswordInput.value = '';
                    if (confirmPasswordInput) confirmPasswordInput.value = '';
                    if (window.i18n && typeof window.i18n.applyToPage === 'function') {
                        window.i18n.applyToPage();
                    }
                    return;
                }
                var msg = formatApiDetail(result.body && result.body.detail);
                showError(msg || t('editProfile.errorSave', 'Could not save changes.'));
            })
            .catch(function () {
                showError(t('editProfile.errorSave', 'Could not save changes.'));
            })
            .finally(function () {
                if (saveBtn) saveBtn.disabled = false;
            });
    });
});
