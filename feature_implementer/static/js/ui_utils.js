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