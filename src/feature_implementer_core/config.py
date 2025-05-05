import os
import logging

# import json # No longer needed here
# import sqlite3 # No longer needed here
from pathlib import Path

# Initialize logger early for potential config warnings
logger = logging.getLogger(__name__)


class Config:
    # --- Security ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Use a less predictable default for development, but warn.
        # In production, SECRET_KEY *must* be set.
        is_production = os.environ.get("FLASK_ENV") == "production"
        if is_production:
            logger.error(
                "FATAL: SECRET_KEY environment variable must be set in production!"
            )
            raise ValueError(
                "SECRET_KEY environment variable must be set in production"
            )
        else:
            # Generate a pseudo-random key for development if not set
            # This won't persist across restarts, breaking sessions.
            SECRET_KEY = os.urandom(
                24
            ).hex()  # Use hex for easier env var setting if needed
            logger.warning(
                "SECRET_KEY environment variable not set. Using a temporary key for development. "
                "Flask sessions will not persist across restarts. "
                "Set SECRET_KEY environment variable for persistent sessions."
            )

    # --- Path Configuration ---
    WORKSPACE_ROOT = Path.cwd().resolve()  # Use resolved absolute path
    MODULE_DIR = Path(__file__).parent.resolve()
    DEFAULT_TEMPLATE_FILE = MODULE_DIR / "feature_implementation_template.md"
    DEFAULT_OUTPUT_DIR = WORKSPACE_ROOT / "outputs"
    DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "implementation_prompt.md"
    # TEMPLATES_DIR = MODULE_DIR / "templates" / "user_templates" # Not used if templates are DB only

    # --- Database Configuration ---
    # Store the database in a standard user data location or relative to workspace?
    # Option 1: Relative to workspace (simple, portable with project)
    DB_PATH = WORKSPACE_ROOT / "feature_implementer.db"
    # Option 2: User data directory (more standard for installed apps)
    # APP_DATA_DIR = Path(os.environ.get("APPDATA") or
    #                    os.environ.get("XDG_DATA_HOME") or
    #                    Path.home() / ".local/share") / "feature_implementer"
    # DB_PATH = APP_DATA_DIR / "feature_implementer.db"
    # APP_DATA_DIR.mkdir(parents=True, exist_ok=True) # Ensure dir exists if using this option

    # --- File Explorer Configuration ---
    # Default scan directory is the workspace root
    SCAN_DIRS = [str(WORKSPACE_ROOT)]
    IGNORE_PATTERNS = [
        ".git",
        ".vscode",
        "__pycache__",
        ".DS_Store",
        "node_modules",
        ".venv",
        "venv",
        "*.pyc",
        "*.egg-info",
        "dist",
        "build",
        str(DEFAULT_OUTPUT_DIR.relative_to(WORKSPACE_ROOT))
        + os.sep
        + "*",  # Ignore output dir
        DB_PATH.name,  # Ignore the database file itself
    ]

    # --- Default Template Content (loaded once) ---
    DEFAULT_TEMPLATE_CONTENT: str = ""
    try:
        if DEFAULT_TEMPLATE_FILE.is_file():
            DEFAULT_TEMPLATE_CONTENT = DEFAULT_TEMPLATE_FILE.read_text()
        else:
            logger.warning(
                f"Default template file not found at {DEFAULT_TEMPLATE_FILE}. Using empty default."
            )
            # Provide a minimal fallback template
            DEFAULT_TEMPLATE_CONTENT = """# Feature Implementation

## Context
{relevant_code_context}

## Request
{jira_description}

## Instructions
{additional_instructions}

## Task
Implement the feature."""

    except Exception as e:
        logger.error(
            f"Failed to load default template content from {DEFAULT_TEMPLATE_FILE}: {e}"
        )
        # Fallback content again
        DEFAULT_TEMPLATE_CONTENT = """# Feature Implementation Error

Error loading default template. Please check configuration.

## Context
{relevant_code_context}

## Request
{jira_description}

## Instructions
{additional_instructions}

## Task
Implement the feature."""

    # NOTE: All database interaction methods (get_presets, _init_preset_db,
    #       add_preset, delete_preset, get_templates, get_default_template_id,
    #       get_template_by_id, add_template, update_template, delete_template,
    #       set_default_template, initialize_default_template, create_standard_templates)
    #       have been moved to the `database.py` module.
    #       The `REFINED_PRESETS` cache has also been removed.


# Example: Ensure output directory exists on config load (optional)
# try:
#     Config.DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
# except OSError as e:
#     logger.warning(f"Could not create default output directory {Config.DEFAULT_OUTPUT_DIR}: {e}")


# --- Functions that might use Config but don't belong in it ---


def get_app_db_path() -> Path:
    """Returns the configured database path."""
    # Ensures DB path creation logic is centralized if needed later
    # For now, just returns the config value.
    # If using APP_DATA_DIR option above, ensure it exists here:
    # Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return Config.DB_PATH


def load_default_template_content() -> str:
    """Loads and returns the content of the default template file."""
    return Config.DEFAULT_TEMPLATE_CONTENT


# --- Placeholder for initialization logic that uses the database ---
# This should be called explicitly from app startup or CLI entry point.


def initialize_app_database():
    """Initializes the database schema and potentially default data."""
    from . import database  # Local import to avoid circular dependencies

    db_path = get_app_db_path()
    try:
        logger.info(
            f"Ensuring database exists and schema is initialized at {db_path}..."
        )
        database.initialize_database(db_path)

        # Check if standard templates need to be created (e.g., if DB was just created)
        templates = database.get_templates(db_path)
        if not templates:
            logger.info(
                "No templates found in database. Creating standard templates..."
            )
            default_content = load_default_template_content()
            success, result = database.add_template(
                db_path,
                name="Default Template",
                content=default_content,
                description="The standard feature implementation template",
                is_default=True,
            )
            if not success:
                logger.error(f"Failed to add default template: {result}")

            # Add a minimal template example
            minimal_template = """# Feature Implementation Prompt

You are tasked with implementing a feature. Relevant info:

## CODE CONTEXT
```
{relevant_code_context}
```

## JIRA
```
{jira_description}
```

## INSTRUCTIONS
```
{additional_instructions}
```

## TASK
Implement the feature."""
            success, result = database.add_template(
                db_path,
                name="Minimal Template",
                content=minimal_template,
                description="A simplified template",
                is_default=False,
            )
            if not success:
                logger.error(f"Failed to add minimal template: {result}")

    except Exception as e:
        logger.error(
            f"Failed during application database initialization: {e}", exc_info=True
        )
        # Depending on severity, might want to raise e here


# Example usage:
# if __name__ == '__main__':
#     print(f"Workspace Root: {Config.WORKSPACE_ROOT}")
#     print(f"Database Path: {get_app_db_path()}")
#     print(f"Default Template Path: {Config.DEFAULT_TEMPLATE_FILE}")
#     initialize_app_database()
#     from . import database
#     print("Templates after init:", database.get_templates(get_app_db_path()))
