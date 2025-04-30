import argparse
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from config import Config
from src.prompt_generator import generate_prompt
from src.file_utils import save_prompt_to_file


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate a feature implementation prompt for an LLM (CLI tool)."
    )
    # Template group (mutually exclusive options for template selection)
    template_group = parser.add_mutually_exclusive_group()
    template_group.add_argument(
        "--template",
        type=Path,
        help=f"Path to the prompt template file. Defaults to the default template.",
    )
    template_group.add_argument(
        "--template-id",
        type=int,
        help="ID of the template to use from the database.",
    )
    template_group.add_argument(
        "--list-templates",
        action="store_true",
        help="List all available templates from the database and exit.",
    )

    # Template management options
    template_mgmt_group = parser.add_argument_group("Template Management")
    template_mgmt_group.add_argument(
        "--create-template",
        metavar="NAME",
        help="Create a new template with the given name.",
    )
    template_mgmt_group.add_argument(
        "--template-content",
        metavar="FILE",
        type=Path,
        help="Path to a file containing the template content for creation.",
    )
    template_mgmt_group.add_argument(
        "--template-description",
        metavar="DESC",
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

    # Content file options
    parser.add_argument(
        "--context-files",
        type=Path,
        nargs="*",
        default=[],
        help="Paths to files to include as code context.",
    )
    parser.add_argument(
        "--always-include",
        type=Path,
        nargs="*",
        default=[],
        help="Paths to files to *always* include as code context (e.g., settings.py).",
    )
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
        default=Config.DEFAULT_OUTPUT_FILE,
        help=f"Path to save the generated prompt file. Defaults to {Config.DEFAULT_OUTPUT_FILE}",
    )
    return parser.parse_args()


def handle_template_operations(
    args: argparse.Namespace, logger: logging.Logger
) -> bool:
    """Handle template operations based on command line arguments.

    Args:
        args: Command line arguments
        logger: Logger instance

    Returns:
        True if a template operation was performed and we should exit, False otherwise
    """
    # List templates
    if args.list_templates:
        templates = Config.get_templates()
        if not templates:
            logger.info("No templates found in the database")
            return True

        default_id = Config.get_default_template_id()
        logger.info(f"Available templates ({len(templates)}):")
        for template in templates:
            is_default = "(DEFAULT)" if template["id"] == default_id else ""
            logger.info(f"  {template['id']}: {template['name']} {is_default}")
            if template.get("description"):
                logger.info(f"     Description: {template['description']}")
        return True

    # Set default template
    if args.set_default:
        success, error = Config.set_default_template(args.set_default)
        if success:
            logger.info(f"Template ID {args.set_default} set as default")
        else:
            logger.error(f"Failed to set default template: {error}")
        return True

    # Delete template
    if args.delete_template:
        success, error = Config.delete_template(args.delete_template)
        if success:
            logger.info(f"Template ID {args.delete_template} deleted")
        else:
            logger.error(f"Failed to delete template: {error}")
        return True

    # Create template
    if args.create_template:
        if not args.template_content:
            logger.error("--template-content is required when creating a template")
            return True

        # Read template content from file
        template_content_path = Path(args.template_content)
        if not template_content_path.exists():
            logger.error(f"Template content file not found: {template_content_path}")
            return True

        try:
            template_content = template_content_path.read_text()
        except Exception as e:
            logger.error(f"Failed to read template content file: {e}")
            return True

        # Create the template
        description = args.template_description or ""
        success, result = Config.add_template(
            args.create_template, template_content, description
        )

        if success:
            logger.info(f"Template '{args.create_template}' created with ID {result}")
        else:
            logger.error(f"Failed to create template: {result}")
        return True

    return False


def main_cli() -> None:
    """Main CLI entry point for generating prompts."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    args = parse_arguments()

    # Initialize database if needed
    Config._init_preset_db()
    Config.initialize_default_template()

    # Handle template operations (if any)
    if handle_template_operations(args, logger):
        return

    all_context_files: List[Path] = args.context_files + args.always_include

    try:
        logger.info(f"Generating prompt with {len(all_context_files)} context files")

        # Determine which template to use
        template_path = None
        template_id = None

        if args.template:
            template_path = args.template
            logger.info(f"Using template file: {template_path}")
        elif args.template_id:
            template_id = args.template_id
            logger.info(f"Using template ID: {template_id}")
        else:
            default_template_id = Config.get_default_template_id()
            if default_template_id:
                template_id = default_template_id
                logger.info(f"Using default template ID: {template_id}")
            else:
                logger.info(f"Using default template file: {Config.DEFAULT_TEMPLATE}")

        # Generate prompt
        final_prompt = generate_prompt(
            template_path=template_path,
            template_id=template_id,
            context_files=all_context_files,
            jira_description=args.jira,
            additional_instructions=args.instructions,
        )

        saved = save_prompt_to_file(final_prompt, args.output)
        if saved:
            logger.info(f"Prompt saved to {args.output}")
        else:
            logger.error("Failed to save prompt to file")
    except ValueError as e:
        logger.error(f"Error generating prompt: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main_cli()
