from pathlib import Path
import logging
from typing import List, Union, Optional

# Use database module and config function
# from .config import Config # No longer needed directly
from . import database
from .config import get_app_db_path  # Needed if db_path isn't passed in
from .file_utils import read_file_content


def gather_context(file_paths: List[Union[Path, str]]) -> str:
    """Gather file contents for code context.

    Args:
        file_paths: List of paths to include in the context

    Returns:
        String with all file contents formatted with start/end markers, or empty string.
    """
    logger = logging.getLogger(__name__)
    context = []
    # Ensure paths are Path objects and unique
    try:
        path_objects = [Path(p).resolve() for p in file_paths]
        unique_paths = sorted(list(set(path_objects)))
    except Exception as e:
        logger.error(f"Error resolving context file paths: {file_paths} - {e}")
        return "Error resolving context paths."

    logger.debug(f"Gathering context from {len(unique_paths)} unique files.")
    for file_path in unique_paths:
        content = read_file_content(
            file_path
        )  # Assumes read_file_content handles its errors
        if content is not None:
            try:
                # Try to get a relative path for display (from CWD)
                try:
                    display_path = file_path.relative_to(Path.cwd()).as_posix()
                except ValueError:
                    # Not relative to CWD, use absolute path
                    display_path = file_path.as_posix()

                context.append(f"--- START FILE: {display_path} ---")
                context.append(content.strip())  # Strip leading/trailing whitespace
                context.append(f"--- END FILE: {display_path} ---\n")
            except Exception as e:
                # Catch unexpected errors during string formatting/appending
                logger.warning(f"Error processing content for file {file_path}: {e}")
        else:
            # read_file_content failed (and hopefully logged the error)
            context.append(f"--- START FILE: {file_path.as_posix()} ---")
            context.append("[Error reading file content - check logs]")
            context.append(f"--- END FILE: {file_path.as_posix()} ---\n")

    return "\n".join(context)


def generate_prompt(
    db_path: Path,  # Database path is now required
    template_id: int,  # Template ID is now required
    context_files: List[Union[Path, str]] = [],
    jira_description: str = "",
    additional_instructions: str = "",
) -> Optional[str]:  # Return None on failure
    """Generate a complete implementation prompt using a template from the database.

    Args:
        db_path: Path to the SQLite database file.
        template_id: ID of the template in the database.
        context_files: List of paths to include as code context.
        jira_description: JIRA ticket description text (or path to file containing it).
        additional_instructions: Additional instructions (or path to file containing it).

    Returns:
        Complete formatted prompt string, or None if the template cannot be loaded.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Generating prompt using template ID: {template_id}")

    # --- Get Template Content ---
    template_data = database.get_template_by_id(db_path, template_id)
    if (
        not template_data
        or "content" not in template_data
        or not template_data["content"]
    ):
        logger.error(
            f"Template ID {template_id} not found in database or has no content."
        )
        return None  # Indicate failure to load template

    template_content_final = template_data["content"]
    logger.debug(
        f"Loaded template '{template_data.get('name', '?')}' (ID: {template_id})"
    )

    # --- Process Jira Description ---
    # Check if it's a path to an existing file
    jira_description_final = "N/A"
    if jira_description:
        try:
            jira_path = Path(jira_description)
            if jira_path.is_file():
                logger.debug(f"Reading Jira description from file: {jira_path}")
                jira_content = read_file_content(jira_path)
                if jira_content is not None:
                    jira_description_final = jira_content
                else:
                    logger.warning(f"Could not read Jira description file: {jira_path}")
                    jira_description_final = (
                        f"N/A (Error reading file: {jira_path.name})"
                    )
            else:
                # Not a file path, use the string directly
                jira_description_final = jira_description
        except Exception as e:
            # Handle potential errors from Path() creation if input is weird
            logger.warning(
                f"Could not interpret jira_description '{jira_description}' as path or string: {e}"
            )
            jira_description_final = jira_description  # Fallback to using as string

    # --- Process Additional Instructions ---
    # Check if it's a path to an existing file
    additional_instructions_final = "N/A"
    if additional_instructions:
        try:
            instr_path = Path(additional_instructions)
            if instr_path.is_file():
                logger.debug(f"Reading instructions from file: {instr_path}")
                instr_content = read_file_content(instr_path)
                if instr_content is not None:
                    additional_instructions_final = instr_content
                else:
                    logger.warning(f"Could not read instructions file: {instr_path}")
                    additional_instructions_final = (
                        f"N/A (Error reading file: {instr_path.name})"
                    )
            else:
                # Not a file path, use the string directly
                additional_instructions_final = additional_instructions
        except Exception as e:
            logger.warning(
                f"Could not interpret additional_instructions '{additional_instructions}' as path or string: {e}"
            )
            additional_instructions_final = (
                additional_instructions  # Fallback to using as string
            )

    # --- Gather Context ---
    relevant_code_context = gather_context(context_files)

    # --- Format Final Prompt ---
    try:
        # Use placeholders, provide "N/A" only if the processed string is empty
        final_prompt = template_content_final.format(
            relevant_code_context=(
                relevant_code_context if relevant_code_context else "N/A"
            ),
            jira_description=(
                jira_description_final if jira_description_final else "N/A"
            ),
            additional_instructions=(
                additional_instructions_final
                if additional_instructions_final
                else "N/A"
            ),
        )
    except KeyError as e:
        logger.error(
            f"Template formatting error: Placeholder {e} not found in template ID {template_id}. Available placeholders: relevant_code_context, jira_description, additional_instructions"
        )
        return f"[ERROR: Template formatting failed - Placeholder {e} missing]"
    except Exception as e:
        logger.error(
            f"Unexpected template formatting error for template ID {template_id}: {e}",
            exc_info=True,
        )
        return "[ERROR: Unexpected error formatting template]"

    logger.info(f"Prompt generation complete using template ID {template_id}.")
    return final_prompt
