/**
 * Tutorial Tour for Feature Implementer
 * 
 * A step-by-step guided tour explaining key features of the application.
 */

class TutorialTour {
    constructor() {
        this.currentStep = 0;
        this.tourActive = false;
        this.steps = [
            // Step 1: Introduction
            {
                title: "Welcome to Feature Implementer!",
                content: "This tool helps you generate detailed prompts for implementing features based on your codebase. Let's take a quick tour of how to use it.",
                target: null, // No specific target, just an intro
                position: "center"
            },
            // Step 2: Data folder explanation
            {
                title: "Project Structure",
                content: "The data folder is where you load your project structure. Files in this folder are used as context for generating implementation prompts.",
                target: ".sidebar-header",
                position: "right"
            },
            // Step 3: File Selection
            {
                title: "Select Context Files",
                content: "Browse your project files and select the ones relevant to your feature implementation. These files provide context for the AI.",
                target: ".file-explorer",
                position: "right"
            },
            // Step 4: Presets
            {
                title: "File Presets",
                content: "Save commonly used file combinations as presets to speed up future prompt generation.",
                target: ".preset-selector",
                position: "bottom"
            },
            // Step 5: Template Selection
            {
                title: "Prompt Templates",
                content: "Choose a template for your prompt or create custom templates from the Template Manager.",
                target: ".template-select-wrapper",
                position: "bottom"
            },
            // Step 6: JIRA Description
            {
                title: "JIRA Description",
                content: "Paste your JIRA ticket description here to provide the feature requirements.",
                target: "#jira_description",
                position: "top"
            },
            // Step 7: Additional Instructions
            {
                title: "Additional Instructions",
                content: "Add any specific implementation details or requirements not covered in the JIRA description.",
                target: "#additional_instructions",
                position: "top"
            },
            // Step 8: Generate Button
            {
                title: "Generate Prompt",
                content: "Click this button to generate your feature implementation prompt based on all the inputs.",
                target: "#generate-button",
                position: "left"
            },
            // Final step
            {
                title: "You're all set!",
                content: "You now know how to use Feature Implementer to generate comprehensive prompts for your feature implementations. Click 'Finish' to start using the tool.",
                target: null,
                position: "center"
            }
        ];

        // DOM elements will be created when tour starts
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        
        // Bind events
        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('DOMContentLoaded', () => {
            const startButton = document.getElementById('start-tutorial');
            if (startButton) {
                startButton.addEventListener('click', () => this.startTour());
            }
        });
    }
    
    createTourElements() {
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        
        // Create spotlight
        this.spotlight = document.createElement('div');
        this.spotlight.className = 'tour-spotlight';
        
        // Create tooltip
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        
        this.tooltip.innerHTML = `
            <div class="tour-tooltip-header">
                <span class="tour-step-title"></span>
                <span class="tour-step-number"></span>
            </div>
            <div class="tour-tooltip-content"></div>
            <div class="tour-tooltip-actions">
                <button class="tour-btn tour-btn-secondary" id="tour-prev">Previous</button>
                <button class="tour-btn tour-btn-secondary" id="tour-skip">Skip Tour</button>
                <button class="tour-btn tour-btn-primary" id="tour-next">Next</button>
            </div>
        `;
        
        // Add elements to DOM
        document.body.appendChild(this.overlay);
        document.body.appendChild(this.spotlight);
        document.body.appendChild(this.tooltip);
        
        // Bind navigation events
        document.getElementById('tour-next').addEventListener('click', () => this.nextStep());
        document.getElementById('tour-prev').addEventListener('click', () => this.prevStep());
        document.getElementById('tour-skip').addEventListener('click', () => this.endTour());
    }
    
    startTour() {
        if (this.tourActive) return;
        
        this.tourActive = true;
        this.currentStep = 0;
        
        this.createTourElements();
        this.showStep(this.currentStep);
    }
    
    showStep(stepIndex) {
        const step = this.steps[stepIndex];
        
        // Update tooltip content
        const title = this.tooltip.querySelector('.tour-step-title');
        const content = this.tooltip.querySelector('.tour-tooltip-content');
        const stepNumber = this.tooltip.querySelector('.tour-step-number');
        
        title.textContent = step.title;
        content.textContent = step.content;
        stepNumber.textContent = `${stepIndex + 1}/${this.steps.length}`;
        
        // Update navigation buttons
        const prevButton = document.getElementById('tour-prev');
        const nextButton = document.getElementById('tour-next');
        
        prevButton.style.visibility = stepIndex === 0 ? 'hidden' : 'visible';
        
        if (stepIndex === this.steps.length - 1) {
            nextButton.textContent = 'Finish';
        } else {
            nextButton.textContent = 'Next';
        }
        
        // Position elements
        if (step.target) {
            const targetElement = document.querySelector(step.target);
            if (targetElement) {
                this.positionElements(targetElement, step.position);
            } else {
                this.centerElements();
            }
        } else {
            this.centerElements();
        }
    }
    
    positionElements(element, position) {
        const rect = element.getBoundingClientRect();
        
        // Position spotlight
        this.spotlight.style.top = `${rect.top}px`;
        this.spotlight.style.left = `${rect.left}px`;
        this.spotlight.style.width = `${rect.width}px`;
        this.spotlight.style.height = `${rect.height}px`;
        this.spotlight.style.display = 'block';
        
        // Position tooltip
        const tooltipRect = this.tooltip.getBoundingClientRect();
        let top, left;
        
        switch(position) {
            case 'top':
                top = rect.top - tooltipRect.height - 10;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = rect.bottom + 10;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - 10;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + 10;
                break;
            default:
                top = window.innerHeight / 2 - tooltipRect.height / 2;
                left = window.innerWidth / 2 - tooltipRect.width / 2;
        }
        
        // Keep tooltip in viewport
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) top = 10;
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = window.innerHeight - tooltipRect.height - 10;
        }
        
        this.tooltip.style.top = `${top}px`;
        this.tooltip.style.left = `${left}px`;
    }
    
    centerElements() {
        // Hide spotlight
        this.spotlight.style.display = 'none';
        
        // Center tooltip
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const top = window.innerHeight / 2 - tooltipRect.height / 2;
        const left = window.innerWidth / 2 - tooltipRect.width / 2;
        
        this.tooltip.style.top = `${top}px`;
        this.tooltip.style.left = `${left}px`;
    }
    
    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.showStep(this.currentStep);
        } else {
            this.endTour();
        }
    }
    
    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.showStep(this.currentStep);
        }
    }
    
    endTour() {
        this.tourActive = false;
        
        // Remove tour elements
        document.body.removeChild(this.overlay);
        document.body.removeChild(this.spotlight);
        document.body.removeChild(this.tooltip);
        
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
    }
}

// Initialize the tour
const tour = new TutorialTour(); 