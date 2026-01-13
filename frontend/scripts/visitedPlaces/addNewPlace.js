document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('addPlaceForm');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const place = {
      placeName: document.getElementById('placeName').value.trim(),
      country: document.getElementById('country').value.trim(),
      visitedDate: document.getElementById('visitedDate').value,
      description: document.getElementById('description').value.trim()
    };
    if (!place.placeName || !place.country || !place.visitedDate) {
      alert('Please fill in Place Name, Country and Date Visited.');
      return;
    }
    const key = 'visitedPlaces';
    const list = JSON.parse(localStorage.getItem(key) || '[]');
    list.push(place);
    localStorage.setItem(key, JSON.stringify(list));
    window.location.href = 'visited_places.html';
  });
});
