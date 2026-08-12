document.addEventListener('DOMContentLoaded', function () {
  var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
  var showErrorMsg = typeof window.showError === 'function'
    ? window.showError.bind(window)
    : function (msg, onClose) { alert(msg); if (typeof onClose === 'function') onClose(); };

  function goToVisitedPlaces() {
    window.location.href = 'visited_places.html';
  }

  function tpl(template, vars) {
    if (!template || typeof template !== 'string') return '';
    return template.replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  /** @returns {HTMLElement | null} */
  function progressEl() {
    return document.getElementById('submitProgress');
  }

  function showProgress(text, variant) {
    var el = progressEl();
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.classList.remove('submit-progress--ok', 'submit-progress--error');
    if (variant === 'ok') el.classList.add('submit-progress--ok');
    if (variant === 'error') el.classList.add('submit-progress--error');
  }

  function hideProgress() {
    var el = progressEl();
    if (!el) return;
    el.hidden = true;
    el.textContent = '';
    el.classList.remove('submit-progress--ok', 'submit-progress--error');
  }

  async function responseDetail(res) {
    var j = await res.json().catch(function () { return null; });
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
  }

  const form = document.getElementById('addPlaceForm');
  const cancelBtn = document.getElementById('cancelBtn');
  const visitedDateInput = document.getElementById('visitedDate');
  const visitedEndDateInput = document.getElementById('visitedEndDate');
  const ratingInput = document.getElementById('rating');
  const starBtns = document.querySelectorAll('.star-btn');
  const countryInputEl = document.getElementById('country');
  if (countryInputEl && window.Countries) {
    window.Countries.mountAutocomplete(countryInputEl);
  }

  if (typeof flatpickr === 'function') {
    var LOCALE_MAP = { hu: 'hu', de: 'de' };
    var lang = localStorage.getItem('language') || 'en';
    var fpLocale = LOCALE_MAP[lang] || 'default';

    var fpOpts = {
      dateFormat: 'Y-m-d',
      maxDate: 'today',
      locale: fpLocale,
      disableMobile: true
    };

    if (visitedDateInput) {
      flatpickr(visitedDateInput, fpOpts);
    }
    if (visitedEndDateInput) {
      flatpickr(visitedEndDateInput, fpOpts);
    }
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

  var photosInput = document.getElementById('photos');
  var photoPreviewGrid = document.getElementById('photoPreviewGrid');
  var photoFormatErrors = document.getElementById('photoFormatErrors');
  var selectedPhotoFiles = [];
  var previewObjectUrls = [];
  var MAX_PHOTO_BYTES = 10 * 1024 * 1024;

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

  function fileKey(f) {
    return (f.name || '') + '|' + String(f.size) + '|' + String(f.lastModified);
  }

  function syncSelectedFilesToInput() {
    if (!photosInput) return;
    var dt = new DataTransfer();
    selectedPhotoFiles.forEach(function (f) {
      dt.items.add(f);
    });
    photosInput.files = dt.files;
  }

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

  function renderPhotoPreviews() {
    if (!photoPreviewGrid) return;
    revokePreviewUrls();
    photoPreviewGrid.innerHTML = '';
    if (selectedPhotoFiles.length === 0) {
      photoPreviewGrid.hidden = true;
      return;
    }
    photoPreviewGrid.hidden = false;
    selectedPhotoFiles.forEach(function (file) {
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
      rm.setAttribute('aria-label', 'Remove photo');
      rm.appendChild(document.createTextNode('×'));

      rm.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var idx = selectedPhotoFiles.indexOf(file);
        if (idx >= 0) selectedPhotoFiles.splice(idx, 1);
        syncSelectedFilesToInput();
        renderPhotoPreviews();
      });

      item.appendChild(img);
      item.appendChild(rm);
      photoPreviewGrid.appendChild(item);
    });
  }

  function showPhotoFormatErrors(batchErrors) {
    if (!photoFormatErrors) return;
    if (!batchErrors || !batchErrors.length) {
      photoFormatErrors.hidden = true;
      photoFormatErrors.textContent = '';
      return;
    }
    photoFormatErrors.hidden = false;
    var lines = batchErrors.map(function (err) {
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
    photoFormatErrors.textContent = lines.join('\n');
  }

  if (photosInput) {
    photosInput.addEventListener('change', function () {
      var picked = Array.from(photosInput.files || []);
      photosInput.value = '';
      var batchErrors = [];
      var prevKeys = {};
      selectedPhotoFiles.forEach(function (f) {
        prevKeys[fileKey(f)] = true;
      });
      if (picked.length === 0) {
        syncSelectedFilesToInput();
        renderPhotoPreviews();
        showPhotoFormatErrors([]);
        return;
      }
      picked.forEach(function (file) {
        if (!isAllowedImage(file)) {
          batchErrors.push({ file: file, reason: 'format' });
        } else if (file.size > MAX_PHOTO_BYTES) {
          batchErrors.push({ file: file, reason: 'size' });
        } else if (!prevKeys[fileKey(file)]) {
          prevKeys[fileKey(file)] = true;
          selectedPhotoFiles.push(file);
        }
      });
      syncSelectedFilesToInput();
      renderPhotoPreviews();
      showPhotoFormatErrors(batchErrors);
    });
  }

  var submitBtn = form.querySelector('[type="submit"]');
  var submitLabelSpan = submitBtn ? submitBtn.querySelector('span') : null;
  var submitLabelOriginal = submitLabelSpan ? submitLabelSpan.textContent : '';

  function setSubmitLoading(loading, labelKeyOrText) {
    if (!submitBtn) return;
    submitBtn.disabled = loading;
    if (cancelBtn) cancelBtn.disabled = loading;
    form.setAttribute('aria-busy', loading ? 'true' : 'false');
    if (submitLabelSpan) {
      if (loading && labelKeyOrText) {
        var translated = t(labelKeyOrText);
        submitLabelSpan.textContent =
          translated !== labelKeyOrText ? translated : labelKeyOrText;
      } else if (!loading) {
        submitLabelSpan.textContent = submitLabelOriginal;
      }
    }
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    var userId = localStorage.getItem('user_id');
    if (!userId) {
      showErrorMsg('Please log in to add a place.', function () {
        window.location.href = '../loginRegister/loginPage.html';
      });
      return;
    }

    var placeName = document.getElementById('placeName').value.trim();
    var countryInput = document.getElementById('country');
    var country =
      (window.Countries && window.Countries.getCode(countryInput)) ||
      (countryInput && countryInput.value.trim()) ||
      '';
    var visitedDate = document.getElementById('visitedDate').value;
    var visitedEndDate = document.getElementById('visitedEndDate').value;
    var description = document.getElementById('description').value.trim();
    var notes = document.getElementById('notes').value.trim();
    var rating = parseInt(document.getElementById('rating').value, 10) || 5;

    if (!placeName || !country || !visitedDate) {
      showErrorMsg('Please fill in Place Name, Country and Start Date.');
      return;
    }

    if (visitedEndDate && visitedEndDate < visitedDate) {
      showErrorMsg('End date must be on or after the start date.');
      return;
    }

    var fullDescription = description;
    if (notes) {
      fullDescription = description ? description + '\n\n' + notes : notes;
    }

    var requestBody = {
      user_id: parseInt(userId, 10),
      place_name: placeName,
      country: country,
      date: visitedDate,
      end_date: visitedEndDate || null,
      rating: rating,
      description: fullDescription || null
    };

    var filesToUpload = selectedPhotoFiles.slice();
    var fileCount = filesToUpload.length;

    hideProgress();
    setSubmitLoading(true, 'addNewPlace.buttonSaving');
    showProgress(t('addNewPlace.progressSaving'));

    try {
      var response = await fetch('/api/visited-places', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        var errDetail = await responseDetail(response);
        throw new Error(errDetail || 'Failed to add place');
      }

      var created = await response.json().catch(function () { return null; });
      var placeId = created && created.id != null ? created.id : null;

      if (placeId == null) {
        throw new Error('Server did not return a place id.');
      }

      if (fileCount === 0) {
        hideProgress();
        setSubmitLoading(false);
        goToVisitedPlaces();
        return;
      }

      setSubmitLoading(true, 'addNewPlace.buttonUploading');

      for (var fi = 0; fi < filesToUpload.length; fi++) {
        var upLine = t('addNewPlace.progressUploadSingle');
        if (!upLine || upLine === 'addNewPlace.progressUploadSingle') {
          upLine = 'Uploading photo…';
        }
        if (filesToUpload.length > 1) {
          upLine = upLine + ' (' + (fi + 1) + '/' + filesToUpload.length + ')';
        }
        showProgress(upLine);

        var fd = new FormData();
        fd.append('file', filesToUpload[fi]);

        var up = await fetch('/api/visited-places/' + placeId + '/images/upload', {
          method: 'POST',
          body: fd
        });

        if (!up.ok) {
          var failDetail = await responseDetail(up);
          showProgress('✗ ' + failDetail, 'error');
          var partialTpl = t('addNewPlace.uploadPartial');
          var partialMsg = tpl(partialTpl, { details: failDetail });
          if (partialMsg.indexOf('addNewPlace.') === 0 || partialMsg.indexOf('{{details}}') >= 0) {
            partialMsg = 'Place saved, but a photo failed to upload:\n' + failDetail;
          }
          setSubmitLoading(false);
          showErrorMsg(partialMsg);
          return;
        }
      }

      var okLine = t('addNewPlace.progressPhotoUploaded');
      if (!okLine || okLine === 'addNewPlace.progressPhotoUploaded') {
        okLine = 'Photo uploaded.';
      }
      if (filesToUpload.length > 1) {
        okLine = filesToUpload.length + ' photos uploaded.';
      }
      showProgress(okLine, 'ok');

      setSubmitLoading(false);
      hideProgress();
      goToVisitedPlaces();
    } catch (error) {
      console.error('Error adding place:', error);
      hideProgress();
      setSubmitLoading(false);
      showErrorMsg('Failed to add place: ' + (error.message || String(error)));
    }
  });
});
