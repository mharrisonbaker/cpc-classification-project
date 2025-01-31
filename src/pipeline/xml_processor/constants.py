"""Constants and configuration for CPC XML processing."""

import os

# Base directories
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "cpc_versions")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "cpc_version.json")

# URL configurations
BULK_DOWNLOAD_URL = "https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk"
BASE_URL = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/"
SCHEME_ZIP_PATTERN = "CPCSchemeXML"

# Download settings
MAX_RETRIES = 5
RETRY_WAIT_TIME = 90  # in seconds
CHUNK_SIZE = 256 * 1024  # 256 KB chunks
TIMEOUT = 600  # 10-minute timeout
MIN_EXPECTED_SIZE_MB = 2  # Minimum expected file size in MB

# File patterns
XML_FILE_PATTERN = "*.xml"
ZIP_FILE_PATTERN = "CPCSchemeXML*.zip"
CHANGES_ZIP_PATTERN = "Compilation*.zip"