(function () {
    const SESSION_KEY = 'admin_secret';
    const CONFIRM_PHRASE = 'DELETE EVERYTHING';

    const loginCard = document.getElementById('adminLoginCard');
    const panel = document.getElementById('adminPanel');
    const loginForm = document.getElementById('adminLoginForm');
    const secretInput = document.getElementById('adminSecret');
    const loginSubmit = document.getElementById('adminLoginSubmit');

    const exportBtn = document.getElementById('adminExportBtn');
    const importFile = document.getElementById('adminImportFile');
    const importConfirm = document.getElementById('adminImportConfirm');
    const importBtn = document.getElementById('adminImportBtn');
    const statusEl = document.getElementById('adminStatus');

    function setStatus(text) {
        statusEl.textContent = text || '';
    }

    function showPanel() {
        loginCard.classList.add('hidden');
        panel.classList.remove('hidden');
    }

    function showLogin() {
        panel.classList.add('hidden');
        loginCard.classList.remove('hidden');
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
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginSubmit.disabled = true;
        loginSubmit.textContent = 'Checking...';

        try {
            const secret = secretInput.value.trim();
            const ok = await verifySecret(secret);
            if (ok) {
                sessionStorage.setItem(SESSION_KEY, secret);
                secretInput.value = '';
                showPanel();
            } else {
                showError('Invalid admin secret.');
            }
        } catch {
            showError('Server error. Please try again later.');
        } finally {
            loginSubmit.disabled = false;
            loginSubmit.textContent = 'Unlock';
        }
    });

    exportBtn.addEventListener('click', async () => {
        exportBtn.disabled = true;
        exportBtn.textContent = 'Exporting...';
        setStatus('');

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
            setStatus('Export downloaded.');
        } catch (err) {
            console.error(err);
            showError('Could not export data. ' + (err.message || ''));
        } finally {
            exportBtn.disabled = false;
            exportBtn.textContent = 'Export data (.json)';
        }
    });

    function updateImportButtonState() {
        const confirmed = importConfirm.value.trim() === CONFIRM_PHRASE;
        const hasFile = importFile.files && importFile.files.length > 0;
        importBtn.disabled = !(confirmed && hasFile);
    }

    importConfirm.addEventListener('input', updateImportButtonState);
    importFile.addEventListener('change', updateImportButtonState);

    importBtn.addEventListener('click', () => {
        const file = importFile.files && importFile.files[0];
        if (!file) return;

        showConfirm(
            'This will permanently delete ALL current data in this environment and replace it with the selected file. Continue?',
            async () => {
                importBtn.disabled = true;
                importBtn.textContent = 'Importing...';
                setStatus('');

                try {
                    const text = await file.text();
                    let payload;
                    try {
                        payload = JSON.parse(text);
                    } catch {
                        throw new Error('Selected file is not valid JSON.');
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

                    setStatus('Import complete:\n' + JSON.stringify(data.counts, null, 2));
                    importConfirm.value = '';
                    importFile.value = '';
                    updateImportButtonState();
                } catch (err) {
                    console.error(err);
                    showError(err.message || 'Import failed.');
                } finally {
                    importBtn.disabled = false;
                    importBtn.textContent = 'Import (overwrite all data)';
                }
            }
        );
    });

    init();
})();
