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
    showModal({
        title: 'Success',
        message,
        type: 'success',
        onClose
    });
}

function showError(message, onClose) {
    showModal({
        title: 'Error',
        message,
        type: 'error',
        onClose
    });
}
