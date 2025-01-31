"""End-to-end tests for the complete CPC processing pipeline."""

import pytest
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import patch, Mock

from src.pipeline.xml_processor import CPCExtractor
from src.pipeline.json_processor import CPCJsonConverter
from src.pipeline.batch_processor import BatchProcessor

def create_mock_zip(zip_path, sample_xml_content, num_files=5):
    """Create a mock CPC ZIP file with multiple XML files."""
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for i in range(num_files):
            zf.writestr(f"cpc_section_{i}.xml", sample_xml_content)

@pytest.fixture
def mock_downloader_response():
    """Mock successful download response."""
    return {
        "status_code": 200,
        "content": b"Mock ZIP content"
    }

def test_complete_pipeline(test_dirs, sample_xml_content, mock_ollama_response):
    """Test complete pipeline from download to expanded definitions."""
    # Mock downloads and API calls
    with patch('requests.get') as mock_get, \
         patch('ollama.chat') as mock_chat:
        
        # Setup mock responses
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html>CPCSchemeXML202501.zip</html>"
        mock_chat.return_value = mock_ollama_response
        
        # Create mock ZIP file
        zip_path = test_dirs['version'] / "CPCSchemeXML202501.zip"
        create_mock_zip(zip_path, sample_xml_content)
        
        # Initialize pipeline components
        extractor = CPCExtractor(data_dir=str(test_dirs['data']))
        converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
        processor = BatchProcessor("2025_01", str(test_dirs['data']))
        
        # Execute pipeline
        try:
            # 1. Extract XML
            version, stats = extractor.process_latest_version()
            assert version == "2025_01"
            assert stats["processed_items"] > 0
            
            # 2. Convert to JSON
            json_dir, conv_stats = converter.convert_directory(
                str(test_dirs['raw_xml']), 
                version
            )
            assert conv_stats["files_processed"] > 0
            assert conv_stats["validation_errors"] == 0
            
            # 3. Generate definitions
            processor.process_directory(Path(json_dir))
            proc_stats = processor.get_processing_stats()
            assert proc_stats["completed"] > 0
            assert proc_stats["failed"] == 0
            
            # Verify final output
            expanded_files = list(test_dirs['expanded_json'].glob("*.json"))
            assert len(expanded_files) > 0
            
            # Check content of expanded files
            for exp_file in expanded_files:
                with open(exp_file) as f:
                    data = json.load(f)
                    # Verify structure
                    assert isinstance(data, list)
                    for item in data:
                        verify_expanded_item(item)
                        
        except Exception as e:
            pytest.fail(f"Pipeline execution failed: {e}")

def test_pipeline_recovery(test_dirs, sample_xml_content, mock_ollama_response):
    """Test pipeline recovery from interruption."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = mock_ollama_response
        
        # Setup initial data
        xml_file = test_dirs['raw_xml'] / "test.xml"
        xml_file.write_text(sample_xml_content)
        
        # 1. Initial partial processing
        converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
        json_dir, _ = converter.convert_directory(str(test_dirs['raw_xml']), "2025_01")
        
        # 2. Start batch processing but simulate interruption
        processor = BatchProcessor("2025_01", str(test_dirs['data']))
        processor.save_state("G06F40/00", "completed")  # Mark one as done
        
        # 3. Resume processing
        new_processor = BatchProcessor("2025_01", str(test_dirs['data']))
        new_processor.process_directory(Path(json_dir))
        
        # Verify all processed
        stats = new_processor.get_processing_stats()
        assert stats["completed"] > 1  # More than just the initial one
        assert stats["failed"] == 0

def test_pipeline_error_handling(test_dirs, sample_xml_content):
    """Test pipeline error handling and logging."""
    # 1. Test XML extraction errors
    invalid_xml = test_dirs['raw_xml'] / "invalid.xml"
    invalid_xml.write_text("<invalid>XML</invalid>")
    
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    json_dir, stats = converter.convert_directory(str(test_dirs['raw_xml']), "2025_01")
    assert stats["validation_errors"] > 0
    
    # 2. Test definition generation errors
    with patch('ollama.chat') as mock_chat:
        def mock_response(messages):
            if "G06F40/20" in str(messages):
                raise Exception("API Error")
            return {'message': {'content': "Definition"}}
        
        mock_chat.side_effect = mock_response
        
        processor = BatchProcessor("2025_01", str(test_dirs['data']))
        processor.process_directory(Path(json_dir))
        
        # Verify error handling
        failed = processor.get_failed_symbols()
        assert len(failed) > 0
        
        # Check error logging
        log_files = list(test_dirs['logs'].glob("*.log"))
        assert len(log_files) > 0

def test_large_dataset_processing(test_dirs, sample_xml_content, mock_ollama_response):
    """Test pipeline with larger dataset."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = mock_ollama_response
        
        # Create multiple XML files
        for i in range(10):  # Create 10 files
            xml_file = test_dirs['raw_xml'] / f"section_{i}.xml"
            xml_file.write_text(sample_xml_content)
        
        # Process pipeline
        converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
        json_dir, conv_stats = converter.convert_directory(
            str(test_dirs['raw_xml']), 
            "2025_01"
        )
        
        processor = BatchProcessor("2025_01", str(test_dirs['data']))
        processor.process_directory(Path(json_dir))
        
        # Verify processing
        stats = processor.get_processing_stats()
        assert stats["total_symbols"] > 20  # Multiple symbols per file
        assert stats["completion_rate"] == 100.0

def verify_expanded_item(item):
    """Helper function to verify expanded CPC item structure."""
    assert "symbol" in item
    assert "title" in item
    assert isinstance(item["title"], dict)
    assert "expanded_definition" in item
    assert isinstance(item["expanded_definition"], str)
    
    if "children" in item and item["children"]:
        for child in item["children"]:
            verify_expanded_item(child)

if __name__ == '__main__':
    pytest.main([__file__])