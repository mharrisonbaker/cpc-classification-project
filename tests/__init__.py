"""Root test package for CPC processing pipeline."""

import os
from pathlib import Path

# Root directory of the project
PROJECT_ROOT = Path(__file__).parent.parent

# Test data directories
TEST_DATA_DIR = Path(__file__).parent / "test_data"
XML_SAMPLES_DIR = TEST_DATA_DIR / "xml_samples"
JSON_SAMPLES_DIR = TEST_DATA_DIR / "json_samples"
EXPECTED_OUTPUTS_DIR = TEST_DATA_DIR / "expected_outputs"

def get_test_file_path(filename: str, category: str = "xml_samples") -> Path:
    """Get path to a test file."""
    category_dir = TEST_DATA_DIR / category
    return category_dir / filename

def ensure_test_dir(path: Path) -> Path:
    """Ensure a test directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path

# Create necessary test directories
for dir_path in [XML_SAMPLES_DIR, JSON_SAMPLES_DIR, EXPECTED_OUTPUTS_DIR]:
    ensure_test_dir(dir_path)