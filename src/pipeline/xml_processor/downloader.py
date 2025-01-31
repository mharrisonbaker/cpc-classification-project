"""CPC XML scheme download functionality."""

import os
import time
import requests
import logging
from typing import Tuple, Optional
from pathlib import Path

from .constants import (
    BULK_DOWNLOAD_URL,
    BASE_URL,
    SCHEME_ZIP_PATTERN,
    MAX_RETRIES,
    RETRY_WAIT_TIME,
    CHUNK_SIZE,
    TIMEOUT
)
from .validator import validate_zip_file

logger = logging.getLogger(__name__)

class CPCDownloader:
    """Handles downloading of CPC scheme files."""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
    def get_latest_version(self) -> Tuple[str, str]:
        """
        Fetch the latest CPC version by scraping the CPC Bulk Download page.
        
        Returns:
            Tuple of (version_string, download_url)
        """
        logger.info("Fetching latest CPC version information...")
        
        response = requests.get(BULK_DOWNLOAD_URL, timeout=TIMEOUT)
        if response.status_code != 200:
            raise Exception(f"Failed to access CPC bulk page. HTTP Status: {response.status_code}")
        
        # Find the version number in the page content
        version_str = None
        for line in response.text.splitlines():
            if SCHEME_ZIP_PATTERN in line and "zip" in line:
                version_str = line.split(SCHEME_ZIP_PATTERN)[1][:6]  # Extract YYYYMM
                break
                
        if not version_str:
            raise Exception("Could not determine the latest CPC version.")
            
        latest_version = f"{version_str[:4]}_{version_str[4:]}"
        download_url = f"{BASE_URL}{SCHEME_ZIP_PATTERN}{version_str}.zip"
        
        logger.info(f"Latest CPC Version: {latest_version}")
        logger.info(f"Download URL: {download_url}")
        
        return latest_version, download_url
        
    def download_scheme(self, version: str, url: str) -> Optional[str]:
        """
        Downloads the CPC Scheme ZIP file with retry and resume support.
        
        Args:
            version: CPC version string (YYYY_MM)
            url: Download URL for the ZIP file
            
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        target_dir = os.path.join(self.data_dir, version)
        os.makedirs(target_dir, exist_ok=True)
        
        zip_path = os.path.join(target_dir, f"{SCHEME_ZIP_PATTERN}{version.replace('_', '')}.zip")
        
        # Check if already downloaded and valid
        is_valid, error = validate_zip_file(zip_path)
        if is_valid:
            logger.info(f"✅ ZIP file already exists and is valid: {zip_path}")
            return zip_path
            
        logger.info(f"Downloading: {url} → {zip_path}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, stream=True, timeout=TIMEOUT)
                response.raise_for_status()
                
                # Download in chunks with resume support
                with open(zip_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            file.write(chunk)
                            
                # Validate downloaded file
                is_valid, error = validate_zip_file(zip_path)
                if not is_valid:
                    logger.warning(f"Downloaded file invalid: {error}")
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    time.sleep(RETRY_WAIT_TIME)
                    continue
                    
                logger.info(f"✅ Download complete: {zip_path}")
                return zip_path
                
            except Exception as e:
                logger.error(f"Download failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_WAIT_TIME)
                    continue
                    
        raise Exception(f"Failed to download CPC Scheme ZIP after {MAX_RETRIES} attempts.")
        
    def download_changes(self, version: str) -> Optional[str]:
        """
        Downloads the CPC Compilation of Changes ZIP file.
        
        Args:
            version: CPC version string (YYYY_MM)
            
        Returns:
            Path to downloaded file if successful, None otherwise
        """
        changes_dir = os.path.join(self.data_dir, version, "changes")
        os.makedirs(changes_dir, exist_ok=True)
        
        zip_filename = f"Compilation{version.replace('_', '')}.zip"
        zip_path = os.path.join(changes_dir, zip_filename)
        
        # Check if already downloaded and valid
        is_valid, error = validate_zip_file(zip_path)
        if is_valid:
            logger.info(f"✅ Changes ZIP file already exists and is valid: {zip_path}")
            return zip_path
            
        download_url = f"{BASE_URL}{zip_filename}"
        logger.info(f"Downloading changes: {download_url} → {zip_path}")
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(download_url, stream=True, timeout=TIMEOUT)
                response.raise_for_status()
                
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            
                # Validate downloaded file
                is_valid, error = validate_zip_file(zip_path)
                if is_valid:
                    logger.info(f"✅ Changes download complete: {zip_path}")
                    return zip_path
                    
                logger.warning(f"Downloaded changes file invalid: {error}")
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    
            except Exception as e:
                logger.error(f"Changes download failed: {e}")
                
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_WAIT_TIME)
                
        raise Exception(f"Failed to download changes ZIP after {MAX_RETRIES} attempts.")