document.addEventListener('DOMContentLoaded', function () {
    var btn = document.querySelector('.hamburger-btn');
    var header = document.querySelector('.main-header');

    if (!btn || !header) return;

    btn.addEventListener('click', function (e) {
        e.stopPropagation();
        header.classList.toggle('nav-open');
    });

    var links = header.querySelectorAll('.nav-link');
    for (var i = 0; i < links.length; i++) {
        links[i].addEventListener('click', function () {
            header.classList.remove('nav-open');
        });
    }

    document.addEventListener('click', function (e) {
        if (!header.contains(e.target)) {
            header.classList.remove('nav-open');
        }
    });
});
