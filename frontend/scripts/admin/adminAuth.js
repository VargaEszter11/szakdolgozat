(function (root) {
  var SESSION_KEY = 'admin_secret';

  function adminT(key, fallback) {
    return root.i18n && typeof root.i18n.t === 'function' ? root.i18n.t(key) : fallback;
  }

  function getStoredSecret() {
    return sessionStorage.getItem(SESSION_KEY) || '';
  }

  function setStoredSecret(secret) {
    sessionStorage.setItem(SESSION_KEY, secret);
  }

  function clearStoredSecret() {
    sessionStorage.removeItem(SESSION_KEY);
  }

  async function verifySecret(secret) {
    var response = await fetch('/api/admin/ping', {
      headers: { 'X-Admin-Secret': secret }
    });
    return response.ok;
  }

  function revealPage() {
    if (root.markAppReady) root.markAppReady();
  }

  function createSetStatus(statusEl) {
    return function setStatus(text, type) {
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
    };
  }

  /**
   * Wire unlock form + restore session.
   * @param {object} opts
   * @param {HTMLElement} opts.loginCard
   * @param {HTMLElement} opts.panel
   * @param {HTMLFormElement} opts.loginForm
   * @param {HTMLInputElement} opts.secretInput
   * @param {HTMLButtonElement} opts.loginSubmit
   * @param {HTMLElement} [opts.statusEl]
   * @param {function(): void} [opts.onUnlocked]
   * @returns {{ setStatus: function }}
   */
  function bindAdminAuth(opts) {
    var loginCard = opts.loginCard;
    var panel = opts.panel;
    var loginForm = opts.loginForm;
    var secretInput = opts.secretInput;
    var loginSubmit = opts.loginSubmit;
    var setStatus = createSetStatus(opts.statusEl || null);
    var onUnlocked = typeof opts.onUnlocked === 'function' ? opts.onUnlocked : null;

    function showPanel() {
      loginCard.classList.add('hidden');
      panel.classList.remove('hidden');
      setStatus(null);
      if (onUnlocked) onUnlocked();
    }

    function showLogin() {
      panel.classList.add('hidden');
      loginCard.classList.remove('hidden');
    }

    async function init() {
      try {
        var stored = getStoredSecret();
        if (!stored) {
          showLogin();
          return;
        }
        var ok = await verifySecret(stored);
        if (ok) {
          showPanel();
        } else {
          clearStoredSecret();
          showLogin();
        }
      } finally {
        revealPage();
      }
    }

    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      loginSubmit.disabled = true;
      setStatus(null);
      try {
        var secret = secretInput.value.trim();
        var ok = await verifySecret(secret);
        if (ok) {
          setStoredSecret(secret);
          secretInput.value = '';
          showPanel();
        } else {
          setStatus(adminT('admin.invalidSecret', 'Invalid admin secret.'), 'error');
        }
      } catch (err) {
        setStatus(adminT('admin.serverError', 'Server error. Please try again later.'), 'error');
      } finally {
        loginSubmit.disabled = false;
      }
    });

    init();
    return { setStatus: setStatus };
  }

  root.AdminAuth = {
    SESSION_KEY: SESSION_KEY,
    adminT: adminT,
    getStoredSecret: getStoredSecret,
    setStoredSecret: setStoredSecret,
    clearStoredSecret: clearStoredSecret,
    verifySecret: verifySecret,
    createSetStatus: createSetStatus,
    bindAdminAuth: bindAdminAuth,
    revealPage: revealPage
  };
})(typeof window !== 'undefined' ? window : globalThis);
