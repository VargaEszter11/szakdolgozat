(function () {
  var DEFAULT_IMAGE = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80';

  function normalizeTrip(trip) {
    // Map API response fields to frontend fields
    // API provides: id, user_id, title, start_date, end_date, start_city, stops
    return {
      id: trip.id,
      destination: trip.title || 'Unknown destination',
      startDate: formatApiDate(trip.start_date),
      endDate: formatApiDate(trip.end_date),
      startDateSort: trip.start_date || null,
      stopCount: trip.stops ? trip.stops.length : 0,
      image: DEFAULT_IMAGE
    };
  }

  function stopsSummaryLine(n) {
    var t = window.i18n && window.i18n.t ? window.i18n.t.bind(window.i18n) : null;
    if (n === 1) return t ? t('plannedTrips.stopsOne') : '1 stop';
    return t ? t('plannedTrips.stopsMany').replace(/\{\{n\}\}/g, String(n)) : (n + ' stops');
  }

  var LOCALE_MAP = { en: 'en-GB', hu: 'hu-HU', de: 'de-DE' };

  function formatApiDate(dateStr) {
    if (!dateStr) return '—';
    try {
      var locale = LOCALE_MAP[localStorage.getItem('language')] || 'en-GB';
      return new Date(dateStr).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  }

  var NOMINATIM_DELAY_MS = 1100;

  function plannedTripsT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      var v = window.i18n.t('plannedTrips.' + key);
      if (v && v.indexOf('plannedTrips.' + key) !== 0) return v;
    }
    return fallback;
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function nominatimGeocode(query) {
    if (!query || !String(query).trim()) return Promise.resolve(null);
    var url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams({
      q: String(query).trim(),
      format: 'json',
      limit: '1'
    });
    return fetch(url, { headers: { Accept: 'application/json' } })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        return Array.isArray(data) && data.length ? data[0] : null;
      })
      .catch(function () {
        return null;
      });
  }

  function labelForStop(stop) {
    var ord = stop.stop_order != null ? String(stop.stop_order) : '?';
    return ord + '. ' + (stop.place_name || '') + (stop.country ? ', ' + stop.country : '');
  }

  /**
   * Ordered points: starting city (if any), then each stop in stop_order.
   * Uses stored lat/lon when present; otherwise Nominatim (throttled).
   */
  function buildAllRoutePoints(trip, orderedStops) {
    var points = [];
    var hadNetworkRequest = false;
    var chain = Promise.resolve();

    function beforeNetwork() {
      var p = hadNetworkRequest ? sleep(NOMINATIM_DELAY_MS) : Promise.resolve();
      hadNetworkRequest = true;
      return p;
    }

    if (trip.start_city && String(trip.start_city).trim()) {
      var startQuery = String(trip.start_city).trim();
      var startPopup = plannedTripsT('mapStartCityLabel', 'Start') + ': ' + startQuery;
      chain = chain
        .then(function () {
          return beforeNetwork().then(function () {
            return nominatimGeocode(startQuery);
          });
        })
        .then(function (hit) {
          if (hit) {
            points.push({
              lat: parseFloat(hit.lat),
              lng: parseFloat(hit.lon),
              label: startPopup,
              kind: 'start',
              startCityName: startQuery
            });
          }
        });
    }

    for (var i = 0; i < orderedStops.length; i++) {
      (function (stop) {
        chain = chain.then(function () {
          var lat = stop.latitude;
          var lon = stop.longitude;
          if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
            points.push({
              lat: lat,
              lng: lon,
              label: labelForStop(stop),
              kind: 'stop',
              order: stop.stop_order
            });
            return undefined;
          }
          var q = (stop.place_name || '').trim();
          if (!q) return undefined;
          if (stop.country) q += ', ' + String(stop.country).trim();
          return beforeNetwork()
            .then(function () {
              return nominatimGeocode(q);
            })
            .then(function (hit) {
              if (hit) {
                points.push({
                  lat: parseFloat(hit.lat),
                  lng: parseFloat(hit.lon),
                  label: labelForStop(stop),
                  kind: 'stop',
                  order: stop.stop_order
                });
              }
            });
        });
      })(orderedStops[i]);
    }

    return chain.then(function () {
      return points;
    });
  }

  function destroyTripMap(mapEl) {
    if (!mapEl || !mapEl._leaflet_map) return;
    try {
      mapEl._leaflet_map.remove();
    } catch (e) {
      /* ignore */
    }
    mapEl._leaflet_map = null;
    mapEl.innerHTML = '';
  }

  function initTripDetailsMap(modal, trip, orderedStops) {
    var section = modal.querySelector('#tripDetailsMapSection');
    var mapEl = modal.querySelector('#tripDetailsMap');
    var noteEl = modal.querySelector('#tripDetailsMapNote');
    if (!section || !mapEl || !noteEl) return Promise.resolve();

    destroyTripMap(mapEl);

    if (typeof L === 'undefined') {
      section.classList.add('hidden');
      return Promise.resolve();
    }

    var hasStart = Boolean(trip.start_city && String(trip.start_city).trim());
    if (!hasStart && orderedStops.length === 0) {
      section.classList.add('hidden');
      return Promise.resolve();
    }

    noteEl.classList.remove('hidden');
    noteEl.textContent = plannedTripsT('mapLoading', 'Locating cities on the map…');

    return buildAllRoutePoints(trip, orderedStops)
      .then(function (points) {
        noteEl.textContent = '';
        noteEl.classList.add('hidden');
        if (points.length === 0) {
          section.classList.add('hidden');
          return;
        }
        var startResolved = points.some(function (p) {
          return p.kind === 'start';
        });
        var resolvedStops = points.filter(function (p) {
          return p.kind === 'stop';
        }).length;
        var showPartial =
          resolvedStops < orderedStops.length || (hasStart && !startResolved);
        renderTripMap(modal, mapEl, noteEl, section, points, showPartial);
      })
      .catch(function (err) {
        console.error('Trip map:', err);
        noteEl.textContent = '';
        noteEl.classList.add('hidden');
        section.classList.add('hidden');
      });
  }

  function renderTripMap(modal, mapEl, noteEl, section, points, showPartialNote) {
    section.classList.remove('hidden');

    var latlngs = points.map(function (p) {
      return [p.lat, p.lng];
    });
    var accent = getComputedStyle(modal).getPropertyValue('--pt-popup-accent').trim() || '#6366f1';

    var map = L.map(mapEl, {
      zoomControl: true,
      scrollWheelZoom: false
    });
    mapEl._leaflet_map = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    if (latlngs.length >= 2) {
      L.polyline(latlngs, {
        color: accent,
        weight: 3,
        opacity: 0.92
      }).addTo(map);
    }

    points.forEach(function (p) {
      var isStart = p.kind === 'start';
      var popupEl = document.createElement('div');
      if (isStart) {
        popupEl.style.textAlign = 'center';
        var sub = document.createElement('div');
        sub.style.fontSize = '0.72rem';
        sub.style.fontWeight = '600';
        sub.style.textTransform = 'uppercase';
        sub.style.letterSpacing = '0.06em';
        sub.style.color = 'var(--pt-popup-muted, #64748b)';
        sub.textContent = plannedTripsT('mapStartMarkerSubtitle', 'Starting city');
        var name = document.createElement('div');
        name.style.fontWeight = '700';
        name.style.fontSize = '1rem';
        name.style.marginTop = '0.35rem';
        name.style.color = 'var(--pt-popup-text, #0f172a)';
        name.textContent = p.startCityName || (p.label && p.label.indexOf(': ') >= 0 ? p.label.split(': ').slice(1).join(': ') : p.label);
        popupEl.appendChild(sub);
        popupEl.appendChild(name);
      } else {
        popupEl.style.fontWeight = '600';
        popupEl.style.fontSize = '0.9rem';
        popupEl.textContent = p.label;
      }
      var markerOpts = isStart
        ? {
            radius: 11,
            color: '#ffffff',
            weight: 3,
            fillColor: accent,
            fillOpacity: 1
          }
        : {
            radius: 8,
            color: accent,
            weight: 2,
            fillColor: '#ffffff',
            fillOpacity: 1
          };
      var marker = L.circleMarker([p.lat, p.lng], markerOpts)
        .addTo(map)
        .bindPopup(popupEl, { maxWidth: 260 });

      if (isStart) {
        var cityText = (p.startCityName && String(p.startCityName).trim()) || '';
        if (cityText) {
          var tip = document.createElement('div');
          tip.className = 'trip-map-onmap-start-label';
          var kSpan = document.createElement('span');
          kSpan.className = 'trip-map-onmap-start-k';
          kSpan.textContent = plannedTripsT('mapStartCityLabel', 'Start');
          var citySpan = document.createElement('span');
          citySpan.className = 'trip-map-onmap-start-city';
          citySpan.textContent = cityText;
          tip.appendChild(kSpan);
          tip.appendChild(citySpan);
          marker.bindTooltip(tip, {
            permanent: true,
            direction: 'top',
            offset: [0, -8],
            opacity: 1,
            interactive: false,
            className: 'trip-map-start-tooltip'
          });
        }
      }
    });

    if (latlngs.length === 1) {
      map.setView(latlngs[0], 6);
    } else {
      var hasStartPoint = points.some(function (p) {
        return p.kind === 'start';
      });
      var pad = hasStartPoint ? [52, 52] : [28, 28];
      try {
        map.fitBounds(L.latLngBounds(latlngs), {
          padding: pad,
          maxZoom: 12
        });
      } catch (e) {
        console.warn('fitBounds failed, using setView fallback', e);
        map.setView(latlngs[0], 6);
      }
    }

    setTimeout(function () {
      if (!mapEl._leaflet_map) return;
      try {
        mapEl._leaflet_map.invalidateSize();
        mapEl._leaflet_map.eachLayer(function (layer) {
          try {
            if (layer.openTooltip && layer.getTooltip && layer.getTooltip()) {
              var tt = layer.getTooltip();
              if (tt && tt.options && tt.options.permanent) {
                layer.openTooltip();
              }
            }
          } catch (e2) {
            /* ignore per-layer */
          }
        });
      } catch (e) {
        /* ignore */
      }
    }, 120);

    if (showPartialNote) {
      noteEl.textContent = plannedTripsT(
        'mapPartialRoute',
        'Some stops could not be located; the line shows the cities we could find, in visit order.'
      );
      noteEl.classList.remove('hidden');
    }

    if (window.i18n && typeof window.i18n.applyToPage === 'function') {
      window.i18n.applyToPage(section);
    }

    setTimeout(function () {
      if (mapEl._leaflet_map) mapEl._leaflet_map.invalidateSize();
    }, 450);
  }

  async function getTrips() {
    // Get user_id from localStorage (set during login)
    var userId = localStorage.getItem('user_id');
    if (!userId) {
      console.warn('No user_id found. User not logged in.');
      return [];
    }

    try {
      var apiUrl = '/api/users/' + userId + '/planned-trips';
      var response = await fetch(apiUrl);

      if (!response.ok) {
        if (response.status === 404) {
          // No trips found for this user
          return [];
        }
        throw new Error('API request failed: ' + response.status);
      }

      var data = await response.json();
      // API returns array of planned trips directly
      var list = Array.isArray(data) ? data : [];
      return list.map(normalizeTrip);
    } catch (error) {
      console.error('Failed to load planned trips from API:', error);
      return [];
    }
  }

  async function deleteTrip(id) {
    try {
      var response = await fetch('/api/planned-trips/' + id, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete trip: ' + response.status);
      }

      await render();
    } catch (error) {
      console.error('Error deleting trip:', error);
      showError('Failed to delete trip: ' + error.message);
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderCard(trip) {
    return (
      '<div class="travel-log-card planned-trip-card" data-id="' + trip.id + '">' +
      '<div class="log-image-wrapper">' +
      '<img src="' + escapeHtml(trip.image || '') + '" alt="' + escapeHtml(trip.destination) + '" class="log-image" onerror="this.src=\'' + escapeHtml(DEFAULT_IMAGE) + '\';">' +
      '</div>' +
      '<div class="log-content">' +
      '<div class="log-header">' +
      '<div class="log-dest">' +
      '<svg class="icon-pin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<path d="M12 21s-6-5.686-6-10a6 6 0 1 1 12 0c0 4.314-6 10-6 10z"/>' +
      '<circle cx="12" cy="11" r="2"/>' +
      '</svg>' +
      '<h3 class="log-title">' + escapeHtml(trip.destination) + '</h3>' +
      '</div>' +
      '<div class="visited-places-card-actions">' +
      '<button type="button" class="place-delete-btn trip-edit" data-id="' + trip.id + '" title="Edit" aria-label="Edit trip">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>' +
      '</button>' +
      '<button type="button" class="place-delete-btn trip-delete" data-id="' + trip.id + '" title="Delete" aria-label="Delete trip">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>' +
      '</button>' +
      '</div>' +
      '</div>' +
      '<div class="log-date">' + escapeHtml(trip.startDate) + ' – ' + escapeHtml(trip.endDate) + '</div>' +
      '<p class="log-notes">' + escapeHtml(stopsSummaryLine(trip.stopCount || 0)) + '</p>' +
      '</div>' +
      '</div>'
    );
  }

  function sortTripsByStartDate(trips) {
    return trips.slice().sort(function (a, b) {
      var tA = a.startDateSort ? new Date(a.startDateSort).getTime() : 0;
      var tB = b.startDateSort ? new Date(b.startDateSort).getTime() : 0;
      return tA - tB;
    });
  }

  async function render() {
    var container = document.getElementById('tripCards');
    var emptyState = document.getElementById('emptyState');
    if (!container || !emptyState) return;

    var trips = await getTrips();
    var sortedTrips = sortTripsByStartDate(trips);

    if (sortedTrips.length === 0) {
      container.classList.add('hidden');
      emptyState.classList.remove('hidden');
      return;
    }

    emptyState.classList.add('hidden');
    container.classList.remove('hidden');
    container.innerHTML = sortedTrips.map(renderCard).join('');
  }

  function bindTripListActions() {
    var container = document.getElementById('tripCards');
    if (!container || container.dataset.tripListBound === '1') return;
    container.dataset.tripListBound = '1';
    container.addEventListener('click', function (e) {
      var delBtn = e.target.closest('.trip-delete');
      if (delBtn) {
        e.preventDefault();
        e.stopPropagation();
        var did = parseInt(delBtn.getAttribute('data-id'), 10);
        if (Number.isNaN(did)) return;
        showConfirm('Delete this trip?', function () { deleteTrip(did); });
        return;
      }
      var editBtn = e.target.closest('.trip-edit');
      if (editBtn) {
        e.preventDefault();
        e.stopPropagation();
        var eid = editBtn.getAttribute('data-id');
        if (eid) window.location.href = 'plan_new_trip.html?edit=' + eid;
        return;
      }
      var card = e.target.closest('.planned-trip-card');
      if (card && !e.target.closest('button, a')) {
        var cid = parseInt(card.getAttribute('data-id'), 10);
        if (!Number.isNaN(cid)) showTripDetails(cid);
      }
    });
  }

  function buildStopCard(stop) {
    var card = document.createElement('div');
    card.className = 'trip-stop-card';
    var num = document.createElement('div');
    num.className = 'trip-stop-number';
    num.textContent = stop.stop_order != null ? String(stop.stop_order) : '?';
    var details = document.createElement('div');
    details.className = 'trip-stop-details';
    var h4 = document.createElement('h4');
    h4.textContent = stop.place_name + (stop.country ? ', ' + stop.country : '');
    var info = document.createElement('div');
    info.className = 'trip-stop-info';
    if (stop.arrival_date) {
      var pArr = document.createElement('p');
      pArr.innerHTML = '<strong>Arrival:</strong> ' + formatApiDate(stop.arrival_date);
      info.appendChild(pArr);
    }
    if (stop.departure_date) {
      var pDep = document.createElement('p');
      pDep.innerHTML = '<strong>Departure:</strong> ' + formatApiDate(stop.departure_date);
      info.appendChild(pDep);
    }
    if (stop.transport_from_last) {
      var pTrans = document.createElement('p');
      pTrans.innerHTML = '<strong>Transport:</strong> ' + escapeHtml(stop.transport_from_last);
      info.appendChild(pTrans);
    }
    if (stop.activities) {
      var pAct = document.createElement('p');
      pAct.innerHTML = '<strong>Activities:</strong> ' + escapeHtml(stop.activities);
      info.appendChild(pAct);
    }
    if (stop.estimated_price != null) {
      var pPrice = document.createElement('p');
      pPrice.innerHTML = '<strong>Estimated Price:</strong> $' + escapeHtml(String(stop.estimated_price));
      info.appendChild(pPrice);
    }
    details.appendChild(h4);
    details.appendChild(info);
    card.appendChild(num);
    card.appendChild(details);
    return card;
  }

  async function showTripDetails(tripId) {
    try {
      var existing = document.querySelectorAll('.trip-details-modal-overlay');
      existing.forEach(function (el) {
        var prevMap = el.querySelector('#tripDetailsMap');
        if (prevMap) destroyTripMap(prevMap);
        if (el.parentNode) el.parentNode.removeChild(el);
      });

      var response = await fetch('/api/planned-trips/' + tripId);
      if (!response.ok) throw new Error('Failed to load trip details');
      var trip = await response.json();

      var template = document.getElementById('tripDetailsModalTemplate');
      if (!template || !template.content) return;
      var clone = document.importNode(template.content, true);
      var modal = clone.querySelector('.trip-details-modal-overlay');
      if (!modal) return;
      document.body.appendChild(clone);

      var titleEl = modal.querySelector('#tripDetailsTitle');
      var startDateEl = modal.querySelector('#tripDetailsStartDate');
      var endDateEl = modal.querySelector('#tripDetailsEndDate');
      var startCityWrap = modal.querySelector('#tripDetailsStartCityWrap');
      var startCityEl = modal.querySelector('#tripDetailsStartCity');
      var stopsCountEl = modal.querySelector('#tripDetailsStopsCount');
      var stopsListEl = modal.querySelector('#tripDetailsStopsList');

      if (titleEl) titleEl.textContent = trip.title || '';
      if (startDateEl) startDateEl.textContent = formatApiDate(trip.start_date);
      if (endDateEl) endDateEl.textContent = formatApiDate(trip.end_date);
      if (trip.start_city) {
        if (startCityWrap) startCityWrap.classList.remove('hidden');
        if (startCityEl) startCityEl.textContent = trip.start_city;
      } else {
        if (startCityWrap) startCityWrap.classList.add('hidden');
      }

      var stops = (trip.stops || []).slice().sort(function (a, b) { return (a.stop_order || 0) - (b.stop_order || 0); });
      if (stopsCountEl) stopsCountEl.textContent = String(stops.length);
      if (stopsListEl) {
        stopsListEl.innerHTML = '';
        if (stops.length === 0) {
          var empty = document.createElement('p');
          empty.className = 'muted';
          empty.textContent = 'No stops added yet.';
          stopsListEl.appendChild(empty);
        } else {
          stops.forEach(function (stop) { stopsListEl.appendChild(buildStopCard(stop)); });
        }
      }

      if (window.i18n && typeof window.i18n.applyToPage === 'function') {
        window.i18n.applyToPage(modal);
      }

      var mapEl = modal.querySelector('#tripDetailsMap');
      await initTripDetailsMap(modal, trip, stops);

      var closeBtn = modal.querySelector('.trip-details-close');
      var modalBox = modal.querySelector('.trip-details-modal');

      function removeModal() {
        document.removeEventListener('keydown', handleEsc);
        if (mapEl) destroyTripMap(mapEl);
        if (modal.parentNode) modal.parentNode.removeChild(modal);
      }

      if (closeBtn) closeBtn.addEventListener('click', removeModal);
      modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
      });
      if (modalBox) {
        modalBox.addEventListener('click', function (e) { e.stopPropagation(); });
      }
      function handleEsc(e) { if (e.key === 'Escape') removeModal(); }
      document.addEventListener('keydown', handleEsc);
    } catch (error) {
      console.error('Error loading trip details:', error);
      showError('Failed to load trip details: ' + error.message);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindTripListActions();
    render();
  });
})();
