(function (root) {
  var MAX_BYTES = 10 * 1024 * 1024;

  function allowedImageMime(type) {
    var x = (type || '').toLowerCase().split(';')[0].trim();
    return x === 'image/jpeg' || x === 'image/jpg' || x === 'image/png';
  }

  function allowedImageExtension(name) {
    var ext = (name || '').split('.').pop().toLowerCase();
    return ext === 'jpg' || ext === 'jpeg' || ext === 'png';
  }

  function isAllowedImage(file) {
    if (!file) return false;
    if (allowedImageMime(file.type)) return true;
    if (!file.type && allowedImageExtension(file.name)) return true;
    return false;
  }

  function fileKey(f) {
    return (f.name || '') + '|' + String(f.size) + '|' + String(f.lastModified);
  }

  function defaultFormatError(err) {
    var name = (err.file && err.file.name) || 'file';
    if (err.reason === 'size') {
      return 'File too large (max 10 MB): ' + name;
    }
    return 'Only PNG or JPEG files are allowed: ' + name;
  }

  /**
   * @param {object} opts
   * @param {HTMLInputElement} opts.input
   * @param {HTMLElement} opts.previewGrid
   * @param {HTMLElement} [opts.errorsEl]
   * @param {number} [opts.maxFiles] default unlimited; use 1 for single image
   * @param {function({file: File, reason: string}): string} [opts.formatError]
   * @param {string} [opts.removeAriaLabel]
   * @returns {{ getFiles: function(): File[], clear: function(): void }}
   */
  function createPicker(opts) {
    var input = opts.input;
    var previewGrid = opts.previewGrid;
    var errorsEl = opts.errorsEl || null;
    var maxFiles = opts.maxFiles != null ? opts.maxFiles : Infinity;
    var formatError = typeof opts.formatError === 'function' ? opts.formatError : defaultFormatError;
    var removeAriaLabel = opts.removeAriaLabel || 'Remove photo';

    var selectedFiles = [];
    var previewObjectUrls = [];

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

    function clearInputValue() {
      if (!input) return;
      try {
        input.value = '';
      } catch (err) {
        /* ignore */
      }
    }

    function showErrors(batchErrors) {
      if (!errorsEl) return;
      if (!batchErrors || !batchErrors.length) {
        errorsEl.hidden = true;
        errorsEl.textContent = '';
        return;
      }
      errorsEl.hidden = false;
      errorsEl.textContent = batchErrors.map(formatError).join('\n');
    }

    function renderPreviews() {
      if (!previewGrid) return;
      revokePreviewUrls();
      previewGrid.innerHTML = '';
      if (selectedFiles.length === 0) {
        previewGrid.hidden = true;
        return;
      }
      previewGrid.hidden = false;
      selectedFiles.forEach(function (file) {
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
        rm.setAttribute('aria-label', removeAriaLabel);
        rm.appendChild(document.createTextNode('×'));
        rm.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          var idx = selectedFiles.indexOf(file);
          if (idx >= 0) selectedFiles.splice(idx, 1);
          clearInputValue();
          renderPreviews();
          showErrors([]);
        });

        item.appendChild(img);
        item.appendChild(rm);
        previewGrid.appendChild(item);
      });
    }

    function clear() {
      selectedFiles = [];
      clearInputValue();
      renderPreviews();
      showErrors([]);
    }

    function handleFiles(picked) {
      var batchErrors = [];
      var prevKeys = {};
      selectedFiles.forEach(function (f) {
        prevKeys[fileKey(f)] = true;
      });

      if (maxFiles === 1) {
        selectedFiles = [];
        prevKeys = {};
      }

      picked.forEach(function (file) {
        if (!isAllowedImage(file)) {
          batchErrors.push({ file: file, reason: 'format' });
          return;
        }
        if (file.size > MAX_BYTES) {
          batchErrors.push({ file: file, reason: 'size' });
          return;
        }
        if (prevKeys[fileKey(file)]) return;
        if (selectedFiles.length >= maxFiles) return;
        prevKeys[fileKey(file)] = true;
        selectedFiles.push(file);
      });

      renderPreviews();
      showErrors(batchErrors);
    }

    function onChange() {
      var picked = Array.from((input && input.files) || []);
      // Clear so the same file can be chosen again. Do NOT write files back to the
      // input — that can re-fire "change" and break the picker in some browsers.
      clearInputValue();
      handleFiles(picked);
    }

    if (input) {
      input.addEventListener('change', onChange);
    }

    // Drag & drop onto the surrounding drop zone (defaults to the <label> the
    // file input lives in, e.g. <label class="upload-zone" for="photos">).
    var dropZone = opts.dropZone || (input && input.closest('.upload-zone')) || null;
    if (dropZone) {
      var dragDepth = 0;

      var setDragOver = function (on) {
        dropZone.classList.toggle('upload-zone--dragover', on);
      };

      dropZone.addEventListener('dragenter', function (e) {
        if (!e.dataTransfer || Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') === -1) return;
        e.preventDefault();
        dragDepth++;
        setDragOver(true);
      });

      dropZone.addEventListener('dragover', function (e) {
        if (!e.dataTransfer || Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') === -1) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
      });

      dropZone.addEventListener('dragleave', function () {
        dragDepth = Math.max(0, dragDepth - 1);
        if (dragDepth === 0) setDragOver(false);
      });

      dropZone.addEventListener('drop', function (e) {
        if (!e.dataTransfer) return;
        e.preventDefault();
        dragDepth = 0;
        setDragOver(false);
        var dropped = Array.from(e.dataTransfer.files || []);
        if (dropped.length) handleFiles(dropped);
      });
    }

    return {
      getFiles: function () {
        return selectedFiles.slice();
      },
      clear: clear
    };
  }

  var api = {
    MAX_BYTES: MAX_BYTES,
    isAllowedImage: isAllowedImage,
    fileKey: fileKey,
    createPicker: createPicker
  };

  root.ImageUpload = api;
})(typeof window !== 'undefined' ? window : globalThis);
