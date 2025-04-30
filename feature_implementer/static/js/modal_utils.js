/**
 * Utility functions for managing modals
 */

/**
 * Shows a modal dialog by ID
 * @param {string} modalId - The ID of the modal to show
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById('modal-overlay');
    
    if (modal && overlay) {
        modal.style.display = 'block';
        overlay.style.display = 'block';
    } else {
        console.error(`Modal or overlay not found: ${modalId}`);
    }
}

/**
 * Hides a modal dialog by ID
 * @param {string} modalId - The ID of the modal to hide
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const overlay = document.getElementById('modal-overlay');
    
    if (modal) {
        modal.style.display = 'none';
    }
    
    // Only hide the overlay if no other modals are visible
    if (overlay) {
        const visibleModals = document.querySelectorAll('.modal[style*="display: block"]');
        if (visibleModals.length <= 1) {
            overlay.style.display = 'none';
        }
    }
}

/**
 * Shows a toast notification
 * @param {string} message - The message to display
 * @param {string} [type='info'] - The type of toast (success, error, info, warning)
 * @param {number} [duration=3000] - How long to show the toast in milliseconds
 */
function showToast(message, type = 'info', duration = 3000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Show with animation
    setTimeout(() => {
        toast.classList.add('visible');
    }, 10);
    
    // Auto-remove after duration
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300); // Match the CSS transition time
    }, duration);
} 