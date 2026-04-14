function saveSessionAndRedirect(data) {
    localStorage.setItem("user_id", data.user_id);
    localStorage.setItem("username", data.username);
    showSuccess("Login successful!", () => {
        window.location.href = "../main_page.html";
    });
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

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
            saveSessionAndRedirect(data);
        } else {
            showError(data.detail || "Login failed");
        }
    } catch (error) {
        console.error(error);
        showError("Server error. Please try again later.");
    }
});

function toggleGoogleSection(show) {
    var divider = document.querySelector(".google-login-divider");
    var host = document.getElementById("googleSignInButton");
    if (divider) divider.style.display = show ? "" : "none";
    if (host) host.style.display = show ? "" : "none";
}

function getAppLanguageCode() {
    var lang =
        window.i18n && typeof window.i18n.getLanguage === "function"
            ? window.i18n.getLanguage()
            : localStorage.getItem("language") || "en";
    if (lang === "hu" || lang === "de") return lang;
    return "en";
}

function getGoogleSignInLocale() {
    return getAppLanguageCode();
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
                if (window.google && window.google.accounts && window.google.accounts.id) {
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

async function handleGoogleCredential(credential) {
    const response = await fetch("/api/google-login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ credential: credential })
    });

    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.detail || "Google login failed");
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
        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
            throw new Error("Google Identity Services failed to initialize");
        }

        var host = document.getElementById("googleSignInButton");
        window.google.accounts.id.initialize({
            client_id: config.client_id,
            locale: getGoogleSignInLocale(),
            callback: async function (response) {
                try {
                    const data = await handleGoogleCredential(response.credential);
                    saveSessionAndRedirect(data);
                } catch (error) {
                    console.error(error);
                    showError(error.message || "Google login failed");
                }
            }
        });

        window.google.accounts.id.renderButton(host, {
            theme: "outline",
            size: "large",
            text: "continue_with",
            shape: "pill",
            width: "280"
        });
    } catch (error) {
        console.error(error);
        showGoogleUnavailable("load_failed");
    }
}

initGoogleLogin();