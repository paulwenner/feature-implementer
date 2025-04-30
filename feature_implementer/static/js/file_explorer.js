/**
 * Manages the file explorer functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initFileExplorer();
    updateSelectedFilesList();
    // Add listener for the refresh button
    const refreshButton = document.getElementById('refresh-file-tree-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshFileTree);
    }
});

function initFileExplorer() {
    const fileTreeContainer = document.querySelector('.file-tree');

    if (!fileTreeContainer) return;

    // Use event delegation for all interactions besides folder toggle (which uses inline onclick)
    fileTreeContainer.addEventListener('click', function(event) {
        // If clicked on a folder-label, don't interfere - let the inline toggleFolder handle it
        if (event.target.closest('.folder-label')) {
            // Don't process any more handlers
            return;
        }
        
        // Use event delegation for file preview toggle (on file-info div)
        const fileInfo = event.target.closest('.file-info');
        if (fileInfo && fileInfo.hasAttribute('onclick')) { // Check if preview is enabled
            const path = fileInfo.getAttribute('data-path');
            const filename = fileInfo.getAttribute('data-filename');
            if (path && filename) {
                toggleFilePreview(path, filename);
            }
            return; // Prevent other handlers
        }
        
        // Use event delegation for preview button
        const previewButton = event.target.closest('.action-button[data-action="preview"]');
        if (previewButton && !previewButton.disabled) {
            const path = previewButton.getAttribute('data-path');
            const filename = previewButton.getAttribute('data-filename');
            if (path && filename) {
                toggleFilePreview(path, filename);
            }
            return;
        }
        
        // Use event delegation for add file button
        const addButton = event.target.closest('.action-button[data-action="add"]');
        if (addButton) {
            const path = addButton.getAttribute('data-path');
            const filename = addButton.getAttribute('data-filename');
            if (path && filename) {
                addFileToContext(path, filename);
            }
            return;
        }
        
        // Use event delegation for checkbox changes
        const checkbox = event.target.closest('input[name="context_files"]');
        if (checkbox) {
            updateSelectedFilesList();
            // Don't return here, let checkbox default behavior proceed
        }
    });
}

function updateSelectedFilesList() {
    const list = document.getElementById('selected-files-list');
    const checked = document.querySelectorAll('input[name="context_files"]:checked');
    if (checked.length === 0) {
        list.innerHTML = '<p class="text-secondary">No files selected yet. Click the + button next to files to add them.</p>';
        return;
    }
    let html = '<ul class="selected-files">';
    checked.forEach(cb => {
        const label = cb.closest('.file-label');
        const name = label.querySelector('.filename').textContent;
        html += `<li>
            <span class="selected-file-name">${name}</span>
            <span class="selected-file-path">${cb.value}</span>
            <button type="button" class="action-button" onclick="removeFile('${cb.value}')">
                <i class="fas fa-times"></i>
            </button>
        </li>`;
    });
    html += '</ul>';
    list.innerHTML = html;
}

function removeFile(filepath) {
    const cb = document.querySelector(`input[value="${filepath}"]`);
    if (cb) {
        cb.checked = false;
        updateSelectedFilesList();
    }
}

function clearSelectedFiles() {
    document.querySelectorAll('input[name="context_files"]:checked').forEach(function(checkbox) {
        checkbox.checked = false;
    });
    
    updateSelectedFilesList();
}

function toggleFilePreview(filepath, filename) {
    // Get file extension
    const filenameLC = filename.toLowerCase();
    const fileExt = filenameLC.includes('.') ? filenameLC.split('.').pop() : '';
    
    // Check if file is a non-previewable type
    const nonPreviewableExtensions = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico', 'xlsx', 'xls', 'docx', 'doc', 'pptx', 'ppt', 'pdf', 'zip', 'gz', 'tar', 'rar'];
    
    if (nonPreviewableExtensions.includes(fileExt)) {
        showToast(`Cannot preview "${filename}": This file type cannot be previewed.`, 'error');
        return;
    }
    
    const area = document.getElementById('file-preview');
    const nameEl = document.getElementById('preview-filename');
    const contentEl = document.getElementById('preview-content');
    const closeBtn = document.querySelector('.close-preview-button');

    if (area.classList.contains('show') && nameEl.textContent === filename) {
        return closeFilePreview();
    }

    area.classList.add('show');
    nameEl.textContent = filename;
    contentEl.textContent = 'Loading file content...';
    if (closeBtn) closeBtn.style.display = 'block';

    fetch('/get_file_content?path=' + encodeURIComponent(filepath))
        .then(res => res.ok ? res.json() : Promise.reject(res.statusText))
        .then(data => {
            if (data.error) throw new Error(data.error);
            contentEl.textContent = data.content;
        })
        .catch(err => contentEl.textContent = 'Error loading file: ' + err);
}

function closeFilePreview() {
    const area = document.getElementById('file-preview');
    const closeBtn = document.querySelector('.close-preview-button');
    area.classList.remove('show'); 
    if (closeBtn) closeBtn.style.display = 'none'; 
    
    // Also hide the preview content area itself if needed
    area.style.display = 'none'; 
}

// Function to handle adding a file via the plus button
function addFileToContext(filepath, filename) {
    const checkboxId = `file_${filepath.replace(/\//g, '_').replace(/\./g, '_')}`;
    const checkbox = document.getElementById(checkboxId);
    if (checkbox) {
        checkbox.checked = true;
        updateSelectedFilesList();
        showToast(`Added "${filename}"`, 'success');
    }
}

// Function to toggle folder expand/collapse state
function toggleFolder(folderLabel) {
    console.log('toggleFolder called directly for:', folderLabel);
    
    // Make sure we have a valid folder label element
    if (!folderLabel || !folderLabel.classList.contains('folder-label')) {
        console.error('Invalid folder label element:', folderLabel);
        return;
    }
    
    const content = folderLabel.nextElementSibling;
    const folderArrow = folderLabel.querySelector('.folder-arrow i');
    
    if (content && folderArrow) {
        if (!content.style.display || content.style.display === 'none') {
            // Opening folder
            content.style.display = 'block';
            folderArrow.classList.remove('fa-chevron-right');
            folderArrow.classList.add('fa-chevron-down'); // Indicate open state
            console.log('Folder opened');
        } else {
            // Closing folder
            content.style.display = 'none';
            folderArrow.classList.remove('fa-chevron-down');
            folderArrow.classList.add('fa-chevron-right'); // Indicate closed state
            console.log('Folder closed');
        }
    } else {
        console.error('Missing content or arrow elements for folder:', folderLabel);
    }
}

// Function to collect paths of all expanded folders
function getExpandedFolderPaths() {
    const expandedFolders = document.querySelectorAll('.folder-content[style="display: block;"]');
    const expandedPaths = [];
    
    console.log(`Found ${expandedFolders.length} expanded folders to save`);
    
    expandedFolders.forEach(folder => {
        // Construct path from folder hierarchy
        let currentElement = folder;
        let path = [];
        
        // Traverse up to find all parent folder names
        while (currentElement) {
            const folderLabel = currentElement.previousElementSibling;
            if (folderLabel && folderLabel.classList.contains('folder-label')) {
                const folderName = folderLabel.querySelector('.folder-name');
                if (folderName) {
                    path.unshift(folderName.textContent.trim());
                }
            }
            
            // Move up to parent folder's content
            const parentFolder = currentElement.closest('.folder');
            if (!parentFolder) break;
            
            currentElement = parentFolder.parentElement;
            // If we're still within the file-tree, continue
            if (!currentElement || !currentElement.closest('.file-tree')) break;
        }
        
        if (path.length > 0) {
            const folderPath = path.join('/');
            expandedPaths.push(folderPath);
            console.log(`Saved expanded folder path: ${folderPath}`);
        }
    });
    
    return expandedPaths;
}

// Function to expand folders based on saved paths
function restoreExpandedFolders(expandedPaths) {
    if (!expandedPaths || expandedPaths.length === 0) {
        console.log('No expanded paths to restore');
        return;
    }
    
    console.log(`Attempting to restore ${expandedPaths.length} expanded folders`);
    
    const fileTree = document.querySelector('.file-tree');
    if (!fileTree) {
        console.warn('File tree not found for restoration');
        return;
    }
    
    // First pass: expand all top-level folders that match
    expandedPaths.forEach(path => {
        const topFolder = path.split('/')[0];
        const topFolderElements = fileTree.querySelectorAll('.folder-label');
        
        topFolderElements.forEach(label => {
            const folderName = label.querySelector('.folder-name');
            if (folderName && folderName.textContent.trim() === topFolder) {
                const content = label.nextElementSibling;
                const folderArrow = label.querySelector('.folder-arrow i');
                
                if (content && folderArrow) {
                    content.style.display = 'block';
                    folderArrow.classList.remove('fa-chevron-right');
                    folderArrow.classList.add('fa-chevron-down');
                    console.log(`Expanded top-level folder: ${topFolder}`);
                }
            }
        });
    });
    
    // Second pass: expand specific paths in full
    expandedPaths.forEach(path => {
        const pathParts = path.split('/');
        let currentLevel = fileTree;
        let currentPath = '';
        
        // Navigate through each path segment
        for (let i = 0; i < pathParts.length; i++) {
            currentPath += (i > 0 ? '/' : '') + pathParts[i];
            
            // Find folder at this level
            const folderLabels = currentLevel.querySelectorAll('.folder-label');
            let found = false;
            
            for (const label of folderLabels) {
                const folderName = label.querySelector('.folder-name');
                if (folderName && folderName.textContent.trim() === pathParts[i]) {
                    // Found the folder, expand it
                    const content = label.nextElementSibling;
                    const folderArrow = label.querySelector('.folder-arrow i');
                    
                    if (content && folderArrow) {
                        content.style.display = 'block';
                        folderArrow.classList.remove('fa-chevron-right');
                        folderArrow.classList.add('fa-chevron-down');
                        console.log(`Expanded folder in path: ${currentPath}`);
                    }
                    
                    // Continue with the next level
                    currentLevel = content;
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                console.log(`Could not find folder in path: ${currentPath}`);
                break; // Path no longer exists, stop trying
            }
        }
    });
}

// Refreshes the file tree by fetching new data from the server
async function refreshFileTree() {
    const fileTreeContainer = document.querySelector('.file-tree');
    const refreshButtonIcon = document.querySelector('#refresh-file-tree-button i');
    
    if (!fileTreeContainer || !refreshButtonIcon) return;

    // Save expanded folder state before refresh
    const expandedPaths = getExpandedFolderPaths();
    
    // Save selected files state
    const selectedFiles = getSelectedFiles();

    // Indicate loading state
    refreshButtonIcon.classList.add('fa-spin');
    fileTreeContainer.style.opacity = '0.5'; // Dim the tree during load

    try {
        const response = await fetch('/refresh_file_tree');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.html) {
            fileTreeContainer.innerHTML = data.html;
            // Restore expanded folders
            restoreExpandedFolders(expandedPaths);
            // Restore selected files
            restoreSelectedFiles(selectedFiles);
            // No need to re-call initFileExplorer due to event delegation
        } else if (data.error) {
            showToast(`Error refreshing file tree: ${data.error}`, 'error');
            fileTreeContainer.innerHTML = `<p class="error">Error loading file tree: ${data.error}</p>`;
        } else {
             showToast('Received empty response during refresh.', 'warning');
             fileTreeContainer.innerHTML = `<p class="error">Empty response received.</p>`;
        }
    } catch (error) {
        console.error('Failed to refresh file tree:', error);
        showToast(`Failed to refresh file tree: ${error.message}`, 'error');
        fileTreeContainer.innerHTML = `<p class="error">Failed to load file tree. ${error.message}</p>`;
    } finally {
        // Remove loading state
        refreshButtonIcon.classList.remove('fa-spin');
        fileTreeContainer.style.opacity = '1';
    }
}

// Function to get all currently selected files
function getSelectedFiles() {
    const selectedCheckboxes = document.querySelectorAll('input[name="context_files"]:checked');
    const selected = [];
    
    selectedCheckboxes.forEach(checkbox => {
        selected.push({
            path: checkbox.value,
            filename: checkbox.getAttribute('data-filename')
        });
    });
    
    console.log(`Saved ${selected.length} selected files before refresh`);
    return selected;
}

// Function to restore previously selected files
function restoreSelectedFiles(selectedFiles) {
    if (!selectedFiles || selectedFiles.length === 0) {
        console.log('No selected files to restore');
        return;
    }
    
    console.log(`Attempting to restore ${selectedFiles.length} selected files`);
    
    selectedFiles.forEach(file => {
        const checkbox = document.querySelector(`input[value="${file.path}"]`);
        if (checkbox) {
            checkbox.checked = true;
            console.log(`Restored selection for file: ${file.filename}`);
        } else {
            console.log(`Could not find checkbox for file: ${file.filename} (${file.path})`);
        }
    });
    
    // Update the selected files list in the UI
    updateSelectedFilesList();
}

// Utility function for showing toast messages (assuming you have a toast mechanism)
function showToast(message, type = 'info') {
    // Replace this with your actual toast implementation
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Example: alert(`[${type.toUpperCase()}] ${message}`);
    // Or integrate with a library like Toastify.js
} 