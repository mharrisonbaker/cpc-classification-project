"""Unit tests for CPC XML downloader."""

import pytest
import os
from unittest.mock import Mock, patch, ANY as mock_ANY
from pathlib import Path

from src.pipeline.xml_processor import CPCDownloader
from src.pipeline.xml_processor.constants import (
    BULK_DOWNLOAD_URL,
    SCHEME_ZIP_PATTERN,
    MIN_EXPECTED_SIZE_MB
)

RETRY_WAIT_TIME = 0  # Speed up tests

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path / "cpc_data"

@pytest.fixture
def downloader(temp_data_dir):
    """Create a downloader instance with temporary directory."""
    return CPCDownloader(str(temp_data_dir))

@pytest.fixture
def bypass_zip_validation(monkeypatch):
    """Bypass ZIP validation for tests."""
    monkeypatch.setattr('src.pipeline.xml_processor.validator.validate_zip_file', 
                        lambda x: (True, None))

def test_init(downloader, temp_data_dir):
    """Test downloader initialization."""
    assert isinstance(downloader, CPCDownloader)
    assert str(temp_data_dir) == downloader.data_dir

@patch('requests.get')
def test_get_latest_version_failure(mock_get, downloader):
    """Test handling of failed version retrieval."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as exc_info:
        downloader.get_latest_version()
    assert "Failed to access CPC bulk page" in str(exc_info.value)

# @pytest.mark.usefixtures("bypass_zip_validation")
def test_download_scheme_success(downloader, temp_data_dir):
    version = "2025_01"
    url = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCSchemeXML202501.zip"
    
    print(f"\nTemp directory: {temp_data_dir}")
    zip_path = downloader.download_scheme(version, url)
    print(f"Downloaded to: {zip_path}")
    
    assert os.path.exists(zip_path)
    assert os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024

def test_download_changes_success(downloader, temp_data_dir):
    """Test successful download of CPC changes."""
    version = "2025_01"
    zip_path = downloader.download_changes(version)
    
    assert os.path.exists(zip_path)
    assert os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024

def test_download_scheme_file_exists(downloader, temp_data_dir):
    """Test handling of already downloaded scheme file."""
    # Create directory and file
    version = "2025_01"
    version_dir = temp_data_dir / version
    version_dir.mkdir(parents=True)
    zip_path = version_dir / f"{SCHEME_ZIP_PATTERN}202501.zip"
    
    # Create file larger than minimum size
    with open(zip_path, 'wb') as f:
        f.write(b"x" * (MIN_EXPECTED_SIZE_MB * 1024 * 1024 + 1024))
    
    # Test with real URL
    url = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCSchemeXML202501.zip"
    result = downloader.download_scheme(version, url)
    assert str(zip_path) == result

if __name__ == '__main__':
    pytest.main([__file__])