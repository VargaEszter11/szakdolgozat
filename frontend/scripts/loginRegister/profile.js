function tProfile(key, fallback) {
  return window.i18n && window.i18n.t ? window.i18n.t(key) : fallback;
}

function notifyHeaderAvatar() {
  if (window.appShell && typeof window.appShell.refreshHeaderProfileAvatar === 'function') {
    window.appShell.refreshHeaderProfileAvatar();
  }
}

function applyStoredGoogleAvatar() {
  var userId = localStorage.getItem('user_id');
  var username = localStorage.getItem('username');
  var url = localStorage.getItem('google_avatar_url');
  var wrap = document.getElementById('profileAvatar');
  var img = document.getElementById('profileAvatarImg');
  if (!wrap || !img) return;

  if (!userId || !username || !url) {
    wrap.classList.remove('profile-avatar--photo');
    img.removeAttribute('src');
    img.alt = '';
    notifyHeaderAvatar();
    return;
  }

  img.onerror = function () {
    wrap.classList.remove('profile-avatar--photo');
    img.removeAttribute('src');
    notifyHeaderAvatar();
  };
  img.onload = function () {
    wrap.classList.add('profile-avatar--photo');
    notifyHeaderAvatar();
  };

  if (img.getAttribute('src') === url && img.complete && img.naturalHeight > 0) {
    wrap.classList.add('profile-avatar--photo');
    notifyHeaderAvatar();
    return;
  }

  img.alt = '';
  img.src = url;
  if (img.complete && img.naturalHeight > 0) {
    wrap.classList.add('profile-avatar--photo');
    notifyHeaderAvatar();
  }
}

function setProfileAvatar(name) {
  var wrap = document.getElementById('profileAvatar');
  if (!wrap) return;
  var span = wrap.querySelector('.profile-avatar-initials');
  if (span) {
    span.textContent = typeof window.displayNameInitials === 'function'
      ? window.displayNameInitials(name)
      : '?';
  }
  var label = name && String(name).trim()
    ? tProfile('profile.avatarLabel', 'Avatar for {{name}}').replace('{{name}}', String(name).trim())
    : tProfile('profile.avatarLabelEmpty', 'Avatar');
  wrap.setAttribute('aria-label', label);
  applyStoredGoogleAvatar();
}

document.addEventListener('DOMContentLoaded', async function () {
  const userId = localStorage.getItem('user_id');
  const username = localStorage.getItem('username');

  const profileName = document.querySelector('.profile-name');
  const profileEmail = document.querySelector('.profile-email');
  const accountSection = document.querySelector('.profile-actions');

  if (!userId || !username) {
    if (window.markAppReady) window.markAppReady();
    return;
  }

  try {
    if (profileName) {
      profileName.removeAttribute('data-i18n');
      profileName.textContent = username;
    }
    setProfileAvatar(username);

    const userResponse = await fetch(`/api/users/${userId}`);
    if (userResponse.ok) {
      const userData = await userResponse.json();
      if (profileEmail) {
        profileEmail.removeAttribute('data-i18n');
        profileEmail.textContent = userData.email || tProfile('profile.noEmail', 'No email');
      }
      if (userData.username) {
        if (profileName) {
          profileName.removeAttribute('data-i18n');
          profileName.textContent = userData.username;
        }
        setProfileAvatar(userData.username);
      }
    } else if (profileEmail) {
      profileEmail.removeAttribute('data-i18n');
      profileEmail.textContent = tProfile('profile.errorLoad', 'Error loading profile');
    }

    if (accountSection) {
      accountSection.innerHTML = `
        <h2 class="main-page-panel-title" data-i18n="profile.account">Account</h2>
        <p class="muted" data-i18n="profile.manageYourAccountAndPreferences">Manage your account and preferences.</p>
        <div class="profile-account-buttons">
          <a href="/settings/profile" class="btn-add btn-add-outline profile-btn-edit">
            <svg class="profile-action-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            <span data-i18n="profile.editProfile">Edit Profile</span>
          </a>
          <button type="button" id="logoutBtn" class="btn-add btn-add-danger">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="profile-action-icon" aria-hidden="true">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          <span data-i18n="profile.logout">Logout</span>
        </button>
        </div>
      `;

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(accountSection);
      }

      const logoutBtn = document.getElementById('logoutBtn');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', function () {
          var confirmMsg = (window.i18n && window.i18n.t)
            ? window.i18n.t('profile.logoutConfirm')
            : 'Are you sure you want to logout?';
          showConfirm(confirmMsg, function () {
            if (window.clearAuthSession) window.clearAuthSession();
            else {
              localStorage.removeItem('user_id');
              localStorage.removeItem('username');
              localStorage.removeItem('google_avatar_url');
              localStorage.removeItem('access_token');
            }
            window.location.href = '/login';
          });
        });
      }
    }
  } catch (error) {
    if (profileEmail) {
      profileEmail.removeAttribute('data-i18n');
      profileEmail.textContent = tProfile('profile.errorLoad', 'Error loading profile');
    }
  }
  if (window.markAppReady) window.markAppReady();
});
