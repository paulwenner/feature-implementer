/**
 * Manages the file explorer functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initFileExplorer();
    // Unwrap root folder: show only its contents
    unwrapRootFolder();
    // Sort root entries: folders first, then files, alphabetically
    sortFileTree(document.querySelector('.file-tree'));
    updateSelectedFilesList();
    // Add listener for the refresh button
    const refreshButton = document.getElementById('refresh-file-tree-button');
    if (refreshButton) {
        refreshButton.addEventListener('click', async () => {
            await refreshFileTree();
            unwrapRootFolder();
            sortFileTree(document.querySelector('.file-tree'));
        });
    }
    
    // Initialize file search functionality
    initFileSearch();
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
        
        // Handle clicks on checkbox container or custom checkbox representation
        const checkboxContainer = event.target.closest('.checkbox-container');
        if (checkboxContainer && !event.target.matches('input[type="checkbox"]')) {
            // Find the actual checkbox input within this container
            const checkbox = checkboxContainer.querySelector('input[type="checkbox"]');
            if (checkbox) {
                // Toggle the checkbox state
                checkbox.checked = !checkbox.checked;
                // Update the UI
                updateSelectedFilesList();
                return;
            }
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
        
        // Handle clicks on file-label (whole file row) to toggle checkbox
        const fileLabel = event.target.closest('.file-label');
        if (fileLabel && !event.target.closest('.action-button') && !event.target.closest('.checkbox-container') && !event.target.closest('.file-info')) {
            // Find the checkbox within this file label
            const checkbox = fileLabel.querySelector('input[name="context_files"]');
            if (checkbox) {
                // Toggle the checkbox state
                checkbox.checked = !checkbox.checked;
                // Update the UI
                updateSelectedFilesList();
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
        // Dispatch custom event for empty selection
        document.dispatchEvent(new CustomEvent('selectedFilesChanged', { detail: { count: 0 } }));
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
    
    // Dispatch custom event with selection count
    document.dispatchEvent(new CustomEvent('selectedFilesChanged', { 
        detail: { count: checked.length } 
    }));
    
    // Check if any preset needs to be unchecked due to file removal
    if (typeof updatePresetCheckboxes === 'function') {
        updatePresetCheckboxes();
    }
}

function removeFile(filepath) {
    const cb = document.querySelector(`input[value="${filepath}"]`);
    if (cb) {
        cb.checked = false;
        updateSelectedFilesList();
        
        // Check if any preset needs to be unchecked
        if (typeof updatePresetCheckboxes === 'function') {
            updatePresetCheckboxes();
        }
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
        return;
    }
    
    const area = document.getElementById('file-preview');
    const nameEl = document.getElementById('preview-filename');
    const contentEl = document.getElementById('preview-content');
    const closeBtn = document.querySelector('.close-preview-button');

    if (area.classList.contains('show') && nameEl.textContent === filename) {
        return closeFilePreview();
    }

    // Ensure preview area is visible if previously hidden
    area.style.display = 'block';
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
            fileTreeContainer.innerHTML = `<p class="error">Error loading file tree: ${data.error}</p>`;
        } else {
             fileTreeContainer.innerHTML = `<p class="error">Empty response received.</p>`;
        }
    } catch (error) {
        console.error('Failed to refresh file tree:', error);
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

/**
 * Removes the top-level folder label and moves its children into the tree container,
 * so only the contents of the root are shown.
 */
function unwrapRootFolder() {
    const tree = document.querySelector('.file-tree');
    if (!tree) return;
    const rootLabel = tree.querySelector('.folder-label');
    const rootContent = rootLabel?.nextElementSibling;
    if (rootContent && rootContent.classList.contains('folder-content')) {
        tree.innerHTML = rootContent.innerHTML;
    }
}

/**
 * Sorts direct children so that folder nodes come before file nodes, both alphabetically.
 */
function sortFileTree(container) {
    if (!container) return;
    
    // Group direct children into folder units (wrapper elements) or file items
    const children = Array.from(container.children);
    if (children.length === 0) return;
    
    const groups = [];
    for (let i = 0; i < children.length; i++) {
        const el = children[i];
        
        // Check different ways to identify folders vs files
        if (el.classList.contains('folder') || el.classList.contains('directory-section')) {
            // Element has folder class directly
            const nameEl = el.querySelector('.folder-name');
            const name = nameEl ? nameEl.textContent.trim().toLowerCase() : '';
            groups.push({ type: 'folder', name, elements: [el] });
        } 
        else if (el.querySelector('.folder-label')) {
            // Element contains a folder label
            const nameEl = el.querySelector('.folder-name');
            const name = nameEl ? nameEl.textContent.trim().toLowerCase() : '';
            groups.push({ type: 'folder', name, elements: [el] });
        } 
        else if (el.classList.contains('file')) {
            // Element has file class
            const fileNameEl = el.querySelector('.filename');
            const name = fileNameEl ? fileNameEl.textContent.trim().toLowerCase() : '';
            groups.push({ type: 'file', name, elements: [el] });
        }
        else if (el.querySelector('.file-label') || el.querySelector('.file-info')) {
            // Element contains file elements
            const fileNameEl = el.querySelector('.filename');
            const name = fileNameEl ? fileNameEl.textContent.trim().toLowerCase() : '';
            groups.push({ type: 'file', name, elements: [el] });
        }
        else {
            // Unknown element, assume file for safety
            const name = el.textContent.trim().toLowerCase();
            groups.push({ type: 'unknown', name, elements: [el] });
        }
    }
    
    // Sort groups: folders first, then files; alphabetical within each group
    groups.sort((a, b) => {
        // First sort by type: folder -> file -> unknown
        if (a.type === 'folder' && b.type !== 'folder') return -1;
        if (a.type !== 'folder' && b.type === 'folder') return 1;
        
        // Then alphabetically within the same type
        return a.name.localeCompare(b.name);
    });
    
    // Remove all children first
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    // Re-append in sorted order
    groups.forEach(group => {
        group.elements.forEach(el => container.appendChild(el));
    });
    
    // Recursively sort folder contents
    const folderContents = container.querySelectorAll('.folder-content');
    folderContents.forEach(content => {
        // Don't sort empty containers
        if (content.children.length > 0) {
            sortFileTree(content);
        }
    });
}

/**
 * Initializes the file search functionality.
 */
function initFileSearch() {
    const searchInput = document.getElementById('file-search-input');
    const clearSearchButton = document.getElementById('clear-search-button');
    const closeSearchButton = document.getElementById('close-search-button');
    const fileTree = document.querySelector('.file-tree');
    const searchResults = document.getElementById('search-results');
    
    if (!searchInput || !fileTree || !searchResults) return;
    
    // Add event listener for search input
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // Toggle clear button visibility
        clearSearchButton.style.display = query ? 'block' : 'none';
        
        if (query.length >= 2) {
            // Perform search with at least 2 characters
            performSearch(query);
        } else {
            // Hide search results if query is less than 2 characters
            searchResults.style.display = 'none';
            fileTree.style.display = 'block';
        }
    });
    
    // Add event listener for clear button
    clearSearchButton.addEventListener('click', function() {
        searchInput.value = '';
        clearSearchButton.style.display = 'none';
        searchResults.style.display = 'none';
        fileTree.style.display = 'block';
    });
    
    // Add event listener for close search button
    closeSearchButton.addEventListener('click', function() {
        searchResults.style.display = 'none';
        fileTree.style.display = 'block';
    });
    
    // Add event listener for keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            // Clear search on Escape key
            searchInput.value = '';
            clearSearchButton.style.display = 'none';
            searchResults.style.display = 'none';
            fileTree.style.display = 'block';
        }
    });
}

/**
 * Performs a file search based on the given query.
 * @param {string} query - The search query to match against file names and paths.
 */
function performSearch(query) {
    const fileTree = document.querySelector('.file-tree');
    const searchResults = document.getElementById('search-results');
    const searchResultsList = document.getElementById('search-results-list');
    const searchResultCount = document.getElementById('search-result-count');
    
    if (!fileTree || !searchResults || !searchResultsList) return;
    
    // Case-insensitive search
    const normalizedQuery = query.toLowerCase();
    
    // Collect file info from the DOM tree
    const files = collectFileInfo(fileTree);
    
    // Split the query by "/" to support path-based searches like "menu/index"
    const queryParts = normalizedQuery.split('/').filter(part => part.trim());
    
    // Filter files based on the search query
    const matchedFiles = files.filter(file => {
        // First check if the file name contains the entire query
        if (file.name.toLowerCase().includes(normalizedQuery)) {
            return true;
        }
        
        // Check if the file path contains the entire query (path-based search)
        if (file.path.toLowerCase().includes(normalizedQuery)) {
            return true;
        }
        
        // If the query contains path separators, do a more specific path match
        if (queryParts.length > 1) {
            const filePath = file.path.toLowerCase();
            
            // Check if all path parts are found in order
            let lastFoundIndex = -1;
            const allPartsFound = queryParts.every(part => {
                const partIndex = filePath.indexOf(part, lastFoundIndex + 1);
                if (partIndex === -1) return false;
                lastFoundIndex = partIndex;
                return true;
            });
            
            if (allPartsFound) return true;
            
            // Check if the query matches the last part of the path (directory + filename)
            const pathDirAndFile = file.path.toLowerCase().split('/').slice(-queryParts.length).join('/');
            if (pathDirAndFile === queryParts.join('/')) {
                return true;
            }
        }
        
        return false;
    });
    
    // Update UI
    fileTree.style.display = 'none';
    searchResults.style.display = 'flex';
    
    // Update result count
    const resultText = matchedFiles.length === 1 
        ? '1 result' 
        : `${matchedFiles.length} results`;
    searchResultCount.textContent = resultText;
    
    // Render search results
    if (matchedFiles.length > 0) {
        renderSearchResults(searchResultsList, matchedFiles, normalizedQuery);
    } else {
        searchResultsList.innerHTML = `
            <div class="search-empty-state">
                <p>No matching files found for "${query}"</p>
                <p>Try a different search term</p>
            </div>
        `;
    }
}

/**
 * Collects file information from the file tree DOM.
 * @param {HTMLElement} fileTree - The file tree container element.
 * @returns {Array<Object>} An array of file objects with name, path, and element information.
 */
function collectFileInfo(fileTree) {
    const files = [];
    
    // Find all file labels in the tree
    const fileLabels = fileTree.querySelectorAll('.file-label');
    
    fileLabels.forEach(label => {
        const checkbox = label.querySelector('input[type="checkbox"]');
        if (!checkbox) return;
        
        const fileNameEl = label.querySelector('.filename');
        if (!fileNameEl) return;
        
        const fileName = fileNameEl.textContent.trim();
        const filePath = checkbox.value;
        const checkboxId = checkbox.id;
        
        // Calculate and store path components for better path-based search
        const pathParts = filePath.split('/');
        
        files.push({
            name: fileName,
            path: filePath,
            fullPath: filePath, // Original full path
            checkboxId: checkboxId,
            element: label,
            pathParts: pathParts
        });
    });
    
    return files;
}

/**
 * Renders the search results in the search results list.
 * @param {HTMLElement} container - The container to render results in.
 * @param {Array<Object>} results - The matching file results.
 * @param {string} query - The search query for highlighting.
 */
function renderSearchResults(container, results, query) {
    container.innerHTML = '';
    
    results.forEach(file => {
        // Create a result item element
        const resultItem = document.createElement('div');
        resultItem.className = 'search-result-item';
        
        // Get file type for icon
        const fileExt = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
        let fileIcon = 'fa-file';
        
        // Customize icon based on file type
        if (['js', 'ts', 'jsx', 'tsx'].includes(fileExt)) {
            fileIcon = 'fa-file-code';
        } else if (['html', 'htm', 'xml'].includes(fileExt)) {
            fileIcon = 'fa-file-code';
        } else if (['css', 'scss', 'sass', 'less'].includes(fileExt)) {
            fileIcon = 'fa-file-code';
        } else if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(fileExt)) {
            fileIcon = 'fa-file-image';
        } else if (['md', 'txt', 'log'].includes(fileExt)) {
            fileIcon = 'fa-file-alt';
        } else if (['pdf'].includes(fileExt)) {
            fileIcon = 'fa-file-pdf';
        } else if (['zip', 'rar', 'tar', 'gz'].includes(fileExt)) {
            fileIcon = 'fa-file-archive';
        }
        
        // Highlight matched parts in filename and path
        const highlightedName = highlightMatches(file.name, query);
        const highlightedPath = highlightMatches(file.path, query);
        
        // Build result item HTML
        resultItem.innerHTML = `
            <div class="search-result-item-info">
                <div class="search-result-item-name">
                    <i class="fas ${fileIcon}"></i> ${highlightedName}
                </div>
                <div class="search-result-item-path">${highlightedPath}</div>
            </div>
            <div class="search-result-item-actions">
                <button type="button" class="action-button" data-action="preview" title="Preview" data-path="${file.path}" data-filename="${file.name}">
                    <i class="fas fa-eye"></i>
                </button>
                <button type="button" class="action-button" data-action="add" title="Add to selected files" data-path="${file.path}" data-filename="${file.name}">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
        `;
        
        // Add click event to open preview when clicking on the file info
        const fileInfo = resultItem.querySelector('.search-result-item-info');
        fileInfo.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent any default actions
            toggleFilePreview(file.path, file.name);
        });
        
        // Add click event for the preview button
        const previewButton = resultItem.querySelector('.action-button[data-action="preview"]');
        previewButton.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent form submission
            e.stopPropagation(); // Stop event from bubbling
            toggleFilePreview(file.path, file.name);
        });
        
        // Add click event for the add button
        const addButton = resultItem.querySelector('.action-button[data-action="add"]');
        addButton.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent form submission
            e.stopPropagation(); // Stop event from bubbling
            
            // Check the corresponding checkbox in the file tree
            const checkbox = document.getElementById(file.checkboxId);
            if (checkbox) {
                checkbox.checked = true;
                updateSelectedFilesList();
            } else {
                addFileToContext(file.path, file.name);
            }
        });
        
        container.appendChild(resultItem);
    });
}

/**
 * Highlights matches of the query in the text.
 * @param {string} text - The text to highlight matches in.
 * @param {string} query - The query to match.
 * @returns {string} HTML with highlighted matches.
 */
function highlightMatches(text, query) {
    if (!query) return text;
    
    // For path searches containing slashes, we need to match each part
    if (query.includes('/')) {
        // Split the query and the text by slashes
        const queryParts = query.toLowerCase().split('/').filter(part => part.trim());
        
        // If there are multiple parts, try to highlight each part separately
        if (queryParts.length > 1) {
            let result = text;
            
            // Highlight each query part in the text
            queryParts.forEach(part => {
                if (!part) return;
                
                // Escape special regex characters in the part
                const escapedPart = part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                
                // Create a regex that's case insensitive
                const regex = new RegExp(`${escapedPart}`, 'gi');
                
                // Replace matched parts with highlighted HTML
                result = result.replace(regex, '<span class="highlighted">$1</span>');
            });
            
            return result;
        }
    }
    
    // Create a regex that's case insensitive
    const regex = new RegExp(`${query}`, 'gi');
    
    // Replace matched parts with highlighted HTML
    return text.replace(regex, '<span class="highlighted">$1</span>');
}