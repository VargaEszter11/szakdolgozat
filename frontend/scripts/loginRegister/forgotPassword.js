document.getElementById('forgotPasswordLink').addEventListener('click', (e) => {
    e.preventDefault();
    showVerifyStep();
});

function showVerifyStep() {
    const overlay = document.createElement('div');
    overlay.className = 'custom-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'custom-modal';

    const header = document.createElement('div');
    header.className = 'custom-modal-header';

    const icon = document.createElement('div');
    icon.className = 'custom-modal-icon';
    icon.innerHTML = '🔑';
    icon.style.background = 'var(--accent-light, #e8f0fe)';

    const title = document.createElement('h3');
    title.className = 'custom-modal-title';
    title.textContent = 'Reset Password';

    header.appendChild(icon);
    header.appendChild(title);

    const desc = document.createElement('p');
    desc.className = 'custom-modal-message';
    desc.textContent = 'Enter your username and registered email to verify your identity.';

    const form = document.createElement('form');
    form.style.display = 'flex';
    form.style.flexDirection = 'column';
    form.style.gap = '12px';
    form.style.marginTop = '8px';

    const usernameInput = createInput('text', 'Your username', true);
    const emailInput = createInput('email', 'Your registered email', true);

    const errorMsg = document.createElement('p');
    errorMsg.style.color = '#dc3545';
    errorMsg.style.fontSize = '0.85rem';
    errorMsg.style.margin = '0';
    errorMsg.style.display = 'none';

    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';
    actions.style.marginTop = '4px';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'custom-modal-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.background = 'var(--muted)';
    cancelBtn.style.color = 'var(--surface)';

    const verifyBtn = document.createElement('button');
    verifyBtn.type = 'submit';
    verifyBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    verifyBtn.textContent = 'Verify';

    actions.appendChild(cancelBtn);
    actions.appendChild(verifyBtn);

    form.appendChild(usernameInput);
    form.appendChild(emailInput);
    form.appendChild(errorMsg);
    form.appendChild(actions);

    modal.appendChild(header);
    modal.appendChild(desc);
    modal.appendChild(form);
    overlay.appendChild(modal);

    const closeModal = () => {
        overlay.style.animation = 'fadeOut 0.2s ease-in-out';
        setTimeout(() => overlay.remove(), 200);
    };

    cancelBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMsg.style.display = 'none';
        verifyBtn.disabled = true;
        verifyBtn.textContent = 'Verifying...';

        try {
            const response = await fetch('/api/forgot-password/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: usernameInput.value.trim(),
                    email: emailInput.value.trim()
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                overlay.remove();
                showResetStep(data.user_id);
            } else {
                errorMsg.textContent = data.detail || 'Verification failed.';
                errorMsg.style.display = 'block';
            }
        } catch {
            errorMsg.textContent = 'Server error. Please try again later.';
            errorMsg.style.display = 'block';
        } finally {
            verifyBtn.disabled = false;
            verifyBtn.textContent = 'Verify';
        }
    });

    document.body.appendChild(overlay);
    usernameInput.focus();
}

function showResetStep(userId) {
    const overlay = document.createElement('div');
    overlay.className = 'custom-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'custom-modal';

    const header = document.createElement('div');
    header.className = 'custom-modal-header';

    const icon = document.createElement('div');
    icon.className = 'custom-modal-icon success';
    icon.innerHTML = '✓';

    const title = document.createElement('h3');
    title.className = 'custom-modal-title';
    title.textContent = 'Set New Password';

    header.appendChild(icon);
    header.appendChild(title);

    const desc = document.createElement('p');
    desc.className = 'custom-modal-message';
    desc.textContent = 'Identity verified. Enter your new password below.';

    const form = document.createElement('form');
    form.style.display = 'flex';
    form.style.flexDirection = 'column';
    form.style.gap = '12px';
    form.style.marginTop = '8px';

    const passwordInput = createInput('password', 'New password (min. 6 characters)', true);
    passwordInput.minLength = 6;
    const confirmInput = createInput('password', 'Confirm new password', true);

    const errorMsg = document.createElement('p');
    errorMsg.style.color = '#dc3545';
    errorMsg.style.fontSize = '0.85rem';
    errorMsg.style.margin = '0';
    errorMsg.style.display = 'none';

    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';
    actions.style.marginTop = '4px';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'custom-modal-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.style.background = 'var(--muted)';
    cancelBtn.style.color = 'var(--surface)';

    const resetBtn = document.createElement('button');
    resetBtn.type = 'submit';
    resetBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    resetBtn.textContent = 'Reset Password';

    actions.appendChild(cancelBtn);
    actions.appendChild(resetBtn);

    form.appendChild(passwordInput);
    form.appendChild(confirmInput);
    form.appendChild(errorMsg);
    form.appendChild(actions);

    modal.appendChild(header);
    modal.appendChild(desc);
    modal.appendChild(form);
    overlay.appendChild(modal);

    const closeModal = () => {
        overlay.style.animation = 'fadeOut 0.2s ease-in-out';
        setTimeout(() => overlay.remove(), 200);
    };

    cancelBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorMsg.style.display = 'none';

        if (passwordInput.value !== confirmInput.value) {
            errorMsg.textContent = 'Passwords do not match.';
            errorMsg.style.display = 'block';
            return;
        }

        if (passwordInput.value.length < 6) {
            errorMsg.textContent = 'Password must be at least 6 characters.';
            errorMsg.style.display = 'block';
            return;
        }

        resetBtn.disabled = true;
        resetBtn.textContent = 'Resetting...';

        try {
            const response = await fetch('/api/forgot-password/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    new_password: passwordInput.value
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                overlay.remove();
                showSuccess('Password reset successfully! You can now log in with your new password.');
            } else {
                errorMsg.textContent = data.detail || 'Reset failed.';
                errorMsg.style.display = 'block';
            }
        } catch {
            errorMsg.textContent = 'Server error. Please try again later.';
            errorMsg.style.display = 'block';
        } finally {
            resetBtn.disabled = false;
            resetBtn.textContent = 'Reset Password';
        }
    });

    document.body.appendChild(overlay);
    passwordInput.focus();
}

function createInput(type, placeholder, required) {
    const input = document.createElement('input');
    input.type = type;
    input.placeholder = placeholder;
    input.required = required;
    input.className = 'form-input';
    return input;
}
