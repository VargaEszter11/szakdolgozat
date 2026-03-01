document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('addPlaceForm');
  const cancelBtn = document.getElementById('cancelBtn');
  const ratingInput = document.getElementById('rating');
  const starBtns = document.querySelectorAll('.star-btn');

  if (starBtns.length && ratingInput) {
    function setRating(value) {
      ratingInput.value = value;
      starBtns.forEach(function (btn) {
        var r = parseInt(btn.getAttribute('data-rating'), 10);
        btn.classList.toggle('active', r <= value);
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
      showError('Please log in to add a place.', function () {
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
      showError('Please fill in Place Name, Country and Date Visited.');
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

      var data = await response.json();
      showSuccess('Place added successfully!', function () {
        window.location.href = 'visited_places.html';
      });
    } catch (error) {
      console.error('Error adding place:', error);
      showError('Failed to add place: ' + error.message);
    }
  });
});
