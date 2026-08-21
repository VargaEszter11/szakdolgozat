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

    var endPicker = visitedEndDateInput ? flatpickr(visitedEndDateInput, Object.assign({}, fpOpts, {
      onOpen: function (selectedDates, dateStr, instance) {
        var jumpTo = dateStr || (instance.input && instance.input.value) || '';
        if (jumpTo) instance.jumpToDate(jumpTo, false);
      }
    })) : null;
    if (visitedDateInput) {
      flatpickr(visitedDateInput, Object.assign({}, fpOpts, {
        onOpen: function (selectedDates, dateStr, instance) {
          var jumpTo = dateStr || (instance.input && instance.input.value) || '';
          if (jumpTo) instance.jumpToDate(jumpTo, false);
        },
        onChange: function (selectedDates, dateStr) {
          if (!dateStr || !endPicker) return;
          endPicker.set('minDate', dateStr);
          var endVal = endPicker.input.value || '';
          if (!endVal || endVal < dateStr) {
            endPicker.setDate(dateStr, true);
          }
          endPicker.jumpToDate(dateStr, true);
        }
      }));
      var initialStart = visitedDateInput.value || '';
      if (initialStart && endPicker) {
        endPicker.set('minDate', initialStart);
        var endVal = endPicker.input.value || '';
        if (!endVal || endVal < initialStart) {
          endPicker.setDate(initialStart, true);
        }
        endPicker.jumpToDate(initialStart, true);
      }
      if (initialStart && visitedDateInput._flatpickr) {
        visitedDateInput._flatpickr.jumpToDate(initialStart, true);
      }
    }
  }

  if (starBtns.length && ratingInput) {
    function paintStars(value) {
      var n = parseInt(value, 10);
      if (!Number.isFinite(n) || n < 1) n = 0;
      if (n > 5) n = 5;
      starBtns.forEach(function (btn) {
        var r = parseInt(btn.getAttribute('data-rating'), 10);
        btn.classList.toggle('selected', n > 0 && r <= n);
        btn.classList.toggle('preview', n > 0 && r <= n);
      });
    }

    function currentRating() {
      var n = parseInt(ratingInput.value, 10);
      return Number.isFinite(n) && n >= 1 && n <= 5 ? n : 0;
    }

    function setRating(value) {
      var n = parseInt(value, 10);
      if (!Number.isFinite(n) || n < 1) n = 0;
      if (n > 5) n = 5;
      ratingInput.value = n > 0 ? String(n) : '';
      paintStars(n);
    }

    var starRating = document.querySelector('.star-rating');
    starBtns.forEach(function (btn) {
      btn.addEventListener('mouseenter', function () {
        paintStars(parseInt(btn.getAttribute('data-rating'), 10));
      });
      btn.addEventListener('focus', function () {
        paintStars(parseInt(btn.getAttribute('data-rating'), 10));
      });
      btn.addEventListener('click', function () {
        setRating(parseInt(btn.getAttribute('data-rating'), 10));
      });
    });
    if (starRating) {
      starRating.addEventListener('mouseleave', function () {
        paintStars(currentRating());
      });
    }
    setRating(0);
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
  var photoPicker = null;
  if (!window.ImageUpload) {
    console.error('ImageUpload helper failed to load');
  } else if (photosInput) {
    photoPicker = window.ImageUpload.createPicker({
      input: photosInput,
      previewGrid: photoPreviewGrid,
      errorsEl: photoFormatErrors,
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
      (window.Countries && window.Countries.getCode(countryInput)) || '';
    var visitedDate = document.getElementById('visitedDate').value;
    var visitedEndDate = document.getElementById('visitedEndDate').value;
    var description = document.getElementById('description').value.trim();
    var notes = document.getElementById('notes').value.trim();
    var ratingRaw = parseInt(document.getElementById('rating').value, 10);
    var rating = Number.isFinite(ratingRaw) && ratingRaw >= 1 && ratingRaw <= 5 ? ratingRaw : null;

    if (!placeName || !country || !visitedDate) {
      showErrorMsg(
        !country && (countryInput && countryInput.value.trim())
          ? 'Please select a country from the suggestions list.'
          : 'Please fill in Place Name, Country and Start Date.'
      );
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

    var filesToUpload = photoPicker ? photoPicker.getFiles() : [];
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
