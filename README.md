# Feature Implementer

A pip-installable tool to generate feature implementation prompts for software development projects. This application helps create well-structured prompts for LLMs by gathering context from relevant code files within your project.

## Features

- Browse and select files from your project directory for context
- Create, manage, and use custom prompt templates stored in a local database
- Add Jira ticket descriptions and custom instructions (either as text or file paths)
- Generate comprehensive prompts for LLM-assisted feature implementation
- Export prompts to Markdown files
- CLI for prompt generation and template management
- Web UI (Flask) for interactive use
- Light/dark mode support in Web UI
- Support for specifying custom working and prompts directories

## Project Structure (Package)

```
feature-implementer/              # Project Root
├── README.md
├── LICENSE
├── pyproject.toml            # Build/package configuration
├── .gitignore
# Removed run.py as entry points are preferred
└── src/
    └── feature_implementer_core/ # The actual Python package
        ├── __init__.py
        ├── app.py              # Flask application setup
        ├── cli.py              # Command Line Interface logic
        ├── config.py           # Configuration settings
        ├── database.py         # Database interaction logic (SQLite)
        ├── file_utils.py       # File management utilities
        ├── prompt_generator.py # Prompt generation logic
        ├── feature_implementation_template.md # Default template source
        ├── templates/          # HTML templates for Flask app
        │   ├── index.html
        │   ├── template_manager.html
        │   └── macros.html
        │   └── ...
        ├── static/             # Static assets (CSS, JS)
        │   ├── css/
        │   ├── js/
        │   └── ...
        └── prompts/                    # Directory for storing custom prompt templates (Markdown files)
            └── example_custom_prompt.md
```

## Setup

1.  **(Recommended) Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Linux/macOS:
    source venv/bin/activate
    # On Windows:
    # venv\Scripts\activate 
    ```

2.  **Install the package:**
    The simplest way is to install directly from the source directory using pip. This handles all dependencies listed in `pyproject.toml`.
    *   Navigate to the project root directory (where `pyproject.toml` is) and run:
        ```bash
        pip install -e .
        ```
        *(The `-e` flag installs the package in "editable" mode, meaning changes to the source code are reflected immediately without needing to reinstall.)*

    *   Alternatively, you can build the wheel first and then install it:
        ```bash
        # Build the sdist and wheel:
        python -m build
        # Install the built wheel (replace version number):
        pip install dist/feature_implementer-0.1.0-py3-none-any.whl 
        ```

3.  **Run the application:**
    Once installed, the package provides two command-line scripts:
    *   **Web UI:** Start the Flask server.
        ```bash
        feature-implementer 
        ```
        This typically runs on `http://127.0.0.1:4605`. You can customize the host and port:
        ```bash
        # Run on a different port
        feature-implementer --port 5001
        
        # Run accessible on your network (use with caution)
        feature-implementer --host 0.0.0.0 
        
        # Run in production mode using gunicorn (if installed)
        feature-implementer --prod --workers 4
        
        # Disable debug mode (default is usually off unless FLASK_DEBUG=true)
        feature-implementer --no-debug
        
        # Use a different working directory than the current one
        feature-implementer --working-dir /path/to/project
        
        # Specify a custom directory for additional prompt files
        feature-implementer --prompts-dir /path/to/prompts
        
        # Combine multiple parameters
        feature-implementer --host 0.0.0.0 --port 4605 --working-dir /app/project --prompts-dir /app/prompts
        ```
    *   **CLI:** Use the `feature-implementer-cli` command for direct operations (see CLI Usage below).

4.  Access the web application (if running) via your browser at the specified host and port.

## Usage (Web UI)

1.  Start the web server using `feature-implementer`.
2.  Navigate to the web interface in your browser.
3.  The file explorer shows files relative to where the application was started (or configured `WORKSPACE_ROOT`).
4.  Select files from your codebase to provide context for the prompt.
5.  Enter the Jira ticket description (or a path to a file containing it).
6.  Add any additional implementation instructions (or a path to a file containing them).
7.  Select a prompt template from the dropdown (defaults to the configured default template).
8.  Click "Generate Prompt".
9.  Copy or export the generated prompt (as Markdown) for use with an LLM.

## Template Management (Web UI & CLI)

The application allows you to create and manage custom prompt templates stored in a local SQLite database (`.feature_implementer.db`). This database is located in a standard user-specific application data directory, not within your project folder. The typical locations are:
- Linux: `~/.local/share/feature_implementer/`
- macOS: `~/Library/Application Support/feature_implementer/`
- Windows: `%APPDATA%\feature_implementer\` (e.g., `C:\Users\YourUser\AppData\Roaming\feature_implementer\`)

If the application cannot create or access this directory, it will fall back to creating a `.feature_implementer_data` directory in your current workspace.

**Web UI:**
1.  Navigate to the "Template Manager" page (link usually in the header/footer).
2.  View existing templates.
3.  Create a new template using the form. Essential placeholders:
    *   `{relevant_code_context}` - Gets replaced with the content of selected code files.
    *   `{jira_description}` - Gets replaced with the Jira text/file content.
    *   `{additional_instructions}` - Gets replaced with the instructions text/file content.
4.  Set a template as the default using the "Set Default" button.
5.  Edit or delete existing templates.
6.  Reset all templates to the initial standard set using the "Reset" button (this deletes all custom templates).

**CLI:** See CLI usage examples below for managing templates directly.

## CLI Usage

The package provides two main commands after installation:

*   `feature-implementer`: Runs the Flask web server (as described in Setup).
*   `feature-implementer-cli`: Accesses core functions for prompt generation and template management.

**`feature-implementer-cli` Examples:**

```bash
# 1. Generate a prompt (requires context files and Jira description)
feature-implementer-cli --context-files src/feature_implementer_core/app.py src/feature_implementer_core/cli.py --jira "FEAT-123: Implement new endpoint" --instructions "Use Pydantic for validation." --output my_prompt.md

# Use a specific template ID for generation
feature-implementer-cli --template-id 2 --context-files ... --jira ... 

# Read Jira description from a file
feature-implementer-cli --context-files ... --jira path/to/description.txt

# Use a different working directory for file operations
feature-implementer-cli --working-dir /path/to/project --context-files app.py models.py --jira "FEAT-456: Add new feature"

# Specify a custom directory for additional prompt files
feature-implementer-cli --prompts-dir /path/to/prompts --context-files app.py --jira "FEAT-789: New feature"

# 2. Manage Templates

# List all available templates
feature-implementer-cli --list-templates

# Create a new template from a content file
feature-implementer-cli --create-template "My API Template" --template-content path/to/my_template.txt --template-description "Template for API endpoints"

# Set template ID 3 as the default
feature-implementer-cli --set-default 3

# Delete template ID 4
feature-implementer-cli --delete-template 4

# Reset all templates to the standard ones (prompts for confirmation)
feature-implementer-cli --reset-templates

```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 