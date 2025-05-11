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
    # Default workspace root is the current working directory
    WORKSPACE_ROOT = Path.cwd().resolve()  # Use resolved absolute path
    MODULE_DIR = Path(__file__).parent.resolve()
    DEFAULT_TEMPLATE_FILE = MODULE_DIR / "feature_implementation_template.md"
    DEFAULT_OUTPUT_DIR = WORKSPACE_ROOT / "outputs"
    DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "implementation_prompt.md"
    # Directory for storing additional prompt templates as markdown files
    PROMPTS_DIR = WORKSPACE_ROOT / "prompts"
    # TEMPLATES_DIR = MODULE_DIR / "templates" / "user_templates" # Not used if templates are DB only

    # --- Application Data and Database Configuration ---
    # Use a standard user data directory for the database.
    _app_name = "feature_implementer"
    if os.name == "nt":  # Windows
        _app_data_base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    elif "XDG_DATA_HOME" in os.environ:  # Linux/other XDG compliant
        _app_data_base = os.environ["XDG_DATA_HOME"]
    elif os.uname().sysname == "Darwin":  # macOS
        _app_data_base = Path.home() / "Library" / "Application Support"
    else:  # Fallback for other Unix-like systems
        _app_data_base = Path.home() / ".local" / "share"

    APP_DATA_DIR = Path(_app_data_base) / _app_name
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Could not create application data directory {APP_DATA_DIR}: {e}")
        # Fallback to workspace root if app data dir creation fails
        APP_DATA_DIR = WORKSPACE_ROOT / f".{_app_name}_data"
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.warning(f"Using fallback data directory: {APP_DATA_DIR}")

    DB_PATH = APP_DATA_DIR / ".feature_implementer.db"

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
        # DB_PATH.name, # No longer need to ignore DB_PATH by name in workspace, as it's outside
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

    @classmethod
    def set_workspace_root(cls, workspace_path: str):
        """Update workspace root and related paths based on a new directory"""
        if not workspace_path:
            logger.warning("Empty workspace path provided, using current directory")
            return

        try:
            # Convert to absolute path and resolve
            workspace = Path(workspace_path).resolve()

            if not workspace.is_dir():
                logger.error(
                    f"Working directory does not exist or is not a directory: {workspace}"
                )
                raise ValueError(f"Invalid working directory: {workspace}")

            # Update workspace root
            cls.WORKSPACE_ROOT = workspace
            logger.info(f"Workspace root set to: {cls.WORKSPACE_ROOT}")

            # Update dependent paths
            cls.DEFAULT_OUTPUT_DIR = cls.WORKSPACE_ROOT / "outputs"
            cls.DEFAULT_OUTPUT_FILE = (
                cls.DEFAULT_OUTPUT_DIR / "implementation_prompt.md"
            )
            # DB_PATH is global, should not be changed when workspace root changes
            # cls.DB_PATH = cls.WORKSPACE_ROOT / ".feature_implementer.db" # This line removed
            cls.PROMPTS_DIR = cls.WORKSPACE_ROOT / "prompts"

            # Update scan directories
            cls.SCAN_DIRS = [str(cls.WORKSPACE_ROOT)]

            # Update ignore patterns (which might include relative paths)
            if cls.DEFAULT_OUTPUT_DIR.is_relative_to(cls.WORKSPACE_ROOT):
                output_pattern = (
                    str(cls.DEFAULT_OUTPUT_DIR.relative_to(cls.WORKSPACE_ROOT))
                    + os.sep
                    + "*"
                )
            else:
                output_pattern = "outputs" + os.sep + "*"

            # Update the ignore patterns
            cls.IGNORE_PATTERNS = [
                p for p in cls.IGNORE_PATTERNS if not p.startswith("outputs" + os.sep)
            ] + [output_pattern]

        except Exception as e:
            logger.error(
                f"Error setting workspace root to {workspace_path}: {e}", exc_info=True
            )
            raise

    @classmethod
    def set_prompts_dir(cls, prompts_dir: str):
        """Set a custom directory for prompt templates"""
        if not prompts_dir:
            logger.warning("Empty prompts directory provided, using default")
            return

        try:
            # Convert to absolute path and resolve
            prompts_path = Path(prompts_dir).resolve()

            # Create the directory if it doesn't exist
            prompts_path.mkdir(parents=True, exist_ok=True)

            # Update the prompts directory
            cls.PROMPTS_DIR = prompts_path
            logger.info(f"Prompts directory set to: {cls.PROMPTS_DIR}")

        except Exception as e:
            logger.error(
                f"Error setting prompts directory to {prompts_dir}: {e}", exc_info=True
            )
            raise

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
    # Ensure the parent directory for the database exists
    try:
        Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(
            f"Could not create database directory {Config.DB_PATH.parent}: {e}"
        )
        # Potentially raise or handle if critical
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
