from pathlib import Path
import time
import logging
from typing import Dict, Any, List, Union, Tuple, Optional

from .config import Config


# Define a better caching structure with TTL and lock mechanism
class FileTreeCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Optional[Dict[str, Any]] = None
        self.timestamp: float = 0
        self.scanning: bool = False
        self.ttl_seconds: int = ttl_seconds
        self.logger = logging.getLogger(__name__)

    def get(self, force_rescan: bool = False) -> Optional[Dict[str, Any]]:
        """Get the cached file tree if valid."""
        if force_rescan:
            return None

        current_time = time.time()
        if self.cache and (current_time - self.timestamp) < self.ttl_seconds:
            return self.cache
        return None

    def set(self, tree: Dict[str, Any]) -> None:
        """Update the cache with new data."""
        self.cache = tree
        self.timestamp = time.time()

    def is_scanning(self) -> bool:
        """Check if a scan is in progress."""
        return self.scanning

    def set_scanning(self, is_scanning: bool) -> None:
        """Update scanning flag."""
        self.scanning = is_scanning


# Initialize the cache
file_tree_cache = FileTreeCache()


def read_file_content(file_path: Union[Path, str]) -> str:
    """Read content from a file safely.

    Args:
        file_path: Path to the file to read

    Returns:
        String content of the file or empty string on error
    """
    logger = logging.getLogger(__name__)
    try:
        path = Path(file_path) if not isinstance(file_path, Path) else file_path
        return path.read_text()
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return ""
    except Exception as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return ""


def get_file_tree(start_dirs: List[str], force_rescan: bool = False) -> Dict[str, Any]:
    """Get a hierarchical tree of files in the specified directories.

    Args:
        start_dirs: List of directory names to scan
        force_rescan: If True, ignore cache and rebuild the file tree

    Returns:
        Dictionary representing the file tree structure
    """
    global file_tree_cache
    logger = logging.getLogger(__name__)

    # Check cache first unless force_rescan
    cached_tree = file_tree_cache.get(force_rescan)
    if cached_tree is not None:
        return cached_tree

    # Prevent concurrent scans
    if file_tree_cache.is_scanning():
        logger.info(
            "File scan already in progress, returning cached data or empty dict"
        )
        return file_tree_cache.cache or {}

    try:
        file_tree_cache.set_scanning(True)

        logger.info("Scanning file tree...")
        tree = {}
        start_time = time.time()

        for start_dir_name in start_dirs:
            start_path = Config.WORKSPACE_ROOT / start_dir_name
            if not start_path.is_dir():
                tree[start_dir_name] = {"error": f"Directory not found: {start_path}"}
                continue

            dir_tree = {}
            try:
                for item in sorted(start_path.rglob("*")):
                    # Improved ignore pattern check - match exact parts only
                    if item.name in Config.IGNORE_PATTERNS:
                        continue
                    if any(part in Config.IGNORE_PATTERNS for part in item.parts):
                        continue

                    if item.is_file():
                        relative_path = item.relative_to(start_path)
                        current_level = dir_tree
                        parts = list(relative_path.parts)

                        for i, part in enumerate(parts):
                            if i == len(parts) - 1:
                                current_level[part] = (
                                    Config.WORKSPACE_ROOT
                                    / start_dir_name
                                    / relative_path
                                ).as_posix()
                            else:
                                if part not in current_level:
                                    current_level[part] = {}
                                if isinstance(current_level[part], str):
                                    logger.warning(
                                        f"Path conflict for {part} in {start_dir_name}"
                                    )
                                    continue
                                current_level = current_level[part]
            except Exception as e:
                logger.error(
                    f"Error scanning directory {start_path}: {e}", exc_info=True
                )
                tree[start_dir_name] = {"error": f"Error scanning: {e}"}
                continue

            tree[start_dir_name] = dir_tree

        end_time = time.time()
        logger.info(f"File tree scan completed in {end_time - start_time:.2f} seconds.")

        # Update cache with new tree
        file_tree_cache.set(tree)
        return tree
    finally:
        file_tree_cache.set_scanning(False)


def save_prompt_to_file(prompt_content: str, output_path: Union[Path, str]) -> bool:
    """Save the generated prompt to a file.

    Args:
        prompt_content: Content to write to file
        output_path: Path where to save the file

    Returns:
        True if file was saved successfully, False otherwise
    """
    logger = logging.getLogger(__name__)
    output_path = Path(output_path)
    output_dir = output_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prompt_content)
        logger.info(f"Successfully generated prompt at: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error: Could not write output file {output_path}: {e}")
        return False
