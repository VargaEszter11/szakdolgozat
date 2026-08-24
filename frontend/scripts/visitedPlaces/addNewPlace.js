document.addEventListener('DOMContentLoaded', function () {
  var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : function (k) { return k; };
  var showErrorMsg = typeof window.showError === 'function'
    ? window.showError.bind(window)
    : function (msg, onClose) { alert(msg); if (typeof onClose === 'function') onClose(); };

  var DRAFT_KEY = 'add_new_place_draft_v1';

  function goToVisitedPlaces() {
    window.location.href = 'visited_places.html';
  }

  function tpl(template, vars) {
    if (!template || typeof template !== 'string') return '';
    return template.replace(/\{\{(\w+)\}\}/g, function (_, key) {
      return vars[key] != null ? String(vars[key]) : '';
    });
  }

  function readDraft() {
    try {
      var raw = sessionStorage.getItem(DRAFT_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      return data && typeof data === 'object' ? data : null;
    } catch (e) {
      return null;
    }
  }

  function clearDraft() {
    try {
      sessionStorage.removeItem(DRAFT_KEY);
    } catch (e) { /* ignore */ }
  }

  /** @returns {HTMLElement | null} */
  function progressEl() {
    return document.getElementById('submitProgress');
  }

  // Inline status banner during save/upload
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

  // Normalizing FastAPI error bodies
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

  // Form field references
  const form = document.getElementById('addPlaceForm');
  const cancelBtn = document.getElementById('cancelBtn');
  const visitedDateInput = document.getElementById('visitedDate');
  const visitedEndDateInput = document.getElementById('visitedEndDate');
  const ratingInput = document.getElementById('rating');
  const starBtns = document.querySelectorAll('.star-btn');
  const countryInputEl = document.getElementById('country');
  const placeNameInput = document.getElementById('placeName');
  const descriptionInput = document.getElementById('description');

  // Country autocomplete based on ISO codes
  var draft = readDraft();
  if (draft && countryInputEl && draft.countryCode) {
    countryInputEl.dataset.countryCode = draft.countryCode;
  }

  if (countryInputEl && window.Countries) {
    window.Countries.mountAutocomplete(countryInputEl);
  }

  var startPicker = null;
  var endPicker = null;
  // Auto-set end date from start date
  var lastAutoEnd = '';
  var setRating = null;

  // Linked date picker, max date today
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

    endPicker = visitedEndDateInput ? flatpickr(visitedEndDateInput, Object.assign({}, fpOpts, {
      onOpen: function (selectedDates, dateStr, instance) {
        var jumpTo = dateStr || (instance.input && instance.input.value) || '';
        if (jumpTo) instance.jumpToDate(jumpTo, false);
      }
    })) : null;
    if (visitedDateInput) {
      startPicker = flatpickr(visitedDateInput, Object.assign({}, fpOpts, {
        onOpen: function (selectedDates, dateStr, instance) {
          var jumpTo = dateStr || (instance.input && instance.input.value) || '';
          if (jumpTo) instance.jumpToDate(jumpTo, false);
        },
        onChange: function (selectedDates, dateStr) {
          if (!dateStr || !endPicker) return;
          endPicker.set('minDate', dateStr);
          var endVal = endPicker.input.value || '';
          if (!endVal || endVal < dateStr || endVal === lastAutoEnd) {
            endPicker.setDate(dateStr, true);
            lastAutoEnd = dateStr;
          }
          endPicker.jumpToDate(endPicker.input.value || dateStr, true);
        }
      }));
    }
  }

  // Rating, optional
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

    setRating = function (value) {
      var n = parseInt(value, 10);
      if (!Number.isFinite(n) || n < 1) n = 0;
      if (n > 5) n = 5;
      ratingInput.value = n > 0 ? String(n) : '';
      paintStars(n);
    };

    var starRating = document.querySelector('.star-rating');
    starBtns.forEach(function (btn) {
      btn.addEventListener('mouseenter', function () {
        paintStars(parseInt(btn.getAttribute('data-rating'), 10)); // hover preview
      });
      btn.addEventListener('focus', function () {
        paintStars(parseInt(btn.getAttribute('data-rating'), 10));
      });
      btn.addEventListener('click', function () {
        setRating(parseInt(btn.getAttribute('data-rating'), 10)); // commit selection
        saveDraft();
      });
    });
    if (starRating) {
      starRating.addEventListener('mouseleave', function () {
        paintStars(currentRating()); // revert preview to committed value
      });
    }
    setRating(0);
  }

  // Save fields content when page reload
  function saveDraft() {
    if (!form) return;
    var payload = {
      placeName: placeNameInput ? placeNameInput.value : '',
      countryCode: (window.Countries && countryInputEl)
        ? (window.Countries.getCode(countryInputEl) || '')
        : '',
      countryLabel: countryInputEl ? countryInputEl.value : '',
      visitedDate: visitedDateInput ? visitedDateInput.value : '',
      visitedEndDate: visitedEndDateInput ? visitedEndDateInput.value : '',
      lastAutoEnd: lastAutoEnd || '',
      rating: ratingInput ? ratingInput.value : '',
      description: descriptionInput ? descriptionInput.value : ''
    };
    try {
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(payload));
    } catch (e) { /* ignore quota */ }
  }

  function restoreDraft() {
    if (!draft) return;
    if (placeNameInput && draft.placeName) placeNameInput.value = draft.placeName;
    if (descriptionInput && draft.description) descriptionInput.value = draft.description;
    if (countryInputEl && draft.countryCode) {
      countryInputEl.dataset.countryCode = draft.countryCode;
      // Re-localize display name if the user changed app language since last save.
      if (typeof countryInputEl._countrySyncLanguage === 'function') {
        countryInputEl._countrySyncLanguage();
      } else if (draft.countryLabel) {
        countryInputEl.value = draft.countryLabel;
      }
    }
    if (draft.visitedDate && startPicker) {
      startPicker.setDate(draft.visitedDate, false);
      if (endPicker) endPicker.set('minDate', draft.visitedDate);
    } else if (draft.visitedDate && visitedDateInput) {
      visitedDateInput.value = draft.visitedDate;
    }
    if (draft.visitedEndDate && endPicker) {
      endPicker.setDate(draft.visitedEndDate, false);
    } else if (draft.visitedEndDate && visitedEndDateInput) {
      visitedEndDateInput.value = draft.visitedEndDate;
    }
    if (draft.lastAutoEnd) lastAutoEnd = draft.lastAutoEnd;
    else if (draft.visitedDate && draft.visitedEndDate === draft.visitedDate) {
      lastAutoEnd = draft.visitedDate;
    }
    if (setRating && draft.rating) setRating(draft.rating);
  }

  restoreDraft();

  // Flatpickr does not fire input/change on the underlying field
  function bindSaveOnChange(picker) {
    if (!picker || !picker.config) return;
    var existing = picker.config.onChange;
    if (Array.isArray(existing)) {
      existing.push(saveDraft);
    } else if (typeof existing === 'function') {
      picker.config.onChange = [existing, saveDraft];
    } else {
      picker.config.onChange = [saveDraft];
    }
  }

  if (form) {
    form.addEventListener('input', saveDraft);
    form.addEventListener('change', saveDraft);
  }
  bindSaveOnChange(startPicker);
  bindSaveOnChange(endPicker);

  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      clearDraft();
      window.location.href = 'visited_places.html';
    });
  }

  if (!form) return;

  // Photo upload
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
          // Fallback if i18n key missing
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

  // Disables submit/cancel and swaps button label while async work runs
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

  // Submit button handler
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    var userId = localStorage.getItem('user_id');
    if (!userId) {
      showErrorMsg(t('addNewPlace.loginRequired'), function () {
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
    var ratingRaw = parseInt(document.getElementById('rating').value, 10);
    var rating = Number.isFinite(ratingRaw) && ratingRaw >= 1 && ratingRaw <= 5 ? ratingRaw : null;

    if (!placeName || !country || !visitedDate) {
      // Free-text country without a resolved ISO code gets a specific hint
      showErrorMsg(
        !country && (countryInput && countryInput.value.trim())
          ? t('addNewPlace.selectCountryFromList')
          : t('addNewPlace.fillRequired')
      );
      return;
    }

    if (visitedEndDate && visitedEndDate < visitedDate) {
      showErrorMsg(t('addNewPlace.endDateBeforeStart'));
      return;
    }

    var requestBody = {
      user_id: parseInt(userId, 10), // schema field; server overwrites from JWT anyway
      place_name: placeName,
      country: country,
      date: visitedDate,
      end_date: visitedEndDate || null,
      rating: rating, // null when not set, optional field
      description: description || null
    };

    var filesToUpload = photoPicker ? photoPicker.getFiles() : [];
    var fileCount = filesToUpload.length;

    hideProgress();
    setSubmitLoading(true, 'addNewPlace.buttonSaving');
    showProgress(t('addNewPlace.progressSaving'));

    try {
      // Step 1: create the place record, backend geocodes place name and country to lat/lon, failure saves without coordinates
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
        clearDraft();
        hideProgress();
        setSubmitLoading(false);
        goToVisitedPlaces();
        return;
      }

      // Photos are uploaded sequentially
      setSubmitLoading(true, 'addNewPlace.buttonUploading');

      // Step 2: upload each selected photo
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
          // Place already saved
          clearDraft();
          setSubmitLoading(false);
          showErrorMsg(partialMsg);
          return;
        }
      }

      var okLine;
      if (filesToUpload.length > 1) {
        okLine = tpl(t('addNewPlace.photosUploaded'), { count: filesToUpload.length });
        if (!okLine || okLine.indexOf('addNewPlace.') === 0 || okLine.indexOf('{{count}}') >= 0) {
          okLine = filesToUpload.length + ' photos uploaded.';
        }
      } else {
        okLine = t('addNewPlace.progressPhotoUploaded');
        if (!okLine || okLine === 'addNewPlace.progressPhotoUploaded') {
          okLine = 'Photo uploaded.';
        }
      }
      showProgress(okLine, 'ok');

      clearDraft();
      setSubmitLoading(false);
      hideProgress();
      goToVisitedPlaces();
    } catch (error) {
      // Step 1 failed, place was not created, draft stays so the user can fix and retry
      hideProgress();
      setSubmitLoading(false);
      var failMsg = tpl(t('addNewPlace.addFailed'), {
        details: error.message || String(error)
      });
      if (!failMsg || failMsg.indexOf('addNewPlace.') === 0 || failMsg.indexOf('{{details}}') >= 0) {
        failMsg = 'Failed to add place: ' + (error.message || String(error));
      }
      showErrorMsg(failMsg);
    }
  });
});
