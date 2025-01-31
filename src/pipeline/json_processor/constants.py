"""Constants for JSON processing."""

import os
from pathlib import Path

# Directory structure
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../"))
JSON_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "cpc_versions")

# JSON output formats
DEFAULT_INDENT = 2
DEFAULT_ENCODING = "utf-8"

# Schema validation settings
SCHEMA_VERSION = "1.0.0"
MAX_TITLE_LENGTH = 1000
MAX_DEFINITION_LENGTH = 2000

# Output file patterns
JSON_FILE_PATTERN = "*.json"
PROCESSED_DIR_NAME = "processed_json"
EXPANDED_DIR_NAME = "expanded_json"

# Processing settings
BATCH_SIZE = 1000  # Number of items to process in memory at once