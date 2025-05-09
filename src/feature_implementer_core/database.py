import sqlite3
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

logger = logging.getLogger(__name__)

# Define schema globally for clarity
SCHEMA = {
    "presets": """
        CREATE TABLE IF NOT EXISTS presets (
            name TEXT PRIMARY KEY,
            files TEXT NOT NULL -- JSON encoded list of file paths
        )
    """,
    "templates": """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            content TEXT NOT NULL,
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "settings": """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """,
}


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Establish and return a database connection."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error to {db_path}: {e}", exc_info=True)
        raise  # Re-raise the exception


def initialize_database(db_path: Path):
    """Initialize the database, creating tables if they don't exist."""
    logger.info(f"Initializing database schema at {db_path}...")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(SCHEMA["presets"])
            cursor.execute(SCHEMA["templates"])
            cursor.execute(SCHEMA["settings"])
            conn.commit()
        logger.info("Database schema initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
        raise


# --- Template Functions ---


def add_template(
    db_path: Path,
    name: str,
    content: str,
    description: Optional[str] = "",
    is_default: bool = False,
) -> Tuple[bool, Union[int, str]]:
    """Add a new template to the database."""
    logger.info(f"Adding template: name={name}, default={is_default}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # If setting as default, unset other defaults first
            if is_default:
                cursor.execute("UPDATE templates SET is_default = 0")

            cursor.execute(
                "INSERT INTO templates (name, content, description, is_default) VALUES (?, ?, ?, ?)",
                (name, content, description, 1 if is_default else 0),
            )
            template_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Template '{name}' added with ID {template_id}")
            return True, template_id
    except sqlite3.IntegrityError:
        logger.warning(f"Failed to add template: Name '{name}' already exists.")
        return False, f"Template name '{name}' already exists."
    except sqlite3.Error as e:
        logger.error(f"Database error adding template: {e}", exc_info=True)
        return False, str(e)


def get_templates(db_path: Path) -> List[Dict[str, Any]]:
    """Retrieve all templates from the database."""
    logger.debug(f"Fetching all templates from {db_path}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description, content, is_default, created_at FROM templates ORDER BY name"
            )
            templates = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Found {len(templates)} templates")
            return templates
    except sqlite3.Error as e:
        logger.error(f"Database error fetching templates: {e}", exc_info=True)
        return []


def get_template_by_id(db_path: Path, template_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a specific template by its ID."""
    logger.debug(f"Fetching template ID {template_id}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description, content, is_default, created_at FROM templates WHERE id = ?",
                (template_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                logger.warning(f"Template ID {template_id} not found.")
                return None
    except sqlite3.Error as e:
        logger.error(
            f"Database error fetching template {template_id}: {e}", exc_info=True
        )
        return None


def update_template(
    db_path: Path,
    template_id: int,
    name: str,
    content: str,
    description: Optional[str] = "",
    is_default: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Update an existing template."""
    logger.info(
        f"Updating template ID {template_id}: name={name}, default={is_default}"
    )
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Check if template exists
            cursor.execute("SELECT id FROM templates WHERE id = ?", (template_id,))
            if not cursor.fetchone():
                return False, f"Template with ID {template_id} not found."

            # If setting as default, unset other defaults first
            if is_default:
                cursor.execute(
                    "UPDATE templates SET is_default = 0 WHERE id != ?", (template_id,)
                )

            cursor.execute(
                """UPDATE templates
                   SET name = ?, content = ?, description = ?, is_default = ?
                   WHERE id = ?""",
                (name, content, description, 1 if is_default else 0, template_id),
            )
            conn.commit()
            logger.info(f"Template ID {template_id} updated successfully.")
            return True, None
    except sqlite3.IntegrityError:
        logger.warning(
            f"Failed to update template {template_id}: Name '{name}' already exists."
        )
        return False, f"Template name '{name}' already exists for another template."
    except sqlite3.Error as e:
        logger.error(
            f"Database error updating template {template_id}: {e}", exc_info=True
        )
        return False, str(e)


def delete_template(db_path: Path, template_id: int) -> Tuple[bool, Optional[str]]:
    """Delete a template by its ID."""
    logger.info(f"Attempting to delete template ID {template_id}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT is_default FROM templates WHERE id = ?", (template_id,)
            )
            result = cursor.fetchone()

            if not result:
                logger.warning(f"Template ID {template_id} not found for deletion.")
                return False, f"Template with ID {template_id} not found."

            if result["is_default"]:
                logger.warning(f"Cannot delete default template ID {template_id}.")
                return False, "Cannot delete the default template."

            cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Template ID {template_id} deleted successfully.")
                return True, None
            else:
                # Should have been caught by the SELECT earlier, but belt-and-suspenders
                logger.warning(
                    f"Template ID {template_id} not found during DELETE operation."
                )
                return False, f"Template with ID {template_id} not found."
    except sqlite3.Error as e:
        logger.error(
            f"Database error deleting template {template_id}: {e}", exc_info=True
        )
        return False, str(e)


def set_default_template(db_path: Path, template_id: int) -> Tuple[bool, Optional[str]]:
    """Set a specific template as the default."""
    logger.info(f"Setting template ID {template_id} as default.")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            # Ensure the template exists
            cursor.execute("SELECT id FROM templates WHERE id = ?", (template_id,))
            if not cursor.fetchone():
                logger.warning(
                    f"Cannot set default: Template ID {template_id} not found."
                )
                return False, f"Template with ID {template_id} not found."

            # Unset current default
            cursor.execute("UPDATE templates SET is_default = 0")
            # Set new default
            cursor.execute(
                "UPDATE templates SET is_default = 1 WHERE id = ?", (template_id,)
            )
            conn.commit()
            logger.info(f"Template ID {template_id} successfully set as default.")
            return True, None
    except sqlite3.Error as e:
        logger.error(
            f"Database error setting default template {template_id}: {e}", exc_info=True
        )
        return False, str(e)


def get_default_template_id(db_path: Path) -> Optional[int]:
    """Get the ID of the default template."""
    logger.debug("Fetching default template ID")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM templates WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row["id"]
            else:
                logger.debug("No default template found.")
                return None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching default template ID: {e}", exc_info=True)
        return None


def delete_all_templates(db_path: Path) -> bool:
    """Deletes all templates from the database."""
    logger.warning(f"Deleting ALL templates from {db_path}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM templates")
            conn.commit()
            logger.info("All templates deleted successfully.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error deleting all templates: {e}", exc_info=True)
        return False


# --- Preset Functions ---


def add_preset(db_path: Path, name: str, files: List[str]) -> bool:
    """Add or update a preset with the given name and file list."""
    logger.info(f"Adding/updating preset: name={name}")
    try:
        # Ensure we have valid file paths
        sanitized_files = [str(path).replace("\\", "/") for path in files if path]

        # Use ensure_ascii=False to properly handle UTF-8 characters
        files_json = json.dumps(sanitized_files, ensure_ascii=False)

        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO presets (name, files) VALUES (?, ?)",
                (name, files_json),
            )
            conn.commit()
            logger.info(f"Preset '{name}' saved successfully.")
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error saving preset '{name}': {e}", exc_info=True)
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Error encoding files for preset '{name}': {e}", exc_info=True)
        return False


def get_presets(db_path: Path) -> Dict[str, List[str]]:
    """Retrieve all presets from the database."""
    logger.debug(f"Fetching all presets from {db_path}")
    presets = {}
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, files FROM presets ORDER BY name")
            for row in cursor.fetchall():
                try:
                    # Get the raw JSON string
                    file_json_str = row["files"]

                    # Validate it's valid JSON before attempting to parse
                    if not file_json_str or not file_json_str.strip().startswith("["):
                        logger.warning(
                            f"Invalid JSON format for preset '{row['name']}': {file_json_str}"
                        )
                        continue

                    # Parse the JSON
                    files_list = json.loads(file_json_str)

                    # Ensure it's a list of strings
                    if isinstance(files_list, list) and all(
                        isinstance(f, str) for f in files_list
                    ):
                        presets[row["name"]] = files_list
                    else:
                        logger.warning(
                            f"Invalid format for files in preset '{row['name']}'. Skipping."
                        )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Could not decode files JSON for preset '{row['name']}': {e}"
                    )
            logger.debug(f"Found {len(presets)} valid presets")
            return presets
    except sqlite3.Error as e:
        logger.error(f"Database error fetching presets: {e}", exc_info=True)
        return {}


def delete_preset(db_path: Path, name: str) -> bool:
    """Delete a preset by name."""
    logger.info(f"Attempting to delete preset: {name}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM presets WHERE name = ?", (name,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Preset '{name}' deleted successfully.")
                return True
            else:
                logger.warning(f"Preset '{name}' not found for deletion.")
                return False
    except sqlite3.Error as e:
        logger.error(f"Database error deleting preset '{name}': {e}", exc_info=True)
        return False


# --- Settings Functions ---


def get_setting(db_path: Path, key: str) -> Optional[str]:
    """Retrieve a setting value by key."""
    logger.debug(f"Getting setting: {key}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error getting setting {key}: {e}", exc_info=True)
        return None


def set_setting(db_path: Path, key: str, value: str) -> bool:
    """Set a setting value by key (insert or update)."""
    logger.debug(f"Setting setting: {key} = {value}")
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Database error setting {key}: {e}", exc_info=True)
        return False


# Example Usage (can be removed or put under if __name__ == "__main__")
# if __name__ == "__main__":
#     DB_FILE = Path("./feature_implementer.db")
#     initialize_database(DB_FILE)
#     # Example template operations
#     add_template(DB_FILE, "Test Template", "This is {{content}}", "A test", is_default=True)
#     templates = get_templates(DB_FILE)
#     print("Templates:", templates)
#     default_id = get_default_template_id(DB_FILE)
#     print("Default ID:", default_id)
#     # Example preset operations
#     add_preset(DB_FILE, "Test Preset", ["file1.py", "src/app.py"])
#     presets = get_presets(DB_FILE)
#     print("Presets:", presets)
#     # Example settings
#     set_setting(DB_FILE, "user_preference", "dark_mode")
#     pref = get_setting(DB_FILE, "user_preference")
#     print("User Preference:", pref)
