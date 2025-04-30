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
    WORKSPACE_ROOT = Path("/app") if os.path.exists("/app") else Path.cwd().parent
    MODULE_DIR = Path(__file__).parent
    DEFAULT_TEMPLATE = MODULE_DIR / "feature_implementation_template.md"
    DEFAULT_OUTPUT_DIR = MODULE_DIR / "outputs"
    DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "implementation_prompt.md"

    # Database configuration for persistent presets
    DB_PATH = MODULE_DIR / "data" / "presets.db"

    # Ensure the data directory exists
    (MODULE_DIR / "data").mkdir(exist_ok=True)

    # File explorer configuration
    SCAN_DIRS = ["data"]
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

            conn.commit()
            conn.close()
            logging.info("Preset database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing preset database: {e}")

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
        try:
            conn = sqlite3.connect(str(cls.DB_PATH))
            cursor = conn.cursor()

            cursor.execute("DELETE FROM presets WHERE name = ?", (name,))

            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting preset from database: {e}")
            return False

    # Load presets on import
    REFINED_PRESETS = {}

    # We'll load presets in app.py instead to avoid the classmethod call issue
