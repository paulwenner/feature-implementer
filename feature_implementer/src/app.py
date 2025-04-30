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

from config import Config
from src.file_utils import get_file_tree, read_file_content
from src.prompt_generator import generate_prompt


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

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

            return render_template(
                "index.html",
                file_tree=file_tree,
                scan_dirs=Config.SCAN_DIRS,
                template_preview=template_preview,
                presets=presets,
                presets_json=presets_json,
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
            success = Config.delete_preset(preset_name)
            if success:
                # Reload presets to get the updated list
                Config.REFINED_PRESETS = Config.get_presets()
                logger.info(f"Successfully deleted preset: {preset_name}")
                return jsonify({"success": True, "presets": Config.REFINED_PRESETS})
            else:
                logger.warning(f"Failed to delete preset (not found): {preset_name}")
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

            # Construct the HTML snippet using the macro
            # We need the macro definition available here.
            # We'll reuse the logic from index.html's rendering.
            # NOTE: This requires Jinja context processors or passing the macro explicitly if not default.
            # Assuming render_template_string can access the macro via the app's env.

            html_parts = []
            # Import the macro rendering function directly within the context
            # This assumes macros.html is correctly located relative to templates folder
            macro_import_string = "{% from 'macros.html' import render_file_tree %}"

            for dir_name, dir_content in file_tree.items():
                if isinstance(
                    dir_content, dict
                ):  # Check if it's a directory structure, not an error
                    # Render the tree for this top-level directory using the macro
                    render_call = (
                        f"{{{{ render_file_tree({{'{dir_name}': dir_content}}, 0) }}}}"
                    )
                    # Use render_template_string which allows using Jinja syntax
                    rendered_part = render_template_string(
                        f"{macro_import_string}<div class='directory-section'>{render_call}</div>",
                        dir_content=dir_content,  # Pass necessary context
                    )
                    html_parts.append(rendered_part)
                elif isinstance(dir_content, dict) and "error" in dir_content:
                    html_parts.append(
                        f'<p class="error">{dir_content["error"]}</p>'
                    )  # Display error
                else:  # Handle unexpected structure or top-level files if necessary
                    logger.warning(
                        f"Unexpected structure in file tree for key: {dir_name}"
                    )
                    html_parts.append(
                        f'<p class="error">Unexpected content for {dir_name}</p>'
                    )

            final_html = "\\n".join(html_parts)
            logger.info("File tree refreshed and HTML generated.")
            return jsonify({"html": final_html})

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

    return app
