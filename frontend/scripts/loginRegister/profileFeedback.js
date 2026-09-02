(function () {
  function tFeedback(key, fallback) {
    return window.i18n && window.i18n.t ? window.i18n.t(key) : fallback;
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function previewMessage(text, limit) {
    var raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (raw.length <= limit) return raw;
    return raw.slice(0, limit - 1).trim() + '…';
  }

  function initProfileFeedback() {
    var feedbackSection = document.getElementById('profileFeedbackSection');
    var feedbackForm = document.getElementById('feedbackForm');
    var feedbackMessage = document.getElementById('feedbackMessage');
    var feedbackImage = document.getElementById('feedbackImage');
    var feedbackImagePreview = document.getElementById('feedbackImagePreview');
    var feedbackImageErrors = document.getElementById('feedbackImageErrors');
    var feedbackStatus = document.getElementById('feedbackStatus');
    var feedbackSubmit = document.getElementById('feedbackSubmit');
    var feedbackListEl = document.getElementById('profileFeedbackList');
    var feedbackItemsById = {};

    if (!feedbackSection) return;

    function closeFeedbackDetailModal() {
      var el = document.getElementById('profileFeedbackDetailOverlay');
      if (el && el.parentNode) el.parentNode.removeChild(el);
    }

    function openFeedbackDetailModal(item) {
      if (!item) return;
      closeFeedbackDetailModal();

      var when = item.created_at ? new Date(item.created_at).toLocaleString() : '—';
      var statusLabel = item.solved
        ? tFeedback('profile.feedbackStatusSolved', 'Solved')
        : tFeedback('profile.feedbackStatusPending', 'Pending');
      var statusClass = item.solved
        ? 'profile-feedback-status-pill--solved'
        : 'profile-feedback-status-pill--pending';

      var overlay = document.createElement('div');
      overlay.id = 'profileFeedbackDetailOverlay';
      overlay.className = 'profile-feedback-detail-overlay';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.setAttribute(
        'aria-label',
        tFeedback('profile.feedbackDetailTitle', 'Feedback details')
      );

      var panel = document.createElement('div');
      panel.className = 'profile-feedback-detail-panel';
      panel.innerHTML =
        '<div class="profile-feedback-detail-header">' +
        '<h3 class="profile-feedback-detail-title">' +
        escapeHtml(tFeedback('profile.feedbackDetailTitle', 'Feedback details')) +
        '</h3>' +
        '<button type="button" class="profile-feedback-detail-close" aria-label="' +
        escapeHtml(tFeedback('profile.feedbackDetailClose', 'Close')) +
        '">×</button>' +
        '</div>' +
        '<div class="profile-feedback-detail-meta">' +
        '<span class="profile-feedback-status-pill ' +
        statusClass +
        '">' +
        escapeHtml(statusLabel) +
        '</span>' +
        '<span class="muted">' +
        escapeHtml(when) +
        '</span>' +
        '</div>' +
        '<p class="profile-feedback-detail-message">' +
        escapeHtml(item.message || '') +
        '</p>' +
        (item.image_path
          ? '<a class="profile-feedback-detail-image-link" href="' +
            escapeHtml(item.image_path) +
            '" target="_blank" rel="noopener noreferrer">' +
            '<img class="profile-feedback-detail-image" src="' +
            escapeHtml(item.image_path) +
            '" alt="">' +
            '</a>'
          : '') +
        '<div class="profile-feedback-detail-actions">' +
        '<button type="button" class="btn-add profile-feedback-detail-ok">' +
        escapeHtml(tFeedback('profile.feedbackDetailClose', 'Close')) +
        '</button>' +
        '</div>';

      overlay.appendChild(panel);
      document.body.appendChild(overlay);

      function onKey(e) {
        if (e.key === 'Escape') cleanup();
      }

      function cleanup() {
        document.removeEventListener('keydown', onKey);
        closeFeedbackDetailModal();
      }

      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) cleanup();
      });
      panel.querySelector('.profile-feedback-detail-close').addEventListener('click', cleanup);
      panel.querySelector('.profile-feedback-detail-ok').addEventListener('click', cleanup);
      document.addEventListener('keydown', onKey);
    }

    async function loadMyFeedback() {
      if (!feedbackListEl) return;
      feedbackItemsById = {};
      try {
        var res = await fetch('/api/feedback/mine');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var items = await res.json();
        if (!items.length) {
          feedbackListEl.innerHTML =
            '<p class="muted">' +
            escapeHtml(tFeedback('profile.feedbackHistoryEmpty', 'You have not sent feedback yet.')) +
            '</p>';
          return;
        }

        var previewLimit = 3;
        var collapsed = items.length > previewLimit;
        var html = items
          .map(function (item, index) {
            feedbackItemsById[String(item.id)] = item;
            var when = item.created_at ? new Date(item.created_at).toLocaleString() : '';
            var statusLabel = item.solved
              ? tFeedback('profile.feedbackStatusSolved', 'Solved')
              : tFeedback('profile.feedbackStatusPending', 'Pending');
            var statusClass = item.solved
              ? 'profile-feedback-status-pill--solved'
              : 'profile-feedback-status-pill--pending';
            var hasImage = !!item.image_path;
            var hiddenClass =
              collapsed && index >= previewLimit ? ' profile-feedback-item--collapsed' : '';
            return (
              '<button type="button" class="profile-feedback-item' +
              hiddenClass +
              '" data-feedback-id="' +
              escapeHtml(String(item.id)) +
              '">' +
              '<div class="profile-feedback-item-meta">' +
              '<span class="profile-feedback-status-pill ' +
              statusClass +
              '">' +
              escapeHtml(statusLabel) +
              '</span>' +
              '<span class="muted">' +
              escapeHtml(when) +
              '</span>' +
              (hasImage
                ? '<span class="profile-feedback-item-has-image muted">' +
                  escapeHtml(tFeedback('profile.feedbackHasImage', 'Has image')) +
                  '</span>'
                : '') +
              '</div>' +
              '<p class="profile-feedback-item-message">' +
              escapeHtml(previewMessage(item.message, 140)) +
              '</p>' +
              '</button>'
            );
          })
          .join('');

        if (collapsed) {
          html +=
            '<button type="button" class="profile-feedback-more" data-feedback-more="1" aria-expanded="false">' +
            escapeHtml(tFeedback('profile.feedbackHistoryMore', 'More')) +
            '</button>';
        }

        feedbackListEl.innerHTML = html;
        feedbackListEl.dataset.feedbackExpanded = '0';
      } catch (e) {
        feedbackListEl.innerHTML =
          '<p class="muted">' +
          escapeHtml(tFeedback('profile.feedbackHistoryFailed', 'Could not load your feedback.')) +
          '</p>';
      }
    }

    function setFeedbackStatus(text, isError) {
      if (!feedbackStatus) return;
      if (!text) {
        feedbackStatus.hidden = true;
        feedbackStatus.textContent = '';
        feedbackStatus.classList.remove(
          'profile-feedback-status--error',
          'profile-feedback-status--success'
        );
        return;
      }
      feedbackStatus.hidden = false;
      feedbackStatus.textContent = text;
      feedbackStatus.classList.remove(
        'profile-feedback-status--error',
        'profile-feedback-status--success'
      );
      feedbackStatus.classList.add(
        isError ? 'profile-feedback-status--error' : 'profile-feedback-status--success'
      );
    }

    if (feedbackListEl && !feedbackListEl.dataset.bound) {
      feedbackListEl.dataset.bound = '1';
      feedbackListEl.addEventListener('click', function (e) {
        var moreBtn = e.target.closest('[data-feedback-more]');
        if (moreBtn && feedbackListEl.contains(moreBtn)) {
          var expanded = feedbackListEl.dataset.feedbackExpanded === '1';
          var nextExpanded = !expanded;
          feedbackListEl.dataset.feedbackExpanded = nextExpanded ? '1' : '0';
          feedbackListEl.querySelectorAll('.profile-feedback-item--collapsed').forEach(function (el) {
            el.classList.toggle('profile-feedback-item--visible', nextExpanded);
          });
          moreBtn.setAttribute('aria-expanded', nextExpanded ? 'true' : 'false');
          moreBtn.textContent = nextExpanded
            ? tFeedback('profile.feedbackHistoryLess', 'Show less')
            : tFeedback('profile.feedbackHistoryMore', 'More');
          return;
        }

        var btn = e.target.closest('[data-feedback-id]');
        if (!btn || !feedbackListEl.contains(btn)) return;
        openFeedbackDetailModal(feedbackItemsById[btn.getAttribute('data-feedback-id')]);
      });
    }

    feedbackSection.hidden = false;
    if (window.i18n && typeof window.i18n.applyToPage === 'function') {
      window.i18n.applyToPage(feedbackSection);
    }
    loadMyFeedback();

    var feedbackImagePicker =
      window.ImageUpload && feedbackImage
        ? window.ImageUpload.createPicker({
            input: feedbackImage,
            previewGrid: feedbackImagePreview,
            errorsEl: feedbackImageErrors,
            maxFiles: 1,
            formatError: function (err) {
              if (err.reason === 'size') {
                return tFeedback(
                  'profile.feedbackImageTooLarge',
                  'Image is too large (max 10MB).'
                );
              }
              return tFeedback(
                'profile.feedbackImageInvalidType',
                'Only PNG or JPEG files are allowed.'
              );
            }
          })
        : null;

    if (feedbackForm && feedbackMessage) {
      feedbackForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        var msg = (feedbackMessage.value || '').trim();
        if (!msg) {
          setFeedbackStatus(tFeedback('profile.feedbackEmpty', 'Please enter a message.'), true);
          return;
        }
        if (feedbackSubmit) feedbackSubmit.disabled = true;
        setFeedbackStatus(null);
        try {
          var formData = new FormData();
          formData.append('message', msg);
          var files = feedbackImagePicker ? feedbackImagePicker.getFiles() : [];
          if (files[0]) formData.append('image', files[0]);

          var res = await fetch('/api/feedback', {
            method: 'POST',
            body: formData
          });
          if (!res.ok) {
            var errBody = await res.json().catch(function () {
              return {};
            });
            var detail = errBody.detail;
            if (Array.isArray(detail)) {
              detail = detail
                .map(function (d) {
                  return d.msg || '';
                })
                .join(' ');
            }
            detail = typeof detail === 'string' ? detail : '';
            var errKey = 'profile.feedbackFailed';
            var errFallback = 'Could not send feedback. Please try again.';
            if (/empty/i.test(detail)) {
              errKey = 'profile.feedbackEmpty';
              errFallback = 'Please enter a message.';
            } else if (/too long/i.test(detail)) {
              errKey = 'profile.feedbackTooLong';
              errFallback = 'Message is too long (max 2000 characters).';
            } else if (/unsupported|jpeg|png|image type/i.test(detail)) {
              errKey = 'profile.feedbackImageInvalidType';
              errFallback = 'Only PNG or JPEG files are allowed.';
            } else if (/too large|10\s?MB/i.test(detail)) {
              errKey = 'profile.feedbackImageTooLarge';
              errFallback = 'Image is too large (max 10MB).';
            }
            setFeedbackStatus(tFeedback(errKey, errFallback), true);
            return;
          }
          feedbackMessage.value = '';
          if (feedbackImagePicker) feedbackImagePicker.clear();
          setFeedbackStatus(
            tFeedback('profile.feedbackSent', 'Thanks! Your feedback was sent.'),
            false
          );
          loadMyFeedback();
          if (window.HeaderNotifications && window.HeaderNotifications.refresh) {
            window.HeaderNotifications.refresh();
          }
        } catch (err) {
          setFeedbackStatus(
            tFeedback('profile.feedbackFailed', 'Could not send feedback. Please try again.'),
            true
          );
        } finally {
          if (feedbackSubmit) feedbackSubmit.disabled = false;
        }
      });
    }
  }

  window.ProfileFeedback = {
    init: initProfileFeedback
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!localStorage.getItem('user_id') || !localStorage.getItem('username')) return;
    initProfileFeedback();
  });
})();
