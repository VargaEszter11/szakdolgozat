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
    icon.style.background = 'var(--color-accent-subtle, #e8f0fe)';

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
    form.className = 'login-form';

    const { group: emailGroup, input: emailInput } = createFormGroup({
        type: 'email',
        id: 'forgotPasswordEmail',
        label: forgotPasswordT('forgotPassword.email', 'Email *'),
        placeholder: forgotPasswordT('forgotPassword.emailPlaceholder', 'Your registered email'),
        required: true,
        autocomplete: 'email',
    });

    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';

    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.className = 'custom-modal-btn custom-modal-btn-secondary';
    cancelBtn.textContent = forgotPasswordT('forgotPassword.cancel', 'Cancel');

    const sendBtn = document.createElement('button');
    sendBtn.type = 'submit';
    sendBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    sendBtn.textContent = forgotPasswordT('forgotPassword.send', 'Send reset link');

    actions.appendChild(cancelBtn);
    actions.appendChild(sendBtn);

    form.appendChild(emailGroup);
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

    // Always show a generic success message
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
                showError(apiErrorDetail(data, forgotPasswordT('forgotPassword.sendFailed', 'Could not send reset email.')));
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

function createFormGroup({ type, id, label, placeholder, required, autocomplete }) {
    const group = document.createElement('div');
    group.className = 'form-group';

    const labelEl = document.createElement('label');
    labelEl.className = 'form-label';
    labelEl.htmlFor = id;
    labelEl.textContent = label;

    const input = document.createElement('input');
    input.type = type;
    input.id = id;
    input.name = id;
    input.placeholder = placeholder;
    input.required = Boolean(required);
    input.className = 'form-input';
    if (autocomplete) {
        input.autocomplete = autocomplete;
    }

    group.appendChild(labelEl);
    group.appendChild(input);
    return { group, input };
}
