document.getElementById("loginForm").addEventListener("submit", async (e) => {

    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {

        const response = await fetch("http://127.0.0.1:8000/api/login", {

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

            // store user session
            localStorage.setItem("user_id", data.user_id);
            localStorage.setItem("username", data.username);

            showSuccess("Login successful!", () => {
                window.location.href = "../main_page.html";
            });

        } else {

            showError(data.detail || "Login failed");

        }

    } catch (error) {

        console.error(error);
        showError("Server error. Please try again later.");

    }

});