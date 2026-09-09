(function (global) {
  'use strict';

  function toDateInputValue(d) {
    if (!d) return '';
    var s = String(d);
    if (s.length >= 10) return s.slice(0, 10);
    return s;
  }

  function fromDateInputVal(v) {
    if (!v || !String(v).trim()) return null;
    return String(v).trim().slice(0, 10);
  }

  function trimOrNull(v) {
    if (v == null) return null;
    var t = String(v).trim();
    return t ? t : null;
  }

  function parseEditDay(s) {
    if (!s || String(s).length < 10) return null;
    var p = String(s).slice(0, 10).split('-');
    var y = parseInt(p[0], 10);
    var m = parseInt(p[1], 10) - 1;
    var d = parseInt(p[2], 10);
    if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
    var dt = new Date(Date.UTC(y, m, d));
    return isNaN(dt.getTime()) ? null : dt;
  }

  function fmtEditDay(dt) {
    if (!dt) return '';
    var mo = dt.getUTCMonth() + 1;
    var day = dt.getUTCDate();
    return dt.getUTCFullYear() + '-' + (mo < 10 ? '0' : '') + mo + '-' + (day < 10 ? '0' : '') + day;
  }

  function addEditDaysUTC(dt, n) {
    var x = new Date(dt.getTime());
    x.setUTCDate(x.getUTCDate() + n);
    return x;
  }

  function dayDiffSigned(a, b) {
    if (!a || !b) return 0;
    return Math.round((b.getTime() - a.getTime()) / 86400000);
  }

  function dayDiffNonNeg(a, b) {
    var ms = dayDiffSigned(a, b);
    return ms >= 0 ? ms : 0;
  }

  function placeNamesMatch(a, b) {
    var x = String(a || '').trim().toLowerCase();
    var y = String(b || '').trim().toLowerCase();
    return !!(x && y && x === y);
  }

  function todayIsoLocal() {
    return global.DatePickers ? global.DatePickers.todayIso() : (function () {
      var now = new Date();
      var y = now.getFullYear();
      var m = String(now.getMonth() + 1).padStart(2, '0');
      var d = String(now.getDate()).padStart(2, '0');
      return y + '-' + m + '-' + d;
    })();
  }

  function dayAfterIsoLocal(isoDate) {
    return global.DatePickers ? global.DatePickers.dayAfterIso(isoDate) : null;
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  global.TripDateUtils = {
    toDateInputValue: toDateInputValue,
    fromDateInputVal: fromDateInputVal,
    trimOrNull: trimOrNull,
    parseEditDay: parseEditDay,
    fmtEditDay: fmtEditDay,
    addEditDaysUTC: addEditDaysUTC,
    dayDiffSigned: dayDiffSigned,
    dayDiffNonNeg: dayDiffNonNeg,
    placeNamesMatch: placeNamesMatch,
    todayIsoLocal: todayIsoLocal,
    dayAfterIsoLocal: dayAfterIsoLocal,
    escapeHtml: escapeHtml
  };
})(window);
