/**
 * UI utility functions for notifications and common interactions
 */

function handlePresetSelection(selectedPresetName) {
    // Make sure presets is defined globally
    if (typeof presets === 'undefined') {
        console.error('Presets data not available');
        return;
    }
    
    console.log("UI handling preset selection:", selectedPresetName);
    
    // If "None" selected, clear all
    if (!selectedPresetName) {
        // Clear selections
        const allFileCheckboxes = document.querySelectorAll('input[name="context_files"]');
        allFileCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Remove all visual highlighting
        document.querySelectorAll('.file-label.preset-file').forEach(label => {
            label.classList.remove('preset-file');
        });
        
        updateSelectedFilesList();
        return;
    }
    
    // Get the preset files array if it exists
    const preset = selectedPresetName ? presets[selectedPresetName] || {} : {};
    console.log("Preset data:", preset);
    
    // Handle both formats: {files: [...]} and {files: {0: "file1", 1: "file2"}}
    let presetFiles = preset.files || [];
    
    // Check if preset.files is an object but not an array
    if (preset.files && typeof preset.files === 'object' && !Array.isArray(preset.files)) {
        // Convert object to array
        presetFiles = Object.values(preset.files);
    }
    
    // Ensure we have an array to work with
    if (!Array.isArray(presetFiles)) {
        console.warn('Invalid preset files format:', selectedPresetName, presetFiles);
        return;
    }
    
    // Ensure all values in the array are strings
    presetFiles = presetFiles.map(file => String(file));
    
    // Always clear all selections first when using radio buttons
    // Clear selections
    const allFileCheckboxes = document.querySelectorAll('input[name="context_files"]');
    allFileCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Remove all visual highlighting first
    document.querySelectorAll('.file-label.preset-file').forEach(label => {
        label.classList.remove('preset-file');
    });

    // Now select only the files from the chosen preset
    allFileCheckboxes.forEach(checkbox => {
        const filePath = checkbox.value;
        
        // Check for exact match
        const exactMatch = presetFiles.includes(filePath);
        
        // Check for basename match with absolute paths
        const isAbsolutePathMatch = presetFiles.some(presetPath => {
            // If preset path is absolute and ends with the file path
            if (presetPath.startsWith('/') && filePath.includes('/')) {
                const checkboxBasename = filePath.split('/').pop();
                const presetBasename = presetPath.split('/').pop();
                return checkboxBasename === presetBasename && 
                      (presetPath.endsWith(filePath) || filePath.endsWith(presetPath));
            }
            return false;
        });
        
        if (exactMatch || isAbsolutePathMatch) {
            checkbox.checked = true;
            
            // Add visual highlight
            const fileLabel = checkbox.closest('label');
            if (fileLabel) {
                fileLabel.classList.add('preset-file');
            }
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