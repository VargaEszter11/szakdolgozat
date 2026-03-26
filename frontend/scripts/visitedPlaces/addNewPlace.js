document.addEventListener('DOMContentLoaded', function () {
  var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
  var showErrorMsg = typeof window.showError === 'function'
    ? window.showError.bind(window)
    : function (msg, onClose) { alert(msg); if (typeof onClose === 'function') onClose(); };
  var showSuccessMsg = typeof window.showSuccess === 'function'
    ? window.showSuccess.bind(window)
    : function (msg, onClose) { alert(msg); if (typeof onClose === 'function') onClose(); };
  const form = document.getElementById('addPlaceForm');
  const cancelBtn = document.getElementById('cancelBtn');
  const visitedDateInput = document.getElementById('visitedDate');
  const ratingInput = document.getElementById('rating');
  const starBtns = document.querySelectorAll('.star-btn');

  if (visitedDateInput && typeof flatpickr === 'function') {
    var LOCALE_MAP = { hu: 'hu', de: 'de' };
    var lang = localStorage.getItem('language') || 'en';
    var fpLocale = LOCALE_MAP[lang] || 'default';

    flatpickr(visitedDateInput, {
      dateFormat: 'Y-m-d',
      maxDate: 'today',
      locale: fpLocale,
      disableMobile: true
    });
  }

  if (starBtns.length && ratingInput) {
    function setRating(value) {
      ratingInput.value = value;
      starBtns.forEach(function (btn) {
        var r = parseInt(btn.getAttribute('data-rating'), 10);
        btn.classList.toggle('selected', r <= value);
      });
    }
    starBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        setRating(parseInt(btn.getAttribute('data-rating'), 10));
      });
    });
    setRating(5);
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      window.location.href = 'visited_places.html';
    });
  }

  if (!form) return;
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      showErrorMsg('Please log in to add a place.', function () {
        window.location.href = '../loginRegister/loginPage.html';
      });
      return;
    }

    var placeName = document.getElementById('placeName').value.trim();
    var country = document.getElementById('country').value.trim();
    var visitedDate = document.getElementById('visitedDate').value;
    var description = document.getElementById('description').value.trim();
    var notes = document.getElementById('notes').value.trim();
    var rating = parseInt(document.getElementById('rating').value, 10) || 5;

    if (!placeName || !country || !visitedDate) {
      showErrorMsg('Please fill in Place Name, Country and Date Visited.');
      return;
    }

    // Combine description and notes
    var fullDescription = description;
    if (notes) {
      fullDescription = description ? description + '\n\n' + notes : notes;
    }

    // Prepare API request body
    var requestBody = {
      user_id: parseInt(userId, 10),
      place_name: placeName,
      country: country,
      date: visitedDate, // Format: YYYY-MM-DD
      rating: rating,
      description: fullDescription || null
    };

    try {
      var response = await fetch('/api/visited-places', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        var errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to add place');
      }

      await response.json().catch(function () { return null; });
      var successMessage = t('addNewPlace.savedMessage');
      if (!successMessage || successMessage === 'addNewPlace.savedMessage') {
        successMessage = 'Place added successfully!';
      }

      showSuccessMsg(successMessage, function () {
        window.location.href = 'visited_places.html';
      });
    } catch (error) {
      console.error('Error adding place:', error);
      showErrorMsg('Failed to add place: ' + error.message);
    }
  });
});
