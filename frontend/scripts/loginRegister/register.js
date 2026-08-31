function registerT(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
        var v = window.i18n.t(key);
        if (v && v !== key) return v;
    }
    return fallback != null ? fallback : key;
}

document.getElementById("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    const submitBtn = e.target.querySelector('[type="submit"]');

    // Checks before hitting the API
    if (password !== confirmPassword) {
        showError(registerT("register.passwordMismatch", "Passwords do not match."));
        return;
    }

    if (password.length < 6) {
        showError(registerT("register.passwordTooShort", "Password must be at least 6 characters."));
        return;
    }

    if (submitBtn) submitBtn.disabled = true;

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                email,
                password
            })
        });

        const data = await response.json();

        if (data.success) {
            window.location.href = "/login";

            return;
        }
        showError(
            apiErrorDetail(data, registerT("register.failed", "Registration failed"))
        );
    } catch (error) {
        console.error(error);
        showError(registerT("register.serverError", "Server error. Please try again later."));
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
});
