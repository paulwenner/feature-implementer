import os
import logging
import json
import sqlite3
from pathlib import Path


class Config:

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError(
                "SECRET_KEY environment variable must be set in production"
            )
        else:
            SECRET_KEY = os.urandom(24)
            logging.warning(
                "Using random SECRET_KEY - sessions will not persist across restarts"
            )

    # Path configuration
    WORKSPACE_ROOT = Path.cwd()
    MODULE_DIR = Path(__file__).parent
    DEFAULT_TEMPLATE = MODULE_DIR / "feature_implementation_template.md"
    DEFAULT_OUTPUT_DIR = Path.cwd() / "outputs"
    DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "implementation_prompt.md"
    TEMPLATES_DIR = MODULE_DIR / "templates" / "user_templates"

    # Database configuration
    DB_PATH = Path.cwd() / "feature_implementer.db"

    # Ensure the *parent* directory for the DB exists (usually CWD, so it should)
    # DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    # (MODULE_DIR / "data").mkdir(exist_ok=True) # Don't create data dir in package

    # Ensure the user templates directory exists (if file-based templates were used)
    # TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)

    # File explorer configuration
    SCAN_DIRS = [str(Path.cwd())]
    IGNORE_PATTERNS = [
        ".git",
        ".vscode",
        "__pycache__",
        ".DS_Store",
        "node_modules",
        ".venv",
        "venv",
    ]

    # Service presets - loaded from database
    @classmethod
    def get_presets(cls):
        presets = {}

        # Create DB if it doesn't exist
        if not cls.DB_PATH.exists():
            cls._init_preset_db()
            return presets

        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT name, files FROM presets")
            rows = cursor.fetchall()

            for row in rows:
                try:
                    files = json.loads(row["files"])
                    presets[row["name"]] = {"files": files}
                except json.JSONDecodeError:
                    logging.error(
                        f"Failed to decode preset files JSON for {row['name']}"
                    )

            conn.close()
        except Exception as e:
            logging.error(f"Error loading presets from database: {e}")

        return presets

    @classmethod
    def _init_preset_db(cls):
        """Initialize the preset database schema"""
        try:
            # Ensure the parent directory for the DB exists
            db_dir = cls.DB_PATH.parent
            db_dir.mkdir(exist_ok=True, parents=True)
            # data_dir = cls.DB_PATH.parent
            # data_dir.mkdir(exist_ok=True)

            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # Create presets table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                files TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # Create templates table - using explicit column definition
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                description TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # Verify templates table was created
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='templates'"
            )
            if not cursor.fetchone():
                logging.error(
                    "Templates table creation failed - still not found after creation attempt"
                )
            else:
                logging.info("Templates table created successfully")

            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            return False

    @classmethod
    def add_preset(cls, name, files):
        """Add a new preset to the database"""
        conn = None
        try:
            # Input validation
            if not name or not isinstance(name, str):
                logging.error(f"Invalid preset name: {name}")
                return False

            if not files or not isinstance(files, list):
                logging.error(f"Invalid files list: {files}")
                return False

            # Sanitize inputs - ensure files are all strings
            sanitized_files = [str(file) for file in files]

            # Log what we're about to do
            logging.info(f"Adding preset '{name}' with {len(sanitized_files)} files")

            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            try:
                # Convert files list to JSON string
                files_json = json.dumps(sanitized_files)
                logging.debug(f"Serialized files JSON: {files_json[:100]}...")
            except TypeError as json_error:
                logging.error(
                    f"JSON serialization error: {json_error} for files: {sanitized_files}"
                )
                return False

            cursor.execute(
                "INSERT INTO presets (name, files) VALUES (?, ?)", (name, files_json)
            )

            conn.commit()
            logging.info(f"Successfully added preset '{name}' to database")
            return True
        except sqlite3.IntegrityError:
            logging.error(f"Preset with name '{name}' already exists")
            return False
        except Exception as e:
            logging.error(f"Error adding preset to database: {e}", exc_info=True)
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def delete_preset(cls, name):
        """Delete a preset from the database"""
        conn = None
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # First check if the preset exists
            cursor.execute("SELECT COUNT(*) FROM presets WHERE name = ?", (name,))
            if cursor.fetchone()[0] == 0:
                logging.warning(f"Attempted to delete non-existent preset: {name}")
                conn.close()
                return False

            # Delete the preset
            cursor.execute("DELETE FROM presets WHERE name = ?", (name,))

            # Ensure the changes are committed
            conn.commit()

            # Check if the delete was successful
            affected_rows = cursor.rowcount
            logging.info(f"Deleted preset '{name}' with {affected_rows} rows affected")

            conn.close()
            return affected_rows > 0

        except Exception as e:
            logging.error(f"Error deleting preset from database: {e}", exc_info=True)
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    # Template management methods
    @classmethod
    def get_templates(cls):
        """Get all templates from the database"""
        templates = []

        # Create DB if it doesn't exist
        if not cls.DB_PATH.exists():
            cls._init_preset_db()
            return templates

        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, name, description, is_default, created_at, updated_at FROM templates ORDER BY name"
            )
            rows = cursor.fetchall()

            for row in rows:
                templates.append(dict(row))

            conn.close()
        except Exception as e:
            logging.error(f"Error loading templates from database: {e}")

        return templates

    @classmethod
    def get_default_template_id(cls):
        """Get the ID of the default template"""
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM templates WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()

            conn.close()

            if row:
                return row["id"]
            return None
        except Exception as e:
            logging.error(f"Error getting default template: {e}")
            return None

    @classmethod
    def get_template_by_id(cls, template_id):
        """Get a template by its ID"""
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            row = cursor.fetchone()

            conn.close()

            if row:
                return dict(row)
            return None
        except Exception as e:
            logging.error(f"Error getting template {template_id}: {e}")
            return None

    @classmethod
    def add_template(cls, name, content, description="", is_default=0):
        """Add a new template to the database"""
        conn = None
        try:
            # Input validation
            if not name or not isinstance(name, str):
                logging.error(f"Invalid template name: {name}")
                return False, "Invalid template name"

            if not content or not isinstance(content, str):
                logging.error("Template content is required")
                return False, "Template content is required"

            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # If this template should be the default, unset any existing default
            if is_default:
                cursor.execute("UPDATE templates SET is_default = 0")

            cursor.execute(
                "INSERT INTO templates (name, content, description, is_default) VALUES (?, ?, ?, ?)",
                (name, content, description, is_default),
            )

            conn.commit()

            # Get the ID of the inserted template
            template_id = cursor.lastrowid

            conn.close()
            logging.info(f"Successfully added template '{name}' to database")
            return True, template_id
        except sqlite3.IntegrityError:
            logging.error(f"Template with name '{name}' already exists")
            return False, "A template with this name already exists"
        except Exception as e:
            logging.error(f"Error adding template to database: {e}", exc_info=True)
            return False, f"Error adding template: {str(e)}"
        finally:
            if conn:
                conn.close()

    @classmethod
    def update_template(cls, template_id, name, content, description="", is_default=0):
        """Update an existing template"""
        conn = None
        try:
            # Input validation
            if not name or not isinstance(name, str):
                logging.error(f"Invalid template name: {name}")
                return False, "Invalid template name"

            if not content or not isinstance(content, str):
                logging.error("Template content is required")
                return False, "Template content is required"

            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # If this template should be the default, unset any existing default
            if is_default:
                cursor.execute("UPDATE templates SET is_default = 0")

            cursor.execute(
                """
                UPDATE templates 
                SET name = ?, content = ?, description = ?, is_default = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (name, content, description, is_default, template_id),
            )

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(
                    f"Successfully updated template '{name}' (ID: {template_id})"
                )
                return True, None
            else:
                return False, f"Template with ID {template_id} not found"
        except sqlite3.IntegrityError:
            logging.error(f"Template name '{name}' conflicts with an existing template")
            return False, "A template with this name already exists"
        except Exception as e:
            logging.error(f"Error updating template: {e}", exc_info=True)
            return False, f"Error updating template: {str(e)}"
        finally:
            if conn:
                conn.close()

    @classmethod
    def delete_template(cls, template_id):
        """Delete a template from the database"""
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # Check if this is the default template
            cursor.execute(
                "SELECT is_default FROM templates WHERE id = ?", (template_id,)
            )
            row = cursor.fetchone()

            if row and row[0] == 1:
                return False, "Cannot delete the default template"

            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(f"Successfully deleted template ID {template_id}")
                return True, None
            else:
                return False, f"Template with ID {template_id} not found"
        except Exception as e:
            logging.error(f"Error deleting template: {e}")
            return False, f"Error deleting template: {str(e)}"

    @classmethod
    def set_default_template(cls, template_id):
        """Set a template as the default"""
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # First, unset any existing default
            cursor.execute("UPDATE templates SET is_default = 0")

            # Set the new default
            cursor.execute(
                "UPDATE templates SET is_default = 1 WHERE id = ?", (template_id,)
            )

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()

            if success:
                logging.info(f"Set template ID {template_id} as default")
                return True, None
            else:
                return False, f"Template with ID {template_id} not found"
        except Exception as e:
            logging.error(f"Error setting default template: {e}")
            return False, f"Error setting default template: {str(e)}"

    @classmethod
    def initialize_default_template(cls):
        """Initialize the database with the default template if none exists"""
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # Check if there are any templates
            cursor.execute("SELECT COUNT(*) FROM templates")
            count = cursor.fetchone()[0]

            if count == 0:
                # No templates exist, create the default one
                default_content = cls.DEFAULT_TEMPLATE.read_text()
                cursor.execute(
                    """
                    INSERT INTO templates (name, content, description, is_default)
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        "Default Template",
                        default_content,
                        "The standard feature implementation template",
                    ),
                )
                conn.commit()
                logging.info("Initialized default template in database")

            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error initializing default template: {e}")
            return False

    @classmethod
    def create_standard_templates(cls):
        """Create standard templates including the default one"""
        try:
            # First check if we need to initialize the database
            if not cls.DB_PATH.exists():
                cls._init_preset_db()

            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            # Check if there are any templates
            cursor.execute("SELECT COUNT(*) FROM templates")
            count = cursor.fetchone()[0]

            # Load the default template content
            default_content = cls.DEFAULT_TEMPLATE.read_text()

            # Create a condensed/minimal template
            minimal_template = """# Feature Implementation Prompt

You are tasked with implementing a feature in a production environment. Please follow these guidelines:

## RELEVANT CODE CONTEXT
```
{relevant_code_context}
```

## JIRA DESCRIPTION
```
{jira_description}
```

## ADDITIONAL INSTRUCTIONS
```
{additional_instructions}
```

## IMPLEMENTATION TASK
Please implement the required feature based on the provided information. Ensure your code is production-ready, follows best practices, and adheres to the existing code conventions.
"""

            if count == 0:
                # No templates exist, create the default one and other standard ones
                cursor.execute(
                    """
                    INSERT INTO templates (name, content, description, is_default)
                    VALUES (?, ?, ?, 1)
                    """,
                    (
                        "Default Template",
                        default_content,
                        "The standard feature implementation template",
                    ),
                )

                # Add a minimal template
                cursor.execute(
                    """
                    INSERT INTO templates (name, content, description, is_default)
                    VALUES (?, ?, ?, 0)
                    """,
                    (
                        "Minimal Template",
                        minimal_template,
                        "A simplified template with only the essential sections",
                    ),
                )

                conn.commit()
                logging.info("Created standard templates in database")

            conn.close()
            return True
        except Exception as e:
            logging.error(f"Error creating standard templates: {e}")
            return False

    # Load presets on import
    REFINED_PRESETS = {}

    # We'll load presets in app.py instead to avoid the classmethod call issue
