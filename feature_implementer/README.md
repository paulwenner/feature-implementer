# Feature Implementer

A tool to generate feature implementation prompts for software development projects. This application helps create well-structured prompts for LLMs by gathering context from relevant code files.

## Features

- Browse and select files from your codebase for context
- Add Jira tickets and custom instructions
- Generate a comprehensive prompt for LLM-assisted feature implementation
- Export prompts to Markdown files
- Light/dark mode support

## Project Structure

```
feature_implementer/
├── README.md               # Project documentation
├── requirements.txt        # Python dependencies
├── config.py              # Configuration settings
├── run.py                 # Application entry point
├── src/                   # Source code
│   ├── __init__.py
│   ├── app.py             # Flask application setup
│   ├── file_utils.py      # File management utilities
│   ├── prompt_generator.py # Prompt generation logic
├── static/                # Static assets
│   ├── css/               # Stylesheets
│   │   └── style.css      # Main stylesheet
│   ├── js/                # JavaScript files
│   │   ├── file_explorer.js # File explorer functionality
│   │   ├── form_handler.js  # Form submission handling
│   │   ├── theme_toggle.js  # Theme switching
│   │   └── ui_utils.js      # UI utility functions
├── templates/             # HTML templates
│   ├── base.html          # Base template with common elements
│   ├── index.html         # Main page
│   ├── macros.html        # Reusable template components
├── outputs/               # Generated output directory
└── Dockerfile             # Docker configuration
```

## Setup

### Local Development

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

4. Access the application at http://localhost:5000

### Docker Setup

1. Build and run with Docker:
   ```
   docker build -t feature-implementer .
   docker run -p 5000:5000 feature-implementer
   ```

2. Or use docker-compose:
   ```
   docker-compose up
   ```

## Usage

1. Navigate to the web interface
2. Select files from your codebase to provide context
3. Enter Jira ticket description (if applicable)
4. Add any additional implementation instructions
5. Click "Generate Prompt"
6. Copy or export the generated prompt for use with an LLM 