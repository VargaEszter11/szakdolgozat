
(function (global) {
  'use strict';

  function todayIso() {
    var d = new Date();
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function dayAfterIso(isoDate) {
    if (!isoDate) return null;
    var d = new Date(String(isoDate).trim() + 'T12:00:00');
    if (Number.isNaN(d.getTime())) return null;
    d.setDate(d.getDate() + 1);
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  // Minimum allowed end for a start date. Same-day allowed for stop arrival/departure
  function minEndFromStart(startIso, allowSameDay) {
    var today = todayIso();
    var start = (startIso || '').trim() || today;
    if (allowSameDay) return start;
    return dayAfterIso(start) || dayAfterIso(today);
  }

  function endNeedsFill(startIso, endIso, allowSameDay) {
    var start = (startIso || '').trim();
    var end = (endIso || '').trim();
    // Never invent an end date until the user has chosen a start.
    if (!start) return false;
    if (!end) return true;
    return allowSameDay ? end < start : end <= start;
  }

  function flatpickrLocaleKey() {
    var map = { hu: 'hu', de: 'de' };
    var lang = localStorage.getItem('language') || 'en';
    return map[lang] || 'default';
  }

  function resolveLocale() {
    var key = flatpickrLocaleKey();
    if (
      key &&
      key !== 'default' &&
      global.flatpickr &&
      flatpickr.l10ns &&
      flatpickr.l10ns[key]
    ) {
      return flatpickr.l10ns[key];
    }
    return null;
  }

  function baseOpts(extra) {
    var opts = {
      dateFormat: 'Y-m-d',
      disableMobile: true,
      allowInput: false,
      onOpen: function (selectedDates, dateStr, instance) {
        var jumpTo = dateStr || (instance.input && instance.input.value) || '';
        if (jumpTo) instance.jumpToDate(jumpTo, false);
      }
    };
    var locale = resolveLocale();
    if (locale) opts.locale = locale;
    if (extra) {
      for (var k in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, k)) opts[k] = extra[k];
      }
    }
    return opts;
  }

  function resolveEl(elOrSelector) {
    if (!elOrSelector) return null;
    if (typeof elOrSelector === 'string') return document.querySelector(elOrSelector);
    return elOrSelector;
  }

  function fp(input) {
    return input && input._flatpickr ? input._flatpickr : null;
  }

  function readIso(input) {
    if (!input) return '';
    var inst = fp(input);
    if (inst && inst.selectedDates && inst.selectedDates[0]) {
      return inst.formatDate(inst.selectedDates[0], 'Y-m-d');
    }
    return String(input.value || '').trim().slice(0, 10);
  }

  function setIso(input, iso, triggerChange) {
    if (!input) return;
    var val = iso ? String(iso).slice(0, 10) : '';
    var inst = fp(input);
    if (inst) {
      if (val) {
        inst.setDate(val, !!triggerChange);
        input.value = val;
      } else {
        inst.clear();
        input.value = '';
      }
    } else {
      input.value = val;
    }
  }

  function setMinDate(input, minIso) {
    if (!input || !minIso) return;
    var inst = fp(input);
    if (inst) inst.set('minDate', minIso);
    else input.setAttribute('min', minIso);
  }

  function destroyIn(root) {
    if (!root || !root.querySelectorAll) return;
    var inputs = root.querySelectorAll('input');
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i]._flatpickr) inputs[i]._flatpickr.destroy();
    }
  }

  function attach(input, options) {
    input = resolveEl(input);
    if (!input) return null;
    options = options || {};
    if (typeof flatpickr === 'undefined') {
      input.type = 'date';
      if (options.minDate) input.setAttribute('min', options.minDate);
      return null;
    }
    try {
      if (input._flatpickr) input._flatpickr.destroy();
      input.type = 'text';
      return flatpickr(input, baseOpts(options));
    } catch (err) {
      console.error('DatePickers.attach', err);
      input.type = 'date';
      if (options.minDate) input.setAttribute('min', options.minDate);
      return null;
    }
  }


  function initLinked(startInput, endInput, options) {
    startInput = resolveEl(startInput);
    endInput = resolveEl(endInput);
    options = options || {};
    if (!startInput || !endInput) {
      return {
        startPicker: null,
        endPicker: null,
        sync: function () { },
        linkEndToStart: function () { },
        destroy: function () { }
      };
    }

    var forceFillEnd = !!(options.forceFillEnd || options.forceFillEnd);
    var allowSameDay = !!(options.allowSameDay || options.allowSameDay);
    var silentFn = options.isSilent || options.isSilent;
    var today = todayIso();
    var startMin = options.minDate || today;
    var start = (startInput.value || '').trim();
    var end = (endInput.value || '').trim();
    if (start && start < startMin) start = startMin;
    // Only adjust end from start when a start value already exists (do not prefill on load).
    var minEnd = start ? minEndFromStart(start, allowSameDay) : minEndFromStart(startMin, allowSameDay);
    if (start && (endNeedsFill(start, end, allowSameDay) || (minEnd && end && end < minEnd))) {
      end = minEnd || '';
    }
    startInput.value = start;
    endInput.value = end;

    function shouldSkip() {
      return typeof silentFn === 'function' && silentFn();
    }

    function linkEndToStart(dateStr) {
      if (!dateStr) return;
      var nextMinEnd = minEndFromStart(dateStr, allowSameDay);
      if (!nextMinEnd) return;

      setMinDate(endInput, nextMinEnd);

      var endVal = readIso(endInput);
      if (forceFillEnd || endNeedsFill(dateStr, endVal, allowSameDay)) {
        setIso(endInput, nextMinEnd, false);
        // Always mirror into the input so the UI updates even if flatpickr is flaky.
        endInput.value = nextMinEnd;
      }

      var inst = fp(endInput);
      if (inst) inst.jumpToDate(nextMinEnd, false);
    }

    function onStartChange(dateStr) {
      linkEndToStart(dateStr);
      if (typeof options.onStartChange === 'function') {
        try {
          options.onStartChange(dateStr);
        } catch (err) {
          console.error('DatePickers onStartChange', err);
        }
      }
      // Hooks (stop sync) must not leave end before/on start.
      linkEndToStart(dateStr || readIso(startInput));
    }

    function onEndChange() {
      var startVal = readIso(startInput);
      var endVal = readIso(endInput);
      // Clamp invalid end picks (calendar can still fire with stale values).
      if (startVal && endNeedsFill(startVal, endVal, allowSameDay)) {
        linkEndToStart(startVal);
        endVal = readIso(endInput);
      }
      if (typeof options.onEndChange === 'function') {
        try {
          options.onEndChange(endVal);
        } catch (err) {
          console.error('DatePickers onEndChange', err);
        }
      }
    }

    var startPicker = null;
    var endPicker = null;
    var fpExtra = {};
    if (options.appendTo) fpExtra.appendTo = options.appendTo;

    function wireNative() {
      startInput.type = 'date';
      endInput.type = 'date';
      startInput.setAttribute('min', startMin);
      if (minEnd) endInput.setAttribute('min', minEnd);
      startInput.addEventListener('change', function () {
        onStartChange(startInput.value || '');
      });
      endInput.addEventListener('change', onEndChange);
    }

    if (typeof flatpickr === 'undefined') {
      wireNative();
    } else {
      try {
        if (endInput._flatpickr) endInput._flatpickr.destroy();
        if (startInput._flatpickr) startInput._flatpickr.destroy();
        endInput.type = 'text';
        startInput.type = 'text';

        endPicker = flatpickr(
          endInput,
          baseOpts(
            Object.assign({}, fpExtra, {
              minDate: minEnd || minEndFromStart(startMin, allowSameDay),
              onChange: function () {
                if (shouldSkip()) return;
                onEndChange();
              }
            })
          )
        );

        startPicker = flatpickr(
          startInput,
          baseOpts(
            Object.assign({}, fpExtra, {
              minDate: startMin,
              onChange: function (selectedDates, dateStr) {
                if (shouldSkip()) return;
                var iso = dateStr;
                if (selectedDates && selectedDates[0]) {
                  iso = flatpickr.formatDate(selectedDates[0], 'Y-m-d');
                }
                if (!iso) return;
                onStartChange(iso);
              }
            })
          )
        );
      } catch (err) {
        console.error('DatePickers.initLinked', err);
        wireNative();
      }
    }

    function sync(startValue, endValue) {
      var s = (startValue != null ? startValue : readIso(startInput) || '').trim();
      var e = (endValue != null ? endValue : readIso(endInput) || '').trim();
      if (s && s < startMin) s = startMin;
      var nextMin = minEndFromStart(s || startMin, allowSameDay);
      if (s && (endNeedsFill(s, e, allowSameDay) || (nextMin && e && e < nextMin))) {
        e = nextMin || '';
      }

      setMinDate(startInput, startMin);
      if (s) setIso(startInput, s, false);
      else if (fp(startInput)) fp(startInput).clear();
      else startInput.value = '';

      setMinDate(endInput, nextMin);
      if (e) setIso(endInput, e, false);
      else if (fp(endInput)) fp(endInput).clear();
      else endInput.value = '';
    }

    sync(start, end);

    return {
      startPicker: startPicker,
      endPicker: endPicker,
      startInput: startInput,
      endInput: endInput,
      sync: sync,
      linkEndToStart: linkEndToStart,
      destroy: function () {
        if (startPicker) startPicker.destroy();
        if (endPicker) endPicker.destroy();
      }
    };
  }

  global.DatePickers = {
    todayIso: todayIso,
    dayAfterIso: dayAfterIso,
    minEndFromStart: minEndFromStart,
    flatpickrLocaleKey: flatpickrLocaleKey,
    baseOpts: baseOpts,
    readIso: readIso,
    setIso: setIso,
    setMinDate: setMinDate,
    attach: attach,
    destroyIn: destroyIn,
    initLinked: initLinked
  };
})(window);
