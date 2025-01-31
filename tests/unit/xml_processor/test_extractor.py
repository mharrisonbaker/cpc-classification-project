"""Unit tests for CPC XML extractor."""

import pytest
import os
import zipfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipeline.xml_processor.extractor import CPCExtractor
from src.pipeline.xml_processor.constants import MIN_EXPECTED_SIZE_MB

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    return {
        'data_dir': tmp_path / "data",
        'version_dir': tmp_path / "data" / "2025_01",
        'raw_xml': tmp_path / "data" / "2025_01" / "raw_xml",
        'changes': tmp_path / "data" / "2025_01" / "changes"
    }

@pytest.fixture
def setup_dirs(temp_dirs):
    """Set up test directories."""
    for dir_path in temp_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    return temp_dirs

@pytest.fixture
def mock_zip_file(temp_dirs):
    """Create a mock ZIP file with test content."""
    zip_path = temp_dirs['version_dir'] / "CPCSchemeXML202501.zip"
    
    # Create a ZIP file with some test XML content
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("test.xml", '''<?xml version="1.0"?>
            <classification-scheme>
                <classification-item>
                    <classification-symbol>A01B1/00</classification-symbol>
                </classification-item>
            </classification-scheme>
        ''')
    
    # Make file larger than minimum size
    with open(zip_path, 'ab') as f:
        f.write(b'0' * (MIN_EXPECTED_SIZE_MB * 1024 * 1024))
    
    return zip_path

@pytest.fixture
def extractor(temp_dirs):
    """Create an extractor instance with mocked dependencies."""
    return CPCExtractor(data_dir=str(temp_dirs['data_dir']))

def test_extractor_initialization(extractor, temp_dirs):
    """Test extractor initialization."""
    assert isinstance(extractor, CPCExtractor)
    assert str(temp_dirs['data_dir']) == extractor.data_dir
    assert hasattr(extractor, 'downloader')
    assert hasattr(extractor, 'parser')

def test_extract_scheme_success(extractor, setup_dirs, mock_zip_file):
    """Test successful extraction of CPC scheme."""
    version = "2025_01"
    extract_dir = extractor.extract_scheme(version, mock_zip_file)
    
    assert os.path.exists(extract_dir)
    assert os.path.exists(os.path.join(extract_dir, "test.xml"))
    
    # Verify XML file is readable
    xml_path = os.path.join(extract_dir, "test.xml")
    with open(xml_path, 'r') as f:
        content = f.read()
        assert "classification-scheme" in content
        assert "A01B1/00" in content

def test_extract_scheme_missing_file(extractor, setup_dirs):
    """Test handling of missing ZIP file."""
    version = "2025_01"
    non_existent_zip = os.path.join(setup_dirs['version_dir'], "nonexistent.zip")
    
    with pytest.raises(FileNotFoundError) as exc_info:
        extractor.extract_scheme(version, non_existent_zip)
    assert "ZIP file not found" in str(exc_info.value)

@patch('src.pipeline.xml_processor.validator.validate_zip_file')
def test_extract_scheme_invalid_zip(mock_validate, extractor, setup_dirs, mock_zip_file):
    """Test handling of invalid ZIP file."""
    mock_validate.return_value = (False, "Invalid ZIP file")
    
    with pytest.raises(ValueError) as exc_info:
        extractor.extract_scheme("2025_01", mock_zip_file)
    assert "Invalid ZIP file" in str(exc_info.value)

def test_extract_changes_success(extractor, setup_dirs):
    """Test successful extraction of changes file."""
    version = "2025_01"
    changes_zip = setup_dirs['version_dir'] / "changes" / f"Compilation202501.zip"
    
    # Create test changes ZIP
    with zipfile.ZipFile(changes_zip, 'w') as zf:
        zf.writestr("changes.txt", "Test changes content")
    
    # Make file larger than minimum size
    with open(changes_zip, 'ab') as f:
        f.write(b'0' * (MIN_EXPECTED_SIZE_MB * 1024 * 1024))
    
    changes_dir = extractor.extract_changes(version, str(changes_zip))
    
    assert os.path.exists(changes_dir)
    assert os.path.exists(os.path.join(changes_dir, "changes.txt"))

@patch('src.pipeline.xml_processor.downloader.CPCDownloader')
def test_process_latest_version(mock_downloader, extractor, setup_dirs, mock_zip_file):
    """Test processing of latest version."""
    # Mock downloader responses
    mock_downloader.return_value.get_latest_version.return_value = (
        "2025_01",
        "http://example.com/CPCSchemeXML202501.zip"
    )
    mock_downloader.return_value.download_scheme.return_value = str(mock_zip_file)
    mock_downloader.return_value.download_changes.return_value = None
    
    # Process latest version
    version, stats = extractor.process_latest_version()
    
    assert version == "2025_01"
    assert isinstance(stats, dict)
    assert os.path.exists(setup_dirs['raw_xml'])

def test_update_version_config(extractor, setup_dirs):
    """Test updating of version configuration."""
    version = "2025_01"
    extractor.update_version_config(version)
    
    config_path = os.path.join(os.path.dirname(extractor.data_dir), "config", "cpc_version.json")
    assert os.path.exists(config_path)
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        assert config["latest_version"] == version
        assert "last_updated" in config
        assert "processing_stats" in config

def test_get_version_info(extractor, setup_dirs):
    """Test retrieval of version information."""
    # First update config
    version = "2025_01"
    extractor.update_version_config(version)
    
    # Then get info
    info = extractor.get_version_info()
    assert info is not None
    assert info["latest_version"] == version
    assert "last_updated" in info

def test_clean_old_versions(extractor, setup_dirs):
    """Test cleanup of old versions."""
    # Create multiple version directories
    versions = ["2024_01", "2024_07", "2025_01"]
    for version in versions:
        (setup_dirs['data_dir'] / version).mkdir(exist_ok=True)
    
    # Keep only the latest 2 versions
    extractor.clean_old_versions(keep_versions=2)
    
    # Check that oldest version was removed
    assert not os.path.exists(setup_dirs['data_dir'] / "2024_01")
    assert os.path.exists(setup_dirs['data_dir'] / "2024_07")
    assert os.path.exists(setup_dirs['data_dir'] / "2025_01")

if __name__ == '__main__':
    pytest.main([__file__])