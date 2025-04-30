import os
import logging
from pathlib import Path


class Config:

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError(
                "SECRET_KEY environment variable must be set in production"
            )
        else:
            SECRET_KEY = os.urandom(24)
            logging.warning(
                "Using random SECRET_KEY - sessions will not persist across restarts"
            )

    # Path configuration
    WORKSPACE_ROOT = Path("/app") if os.path.exists("/app") else Path.cwd().parent
    MODULE_DIR = Path(__file__).parent
    DEFAULT_TEMPLATE = MODULE_DIR / "feature_implementation_template.md"
    DEFAULT_OUTPUT_DIR = MODULE_DIR / "outputs"
    DEFAULT_OUTPUT_FILE = DEFAULT_OUTPUT_DIR / "implementation_prompt.md"

    # File explorer configuration
    SCAN_DIRS = ["data"]
    IGNORE_PATTERNS = [
        ".git",
        ".vscode",
        "__pycache__",
        ".DS_Store",
        "node_modules",
        ".venv",
        "venv",
    ]

    # Service presets
    REFINED_PRESETS = {}
