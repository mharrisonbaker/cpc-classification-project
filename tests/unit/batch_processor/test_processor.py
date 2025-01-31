"""Unit tests for CPC batch processor."""

import pytest
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from src.pipeline.batch_processor.processor import BatchProcessor, ProcessingState

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    dirs = {
        'base': tmp_path / "cpc_data",
        'version': tmp_path / "cpc_data" / "2025_01",
        'input': tmp_path / "cpc_data" / "2025_01" / "processed_json",
        'output': tmp_path / "cpc_data" / "2025_01" / "expanded_json",
        'logs': tmp_path / "cpc_data" / "2025_01" / "logs"
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True)
    return dirs

@pytest.fixture
def sample_cpc_items():
    """Create sample CPC items for testing."""
    return [
        {
            "symbol": "G06F40/00",
            "title": {"main": "Natural language processing"},
            "level": "main-group",
            "children": [
                {
                    "symbol": "G06F40/20",
                    "title": {"main": "Syntax analysis"},
                    "level": "subgroup"
                }
            ]
        },
        {
            "symbol": "G06F40/30",
            "title": {"main": "Semantic analysis"},
            "level": "subgroup"
        }
    ]

@pytest.fixture
def processor(temp_dirs):
    """Create a batch processor instance."""
    return BatchProcessor("2025_01", str(temp_dirs['base']))

def test_processor_initialization(processor, temp_dirs):
    """Test batch processor initialization."""
    assert isinstance(processor, BatchProcessor)
    assert processor.version == "2025_01"
    assert processor.base_dir == Path(temp_dirs['base'])
    assert processor.state_db.exists()

def test_state_db_creation(processor):
    """Test SQLite database initialization."""
    with sqlite3.connect(processor.state_db) as conn:
        # Check tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "processed_symbols" in tables
        assert "processing_stats" in tables

def test_save_and_get_processed_symbols(processor):
    """Test saving and retrieving processed symbols."""
    # Save some processed symbols
    processor.save_state("G06F40/00", "completed")
    processor.save_state("G06F40/20", "completed")
    processor.save_state("G06F40/30", "failed", "Error message")
    
    # Get processed symbols
    processed = processor.get_processed_symbols()
    assert len(processed) == 2
    assert "G06F40/00" in processed
    assert "G06F40/20" in processed
    assert "G06F40/30" not in processed

    # Get failed symbols
    failed = processor.get_failed_symbols()
    assert len(failed) == 1
    assert "G06F40/30" in failed
    assert "Error message" in failed["G06F40/30"]

def test_process_json_file(processor, temp_dirs, sample_cpc_items):
    """Test processing of a single JSON file."""
    # Create test JSON file
    json_path = temp_dirs['input'] / "test.json"
    with open(json_path, 'w') as f:
        json.dump(sample_cpc_items, f)

    # Process file
    processor.process_json_file(json_path, set())

    # Check output file exists
    output_path = temp_dirs['output'] / "test.json"
    assert output_path.exists()

    # Verify processed content
    with open(output_path) as f:
        processed_data = json.load(f)
        assert len(processed_data) == len(sample_cpc_items)
        # Verify symbols were processed
        for item in processed_data:
            assert processor.get_processed_symbols()

def test_resume_processing(processor, temp_dirs, sample_cpc_items):
    """Test resuming processing from previous state."""
    # Mark some symbols as already processed
    processor.save_state("G06F40/00", "completed")
    
    # Create test file
    json_path = temp_dirs['input'] / "test.json"
    with open(json_path, 'w') as f:
        json.dump(sample_cpc_items, f)

    # Process file
    processor.process_json_file(json_path, processor.get_processed_symbols())

    # Verify only unprocessed symbols were handled
    processed = processor.get_processed_symbols()
    assert "G06F40/00" in processed  # Previously processed
    assert "G06F40/20" in processed  # Newly processed
    assert "G06F40/30" in processed  # Newly processed

def test_process_directory(processor, temp_dirs, sample_cpc_items):
    """Test processing of multiple files in directory."""
    # Create multiple test files
    for i in range(3):
        json_path = temp_dirs['input'] / f"test_{i}.json"
        with open(json_path, 'w') as f:
            json.dump(sample_cpc_items, f)

    # Process directory
    processor.process_directory(temp_dirs['input'])

    # Verify outputs
    assert len(list(temp_dirs['output'].glob("*.json"))) == 3
    stats = processor.get_processing_stats()
    assert stats["total_symbols"] > 0
    assert stats["completed"] > 0

def test_error_handling(processor, temp_dirs):
    """Test handling of processing errors."""
    # Create invalid JSON file
    invalid_path = temp_dirs['input'] / "invalid.json"
    with open(invalid_path, 'w') as f:
        f.write("Invalid JSON content")

    # Process should handle error gracefully
    processor.process_json_file(invalid_path, set())
    
    failed = processor.get_failed_symbols()
    assert len(failed) > 0

def test_processing_stats(processor, temp_dirs, sample_cpc_items):
    """Test generation of processing statistics."""
    # Create and process a test file
    json_path = temp_dirs['input'] / "test.json"
    with open(json_path, 'w') as f:
        json.dump(sample_cpc_items, f)

    processor.process_json_file(json_path, set())
    
    stats = processor.get_processing_stats()
    assert isinstance(stats, dict)
    assert "total_symbols" in stats
    assert "completed" in stats
    assert "failed" in stats
    assert "completion_rate" in stats
    assert 0 <= stats["completion_rate"] <= 100

def test_concurrent_processing(processor, temp_dirs, sample_cpc_items):
    """Test concurrent processing of items."""
    # Create multiple test files
    for i in range(5):
        json_path = temp_dirs['input'] / f"test_{i}.json"
        with open(json_path, 'w') as f:
            json.dump(sample_cpc_items, f)

    # Process directory (this will use ThreadPoolExecutor internally)
    processor.process_directory(temp_dirs['input'])

    # Verify all files were processed
    processed = processor.get_processed_symbols()
    assert len(processed) > 0
    
    stats = processor.get_processing_stats()
    assert stats["completed"] == stats["total_symbols"]

if __name__ == '__main__':
    pytest.main([__file__])