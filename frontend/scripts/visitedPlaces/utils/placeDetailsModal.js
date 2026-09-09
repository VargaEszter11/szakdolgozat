(function (global) {
  'use strict';

  var F = global.PlaceFormatHelpers;
  var t = F.t;
  var formatVisitDates = F.formatVisitDates;
  var formatRatingDisplay = F.formatRatingDisplay;
  var countryLabel = F.countryLabel;
  var formatPlaceTitle = F.formatPlaceTitle;
  var collectPhotoUrls = F.collectPhotoUrls;

  // Clone template, fill place/details/photos, wire close handlers
  function show(placeId) {
    var rawId = parseInt(placeId, 10);
    if (Number.isNaN(rawId)) return;

    global.PlacePopups.closeAll();

    Promise.all([
      fetch('/api/visited-places/' + rawId).then(function (res) {
        if (!res.ok) throw new Error('place');
        return res.json();
      }),
      fetch('/api/visited-places/' + rawId + '/images').then(function (res) {
        return res.ok ? res.json() : [];
      })
    ])
      .then(function (results) {
        var place = results[0];
        var images = Array.isArray(results[1]) ? results[1] : [];
        var template = document.getElementById('placeDetailsModalTemplate');
        if (!template || !template.content) return;
        var clone = document.importNode(template.content, true);
        var modal = clone.querySelector('.visited-place-details-overlay');
        if (!modal) return;
        document.body.appendChild(clone);

        if (global.i18n && typeof global.i18n.applyToPage === 'function') {
          global.i18n.applyToPage(modal);
        }

        var titleEl = modal.querySelector('#placeDetailsTitle');
        var countryRow = modal.querySelector('#placeDetailsCountryRow');
        var countryEl = modal.querySelector('#placeDetailsCountry');
        var dateEl = modal.querySelector('#placeDetailsDate');
        var ratingEl = modal.querySelector('#placeDetailsRating');
        var ratingRow = modal.querySelector('#placeDetailsRatingRow');
        var coordsRow = modal.querySelector('#placeDetailsCoordsRow');
        var mapLink = modal.querySelector('#placeDetailsMapLink');
        var photoGrid = modal.querySelector('#placeDetailsPhotoGrid');
        var noPhotosEl = modal.querySelector('#placeDetailsNoPhotos');
        var descEl = modal.querySelector('#placeDetailsDescription');

        var placeName = place.place_name || '';
        var country = place.country || '';
        if (titleEl) titleEl.textContent = formatPlaceTitle(placeName, country);

        if (countryEl) countryEl.textContent = countryLabel(country) || '—';
        if (countryRow) countryRow.style.display = country ? '' : 'none';

        var dateVal = place.date || place.visitedDate;
        var endDateVal = place.end_date || place.endDate;
        if (dateEl) dateEl.textContent = formatVisitDates(dateVal, endDateVal);

        if (ratingRow) ratingRow.style.display = place.rating != null ? '' : 'none';
        if (ratingEl) ratingEl.textContent = formatRatingDisplay(place.rating);

        var lat = place.latitude;
        var lon = place.longitude;
        if (coordsRow && mapLink && lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
          coordsRow.classList.remove('hidden');
          var osm = 'https://www.openstreetmap.org/?mlat=' + encodeURIComponent(lat) + '&mlon=' + encodeURIComponent(lon) + '#map=14/' + lat + '/' + lon;
          mapLink.href = osm;
          mapLink.textContent = t('visitedPlaces.detailsMapLink', 'Open map');
        } else if (coordsRow) {
          coordsRow.classList.add('hidden');
        }

        var photoUrls = collectPhotoUrls(place, images);
        if (photoGrid) {
          photoGrid.innerHTML = '';
          photoUrls.forEach(function (url) {
            var cell = document.createElement('a');
            cell.className = 'place-details-photo-item';
            cell.href = url;
            cell.target = '_blank';
            cell.rel = 'noopener noreferrer';
            var img = document.createElement('img');
            img.src = url;
            img.alt = '';
            img.loading = 'lazy';
            img.onerror = function () {
              this.style.display = 'none';
            };
            cell.appendChild(img);
            photoGrid.appendChild(cell);
          });
        }
        if (noPhotosEl) {
          if (photoUrls.length === 0) {
            noPhotosEl.classList.remove('hidden');
          } else {
            noPhotosEl.classList.add('hidden');
          }
        }

        if (descEl) {
          var desc = place.description || '';
          descEl.classList.remove('place-details-description--empty');
          if (desc.trim()) {
            descEl.textContent = desc;
          } else {
            descEl.textContent = t('visitedPlaces.detailsNoDescription', 'No description for this place.');
            descEl.classList.add('place-details-description--empty');
          }
        }

        var closeBtn = modal.querySelector('[data-place-details-close]');
        var modalBox = modal.querySelector('#placeDetailsModalBox');
        if (closeBtn) {
          closeBtn.setAttribute('aria-label', t('visitedPlaces.detailsClose', 'Close'));
        }

        function removeModal() {
          document.removeEventListener('keydown', handleEsc);
          if (modal.parentNode) modal.parentNode.removeChild(modal);
        }

        if (closeBtn) closeBtn.addEventListener('click', removeModal);
        modal.addEventListener('click', function (e) {
          if (e.target === modal) removeModal();
        });
        if (modalBox) {
          modalBox.addEventListener('click', function (e) {
            e.stopPropagation();
          });
        }
        function handleEsc(e) {
          if (e.key === 'Escape') removeModal();
        }
        document.addEventListener('keydown', handleEsc);
      })
      .catch(function (err) {
        showError(t('visitedPlaces.detailsLoadFailed', 'Could not load place details.'));
      });
  }

  global.PlaceDetailsModal = {
    show: show
  };
})(window);
