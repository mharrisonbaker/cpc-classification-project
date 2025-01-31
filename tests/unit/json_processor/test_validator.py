"""Unit tests for CPC JSON validator."""

import pytest
import json
from pathlib import Path
from src.pipeline.json_processor.validator import CPCJsonValidator
from src.pipeline.json_processor.constants import MAX_TITLE_LENGTH, MAX_DEFINITION_LENGTH

@pytest.fixture
def validator():
    """Create a validator instance."""
    return CPCJsonValidator()

@pytest.fixture
def valid_cpc_item():
    """Create a valid CPC item."""
    return {
        "symbol": "G06F40/00",
        "title": {
            "main": "Natural language processing",
            "cpc_specific": "for machine translation",
            "additional": ["Additional info"],
            "synonyms": ["NLP"]
        },
        "level": "main-group",
        "metadata": {
            "notes": ["Important note"],
            "warnings": ["Warning message"],
            "references": [
                {
                    "text": "See also neural networks",
                    "symbol": "G06N3/00",
                    "type": "informative"
                }
            ]
        },
        "children": []
    }

def test_validator_initialization(validator):
    """Test validator initialization."""
    assert isinstance(validator, CPCJsonValidator)
    assert validator.validation_stats["total_validated"] == 0
    assert validator.validation_stats["valid"] == 0
    assert validator.validation_stats["invalid"] == 0

def test_validate_valid_item(validator, valid_cpc_item):
    """Test validation of a valid CPC item."""
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert is_valid
    assert error is None
    assert validator.validation_stats["valid"] == 1

def test_invalid_symbol_format(validator, valid_cpc_item):
    """Test validation of invalid symbol format."""
    valid_cpc_item["symbol"] = "invalid-symbol"
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert not is_valid
    assert "Schema validation error" in error
    assert validator.validation_stats["invalid"] == 1

def test_missing_required_fields(validator, valid_cpc_item):
    """Test validation of missing required fields."""
    del valid_cpc_item["level"]
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert not is_valid
    assert "Schema validation error" in error

def test_invalid_level_value(validator, valid_cpc_item):
    """Test validation of invalid level value."""
    valid_cpc_item["level"] = "invalid-level"
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert not is_valid
    assert "Schema validation error" in error

def test_title_length_validation(validator, valid_cpc_item):
    """Test validation of title length."""
    valid_cpc_item["title"]["main"] = "x" * (MAX_TITLE_LENGTH + 1)
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert not is_valid
    assert "exceeds maximum length" in error

def test_definition_length_validation(validator, valid_cpc_item):
    """Test validation of definition length."""
    valid_cpc_item["expanded_definition"] = "x" * (MAX_DEFINITION_LENGTH + 1)
    is_valid, error = validator.validate_cpc_item(valid_cpc_item)
    assert not is_valid
    assert "exceeds maximum length" in error

def test_validate_json_file(validator, valid_cpc_item, tmp_path):
    """Test validation of a JSON file."""
    # Create test JSON file
    json_path = tmp_path / "test.json"
    with open(json_path, 'w') as f:
        json.dump([valid_cpc_item], f)
    
    is_valid, error = validator.validate_json_file(str(json_path))
    assert is_valid
    assert error is None

def test_validate_invalid_json_file(validator, tmp_path):
    """Test validation of an invalid JSON file."""
    # Create invalid JSON file
    json_path = tmp_path / "invalid.json"
    with open(json_path, 'w') as f:
        f.write("Invalid JSON content")
    
    is_valid, error = validator.validate_json_file(str(json_path))
    assert not is_valid
    assert "JSON decode error" in error

def test_validate_stats(validator):
    """Test validation of processing statistics."""
    valid_stats = {
        "processed_items": 100,
        "with_notes": 50,
        "with_warnings": 20,
        "with_references": 30,
        "with_definitions": 100,
        "processing_time": 10.5,
        "timestamp": "2025-01-31T12:00:00Z"
    }
    
    is_valid, error = validator.validate_stats(valid_stats)
    assert is_valid
    assert error is None

def test_validate_version_info(validator):
    """Test validation of version information."""
    valid_version_info = {
        "version": "2025_01",
        "processed_date": "2025-01-31T12:00:00Z",
        "stats": {
            "processed_items": 100,
            "timestamp": "2025-01-31T12:00:00Z"
        },
        "source_files": ["file1.xml", "file2.xml"]
    }
    
    is_valid, error = validator.validate_version_info(valid_version_info)
    assert is_valid
    assert error is None

def test_validation_stats_tracking(validator, valid_cpc_item):
    """Test tracking of validation statistics."""
    # Validate multiple items
    validator.validate_cpc_item(valid_cpc_item)  # Valid
    validator.validate_cpc_item({"invalid": "item"})  # Invalid
    
    stats = validator.get_validation_stats()
    assert stats["total_validated"] == 2
    assert stats["valid"] == 1
    assert stats["invalid"] == 1
    assert len(stats["errors"]) == 1

def test_reset_stats(validator, valid_cpc_item):
    """Test resetting of validation statistics."""
    # First validate something
    validator.validate_cpc_item(valid_cpc_item)
    assert validator.validation_stats["total_validated"] > 0
    
    # Reset stats
    validator.reset_stats()
    assert validator.validation_stats["total_validated"] == 0
    assert validator.validation_stats["valid"] == 0
    assert validator.validation_stats["invalid"] == 0
    assert len(validator.validation_stats["errors"]) == 0

if __name__ == '__main__':
    pytest.main([__file__])