(function () {
  var CONFIRM_PHRASE = 'DELETE EVERYTHING';
  var adminT = window.AdminAuth.adminT;
  var getStoredSecret = window.AdminAuth.getStoredSecret;

  var exportBtn = document.getElementById('adminExportBtn');
  var importFile = document.getElementById('adminImportFile');
  var importFileText = document.getElementById('adminImportFileText');
  var importConfirm = document.getElementById('adminImportConfirm');
  var importBtn = document.getElementById('adminImportBtn');
  var statusEl = document.getElementById('adminStatus');

  var auth = window.AdminAuth.bindAdminAuth({
    loginCard: document.getElementById('adminLoginCard'),
    panel: document.getElementById('adminPanel'),
    loginForm: document.getElementById('adminLoginForm'),
    secretInput: document.getElementById('adminSecret'),
    loginSubmit: document.getElementById('adminLoginSubmit'),
    statusEl: statusEl
  });
  var setStatus = auth.setStatus;

  function mapImportError(detail) {
    var text = typeof detail === 'string' ? detail : '';
    if (/not valid json|invalid export file/i.test(text)) {
      return adminT('admin.invalidFile', 'Selected file is not valid JSON.');
    }
    if (/import failed/i.test(text)) {
      return adminT('admin.importFailed', 'Import failed.');
    }
    return text || adminT('admin.importFailed', 'Import failed.');
  }

  function updateImportFileText() {
    var file = importFile.files && importFile.files[0];
    importFileText.textContent = file
      ? file.name
      : adminT('admin.importFilePrompt', 'Click to choose a file');
  }

  function updateImportButtonState() {
    var confirmed = importConfirm.value.trim() === CONFIRM_PHRASE;
    var hasFile = importFile.files && importFile.files.length > 0;
    importBtn.disabled = !(confirmed && hasFile);
  }

  exportBtn.addEventListener('click', async function () {
    exportBtn.disabled = true;
    setStatus(null);
    try {
      var response = await fetch('/api/admin/export', {
        headers: { 'X-Admin-Secret': getStoredSecret() }
      });
      if (!response.ok) {
        throw new Error(adminT('admin.exportFailed', 'Could not export data.'));
      }
      var text = await response.text();
      var blob = new Blob([text], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      var stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      a.href = url;
      a.download = 'travelapp-export-' + stamp + '.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus(adminT('admin.exportComplete', 'Export downloaded.'), 'success');
    } catch (err) {
      setStatus(
        (err && err.message) || adminT('admin.exportFailed', 'Could not export data.'),
        'error'
      );
    } finally {
      exportBtn.disabled = false;
    }
  });

  importConfirm.addEventListener('input', updateImportButtonState);
  importFile.addEventListener('change', function () {
    updateImportFileText();
    updateImportButtonState();
  });

  importBtn.addEventListener('click', function () {
    var file = importFile.files && importFile.files[0];
    if (!file) return;

    showConfirm(
      adminT(
        'admin.importConfirmPrompt',
        'This will permanently delete ALL current data in this environment and replace it with the selected file. Continue?'
      ),
      async function () {
        importBtn.disabled = true;
        setStatus(null);
        try {
          var text = await file.text();
          var payload;
          try {
            payload = JSON.parse(text);
          } catch (parseErr) {
            throw new Error(adminT('admin.invalidFile', 'Selected file is not valid JSON.'));
          }

          var response = await fetch('/api/admin/import', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Admin-Secret': getStoredSecret()
            },
            body: JSON.stringify(payload)
          });

          var data = await response.json().catch(function () { return {}; });
          if (!response.ok || !data.success) {
            throw new Error(mapImportError(data.detail));
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
          setStatus(
            mapImportError(err && err.message) || adminT('admin.importFailed', 'Import failed.'),
            'error'
          );
        } finally {
          importBtn.disabled = false;
        }
      }
    );
  });
})();
