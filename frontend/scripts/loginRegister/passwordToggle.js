// Show/hide password on auth forms
document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        const input = btn.parentElement.querySelector('input');
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';

        btn.querySelector('.eye-open').style.display = isHidden ? 'none' : '';
        btn.querySelector('.eye-closed').style.display = isHidden ? '' : 'none';

        var showLabel = 'Show password';
        var hideLabel = 'Hide password';
        if (window.i18n && typeof window.i18n.t === 'function') {
            var s = window.i18n.t('login.showPassword');
            var h = window.i18n.t('login.hidePassword');
            if (s && s !== 'login.showPassword') showLabel = s;
            if (h && h !== 'login.hidePassword') hideLabel = h;
        }
        btn.setAttribute('aria-label', isHidden ? hideLabel : showLabel);
    });
});
