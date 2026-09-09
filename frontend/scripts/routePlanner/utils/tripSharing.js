(function (global) {
  'use strict';

  function plannedTripsT(key, fallback) {
    if (global.i18n && typeof global.i18n.t === 'function') {
      var v = global.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  var DU = global.TripDateUtils;
  var escapeHtml = DU ? DU.escapeHtml : function (s) { return s || ''; };

  var deps = { refreshList: function () { return Promise.resolve(); } };

  function init(options) {
    options = options || {};
    if (typeof options.refreshList === 'function') deps.refreshList = options.refreshList;
  }

  function destroyPopups() {
    if (global.TripPopups && typeof global.TripPopups.destroyAll === 'function') {
      global.TripPopups.destroyAll();
    }
  }

  function absoluteShareUrl(relativePath) {
    if (!relativePath) return '';
    if (/^https?:\/\//i.test(relativePath)) return relativePath;
    // Public /share page is served with the frontend origin
    var base = global.location.origin || '';
    if (relativePath.charAt(0) === '/') return base + relativePath;
    return base + '/' + relativePath;
  }

  async function createShareLink(tripId) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return null;
    var response = await fetch('/api/planned-trips/' + tripId + '/share-link', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: parseInt(userId, 10) })
    });
    if (!response.ok) throw new Error('share-link ' + response.status);
    return response.json();
  }

  async function sendTripShare(tripId, toUserId) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return false;
    var response = await fetch('/api/planned-trips/' + tripId + '/share', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_user_id: parseInt(userId, 10),
        to_user_id: parseInt(toUserId, 10)
      })
    });
    if (!response.ok) throw new Error('share ' + response.status);
    return true;
  }

  async function searchShareUsers(query) {
    var userId = localStorage.getItem('user_id');
    if (!userId || !query || !String(query).trim()) return [];
    var params = new URLSearchParams({
      search: String(query).trim(),
      exclude_user_id: userId,
      limit: '20'
    });
    var response = await fetch('/api/users?' + params.toString());
    if (!response.ok) return [];
    var data = await response.json();
    return Array.isArray(data) ? data : [];
  }

  async function openShareModal(tripId) {
    try {
      destroyPopups();
      var template = document.getElementById('tripShareModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var linkInput = modal.querySelector('#tripShareLinkInput');
      var copyBtn = modal.querySelector('#tripShareCopyBtn');
      var searchInput = modal.querySelector('#tripShareUserSearch');
      var resultsEl = modal.querySelector('#tripShareUserResults');
      var sendBtn = modal.querySelector('#tripShareSendBtn');
      var selectedUserId = null;

      if (global.i18n && typeof global.i18n.applyToPage === 'function') {
        global.i18n.applyToPage(modal);
      }

      try {
        var linkData = await createShareLink(tripId);
        if (linkInput && linkData) {
          linkInput.value = absoluteShareUrl(linkData.share_url || '');
        }
      } catch (e) {
        console.error(e);
        showError(plannedTripsT('shareLinkError', 'Could not create share link.'));
      }

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        modal.remove();
      }

      if (copyBtn && linkInput) {
        copyBtn.addEventListener('click', function () {
          var url = linkInput.value;
          if (!url) return;
          function notifyCopied() {
            var msg = plannedTripsT('linkCopied', 'Link copied to clipboard.');
            if (typeof showModal === 'function') {
              showModal({ title: plannedTripsT('copyLink', 'Copy link'), message: msg, type: 'success' });
            } else {
              showError(msg);
            }
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(notifyCopied).catch(function () {
              linkInput.select();
              document.execCommand('copy');
              notifyCopied();
            });
          } else {
            linkInput.select();
            document.execCommand('copy');
            notifyCopied();
          }
        });
      }

      function renderUserResults(users) {
        if (!resultsEl) return;
        resultsEl.innerHTML = '';
        selectedUserId = null;
        if (sendBtn) sendBtn.disabled = true;
        users.forEach(function (user) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'trip-share-user-option';
          btn.textContent = user.username;
          btn.setAttribute('data-user-id', String(user.id));
          btn.addEventListener('click', function () {
            resultsEl.querySelectorAll('.trip-share-user-option').forEach(function (el) {
              el.classList.remove('selected');
            });
            btn.classList.add('selected');
            selectedUserId = user.id;
            if (sendBtn) sendBtn.disabled = false;
          });
          resultsEl.appendChild(btn);
        });
      }

      var searchTimer = null;
      if (searchInput) {
        searchInput.addEventListener('input', function () {
          clearTimeout(searchTimer);
          searchTimer = setTimeout(function () {
            searchShareUsers(searchInput.value).then(renderUserResults);
          }, 250);
        });
      }

      if (sendBtn) {
        sendBtn.addEventListener('click', async function () {
          if (!selectedUserId) return;
          sendBtn.disabled = true;
          try {
            await sendTripShare(tripId, selectedUserId);
            var sentMsg = plannedTripsT('shareSent', 'Trip share invitation sent.');
            if (typeof showModal === 'function') {
              showModal({ title: plannedTripsT('shareTrip', 'Share trip'), message: sentMsg, type: 'success' });
            } else {
              showError(sentMsg);
            }
            removeModal();
          } catch (e) {
            console.error(e);
            showError(plannedTripsT('shareSendError', 'Could not send trip share.'));
            sendBtn.disabled = false;
          }
        });
      }

      var closeBtn = modal.querySelector('.trip-details-close');
      var modalBox = modal.querySelector('#tripShareModalBox');
      if (closeBtn) closeBtn.addEventListener('click', removeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
      });
      if (modalBox) modalBox.addEventListener('click', function (e) { e.stopPropagation(); });
      function handleEsc(e) { if (e.key === 'Escape') removeModal(); }
      document.addEventListener('keydown', handleEsc);
    } catch (err) {
      console.error('openShareModal', err);
      showError(plannedTripsT('shareLinkError', 'Could not create share link.'));
    }
  }

  async function respondToShareInvitation(invitationId, action) {
    var userId = localStorage.getItem('user_id');
    if (!userId) return;
    var response = await fetch('/api/trip-share-invitations/' + invitationId + '/' + action, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: parseInt(userId, 10) })
    });
    if (!response.ok) throw new Error(action + ' ' + response.status);
  }

  async function loadShareInbox() {
    var userId = localStorage.getItem('user_id');
    var section = document.getElementById('shareInboxSection');
    var inbox = document.getElementById('shareInbox');
    if (!userId || !section || !inbox) return;

    try {
      var response = await fetch('/api/users/' + userId + '/trip-share-invitations?status=pending');
      if (!response.ok) {
        section.classList.add('hidden');
        return;
      }
      var invitations = await response.json();
      section.classList.remove('hidden');
      if (!Array.isArray(invitations) || invitations.length === 0) {
        inbox.innerHTML =
          '<p class="muted share-inbox-empty">' +
          escapeHtml(plannedTripsT('shareInboxEmpty', 'No pending trip invitations.')) +
          '</p>';
        return;
      }

      inbox.innerHTML = invitations.map(function (inv) {
        var title = inv.source_trip && inv.source_trip.title ? inv.source_trip.title : 'Trip';
        var sharer = inv.from_username
          || (inv.from_user_id != null ? ('#' + inv.from_user_id) : 'User');
        var fromLabel = plannedTripsT('shareFromUser', 'From {{user}}').replace('{{user}}', String(sharer));
        return (
          '<div class="share-inbox-card" data-invitation-id="' + inv.id + '">' +
          '<div><strong>' + escapeHtml(title) + '</strong><br><span class="muted">' + escapeHtml(fromLabel) + '</span></div>' +
          '<div class="share-inbox-card-actions">' +
          '<button type="button" class="btn-add share-accept" data-id="' + inv.id + '">' + escapeHtml(plannedTripsT('acceptShare', 'Accept')) + '</button>' +
          '<button type="button" class="btn-cancel share-decline" data-id="' + inv.id + '">' + escapeHtml(plannedTripsT('declineShare', 'Decline')) + '</button>' +
          '</div></div>'
        );
      }).join('');

      if (global.i18n && typeof global.i18n.applyToPage === 'function') {
        global.i18n.applyToPage(section);
      }
    } catch (e) {
      console.error('loadShareInbox', e);
      section.classList.add('hidden');
    }
  }

  function bindShareInboxActions() {
    var inbox = document.getElementById('shareInbox');
    if (!inbox || inbox.dataset.shareInboxBound === '1') return;
    inbox.dataset.shareInboxBound = '1';
    inbox.addEventListener('click', function (e) {
      var acceptBtn = e.target.closest('.share-accept');
      var declineBtn = e.target.closest('.share-decline');
      var btn = acceptBtn || declineBtn;
      if (!btn) return;
      e.preventDefault();
      var id = parseInt(btn.getAttribute('data-id'), 10);
      if (Number.isNaN(id)) return;
      var action = acceptBtn ? 'accept' : 'decline';
      respondToShareInvitation(id, action)
        .then(function () {
          return Promise.all([loadShareInbox(), deps.refreshList()]);
        })
        .catch(function (err) {
          console.error(err);
          showError(plannedTripsT('shareSendError', 'Could not send trip share.'));
        });
    });
  }

  global.TripSharing = {
    init: init,
    openShareModal: openShareModal,
    loadShareInbox: loadShareInbox,
    bindShareInboxActions: bindShareInboxActions
  };
})(window);
