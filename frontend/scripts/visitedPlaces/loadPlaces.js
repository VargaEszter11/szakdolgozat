function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, function (m) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[m]);
  });
}

document.addEventListener('DOMContentLoaded', function () {
  const tbody = document.querySelector('#visitedPlacesTable tbody');
  if (!tbody) return;
  const jsonUrl = '../../../dummy_places/places.json';

  function render(list) {
    tbody.innerHTML = '';
    if (!list || list.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 4;
      td.textContent = 'No places yet.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    list.forEach(function (item) {
      const tr = document.createElement('tr');
      const placeName = item.placeName || item.name || '';
      const country = item.country || '';
      const visitedDate = item.visitedDate || item.dateVisited || '';
      const description = item.description || '';
      tr.innerHTML = '<td>' + escapeHtml(placeName) + '</td>' +
                     '<td>' + escapeHtml(country) + '</td>' +
                     '<td>' + escapeHtml(visitedDate) + '</td>' +
                     '<td>' + escapeHtml(description) + '</td>';
      tbody.appendChild(tr);
    });
  }

  fetch(jsonUrl)
    .then(function (res) {
      if (!res.ok) throw new Error('Network response was not ok');
      return res.json();
    })
    .then(function (data) {
      const list = data && data.places ? data.places : [];
      render(list);
    })
    .catch(function (err) {
      console.warn('Could not load places.json, falling back to localStorage:', err);
      const list = JSON.parse(localStorage.getItem('visitedPlaces') || '[]');
      render(list);
    });
});
