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
    
    /**
     * Rough client-side GPT token estimator
     * @param {string} text - the full prompt text
     * @returns {number} estimated token count
     */
    function estimateTokens(text) {
        // On average 1 token ≈ 4 characters
        return Math.ceil(text.length / 4);
    }
    
    // Preset selector is initialized in preset_handler.js
    
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
        showModal('prompt-modal');
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
                const promptText = data.prompt || '';
                // Character count
                const charCountValue = data.char_count != null ? data.char_count : promptText.length;
                charCountInfo.textContent = `${charCountValue.toLocaleString()} characters`;
                // Token estimate with fallback to client-side estimator
                let tokenCount;
                if (data.token_estimate && data.token_estimate > 0) {
                    tokenCount = data.token_estimate;
                } else {
                    tokenCount = estimateTokens(promptText);
                }
                tokenEstimateInfo.textContent = `~${tokenCount.toLocaleString()} tokens`;
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
            return;
        }
        
        // Use clipboard API to copy text
        navigator.clipboard.writeText(promptText)
            .catch(err => {
                console.error('Error copying text: ', err);
            });
    }
    
    /**
     * Exports the generated prompt as a markdown file
     */
    function exportGeneratedPrompt() {
        const promptText = promptContent.textContent || '';
        if (!promptText.trim()) {
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
    }
});

/**
 * Closes the prompt modal dialog
 */
function closePromptModal() {
    closeModal('prompt-modal');
} 