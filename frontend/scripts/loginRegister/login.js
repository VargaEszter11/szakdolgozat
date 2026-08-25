function loginT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
        var v = window.i18n.t(key);
        if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
}

// Session / tutorial
function clearLegacyTutorialLocalStorage() {
    [
        "tutorial_completed",
        "pending_tutorial",
        "tutorial_step",
        "tutorial_language_ready",
    ].forEach(function (key) {
        localStorage.removeItem(key);
    });
}

function migrateLegacyTutorialCompleted(userId) {
    if (!userId) return;
    fetch("/api/users/" + userId, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tutorial_completed: true }),
    }).catch(function () { /* ignore */ });
}

// Save session and redirect
function saveSessionAndRedirect(data) {
    localStorage.setItem("user_id", data.user_id);
    localStorage.setItem("username", data.username);
    if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
    }

    var legacyDone = localStorage.getItem("tutorial_completed") === "1";
    clearLegacyTutorialLocalStorage();

    if (data.tutorial_completed || legacyDone) {
        if (!data.tutorial_completed && legacyDone) {
            migrateLegacyTutorialCompleted(data.user_id);
        }
        sessionStorage.removeItem("pending_tutorial");
        sessionStorage.removeItem("tutorial_step");
        sessionStorage.removeItem("tutorial_language_ready");
    } else {
        sessionStorage.setItem("pending_tutorial", "1");
        sessionStorage.setItem("tutorial_step", "1");
        sessionStorage.removeItem("tutorial_language_ready");
    }
    window.location.href = "../main_page.html";
}

// Password login
document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const submitBtn = e.target.querySelector('[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                password
            })
        });

        const data = await response.json();
        if (data.success) {
            localStorage.removeItem("google_avatar_url");
            saveSessionAndRedirect(data);
            return;
        }
        showError(
            apiErrorDetail(data, loginT("login.failed", "Login failed"))
        );
    } catch (error) {
        console.error(error);
        showError(loginT("login.serverError", "Server error. Please try again later."));
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
});

// Google Sign-In
function getAppLanguageCode() {
    var lang =
        window.i18n && typeof window.i18n.getLanguage === "function"
            ? window.i18n.getLanguage()
            : localStorage.getItem("language") || "en";
    if (lang === "hu" || lang === "de") return lang;
    return "en";
}

function showGoogleUnavailable(reason) {
    var key = "login.googleUnavailable";
    if (reason === "not_configured") key = "login.googleNotConfigured";
    else if (reason === "load_failed") key = "login.googleLoadFailed";

    var host = document.getElementById("googleSignInButton");
    if (!host) return;
    host.innerHTML = "";
    var hint = document.createElement("p");
    hint.className = "google-login-hint";
    hint.setAttribute("data-i18n", key);
    if (window.i18n && typeof window.i18n.t === "function") {
        hint.textContent = window.i18n.t(key);
    } else {
        hint.textContent =
            reason === "not_configured"
                ? "Google sign-in is not configured on the server."
                : reason === "load_failed"
                    ? "Google sign-in failed to load. Please try refreshing."
                    : "Google sign-in is currently unavailable.";
    }
    host.appendChild(hint);
}

function loadGoogleIdentityScript() {
    return new Promise(function (resolve, reject) {
        var hl = getAppLanguageCode();
        var scriptUrl =
            "https://accounts.google.com/gsi/client?hl=" + encodeURIComponent(hl);

        function scriptHasHl(el) {
            return el && el.src && el.src.indexOf("hl=" + hl) !== -1;
        }

        var existing = document.getElementById("google-identity-script");
        if (existing) {
            if (scriptHasHl(existing)) {
                if (window.google && window.google.accounts && window.google.accounts.oauth2) {
                    resolve();
                    return;
                }
                existing.addEventListener("load", resolve, { once: true });
                existing.addEventListener("error", reject, { once: true });
                return;
            }
            existing.remove();
        }

        try {
            if (window.google) {
                delete window.google;
            }
        } catch (e) {
            /* ignore */
        }

        var script = document.createElement("script");
        script.id = "google-identity-script";
        script.src = scriptUrl;
        script.async = true;
        script.defer = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function handleGoogleAuthCode(code) {
    const response = await fetch("/api/google-login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ code: code })
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(
            apiErrorDetail(data, loginT("login.googleFailed", "Google login failed"))
        );
    }

    if (data.avatar_url && typeof data.avatar_url === "string") {
        localStorage.setItem("google_avatar_url", data.avatar_url);
    } else {
        localStorage.removeItem("google_avatar_url");
    }

    return data;
}

async function initGoogleLogin() {
    try {
        const configResponse = await fetch("/api/google-config");
        if (!configResponse.ok) {
            showGoogleUnavailable("unavailable");
            return;
        }

        const config = await configResponse.json();
        if (!config.client_id) {
            showGoogleUnavailable("not_configured");
            return;
        }

        await loadGoogleIdentityScript();
        if (!window.google || !window.google.accounts || !window.google.accounts.oauth2) {
            throw new Error("Google Identity Services failed to initialize");
        }

        var btn = document.getElementById("googleSignInBtn");

        var codeClient = window.google.accounts.oauth2.initCodeClient({
            client_id: config.client_id,
            scope: "openid email profile",
            ux_mode: "popup",
            callback: async function (response) {
                if (!response || !response.code) {
                    if (response && response.error && response.error !== "popup_closed") {
                        console.error(response.error);
                        showError(loginT("login.googleFailed", "Google login failed"));
                    }
                    return;
                }
                try {
                    const data = await handleGoogleAuthCode(response.code);
                    saveSessionAndRedirect(data);
                } catch (error) {
                    console.error(error);
                    showError(
                        (error && error.message) ||
                        loginT("login.googleFailed", "Google login failed")
                    );
                }
            }
        });

        if (btn) {
            btn.disabled = false;
            btn.addEventListener("click", function () {
                codeClient.requestCode();
            });
        }
    } catch (error) {
        console.error(error);
        showGoogleUnavailable("load_failed");
    }
}

initGoogleLogin();
