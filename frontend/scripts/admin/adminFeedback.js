(function () {
    const SESSION_KEY = 'admin_secret';

    function adminT(key, fallback) {
        return window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t(key) : fallback;
    }

    const loginCard = document.getElementById('adminLoginCard');
    const panel = document.getElementById('adminPanel');
    const loginForm = document.getElementById('adminLoginForm');
    const secretInput = document.getElementById('adminSecret');
    const loginSubmit = document.getElementById('adminLoginSubmit');
    const feedbackListEl = document.getElementById('adminFeedbackList');
    const statusEl = document.getElementById('adminStatus');

    function setStatus(text, type) {
        if (!statusEl) return;
        if (!text) {
            statusEl.hidden = true;
            statusEl.textContent = '';
            statusEl.classList.remove('admin-message--success', 'admin-message--error');
            return;
        }
        statusEl.hidden = false;
        statusEl.textContent = text;
        statusEl.classList.remove('admin-message--success', 'admin-message--error');
        statusEl.classList.add(type === 'error' ? 'admin-message--error' : 'admin-message--success');
    }

    function showPanel() {
        loginCard.classList.add('hidden');
        panel.classList.remove('hidden');
        loadFeedback();
    }

    function showLogin() {
        panel.classList.add('hidden');
        loginCard.classList.remove('hidden');
    }

    function revealPage() {
        if (window.markAppReady) window.markAppReady();
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    async function verifySecret(secret) {
        const response = await fetch('/api/admin/ping', {
            headers: { 'X-Admin-Secret': secret }
        });
        return response.ok;
    }

    function getStoredSecret() {
        return sessionStorage.getItem(SESSION_KEY) || '';
    }

    async function loadFeedback() {
        if (!feedbackListEl) return;
        setStatus(null);
        feedbackListEl.innerHTML = '<p class="muted">' +
            escapeHtml(adminT('admin.feedbackLoading', 'Loading…')) + '</p>';
        try {
            const response = await fetch('/api/admin/feedback', {
                headers: { 'X-Admin-Secret': getStoredSecret() }
            });
            if (!response.ok) throw new Error('HTTP ' + response.status);
            const items = await response.json();
            if (!items.length) {
                feedbackListEl.innerHTML = '<p class="muted">' +
                    escapeHtml(adminT('admin.feedbackEmpty', 'No feedback yet.')) + '</p>';
                return;
            }
            feedbackListEl.innerHTML = items.map(function (item) {
                const when = item.created_at ? new Date(item.created_at).toLocaleString() : '';
                return (
                    '<article class="admin-feedback-item" data-id="' + item.id + '">' +
                    '<div class="admin-feedback-meta">' +
                    '<strong>' + escapeHtml(item.username) + '</strong>' +
                    (item.email ? ' <span class="muted">&lt;' + escapeHtml(item.email) + '&gt;</span>' : '') +
                    '<span class="muted admin-feedback-date">' + escapeHtml(when) + '</span>' +
                    '</div>' +
                    '<p class="admin-feedback-message">' + escapeHtml(item.message) + '</p>' +
                    (item.image_path
                        ? '<a class="admin-feedback-image-link" href="' + escapeHtml(item.image_path) +
                          '" target="_blank" rel="noopener">' +
                          '<img class="admin-feedback-image" src="' + escapeHtml(item.image_path) +
                          '" alt="">' +
                          '</a>'
                        : '') +
                    '<div class="admin-feedback-actions">' +
                    '<button type="button" class="btn-add btn-add-danger admin-feedback-delete" data-id="' + item.id + '">' +
                    escapeHtml(adminT('admin.feedbackDelete', 'Delete')) +
                    '</button>' +
                    '</div>' +
                    '</article>'
                );
            }).join('');

            feedbackListEl.querySelectorAll('.admin-feedback-delete').forEach(function (btn) {
                btn.addEventListener('click', async function () {
                    const id = btn.getAttribute('data-id');
                    if (!id) return;
                    btn.disabled = true;
                    try {
                        const res = await fetch('/api/admin/feedback/' + id, {
                            method: 'DELETE',
                            headers: { 'X-Admin-Secret': getStoredSecret() }
                        });
                        if (!res.ok) throw new Error('HTTP ' + res.status);
                        await loadFeedback();
                    } catch (err) {
                        console.error(err);
                        setStatus(adminT('admin.feedbackDeleteFailed', 'Could not delete feedback.'), 'error');
                        btn.disabled = false;
                    }
                });
            });
        } catch (err) {
            console.error(err);
            feedbackListEl.innerHTML = '<p class="muted">' +
                escapeHtml(adminT('admin.feedbackLoadFailed', 'Could not load feedback.')) + '</p>';
        }
    }

    async function init() {
        try {
            const stored = getStoredSecret();
            if (!stored) {
                showLogin();
                return;
            }
            const ok = await verifySecret(stored);
            if (ok) {
                showPanel();
            } else {
                sessionStorage.removeItem(SESSION_KEY);
                showLogin();
            }
        } finally {
            revealPage();
        }
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginSubmit.disabled = true;

        try {
            const secret = secretInput.value.trim();
            const ok = await verifySecret(secret);
            if (ok) {
                sessionStorage.setItem(SESSION_KEY, secret);
                secretInput.value = '';
                showPanel();
            } else {
                showError(adminT('admin.invalidSecret', 'Invalid admin secret.'));
            }
        } catch {
            showError(adminT('admin.serverError', 'Server error. Please try again later.'));
        } finally {
            loginSubmit.disabled = false;
        }
    });

    init();
})();
