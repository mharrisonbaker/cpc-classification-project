"""Unit tests for CPC JSON converter."""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.pipeline.json_processor.converter import CPCJsonConverter
from src.pipeline.xml_processor.parser import CPCClassification, CPCTitle, CPCReference

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    dirs = {
        'input_dir': tmp_path / "input",
        'output_dir': tmp_path / "output",
        'version_dir': tmp_path / "2025_01"
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True)
    return dirs

@pytest.fixture
def sample_xml_content():
    """Sample XML content for testing."""
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

@pytest.fixture
def sample_classification():
    """Create a sample CPCClassification object."""
    return CPCClassification(
        symbol="G06F40/00",
        title=CPCTitle(
            main_text="Natural language processing",
            cpc_specific_text="for machine translation"
        ),
        level="main-group",
        notes=["Important note"],
        warnings=["Warning message"],
        references=[
            CPCReference(
                text="See also neural networks",
                symbol="G06N3/00",
                type="informative"
            )
        ],
        children=[
            CPCClassification(
                symbol="G06F40/20",
                title=CPCTitle(main_text="Syntax analysis"),
                level="subgroup"
            )
        ]
    )

@pytest.fixture
def converter(temp_dirs):
    """Create a converter instance."""
    return CPCJsonConverter(output_dir=str(temp_dirs['output_dir']))

def test_converter_initialization(converter, temp_dirs):
    """Test converter initialization."""
    assert isinstance(converter, CPCJsonConverter)
    assert str(temp_dirs['output_dir']) == converter.output_dir
    assert converter.conversion_stats["files_processed"] == 0

def test_convert_classification(converter, sample_classification):
    """Test conversion of a single classification to JSON structure."""
    json_data = converter._convert_classification(sample_classification)
    
    assert isinstance(json_data, dict)
    assert json_data["symbol"] == "G06F40/00"
    assert json_data["level"] == "main-group"
    assert json_data["title"]["main"] == "Natural language processing"
    assert json_data["title"]["cpc_specific"] == "for machine translation"
    assert len(json_data["children"]) == 1
    assert json_data["metadata"]["notes"] == ["Important note"]
    assert json_data["metadata"]["warnings"] == ["Warning message"]
    assert len(json_data["metadata"]["references"]) == 1

def test_convert_file(converter, temp_dirs, sample_xml_content):
    """Test conversion of an XML file to JSON."""
    # Create test XML file
    xml_path = temp_dirs['input_dir'] / "test.xml"
    xml_path.write_text(sample_xml_content)
    
    # Create output JSON path
    json_path = temp_dirs['output_dir'] / "test.json"
    
    # Convert file
    converter.convert_file(str(xml_path), str(json_path))
    
    # Verify JSON output
    assert json_path.exists()
    with open(json_path) as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["symbol"] == "G06F40/00"
        assert len(data[0]["children"]) == 1

def test_convert_directory(converter, temp_dirs, sample_xml_content):
    """Test conversion of a directory of XML files."""
    # Create multiple test XML files
    for i in range(3):
        xml_path = temp_dirs['input_dir'] / f"test_{i}.xml"
        xml_path.write_text(sample_xml_content)
    
    # Convert directory
    output_dir, stats = converter.convert_directory(
        str(temp_dirs['input_dir']),
        "2025_01"
    )
    
    # Verify results
    assert os.path.exists(output_dir)
    assert stats["files_processed"] == 3
    assert stats["items_converted"] > 0
    assert "validation_stats" in stats

def test_validation_error_handling(converter, temp_dirs):
    """Test handling of validation errors during conversion."""
    # Create XML with invalid content
    invalid_xml = temp_dirs['input_dir'] / "invalid.xml"
    invalid_xml.write_text('''<?xml version="1.0"?>
        <invalid>Not proper CPC XML</invalid>
    ''')
    
    json_path = temp_dirs['output_dir'] / "invalid.json"
    
    # Should handle error without raising exception
    converter.convert_file(str(invalid_xml), str(json_path))
    assert converter.conversion_stats["validation_errors"] > 0

def test_conversion_stats(converter, temp_dirs, sample_xml_content):
    """Test tracking of conversion statistics."""
    # Create and convert a test file
    xml_path = temp_dirs['input_dir'] / "test.xml"
    xml_path.write_text(sample_xml_content)
    json_path = temp_dirs['output_dir'] / "test.json"
    
    converter.convert_file(str(xml_path), str(json_path))
    stats = converter.get_conversion_stats()
    
    assert "files_processed" in stats
    assert "items_converted" in stats
    assert "validation_errors" in stats
    assert "processing_time" in stats
    assert stats["files_processed"] == 1

def test_reset_stats(converter):
    """Test resetting of conversion statistics."""
    # First update some stats
    converter.conversion_stats["files_processed"] = 5
    converter.conversion_stats["items_converted"] = 10
    
    # Reset stats
    converter.reset_stats()
    
    # Verify reset
    assert converter.conversion_stats["files_processed"] == 0
    assert converter.conversion_stats["items_converted"] == 0
    assert converter.conversion_stats["validation_errors"] == 0

if __name__ == '__main__':
    pytest.main([__file__])