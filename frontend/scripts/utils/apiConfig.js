(function () {
    var BACKEND = 'http://127.0.0.1:8000';
    var isBackend = window.location.origin === BACKEND ||
        window.location.origin === 'http://localhost:8000';

    window.API_BASE_URL = isBackend ? '' : BACKEND;

    if (!isBackend) {
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
