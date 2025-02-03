"""Constants for batch processing of CPC definitions."""

import os
from pathlib import Path

# Directory structure
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../"))
BATCH_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "batch_output")
STATE_DB_NAME = "batch_state.db"

# Processing settings
MAX_WORKERS = 4
BATCH_SIZE = 100
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds

# LLM settings
LLM_MODEL = "phi4:14b"

# Database tables
PROCESSED_TABLE = "processed_symbols"
STATS_TABLE = "processing_stats"

# Status codes
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"

# Logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# File patterns
JSON_PATTERN = "*.json"
LOG_PATTERN = "batch_process_*.log"

# Memory management
MAX_CACHE_SIZE = 1000  # items
CACHE_CLEANUP_THRESHOLD = 0.8  # 80% full