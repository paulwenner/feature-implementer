from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    Response,
    render_template_string,
)
import json
import logging
import os.path
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import sqlite3
import platform

from .config import (
    Config,
    get_app_db_path,
    initialize_app_database,
    load_default_template_content,
)
from . import database
from .file_utils import get_file_tree, read_file_content
from .prompt_generator import generate_prompt


def load_prompt_templates_from_dir():
    """Load markdown files from the prompts directory and add them to the database."""
    logger = logging.getLogger(__name__)
    prompts_dir = Config.PROMPTS_DIR
    db_path = get_app_db_path()

    # Ensure prompts directory exists
    try:
        prompts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured prompts directory exists at: {prompts_dir}")
    except Exception as e:
        logger.error(f"Failed to create prompts directory {prompts_dir}: {e}")
        return

    if not prompts_dir.exists():
        logger.error(
            f"Prompts directory does not exist despite creation attempt: {prompts_dir}"
        )
        return

    logger.info(f"Loading prompt templates from directory: {prompts_dir}")

    # List files to help with debugging
    try:
        files = list(prompts_dir.glob("*.md"))
        logger.info(f"Found {len(files)} markdown files in {prompts_dir}")
        for file in files:
            logger.info(f"  - {file.name}")
    except Exception as e:
        logger.error(f"Error listing files in prompts dir {prompts_dir}: {e}")
        files = []

    try:
        # Get existing template names to avoid duplicates
        existing_templates = database.get_templates(db_path)
        existing_names = {template["name"] for template in existing_templates}

        # Also check file-based templates that were previously loaded
        file_templates = {
            t["name"] for t in existing_templates if "(File)" in t["name"]
        }

        # Track loaded templates for summary
        loaded_templates = []
        skipped_templates = []

        count = 0
        for file_path in prompts_dir.glob("*.md"):
            template_name = file_path.stem
            file_template_name = f"{template_name} (File)"

            # Skip if a template with this name already exists but not if it's a previously loaded file template
            # This allows refreshing file-based templates
            if (
                template_name in existing_names
                and file_template_name not in file_templates
            ):
                logger.debug(f"Template '{template_name}' already exists, skipping")
                skipped_templates.append(template_name)
                continue

            try:
                # Check file readability and permissions
                if not os.access(str(file_path), os.R_OK):
                    logger.warning(f"No read permission for template file: {file_path}")
                    skipped_templates.append(f"{template_name} (permission denied)")
                    continue

                content = file_path.read_text()

                # Skip empty files
                if not content.strip():
                    logger.warning(f"Empty template file: {file_path}, skipping")
                    skipped_templates.append(f"{template_name} (empty)")
                    continue

                # Either add new template or update existing file-based template
                if file_template_name in file_templates:
                    # Update existing file template
                    template_id = next(
                        t["id"]
                        for t in existing_templates
                        if t["name"] == file_template_name
                    )
                    success, result = database.update_template(
                        db_path,
                        template_id=template_id,
                        name=file_template_name,
                        content=content,
                        description=f"Loaded from file: {file_path.name} (updated)",
                        is_default=False,  # Don't change default status on update
                    )
                    if success:
                        loaded_templates.append(f"{template_name} (updated)")
                        logger.info(
                            f"Updated template '{template_name}' from file {file_path.name}"
                        )
                    else:
                        logger.warning(
                            f"Failed to update template from {file_path}: {result}"
                        )
                        skipped_templates.append(f"{template_name} (update failed)")
                else:
                    # Add new template
                    success, result = database.add_template(
                        db_path,
                        name=file_template_name,
                        content=content,
                        description=f"Loaded from file: {file_path.name}",
                        is_default=False,
                    )
                    if success:
                        count += 1
                        loaded_templates.append(template_name)
                        existing_names.add(template_name)
                        logger.info(
                            f"Added template '{template_name}' from file {file_path.name}"
                        )
                    else:
                        logger.warning(
                            f"Failed to add template from {file_path}: {result}"
                        )
                        skipped_templates.append(f"{template_name} (add failed)")

            except Exception as e:
                logger.error(
                    f"Error processing template file {file_path}: {e}", exc_info=True
                )
                skipped_templates.append(f"{template_name} (error: {str(e)[:30]}...)")

        # Summary logging
        if loaded_templates:
            logger.info(
                f"Successfully loaded {len(loaded_templates)} templates: {', '.join(loaded_templates[:5])}"
                + (
                    f" and {len(loaded_templates)-5} more"
                    if len(loaded_templates) > 5
                    else ""
                )
            )
        if skipped_templates:
            logger.info(
                f"Skipped {len(skipped_templates)} templates: {', '.join(skipped_templates[:5])}"
                + (
                    f" and {len(skipped_templates)-5} more"
                    if len(skipped_templates) > 5
                    else ""
                )
            )

    except Exception as e:
        logger.error(
            f"Error during template loading from directory: {e}", exc_info=True
        )


def create_app():
    # When installed as a package, Flask automatically finds 'templates' and 'static'
    # folders within the package if they are included as package_data.
    app = Flask(__name__)

    app.secret_key = Config.SECRET_KEY

    # Configure logging
    log_level = logging.DEBUG if app.debug else logging.INFO
    # Basic config if no handlers are present (e.g. running directly)
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    logger.info(f"Flask app starting up. Debug mode: {app.debug}")

    # Initialize database structure (calls database.initialize_database)
    try:
        logger.info("Initializing application database...")
        initialize_app_database()  # This now handles schema and default templates
        logger.info("Application database initialization complete.")
    except Exception as e:
        # Log the error, but allow the app to potentially start
        # depending on whether DB access is critical for all routes immediately.
        logger.error(
            f"CRITICAL: Failed to initialize application database: {e}", exc_info=True
        )
        # Optionally, you could re-raise or return None here to prevent app start
        # flash("Critical database initialization error. App may not function.", "error")

    # Load additional prompt templates from the prompts directory
    try:
        load_prompt_templates_from_dir()
    except Exception as e:
        logger.error(
            f"Error loading prompt templates from directory: {e}", exc_info=True
        )

    # --- App startup tasks (moved from Config) ---
    # Pre-populate the file tree cache on startup
    try:
        logger.info("Performing initial file tree scan...")
        get_file_tree(Config.SCAN_DIRS, force_rescan=True)
        logger.info("Initial file tree scan complete and cached.")
    except Exception as e:
        logger.error(f"ERROR: Initial file tree scan failed: {e}", exc_info=True)

    # --- Routes ---
    # Helper to get DB path easily in routes
    def _db_path() -> Path:
        return get_app_db_path()

    @app.route("/", methods=["GET"])
    def index() -> str:
        """Render the main application page."""
        logger.debug("Rendering index page")
        db_path = _db_path()
        try:
            file_tree = get_file_tree(Config.SCAN_DIRS)

            # Get presets from DB
            presets = database.get_presets(db_path)
            # Debug info for presets
            logger.debug(f"Loaded {len(presets)} presets")
            for name, files in presets.items():
                logger.debug(f"Preset '{name}': {len(files)} files")

            # Fix the presets structure for JavaScript
            # JavaScript expects: { "presetName": { "files": ["file1", "file2"] } }
            formatted_presets = {}
            for name, files in presets.items():
                formatted_presets[name] = {"files": files}

            presets_json = json.dumps(formatted_presets)

            # Get available templates from DB
            templates = database.get_templates(db_path)
            default_template_id = database.get_default_template_id(db_path)
            templates_json = json.dumps(templates)

            # Get default template content preview
            template_preview = "Default template not configured or found."
            if default_template_id:
                default_template_data = database.get_template_by_id(
                    db_path, default_template_id
                )
                if default_template_data and default_template_data.get("content"):
                    preview_content = default_template_data["content"]
                    template_preview = (
                        (preview_content[:500] + "...")
                        if len(preview_content) > 500
                        else preview_content
                    )
                else:
                    logger.warning(
                        f"Default template ID {default_template_id} found but content missing."
                    )
            else:
                logger.warning("No default template ID found in database.")

            # Get app version for debugging
            app_version = getattr(Config, "VERSION", "Unknown")
            host_info = platform.platform()

            logger.debug(
                f"Rendering index template with app version: {app_version}, host: {host_info}"
            )

            return render_template(
                "index.html",
                file_tree=file_tree,
                scan_dirs=Config.SCAN_DIRS,
                template_preview=template_preview,
                presets=formatted_presets,
                presets_json=presets_json,
                templates=templates,
                templates_json=templates_json,
                default_template_id=default_template_id,
                app_version=app_version,
                host_info=host_info,
            )
        except Exception as e:
            logger.error(f"Error rendering index page: {e}", exc_info=True)
            flash(f"Error rendering page: {e}", "error")
            # Render with empty data on error
            return render_template(
                "index.html",
                file_tree={},
                scan_dirs=Config.SCAN_DIRS,
                template_preview="Error loading page data.",
                presets={},
                presets_json="{}",
                templates=[],
                templates_json="[]",
                default_template_id=None,
                app_version="Unknown",
                host_info="Unknown",
            )

    @app.route("/generate", methods=["POST"])
    def handle_generate() -> Response:
        """Generate a feature implementation prompt."""
        logger.info("--- Handling /generate POST request ---")
        db_path = _db_path()
        try:
            selected_files = request.form.getlist("context_files")
            jira_desc = request.form.get("jira_description", "")
            instructions = request.form.get("additional_instructions", "")
            template_id_str = request.form.get("template_id")

            template_id: Optional[int] = None
            if template_id_str and template_id_str.isdigit():
                template_id = int(template_id_str)
            else:
                # Fallback to default template ID from DB
                template_id = database.get_default_template_id(db_path)
                if not template_id:
                    logger.error(
                        "Generate failed: No template ID provided and no default template set in DB."
                    )
                    return (
                        jsonify(
                            {
                                "error": "No template selected and no default template configured."
                            }
                        ),
                        400,
                    )

            if not selected_files:
                logger.warning("No files selected, returning error.")
                return (
                    jsonify({"error": "Please select at least one context file."}),
                    400,
                )

            logger.info(
                f"Files selected ({len(selected_files)}), generating prompt using template ID: {template_id}..."
            )

            # Generate prompt using template ID (guaranteed to have one here)
            final_prompt = generate_prompt(
                db_path=db_path,
                template_id=template_id,
                context_files=selected_files,
                jira_description=jira_desc,
                additional_instructions=instructions,
            )

            if (
                final_prompt is None
            ):  # Check if generate_prompt indicated an error (e.g., template not found)
                logger.error(
                    f"Prompt generation failed for template ID {template_id}. Check logs for details."
                )
                return (
                    jsonify(
                        {
                            "error": f"Failed to generate prompt using template ID {template_id}. Template might be missing or invalid."
                        }
                    ),
                    500,
                )

            char_count = len(final_prompt)
            # TODO: Implement more accurate token estimation using tiktoken if needed
            token_estimate = char_count // 4  # Rough estimate

            logger.info(
                f"Prompt generated ({char_count} chars, ~{token_estimate} tokens), returning JSON."
            )

            return jsonify(
                {
                    "prompt": final_prompt,
                    "char_count": char_count,
                    "token_estimate": token_estimate,
                }
            )
        # Catch specific errors if generate_prompt raises them
        except FileNotFoundError as e:
            logger.error(f"File not found during prompt generation: {e}", exc_info=True)
            return jsonify({"error": f"Context file not found: {e}"}), 404
        except ValueError as e:
            logger.error(f"Value error during prompt generation: {e}", exc_info=True)
            return (
                jsonify({"error": f"Error generating prompt: {e}"}),
                500,
            )  # Or 400 if user input error
        except Exception as e:
            logger.error(
                f"Unexpected error during prompt generation: {e}", exc_info=True
            )
            return jsonify({"error": f"An unexpected server error occurred: {e}"}), 500

    @app.route("/get_file_content", methods=["GET"])
    def get_file_content() -> Response:
        """Get content of a file with strict path validation."""
        logger.debug("Handling /get_file_content request")
        try:
            file_path_str = request.args.get("path")
            if not file_path_str:
                return jsonify({"error": "No file path provided"}), 400

            # Security check: Use Config.WORKSPACE_ROOT for validation
            try:
                workspace_root = Config.WORKSPACE_ROOT
                # Resolve both paths AFTER joining with root if relative
                # Ensure file_path_str is treated as relative to workspace_root initially
                abs_requested_path = (workspace_root / file_path_str).resolve()

                # Check if the resolved path is within the resolved workspace root
                if (
                    workspace_root not in abs_requested_path.parents
                    and abs_requested_path != workspace_root
                ):
                    # More robust check using common path
                    if os.path.commonpath(
                        [str(workspace_root), str(abs_requested_path)]
                    ) != str(workspace_root):
                        logger.warning(
                            f"Security: Blocked access to path outside workspace: {file_path_str} (resolved: {abs_requested_path})"
                        )
                        return (
                            jsonify({"error": "Access denied: Path outside workspace"}),
                            403,
                        )

                requested_path = abs_requested_path  # Use the resolved, validated path

                if not requested_path.is_file():
                    logger.warning(
                        f"File not found at validated path: {requested_path}"
                    )
                    return (
                        jsonify({"error": f"Not a file or not found: {file_path_str}"}),
                        404,
                    )
            except (
                ValueError,
                OSError,
                SecurityError,
            ) as e:  # Catch potential resolution/path errors
                logger.warning(f"Path validation error for {file_path_str}: {e}")
                return (
                    jsonify(
                        {"error": f"Invalid or inaccessible path: {file_path_str}"}
                    ),
                    400,
                )

            # Read content using the validated Path object
            content = read_file_content(requested_path)
            if content is None:  # read_file_content might return None on error
                logger.error(f"Could not read file content for: {requested_path}")
                return jsonify({"error": f"Could not read file: {file_path_str}"}), 500

            return jsonify({"content": content})
        except Exception as e:
            logger.error(f"Error reading file content: {e}", exc_info=True)
            return jsonify({"error": "Server error reading file"}), 500

    @app.route("/presets", methods=["GET"])
    def get_presets_route() -> Response:
        """Get all available presets from the database."""
        logger.debug("Handling GET /presets")
        db_path = _db_path()
        try:
            presets_data = database.get_presets(db_path)

            # Format presets for JavaScript
            formatted_presets = {}
            for preset_name, preset_files in presets_data.items():
                formatted_presets[preset_name] = {"files": preset_files}

            return jsonify({"presets": formatted_presets})
        except Exception as e:
            logger.error(f"Error retrieving presets: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve presets"}), 500

    @app.route("/presets", methods=["POST"])
    def add_preset_route() -> Response:
        """Add a new preset via POST request."""
        logger.info("Handling POST /presets")
        db_path = _db_path()
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON data provided"}), 400

            name = data.get("name")
            files = data.get("files")

            if not name or not isinstance(name, str):
                return (
                    jsonify({"error": "Preset name is required and must be a string"}),
                    400,
                )
            if not files or not isinstance(files, list):
                return jsonify({"error": "Selected files list is required"}), 400
            if not all(isinstance(f, str) for f in files):
                logger.warning(
                    f"Preset '{name}' received non-string file paths. Attempting conversion."
                )
                try:
                    files = [str(f) for f in files]
                except Exception:
                    return jsonify({"error": "File paths must be strings"}), 400

            # Add the preset using the database module
            success = database.add_preset(db_path, name, files)
            if success:
                # Return the updated list of presets
                presets_data = database.get_presets(db_path)

                # Format presets for JavaScript
                formatted_presets = {}
                for preset_name, preset_files in presets_data.items():
                    formatted_presets[preset_name] = {"files": preset_files}

                return jsonify({"success": True, "presets": formatted_presets})
            else:
                # add_preset handles logging, check if it was due to existence?
                # We might need more specific return values from database module
                # For now, assume generic failure.
                logger.error(f"Failed to add preset '{name}' (check logs for details)")
                return (
                    jsonify(
                        {
                            "error": f"Failed to add preset '{name}'. It might already exist or there was a database error."
                        }
                    ),
                    400,
                )  # Or 500?

        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format received"}), 400
        except Exception as e:
            logger.error(f"Error adding preset: {e}", exc_info=True)
            return jsonify({"error": "Server error adding preset"}), 500

    @app.route("/presets/<preset_name>", methods=["DELETE"])
    def delete_preset_route(preset_name: str) -> Response:
        """Delete a preset by name via DELETE request."""
        logger.info(f"Handling DELETE /presets/{preset_name}")
        db_path = _db_path()
        try:
            success = database.delete_preset(db_path, preset_name)
            if success:
                # Return the updated list of presets
                presets_data = database.get_presets(db_path)

                # Format presets for JavaScript
                formatted_presets = {}
                for preset_name, preset_files in presets_data.items():
                    formatted_presets[preset_name] = {"files": preset_files}

                return jsonify({"success": True, "presets": formatted_presets})
            else:
                logger.warning(f"Preset '{preset_name}' not found or deletion failed.")
                return jsonify({"error": f"Preset '{preset_name}' not found"}), 404
        except Exception as e:
            logger.error(f"Error deleting preset '{preset_name}': {e}", exc_info=True)
            return jsonify({"error": "Server error deleting preset"}), 500

    @app.route("/refresh_file_tree", methods=["GET"])
    def refresh_file_tree() -> Response:
        """Rescan the file tree and return the rendered HTML fragment."""
        logger.info("--- Handling /refresh_file_tree GET request ---")
        try:
            file_tree = get_file_tree(Config.SCAN_DIRS, force_rescan=True)
            # Assuming 'macros.html' has a render_file_tree macro
            macro_import = "{% from 'macros.html' import render_file_tree %}"
            rendered_html = render_template_string(
                f"{macro_import}{{{{ render_file_tree(file_tree, 0) }}}}",
                file_tree=file_tree,
            )
            logger.info("File tree refreshed and HTML fragment generated.")
            return jsonify({"html": rendered_html})
        except Exception as e:
            logger.error(f"Error refreshing file tree: {e}", exc_info=True)
            return jsonify({"error": "Error refreshing file tree"}), 500

    # Removed /rescan endpoint as /refresh_file_tree provides the needed data
    # @app.route("/rescan", methods=["POST"])
    # def rescan_files() -> Response: ...

    # Removed /debug/test-json endpoint - enable only if needed for specific debugging
    # @app.route("/debug/test-json", methods=["POST"])
    # def test_json() -> Response: ...

    # --- Template Management Routes ---

    @app.route("/templates", methods=["GET"])
    def get_templates_route() -> Response:
        """Get all templates from the database."""
        logger.debug("Handling GET /templates")
        db_path = _db_path()
        try:
            templates_data = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)
            return jsonify(
                {"templates": templates_data, "default_template_id": default_id}
            )
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}", exc_info=True)
            return jsonify({"error": "Failed to retrieve templates"}), 500

    @app.route("/templates/<int:template_id>", methods=["GET"])
    def get_template_route(template_id: int) -> Response:
        """Get a specific template by ID."""
        logger.debug(f"Handling GET /templates/{template_id}")
        db_path = _db_path()
        try:
            template_data = database.get_template_by_id(db_path, template_id)
            if not template_data:
                return (
                    jsonify({"error": f"Template with ID {template_id} not found"}),
                    404,
                )
            # We might not want to send the full content here if it's large?
            # Or maybe we do for editing. Consider payload size.
            return jsonify({"template": template_data})
        except Exception as e:
            logger.error(f"Error retrieving template {template_id}: {e}", exc_info=True)
            return jsonify({"error": "Server error retrieving template"}), 500

    @app.route("/templates", methods=["POST"])
    def add_template_route() -> Response:
        """Add a new template to the database."""
        logger.info("Handling POST /templates")
        db_path = _db_path()
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON data provided"}), 400

            name = data.get("name")
            content = data.get("content")
            description = data.get("description", "")  # Optional
            is_default = data.get("is_default", False)  # Optional, default to False

            if not name or not isinstance(name, str):
                return (
                    jsonify(
                        {"error": "Template name is required and must be a string"}
                    ),
                    400,
                )
            if content is None or not isinstance(content, str):
                return (
                    jsonify(
                        {"error": "Template content is required and must be a string"}
                    ),
                    400,
                )
            if not isinstance(is_default, bool):
                try:
                    is_default = bool(int(is_default))  # Allow 0 or 1
                except (ValueError, TypeError):
                    return (
                        jsonify(
                            {
                                "error": "Invalid value for is_default (must be boolean or 0/1)"
                            }
                        ),
                        400,
                    )

            # Add the template using database module
            success, result = database.add_template(
                db_path, name, content, description, is_default
            )

            if not success:
                # result contains error message from database module
                logger.warning(f"Failed to add template '{name}': {result}")
                status_code = (
                    409 if "already exists" in str(result) else 500
                )  # Conflict or Server Error
                return jsonify({"error": result}), status_code

            # Return updated list
            templates_data = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)
            new_template_id = result  # result is the new ID on success

            return (
                jsonify(
                    {
                        "message": f"Template '{name}' added successfully with ID {new_template_id}",
                        "template_id": new_template_id,
                        "templates": templates_data,
                        "default_template_id": default_id,
                    }
                ),
                201,
            )  # Created

        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format received"}), 400
        except Exception as e:
            logger.error(f"Error adding template: {e}", exc_info=True)
            return jsonify({"error": "Server error adding template"}), 500

    @app.route("/templates/<int:template_id>", methods=["PUT"])
    def update_template_route(template_id: int) -> Response:
        """Update an existing template."""
        logger.info(f"Handling PUT /templates/{template_id}")
        db_path = _db_path()
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON data provided"}), 400

            # Get data, providing defaults from existing template could be nice, but complex
            name = data.get("name")
            content = data.get("content")
            description = data.get("description")  # If None, don't update?
            is_default_val = data.get("is_default")

            # Validation - need all fields for update?
            if not name or not isinstance(name, str):
                return (
                    jsonify(
                        {"error": "Template name is required and must be a string"}
                    ),
                    400,
                )
            if content is None or not isinstance(content, str):
                return (
                    jsonify(
                        {"error": "Template content is required and must be a string"}
                    ),
                    400,
                )
            if description is not None and not isinstance(description, str):
                return jsonify({"error": "Description must be a string"}), 400

            is_default = None
            if is_default_val is not None:
                if not isinstance(is_default_val, bool):
                    try:
                        is_default = bool(int(is_default_val))
                    except (ValueError, TypeError):
                        return (
                            jsonify(
                                {
                                    "error": "Invalid value for is_default (must be boolean or 0/1)"
                                }
                            ),
                            400,
                        )
                else:
                    is_default = is_default_val
            else:
                # If is_default not provided in PUT, should it retain its value?
                # For simplicity now, assume it needs to be provided or defaults to False
                is_default = False

            # Fetch existing description if not provided?
            if description is None:
                existing_template = database.get_template_by_id(db_path, template_id)
                description = (
                    existing_template.get("description", "")
                    if existing_template
                    else ""
                )

            # Update using database module
            success, error = database.update_template(
                db_path, template_id, name, content, description, is_default
            )

            if not success:
                logger.warning(f"Failed to update template ID {template_id}: {error}")
                if "not found" in str(error):
                    return jsonify({"error": error}), 404
                elif "already exists" in str(error):
                    return jsonify({"error": error}), 409  # Conflict
                else:
                    return jsonify({"error": error or "Failed to update template"}), 500

            # Return updated list
            templates_data = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)

            return jsonify(
                {
                    "message": f"Template '{name}' (ID: {template_id}) updated successfully",
                    "templates": templates_data,
                    "default_template_id": default_id,
                }
            )
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format received"}), 400
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
            return jsonify({"error": "Server error updating template"}), 500

    @app.route("/templates/<int:template_id>", methods=["DELETE"])
    def delete_template_route(template_id: int) -> Response:
        """Delete a template."""
        logger.info(f"Handling DELETE /templates/{template_id}")
        db_path = _db_path()
        try:
            success, error = database.delete_template(db_path, template_id)

            if not success:
                logger.warning(f"Failed to delete template ID {template_id}: {error}")
                if "not found" in str(error):
                    return jsonify({"error": error}), 404
                elif "Cannot delete the default template" in str(error):
                    return jsonify({"error": error}), 400  # Bad Request
                else:
                    return jsonify({"error": error or "Failed to delete template"}), 500

            # Return updated list
            templates_data = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)

            return jsonify(
                {
                    "message": f"Template with ID {template_id} deleted successfully",
                    "templates": templates_data,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}", exc_info=True)
            return jsonify({"error": "Server error deleting template"}), 500

    @app.route("/templates/<int:template_id>/set-default", methods=["POST"])
    def set_default_template_route(template_id: int) -> Response:
        """Set a template as the default."""
        logger.info(f"Handling POST /templates/{template_id}/set-default")
        db_path = _db_path()
        try:
            success, error = database.set_default_template(db_path, template_id)

            if not success:
                logger.warning(
                    f"Failed to set template ID {template_id} as default: {error}"
                )
                if "not found" in str(error):
                    return jsonify({"error": error}), 404
                else:
                    return (
                        jsonify({"error": error or "Failed to set default template"}),
                        500,
                    )

            # Return updated list
            templates_data = database.get_templates(db_path)
            # The default_id should now be template_id

            return jsonify(
                {
                    "message": f"Template with ID {template_id} set as default",
                    "templates": templates_data,
                    "default_template_id": template_id,
                }
            )
        except Exception as e:
            logger.error(
                f"Error setting default template {template_id}: {e}", exc_info=True
            )
            return jsonify({"error": "Server error setting default template"}), 500

    @app.route("/template-manager", methods=["GET"])
    def template_manager() -> str:
        """Render the template management page."""
        logger.debug("Rendering template manager page")
        db_path = _db_path()
        try:
            # Fetch current templates and default ID
            templates = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)
            # Note: initialize_app_database should have ensured defaults exist if needed

            return render_template(
                "template_manager.html",
                templates=templates,
                default_template_id=default_id,
            )
        except Exception as e:
            logger.error(f"Error rendering template manager: {e}", exc_info=True)
            flash(f"Error loading template manager: {e}", "error")
            return render_template(
                "template_manager.html", templates=[], default_template_id=None
            )

    @app.route("/templates/reset-to-standard", methods=["POST"])
    def reset_to_standard_templates() -> Response:
        """Reset templates to standard set (deletes all first)."""
        logger.warning("Handling POST /templates/reset-to-standard")
        db_path = _db_path()
        try:
            # Delete all existing templates
            deleted_ok = database.delete_all_templates(db_path)
            if not deleted_ok:
                logger.error("Failed to delete existing templates during reset.")
                return (
                    jsonify(
                        {"error": "Failed to clear existing templates before reset."}
                    ),
                    500,
                )

            logger.info(
                "Existing templates cleared. Re-initializing standard templates..."
            )
            # Re-run the initialization logic which includes adding standard templates
            initialize_app_database()
            logger.info("Standard templates re-initialized.")

            # Fetch the new state
            templates = database.get_templates(db_path)
            default_id = database.get_default_template_id(db_path)

            return jsonify(
                {
                    "message": "Reset to standard templates successfully",
                    "templates": templates,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error resetting to standard templates: {e}", exc_info=True)
            return jsonify({"error": "Server error resetting templates"}), 500

    @app.route("/debug/presets", methods=["GET"])
    def debug_presets() -> Response:
        """Debug route to examine preset data structure."""
        logger.debug("Handling GET /debug/presets")
        db_path = _db_path()
        try:
            # Get raw presets from DB
            raw_presets = database.get_presets(db_path)

            # Format presets for JavaScript
            formatted_presets = {}
            for preset_name, preset_files in raw_presets.items():
                formatted_presets[preset_name] = {"files": preset_files}

            # Prepare debug info
            debug_info = {
                "raw_presets": raw_presets,
                "formatted_presets": formatted_presets,
                "preset_count": len(raw_presets),
                "formatted_json": json.dumps(formatted_presets),
            }

            return jsonify(debug_info)
        except Exception as e:
            logger.error(f"Error debugging presets: {e}", exc_info=True)
            return jsonify({"error": f"Error: {str(e)}"}), 500

    return app


# Note: The run_web_app function is now in cli.py and serves as the entry point
# for the 'feature-implementer' script.
# If you need to run directly using `python -m feature_implementer_core.app`,
# you might add a `if __name__ == "__main__":` block here to call create_app().run().

# Example for direct execution (optional):
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.DEBUG)
#     flask_app = create_app()
#     flask_app.run(debug=True, host='0.0.0.0', port=5001) # Use a different port than default
