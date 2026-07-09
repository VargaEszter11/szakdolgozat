function forgotPasswordT(key, fallback) {
    return window.i18n && typeof window.i18n.t === 'function' ? window.i18n.t(key) : fallback;
}

document.getElementById('forgotPasswordLink').addEventListener('click', (e) => {
    e.preventDefault();
    showRequestStep();
});

function showRequestStep() {
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
    title.textContent = forgotPasswordT('forgotPassword.title', 'Reset Password');

    header.appendChild(icon);
    header.appendChild(title);

    const desc = document.createElement('p');
    desc.className = 'custom-modal-message';
    desc.textContent = forgotPasswordT(
        'forgotPassword.description',
        "Enter your account's email and we'll send you a link to reset your password."
    );

    const form = document.createElement('form');
    form.style.display = 'flex';
    form.style.flexDirection = 'column';
    form.style.gap = '12px';
    form.style.marginTop = '8px';

    const emailInput = createInput('email', forgotPasswordT('forgotPassword.emailPlaceholder', 'Your registered email'), true);

    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';
    actions.style.marginTop = '4px';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'custom-modal-btn';
    cancelBtn.textContent = forgotPasswordT('forgotPassword.cancel', 'Cancel');
    cancelBtn.style.background = 'var(--muted)';
    cancelBtn.style.color = 'var(--surface)';

    const sendBtn = document.createElement('button');
    sendBtn.type = 'submit';
    sendBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    sendBtn.textContent = forgotPasswordT('forgotPassword.send', 'Send reset link');

    actions.appendChild(cancelBtn);
    actions.appendChild(sendBtn);

    form.appendChild(emailInput);
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
        sendBtn.disabled = true;
        sendBtn.textContent = forgotPasswordT('forgotPassword.sending', 'Sending...');

        try {
            const response = await fetch('/api/forgot-password/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: emailInput.value.trim()
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                closeModal();
                showModal({
                    title: forgotPasswordT('forgotPassword.checkEmailTitle', 'Check your email'),
                    message: data.message || forgotPasswordT(
                        'forgotPassword.genericSuccessMessage',
                        "If an account with that email exists, we've sent a password reset link to it."
                    ),
                    type: 'success'
                });
            } else {
                showError(data.detail || forgotPasswordT('forgotPassword.sendFailed', 'Could not send reset email.'));
            }
        } catch {
            showError(forgotPasswordT('forgotPassword.serverError', 'Server error. Please try again later.'));
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = forgotPasswordT('forgotPassword.send', 'Send reset link');
        }
    });

    document.body.appendChild(overlay);
    emailInput.focus();
}

function createInput(type, placeholder, required) {
    const input = document.createElement('input');
    input.type = type;
    input.placeholder = placeholder;
    input.required = required;
    input.className = 'form-input';
    return input;
}
