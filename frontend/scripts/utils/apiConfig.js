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

    function isApiUrl(url) {
        if (typeof url !== 'string') {
            try {
                url = url && url.url ? String(url.url) : '';
            } catch (e) {
                return false;
            }
        }
        return (
            url.indexOf('/api') !== -1 ||
            url.indexOf('/generate_travel_plans') !== -1
        );
    }

    function clearSession() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('username');
        localStorage.removeItem('google_avatar_url');
    }

    window.clearAuthSession = clearSession;

    var _fetch = window.fetch;
    window.fetch = function (url, opts) {
        opts = opts || {};
        var headers = new Headers(opts.headers || {});

        if (isLocalDevOnOtherPort && typeof url === 'string' &&
            (url.startsWith('/api') || url.startsWith('/generate_travel_plans'))) {
            url = BACKEND + url;
        }

        var token = localStorage.getItem('access_token');
        if (token && isApiUrl(url) && !headers.has('Authorization')) {
            headers.set('Authorization', 'Bearer ' + token);
        }
        opts.headers = headers;

        return _fetch.call(this, url, opts).then(function (res) {
            if (res.status === 401 && isApiUrl(url)) {
                var path = location.pathname || '';
                var isPublicPage = /(loginPage|registerPage|shared_trip|forgotPassword|resetPassword|admin(_feedback)?)\.html/.test(path);
                if (!isPublicPage && localStorage.getItem('access_token')) {
                    clearSession();
                    var depth = (path.match(/\//g) || []).length;
                    // pages/... → login under pages/loginRegister/
                    var loginHref = depth >= 3
                        ? '../loginRegister/loginPage.html'
                        : 'loginRegister/loginPage.html';
                    if (path.indexOf('/pages/') !== -1) {
                        if (path.indexOf('/pages/main_page') !== -1) {
                            loginHref = 'loginRegister/loginPage.html';
                        } else if (path.indexOf('/pages/') !== -1) {
                            loginHref = '../loginRegister/loginPage.html';
                        }
                    }
                    try {
                        location.replace(loginHref);
                    } catch (e) { /* ignore */ }
                }
            }
            return res;
        });
    };
})();
