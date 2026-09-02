(function () {
  var DISMISS_KEY = 'planventure.notifications.dismissed.v1';

  function t(key, fallback, vars) {
    var out = fallback || key;
    if (window.i18n && typeof window.i18n.t === 'function') {
      var v = window.i18n.t(key);
      if (v && v.indexOf(key) !== 0) out = v;
    }
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        out = out.replace(new RegExp('\\{\\{' + k + '\\}\\}', 'g'), String(vars[k]));
      });
    }
    return out;
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function readDismissed() {
    try {
      var raw = localStorage.getItem(DISMISS_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch (e) {
      return [];
    }
  }

  function writeDismissed(ids) {
    try {
      localStorage.setItem(DISMISS_KEY, JSON.stringify(ids.slice(-200)));
    } catch (e) {
      /* ignore */
    }
  }

  function dismissId(id) {
    var ids = readDismissed();
    if (ids.indexOf(String(id)) === -1) {
      ids.push(String(id));
      writeDismissed(ids);
    }
  }

  function localizeItem(item) {
    var type = item.type || '';
    var meta = item.meta || {};
    if (type === 'share_pending') {
      return {
        title: t('notifications.shareTitle', 'Shared trip invitation'),
        body: t('notifications.shareBody', '{{user}} shared “{{trip}}” with you.', {
          user: meta.from_username || 'Someone',
          trip: meta.trip_title || 'Trip'
        })
      };
    }
    if (type === 'feedback_solved') {
      return {
        title: t('notifications.feedbackSolvedTitle', 'Feedback marked as solved'),
        body: meta.message_preview || item.body || ''
      };
    }
    if (type === 'trip_completed') {
      return {
        title: t('notifications.tripCompletedTitle', 'Trip completed'),
        body: t('notifications.tripCompletedBody', '“{{trip}}” ended on {{date}}.', {
          trip: meta.trip_title || 'Trip',
          date: meta.end_date || ''
        })
      };
    }
    if (type === 'planner_ready') {
      return {
        title: t('notifications.plannerReadyTitle', 'Your trip plan is ready'),
        body: meta.trip_title
          ? t('notifications.plannerReadyBody', 'Open “{{trip}}” to review and save.', {
            trip: meta.trip_title
          })
          : t('notifications.plannerReadyBodyGeneric', 'Open the planner to review and save it.')
      };
    }
    return { title: item.title || '', body: item.body || '' };
  }

  /** Ready draft from sessionStorage (after the toast was dismissed). */
  function plannerReadyItem() {
    var PS = window.PlannerSession;
    if (!PS || typeof PS.load !== 'function') return null;
    if (typeof PS.isPlannerPage === 'function' && PS.isPlannerPage()) return null;
    var session = PS.load();
    if (!session || session.status !== 'ready' || !session.resultData) return null;
    var title =
      (session.resultData && session.resultData.userTripTitle) ||
      (session.form && session.form.tripTitle) ||
      '';
    var genId = session.generationId != null ? String(session.generationId) : '1';
    return {
      id: 'planner_ready:' + genId,
      type: 'planner_ready',
      title: 'Your trip plan is ready',
      body: title || '',
      href: (typeof PS.plannerPageUrl === 'function' ? PS.plannerPageUrl() : '/trips/new') + '#resultsContainer',
      created_at: session.updatedAt
        ? new Date(session.updatedAt).toISOString()
        : null,
      meta: { trip_title: String(title || '').trim() }
    };
  }

  function mergeClientItems(serverItems) {
    var items = Array.isArray(serverItems) ? serverItems.slice() : [];
    var ready = plannerReadyItem();
    if (ready) {
      items = items.filter(function (it) {
        return String(it.id).indexOf('planner_ready:') !== 0;
      });
      items.unshift(ready);
    }
    return items;
  }

  function setBadge(count) {
    var badge = document.getElementById('headerNotificationsBadge');
    if (!badge) return;
    if (count > 0) {
      badge.hidden = false;
      badge.textContent = count > 9 ? '9+' : String(count);
    } else {
      badge.hidden = true;
      badge.textContent = '';
    }
  }

  function renderList(items) {
    var listEl = document.getElementById('headerNotificationsList');
    var emptyEl = document.getElementById('headerNotificationsEmpty');
    if (!listEl) return;

    var dismissed = readDismissed();
    var visible = (items || []).filter(function (item) {
      return dismissed.indexOf(String(item.id)) === -1;
    });

    setBadge(visible.length);

    if (!visible.length) {
      listEl.innerHTML = '';
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    listEl.innerHTML = visible
      .map(function (item) {
        var loc = localizeItem(item);
        var href = item.href || '#';
        return (
          '<li class="header-notifications-item" data-id="' +
          escapeHtml(item.id) +
          '">' +
          '<a class="header-notifications-link" href="' +
          escapeHtml(href) +
          '">' +
          '<span class="header-notifications-item-title">' +
          escapeHtml(loc.title) +
          '</span>' +
          (loc.body
            ? '<span class="header-notifications-item-body">' + escapeHtml(loc.body) + '</span>'
            : '') +
          '</a>' +
          '<button type="button" class="header-notifications-dismiss" data-dismiss="' +
          escapeHtml(item.id) +
          '" aria-label="' +
          escapeHtml(t('notifications.dismiss', 'Dismiss')) +
          '">×</button>' +
          '</li>'
        );
      })
      .join('');
  }

  var cachedItems = [];

  async function refresh() {
    var wrap = document.getElementById('headerNotifications');
    var userId = localStorage.getItem('user_id');
    if (!wrap) return;
    if (!userId) {
      wrap.hidden = true;
      setBadge(0);
      return;
    }
    wrap.hidden = false;
    try {
      var res = await fetch('/api/notifications', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      cachedItems = mergeClientItems((data && data.items) || []);
      renderList(cachedItems);
    } catch (e) {
      cachedItems = mergeClientItems([]);
      renderList(cachedItems);
    }
  }

  function setOpen(open) {
    var panel = document.getElementById('headerNotificationsPanel');
    var btn = document.getElementById('headerNotificationsBtn');
    if (!panel || !btn) return;
    panel.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function bind() {
    var wrap = document.getElementById('headerNotifications');
    var btn = document.getElementById('headerNotificationsBtn');
    var panel = document.getElementById('headerNotificationsPanel');
    var listEl = document.getElementById('headerNotificationsList');
    if (!wrap || !btn || !panel || wrap.dataset.bound === '1') return;
    wrap.dataset.bound = '1';

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var willOpen = panel.hidden;
      setOpen(willOpen);
      if (willOpen) refresh();
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setOpen(false);
    });

    if (listEl) {
      listEl.addEventListener('click', function (e) {
        var dismissBtn = e.target.closest('[data-dismiss]');
        if (dismissBtn) {
          e.preventDefault();
          e.stopPropagation();
          dismissId(dismissBtn.getAttribute('data-dismiss'));
          renderList(cachedItems);
          return;
        }
        var link = e.target.closest('.header-notifications-link');
        if (link) {
          var item = link.closest('[data-id]');
          if (item) dismissId(item.getAttribute('data-id'));
          setOpen(false);
        }
      });
    }
  }

  window.HeaderNotifications = {
    init: function () {
      bind();
      refresh();
    },
    refresh: refresh
  };
})();
