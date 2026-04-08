document.addEventListener('DOMContentLoaded', async function () {
  const userId = localStorage.getItem('user_id');
  const username = localStorage.getItem('username');

  const profileName = document.querySelector('.profile-name');
  const profileEmail = document.querySelector('.profile-email');
  const placesVisitedEl = document.querySelector('.profile-stat-value');
  const tripsPlannedEl = document.querySelectorAll('.profile-stat-value')[1];
  const accountSection = document.querySelector('.profile-actions');

  if (!userId || !username) {
    if (profileName) profileName.textContent = 'Guest';
    if (profileEmail) profileEmail.textContent = 'Please log in to view your profile';

    if (accountSection) {
      accountSection.innerHTML = `
        <h2 class="section-title" data-i18n="profile.account">Account</h2>
        <p class="muted" data-i18n="profile.notLoggedIn">You are not logged in.</p>
        <div class="profile-actions-row">
          <a href="loginPage.html" class="btn-add" data-i18n="profile.login">Login</a>
          <a href="registerPage.html" class="btn-add btn-add-outline" data-i18n="profile.register">Register</a>
        </div>
      `;
    }
    return;
  }

  try {
    if (profileName) profileName.textContent = username;

    const userResponse = await fetch(`/api/users/${userId}`);
    if (userResponse.ok) {
      const userData = await userResponse.json();
      if (profileEmail) profileEmail.textContent = userData.email || 'No email';
    }

    const placesResponse = await fetch(`/api/users/${userId}/visited-places`);
    if (placesResponse.ok) {
      const places = await placesResponse.json();
      if (placesVisitedEl) {
        placesVisitedEl.textContent = Array.isArray(places) ? places.length : 0;
      }
    }

    const tripsResponse = await fetch(`/api/users/${userId}/planned-trips`);
    if (tripsResponse.ok) {
      const trips = await tripsResponse.json();
      if (tripsPlannedEl) {
        tripsPlannedEl.textContent = Array.isArray(trips) ? trips.length : 0;
      }
    }

    if (accountSection) {
      accountSection.innerHTML = `
        <h2 class="section-title" data-i18n="profile.account">Account</h2>
        <p class="muted" data-i18n="profile.manageYourAccountAndPreferences">Manage your account and preferences.</p>
        <button type="button" id="logoutBtn" class="btn-add btn-add-danger">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          Logout
        </button>
      `;

      const logoutBtn = document.getElementById('logoutBtn');
      if (logoutBtn) {
        logoutBtn.addEventListener('click', function () {
          showConfirm('Are you sure you want to logout?', function () {
            localStorage.removeItem('user_id');
            localStorage.removeItem('username');
            showSuccess('Logged out successfully', function () {
              window.location.href = 'loginPage.html';
            });
          });
        });
      }
    }

  } catch (error) {
    console.error('Error loading profile data:', error);
    if (profileEmail) {
      profileEmail.textContent = 'Error loading profile';
    }
  }
});
