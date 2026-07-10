(function () {
    // Local dev only: frontend opened on a different port than the backend's own
    // dev server (e.g. a static file server on :5500) needs API calls pointed at
    // the backend explicitly. In production (and when the backend serves the
    // frontend itself, or a reverse proxy like nginx sits in front of both on the
    // same origin), relative /api paths already resolve correctly — don't rewrite.
    var BACKEND = 'http://127.0.0.1:8000';
    var isLocalDevOnOtherPort =
        (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') &&
        window.location.port && window.location.port !== '8000';

    window.API_BASE_URL = isLocalDevOnOtherPort ? BACKEND : '';

    if (isLocalDevOnOtherPort) {
        var _fetch = window.fetch;
        window.fetch = function (url, opts) {
            if (typeof url === 'string' &&
                (url.startsWith('/api') || url.startsWith('/generate_travel_plans'))) {
                url = BACKEND + url;
            }
            return _fetch.call(this, url, opts);
        };
    }
})();
