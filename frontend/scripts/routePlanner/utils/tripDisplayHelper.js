(function (global) {
    var AIRPORT_LABEL_WORDS = /\b(airport|aeroport|aerodrome|airfield|lufthavn|flughafen|heliport)\b/gi;

    function plannedTripsT(key, fallback) {
        if (global.i18n && typeof global.i18n.t === 'function') {
            var v = global.i18n.t('plannedTrips.' + key);
            if (v && String(v).indexOf('plannedTrips.' + key) !== 0) return v;
        }
        return fallback;
    }

    function transportLabel(transport) {
        if (!transport) return 'N/A';
        var key = String(transport).trim().toLowerCase();
        var label = plannedTripsT('transportTypes.' + key, null);
        return label || transport;
    }

    // City name for Booking.com — not necessarily the IATA hub label
    function lodgingSearchCity(stop) {
        if (!stop) return '';
        var requested = String(stop.requested_place || stop.requestedPlace || '').trim();
        if (requested) {
            return sanitizeLodgingCity(requested.split(',')[0].trim());
        }
        return sanitizeLodgingCity(stop.city || stop.place_name || '');
    }

    function sanitizeLodgingCity(name) {
        var original = String(name || '').trim();
        if (!original) return '';
        var cleaned = original
            .replace(/\([^)]*\)/g, ' ')
            .replace(AIRPORT_LABEL_WORDS, ' ')
            .replace(/\s+/g, ' ')
            .trim(' ,-/');
        return cleaned || original;
    }

    // lodging_* from draft plans; latitude/longitude from saved trip stops
    function lodgingCoordinates(stop) {
        if (!stop) return null;
        var lat = stop.lodging_latitude != null ? stop.lodging_latitude : stop.lodgingLatitude;
        var lon = stop.lodging_longitude != null ? stop.lodging_longitude : stop.lodgingLongitude;
        if (lat == null || lon == null) {
            lat = stop.latitude;
            lon = stop.longitude;
        }
        lat = Number(lat);
        lon = Number(lon);
        if (!isFinite(lat) || !isFinite(lon)) return null;
        return { lat: lat, lon: lon };
    }

    function accommodationBookingUrl(city, country, checkin, checkout, people, coords) {
        if (!city || !checkin || !checkout || checkin === checkout) return null;
        var params = new URLSearchParams({
            ss: [city, country].filter(Boolean).join(', '),
            checkin: checkin,
            checkout: checkout,
            group_adults: String(Math.max(1, parseInt(people, 10) || 1)),
            no_rooms: '1',
            group_children: '0'
        });
        if (coords && isFinite(coords.lat) && isFinite(coords.lon)) {
            params.set('latitude', String(coords.lat));
            params.set('longitude', String(coords.lon));
        }
        return 'https://www.booking.com/searchresults.html?' + params.toString();
    }

    function accommodationBookingUrlForStop(stop, country, checkin, checkout, people) {
        return accommodationBookingUrl(
            lodgingSearchCity(stop),
            country,
            checkin,
            checkout,
            people,
            lodgingCoordinates(stop)
        );
    }

    global.TripDisplayHelper = {
        transportLabel: transportLabel,
        lodgingSearchCity: lodgingSearchCity,
        lodgingCoordinates: lodgingCoordinates,
        accommodationBookingUrl: accommodationBookingUrl,
        accommodationBookingUrlForStop: accommodationBookingUrlForStop,
        plannedTripsT: plannedTripsT
    };
})(typeof window !== 'undefined' ? window : this);
