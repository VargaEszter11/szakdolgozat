document.addEventListener('DOMContentLoaded', function () {
    var userId = localStorage.getItem('user_id');
    var form = document.getElementById('editProfileForm');
    var usernameInput = document.getElementById('profileUsername');
    var emailInput = document.getElementById('profileEmail');
    var homeCityInput = document.getElementById('profileHomeCity');
    var errorEl = document.getElementById('editProfileError');
    var successEl = document.getElementById('editProfileSuccess');
    var saveBtn = document.getElementById('saveProfileBtn');
    var resetBtn = document.getElementById('sendPasswordResetBtn');
    var successTimer = null;

    function t(key, fallback) {
        if (window.i18n && typeof window.i18n.t === 'function') {
            var v = window.i18n.t(key);
            if (v && v !== key) return v;
        }
        return fallback;
    }

    function hideMessages() {
        if (errorEl) errorEl.hidden = true;
        if (successEl) successEl.hidden = true;
        clearTimeout(successTimer);
    }

    function showError(text) {
        hideMessages();
        if (errorEl) {
            errorEl.textContent = text;
            errorEl.hidden = false;
        }
    }

    function showSuccess(message) {
        hideMessages();
        if (!successEl) return;
        successEl.textContent =
            message || t('editProfile.savedMessage', 'Profile updated successfully.');
        successEl.hidden = false;
        successTimer = setTimeout(function () {
            if (successEl) successEl.hidden = true;
        }, 6000);
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

    function mapApiError(detail) {
        var text = formatApiDetail(detail);
        if (/username already taken/i.test(text)) {
            return t('editProfile.usernameTaken', 'Username already taken.');
        }
        if (/email already registered/i.test(text)) {
            return t('editProfile.emailTaken', 'Email already registered.');
        }
        if (/user not found/i.test(text)) {
            return t('editProfile.userNotFound', 'User not found.');
        }
        if (/could not send email|email sending is not configured/i.test(text)) {
            return t(
                'editProfile.passwordEmailFailed',
                'Could not send the password reset email. Check email settings or try again later.'
            );
        }
        return t('editProfile.errorSave', 'Could not save changes.');
    }

    if (!userId || !form) {
        if (window.markAppReady) window.markAppReady();
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
        })
        .finally(function () {
            if (window.markAppReady) window.markAppReady();
        });

    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            hideMessages();
            var email = (emailInput && emailInput.value) ? emailInput.value.trim() : '';
            if (!email) {
                showError(t('editProfile.passwordResetNeedsEmail', 'Save a valid email on your profile first.'));
                return;
            }

            resetBtn.disabled = true;
            fetch('/api/forgot-password/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            })
                .then(function (res) {
                    return res.json().then(
                        function (body) {
                            return { ok: res.ok, body: body };
                        },
                        function () {
                            return { ok: res.ok, body: {} };
                        }
                    );
                })
                .then(function (result) {
                    if (result.ok && result.body && result.body.success) {
                        showSuccess(
                            t(
                                'editProfile.passwordEmailSent',
                                'If an account exists for this email, we sent a password reset link. Check your inbox.'
                            )
                        );
                        return;
                    }
                    showError(mapApiError(result.body && result.body.detail));
                })
                .catch(function () {
                    showError(
                        t(
                            'editProfile.passwordEmailFailed',
                            'Could not send the password reset email. Check email settings or try again later.'
                        )
                    );
                })
                .finally(function () {
                    resetBtn.disabled = false;
                });
        });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        hideMessages();

        var username = (usernameInput && usernameInput.value) ? usernameInput.value.trim() : '';
        var email = (emailInput && emailInput.value) ? emailInput.value.trim() : '';

        if (!username || !email) {
            showError(t('editProfile.validationRequired', 'Username and email are required.'));
            return;
        }

        var homeCity = (homeCityInput && homeCityInput.value) ? homeCityInput.value.trim() : '';
        var payload = { username: username, email: email, home_city: homeCity };

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
                    if (window.appShell && typeof window.appShell.refreshHeaderProfileAvatar === 'function') {
                        window.appShell.refreshHeaderProfileAvatar();
                    }
                    showSuccess();
                    return;
                }
                showError(mapApiError(result.body && result.body.detail));
            })
            .catch(function () {
                showError(t('editProfile.errorSave', 'Could not save changes.'));
            })
            .finally(function () {
                if (saveBtn) saveBtn.disabled = false;
            });
    });
});
