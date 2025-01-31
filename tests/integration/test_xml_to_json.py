"""Integration tests for XML to JSON conversion pipeline."""

import pytest
import json
from pathlib import Path

from src.pipeline.xml_processor import CPCExtractor
from src.pipeline.json_processor import CPCJsonConverter

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directory structure."""
    dirs = {
        'root': tmp_path / "cpc_project",
        'data': tmp_path / "cpc_project" / "data",
        'version': tmp_path / "cpc_project" / "data" / "2025_01",
        'raw_xml': tmp_path / "cpc_project" / "data" / "2025_01" / "raw_xml",
        'processed_json': tmp_path / "cpc_project" / "data" / "2025_01" / "processed_json",
        'logs': tmp_path / "cpc_project" / "data" / "2025_01" / "logs"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

@pytest.fixture
def sample_xml_content():
    """Sample CPC XML content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <classification-scheme>
        <classification-item>
            <classification-symbol>G06F40/00</classification-symbol>
            <class-title>
                <title-part>
                    <text>Natural language processing</text>
                    <CPC-specific-text>
                        <text>for machine translation</text>
                    </CPC-specific-text>
                </title-part>
            </class-title>
            <classification-item>
                <classification-symbol>G06F40/20</classification-symbol>
                <class-title>
                    <title-part>
                        <text>Syntax analysis</text>
                    </title-part>
                </class-title>
            </classification-item>
        </classification-item>
    </classification-scheme>
    '''

def test_xml_to_json_integration(test_dirs, sample_xml_content):
    """Test integration between XML processor and JSON processor."""
    # Create sample XML file
    xml_file = test_dirs['raw_xml'] / "test.xml"
    xml_file.write_text(sample_xml_content)
    
    # Initialize components
    extractor = CPCExtractor(data_dir=str(test_dirs['root'] / "data"))
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    
    # Process XML
    json_dir, _ = converter.convert_directory(str(test_dirs['raw_xml']), "2025_01")
    
    # Verify JSON output
    json_files = list(Path(json_dir).glob("*.json"))
    assert len(json_files) > 0
    
    with open(json_files[0]) as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert data[0]["symbol"] == "G06F40/00"
        assert data[0]["title"]["main"] == "Natural language processing"
        assert data[0]["title"]["cpc_specific"] == "for machine translation"
        assert len(data[0]["children"]) > 0
        assert data[0]["children"][0]["symbol"] == "G06F40/20"

def test_xml_conversion_error_handling(test_dirs):
    """Test error handling in XML to JSON conversion."""
    # Create invalid XML
    invalid_xml = test_dirs['raw_xml'] / "invalid.xml"
    invalid_xml.write_text("<invalid>XML</invalid>")
    
    # Initialize components
    extractor = CPCExtractor(data_dir=str(test_dirs['root'] / "data"))
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    
    # Process should handle error gracefully
    json_dir, stats = converter.convert_directory(str(test_dirs['raw_xml']), "2025_01")
    assert stats["validation_errors"] > 0
    
    # Check error logging
    log_files = list(test_dirs['logs'].glob("*.log"))
    assert len(log_files) > 0

def test_multiple_file_conversion(test_dirs, sample_xml_content):
    """Test conversion of multiple XML files."""
    # Create multiple XML files
    for i in range(3):
        xml_file = test_dirs['raw_xml'] / f"test_{i}.xml"
        xml_file.write_text(sample_xml_content)
    
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    json_dir, stats = converter.convert_directory(str(test_dirs['raw_xml']), "2025_01")
    
    # Verify all files converted
    json_files = list(Path(json_dir).glob("*.json"))
    assert len(json_files) == 3
    assert stats["files_processed"] == 3

if __name__ == '__main__':
    pytest.main([__file__])