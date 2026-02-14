document.getElementById("registerForm").addEventListener("submit", async (e) => {

    e.preventDefault();

    const username = document.getElementById("username").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {

        showError("Passwords do not match");
        return;

    }

    try {

        const response = await fetch("http://127.0.0.1:8000/api/register", {

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

            showSuccess("Registration successful! You can now log in.", () => {
                window.location.href = "loginPage.html";
            });

        } else {

            showError(data.detail || "Registration failed");

        }

    } catch (error) {

        console.error(error);
        showError("Server error. Please try again later.");

    }

});