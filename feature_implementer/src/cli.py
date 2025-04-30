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
    parser.add_argument(
        "--template",
        type=Path,
        default=Config.DEFAULT_TEMPLATE,
        help=f"Path to the prompt template file. Defaults to {Config.DEFAULT_TEMPLATE}",
    )
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


def main_cli() -> None:
    """Main CLI entry point for generating prompts."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger(__name__)

    args = parse_arguments()

    all_context_files: List[Path] = args.context_files + args.always_include

    try:
        logger.info(f"Generating prompt with {len(all_context_files)} context files")
        final_prompt = generate_prompt(
            template_path=args.template,
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
