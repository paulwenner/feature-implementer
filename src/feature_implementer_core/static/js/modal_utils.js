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
 