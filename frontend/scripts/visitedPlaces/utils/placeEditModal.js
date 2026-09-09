(function (global) {
  'use strict';

  var F = global.PlaceFormatHelpers;
  var t = F.t;
  var tpl = F.tpl;
  var escapeHtml = F.escapeHtml;
  var responseDetail = F.responseDetail;
  var fetchPlaceImages = F.fetchPlaceImages;

  var deps = {
    getPlaces: function () { return []; },
    refreshList: function () { return Promise.resolve(); }
  };

  function init(options) {
    options = options || {};
    if (typeof options.getPlaces === 'function') deps.getPlaces = options.getPlaces;
    if (typeof options.refreshList === 'function') deps.refreshList = options.refreshList;
  }

  function closeEditModal(overlay) {
    global.PlacePopups.closeOverlay(overlay);
  }

  function deletePlace(id) {
    fetch('/api/visited-places/' + id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to delete: ' + res.status);
        deps.refreshList();
      })
      .catch(function (err) {
        showError(t('visitedPlaces.deleteFailed', 'Failed to delete place. Please try again.'));
      });
  }

  // Load images, build edit dialog
  function openEditPlaceModal(placeId) {
    var rawId = parseInt(placeId, 10);
    if (Number.isNaN(rawId)) {
      showError(t('visitedPlaces.editInvalid', 'Cannot edit this place.'));
      return;
    }
    var places = deps.getPlaces() || [];
    var place = null;
    for (var i = 0; i < places.length; i++) {
      if (String(places[i].id) === String(rawId)) {
        place = places[i];
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

  // Build edit form
  function mountEditPlaceModal(place, rawId, existingImages) {
    var uid = 'ep-' + rawId + '-' + String(Date.now()).slice(-6);
    var removedImageIds = {};
    var clearLegacyPhoto = false;

    global.PlacePopups.closeAll();

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

    var dateId = uid + '-date';
    var dateInput = document.createElement('input');
    dateInput.type = typeof flatpickr === 'function' ? 'text' : 'date';
    dateInput.className = 'form-input';
    dateInput.id = dateId;
    dateInput.name = 'date';
    dateInput.value = place.dateIso || '';
    dateInput.autocomplete = 'off';
    syncHasValue(dateInput);
    dateInput.addEventListener('change', function () { syncHasValue(dateInput); });

    var endDateId = uid + '-end-date';
    var endDateInput = document.createElement('input');
    endDateInput.type = typeof flatpickr === 'function' ? 'text' : 'date';
    endDateInput.className = 'form-input';
    endDateInput.id = endDateId;
    endDateInput.name = 'end_date';
    endDateInput.value = place.endDateIso || '';
    endDateInput.autocomplete = 'off';
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
    // Autocomplete wraps the input via parentNode — must run after the input is in the DOM.
    if (global.Countries && global.Countries.mountAutocomplete) {
      global.Countries.mountAutocomplete(countryInput, {
        onChange: function () { syncHasValue(countryInput); }
      });
    }

    var dateRow = document.createElement('div');
    dateRow.className = 'form-row-2';
    dateRow.appendChild(formGroup(dateId, t('addNewPlace.visitedDate', 'Start date'), dateInput));
    dateRow.appendChild(formGroup(endDateId, t('addNewPlace.visitedEndDate', 'End date'), endDateInput));
    bodyWrap.appendChild(dateRow);

    // Linked flatpickr
    var startPicker = null;
    var endPicker = null;
    var lastAutoEnd = '';
    if (typeof flatpickr === 'function') {
      var FP_LOCALE = { hu: 'hu', de: 'de' };
      var fpLang = localStorage.getItem('language') || 'en';
      var fpLocale = FP_LOCALE[fpLang] || 'default';
      var fpOpts = {
        dateFormat: 'Y-m-d',
        maxDate: 'today',
        locale: fpLocale,
        disableMobile: true
      };
      endPicker = flatpickr(endDateInput, Object.assign({}, fpOpts, {
        onOpen: function (selectedDates, dateStr, instance) {
          var jumpTo = dateStr || (instance.input && instance.input.value) || '';
          if (jumpTo) instance.jumpToDate(jumpTo, false);
        },
        onChange: function () {
          syncHasValue(endDateInput);
        }
      }));
      startPicker = flatpickr(dateInput, Object.assign({}, fpOpts, {
        onOpen: function (selectedDates, dateStr, instance) {
          var jumpTo = dateStr || (instance.input && instance.input.value) || '';
          if (jumpTo) instance.jumpToDate(jumpTo, false);
        },
        onChange: function (selectedDates, dateStr) {
          syncHasValue(dateInput);
          if (!dateStr || !endPicker) return;
          endPicker.set('minDate', dateStr);
          var endVal = endPicker.input.value || '';
          if (!endVal || endVal < dateStr || endVal === lastAutoEnd) {
            endPicker.setDate(dateStr, true);
            lastAutoEnd = dateStr;
          }
          endPicker.jumpToDate(endPicker.input.value || dateStr, true);
          syncHasValue(endDateInput);
        }
      }));
      if (place.dateIso) {
        startPicker.setDate(place.dateIso, false);
        endPicker.set('minDate', place.dateIso);
      }
      if (place.endDateIso) {
        endPicker.setDate(place.endDateIso, false);
        if (place.dateIso && place.endDateIso === place.dateIso) {
          lastAutoEnd = place.dateIso;
        }
      }
      syncHasValue(dateInput);
      syncHasValue(endDateInput);
      overlay._startPicker = startPicker;
      overlay._endPicker = endPicker;
    }

    // Star rating
    var ratingGroup = document.createElement('div');
    ratingGroup.className = 'form-group';
    var ratingLabel = document.createElement('span');
    ratingLabel.className = 'form-label';
    ratingLabel.textContent = t('addNewPlace.rating', 'Rating');
    ratingGroup.appendChild(ratingLabel);

    var ratingHidden = document.createElement('input');
    ratingHidden.type = 'hidden';
    ratingHidden.id = uid + '-rating';
    ratingHidden.name = 'rating';
    var initialRating = parseInt(place.rating, 10);
    if (!Number.isFinite(initialRating) || initialRating < 1) initialRating = 0;
    if (initialRating > 5) initialRating = 5;
    ratingHidden.value = initialRating > 0 ? String(initialRating) : '';

    var starRating = document.createElement('div');
    starRating.className = 'star-rating';
    starRating.setAttribute('role', 'group');
    starRating.setAttribute('aria-label', t('addNewPlace.rating', 'Rating'));
    var starPoly =
      '12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2';
    for (var si = 1; si <= 5; si++) {
      var starBtn = document.createElement('button');
      starBtn.type = 'button';
      starBtn.className = 'star-btn';
      starBtn.setAttribute('data-rating', String(si));
      starBtn.setAttribute(
        'aria-label',
        tpl(
          t(
            si === 1 ? 'addNewPlace.starLabelOne' : 'addNewPlace.starLabelMany',
            si === 1 ? '{{n}} star' : '{{n}} stars'
          ),
          { n: si }
        )
      );
      starBtn.innerHTML =
        '<svg class="star-icon" xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<polygon points="' + starPoly + '" /></svg>';
      starRating.appendChild(starBtn);
    }
    ratingGroup.appendChild(starRating);
    ratingGroup.appendChild(ratingHidden);
    bodyWrap.appendChild(ratingGroup);

    var editStarBtns = starRating.querySelectorAll('.star-btn');
    function paintEditStars(value) {
      var n = parseInt(value, 10);
      if (!Number.isFinite(n) || n < 1) n = 0;
      if (n > 5) n = 5;
      editStarBtns.forEach(function (btn) {
        var r = parseInt(btn.getAttribute('data-rating'), 10);
        btn.classList.toggle('selected', n > 0 && r <= n);
        btn.classList.toggle('preview', n > 0 && r <= n);
      });
    }
    function currentEditRating() {
      var n = parseInt(ratingHidden.value, 10);
      return Number.isFinite(n) && n >= 1 && n <= 5 ? n : 0;
    }
    function setEditRating(value) {
      var n = parseInt(value, 10);
      if (!Number.isFinite(n) || n < 1) n = 0;
      if (n > 5) n = 5;
      ratingHidden.value = n > 0 ? String(n) : '';
      paintEditStars(n);
    }
    editStarBtns.forEach(function (btn) {
      btn.addEventListener('mouseenter', function () {
        paintEditStars(parseInt(btn.getAttribute('data-rating'), 10));
      });
      btn.addEventListener('focus', function () {
        paintEditStars(parseInt(btn.getAttribute('data-rating'), 10));
      });
      btn.addEventListener('click', function () {
        setEditRating(parseInt(btn.getAttribute('data-rating'), 10));
      });
    });
    starRating.addEventListener('mouseleave', function () {
      paintEditStars(currentEditRating());
    });
    setEditRating(initialRating);

    bodyWrap.appendChild(formGroup(descId, t('addNewPlace.description', 'Description'), descInput));

    // Existing photos + new uploads
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
      '<p class="upload-text">' + escapeHtml(t('visitedPlaces.addPhotosHint', 'Add photos by clicking or dragging and dropping (PNG or JPG, max 10 MB each). You can select several at once or add more in another step.')) + '</p>' +
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

    var newPhotoPicker = global.ImageUpload
      ? global.ImageUpload.createPicker({
        input: photosInput,
        previewGrid: newPreviewGrid,
        errorsEl: photoErrors,
        removeAriaLabel: t('visitedPlaces.clearNewPhoto', 'Remove new photo'),
        formatError: function (err) {
          var name = (err.file && err.file.name) || 'file';
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
        }
      })
      : null;

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
      if (newPhotoPicker) newPhotoPicker.clear();
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

    // After PUT: delete removed images, upload new ones
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
      (newPhotoPicker ? newPhotoPicker.getFiles() : []).forEach(function (file) {
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

    // Validate + PUT place, then apply photo changes
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
      var ratingRaw = parseInt(ratingHidden.value, 10);
      var rating =
        Number.isFinite(ratingRaw) && ratingRaw >= 1 && ratingRaw <= 5 ? ratingRaw : null;
      var body = {
        place_name: pn,
        country: (global.Countries && global.Countries.getCode(countryInput)) || null,
        date: startDate || null,
        end_date: endDate || null,
        rating: rating,
        description: (descInput.value || '').trim() || null
      };
      if (!body.country) {
        showError(t('addNewPlace.selectCountryFromList', 'Please select a country from the list.'));
        return;
      }
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
          deps.refreshList();
        })
        .catch(function (err) {
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

  global.PlaceEditModal = {
    init: init,
    deletePlace: deletePlace,
    openEditPlaceModal: openEditPlaceModal
  };
})(window);
