function showModal(options) {
    const {
        title = 'Notification',
        message = '',
        type = 'success', // 'success' or 'error'
        onClose = null
    } = options;

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'custom-modal-overlay';

    // Create modal
    const modal = document.createElement('div');
    modal.className = 'custom-modal';

    // Icon
    const icon = document.createElement('div');
    icon.className = `custom-modal-icon ${type}`;
    icon.innerHTML = type === 'success' ? '✓' : '✕';

    // Title
    const titleEl = document.createElement('h3');
    titleEl.className = 'custom-modal-title';
    titleEl.textContent = title;

    // Header (icon + title)
    const header = document.createElement('div');
    header.className = 'custom-modal-header';
    header.appendChild(icon);
    header.appendChild(titleEl);

    // Message
    const messageEl = document.createElement('p');
    messageEl.className = 'custom-modal-message';
    messageEl.textContent = message;

    // OK button
    const okBtn = document.createElement('button');
    okBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    okBtn.textContent = 'OK';

    // Actions container
    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';
    actions.appendChild(okBtn);

    // Assemble modal
    modal.appendChild(header);
    modal.appendChild(messageEl);
    modal.appendChild(actions);
    overlay.appendChild(modal);

    // Close function
    const closeModal = () => {
        overlay.style.animation = 'fadeOut 0.2s ease-in-out';
        setTimeout(() => {
            document.body.removeChild(overlay);
            if (onClose) onClose();
        }, 200);
    };

    // Event listeners
    okBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });

    // Add fadeOut animation
    if (!document.querySelector('#modal-fadeout-animation')) {
        const style = document.createElement('style');
        style.id = 'modal-fadeout-animation';
        style.textContent = `
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    // Show modal
    document.body.appendChild(overlay);
}

// Shorthand functions
function showSuccess(message, onClose) {
    if (typeof onClose === 'function') {
        onClose();
    }
}

function showError(message, onClose) {
    showModal({
        title: 'Error',
        message,
        type: 'error',
        onClose
    });
}

function showConfirm(message, onConfirm, onCancel) {
    function tModal(key, fallback) {
        if (!(window.i18n && typeof window.i18n.t === 'function')) return fallback;
        var val = window.i18n.t(key);
        return (!val || val === key) ? fallback : val;
    }

    const overlay = document.createElement('div');
    overlay.className = 'custom-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'custom-modal';

    const icon = document.createElement('div');
    icon.className = 'custom-modal-icon warning';
    icon.innerHTML = '!';

    const titleEl = document.createElement('h3');
    titleEl.className = 'custom-modal-title';
    titleEl.textContent = tModal('common.areYouSure', 'Are you sure?');

    const header = document.createElement('div');
    header.className = 'custom-modal-header';
    header.appendChild(icon);
    header.appendChild(titleEl);

    const messageEl = document.createElement('p');
    messageEl.className = 'custom-modal-message';
    messageEl.textContent = message;

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'custom-modal-btn custom-modal-btn-secondary';
    cancelBtn.textContent = tModal('common.cancel', 'Cancel');

    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'custom-modal-btn custom-modal-btn-primary';
    confirmBtn.textContent = tModal('common.confirm', 'Confirm');

    const actions = document.createElement('div');
    actions.className = 'custom-modal-actions';
    actions.appendChild(cancelBtn);
    actions.appendChild(confirmBtn);

    modal.appendChild(header);
    modal.appendChild(messageEl);
    modal.appendChild(actions);
    overlay.appendChild(modal);

    const close = (callback) => {
        overlay.style.animation = 'fadeOut 0.2s ease-in-out';
        setTimeout(() => {
            document.body.removeChild(overlay);
            if (callback) callback();
        }, 200);
    };

    cancelBtn.addEventListener('click', () => close(onCancel));
    confirmBtn.addEventListener('click', () => close(onConfirm));
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) close(onCancel);
    });

    if (!document.querySelector('#modal-fadeout-animation')) {
        const style = document.createElement('style');
        style.id = 'modal-fadeout-animation';
        style.textContent = `
            @keyframes fadeOut {
                from { opacity: 1; }
                to { opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(overlay);
}
