/**
 * Manages the file explorer functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initFileExplorer();
    updateSelectedFilesList();
});

function initFileExplorer() {
    // Folder expand/collapse functionality
    document.querySelectorAll('.folder-label').forEach(function(label) {
        label.addEventListener('click', function() {
            const content = this.nextElementSibling;
            const folderArrow = this.querySelector('.folder-arrow i');
            
            if (!content.style.display || content.style.display === 'none') {
                content.style.display = 'block';
                folderArrow.classList.add('folder-arrow-rotated');
            } else {
                content.style.display = 'none';
                folderArrow.classList.remove('folder-arrow-rotated');
            }
        });
    });
    
    // File preview functionality
    document.querySelectorAll('.file-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const path = this.getAttribute('data-path');
            previewFile(path);
        });
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
    document.getElementById('file-preview').style.display = 'none';
} 