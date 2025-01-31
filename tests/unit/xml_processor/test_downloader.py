"""Unit tests for CPC XML downloader."""

import pytest
import os
from unittest.mock import Mock, patch
import requests
from pathlib import Path

from src.pipeline.xml_processor.downloader import CPCDownloader
from src.pipeline.xml_processor.constants import (
    BULK_DOWNLOAD_URL,
    SCHEME_ZIP_PATTERN,
    MIN_EXPECTED_SIZE_MB
)

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path / "cpc_data"

@pytest.fixture
def downloader(temp_data_dir):
    """Create a downloader instance with temporary directory."""
    return CPCDownloader(str(temp_data_dir))

def test_init(downloader, temp_data_dir):
    """Test downloader initialization."""
    assert isinstance(downloader, CPCDownloader)
    assert str(temp_data_dir) == downloader.data_dir

@patch('requests.get')
def test_get_latest_version_success(mock_get, downloader):
    """Test successful retrieval of latest CPC version."""
    # Mock successful response with sample HTML content
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '''
    <html>
        <body>
            <a href="CPCSchemeXML202501.zip">Download CPC Scheme January 2025</a>
        </body>
    </html>
    '''
    mock_get.return_value = mock_response

    version, url = downloader.get_latest_version()
    
    assert version == "2025_01"
    assert SCHEME_ZIP_PATTERN in url
    assert url.endswith("202501.zip")
    mock_get.assert_called_once_with(BULK_DOWNLOAD_URL, timeout=mock.ANY)

@patch('requests.get')
def test_get_latest_version_failure(mock_get, downloader):
    """Test handling of failed version retrieval."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as exc_info:
        downloader.get_latest_version()
    assert "Failed to access CPC bulk page" in str(exc_info.value)

@patch('requests.get')
def test_download_scheme_success(mock_get, downloader, temp_data_dir):
    """Test successful download of CPC scheme."""
    # Create mock response with content larger than minimum size
    mock_content = b"x" * (MIN_EXPECTED_SIZE_MB * 1024 * 1024 + 1024)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [mock_content]
    mock_get.return_value = mock_response

    version = "2025_01"
    url = f"https://example.com/{SCHEME_ZIP_PATTERN}202501.zip"
    
    zip_path = downloader.download_scheme(version, url)
    
    assert os.path.exists(zip_path)
    assert os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024
    mock_get.assert_called_once_with(url, stream=True, timeout=mock.ANY)

@patch('requests.get')
def test_download_changes_success(mock_get, downloader, temp_data_dir):
    """Test successful download of CPC changes."""
    # Create mock response
    mock_content = b"x" * (MIN_EXPECTED_SIZE_MB * 1024 * 1024 + 1024)
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [mock_content]
    mock_get.return_value = mock_response

    version = "2025_01"
    zip_path = downloader.download_changes(version)
    
    assert os.path.exists(zip_path)
    assert os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024

def test_download_scheme_file_exists(downloader, temp_data_dir):
    """Test handling of already downloaded scheme file."""
    version = "2025_01"
    # Create a dummy ZIP file
    version_dir = temp_data_dir / version
    version_dir.mkdir(parents=True)
    zip_path = version_dir / f"{SCHEME_ZIP_PATTERN}202501.zip"
    
    # Create file larger than minimum size
    with open(zip_path, 'wb') as f:
        f.write(b"x" * (MIN_EXPECTED_SIZE_MB * 1024 * 1024 + 1024))
    
    result = downloader.download_scheme(version, "https://example.com/dummy.zip")
    assert str(zip_path) == result

@patch('requests.get')
def test_download_retry_on_small_file(mock_get, downloader, temp_data_dir):
    """Test retry behavior when downloaded file is too small."""
    # First attempt returns small file, second attempt returns valid file
    small_content = b"x" * 1024  # Too small
    valid_content = b"x" * (MIN_EXPECTED_SIZE_MB * 1024 * 1024 + 1024)
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.iter_content.side_effect = [
        [small_content],
        [valid_content]
    ]
    mock_get.return_value = mock_response

    version = "2025_01"
    url = f"https://example.com/{SCHEME_ZIP_PATTERN}202501.zip"
    
    zip_path = downloader.download_scheme(version, url)
    
    assert os.path.exists(zip_path)
    assert os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024
    assert mock_get.call_count == 2  # Verify retry occurred

if __name__ == '__main__':
    pytest.main([__file__])