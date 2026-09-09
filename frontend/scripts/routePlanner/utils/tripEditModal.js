(function (global) {
  'use strict';

  function plannedTripsT(key, fallback) {
    if (global.i18n && typeof global.i18n.t === 'function') {
      var v = global.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  var H = global.TripMapHelper || null;
  function countryDisplay(value) {
    if (H && typeof H.countryDisplay === 'function') return H.countryDisplay(value);
    return value || '';
  }

  var DU = global.TripDateUtils;
  var toDateInputValue = DU.toDateInputValue;
  var fromDateInputVal = DU.fromDateInputVal;
  var trimOrNull = DU.trimOrNull;
  var parseEditDay = DU.parseEditDay;
  var fmtEditDay = DU.fmtEditDay;
  var addEditDaysUTC = DU.addEditDaysUTC;
  var dayDiffSigned = DU.dayDiffSigned;
  var dayDiffNonNeg = DU.dayDiffNonNeg;
  var placeNamesMatch = DU.placeNamesMatch;
  var todayIsoLocal = DU.todayIsoLocal;
  var dayAfterIsoLocal = DU.dayAfterIsoLocal;

  var deps = { refreshList: function () { return Promise.resolve(); } };

  function init(options) {
    options = options || {};
    if (typeof options.refreshList === 'function') deps.refreshList = options.refreshList;
  }

  function destroyPopups() {
    if (global.TripPopups && typeof global.TripPopups.destroyAll === 'function') {
      global.TripPopups.destroyAll();
    }
  }

  function renumberEditStops(listEl) {
    if (!listEl) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    for (var i = 0; i < rows.length; i++) {
      var b = rows[i].querySelector('.trip-stop-number');
      if (b) b.textContent = String(i + 1);
    }
  }

  /** Last stop whose place matches the trip start city = return-home leg. */
  function isReturnHomeEditStop(stop, startCity, index, total) {
    if (index !== total - 1 || total < 1) return false;
    return placeNamesMatch(stop && stop.place_name, startCity);
  }

  function isReturnHomeEditRow(row) {
    return !!(row && row.getAttribute('data-return-home') === '1');
  }

  var editDatesSilent = false;

  function setEditDateFieldValue(input, iso) {
    if (!input) return;
    editDatesSilent = true;
    try {
      if (global.DatePickers) {
        global.DatePickers.setIso(input, iso, false);
      } else {
        var val = iso ? String(iso).slice(0, 10) : '';
        if (input._flatpickr) {
          if (val) {
            input._flatpickr.setDate(val, false);
            input.value = val;
          } else {
            input._flatpickr.clear();
            input.value = '';
          }
        } else {
          input.value = val;
        }
      }
    } finally {
      editDatesSilent = false;
    }
  }

  function destroyEditDatePickers(root) {
    if (global.DatePickers) global.DatePickers.destroyIn(root);
    else if (root) {
      var inputs = root.querySelectorAll('input');
      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i]._flatpickr) inputs[i]._flatpickr.destroy();
      }
    }
  }

  function attachEditDatePicker(input, options) {
    if (global.DatePickers) return global.DatePickers.attach(input, options || {});
    return null;
  }

  function readEditIsoDate(input) {
    if (global.DatePickers) return global.DatePickers.readIso(input);
    if (!input) return '';
    return String(input.value || '').trim().slice(0, 10);
  }

  function ensureEditEndAfterStart(startInput, endInput) {
    if (!startInput || !endInput) return;
    var today = todayIsoLocal();
    var start = readEditIsoDate(startInput);
    var minEnd = dayAfterIsoLocal(start) || dayAfterIsoLocal(today);
    if (!minEnd) return;
    if (endInput._flatpickr) endInput._flatpickr.set('minDate', minEnd);
    else endInput.setAttribute('min', minEnd);
    var end = readEditIsoDate(endInput);
    if (!end || end <= start) setEditDateFieldValue(endInput, minEnd);
  }

  function attachStopDatePickers(row) {
    if (!row || !global.DatePickers) return;
    var today = todayIsoLocal();
    var arrIn = row.querySelector('input[data-field="arrival_date"]');
    var depIn = row.querySelector('input[data-field="departure_date"]');
    var retIn = row.querySelector('input[data-field="return_date"]');

    function bubbleChange(el) {
      if (!el) return;
      try {
        el.dispatchEvent(new Event('change', { bubbles: true }));
      } catch (err) {
        /* ignore */
      }
    }

    // Arrival → departure: departure is at least the day after arrival.
    if (arrIn && depIn) {
      var bubbling = false;
      global.DatePickers.initLinked(arrIn, depIn, {
        forceFillEnd: true,
        allowSameDay: false,
        minDate: today,
        appendTo: document.body,
        isSilent: function () {
          return editDatesSilent || bubbling;
        },
        onStartChange: function () {
          // Arrival change already bubbles from flatpickr; notify cascade for filled departure.
          if (bubbling) return;
          bubbling = true;
          try {
            bubbleChange(depIn);
          } finally {
            bubbling = false;
          }
        }
      });
    } else {
      if (arrIn) attachEditDatePicker(arrIn, { minDate: today });
      if (depIn) attachEditDatePicker(depIn, { minDate: today });
    }
    if (retIn) {
      attachEditDatePicker(retIn, { minDate: today });
      if (!retIn._flatpickr) retIn.setAttribute('min', today);
    }
  }

  function initEditTripBoundDatePickers(startInput, endInput, hooks) {
    if (!startInput || !endInput) return null;
    hooks = hooks || {};
    if (!global.DatePickers) {
      console.error('DatePickers module missing');
      return null;
    }
    // Trip bounds: end must be after start; always autofill end when start changes.
    return global.DatePickers.initLinked(startInput, endInput, {
      forceFillEnd: true,
      allowSameDay: false,
      appendTo: document.body,
      isSilent: function () {
        return editDatesSilent;
      },
      onStartChange: function () {
        if (typeof hooks.onStartChange === 'function') hooks.onStartChange();
      },
      onEndChange: function () {
        if (typeof hooks.onEndChange === 'function') hooks.onEndChange();
      }
    });
  }

  //Trip start follows first stop; end follows last destination departure.
  //Return-home shows a single date mirrored from trip end.
  function syncTripBoundsFromStops(listEl) {
    if (!listEl) return;
    var modalRoot = listEl.closest('.trip-details-modal-overlay');
    var tripStart = modalRoot ? modalRoot.querySelector('#editTripStartDate') : null;
    var tripEnd = modalRoot ? modalRoot.querySelector('#editTripEndDate') : null;
    if (!tripStart || !tripEnd) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    if (!rows.length) return;
    var first = rows[0];
    var fa = first.querySelector('[data-field="arrival_date"]');
    var fd = first.querySelector('[data-field="departure_date"]');
    var startVal = (fa && fa.value) ? fa.value : fd && fd.value ? fd.value : '';

    var endSource = rows[rows.length - 1];
    if (isReturnHomeEditRow(endSource) && rows.length >= 2) {
      endSource = rows[rows.length - 2];
    }
    var la = endSource.querySelector('[data-field="arrival_date"]');
    var ld = endSource.querySelector('[data-field="departure_date"]');
    var endVal = (ld && ld.value) ? ld.value : la && la.value ? la.value : '';

    if (startVal) setEditDateFieldValue(tripStart, String(startVal).slice(0, 10));
    if (endVal) setEditDateFieldValue(tripEnd, String(endVal).slice(0, 10));

    // Never leave end empty or on/before start after stop sync (plan-new-trip rule).
    ensureEditEndAfterStart(tripStart, tripEnd);

    // Keep linked flatpickr minDates in sync after stop-driven bound changes.
    var linked = modalRoot && modalRoot._tripDateLink;
    if (linked && typeof linked.sync === 'function') {
      linked.sync(tripStart.value || '', tripEnd.value || '');
    }

    var last = rows[rows.length - 1];
    if (isReturnHomeEditRow(last) && tripEnd.value) {
      var retIn = last.querySelector('[data-field="return_date"]');
      if (retIn) setEditDateFieldValue(retIn, tripEnd.value);
    }
  }

  //Slide every stop date by deltaDays so the itinerary stays consistent
  function shiftAllEditStopDates(listEl, deltaDays, skipBoundSync) {
    if (!listEl || !deltaDays) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    for (var i = 0; i < rows.length; i++) {
      var arrIn = rows[i].querySelector('[data-field="arrival_date"]');
      var depIn = rows[i].querySelector('[data-field="departure_date"]');
      if (arrIn && arrIn.value) {
        var arr = parseEditDay(arrIn.value);
        if (arr) setEditDateFieldValue(arrIn, fmtEditDay(addEditDaysUTC(arr, deltaDays)));
      }
      if (depIn && depIn.value) {
        var dep = parseEditDay(depIn.value);
        if (dep) setEditDateFieldValue(depIn, fmtEditDay(addEditDaysUTC(dep, deltaDays)));
      }
    }
    // When start-linking already set trip end, skip sync so it cannot overwrite the filled end.
    if (!skipBoundSync) syncTripBoundsFromStops(listEl);
  }

  function chainEditStopDates(listEl, fromIndex, skipBoundSync) {
    if (!listEl) return;
    var rows = listEl.querySelectorAll('.trip-stop-card');
    if (rows.length <= 1) return;
    fromIndex = (typeof fromIndex === 'number' && fromIndex >= 1) ? fromIndex : 1;

    function parseDay(s) {
      return parseEditDay(s);
    }

    function fmt(dt) {
      return fmtEditDay(dt);
    }

    function addDaysUTC(dt, n) {
      return addEditDaysUTC(dt, n);
    }

    function dayDiff(a, b) {
      return dayDiffNonNeg(a, b);
    }

    var states = [];
    for (var i = 0; i < rows.length; i++) {
      var arrIn = rows[i].querySelector('[data-field="arrival_date"]');
      var depIn = rows[i].querySelector('[data-field="departure_date"]');
      states.push({
        arrIn: arrIn,
        depIn: depIn,
        arrStr: fromDateInputVal(arrIn && arrIn.value) || '',
        depStr: fromDateInputVal(depIn && depIn.value) || ''
      });
    }

    var out = [];
    for (var j = 0; j < states.length; j++) {
      out.push({ arrStr: states[j].arrStr, depStr: states[j].depStr });
    }

    for (var k = fromIndex; k < states.length; k++) {
      var prevOut = out[k - 1];
      var s = states[k];
      var prevExit = prevOut.depStr ? parseDay(prevOut.depStr) : (prevOut.arrStr ? parseDay(prevOut.arrStr) : null);
      if (!prevExit) continue;

      if (!s.arrStr && !s.depStr) continue;

      var oldArr = s.arrStr ? parseDay(s.arrStr) : null;
      var oldDep = s.depStr ? parseDay(s.depStr) : null;
      var newArr = prevExit;
      var newDepStr = '';

      if (oldArr && oldDep) {
        newDepStr = fmt(addDaysUTC(newArr, dayDiff(oldArr, oldDep)));
      } else if (oldDep && !oldArr) {
        var newDep = oldDep >= newArr ? oldDep : newArr;
        newDepStr = fmt(newDep);
      } else {
        newDepStr = '';
      }

      out[k].arrStr = fmt(newArr);
      out[k].depStr = newDepStr;

      var na = parseDay(out[k].arrStr);
      var nd = out[k].depStr ? parseDay(out[k].depStr) : null;
      if (na && nd && nd < na) {
        out[k].depStr = out[k].arrStr;
      }
    }

    for (var w = 0; w < states.length; w++) {
      if (states[w].arrIn) setEditDateFieldValue(states[w].arrIn, out[w].arrStr || '');
      if (states[w].depIn) setEditDateFieldValue(states[w].depIn, out[w].depStr || '');
    }
    if (!skipBoundSync) syncTripBoundsFromStops(listEl);
  }

  function makeStopsListSortable(listEl) {
    global.TripStopReorder.makeSortable(listEl, {
      onReorder: function (list) {
        renumberEditStops(list);
        chainEditStopDates(list);
      }
    });
  }

  function buildEditStopRowEl(stop, options) {
    stop = stop || {};
    options = options || {};
    var isReturnHome = !!options.isReturnHome;
    var row = document.createElement('div');
    row.className = 'trip-stop-card';
    if (stop.id != null) row.setAttribute('data-stop-id', String(stop.id));
    if (isReturnHome) row.setAttribute('data-return-home', '1');

    var num = document.createElement('div');
    num.className = 'trip-stop-number';
    num.textContent = '1';

    var details = document.createElement('div');
    details.className = 'trip-stop-details';

    var actions = document.createElement('div');
    actions.className = 'trip-details-edit-stop-actions';

    var rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'btn-cancel';
    rm.setAttribute('data-i18n', 'plannedTrips.editRemoveStop');
    rm.textContent = plannedTripsT('editRemoveStop', 'Remove');
    actions.appendChild(rm);

    var grid = document.createElement('div');
    grid.className = 'trip-details-form-grid';

    function mkField(full, i18nSuffix, shortKey, fieldName, type, val, isTa) {
      var wrap = document.createElement('div');
      wrap.className = 'trip-details-form-field' + (full ? ' trip-details-form-field--full' : '');
      var lab = document.createElement('label');
      lab.setAttribute('data-i18n', 'plannedTrips.' + i18nSuffix);
      lab.textContent = plannedTripsT(shortKey, fieldName);
      var inp;
      if (isTa) {
        inp = document.createElement('textarea');
        inp.className = 'trip-details-textarea';
        inp.rows = 2;
      } else {
        inp = document.createElement('input');
        inp.className = 'trip-details-text-input';
        inp.type = type || 'text';
      }
      inp.setAttribute('data-field', fieldName);
      if (val != null && val !== '') inp.value = String(val);
      wrap.appendChild(lab);
      wrap.appendChild(inp);
      return wrap;
    }

    grid.appendChild(mkField(false, 'editFieldPlace', 'editFieldPlace', 'place_name', 'text', stop.place_name, false));
    var countryField = mkField(
      false,
      'editFieldCountry',
      'editFieldCountry',
      'country',
      'text',
      countryDisplay(stop.country) || stop.country,
      false
    );
    grid.appendChild(countryField);
    var countryInput = countryField.querySelector('[data-field="country"]');
    if (countryInput && global.Countries && global.Countries.mountAutocomplete) {
      if (stop.country) countryInput.dataset.countryCode = String(stop.country).trim().toUpperCase();
      global.Countries.mountAutocomplete(countryInput);
    }
    if (isReturnHome) {
      var returnDateVal =
        options.tripEndDate || stop.arrival_date || stop.departure_date || '';
      grid.appendChild(
        mkField(
          false,
          'editFieldReturnDate',
          'editFieldReturnDate',
          'return_date',
          'text',
          toDateInputValue(returnDateVal),
          false
        )
      );
    } else {
      grid.appendChild(mkField(false, 'editFieldArrival', 'editFieldArrival', 'arrival_date', 'text', toDateInputValue(stop.arrival_date), false));
      grid.appendChild(mkField(false, 'editFieldDeparture', 'editFieldDeparture', 'departure_date', 'text', toDateInputValue(stop.departure_date), false));
    }
    grid.appendChild(mkField(true, 'editFieldTransport', 'editFieldTransport', 'transport_from_last', 'text', stop.transport_from_last, false));
    if (!isReturnHome) {
      grid.appendChild(mkField(true, 'editFieldActivities', 'editFieldActivities', 'activities', null, stop.activities, true));
    }

    details.appendChild(actions);
    details.appendChild(grid);

    row.appendChild(global.TripStopReorder.buildDragHandle(isReturnHome));
    row.appendChild(num);
    row.appendChild(details);

    rm.addEventListener('click', function () {
      var listEl = row.closest('#editStopsList');
      row.remove();
      renumberEditStops(listEl);
      chainEditStopDates(listEl);
    });

    if (!options.skipDatePickers) attachStopDatePickers(row);
    return row;
  }

  function readStopRow(row, orderIndex, tripEndDate) {
    var placeIn = row.querySelector('[data-field="place_name"]');
    var place = placeIn && placeIn.value.trim();
    var countryIn = row.querySelector('[data-field="country"]');
    var transportIn = row.querySelector('[data-field="transport_from_last"]');
    var activitiesIn = row.querySelector('[data-field="activities"]');
    var arrIn = row.querySelector('[data-field="arrival_date"]');
    var depIn = row.querySelector('[data-field="departure_date"]');
    var retIn = row.querySelector('[data-field="return_date"]');
    var sid = row.getAttribute('data-stop-id');
    var isReturnHome = isReturnHomeEditRow(row);
    var endIso = isReturnHome
      ? fromDateInputVal(retIn && retIn.value) || fromDateInputVal(tripEndDate)
      : fromDateInputVal(tripEndDate);
    return {
      id: sid ? parseInt(sid, 10) : null,
      stop_order: orderIndex,
      place_name: place,
      country: trimOrNull(
        (global.Countries && global.Countries.getCode(countryIn)) ||
        (countryIn && countryIn.value)
      ),
      arrival_date: isReturnHome ? endIso : fromDateInputVal(arrIn && arrIn.value),
      departure_date: isReturnHome ? endIso : fromDateInputVal(depIn && depIn.value),
      transport_from_last: trimOrNull(transportIn && transportIn.value),
      activities: isReturnHome ? null : trimOrNull(activitiesIn && activitiesIn.value)
    };
  }

  async function saveTripEdits(tripId, modal, originalStopIds) {
    var titleIn = modal.querySelector('#editTripTitle');
    var saveBtn = modal.querySelector('#tripEditSaveBtn');
    var title = titleIn && titleIn.value.trim();
    if (!title) {
      showError(plannedTripsT('editTitleRequired', 'Trip title is required.'));
      return false;
    }

    var listEl = modal.querySelector('#editStopsList');
    var rows = listEl ? listEl.querySelectorAll('.trip-stop-card') : [];
    var endDateIn = modal.querySelector('#editTripEndDate');

    if (!rows.length) {
      showError(plannedTripsT('editStopsRequired', 'A trip must have at least one stop.'));
      return false;
    }

    var collected = [];
    var endPreview = fromDateInputVal(endDateIn && endDateIn.value);
    var lastRow = rows[rows.length - 1];
    if (isReturnHomeEditRow(lastRow)) {
      var retField = lastRow.querySelector('[data-field="return_date"]');
      if (retField && retField.value) {
        endPreview = fromDateInputVal(retField.value);
        if (endDateIn) setEditDateFieldValue(endDateIn, retField.value);
      }
    }
    for (var i = 0; i < rows.length; i++) {
      var data = readStopRow(rows[i], i + 1, endPreview);
      if (!data.place_name) {
        showError(plannedTripsT('editStopPlaceRequired', 'Each stop must have a place name.'));
        return false;
      }
      collected.push(data);
    }

    var startCityIn = modal.querySelector('#editTripStartCity');
    var startDateIn = modal.querySelector('#editTripStartDate');
    var peopleIn = modal.querySelector('#editTripPeople');
    var peopleParsed = peopleIn ? parseInt(peopleIn.value, 10) : NaN;
    if (!Number.isFinite(peopleParsed) || peopleParsed < 1) {
      showError(plannedTripsT('editPeopleInvalid', 'Travellers must be at least 1.'));
      return false;
    }

    var startDateVal = fromDateInputVal(startDateIn && startDateIn.value);
    var endDateVal = endPreview;
    if (!startDateVal || !endDateVal) {
      showError(plannedTripsT('editDatesRequired', 'Please select both start and end dates.'));
      return false;
    }
    if (startDateVal < todayIsoLocal()) {
      showError(plannedTripsT('editStartDateNotInPast', 'Start date cannot be before today.'));
      return false;
    }
    if (endDateVal <= startDateVal) {
      showError(plannedTripsT('editEndDateAfterStart', 'End date must be after start date.'));
      return false;
    }

    var tripBody = {
      title: title,
      start_city: trimOrNull(startCityIn && startCityIn.value),
      start_date: fromDateInputVal(startDateIn && startDateIn.value),
      end_date: endPreview,
      people: peopleParsed
    };

    // Last stop matching start city is return-home: pin dates to trip end.
    if (collected.length && tripBody.start_city && tripBody.end_date) {
      var last = collected[collected.length - 1];
      if (placeNamesMatch(last.place_name, tripBody.start_city)) {
        last.arrival_date = tripBody.end_date;
        last.departure_date = tripBody.end_date;
      }
    }

    if (saveBtn) saveBtn.disabled = true;

    try {
      var putRes = await fetch('/api/planned-trips/' + tripId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tripBody)
      });
      if (!putRes.ok) throw new Error('trip ' + putRes.status);

      var currentIds = collected
        .filter(function (c) {
          return c.id != null;
        })
        .map(function (c) {
          return c.id;
        });

      for (var j = 0; j < originalStopIds.length; j++) {
        var oid = originalStopIds[j];
        if (currentIds.indexOf(oid) === -1) {
          var delRes = await fetch('/api/trip-stops/' + oid, { method: 'DELETE' });
          if (!delRes.ok && delRes.status !== 404) throw new Error('delete stop ' + oid);
        }
      }

      for (var k = 0; k < collected.length; k++) {
        var c = collected[k];
        var body = {
          place_name: c.place_name,
          country: c.country,
          stop_order: c.stop_order,
          arrival_date: c.arrival_date,
          departure_date: c.departure_date,
          transport_from_last: c.transport_from_last,
          activities: c.activities
        };
        if (c.id) {
          var ur = await fetch('/api/trip-stops/' + c.id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          });
          if (!ur.ok) throw new Error('update stop ' + c.id);
        } else {
          var postBody = Object.assign({ trip_id: tripId }, body);
          var pr = await fetch('/api/trip-stops', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(postBody)
          });
          if (!pr.ok) throw new Error('create stop');
        }
      }

      await deps.refreshList();
      return true;
    } catch (e) {
      console.error('saveTripEdits', e);
      showError(plannedTripsT('editSaveError', 'Could not save changes.') + (e && e.message ? ' (' + e.message + ')' : ''));
      return false;
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  async function open(tripId) {
    try {
      destroyPopups();

      var response = await fetch('/api/planned-trips/' + tripId);
      if (!response.ok) throw new Error('load');
      var trip = await response.json();

      var template = document.getElementById('tripEditModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var stops = (trip.stops || [])
        .slice()
        .sort(function (a, b) {
          return (a.stop_order || 0) - (b.stop_order || 0);
        });
      var originalStopIds = stops
        .map(function (s) {
          return s.id;
        })
        .filter(function (id) {
          return id != null;
        });

      var titleIn = modal.querySelector('#editTripTitle');
      var startCityIn = modal.querySelector('#editTripStartCity');
      var startDateIn = modal.querySelector('#editTripStartDate');
      var endDateIn = modal.querySelector('#editTripEndDate');
      var peopleIn = modal.querySelector('#editTripPeople');
      var listEl = modal.querySelector('#editStopsList');
      if (titleIn) titleIn.value = trip.title || '';
      if (startCityIn) startCityIn.value = trip.start_city || '';
      var todayOpen = todayIsoLocal();
      var openStart = toDateInputValue(trip.start_date);
      var openEnd = toDateInputValue(trip.end_date);
      var openStartDelta = 0;
      if (openStart && openStart < todayOpen) {
        openStartDelta = dayDiffSigned(parseEditDay(openStart), parseEditDay(todayOpen));
        openStart = todayOpen;
      }
      var openMinEnd = dayAfterIsoLocal(openStart) || dayAfterIsoLocal(todayOpen);
      if (!openEnd || (openStart && openEnd <= openStart)) openEnd = openMinEnd || '';
      if (startDateIn) startDateIn.value = openStart;
      if (endDateIn) endDateIn.value = openEnd;
      if (peopleIn) {
        var peopleVal = parseInt(trip.people, 10);
        peopleIn.value = String(Number.isFinite(peopleVal) && peopleVal > 0 ? peopleVal : 1);
      }

      if (listEl) {
        listEl.innerHTML = '';
        stops.forEach(function (s, i) {
          listEl.appendChild(
            buildEditStopRowEl(s, {
              isReturnHome: isReturnHomeEditStop(s, trip.start_city, i, stops.length),
              tripEndDate: trip.end_date
            })
          );
        });
        renumberEditStops(listEl);
        makeStopsListSortable(listEl);
        if (openStartDelta) shiftAllEditStopDates(listEl, openStartDelta);
        function onEditStopsDateField(e) {
          if (editDatesSilent) return;
          var t = e.target;
          if (!t || !t.matches) return;
          if (t.matches('input[data-field="return_date"]')) {
            var oldEnd = parseEditDay(prevTripEnd);
            var newEnd = parseEditDay(t.value);
            var retDelta = dayDiffSigned(oldEnd, newEnd);
            if (endDateIn) setEditDateFieldValue(endDateIn, t.value || '');
            if (retDelta) shiftAllEditStopDates(listEl, retDelta);
            else syncTripBoundsFromStops(listEl);
            prevTripStart = startDateIn ? startDateIn.value : '';
            prevTripEnd = endDateIn ? endDateIn.value : '';
            return;
          }
          if (!t.matches('input[data-field="arrival_date"], input[data-field="departure_date"]')) return;
          var row = t.closest('.trip-stop-card');
          var rows = Array.prototype.slice.call(listEl.querySelectorAll('.trip-stop-card'));
          var idx = rows.indexOf(row);
          if (idx === -1) {
            syncTripBoundsFromStops(listEl);
            return;
          }
          // Cascade the edit forward onto later stops (chainEditStopDates also
          // syncs the trip start/end fields at the end, so no separate call needed).
          chainEditStopDates(listEl, idx + 1);
          prevTripStart = startDateIn ? startDateIn.value : '';
          prevTripEnd = endDateIn ? endDateIn.value : '';
        }
        listEl.addEventListener('change', onEditStopsDateField);
      }

      //Moving trip start/end slides every stop by the same delta so middle stops stay aligned (only updating first/last left them stale).
      var prevTripStart = startDateIn ? startDateIn.value : '';
      var prevTripEnd = endDateIn ? endDateIn.value : '';
      function applyEditStartBoundChange() {
        if (editDatesSilent) return;
        if (!listEl || !startDateIn) return;
        var rows = listEl.querySelectorAll('.trip-stop-card');
        if (!rows.length) return;
        var oldStart = parseEditDay(prevTripStart);
        var newStart = parseEditDay(startDateIn.value);
        var startDelta = dayDiffSigned(oldStart, newStart);
        // Never sync trip bounds from stops here — end is owned by start→end linking.
        if (startDelta) shiftAllEditStopDates(listEl, startDelta, true);
        else {
          var first = rows[0];
          var firstField = first.querySelector('[data-field="arrival_date"]') ||
            first.querySelector('[data-field="departure_date"]');
          if (firstField) setEditDateFieldValue(firstField, startDateIn.value);
          chainEditStopDates(listEl, 1, true);
        }
        prevTripStart = startDateIn.value || '';
        prevTripEnd = endDateIn ? endDateIn.value : '';
      }
      function applyEditEndBoundChange() {
        if (editDatesSilent) return;
        if (!listEl || !endDateIn) return;
        var rows = listEl.querySelectorAll('.trip-stop-card');
        if (!rows.length) return;
        var oldEnd = parseEditDay(prevTripEnd);
        var newEnd = parseEditDay(endDateIn.value);
        var endDelta = dayDiffSigned(oldEnd, newEnd);
        if (endDelta) {
          shiftAllEditStopDates(listEl, endDelta);
        } else {
          var endRow = rows[rows.length - 1];
          if (isReturnHomeEditRow(endRow) && rows.length >= 2) {
            endRow = rows[rows.length - 2];
          }
          var pinDep = endRow.querySelector('[data-field="departure_date"]');
          if (pinDep) setEditDateFieldValue(pinDep, endDateIn.value);
        }
        ensureEditEndAfterStart(startDateIn, endDateIn);
        prevTripStart = startDateIn ? startDateIn.value : '';
        prevTripEnd = endDateIn.value || '';
      }

      try {
        modal._tripDateLink = initEditTripBoundDatePickers(startDateIn, endDateIn, {
          onStartChange: applyEditStartBoundChange,
          onEndChange: applyEditEndBoundChange
        });
      } catch (err) {
        console.error('initEditTripBoundDatePickers', err);
      }

      if (global.i18n && typeof global.i18n.applyToPage === 'function') {
        global.i18n.applyToPage(modal);
      }

      var closeBtn = modal.querySelector('.trip-details-close');
      if (closeBtn && global.i18n && typeof global.i18n.t === 'function') {
        closeBtn.setAttribute('aria-label', global.i18n.t('plannedTrips.editCloseAria'));
      } else if (closeBtn) {
        closeBtn.setAttribute('aria-label', 'Close');
      }

      var addBtn = modal.querySelector('#editAddStopBtn');
      if (addBtn && listEl) {
        addBtn.addEventListener('click', function () {
          var existing = listEl.querySelectorAll('.trip-stop-card');
          var last = existing.length ? existing[existing.length - 1] : null;
          var insertBefore = last && isReturnHomeEditRow(last) ? last : null;
          var prevRow = insertBefore
            ? existing.length >= 2
              ? existing[existing.length - 2]
              : null
            : last;

          // New stop arrival = previous stop's departure (end date).
          var prevDep = prevRow
            ? readEditIsoDate(prevRow.querySelector('[data-field="departure_date"]')) ||
              readEditIsoDate(prevRow.querySelector('[data-field="arrival_date"]')) ||
              readEditIsoDate(prevRow.querySelector('[data-field="return_date"]'))
            : '';
          var arrivalSeed =
            prevDep || readEditIsoDate(startDateIn) || todayIsoLocal();
          // Departure = day after arrival (trip stops are at least overnight).
          var departureSeed =
            global.DatePickers && global.DatePickers.dayAfterIso
              ? global.DatePickers.dayAfterIso(arrivalSeed)
              : global.DatePickers && global.DatePickers.minEndFromStart
                ? global.DatePickers.minEndFromStart(arrivalSeed, false)
                : arrivalSeed;

          var newRow = buildEditStopRowEl(
            {
              arrival_date: arrivalSeed,
              departure_date: departureSeed
            },
            { skipDatePickers: true }
          );

          if (insertBefore) listEl.insertBefore(newRow, insertBefore);
          else listEl.appendChild(newRow);
          renumberEditStops(listEl);
          attachStopDatePickers(newRow);
          syncTripBoundsFromStops(listEl);
          if (global.i18n && typeof global.i18n.applyToPage === 'function') {
            global.i18n.applyToPage(newRow);
          }
        });
      }

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        destroyEditDatePickers(modal);
        modal.remove();
      }

      var saveBtn = modal.querySelector('#tripEditSaveBtn');
      var cancelBtn = modal.querySelector('#tripEditCancelBtn');
      var modalBox = modal.querySelector('#tripEditModalBox');
      var origIdsCopy = originalStopIds.slice();

      if (saveBtn) {
        saveBtn.addEventListener('click', function () {
          saveTripEdits(tripId, modal, origIdsCopy).then(function (ok) {
            if (ok) removeModal();
          });
        });
      }
      if (cancelBtn) cancelBtn.addEventListener('click', removeModal);
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
    } catch (err) {
      console.error('openTripEditModal', err);
      showError(plannedTripsT('editLoadError', 'Could not load trip for editing.'));
    }
  }

  global.TripEditModal = {
    init: init,
    open: open
  };
})(window);
