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
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var place = {
      placeName: document.getElementById('placeName').value.trim(),
      country: document.getElementById('country').value.trim(),
      visitedDate: document.getElementById('visitedDate').value,
      description: document.getElementById('description').value.trim(),
      notes: document.getElementById('notes').value.trim(),
      rating: parseInt(document.getElementById('rating').value, 10) || 5
    };
    if (!place.placeName || !place.country || !place.visitedDate) {
      alert('Please fill in Place Name, Country and Date Visited.');
      return;
    }
    var key = 'visitedPlaces';
    var list = JSON.parse(localStorage.getItem(key) || '[]');
    list.push(place);
    localStorage.setItem(key, JSON.stringify(list));
    window.location.href = 'visited_places.html';
  });
});
