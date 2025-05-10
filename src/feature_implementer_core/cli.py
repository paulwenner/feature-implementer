import argparse
import logging
import sys  # For sys.exit
from pathlib import Path
from typing import List, Optional, Tuple

# Use refactored config and database module
from .config import (
    Config,
    get_app_db_path,
    initialize_app_database,
    load_default_template_content,
)
from . import database
from .prompt_generator import generate_prompt
from .file_utils import save_prompt_to_file


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="feature-implementer",
        description="Generate feature implementation prompts from templates",
    )

    # Server mode arguments
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run in web server mode instead of CLI mode",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host for server mode [127.0.0.1]"
    )
    parser.add_argument(
        "--port", type=int, default=4605, help="Port for server mode [4605]"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for the web server (not recommended for production)",
    )

    # New option for forcing prompt reload
    parser.add_argument(
        "--reload-prompts",
        action="store_true",
        help="Force reload of prompt templates from the prompts directory",
    )

    # Template group (mutually exclusive options for template selection)
    template_group = parser.add_mutually_exclusive_group()
    # Allow template by path - DEPRECATED if using DB only?
    # template_group.add_argument(
    #     "--template",
    #     type=Path,
    #     help=f"Path to the prompt template file. Uses DB template by default.",
    # )
    template_group.add_argument(
        "--template-id",
        type=int,
        help="ID of the template to use from the database (defaults to the DB default).",
    )
    template_group.add_argument(
        "--list-templates",
        action="store_true",
        help="List all available templates from the database and exit.",
    )

    # Template management options
    template_mgmt_group = parser.add_argument_group("Template Management (Database)")
    template_mgmt_group.add_argument(
        "--create-template",
        metavar="NAME",
        help="Create a new template with the given name.",
    )
    template_mgmt_group.add_argument(
        "--template-content",
        metavar="FILE",
        type=Path,
        help="Path to a file containing the template content (required for --create-template).",
    )
    template_mgmt_group.add_argument(
        "--template-description",
        metavar="DESC",
        default="",
        help="Description for the new template.",
    )
    template_mgmt_group.add_argument(
        "--set-default",
        metavar="ID",
        type=int,
        help="Set the template with the given ID as the default.",
    )
    template_mgmt_group.add_argument(
        "--delete-template",
        metavar="ID",
        type=int,
        help="Delete the template with the given ID.",
    )
    template_mgmt_group.add_argument(
        "--reset-templates",
        action="store_true",
        help="Reset templates to the standard set (DELETES ALL existing templates).",
    )

    # Content file options
    parser.add_argument(
        "--context-files",
        type=Path,
        nargs="*",
        default=[],
        help="Paths to files to include as code context.",
    )
    # --always-include seems redundant if presets are available?
    # parser.add_argument(
    #     "--always-include",
    #     type=Path,
    #     nargs="*",
    #     default=[],
    #     help="Paths to files to *always* include as code context (use presets instead?).",
    # )
    parser.add_argument(
        "--jira",
        type=str,
        default="",
        help="Jira ticket description (or path to a file containing it).",
    )
    parser.add_argument(
        "--instructions",
        type=str,
        default="",
        help="Additional implementation instructions (or path to a file containing them).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,  # Default handled later based on Config
        help=f"Path to save the generated prompt file. Defaults to ./outputs/implementation_prompt.md",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=None,
        help=f"Path to use as the working directory instead of the current one. Files, database and outputs will be relative to this location.",
    )
    parser.add_argument(
        "--prompts-dir",
        type=str,
        default=None,
        help=f"Path to a directory containing additional prompt files (.md). Defaults to ./prompts/ within the working directory.",
    )
    return parser.parse_args()


def handle_template_operations(
    args: argparse.Namespace, db_path: Path, logger: logging.Logger
) -> bool:
    """Handle template operations based on CLI args. Returns True if an op was performed."""
    operation_performed = False

    # List templates
    if args.list_templates:
        operation_performed = True
        templates = database.get_templates(db_path)
        if not templates:
            logger.info("No templates found in the database.")
            return True  # Performed op, exit

        default_id = database.get_default_template_id(db_path)
        logger.info(f"--- Available Templates ({len(templates)}) ---")
        for template in templates:
            is_default = " (DEFAULT)" if template["id"] == default_id else ""
            desc = template.get("description") or "No description"
            logger.info(
                f"  ID: {template['id']:<4} Name: {template['name']}{is_default}"
            )
            logger.info(f"     Desc: {desc}")
            logger.info("-" * 20)
        return True  # Performed op, exit

    # Set default template
    if args.set_default:
        operation_performed = True
        template_id = args.set_default
        success, error = database.set_default_template(db_path, template_id)
        if success:
            logger.info(f"Template ID {template_id} successfully set as default.")
        else:
            logger.error(f"Failed to set default template ID {template_id}: {error}")
            # sys.exit(1) # Exit with error code?
        return True  # Performed op, exit

    # Delete template
    if args.delete_template:
        operation_performed = True
        template_id = args.delete_template
        success, error = database.delete_template(db_path, template_id)
        if success:
            logger.info(f"Template ID {template_id} deleted successfully.")
        else:
            logger.error(f"Failed to delete template ID {template_id}: {error}")
            # sys.exit(1)
        return True  # Performed op, exit

    # Create template
    if args.create_template:
        operation_performed = True
        if not args.template_content:
            logger.error(
                "--template-content (path to content file) is required when using --create-template"
            )
            sys.exit(1)

        template_content_path = Path(args.template_content).resolve()
        if not template_content_path.is_file():
            logger.error(f"Template content file not found: {template_content_path}")
            sys.exit(1)

        try:
            template_content = template_content_path.read_text()
        except Exception as e:
            logger.error(
                f"Failed to read template content file '{template_content_path}': {e}",
                exc_info=True,
            )
            sys.exit(1)

        # Create the template
        success, result = database.add_template(
            db_path,
            name=args.create_template,
            content=template_content,
            description=args.template_description,
            is_default=False,  # Never set default via create flag
        )

        if success:
            new_id = result
            logger.info(
                f"Template '{args.create_template}' created successfully with ID {new_id}."
            )
        else:
            error_msg = result
            logger.error(
                f"Failed to create template '{args.create_template}': {error_msg}"
            )
            sys.exit(1)
        return True  # Performed op, exit

    # Reset templates
    if args.reset_templates:
        operation_performed = True
        logger.warning("--- RESETTING TEMPLATES --- ")
        confirm = input(
            "This will DELETE ALL existing templates. Are you sure? (y/N): "
        )
        if confirm.lower() == "y":
            logger.info("Deleting all existing templates...")
            deleted_ok = database.delete_all_templates(db_path)
            if not deleted_ok:
                logger.error("Failed to delete existing templates during reset.")
                sys.exit(1)

            logger.info("Re-initializing standard templates...")
            # Re-run the initialization logic which includes adding standard templates
            # We need to call the function from config here
            try:
                initialize_app_database()  # This function handles adding defaults
                logger.info("Standard templates re-initialized successfully.")
            except Exception as e:
                logger.error(
                    f"Failed during standard template re-initialization: {e}",
                    exc_info=True,
                )
                sys.exit(1)
        else:
            logger.info("Reset cancelled.")
        return True  # Performed op (or cancellation), exit

    return operation_performed


def main_cli() -> None:
    """Main CLI entry point for generating prompts and managing templates."""
    # Configure basic logging for CLI
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",  # Simpler format for CLI
    )
    logger = logging.getLogger("feature_implementer_cli")

    # Parse command-line arguments
    args = parse_arguments()

    # Set up the working directory if specified
    if args.working_dir:
        logger.info(f"Using custom working directory: {args.working_dir}")
        try:
            Config.set_workspace_root(args.working_dir)
        except ValueError as e:
            logger.error(f"Working directory error: {e}")
            sys.exit(1)

    # Set up the prompts directory if specified
    if args.prompts_dir:
        logger.info(f"Using custom prompts directory: {args.prompts_dir}")
        try:
            Config.set_prompts_dir(args.prompts_dir)
        except ValueError as e:
            logger.error(f"Prompts directory error: {e}")
            sys.exit(1)

    # Ensure prompts directory exists
    try:
        Config.PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Prompts directory: {Config.PROMPTS_DIR}")
    except Exception as e:
        logger.warning(f"Could not create prompts directory: {e}")

    # Get the configured DB path (after working_dir is applied)
    db_path = get_app_db_path()

    # Ensure DB initialization with the correct path
    try:
        initialize_app_database()  # This initializes the DB at the configured path
    except Exception as e:
        logger.error(f"Failed to initialize database at {db_path}: {e}")
        sys.exit(1)

    # Handle the reload-prompts option if specified
    if args.reload_prompts:
        logger.info("Force reloading prompts from prompts directory...")
        from .app import load_prompt_templates_from_dir

        load_prompt_templates_from_dir()
        logger.info(f"Completed prompt reload from {Config.PROMPTS_DIR}")
        # If this was the only operation requested, exit successfully
        if (
            not args.list_templates
            and not args.set_default
            and not args.delete_template
            and not args.create_template
            and not args.reset_templates
            and not args.generate
            and not args.server
        ):
            logger.info("Prompt reload completed successfully.")
            sys.exit(0)

    # Handle any template operations first
    template_op = handle_template_operations(args, db_path, logger)
    if template_op:
        # Template operation performed, exit early
        sys.exit(0)

    # --- Proceed with Prompt Generation ---
    logger.info("Generating prompt...")

    # Validate required args for generation
    if not args.context_files:
        logger.error("Error: --context-files are required for prompt generation.")
        sys.exit(1)
    if not args.jira:
        logger.error("Error: --jira description is required for prompt generation.")
        sys.exit(1)

    # Combine context files (removed always_include)
    all_context_files: List[Path] = [Path(f).resolve() for f in args.context_files]

    # Determine output path
    output_path: Path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        # Default to ./outputs/implementation_prompt.md
        output_path = Config.DEFAULT_OUTPUT_FILE
    # Ensure output directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create output directory {output_path.parent}: {e}")
        sys.exit(1)

    try:
        logger.info(f"Using {len(all_context_files)} context files.")

        # Determine template ID (handles default)
        template_id_to_use: Optional[int] = (
            args.template_id
        )  # Use specified ID if provided
        if template_id_to_use is None:
            template_id_to_use = database.get_default_template_id(db_path)
            if template_id_to_use:
                logger.info(f"Using default template ID: {template_id_to_use}")
            else:
                # This case should be rare if initialize_app_database worked
                logger.error(
                    "No template ID specified and no default template found in database."
                )
                sys.exit(1)
        else:
            logger.info(f"Using specified template ID: {template_id_to_use}")

        # Generate prompt using the chosen template ID
        final_prompt = generate_prompt(
            db_path=db_path,
            template_id=template_id_to_use,
            context_files=all_context_files,
            jira_description=args.jira,  # TODO: Handle reading from file if path provided
            additional_instructions=args.instructions,  # TODO: Handle reading from file if path provided
        )

        if final_prompt is None:
            logger.error(
                f"Prompt generation failed. Check logs for details (template ID: {template_id_to_use})."
            )
            sys.exit(1)

        # Save the prompt
        saved = save_prompt_to_file(final_prompt, output_path)
        if saved:
            logger.info(f"Prompt saved successfully to: {output_path}")
        else:
            logger.error(f"Failed to save prompt to file: {output_path}")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"Error: Context file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Error generating prompt: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


def run_web_app():
    """Entry point function to run the Flask web application via Gunicorn or Flask dev server."""
    import os
    import argparse
    from .app import create_app  # Assuming create_app is defined in app.py

    # Configure basic logging if not already configured
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger("feature_implementer_web")

    # --- Argument Parsing (primarily for Flask dev server) ---
    # Gunicorn typically gets config via its own args or config file
    parser = argparse.ArgumentParser(
        description="Run the Feature Implementer web server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host address (set HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 4605)),
        help="Port number (set PORT env var)",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,  # Allows --debug / --no-debug
        default=os.environ.get("FLASK_DEBUG", "false").lower() in ["true", "1", "t"],
        help="Enable Flask debug mode (set FLASK_DEBUG env var)",
    )
    # Add argument for using Gunicorn (if desired)
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run using Gunicorn (requires Gunicorn installed). Ignores --host/--port/--debug.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("WEB_CONCURRENCY", 4)),
        help="Number of Gunicorn workers (if --prod is used).",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=None,
        help="Path to use as the working directory instead of the current one. Files, database, and outputs will be relative to this location.",
    )
    parser.add_argument(
        "--prompts-dir",
        type=str,
        default=None,
        help="Path to a directory containing additional prompt files (.md). Defaults to ./prompts/ within the working directory.",
    )

    # Parse known arguments, allowing unknown arguments to pass through
    # This helps with Docker and other deployment scenarios
    args, unknown = parser.parse_known_args()

    # Set up the working directory if specified
    if args.working_dir:
        logger.info(f"Using custom working directory: {args.working_dir}")
        try:
            Config.set_workspace_root(args.working_dir)
        except ValueError as e:
            logger.error(f"Working directory error: {e}")
            sys.exit(1)

    # Set up the prompts directory if specified
    if args.prompts_dir:
        logger.info(f"Using custom prompts directory: {args.prompts_dir}")
        try:
            Config.set_prompts_dir(args.prompts_dir)
        except ValueError as e:
            logger.error(f"Prompts directory error: {e}")
            sys.exit(1)

    # Ensure prompts directory exists
    try:
        Config.PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Prompts directory: {Config.PROMPTS_DIR}")
    except Exception as e:
        logger.warning(f"Could not create prompts directory: {e}")

    # Create the Flask app instance
    # Database initialization happens inside create_app()
    app = create_app()

    if args.prod:
        # --- Run with Gunicorn ---
        logger.info("Attempting to start production server with Gunicorn...")
        try:
            from gunicorn.app.base import BaseApplication

            class StandaloneApplication(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    config = {
                        key: value
                        for key, value in self.options.items()
                        if key in self.cfg.settings and value is not None
                    }
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            options = {
                "bind": f"{args.host}:{args.port}",  # Gunicorn uses BIND env var too
                "workers": args.workers,
                "loglevel": "info",
                # Add other Gunicorn options here if needed
                # e.g., 'timeout': 120
            }
            logger.info(f"Gunicorn options: {options}")
            StandaloneApplication(app, options).run()

        except ImportError:
            logger.error("Gunicorn not installed. Cannot run in --prod mode.")
            logger.error("Install it with: pip install gunicorn")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to start Gunicorn: {e}", exc_info=True)
            sys.exit(1)
    else:
        # --- Run with Flask Development Server ---
        logger.info("Starting Flask development server...")
        host = args.host
        port = args.port
        debug_mode = args.debug
        logger.info(f"Running on http://{host}:{port} (Debug mode: {debug_mode})")
        # Turn off reloader if debugging to avoid issues?
        use_reloader = debug_mode
        try:
            app.run(host=host, port=port, debug=debug_mode, use_reloader=use_reloader)
        except Exception as e:
            logger.error(
                f"Failed to start Flask development server: {e}", exc_info=True
            )
            sys.exit(1)


if __name__ == "__main__":
    # This allows running the CLI via `python -m feature_implementer_core.cli`
    main_cli()
