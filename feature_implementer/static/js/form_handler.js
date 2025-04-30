/**
 * Handles form submission and prompt generation
 */
document.addEventListener('DOMContentLoaded', function() {
    const generateForm = document.getElementById('generate-form');
    const promptModal = document.getElementById('prompt-modal');
    const modalOverlay = document.getElementById('modal-overlay');
    const promptContent = document.getElementById('prompt-modal-content');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorArea = document.getElementById('prompt-error-area');
    const charCountInfo = document.getElementById('char-count-info');
    const tokenEstimateInfo = document.getElementById('token-estimate-info');
    
    // Set up preset selector
    initPresetSelector();
    
    // Bind the form submit event
    if (generateForm) {
        generateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleFormSubmit(this);
        });
    }
    
    // Copy button functionality
    document.getElementById('copy-button').addEventListener('click', function() {
        copyGeneratedPrompt();
    });
    
    // Export button functionality
    document.getElementById('export-button').addEventListener('click', function() {
        exportGeneratedPrompt();
    });
    
    /**
     * Handles form submission and generates a prompt
     * @param {HTMLFormElement} form - The form element containing context files and other inputs
     */
    function handleFormSubmit(form) {
        // Show the modal with loading indicator
        promptModal.style.display = 'block';
        modalOverlay.style.display = 'block';
        promptContent.style.display = 'none';
        loadingIndicator.style.display = 'block';
        errorArea.style.display = 'none';
        charCountInfo.textContent = '';
        tokenEstimateInfo.textContent = '';
        
        // Use FormData to handle the submission
        const formData = new FormData(form);
        
        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';
            
            if (data.error) {
                // Handle error
                errorArea.textContent = data.error;
                errorArea.style.display = 'block';
            } else {
                // Display the successful result
                promptContent.textContent = data.prompt;
                promptContent.style.display = 'block';
                
                // Update metadata info
                if (data.char_count) {
                    charCountInfo.textContent = `${data.char_count.toLocaleString()} characters`;
                }
                if (data.token_estimate) {
                    tokenEstimateInfo.textContent = `~${data.token_estimate.toLocaleString()} tokens`;
                }
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            errorArea.textContent = `Network error: ${error.message}`;
            errorArea.style.display = 'block';
        });
    }
    
    /**
     * Copies the generated prompt to clipboard
     * @returns {Promise<void>} Promise resolving when copy is complete
     */
    function copyGeneratedPrompt() {
        const promptText = promptContent.textContent || '';
        if (!promptText.trim()) {
            showToast('No content to copy', 'error');
            return;
        }
        
        // Use clipboard API to copy text
        navigator.clipboard.writeText(promptText)
            .then(() => {
                showToast('Prompt copied to clipboard!', 'success');
            })
            .catch(err => {
                console.error('Error copying text: ', err);
                showToast('Failed to copy: ' + err, 'error');
            });
    }
    
    /**
     * Exports the generated prompt as a markdown file
     */
    function exportGeneratedPrompt() {
        const promptText = promptContent.textContent || '';
        if (!promptText.trim()) {
            showToast('No content to export', 'error');
            return;
        }
        
        // Create a blob and download link
        const blob = new Blob([promptText], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        // Set filename with timestamp
        const date = new Date();
        const timestamp = date.toISOString().replace(/[:.]/g, '-').substring(0, 19);
        a.download = `implementation-prompt-${timestamp}.md`;
        
        a.href = url;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
        
        showToast('Prompt exported as Markdown file', 'success');
    }
});

/**
 * Initializes the preset selector radio buttons with event listeners
 */
function initPresetSelector() {
    const presetRadios = document.querySelectorAll('input[name="preset"]');
    presetRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            handlePresetSelection(this.value);
        });
    });
}

/**
 * Closes the prompt modal dialog
 */
function closePromptModal() {
    document.getElementById('prompt-modal').style.display = 'none';
    document.getElementById('modal-overlay').style.display = 'none';
} 