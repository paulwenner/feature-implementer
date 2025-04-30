# Feature Implementer

A tool to generate feature implementation prompts for software development projects. This application helps create well-structured prompts for LLMs by gathering context from relevant code files.

## Features

- Browse and select files from your codebase for context
- Create and manage custom prompt templates
- Add Jira tickets and custom instructions
- Generate a comprehensive prompt for LLM-assisted feature implementation
- Export prompts to Markdown files
- Light/dark mode support

## Project Structure

```
feature_implementer/
├── README.md               # Project documentation
├── LICENSE                 # Project License (MIT)
├── requirements.txt        # Python dependencies
├── config.py              # Configuration settings
├── run.py                 # Application entry point
├── feature_implementation_template.md # Default template for feature implementation prompts
├── src/                   # Source code
│   ├── __init__.py
│   ├── app.py             # Flask application setup
│   ├── cli.py             # Command Line Interface entry point
│   ├── file_utils.py      # File management utilities
│   ├── prompt_generator.py # Prompt generation logic
├── static/                # Static assets
│   ├── css/               # Stylesheets
│   │   └── style.css      # Main stylesheet
│   ├── js/                # JavaScript files
│   │   ├── file_explorer.js # File explorer functionality
│   │   ├── form_handler.js  # Form submission handling
│   │   ├── modal_utils.js   # Modal dialog utilities
│   │   ├── preset_handler.js # Preset management functionality
│   │   ├── theme_toggle.js  # Theme switching
│   │   └── ui_utils.js      # UI utility functions
│   └── assets/            # Static assets like icons
├── templates/             # HTML templates
│   ├── base.html          # Base template with common elements
│   ├── index.html         # Main page for prompt generation
│   ├── macros.html        # Reusable template components
│   ├── result.html        # Page to display generated prompt
│   ├── template_manager.html # Template management page
│   └── user_templates/    # Directory for user-created templates (if stored as files)
├── outputs/               # Default directory for generated output files
├── Dockerfile             # Docker configuration
└── docker-compose.yml     # Docker Compose configuration (if used from parent directory)
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

1. **Place your project code** into the `data/` directory within the `feature_implementer` folder. The file explorer in the web UI will display the contents of this directory. (The current content is just placeholder data).
2. Navigate to the web interface (usually http://localhost:5000).
3. Select files from your codebase (shown in the file explorer) to provide context for the prompt.
4. Enter Jira ticket description (if applicable).
5. Add any additional implementation instructions.
6. Click "Generate Prompt".
7. Copy or export the generated prompt for use with an LLM.

## Template Management

The application allows you to create and manage custom prompt templates for different use cases:

1. Navigate to the Templates page
2. Create a new template with placeholders:
   - `{relevant_code_context}` - Selected code files
   - `{jira_description}` - Jira ticket details
   - `{additional_instructions}` - Any extra notes
3. Set a template as default for all new prompts
4. Templates are stored in a SQLite database for persistence

## CLI Usage

The application also provides a command-line interface for generating prompts:

```
python -m src.cli --context-files path/to/file1.py path/to/file2.py --jira "Jira ticket details" --instructions "Implementation notes"
```

For template management via CLI:

```
# List all templates
python -m src.cli --list-templates

# Create a new template
python -m src.cli --create-template "My Template" --template-content path/to/template.md --template-description "Template description"

# Set a template as default
python -m src.cli --set-default TEMPLATE_ID

# Use a specific template
python -m src.cli --template-id TEMPLATE_ID --context-files path/to/file.py
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 