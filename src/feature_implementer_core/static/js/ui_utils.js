/**
 * UI utility functions for notifications and common interactions
 */

function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        toast.classList.add('toast-fade-out');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function handlePresetSelection(selectedPresetName) {
    // Make sure presets is defined globally
    if (typeof presets === 'undefined') {
        console.error('Presets data not available');
        return;
    }
    
    const presetFiles = selectedPresetName ? presets[selectedPresetName] || [] : [];
    const allFileCheckboxes = document.querySelectorAll('input[name="context_files"]');

    allFileCheckboxes.forEach(checkbox => {
        if (presetFiles.includes(checkbox.value)) {
            checkbox.checked = true;
        } else {
            checkbox.checked = false;
        }
    });

    updateSelectedFilesList();
}

/**
 * Shows a modal dialog and the overlay.
 * @param {string} modalId - The ID of the modal element to show.
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    const modalOverlay = document.getElementById('modal-overlay');

    if (modal) {
        modal.style.display = 'flex'; // Use flex for modal layout consistency
    } else {
        console.error(`Modal with ID "${modalId}" not found.`);
        return;
    }

    if (modalOverlay) {
        modalOverlay.style.display = 'block';
    } else {
        // Fallback: Create overlay if it doesn't exist (should not happen with base.html)
        console.warn('Modal overlay not found, creating one.');
        const overlay = document.createElement('div');
        overlay.id = 'modal-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
        overlay.style.zIndex = '1000';
        overlay.style.display = 'block';
        document.body.appendChild(overlay);
         // Add click listener to close modals when overlay is clicked
        overlay.addEventListener('click', () => {
            // Find all visible modals and close them
            document.querySelectorAll('.modal[style*="display: flex"], .modal[style*="display: block"]').forEach(visibleModal => {
                closeModal(visibleModal.id);
            });
        });
    }

    // Add event listener for Escape key
    document.addEventListener('keydown', handleEscKey);
}

/**
 * Hides a modal dialog and potentially the overlay if no other modals are open.
 * @param {string} modalId - The ID of the modal element to hide.
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const modalOverlay = document.getElementById('modal-overlay');

    if (modal) {
        modal.style.display = 'none';
    } else {
        console.error(`Modal with ID "${modalId}" not found.`);
    }

    // Check if any other modals are still visible
    const anyModalVisible = Array.from(document.querySelectorAll('.modal')) // Assuming modals have a common class '.modal'
                               .some(m => m.style.display === 'flex' || m.style.display === 'block');

    if (modalOverlay && !anyModalVisible) {
        modalOverlay.style.display = 'none';
    }

    // Remove Escape key listener if no modals are open
    if (!anyModalVisible) {
        document.removeEventListener('keydown', handleEscKey);
    }
}

/**
 * Handles the Escape key press to close the top-most visible modal.
 * @param {KeyboardEvent} event - The keydown event.
 */
function handleEscKey(event) {
    if (event.key === 'Escape') {
        // Find the last opened (visually top-most) modal that is visible
        const visibleModals = Array.from(document.querySelectorAll('.modal[style*="display: flex"], .modal[style*="display: block"]'));
        if (visibleModals.length > 0) {
            // Close the last modal in the NodeList (likely the top-most)
            closeModal(visibleModals[visibleModals.length - 1].id);
        }
    }
}

// Ensure all modal elements have the 'modal' class for the logic above to work
// We'll add this class in the HTML templates. 