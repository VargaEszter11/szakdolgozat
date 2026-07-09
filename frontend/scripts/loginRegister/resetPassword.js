function resetPasswordT(key, fallback) {
    return window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t(key) : fallback;
}

function getResetTokenFromUrl() {
    try {
        return new URLSearchParams(window.location.search).get('token') || '';
    } catch (e) {
        return '';
    }
}

(function init() {
    const token = getResetTokenFromUrl();
    if (!token) {
        document.getElementById('resetPasswordCard').classList.add('hidden');
        document.getElementById('resetPasswordInvalid').classList.remove('hidden');
        return;
    }

    const form = document.getElementById('resetPasswordForm');
    const passwordInput = document.getElementById('newPassword');
    const confirmInput = document.getElementById('confirmPassword');
    const submitBtn = document.getElementById('resetPasswordSubmit');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (passwordInput.value !== confirmInput.value) {
            showError(resetPasswordT('resetPassword.passwordMismatch', 'Passwords do not match.'));
            return;
        }

        if (passwordInput.value.length < 6) {
            showError(resetPasswordT('resetPassword.passwordTooShort', 'Password must be at least 6 characters.'));
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = resetPasswordT('resetPassword.submit', 'Reset password');

        try {
            const response = await fetch('/api/forgot-password/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    new_password: passwordInput.value
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                window.location.href = '/pages/loginRegister/loginPage.html';
            } else {
                showError(data.detail || resetPasswordT('resetPassword.resetFailed', 'Reset failed.'));
            }
        } catch {
            showError(resetPasswordT('resetPassword.serverError', 'Server error. Please try again later.'));
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = resetPasswordT('resetPassword.submit', 'Reset password');
        }
    });
})();
