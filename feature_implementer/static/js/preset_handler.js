/**
 * Handles preset management functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    const addPresetButton = document.getElementById('add-preset-button');
    const addPresetModal = document.getElementById('add-preset-modal');
    const modalOverlay = document.getElementById('modal-overlay');
    const savePresetButton = document.getElementById('save-preset-button');
    
    // Show/hide "Save as Preset" button based on selected files
    function updateAddPresetButtonVisibility() {
        const selectedFiles = getSelectedFiles();
        if (addPresetButton) {
            addPresetButton.style.display = selectedFiles.length > 0 ? 'block' : 'none';
        }
    }
    
    // Initialize "Save as Preset" button visibility
    updateAddPresetButtonVisibility();
    
    // Listen for changes in the selected files list
    document.addEventListener('selectedFilesChanged', function() {
        updateAddPresetButtonVisibility();
    });
    
    // Add preset button functionality
    if (addPresetButton) {
        addPresetButton.addEventListener('click', function() {
            showAddPresetModal();
        });
    }
    
    // Save preset button functionality
    if (savePresetButton) {
        savePresetButton.addEventListener('click', function() {
            savePreset();
        });
    }
    
    /**
     * Shows the add preset modal with currently selected files
     */
    function showAddPresetModal() {
        // Get all selected files
        const selectedFiles = getSelectedFiles();
        if (selectedFiles.length === 0) {
            showToast('No files selected', 'error');
            return;
        }
        
        // Show the modal overlay and preset modal
        modalOverlay.style.display = 'block';
        addPresetModal.style.display = 'flex';
        
        // Clear any previous errors
        document.getElementById('preset-error').style.display = 'none';
        document.getElementById('preset-error').textContent = '';
        
        // Clear the input field
        document.getElementById('preset-name').value = '';
        
        // Populate the files summary
        const filesSummaryEl = document.getElementById('preset-files-summary');
        let filesHtml = '<p>Selected files:</p><ul class="preset-file-list">';
        
        selectedFiles.forEach(file => {
            const displayName = file.filename || 
                               (typeof file.path === 'string' ? file.path.split('/').pop() : 'Unknown file');
            filesHtml += `<li>${displayName}</li>`;
        });
        
        filesHtml += '</ul>';
        filesSummaryEl.innerHTML = filesHtml;
    }
});

/**
 * Closes the add preset modal
 */
function closeAddPresetModal() {
    document.getElementById('add-preset-modal').style.display = 'none';
    
    // Only hide the overlay if the prompt modal is also hidden
    if (document.getElementById('prompt-modal').style.display === 'none') {
        document.getElementById('modal-overlay').style.display = 'none';
    }
}

/**
 * Saves the current selected files as a preset
 */
function savePreset() {
    const presetName = document.getElementById('preset-name').value.trim();
    const errorEl = document.getElementById('preset-error');
    
    errorEl.style.display = 'none'; // Reset error state
    
    if (!presetName) {
        errorEl.textContent = 'Please enter a preset name';
        errorEl.style.display = 'block';
        return;
    }
    
    const selectedFiles = getSelectedFiles();
    if (selectedFiles.length === 0) {
        errorEl.textContent = 'No files selected';
        errorEl.style.display = 'block';
        return;
    }
    
    // Extract just the paths as strings and validate
    const filePaths = [];
    for (const file of selectedFiles) {
        if (!file || !file.path) {
            console.warn('Invalid file object in selection:', file);
            continue;
        }
        // Ensure it's a string
        filePaths.push(String(file.path));
    }
    
    if (filePaths.length === 0) {
        errorEl.textContent = 'No valid file paths in selection';
        errorEl.style.display = 'block';
        return;
    }
    
    // Create payload
    const payload = {
        name: presetName,
        files: filePaths
    };
    
    // Debug
    console.log('Sending preset data:', JSON.stringify(payload));
    
    // Show loading state
    const saveButton = document.getElementById('save-preset-button');
    if (saveButton) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }
    
    // Send the request to the server
    fetch('/presets', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => {
        // Reset button state
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.innerHTML = 'Save Preset';
        }
        
        // Check if response is OK first
        if (!response.ok) {
            return response.text().then(text => {
                console.error('Error response:', response.status, response.statusText);
                console.error('Response content:', text.substring(0, 500));
                
                // Try to parse as JSON if possible
                try {
                    const json = JSON.parse(text);
                    throw new Error(json.error || 'Server error');
                } catch (e) {
                    // If not JSON, show relevant part of the HTML error
                    if (text.includes('<!doctype')) {
                        throw new Error('Server error: Received HTML instead of JSON');
                    }
                    throw new Error(`Server error: ${text.substring(0, 100)}`);
                }
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            // Handle error
            errorEl.textContent = data.error;
            errorEl.style.display = 'block';
        } else {
            // Success - refresh presets
            updatePresets(data.presets);
            closeAddPresetModal();
            showToast(`Preset "${presetName}" saved successfully`, 'success');
        }
    })
    .catch(error => {
        console.error('Preset save error:', error);
        errorEl.textContent = `Error saving preset: ${error.message}`;
        errorEl.style.display = 'block';
    });
}

/**
 * Handles preset selection from the radio buttons
 * @param {string} presetName - The name of the selected preset
 */
function handlePresetSelection(presetName) {
    if (!presetName) {
        // "None" selected - clear selections
        clearSelectedFiles();
        return;
    }
    
    const preset = window.presets[presetName];
    if (!preset || !preset.files || !Array.isArray(preset.files)) {
        showToast('Invalid preset', 'error');
        return;
    }
    
    // Clear existing selections
    clearSelectedFiles();
    
    // Select all files from the preset
    preset.files.forEach(filePath => {
        const checkbox = document.querySelector(`input[value="${filePath}"]`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });
    
    // Update the UI
    updateSelectedFilesList();
    showToast(`Loaded preset "${presetName}"`, 'success');
}

/**
 * Deletes a preset
 * @param {string} presetName - The name of the preset to delete
 */
function deletePreset(presetName) {
    if (!confirm(`Are you sure you want to delete the preset "${presetName}"?`)) {
        return;
    }
    
    fetch(`/presets/${encodeURIComponent(presetName)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
        } else {
            // Update presets in UI
            updatePresets(data.presets);
            showToast(`Preset "${presetName}" deleted`, 'success');
        }
    })
    .catch(error => {
        console.error("Error deleting preset:", error);
        showToast(`Error deleting preset: ${error.message}`, 'error');
    });
}

/**
 * Updates the presets in the UI
 * @param {Object} presets - The updated presets object
 */
function updatePresets(presets) {
    // Update the global presets object
    window.presets = presets;
    
    // Update the preset selector
    const presetContainer = document.querySelector('.preset-options');
    if (!presetContainer) return;
    
    // Keep the 'None' option
    let html = `
        <label class="preset-option">
            <input type="radio" name="preset" value="" checked> None
        </label>
    `;
    
    // Add all presets
    for (const [name, _] of Object.entries(presets)) {
        html += `
            <label class="preset-option">
                <input type="radio" name="preset" value="${name}"> ${name}
                <button type="button" class="action-button delete-preset-btn" data-preset="${name}" title="Delete preset">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </label>
        `;
    }
    
    presetContainer.innerHTML = html;
    
    // Add click handlers for delete buttons
    document.querySelectorAll('.delete-preset-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const presetName = this.getAttribute('data-preset');
            deletePreset(presetName);
        });
    });
    
    // Reinitialize the preset selector
    initPresetSelector();
}

/**
 * Test function to diagnose JSON issues - called from the console
 */
function testJsonEndpoint() {
    const testData = {
        test: "Testing JSON endpoint",
        timestamp: new Date().toISOString()
    };
    
    console.log("Sending test data:", testData);
    
    fetch('/debug/test-json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(testData)
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                console.error("Response not OK:", response.status, response.statusText);
                try {
                    return JSON.parse(text);
                } catch (e) {
                    console.error("Failed to parse response as JSON:", text.substring(0, 500));
                    throw new Error(`Non-JSON response: ${text.substring(0, 100)}`);
                }
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("Test JSON endpoint response:", data);
        return data;
    })
    .catch(error => {
        console.error("Error testing JSON endpoint:", error);
    });
}

// Make it available globally
window.testJsonEndpoint = testJsonEndpoint; 