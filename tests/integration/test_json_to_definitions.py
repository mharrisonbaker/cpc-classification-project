"""Integration tests for JSON to expanded definitions pipeline."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from src.pipeline.json_processor import CPCJsonConverter
from src.pipeline.batch_processor import BatchProcessor

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directory structure."""
    dirs = {
        'root': tmp_path / "cpc_project",
        'data': tmp_path / "cpc_project" / "data",
        'version': tmp_path / "cpc_project" / "data" / "2025_01",
        'processed_json': tmp_path / "cpc_project" / "data" / "2025_01" / "processed_json",
        'expanded_json': tmp_path / "cpc_project" / "data" / "2025_01" / "expanded_json",
        'logs': tmp_path / "cpc_project" / "data" / "2025_01" / "logs"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

@pytest.fixture
def sample_json_content():
    """Sample CPC JSON content."""
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
        }
    ]

@patch('ollama.chat')
def test_json_to_definitions_integration(mock_chat, test_dirs, sample_json_content):
    """Test integration between JSON processing and batch definition expansion."""
    # Mock Ollama response
    mock_chat.return_value = {
        'message': {
            'content': "Technical system for processing natural language."
        }
    }
    
    # Create sample JSON file
    json_file = test_dirs['processed_json'] / "test.json"
    with open(json_file, 'w') as f:
        json.dump(sample_json_content, f)
    
    # Initialize batch processor
    processor = BatchProcessor("2025_01", str(test_dirs['root'] / "data"))
    
    # Process JSON
    processor.process_directory(test_dirs['processed_json'])
    
    # Verify expanded definitions
    expanded_files = list(test_dirs['expanded_json'].glob("*.json"))
    assert len(expanded_files) > 0
    
    with open(expanded_files[0]) as f:
        data = json.load(f)
        assert "expanded_definition" in data[0]
        assert isinstance(data[0]["expanded_definition"], str)
        assert "expanded_definition" in data[0]["children"][0]

def test_resume_capability_integration(test_dirs, sample_json_content):
    """Test resume capability of batch processing."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = {
            'message': {
                'content': "Technical definition."
            }
        }
        
        # Create JSON file
        json_file = test_dirs['processed_json'] / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_json_content, f)
        
        processor = BatchProcessor("2025_01", str(test_dirs['root'] / "data"))
        
        # Process one symbol
        processor.save_state("G06F40/00", "completed")
        
        # Resume processing
        processor.process_directory(test_dirs['processed_json'])
        
        # Verify all symbols processed
        processed = processor.get_processed_symbols()
        assert "G06F40/00" in processed
        assert "G06F40/20" in processed
        
        # Check definitions exist
        expanded_files = list(test_dirs['expanded_json'].glob("*.json"))
        with open(expanded_files[0]) as f:
            data = json.load(f)
            assert "expanded_definition" in data[0]
            assert "expanded_definition" in data[0]["children"][0]

@patch('ollama.chat')
def test_batch_processing_error_handling(mock_chat, test_dirs, sample_json_content):
    """Test error handling in batch processing."""
    # Setup mock to fail for specific symbol
    def mock_response(messages):
        if "G06F40/20" in str(messages):
            raise Exception("API Error")
        return {'message': {'content': "Technical definition."}}
    
    mock_chat.side_effect = mock_response
    
    # Create JSON file
    json_file = test_dirs['processed_json'] / "test.json"
    with open(json_file, 'w') as f:
        json.dump(sample_json_content, f)
    
    processor = BatchProcessor("2025_01", str(test_dirs['root'] / "data"))
    processor.process_directory(test_dirs['processed_json'])
    
    # Check error handling
    failed_symbols = processor.get_failed_symbols()
    assert "G06F40/20" in failed_symbols
    assert "G06F40/00" not in failed_symbols

def test_full_pipeline_integration(test_dirs, sample_json_content):
    """Test complete pipeline from JSON to expanded definitions."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = {
            'message': {
                'content': "Technical definition for classification system."
            }
        }
        
        # Create input JSON
        json_file = test_dirs['processed_json'] / "test.json"
        with open(json_file, 'w') as f:
            json.dump(sample_json_content, f)
        
        # Initialize processor
        processor = BatchProcessor("2025_01", str(test_dirs['root'] / "data"))
        
        # Process definitions
        processor.process_directory(test_dirs['processed_json'])
        
        # Verify results
        expanded_files = list(test_dirs['expanded_json'].glob("*.json"))
        assert len(expanded_files) > 0
        
        with open(expanded_files[0]) as f:
            data = json.load(f)
            # Check structure maintained
            assert data[0]["symbol"] == "G06F40/00"
            assert isinstance(data[0]["expanded_definition"], str)
            assert len(data[0]["children"]) == 1
            # Check definitions added
            assert "expanded_definition" in data[0]
            assert "expanded_definition" in data[0]["children"][0]

if __name__ == '__main__':
    pytest.main([__file__])