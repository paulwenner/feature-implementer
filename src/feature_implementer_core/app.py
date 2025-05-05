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

from .config import Config
from .file_utils import get_file_tree, read_file_content
from .prompt_generator import generate_prompt


def create_app():
    # When installed as a package, Flask automatically finds 'templates' and 'static'
    # folders within the package if they are included as package_data.
    app = Flask(__name__)

    app.secret_key = Config.SECRET_KEY

    # Configure logging
    if app.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
        )

    logger = logging.getLogger(__name__)

    # Initialize database structure first
    try:
        logger.info("Initializing database structure...")
        Config._init_preset_db()
        logger.info("Database structure initialized.")
    except Exception as e:
        logger.error(
            f"ERROR: Failed to initialize database structure: {e}", exc_info=True
        )

    # Load presets at startup
    try:
        Config.REFINED_PRESETS = Config.get_presets()
        logger.info(f"Loaded {len(Config.REFINED_PRESETS)} presets from database")
    except Exception as e:
        logger.error(f"Failed to load presets: {e}", exc_info=True)
        Config.REFINED_PRESETS = {}

    # Pre-populate the file tree cache on startup
    try:
        logger.info("Performing initial file tree scan...")
        get_file_tree(Config.SCAN_DIRS, force_rescan=True)
        logger.info("Initial file tree scan complete and cached.")
    except Exception as e:
        logger.error(f"ERROR: Initial file tree scan failed: {e}", exc_info=True)

    # Initialize standard templates (after database is created)
    try:
        logger.info("Initializing standard templates...")
        Config.create_standard_templates()
        logger.info("Standard templates initialized.")
    except Exception as e:
        logger.error(
            f"ERROR: Failed to initialize standard templates: {e}", exc_info=True
        )

    @app.route("/", methods=["GET"])
    def index() -> str:
        """Render the main application page.

        Returns:
            Rendered HTML template with file tree and form
        """
        try:
            file_tree = get_file_tree(Config.SCAN_DIRS)

            template_preview = ""
            try:
                if Config.DEFAULT_TEMPLATE.exists():
                    template_preview = (
                        read_file_content(Config.DEFAULT_TEMPLATE)[:500] + "..."
                    )
                else:
                    template_preview = "Default template not found."
            except Exception as template_error:
                logger.error(f"Error reading template preview: {template_error}")
                template_preview = "Error loading template preview."

            # Get the latest presets from the database
            presets = Config.REFINED_PRESETS
            presets_json = json.dumps(presets)

            # Get available templates
            templates = Config.get_templates()
            default_template_id = Config.get_default_template_id()
            templates_json = json.dumps(templates)

            # Initialize default template if none exists
            if not templates:
                Config.initialize_default_template()
                templates = Config.get_templates()
                default_template_id = Config.get_default_template_id()
                templates_json = json.dumps(templates)

            return render_template(
                "index.html",
                file_tree=file_tree,
                scan_dirs=Config.SCAN_DIRS,
                template_preview=template_preview,
                presets=presets,
                presets_json=presets_json,
                templates=templates,
                templates_json=templates_json,
                default_template_id=default_template_id,
            )
        except Exception as e:
            flash(f"Error rendering page: {e}", "error")
            return render_template(
                "index.html",
                file_tree={},
                scan_dirs=Config.SCAN_DIRS,
                template_preview="Error loading page.",
                presets={},
                presets_json="{}",
                templates=[],
                templates_json="[]",
                default_template_id=None,
            )

    @app.route("/generate", methods=["POST"])
    def handle_generate() -> Response:
        """Generate a feature implementation prompt from selected files and inputs.

        Returns:
            JSON response with the generated prompt or error message
        """
        logger.info("--- Handling /generate POST request ---")
        try:
            selected_files = request.form.getlist("context_files")
            jira_desc = request.form.get("jira_description", "")
            instructions = request.form.get("additional_instructions", "")
            template_id = request.form.get("template_id")

            if template_id and template_id.isdigit():
                template_id = int(template_id)
            else:
                template_id = Config.get_default_template_id()

            if not selected_files:
                logger.warning("No files selected, returning error.")
                return (
                    jsonify({"error": "Please select at least one context file."}),
                    400,
                )
            if not jira_desc:
                logger.warning("No Jira description provided, returning error.")
                return (
                    jsonify({"error": "Please provide a Jira description."}),
                    400,
                )

            logger.info(f"Files selected ({len(selected_files)}), generating prompt...")

            # Use the specified template or default
            if template_id:
                logger.info(f"Using template ID: {template_id}")
                final_prompt = generate_prompt(
                    template_id=template_id,
                    context_files=selected_files,
                    jira_description=jira_desc,
                    additional_instructions=instructions,
                )
            else:
                logger.info(f"Using default template file: {Config.DEFAULT_TEMPLATE}")
                final_prompt = generate_prompt(
                    template_path=Config.DEFAULT_TEMPLATE,
                    context_files=selected_files,
                    jira_description=jira_desc,
                    additional_instructions=instructions,
                )

            char_count = len(final_prompt)
            # Better token estimation - approx 4 chars per token for English text
            token_estimate = len(final_prompt) // 4

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
        except ValueError as e:
            logger.error(f"ValueError during prompt generation: {e}")
            return jsonify({"error": f"Error generating prompt: {e}"}), 500
        except Exception as e:
            logger.error(
                f"Unexpected error during prompt generation: {e}", exc_info=True
            )
            import traceback

            traceback.print_exc()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @app.route("/get_file_content", methods=["GET"])
    def get_file_content() -> Response:
        """Get content of a file with strict path validation to prevent path traversal.

        Returns:
            JSON response with file content or error message
        """
        try:
            file_path_str = request.args.get("path")

            if not file_path_str:
                return jsonify({"error": "No file path provided"}), 400

            # Security check: Validate the file path is within workspace root
            try:
                workspace_root = Config.WORKSPACE_ROOT.resolve()
                requested_path = Path(file_path_str).resolve()

                # Use os.path.commonpath for more secure validation
                if os.path.commonpath(
                    [str(workspace_root), str(requested_path)]
                ) != str(workspace_root):
                    logger.warning(
                        f"Security: Blocked access to path outside workspace: {file_path_str}"
                    )
                    return (
                        jsonify({"error": "Access denied: Path outside workspace"}),
                        403,
                    )

                if not requested_path.is_file():
                    return (
                        jsonify({"error": f"Not a file or not found: {file_path_str}"}),
                        404,
                    )
            except (ValueError, RuntimeError) as e:
                logger.warning(f"Path validation error: {e}")
                return jsonify({"error": f"Invalid path: {e}"}), 400

            content = read_file_content(requested_path)
            if not content:
                return jsonify({"error": f"Could not read file: {file_path_str}"}), 404

            return jsonify({"content": content})
        except Exception as e:
            logger.error(f"Error reading file: {e}", exc_info=True)
            return jsonify({"error": f"Error reading file: {e}"}), 500

    @app.route("/presets", methods=["GET"])
    def get_presets() -> Response:
        """Get all available presets.

        Returns:
            JSON response with all presets
        """
        try:
            # Use the cached presets rather than calling the method again
            presets = Config.REFINED_PRESETS
            return jsonify({"presets": presets})
        except Exception as e:
            logger.error(f"Error retrieving presets: {e}", exc_info=True)
            return jsonify({"error": f"Error retrieving presets: {e}"}), 500

    @app.route("/presets", methods=["POST"])
    def add_preset() -> Response:
        """Add a new preset.

        Returns:
            JSON response indicating success or error
        """
        try:
            data = request.get_json()

            if not data:
                logger.error("No JSON data received in add_preset request")
                return jsonify({"error": "No data provided or invalid JSON"}), 400

            name = data.get("name")
            files = data.get("files")

            logger.info(
                f"Adding preset: name={name}, files count={len(files) if files else 0}"
            )

            if not name:
                return jsonify({"error": "Preset name is required"}), 400
            if not files or not isinstance(files, list):
                return jsonify({"error": "Selected files list is required"}), 400

            # Validate files - ensure all are strings
            if not all(isinstance(f, str) for f in files):
                logger.warning(f"Non-string file paths detected: {files}")
                files = [str(f) for f in files]

            # Add the preset
            success = Config.add_preset(name, files)
            if success:
                # Reload presets to get the updated list
                Config.REFINED_PRESETS = Config.get_presets()
                return jsonify({"success": True, "presets": Config.REFINED_PRESETS})
            else:
                return (
                    jsonify({"error": f"Preset with name '{name}' already exists"}),
                    400,
                )
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in add_preset: {e}")
            return jsonify({"error": f"Invalid JSON format: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"Error adding preset: {e}", exc_info=True)
            # Ensure we return JSON, not HTML error page
            return jsonify({"error": f"Server error: {str(e)}"}), 500

    @app.route("/presets/<preset_name>", methods=["DELETE"])
    def delete_preset_by_name(preset_name: str) -> Response:
        """Delete a preset by name.

        Args:
            preset_name: The name of the preset to delete

        Returns:
            JSON response indicating success or error
        """
        try:
            logger.info(f"Attempting to delete preset: {preset_name}")

            # Attempt to delete the preset
            success = Config.delete_preset(preset_name)

            if success:
                # Reload presets to get the updated list
                Config.REFINED_PRESETS = Config.get_presets()
                logger.info(f"Successfully deleted preset: {preset_name}")

                # Log the number of presets after deletion
                logger.info(f"Presets after deletion: {len(Config.REFINED_PRESETS)}")

                return jsonify({"success": True, "presets": Config.REFINED_PRESETS})
            else:
                logger.warning(f"Preset '{preset_name}' not found or deletion failed")
                return jsonify({"error": f"Preset '{preset_name}' not found"}), 404
        except Exception as e:
            logger.error(f"Error deleting preset: {e}", exc_info=True)
            return jsonify({"error": f"Error deleting preset: {e}"}), 500

    @app.route("/refresh_file_tree", methods=["GET"])
    def refresh_file_tree() -> Response:
        """Rescan the file tree and return the rendered HTML."""
        logger = logging.getLogger(__name__)
        logger.info("--- Handling /refresh_file_tree GET request ---")
        try:
            # Force rescan using configured directories
            file_tree = get_file_tree(Config.SCAN_DIRS, force_rescan=True)

            # Render the entire file tree with one macro call
            macro_import = "{% from 'macros.html' import render_file_tree %}"
            rendered = render_template_string(
                f"{macro_import}{{{{ render_file_tree(file_tree, 0) }}}}",
                file_tree=file_tree,
            )
            logger.info("File tree refreshed and HTML generated.")
            return jsonify({"html": rendered})

        except Exception as e:
            logger.error(f"Error refreshing file tree: {e}", exc_info=True)
            return jsonify({"error": f"Error refreshing file tree: {e}"}), 500

    @app.route("/rescan", methods=["POST"])
    def rescan_files() -> Response:
        """Rescan the file tree to update the cache.

        Returns:
            JSON response indicating success or error
        """
        try:
            get_file_tree(Config.SCAN_DIRS, force_rescan=True)
            return jsonify(
                {"success": True, "message": "File tree rescanned successfully"}
            )
        except Exception as e:
            return jsonify({"error": f"Error rescanning files: {e}"}), 500

    @app.route("/debug/test-json", methods=["POST"])
    def test_json() -> Response:
        """Test endpoint for debugging JSON parsing issues.

        Returns:
            JSON response with the parsed data
        """
        try:
            logger.info(f"Received test-json request: {request.content_type}")
            logger.info(f"Request headers: {dict(request.headers)}")

            # Try to get JSON data
            data = request.get_json(silent=True)

            if data is None:
                # If silent=True didn't work, try to read the raw data
                raw_data = request.get_data(as_text=True)
                logger.info(f"Raw request data: {raw_data[:1000]}")
                return (
                    jsonify(
                        {
                            "error": "Failed to parse JSON",
                            "content_type": request.content_type,
                            "raw_data_sample": raw_data[:100] if raw_data else None,
                        }
                    ),
                    400,
                )

            # Successfully got JSON
            return jsonify({"success": True, "received_data": data})
        except Exception as e:
            logger.error(f"Error in test-json endpoint: {e}", exc_info=True)
            return jsonify({"error": f"Server error: {str(e)}"}), 500

    @app.route("/templates", methods=["GET"])
    def get_templates() -> Response:
        """Get all templates from the database.

        Returns:
            JSON response with all templates
        """
        try:
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()
            return jsonify({"templates": templates, "default_template_id": default_id})
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}", exc_info=True)
            return jsonify({"error": f"Error retrieving templates: {e}"}), 500

    @app.route("/templates/<int:template_id>", methods=["GET"])
    def get_template(template_id: int) -> Response:
        """Get a specific template by ID.

        Args:
            template_id: The ID of the template to retrieve

        Returns:
            JSON response with the template data
        """
        try:
            template = Config.get_template_by_id(template_id)
            if not template:
                return (
                    jsonify({"error": f"Template with ID {template_id} not found"}),
                    404,
                )
            return jsonify({"template": template})
        except Exception as e:
            logger.error(f"Error retrieving template {template_id}: {e}", exc_info=True)
            return jsonify({"error": f"Error retrieving template: {e}"}), 500

    @app.route("/templates", methods=["POST"])
    def add_template() -> Response:
        """Add a new template to the database.

        Returns:
            JSON response indicating success or error
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No data provided"}), 400

            name = data.get("name")
            content = data.get("content")
            description = data.get("description", "")
            is_default = data.get("is_default", 0)

            if not name:
                return jsonify({"error": "Template name is required"}), 400
            if not content:
                return jsonify({"error": "Template content is required"}), 400

            # Add the template
            success, result = Config.add_template(
                name, content, description, is_default
            )

            if not success:
                return jsonify({"error": result}), 400

            # Get all templates to return
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()

            return jsonify(
                {
                    "message": f"Template '{name}' added successfully with ID {result}",
                    "template_id": result,
                    "templates": templates,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error adding template: {e}", exc_info=True)
            return jsonify({"error": f"Error adding template: {e}"}), 500

    @app.route("/templates/<int:template_id>", methods=["PUT"])
    def update_template(template_id: int) -> Response:
        """Update an existing template.

        Args:
            template_id: The ID of the template to update

        Returns:
            JSON response indicating success or error
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No data provided"}), 400

            name = data.get("name")
            content = data.get("content")
            description = data.get("description", "")
            is_default = data.get("is_default", 0)

            if not name:
                return jsonify({"error": "Template name is required"}), 400
            if not content:
                return jsonify({"error": "Template content is required"}), 400

            # Update the template
            success, error = Config.update_template(
                template_id, name, content, description, is_default
            )

            if not success:
                return jsonify({"error": error}), 400 if "not found" in error else 500

            # Get all templates to return
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()

            return jsonify(
                {
                    "message": f"Template '{name}' updated successfully",
                    "templates": templates,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error updating template: {e}", exc_info=True)
            return jsonify({"error": f"Error updating template: {e}"}), 500

    @app.route("/templates/<int:template_id>", methods=["DELETE"])
    def delete_template(template_id: int) -> Response:
        """Delete a template.

        Args:
            template_id: The ID of the template to delete

        Returns:
            JSON response indicating success or error
        """
        try:
            success, error = Config.delete_template(template_id)

            if not success:
                return jsonify({"error": error}), 400 if "not found" in error else 500

            # Get all templates to return
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()

            return jsonify(
                {
                    "message": f"Template with ID {template_id} deleted successfully",
                    "templates": templates,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error deleting template: {e}", exc_info=True)
            return jsonify({"error": f"Error deleting template: {e}"}), 500

    @app.route("/templates/<int:template_id>/set-default", methods=["POST"])
    def set_default_template(template_id: int) -> Response:
        """Set a template as the default.

        Args:
            template_id: The ID of the template to set as default

        Returns:
            JSON response indicating success or error
        """
        try:
            success, error = Config.set_default_template(template_id)

            if not success:
                return jsonify({"error": error}), 400 if "not found" in error else 500

            # Get all templates to return
            templates = Config.get_templates()

            return jsonify(
                {
                    "message": f"Template with ID {template_id} set as default",
                    "templates": templates,
                    "default_template_id": template_id,
                }
            )
        except Exception as e:
            logger.error(f"Error setting default template: {e}", exc_info=True)
            return jsonify({"error": f"Error setting default template: {e}"}), 500

    @app.route("/template-manager", methods=["GET"])
    def template_manager() -> str:
        """Render the template management page.

        Returns:
            Rendered HTML template for managing templates
        """
        try:
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()

            # If no templates exist, initialize the default one
            if not templates:
                Config.initialize_default_template()
                templates = Config.get_templates()
                default_id = Config.get_default_template_id()

            return render_template(
                "template_manager.html",
                templates=templates,
                default_template_id=default_id,
            )
        except Exception as e:
            logger.error(f"Error rendering template manager: {e}", exc_info=True)
            flash(f"Error loading templates: {e}", "error")
            return render_template(
                "template_manager.html", templates=[], default_template_id=None
            )

    @app.route("/templates/reset-to-standard", methods=["POST"])
    def reset_to_standard_templates() -> Response:
        """Reset to standard templates.

        Returns:
            JSON response indicating success or error
        """
        try:
            conn = sqlite3.connect(str(Config.DB_PATH))
            cursor = conn.cursor()

            # Delete all existing templates
            cursor.execute("DELETE FROM templates")

            # Create the standard templates
            success = Config.create_standard_templates()

            if not success:
                return jsonify({"error": "Failed to create standard templates"}), 500

            # Get all templates to return
            templates = Config.get_templates()
            default_id = Config.get_default_template_id()

            return jsonify(
                {
                    "message": "Reset to standard templates successfully",
                    "templates": templates,
                    "default_template_id": default_id,
                }
            )
        except Exception as e:
            logger.error(f"Error resetting to standard templates: {e}", exc_info=True)
            return (
                jsonify({"error": f"Error resetting to standard templates: {e}"}),
                500,
            )

    return app
