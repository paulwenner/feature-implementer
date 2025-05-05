/**
 * Handles theme switching between light and dark modes
 */

// Immediately apply theme to prevent flickering during page loads
function applyThemeImmediately() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

// Main theme toggle functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        
        // Check saved preference or system preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            // We already set the data-theme attribute, just update the icon
            updateThemeIcon(savedTheme, icon);
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            // We already set the data-theme attribute, just update the icon
            updateThemeIcon('dark', icon);
        }
        
        // Toggle theme when button is clicked
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme, icon);
        });
    }
});

function updateThemeIcon(theme, icon) {
    if (!icon) return;
    
    if (theme === 'dark') {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }
} 