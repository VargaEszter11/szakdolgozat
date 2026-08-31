(function () {
    var userId = localStorage.getItem("user_id");
    var token = localStorage.getItem("access_token");
    var path = (location.pathname || "/").replace(/\/+$/, "") || "/";
    var isPublicPage = /^\/(login|register|share|reset-password)$/.test(path);
    var loggedIn = !!(userId && token);

    if (isPublicPage && loggedIn) {
        location.replace("/");
    } else if (!isPublicPage && !loggedIn) {
        location.replace("/login");
    }
})();
