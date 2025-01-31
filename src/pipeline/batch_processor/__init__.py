"""Batch processor module for CPC definition expansion."""

from .processor import BatchProcessor, ProcessingState
from .definition_expander import CPCDefinitionExpander
from .constants import (
    BATCH_OUTPUT_DIR,
    MAX_WORKERS,
    BATCH_SIZE,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING
)

__all__ = [
    'BatchProcessor',
    'ProcessingState',
    'CPCDefinitionExpander',
    'BATCH_OUTPUT_DIR',
    'MAX_WORKERS',
    'BATCH_SIZE',
    'STATUS_COMPLETED',
    'STATUS_FAILED',
    'STATUS_PENDING',
    'STATUS_PROCESSING'
]