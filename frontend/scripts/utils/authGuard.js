(function () {
    var userId = localStorage.getItem("user_id");
    var token = localStorage.getItem("access_token");
    var path = location.pathname;
    var isPublicPage = /(loginPage|registerPage|shared_trip|forgotPassword|resetPassword)\.html/.test(path);
    var loggedIn = !!(userId && token);

    var scriptEl = document.currentScript;
    var src = scriptEl ? scriptEl.getAttribute("src") : "";
    var depth = (src.match(/\.\.\//g) || []).length;
    var prefix = depth >= 2 ? "../" : "";

    if (isPublicPage && loggedIn) {
        location.replace(prefix + "main_page.html");
    } else if (!isPublicPage && !loggedIn) {
        location.replace(prefix + "loginRegister/loginPage.html");
    }
})();
