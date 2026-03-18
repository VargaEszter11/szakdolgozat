(function () {
    var scriptEl = document.currentScript;
    var src = scriptEl ? scriptEl.getAttribute('src') : '';
    var depth = (src.match(/\.\.\//g) || []).length;
    var prefix = depth >= 2 ? '../../' : '../';
    var pagePrefix = depth >= 2 ? '../' : '';

    var HEADER_HTML =
        '<a href="' + pagePrefix + 'main_page.html" class="nav-logo">' +
            '<img src="' + prefix + 'pictures/marker.png" alt="TravelApp">' +
        '</a>' +
        '<a href="' + pagePrefix + 'loginRegister/profile.html" class="main-header-profile" aria-label="Profile">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>' +
                '<circle cx="12" cy="7" r="4"/>' +
            '</svg>' +
        '</a>';

    var MAP_ICON = '<svg class="sidebar-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M5.25345 4.19584L4.02558 4.90813C3.03739 5.48137 2.54329 5.768 2.27164 6.24483C2 6.72165 2 7.30233 2 8.46368V16.6283C2 18.1542 2 18.9172 2.34226 19.3418C2.57001 19.6244 2.88916 19.8143 3.242 19.8773C3.77226 19.9719 4.42148 19.5953 5.71987 18.8421C6.60156 18.3306 7.45011 17.7994 8.50487 17.9435C8.98466 18.009 9.44231 18.2366 10.3576 18.6917L14.1715 20.588C14.9964 20.9982 15.004 21 15.9214 21H18C19.8856 21 20.8284 21 21.4142 20.4013C22 19.8026 22 18.8389 22 16.9117V10.1715C22 8.24423 22 7.2806 21.4142 6.68188C20.8284 6.08316 19.8856 6.08316 18 6.08316H15.9214C15.004 6.08316 14.9964 6.08139 14.1715 5.6712L10.8399 4.01463C9.44884 3.32297 8.75332 2.97714 8.01238 3.00117C7.27143 3.02521 6.59877 3.41542 5.25345 4.19584Z"/>' +
        '<path d="M15 6.5V20.5" stroke-dasharray="1 3"/>' +
        '<path d="M8 3.5V17.5" stroke-dasharray="1 3"/>' +
        '</svg>';

    var PLANE_ICON = '<svg class="sidebar-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M2.00031 20H18.0003"/>' +
        '<path d="M3.82527 12.1661C3.55027 11.9661 3.30027 11.7161 3.00028 10.8411C2.91891 10.6241 2.61139 9.53619 2.35028 8.54109C2.13003 7.7017 1.93377 6.93555 2.02528 6.74109C2.10029 6.54109 2.20027 6.39109 2.52527 6.19109C2.72527 6.06802 3.75027 5.81609 3.95027 5.76609C4.15027 5.71609 4.42526 5.69109 4.65027 5.76609C5.07527 5.84109 5.95027 7.11609 6.17527 7.26609C6.27526 7.36609 6.60027 7.657 6.97527 7.69109C7.25027 7.71609 7.52527 7.64109 7.82528 7.51609C8.10027 7.40151 13.5253 4.76609 14.0253 4.54109C18.1003 2.84109 21.0603 5.63609 21.5103 6.23609C21.9753 6.81609 22.0753 6.99109 21.9503 7.49109C21.7887 8.01609 21.3503 8.11609 21.1003 8.19109C20.8503 8.26609 17.4003 9.19109 16.0503 9.56609C15.7554 9.6621 15.6114 9.85492 15.5753 9.89109C15.4003 10.1411 14.6053 11.8411 14.3803 12.2161C14.2253 12.6161 13.8003 13.1161 13.2503 13.3161C12.6753 13.5161 11.6753 13.7411 11.4503 13.8161C11.2253 13.8911 10.7003 14.0411 10.5253 13.9911C10.3003 13.9411 10.0853 13.7161 10.1853 13.3661C10.2853 13.0161 10.4753 12.0411 10.5003 11.8911C10.5253 11.7411 10.7753 11.1161 10.5003 11.0911C10.4503 11.0161 9.92527 11.2411 9.15027 11.4161C8.57449 11.5782 7.9715 11.7386 7.55027 11.8411C5.92527 12.3161 5.04521 12.4411 4.85027 12.4411C4.47527 12.4411 4.20027 12.3911 3.82527 12.1661Z"/>' +
        '</svg>';

    var SETTINGS_ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round">' +
        '<path d="M21.3175 7.14139L20.8239 6.28479C20.4506 5.63696 20.264 5.31305 19.9464 5.18388C19.6288 5.05472 19.2696 5.15664 18.5513 5.36048L17.3311 5.70418C16.8725 5.80994 16.3913 5.74994 15.9726 5.53479L15.6357 5.34042C15.2766 5.11043 15.0004 4.77133 14.8475 4.37274L14.5136 3.37536C14.294 2.71534 14.1842 2.38533 13.9228 2.19657C13.6615 2.00781 13.3143 2.00781 12.6199 2.00781H11.5051C10.8108 2.00781 10.4636 2.00781 10.2022 2.19657C9.94085 2.38533 9.83106 2.71534 9.61149 3.37536L9.27753 4.37274C9.12465 4.77133 8.84845 5.11043 8.48937 5.34042L8.15249 5.53479C7.73374 5.74994 7.25259 5.80994 6.79398 5.70418L5.57375 5.36048C4.85541 5.15664 4.49625 5.05472 4.17867 5.18388C3.86109 5.31305 3.67445 5.63696 3.30115 6.28479L2.80757 7.14139C2.45766 7.74864 2.2827 8.05227 2.31666 8.37549C2.35061 8.69871 2.58483 8.95918 3.05326 9.48012L4.0843 10.6328C4.3363 10.9518 4.51521 11.5078 4.51521 12.0077C4.51521 12.5078 4.33636 13.0636 4.08433 13.3827L3.05326 14.5354C2.58483 15.0564 2.35062 15.3168 2.31666 15.6401C2.2827 15.9633 2.45766 16.2669 2.80757 16.8741L3.30114 17.7307C3.67443 18.3785 3.86109 18.7025 4.17867 18.8316C4.49625 18.9608 4.85542 18.8589 5.57377 18.655L6.79394 18.3113C7.25263 18.2055 7.73387 18.2656 8.15267 18.4808L8.4895 18.6752C8.84851 18.9052 9.12464 19.2442 9.2775 19.6428L9.61149 20.6403C9.83106 21.3003 9.94085 21.6303 10.2022 21.8191C10.4636 22.0078 10.8108 22.0078 11.5051 22.0078H12.6199C13.3143 22.0078 13.6615 22.0078 13.9228 21.8191C14.1842 21.6303 14.294 21.3003 14.5136 20.6403L14.8476 19.6428C15.0004 19.2442 15.2765 18.9052 15.6356 18.6752L15.9724 18.4808C16.3912 18.2656 16.8724 18.2055 17.3311 18.3113L18.5513 18.655C19.2696 18.8589 19.6288 18.9608 19.9464 18.8316C20.264 18.7025 20.4506 18.3785 20.8239 17.7307L21.3175 16.8741C21.6674 16.2669 21.8423 15.9633 21.8084 15.6401C21.7744 15.3168 21.5402 15.0564 21.0718 14.5354L20.0407 13.3827C19.7887 13.0636 19.6098 12.5078 19.6098 12.0077C19.6098 11.5078 19.7888 10.9518 20.0407 10.6328L21.0718 9.48012C21.5402 8.95918 21.7744 8.69871 21.8084 8.37549C21.8423 8.05227 21.6674 7.74864 21.3175 7.14139Z"/>' +
        '<path d="M15.5195 12C15.5195 13.933 13.9525 15.5 12.0195 15.5C10.0865 15.5 8.51953 13.933 8.51953 12C8.51953 10.067 10.0865 8.5 12.0195 8.5C13.9525 8.5 15.5195 10.067 15.5195 12Z"/>' +
        '</svg>';

    var SIDEBAR_HTML =
        '<nav class="sidebar-nav">' +
            '<div class="sidebar-section">' +
                '<div class="sidebar-section-title">' + MAP_ICON +
                    '<span data-i18n="nav.placesSection">Places</span>' +
                '</div>' +
                '<a href="' + pagePrefix + 'visitedPlaces/visited_places.html" class="sidebar-link" data-i18n="nav.visitedPlaces" data-sidebar-id="visitedPlaces">Visited Places</a>' +
                '<a href="' + pagePrefix + 'visitedPlaces/add_new_place.html" class="sidebar-link" data-i18n="nav.addNewPlace" data-sidebar-id="addNewPlace">Add New Place</a>' +
            '</div>' +
            '<div class="sidebar-section">' +
                '<div class="sidebar-section-title">' + PLANE_ICON +
                    '<span data-i18n="nav.tripsSection">Trips</span>' +
                '</div>' +
                '<a href="' + pagePrefix + 'routePlanner/planned_trips.html" class="sidebar-link" data-i18n="nav.plannedTrips" data-sidebar-id="plannedTrips">Planned Trips</a>' +
                '<a href="' + pagePrefix + 'routePlanner/plan_new_trip.html" class="sidebar-link" data-i18n="nav.planNewTrip" data-sidebar-id="planNewTrip">Plan New Trip</a>' +
            '</div>' +
            '<div class="sidebar-section sidebar-section-settings">' +
                '<a href="' + pagePrefix + 'settings/settings.html" class="sidebar-link sidebar-link-single" data-sidebar-id="settings">' +
                    SETTINGS_ICON +
                    '<span data-i18n="nav.settings">Settings</span>' +
                '</a>' +
            '</div>' +
        '</nav>';

    var PAGE_MAP = {
        'visited_places': 'visitedPlaces',
        'add_new_place': 'addNewPlace',
        'planned_trips': 'plannedTrips',
        'plan_new_trip': 'planNewTrip',
        'surprise_me': 'planNewTrip',
        'plan_new_trip_visited_places': 'planNewTrip',
        'plan_new_trip_unvisited_places': 'planNewTrip',
        'settings': 'settings',
        'places_map_view': 'visitedPlaces'
    };

    function highlightActive() {
        var path = location.pathname;
        var file = path.split('/').pop().replace('.html', '');
        var activeId = PAGE_MAP[file];
        if (!activeId) return;
        var link = document.querySelector('[data-sidebar-id="' + activeId + '"]');
        if (link) link.classList.add('sidebar-link-active');
    }

    function injectHeader() {
        var el = document.getElementById('app-header');
        if (!el) return;
        el.innerHTML = HEADER_HTML;
    }

    function injectSidebar() {
        var el = document.getElementById('app-sidebar');
        if (!el) return;
        el.innerHTML = SIDEBAR_HTML;
        highlightActive();
    }

    window.appShell = {
        injectHeader: injectHeader,
        injectSidebar: injectSidebar,
        init: function () {
            injectHeader();
            injectSidebar();
            if (window.i18n) window.i18n.applyToPage();
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.appShell.init);
    } else {
        window.appShell.init();
    }
})();
