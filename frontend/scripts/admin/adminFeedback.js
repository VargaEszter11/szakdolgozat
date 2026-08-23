(function () {
  var adminT = window.AdminAuth.adminT;
  var getStoredSecret = window.AdminAuth.getStoredSecret;

  var feedbackListEl = document.getElementById('adminFeedbackList');
  var statusEl = document.getElementById('adminStatus');

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var setStatus;

  async function loadFeedback() {
    if (!feedbackListEl) return;
    setStatus(null);
    feedbackListEl.innerHTML = '<p class="muted">' +
      escapeHtml(adminT('admin.feedbackLoading', 'Loading…')) + '</p>';
    try {
      var response = await fetch('/api/admin/feedback', {
        headers: { 'X-Admin-Secret': getStoredSecret() }
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var items = await response.json();
      if (!items.length) {
        feedbackListEl.innerHTML = '<p class="muted">' +
          escapeHtml(adminT('admin.feedbackEmpty', 'No feedback yet.')) + '</p>';
        return;
      }
      feedbackListEl.innerHTML = items.map(function (item) {
        var when = item.created_at ? new Date(item.created_at).toLocaleString() : '';
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
        btn.addEventListener('click', function () {
          var id = btn.getAttribute('data-id');
          if (!id) return;
          showConfirm(
            adminT('admin.feedbackDeleteConfirm', 'Delete this feedback message?'),
            async function () {
              btn.disabled = true;
              try {
                var res = await fetch('/api/admin/feedback/' + id, {
                  method: 'DELETE',
                  headers: { 'X-Admin-Secret': getStoredSecret() }
                });
                if (!res.ok) throw new Error('HTTP ' + res.status);
                await loadFeedback();
              } catch (err) {
                setStatus(adminT('admin.feedbackDeleteFailed', 'Could not delete feedback.'), 'error');
                btn.disabled = false;
              }
            }
          );
        });
      });
    } catch (err) {
      feedbackListEl.innerHTML = '<p class="muted">' +
        escapeHtml(adminT('admin.feedbackLoadFailed', 'Could not load feedback.')) + '</p>';
    }
  }

  var auth = window.AdminAuth.bindAdminAuth({
    loginCard: document.getElementById('adminLoginCard'),
    panel: document.getElementById('adminPanel'),
    loginForm: document.getElementById('adminLoginForm'),
    secretInput: document.getElementById('adminSecret'),
    loginSubmit: document.getElementById('adminLoginSubmit'),
    statusEl: statusEl,
    onUnlocked: loadFeedback
  });
  setStatus = auth.setStatus;
})();
