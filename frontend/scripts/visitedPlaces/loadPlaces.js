//next: reduce redundant API calls

(function () {
  var STORAGE_KEY = 'visitedPlaces';
  var DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80';
  var lastPlaces = [];

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function formatDate(value) {
    if (!value) return '—';
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
    return d.toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
  }

  function formatVisitDates(startValue, endValue) {
    var startIso = toIsoDateInput(startValue);
    var endIso = toIsoDateInput(endValue);
    if (!startIso && !endIso) return '—';
    if (startIso && endIso && startIso !== endIso) {
      return formatDate(startIso) + ' – ' + formatDate(endIso);
    }
    return formatDate(startIso || endIso);
  }

  function toIsoDateInput(value) {
    if (!value) return '';
    var s = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
    var d = new Date(s);
    if (isNaN(d.getTime())) return '';
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function t(key, fallback) {
    if (window.i18n && window.i18n.t) {
      var v = window.i18n.t(key);
      if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
  }

  function tpl(template, vars) {
    if (!template || typeof template !== 'string') return '';
    return template.replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  var MAX_PHOTO_BYTES = 10 * 1024 * 1024;

  function responseDetail(res) {
    return res.json().catch(function () { return null; }).then(function (j) {
      if (!j) return 'HTTP ' + res.status;
      var d = j.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) {
        return d.map(function (e) {
          if (typeof e === 'string') return e;
          return (e.msg || '') + (e.loc ? ' (' + e.loc.join('.') + ')' : '');
        }).filter(Boolean).join('; ') || ('HTTP ' + res.status);
      }
      if (d != null && typeof d === 'object') return JSON.stringify(d);
      return res.statusText || ('HTTP ' + res.status);
    });
  }

  function allowedImageMime(type) {
    var x = (type || '').toLowerCase().split(';')[0].trim();
    return x === 'image/jpeg' || x === 'image/jpg' || x === 'image/png';
  }

  function allowedImageExtension(name) {
    var ext = (name || '').split('.').pop().toLowerCase();
    return ext === 'jpg' || ext === 'jpeg' || ext === 'png';
  }

  function isAllowedImage(file) {
    if (allowedImageMime(file.type)) return true;
    if (!file.type && allowedImageExtension(file.name)) return true;
    return false;
  }

  function fetchPlaceImages(placeId) {
    return fetch('/api/visited-places/' + placeId + '/images')
      .then(function (res) {
        return res.ok ? res.json() : [];
      })
      .catch(function () {
        return [];
      });
  }

  function starsHtml(placeId, rating) {
    rating = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    var html = '';
    for (var i = 1; i <= 5; i++) {
      var filled = i <= rating ? ' place-star-filled' : '';
      html += '<button type="button" class="place-star-btn' + filled + '" data-place-id="' +
        escapeHtml(placeId) + '" data-value="' + i + '" aria-label="Rate ' + i + ' out of 5 stars">' +
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' +
        '</button>';
    }
    return html;
  }

  function countryLabel(value) {
    if (window.Countries && window.Countries.displayName) {
      return window.Countries.displayName(value);
    }
    return String(value || '').trim();
  }

  function formatPlaceTitle(placeName, country) {
    if (window.Countries && window.Countries.formatPlace) {
      return window.Countries.formatPlace(placeName, country);
    }
    var city = String(placeName || '').trim();
    var c = countryLabel(country);
    if (!city) return c || 'Unnamed place';
    return c ? city + ', ' + c : city;
  }

  function normalizePlace(item, index) {
    var placeName = item.place_name || item.placeName || item.name || '';
    var country = item.country || '';
    var name = formatPlaceTitle(placeName, country);
    if (!name.trim()) name = 'Unnamed place';
    var dateValue = item.date || item.visitedDate || item.dateVisited;
    var endDateValue = item.end_date || item.endDate || item.visitedEndDate;
    var d = dateValue ? new Date(dateValue) : null;
    var endD = endDateValue ? new Date(endDateValue) : null;
    var dateSortKey = d && !isNaN(d.getTime()) ? d.getTime() : 0;
    if (endD && !isNaN(endD.getTime()) && endD.getTime() > dateSortKey) {
      dateSortKey = endD.getTime();
    }
    var rawDescription = item.description || item.notes || '';
    var rawPhotoPath = item.photo_path != null && item.photo_path !== '' ? String(item.photo_path) : null;
    return {
      id: item.id != null && item.id !== '' ? item.id : (placeName + '-' + (dateValue || '') + '-' + index),
      name: name,
      place_name: placeName,
      country: country,
      date: formatVisitDates(dateValue, endDateValue),
      dateIso: toIsoDateInput(dateValue),
      endDateIso: toIsoDateInput(endDateValue),
      dateSortKey: dateSortKey,
      rating: item.rating != null ? item.rating : 5,
      description: rawDescription,
      photo_path: rawPhotoPath,
      image: item.image || item.photo_path || DEFAULT_IMAGE,
      coordinates: item.coordinates || null,
      latitude: item.latitude != null ? item.latitude : null,
      longitude: item.longitude != null ? item.longitude : null
    };
  }

  function renderCard(place) {
    return (
      '<div class="travel-log-card visited-place-card" data-id="' + escapeHtml(place.id) + '">' +

      '<div class="log-image-wrapper">' +
      '<img src="' + escapeHtml(place.image) + '" ' +
      'alt="' + escapeHtml(place.name) + '" ' +
      'class="log-image" ' +
      'onerror="this.src=\'' + escapeHtml(DEFAULT_IMAGE) + '\';">' +
      '</div>' +

      '<div class="log-content">' +

      '<div class="log-header">' +

      '<div class="log-dest">' +
      '<svg class="icon-pin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 21s-6-5.686-6-10a6 6 0 1 1 12 0c0 4.314-6 10-6 10z"/>' +
      '<circle cx="12" cy="11" r="2"/>' +
      '</svg>' +
      '<h3 class="log-title">' + escapeHtml(place.name) + '</h3>' +
      '</div>' +

      '<div class="visited-places-card-actions">' +
      '<div class="place-stars" role="group" aria-label="Rating">' + starsHtml(place.id, place.rating) + '</div>' +
      '<button type="button" class="place-edit-btn" data-id="' + escapeHtml(place.id) + '" title="' + escapeHtml(t('visitedPlaces.editPlace', 'Edit place')) + '" aria-label="' + escapeHtml(t('visitedPlaces.editPlace', 'Edit place')) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 20h9"/>' +
      '<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/>' +
      '</svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn" data-id="' + escapeHtml(place.id) + '" title="Delete" aria-label="Delete place">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M3 6h18"/>' +
      '<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>' +
      '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>' +
      '<line x1="10" x2="10" y1="11" y2="17"/>' +
      '<line x1="14" x2="14" y1="11" y2="17"/>' +
      '</svg>' +
      '</button>' +
      '</div>' +

      '</div>' +

      '<div class="log-date">' + escapeHtml(place.date) + '</div>' +

      '<p class="log-notes">' +
      escapeHtml(place.description || 'No description.') +
      '</p>' +

      '</div>' +
      '</div>'
    );
  }

  function deletePlace(id) {
    fetch('/api/visited-places/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to delete: ' + res.status);
        loadPlaces();
      })
      .catch(function (err) {
        console.error('Error deleting place:', err);
        showError('Failed to delete place. Please try again.');
      });
  }

  function updateRating(placeId, rating) {
    fetch('/api/visited-places/' + placeId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating: rating })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to update rating: ' + res.status);
        return res.json();
      })
      .then(function () {
        loadPlaces();
      })
      .catch(function (err) {
        console.error('Error updating rating:', err);
        showError('Failed to update rating. Please try again.');
      });
  }

  function closeEditModal(overlay) {
    if (overlay && overlay.parentNode) {
      overlay.parentNode.removeChild(overlay);
    }
  }

  function openEditPlaceModal(placeId) {
    var rawId = parseInt(placeId, 10);
    if (Number.isNaN(rawId)) {
      showError(t('visitedPlaces.editInvalid', 'Cannot edit this place.'));
      return;
    }
    var place = null;
    for (var i = 0; i < lastPlaces.length; i++) {
      if (String(lastPlaces[i].id) === String(rawId)) {
        place = lastPlaces[i];
        break;
      }
    }
    if (!place) {
      showError(t('visitedPlaces.editInvalid', 'Cannot edit this place.'));
      return;
    }

    fetchPlaceImages(rawId).then(function (images) {
      var arr = Array.isArray(images) ? images : [];
      mountEditPlaceModal(place, rawId, arr);
    });
  }

  function mountEditPlaceModal(place, rawId, existingImages) {
    var uid = 'ep-' + rawId + '-' + String(Date.now()).slice(-6);
    var selectedNewFiles = [];
    var previewObjectUrls = [];
    var removedImageIds = {};
    var clearLegacyPhoto = false;

    document.querySelectorAll('.visited-place-details-overlay').forEach(function (el) {
      if (el.parentNode) el.parentNode.removeChild(el);
    });

    var overlay = document.createElement('div');
    overlay.className = 'place-details-overlay edit-place-modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', uid + '-edit-title');

    var modal = document.createElement('div');
    modal.className = 'place-details-panel edit-place-modal';

    var titleEl = document.createElement('h2');
    titleEl.className = 'place-details-title edit-place-modal-title';
    titleEl.id = uid + '-edit-title';
    titleEl.textContent = t('visitedPlaces.editTitle', 'Edit place');

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'place-details-close';
    closeBtn.setAttribute('aria-label', t('visitedPlaces.detailsClose', 'Close'));
    closeBtn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>';

    var header = document.createElement('div');
    header.className = 'place-details-header edit-place-modal-header';
    header.appendChild(titleEl);
    header.appendChild(closeBtn);

    var form = document.createElement('form');
    form.className = 'add-place-form edit-place-form edit-place-modal-form';

    var bodyWrap = document.createElement('div');
    bodyWrap.className = 'place-details-body edit-place-modal-body';

    function formGroup(labelForId, labelText, control) {
      var group = document.createElement('div');
      group.className = 'form-group';
      var lab = document.createElement('label');
      lab.className = 'form-label';
      lab.setAttribute('for', labelForId);
      lab.textContent = labelText;
      group.appendChild(lab);
      group.appendChild(control);
      return group;
    }

    function syncHasValue(el) {
      if (!el) return;
      var v = el.value != null ? String(el.value).trim() : '';
      el.classList.toggle('has-value', v.length > 0);
    }

    var nameId = uid + '-name';
    var nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'form-input';
    nameInput.id = nameId;
    nameInput.name = 'place_name';
    nameInput.required = true;
    nameInput.value = place.place_name || '';
    nameInput.autocomplete = 'off';
    syncHasValue(nameInput);
    nameInput.addEventListener('input', function () { syncHasValue(nameInput); });

    var countryId = uid + '-country';
    var countryInput = document.createElement('input');
    countryInput.type = 'text';
    countryInput.className = 'form-input';
    countryInput.id = countryId;
    countryInput.name = 'country';
    countryInput.value = place.country || '';
    countryInput.autocomplete = 'off';
    syncHasValue(countryInput);
    countryInput.addEventListener('input', function () { syncHasValue(countryInput); });
    if (window.Countries && window.Countries.mountAutocomplete) {
      window.Countries.mountAutocomplete(countryInput, {
        onChange: function () { syncHasValue(countryInput); }
      });
    }

    var dateId = uid + '-date';
    var dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.className = 'form-input';
    dateInput.id = dateId;
    dateInput.name = 'date';
    dateInput.value = place.dateIso || '';
    syncHasValue(dateInput);
    dateInput.addEventListener('change', function () { syncHasValue(dateInput); });

    var endDateId = uid + '-end-date';
    var endDateInput = document.createElement('input');
    endDateInput.type = 'date';
    endDateInput.className = 'form-input';
    endDateInput.id = endDateId;
    endDateInput.name = 'end_date';
    endDateInput.value = place.endDateIso || '';
    syncHasValue(endDateInput);
    endDateInput.addEventListener('change', function () { syncHasValue(endDateInput); });

    var descId = uid + '-desc';
    var descInput = document.createElement('textarea');
    descInput.className = 'form-input form-textarea';
    descInput.id = descId;
    descInput.name = 'description';
    descInput.rows = 4;
    descInput.value = place.description || '';
    syncHasValue(descInput);
    descInput.addEventListener('input', function () { syncHasValue(descInput); });

    bodyWrap.appendChild(formGroup(nameId, t('addNewPlace.placeName', 'Place name'), nameInput));
    bodyWrap.appendChild(formGroup(countryId, t('addNewPlace.country', 'Country'), countryInput));

    var dateRow = document.createElement('div');
    dateRow.className = 'form-row-2';
    dateRow.appendChild(formGroup(dateId, t('addNewPlace.visitedDate', 'Start date'), dateInput));
    dateRow.appendChild(formGroup(endDateId, t('addNewPlace.visitedEndDate', 'End date'), endDateInput));
    bodyWrap.appendChild(dateRow);

    bodyWrap.appendChild(formGroup(descId, t('addNewPlace.description', 'Description'), descInput));

    var photoGroup = document.createElement('div');
    photoGroup.className = 'form-group';
    var photoLabel = document.createElement('span');
    photoLabel.className = 'form-label';
    photoLabel.textContent = t('addNewPlace.photos', 'Photos');
    photoGroup.appendChild(photoLabel);

    var photoShell = document.createElement('div');
    photoShell.className = 'photo-upload-shell edit-place-photo-shell';

    var currentWrap = document.createElement('div');
    currentWrap.className = 'edit-place-current-photo';
    var currentGrid = document.createElement('div');
    currentGrid.className = 'photo-preview-grid';
    currentWrap.appendChild(currentGrid);

    var sortedImages = (existingImages || []).slice().sort(function (a, b) {
      return (a.id || 0) - (b.id || 0);
    });

    var legacyPath =
      place.photo_path != null && place.photo_path !== '' ? String(place.photo_path) : null;

    function galleryHasUrl(url) {
      if (!url) return false;
      return sortedImages.some(function (im) {
        return im.image_path === url;
      });
    }

    var orphanLegacy = !!legacyPath && !galleryHasUrl(legacyPath);

    function refreshExistingPhotoGrid() {
      currentGrid.innerHTML = '';
      sortedImages.forEach(function (im) {
        if (!im || im.id == null) return;
        if (removedImageIds[im.id]) return;
        var src = im.image_path || im.url || '';
        if (!src) return;
        var curItem = document.createElement('div');
        curItem.className = 'photo-preview-item';
        var curImg = document.createElement('img');
        curImg.src = src;
        curImg.alt = '';
        var curRm = document.createElement('button');
        curRm.type = 'button';
        curRm.className = 'photo-preview-remove';
        curRm.setAttribute('aria-label', t('visitedPlaces.removePhoto', 'Remove photo'));
        curRm.appendChild(document.createTextNode('×'));
        var idToRemove = im.id;
        curRm.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          removedImageIds[idToRemove] = true;
          refreshExistingPhotoGrid();
        });
        curItem.appendChild(curImg);
        curItem.appendChild(curRm);
        currentGrid.appendChild(curItem);
      });
      if (orphanLegacy && !clearLegacyPhoto) {
        var legItem = document.createElement('div');
        legItem.className = 'photo-preview-item';
        var legImg = document.createElement('img');
        legImg.src = legacyPath;
        legImg.alt = '';
        var legRm = document.createElement('button');
        legRm.type = 'button';
        legRm.className = 'photo-preview-remove';
        legRm.setAttribute('aria-label', t('visitedPlaces.removePhoto', 'Remove photo'));
        legRm.appendChild(document.createTextNode('×'));
        legRm.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          clearLegacyPhoto = true;
          refreshExistingPhotoGrid();
        });
        legItem.appendChild(legImg);
        legItem.appendChild(legRm);
        currentGrid.appendChild(legItem);
      }
      currentWrap.hidden = currentGrid.children.length === 0;
    }

    refreshExistingPhotoGrid();

    var photosInputId = uid + '-photos';
    var uploadLabel = document.createElement('label');
    uploadLabel.className = 'upload-zone';
    uploadLabel.setAttribute('for', photosInputId);
    uploadLabel.innerHTML =
      '<svg class="upload-icon" xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>' +
      '<polyline points="17 8 12 3 7 8"/>' +
      '<line x1="12" x2="12" y1="3" y2="15"/>' +
      '</svg>' +
      '<p class="upload-text">' + escapeHtml(t('visitedPlaces.addPhotosHint', 'Add photos (PNG or JPG, max 10 MB each). You can select several at once or add more in another step.')) + '</p>' +
      '<p class="upload-hint">' + escapeHtml(t('addNewPlace.photosHint', 'PNG or JPG, max 10 MB each')) + '</p>';

    var photosInput = document.createElement('input');
    photosInput.type = 'file';
    photosInput.id = photosInputId;
    photosInput.name = 'photos';
    photosInput.accept = 'image/png,image/jpeg,image/jpg';
    photosInput.className = 'upload-input';
    photosInput.multiple = true;
    uploadLabel.appendChild(photosInput);

    var newPreviewGrid = document.createElement('div');
    newPreviewGrid.className = 'photo-preview-grid';
    newPreviewGrid.hidden = true;

    var photoErrors = document.createElement('p');
    photoErrors.className = 'photo-upload-errors';
    photoErrors.hidden = true;
    photoErrors.setAttribute('role', 'alert');

    photoShell.appendChild(currentWrap);
    photoShell.appendChild(uploadLabel);
    photoShell.appendChild(newPreviewGrid);
    photoShell.appendChild(photoErrors);
    photoGroup.appendChild(photoShell);
    bodyWrap.appendChild(photoGroup);

    function revokePreviewUrls() {
      previewObjectUrls.forEach(function (u) {
        try {
          URL.revokeObjectURL(u);
        } catch (err) {
          /* ignore */
        }
      });
      previewObjectUrls = [];
    }

    function showPhotoErrors(lines) {
      if (!lines || !lines.length) {
        photoErrors.hidden = true;
        photoErrors.textContent = '';
        return;
      }
      photoErrors.hidden = false;
      photoErrors.textContent = lines.join('\n');
    }

    function fileKey(f) {
      return (f.name || '') + '|' + String(f.size) + '|' + String(f.lastModified);
    }

    function renderNewFilePreview() {
      revokePreviewUrls();
      newPreviewGrid.innerHTML = '';
      if (!selectedNewFiles.length) {
        newPreviewGrid.hidden = true;
        return;
      }
      newPreviewGrid.hidden = false;
      selectedNewFiles.forEach(function (file) {
        var url = URL.createObjectURL(file);
        previewObjectUrls.push(url);
        var item = document.createElement('div');
        item.className = 'photo-preview-item';
        var img = document.createElement('img');
        img.src = url;
        img.alt = file.name || '';
        var rm = document.createElement('button');
        rm.type = 'button';
        rm.className = 'photo-preview-remove';
        rm.setAttribute('aria-label', t('visitedPlaces.clearNewPhoto', 'Remove new photo'));
        rm.appendChild(document.createTextNode('×'));
        rm.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          var ix = selectedNewFiles.indexOf(file);
          if (ix >= 0) selectedNewFiles.splice(ix, 1);
          photosInput.value = '';
          renderNewFilePreview();
          showPhotoErrors([]);
        });
        item.appendChild(img);
        item.appendChild(rm);
        newPreviewGrid.appendChild(item);
      });
    }

    photosInput.addEventListener('change', function () {
      var picked = Array.from(photosInput.files || []);
      photosInput.value = '';
      var batchErrors = [];
      var prevKeys = {};
      selectedNewFiles.forEach(function (f) {
        prevKeys[fileKey(f)] = true;
      });
      picked.forEach(function (file) {
        if (!isAllowedImage(file)) {
          batchErrors.push({ file: file, reason: 'format' });
          return;
        }
        if (file.size > MAX_PHOTO_BYTES) {
          batchErrors.push({ file: file, reason: 'size' });
          return;
        }
        if (prevKeys[fileKey(file)]) return;
        prevKeys[fileKey(file)] = true;
        selectedNewFiles.push(file);
      });
      var errLines = batchErrors.map(function (err) {
        var name = err.file.name || 'file';
        var msg;
        if (err.reason === 'size') {
          msg = tpl(t('addNewPlace.photoTooLarge'), { name: name });
          if (msg.indexOf('addNewPlace.') === 0 || msg.indexOf('{{name}}') >= 0) {
            msg = 'File too large (max 10 MB): ' + name;
          }
        } else {
          msg = tpl(t('addNewPlace.photoInvalidType'), { name: name });
          if (msg.indexOf('addNewPlace.') === 0 || msg.indexOf('{{name}}') >= 0) {
            msg = 'Only PNG or JPEG files are allowed: ' + name;
          }
        }
        return msg;
      });
      showPhotoErrors(errLines);
      renderNewFilePreview();
    });

    var footer = document.createElement('div');
    footer.className = 'edit-place-modal-footer';

    var actions = document.createElement('div');
    actions.className = 'form-actions edit-place-modal-actions';

    var saveBtn = document.createElement('button');
    saveBtn.type = 'submit';
    saveBtn.className = 'btn-add';
    saveBtn.textContent = t('visitedPlaces.saveChanges', 'Save changes');

    var cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'btn-cancel';
    cancelBtn.textContent = t('settings.cancel', 'Cancel');

    actions.appendChild(saveBtn);
    actions.appendChild(cancelBtn);
    footer.appendChild(actions);

    form.appendChild(bodyWrap);
    form.appendChild(footer);

    modal.appendChild(header);
    modal.appendChild(form);
    overlay.appendChild(modal);

    function cleanupOverlay() {
      revokePreviewUrls();
      closeEditModal(overlay);
    }

    closeBtn.addEventListener('click', function () {
      cleanupOverlay();
    });

    cancelBtn.addEventListener('click', function () {
      cleanupOverlay();
    });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) cleanupOverlay();
    });

    function applyPhotoChangesAfterPut() {
      var chain = Promise.resolve();
      var idsToDelete = Object.keys(removedImageIds)
        .map(function (k) {
          return parseInt(k, 10);
        })
        .filter(function (id) {
          return !Number.isNaN(id);
        });
      idsToDelete.forEach(function (imageId) {
        chain = chain.then(function () {
          return fetch('/api/images/' + imageId, { method: 'DELETE' }).then(function (res) {
            if (!res.ok && res.status !== 404) {
              return responseDetail(res).then(function (msg) {
                throw new Error(msg || 'Failed to remove a photo');
              });
            }
          });
        });
      });
      selectedNewFiles.forEach(function (file) {
        chain = chain.then(function () {
          var fd = new FormData();
          fd.append('file', file);
          return fetch('/api/visited-places/' + rawId + '/images/upload', {
            method: 'POST',
            body: fd
          }).then(function (res) {
            if (!res.ok) {
              return responseDetail(res).then(function (msg) {
                throw new Error(msg || 'Photo upload failed');
              });
            }
          });
        });
      });
      return chain;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var pn = (nameInput.value || '').trim();
      if (!pn) {
        showError(t('visitedPlaces.placeNameRequired', 'Please enter a place name.'));
        return;
      }
      var startDate = (dateInput.value || '').trim();
      var endDate = (endDateInput.value || '').trim();
      if (startDate && endDate && endDate < startDate) {
        showError(t('visitedPlaces.endDateBeforeStart', 'End date must be on or after the start date.'));
        return;
      }
      var body = {
        place_name: pn,
        country: (window.Countries && window.Countries.getCode(countryInput)) ||
          (countryInput.value || '').trim() || null,
        date: startDate || null,
        end_date: endDate || null,
        description: (descInput.value || '').trim() || null
      };
      if (clearLegacyPhoto) {
        body.photo_path = null;
      }
      saveBtn.disabled = true;
      cancelBtn.disabled = true;
      saveBtn.textContent = t('visitedPlaces.saving', 'Saving…');
      fetch('/api/visited-places/' + rawId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
        .then(function (res) {
          if (!res.ok) {
            return responseDetail(res).then(function (msg) {
              throw new Error(msg || ('HTTP ' + res.status));
            });
          }
        })
        .then(function () {
          return applyPhotoChangesAfterPut();
        })
        .then(function () {
          cleanupOverlay();
          loadPlaces();
        })
        .catch(function (err) {
          console.error('Error updating place:', err);
          showError(
            (err && err.message) ||
              t('visitedPlaces.editFailed', 'Could not save changes. Please try again.')
          );
          saveBtn.disabled = false;
          cancelBtn.disabled = false;
          saveBtn.textContent = t('visitedPlaces.saveChanges', 'Save changes');
        });
    });

    document.body.appendChild(overlay);
    nameInput.focus();
    nameInput.select();
  }

  function formatRatingDisplay(rating) {
    if (rating == null || rating === '') return '\u2014';
    var n = Math.min(5, Math.max(0, parseInt(rating, 10) || 0));
    return String(n) + '/5';
  }

  function collectPhotoUrls(place, images) {
    var urls = [];
    var seen = {};
    function add(u) {
      if (!u || typeof u !== 'string') return;
      if (seen[u]) return;
      seen[u] = true;
      urls.push(u);
    }
    (images || []).forEach(function (im) {
      add(im.image_path);
    });
    if (place && place.photo_path) add(place.photo_path);
    return urls;
  }

  function showPlaceDetails(placeId) {
    var rawId = parseInt(placeId, 10);
    if (Number.isNaN(rawId)) return;

    document.querySelectorAll('.visited-place-details-overlay').forEach(function (el) {
      if (el.parentNode) el.parentNode.removeChild(el);
    });

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

        if (window.i18n && typeof window.i18n.applyToPage === 'function') {
          window.i18n.applyToPage(modal);
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

        if (countryEl) countryEl.textContent = countryLabel(country) || '\u2014';
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
            descEl.textContent = t('visitedPlaces.detailsNoDescription', 'No notes for this place.');
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
        console.error('Error loading place details:', err);
        showError(t('visitedPlaces.detailsLoadFailed', 'Could not load place details.'));
      });
  }

  function bindPlaceCardActions() {
    var container = document.getElementById('placeCards');
    if (!container || container.dataset.placeActionsBound === '1') return;
    container.dataset.placeActionsBound = '1';
    container.addEventListener('click', function (e) {
      var editBtn = e.target.closest('.place-edit-btn');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        var editId = editBtn.getAttribute('data-id');
        openEditPlaceModal(editId);
        return;
      }
      var delBtn = e.target.closest('.place-delete-btn');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        var raw = delBtn.getAttribute('data-id');
        var delId = parseInt(raw, 10);
        if (raw == null || String(raw).trim() === '' || Number.isNaN(delId)) {
          showError('Cannot delete this place.');
          return;
        }
        showConfirm('Are you sure you want to delete this place?', function () {
          deletePlace(delId);
        });
        return;
      }
      var starBtn = e.target.closest('.place-star-btn');
      if (starBtn) {
        e.preventDefault();
        var pid = parseInt(starBtn.getAttribute('data-place-id'), 10);
        var val = parseInt(starBtn.getAttribute('data-value'), 10);
        if (isNaN(pid) || isNaN(val)) return;
        updateRating(pid, val);
        return;
      }
      var card = e.target.closest('.visited-place-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) showPlaceDetails(cid);
      }
    });
  }

  function sortByVisitDate(places) {
    return places.slice().sort(function (a, b) {
      return (b.dateSortKey || 0) - (a.dateSortKey || 0);
    });
  }

  function render(places) {
    var container = document.getElementById('placeCards');
    var countEl = document.getElementById('placeCount');
    if (!container) return;

    var sorted = sortByVisitDate(places);
    lastPlaces = sorted;
    if (countEl) countEl.textContent = sorted.length;

    var tEmpty = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
    var emptyHtml = (tEmpty('visitedPlaces.emptyText') || 'No places yet.') + ' <a href="add_new_place.html">' + (tEmpty('visitedPlaces.addFirstPlace') || 'Add your first place') + '</a>.';
    container.innerHTML = sorted.length
      ? sorted.map(renderCard).join('')
      : '<p class="place-cards-empty">' + emptyHtml + '</p>';
  }

  function loadPlaces() {
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.error('No user_id found. Please log in.');
      var container = document.getElementById('placeCards');
      if (container) {
        container.innerHTML = '<p class="place-cards-empty">Please log in to view your places. <a href="../loginRegister/loginPage.html">Log in here</a>.</p>';
      }
      return;
    }

    var apiUrl = '/api/users/' + userId + '/visited-places';
    fetch(apiUrl)
      .then(function (res) {
        if (!res.ok) {
          if (res.status === 404) {
            render([]);
            return null;
          }
          throw new Error('API request failed: ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (data === null) return;
        var list = Array.isArray(data) ? data : [];
        var places = list.map(function (item, index) {
          return normalizePlace(item, index);
        });
        render(places);
      })
      .catch(function (err) {
        console.error('Failed to load visited places from API:', err);
        var container = document.getElementById('placeCards');
        if (container) {
          container.innerHTML = '<p class="place-cards-empty">Failed to load places. Please try again later.</p>';
        }
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindPlaceCardActions();
    loadPlaces();
  });
})();
