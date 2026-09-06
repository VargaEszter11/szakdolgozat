function verifyEmailT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
        var v = window.i18n.t(key);
        if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
}

function getVerifyTokenFromUrl() {
    try {
        return new URLSearchParams(window.location.search).get('token') || '';
    } catch (e) {
        return '';
    }
}

(function init() {
    var token = getVerifyTokenFromUrl();
    var pending = document.getElementById('verifyEmailPending');
    var success = document.getElementById('verifyEmailSuccess');
    var invalid = document.getElementById('verifyEmailInvalid');

    function show(el) {
        if (pending) pending.classList.add('hidden');
        if (success) success.classList.add('hidden');
        if (invalid) invalid.classList.add('hidden');
        if (el) el.classList.remove('hidden');
    }

    if (!token) {
        show(invalid);
        return;
    }

    fetch('/api/verify-email/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
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
                show(success);
                return;
            }
            show(invalid);
        })
        .catch(function () {
            show(invalid);
        });
})();
