from pathlib import Path
import logging
from typing import List, Union, Optional

from .config import Config
from .file_utils import read_file_content


def gather_context(file_paths: List[Union[Path, str]]) -> str:
    """Gather file contents for code context.

    Args:
        file_paths: List of paths to include in the context

    Returns:
        String with all file contents formatted with start/end markers
    """
    logger = logging.getLogger(__name__)
    context = []
    # Convert all paths to Path objects
    path_objects = [Path(p) if not isinstance(p, Path) else p for p in file_paths]
    unique_paths = sorted(list(set(path_objects)))

    for file_path in unique_paths:
        content = read_file_content(file_path)
        if content:
            try:
                # Try to get a relative path for display
                if Path.cwd() in file_path.parents:
                    display_path = file_path.relative_to(Path.cwd()).as_posix()
                else:
                    display_path = file_path.as_posix()

                context.append(f"--- START FILE: {display_path} ---")
                context.append(content.strip())
                context.append(f"--- END FILE: {display_path} ---\n")
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")

    return "\n".join(context)


def generate_prompt(
    template_path: Optional[Union[Path, str]] = None,
    template_id: Optional[int] = None,
    template_content: Optional[str] = None,
    context_files: List[Union[Path, str]] = [],
    jira_description: str = "",
    additional_instructions: str = "",
) -> str:
    """Generate a complete implementation prompt with file context.

    Args:
        template_path: Path to the template file (optional)
        template_id: ID of the template in the database (optional)
        template_content: Direct template content string (optional)
        context_files: List of paths to include as code context
        jira_description: JIRA ticket description text
        additional_instructions: Additional implementation instructions

    Returns:
        Complete formatted prompt string

    Raises:
        ValueError: If template could not be loaded
    """
    logger = logging.getLogger(__name__)

    # Determine template content source (content string, db ID, or file path)
    template_content_final = None

    # If direct content is provided, use it
    if template_content:
        template_content_final = template_content
    # Otherwise if an ID is provided, fetch from database
    elif template_id:
        template_data = Config.get_template_by_id(template_id)
        if template_data and "content" in template_data:
            template_content_final = template_data["content"]
        else:
            logger.error(f"Template with ID {template_id} not found or has no content")
    # Otherwise use the template file path (default if none provided)
    else:
        template_path_obj = Config.DEFAULT_TEMPLATE
        if template_path:
            template_path_obj = (
                Path(template_path)
                if not isinstance(template_path, Path)
                else template_path
            )

        logger.info(f"Using template file: {template_path_obj}")
        template_content_final = read_file_content(template_path_obj)

    # Validate that we have template content
    if not template_content_final:
        logger.error("Template could not be loaded")
        raise ValueError("Template could not be loaded")

    # Process Jira description if it's a file path
    jira_description_final = ""
    if jira_description:
        jira_path = Path(jira_description)
        if jira_path.is_file():
            jira_description_content = read_file_content(jira_path)
            if not jira_description_content:
                logger.warning(
                    f"Could not read Jira description file: {jira_description}"
                )
                jira_description_final = "N/A (Error reading file)"
            else:
                jira_description_final = jira_description_content
        else:
            jira_description_final = jira_description
    else:
        jira_description_final = jira_description

    # Process additional instructions if it's a file path
    additional_instructions_final = ""
    if additional_instructions:
        instr_path = Path(additional_instructions)
        if instr_path.is_file():
            additional_instructions_content = read_file_content(instr_path)
            if not additional_instructions_content:
                logger.warning(
                    f"Could not read instructions file: {additional_instructions}"
                )
                additional_instructions_final = "N/A (Error reading file)"
            else:
                additional_instructions_final = additional_instructions_content
        else:
            additional_instructions_final = additional_instructions
    else:
        additional_instructions_final = additional_instructions

    # Gather context from specified files
    relevant_code_context = gather_context(context_files)

    # Use placeholders if any input is effectively empty
    final_prompt = template_content_final.format(
        relevant_code_context=relevant_code_context if relevant_code_context else "N/A",
        jira_description=jira_description_final if jira_description_final else "N/A",
        additional_instructions=(
            additional_instructions_final if additional_instructions_final else "N/A"
        ),
    )

    return final_prompt
