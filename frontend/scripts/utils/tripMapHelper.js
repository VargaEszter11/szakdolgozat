(function (global) {
    var NOMINATIM_DELAY_MS = 1100;

    function sleep(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    // Client-side geocode, used only when DB coordinates are missing
    function nominatimGeocode(query, options) {
        options = options || {};
        if (!query || !String(query).trim()) return Promise.resolve(null);
        var params = {
            q: String(query).trim(),
            format: 'json',
            limit: String(options.limit || 1)
        };
        if (options.addressdetails) params.addressdetails = '1';
        if (options.featuretype) params.featuretype = String(options.featuretype);
        var url = 'https://nominatim.openstreetmap.org/search?' + new URLSearchParams(params);
        return fetch(url, { headers: { Accept: 'application/json' } })
            .then(function (res) {
                return res.ok ? res.json() : null;
            })
            .then(function (data) {
                return Array.isArray(data) && data.length ? data[0] : null;
            })
            .catch(function () {
                return null;
            });
    }

    function countryDisplay(value) {
        return global.Countries && global.Countries.displayName
            ? global.Countries.displayName(value)
            : String(value || '').trim();
    }

    function placeDisplay(placeName, country) {
        return global.Countries && global.Countries.formatPlace
            ? global.Countries.formatPlace(placeName, country)
            : (placeName || '') + (country ? ', ' + country : '');
    }

    function labelForStop(stop) {
        var ord = stop.stop_order != null ? String(stop.stop_order) : '?';
        return ord + '. ' + placeDisplay(stop.place_name, stop.country);
    }

    function defaultT(key, fallback) {
        if (global.i18n && typeof global.i18n.t === 'function') {
            var v = global.i18n.t('plannedTrips.' + key);
            if (v && String(v).indexOf('plannedTrips.' + key) !== 0) return v;
        }
        return fallback;
    }

    /**
     * Ordered points: start city (if any), then stops.
     * Uses stored lat/lon when present; otherwise Nominatim (throttled).
     * @param {object} trip
     * @param {Array} orderedStops
     * @param {function(string, string): string} [tFn] i18n helper (key, fallback)
     * @returns {Promise<Array>}
     */
    function buildAllRoutePoints(trip, orderedStops, tFn) {
        var t = typeof tFn === 'function' ? tFn : defaultT;
        var points = [];
        var hadNetworkRequest = false;
        var chain = Promise.resolve();
        orderedStops = orderedStops || [];

        function beforeNetwork() {
            // Nominatim asks for ~1 request/second
            var p = hadNetworkRequest ? sleep(NOMINATIM_DELAY_MS) : Promise.resolve();
            hadNetworkRequest = true;
            return p;
        }

        if (trip && trip.start_city && String(trip.start_city).trim()) {
            var startQuery = String(trip.start_city).trim();
            var startPopup = t('mapStartCityLabel', 'Start') + ': ' + startQuery;
            var startLat = trip.start_latitude;
            var startLon = trip.start_longitude;
            // Saved at trip create/update
            if (startLat != null && startLon != null && !isNaN(startLat) && !isNaN(startLon)) {
                points.push({
                    lat: Number(startLat),
                    lng: Number(startLon),
                    label: startPopup,
                    kind: 'start',
                    startCityName: startQuery
                });
            } else {
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
                    if (stop.country) q += ', ' + countryDisplay(stop.country);
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

    /**
     * Render an itinerary route map (start + stops).
     * @param {HTMLElement} accentHostEl element used to read --pt-popup-accent
     * @param {HTMLElement} mapEl
     * @param {HTMLElement} noteEl
     * @param {HTMLElement} section
     * @param {Array} points
     * @param {boolean} showPartialNote
     * @param {function(string, string): string} [tFn]
     */
    function renderTripMap(accentHostEl, mapEl, noteEl, section, points, showPartialNote, tFn) {
        var t = typeof tFn === 'function' ? tFn : defaultT;
        var L = global.L;
        if (!section || !mapEl || !noteEl || typeof L === 'undefined' || !points || !points.length) {
            return;
        }

        section.classList.remove('hidden');
        destroyTripMap(mapEl);

        var latlngs = points.map(function (p) {
            return [p.lat, p.lng];
        });
        var host = accentHostEl || document.documentElement;
        var accent = getComputedStyle(host).getPropertyValue('--pt-popup-accent').trim() || '#6366f1';

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
                sub.textContent = t('mapStartMarkerSubtitle', 'Starting city');
                var name = document.createElement('div');
                name.style.fontWeight = '700';
                name.style.fontSize = '1rem';
                name.style.marginTop = '0.35rem';
                name.style.color = 'var(--pt-popup-text, #0f172a)';
                name.textContent = p.startCityName
                    || (p.label && p.label.indexOf(': ') >= 0 ? p.label.split(': ').slice(1).join(': ') : p.label);
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
                    kSpan.textContent = t('mapStartCityLabel', 'Start');
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
                        /* ignore */
                    }
                });
            } catch (e) {
                /* ignore */
            }
        }, 120);

        if (showPartialNote) {
            noteEl.textContent = t(
                'mapPartialRoute',
                'Some stops could not be located; the line shows the cities we could find, in visit order.'
            );
            noteEl.classList.remove('hidden');
        }

        if (global.i18n && typeof global.i18n.applyToPage === 'function') {
            global.i18n.applyToPage(section);
        }

        setTimeout(function () {
            if (mapEl._leaflet_map) mapEl._leaflet_map.invalidateSize();
        }, 450);
    }

    global.TripMapHelper = {
        sleep: sleep,
        nominatimGeocode: nominatimGeocode,
        countryDisplay: countryDisplay,
        placeDisplay: placeDisplay,
        labelForStop: labelForStop,
        buildAllRoutePoints: buildAllRoutePoints,
        destroyTripMap: destroyTripMap,
        renderTripMap: renderTripMap
    };
})(typeof window !== 'undefined' ? window : this);