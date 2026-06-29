(function () {
    var userId = localStorage.getItem("user_id");
    var path = location.pathname;
    var isPublicPage = /(loginPage|registerPage|shared_trip)\.html/.test(path);

    var scriptEl = document.currentScript;
    var src = scriptEl ? scriptEl.getAttribute("src") : "";
    var depth = (src.match(/\.\.\//g) || []).length;
    var prefix = depth >= 2 ? "../" : "";

    if (isPublicPage && userId) {
        location.replace(prefix + "main_page.html");
    } else if (!isPublicPage && !userId) {
        location.replace(prefix + "loginRegister/loginPage.html");
    }
})();
