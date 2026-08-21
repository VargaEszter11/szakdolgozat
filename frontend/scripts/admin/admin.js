(function () {
    const SESSION_KEY = 'admin_secret';
    const CONFIRM_PHRASE = 'DELETE EVERYTHING';

    function adminT(key, fallback) {
        return window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t(key) : fallback;
    }

    const loginCard = document.getElementById('adminLoginCard');
    const panel = document.getElementById('adminPanel');
    const loginForm = document.getElementById('adminLoginForm');
    const secretInput = document.getElementById('adminSecret');
    const loginSubmit = document.getElementById('adminLoginSubmit');

    const exportBtn = document.getElementById('adminExportBtn');
    const importFile = document.getElementById('adminImportFile');
    const importFileText = document.getElementById('adminImportFileText');
    const importConfirm = document.getElementById('adminImportConfirm');
    const importBtn = document.getElementById('adminImportBtn');
    const statusEl = document.getElementById('adminStatus');

    function updateImportFileText() {
        const file = importFile.files && importFile.files[0];
        importFileText.textContent = file
            ? file.name
            : adminT('admin.importFilePrompt', 'Click to choose a file');
    }

    function setStatus(text, type) {
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
    }

    function showLogin() {
        panel.classList.add('hidden');
        loginCard.classList.remove('hidden');
    }

    function revealPage() {
        if (window.markAppReady) window.markAppReady();
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

    exportBtn.addEventListener('click', async () => {
        exportBtn.disabled = true;
        setStatus(null);

        try {
            const response = await fetch('/api/admin/export', {
                headers: { 'X-Admin-Secret': getStoredSecret() }
            });
            if (!response.ok) {
                throw new Error('Export failed (' + response.status + ')');
            }
            const text = await response.text();
            const blob = new Blob([text], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
            a.href = url;
            a.download = 'travelapp-export-' + stamp + '.json';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            setStatus(adminT('admin.exportComplete', 'Export downloaded.'), 'success');
        } catch (err) {
            console.error(err);
            showError(adminT('admin.exportFailed', 'Could not export data.') + ' ' + (err.message || ''));
        } finally {
            exportBtn.disabled = false;
        }
    });

    function updateImportButtonState() {
        const confirmed = importConfirm.value.trim() === CONFIRM_PHRASE;
        const hasFile = importFile.files && importFile.files.length > 0;
        importBtn.disabled = !(confirmed && hasFile);
    }

    importConfirm.addEventListener('input', updateImportButtonState);
    importFile.addEventListener('change', () => {
        updateImportFileText();
        updateImportButtonState();
    });

    importBtn.addEventListener('click', () => {
        const file = importFile.files && importFile.files[0];
        if (!file) return;

        showConfirm(
            adminT(
                'admin.importConfirmPrompt',
                'This will permanently delete ALL current data in this environment and replace it with the selected file. Continue?'
            ),
            async () => {
                importBtn.disabled = true;
                setStatus(null);

                try {
                    const text = await file.text();
                    let payload;
                    try {
                        payload = JSON.parse(text);
                    } catch {
                        throw new Error(adminT('admin.invalidFile', 'Selected file is not valid JSON.'));
                    }

                    const response = await fetch('/api/admin/import', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Admin-Secret': getStoredSecret()
                        },
                        body: JSON.stringify(payload)
                    });

                    const data = await response.json();
                    if (!response.ok || !data.success) {
                        throw new Error(data.detail || ('Import failed (' + response.status + ')'));
                    }

                    setStatus(
                        adminT('admin.importComplete', 'Import complete:') + '\n' + JSON.stringify(data.counts, null, 2),
                        'success'
                    );
                    importConfirm.value = '';
                    importFile.value = '';
                    updateImportFileText();
                    updateImportButtonState();
                } catch (err) {
                    console.error(err);
                    setStatus(err.message || adminT('admin.importFailed', 'Import failed.'), 'error');
                } finally {
                    importBtn.disabled = false;
                }
            }
        );
    });

    init();
})();
