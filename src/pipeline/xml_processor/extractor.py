"""CPC XML scheme extraction functionality."""

import os
import json
import zipfile
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime
from pathlib import Path

from .constants import DATA_DIR, CONFIG_PATH
from .validator import validate_extraction_directory, validate_zip_file
from .downloader import CPCDownloader
from .parser import CPCSchemeParser

logger = logging.getLogger(__name__)

class CPCExtractor:
    """Handles extraction of CPC scheme files."""
    
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.downloader = CPCDownloader(data_dir)
        self.parser = CPCSchemeParser()
        
    def process_latest_version(self) -> Tuple[str, Dict]:
        """
        Downloads and processes the latest CPC version.
        
        Returns:
            Tuple of (version, processing_stats)
        """
        # Get latest version info
        version, download_url = self.downloader.get_latest_version()
        logger.info(f"Processing CPC version {version}")
        
        # Download main scheme
        scheme_zip = self.downloader.download_scheme(version, download_url)
        
        # Extract scheme
        xml_dir = self.extract_scheme(version, scheme_zip)
        
        # Download and extract changes
        changes_zip = self.downloader.download_changes(version)
        if changes_zip:
            self.extract_changes(version, changes_zip)
        
        # Update version tracking
        self.update_version_config(version)
        
        # Return processing stats
        return version, self.parser.get_statistics()

    def extract_scheme(self, version: str, zip_path: str) -> str:
        """
        Extracts the CPC Scheme XML ZIP file into the correct directories.
        
        Args:
            version: CPC version string (YYYY_MM)
            zip_path: Path to the ZIP file
            
        Returns:
            Path to extraction directory
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
            
        # Validate zip before extraction
        is_valid, error = validate_zip_file(zip_path)
        if not is_valid:
            raise ValueError(f"Invalid ZIP file: {error}")
            
        extract_dir = os.path.join(self.data_dir, version, "raw_xml")
        logger.info(f"Extracting {zip_path} to {extract_dir}...")
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Validate extraction
        is_valid, error = validate_extraction_directory(extract_dir)
        if not is_valid:
            raise Exception(f"Extraction validation failed: {error}")
            
        logger.info(f"✅ Extraction complete for version {version}")
        return extract_dir
        
    def extract_changes(self, version: str, zip_path: str) -> str:
        """
        Extracts the CPC Compilation of Changes ZIP file.
        
        Args:
            version: CPC version string (YYYY_MM)
            zip_path: Path to the changes ZIP file
            
        Returns:
            Path to changes extraction directory
        """
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Changes ZIP not found: {zip_path}")
            
        changes_dir = os.path.join(self.data_dir, version, "changes")
        logger.info(f"Extracting changes {zip_path} → {changes_dir}")
        
        # Validate zip before extraction
        is_valid, error = validate_zip_file(zip_path)
        if not is_valid:
            raise ValueError(f"Invalid changes ZIP: {error}")
            
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(changes_dir)
            
        logger.info("✅ Changes extraction complete")
        return changes_dir
        
    def update_version_config(self, version: str):
        """Updates config/cpc_version.json with the latest CPC version."""
        config_data = {
            "latest_version": version,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processing_stats": self.parser.get_statistics()
        }
        
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        
        with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file, indent=4)
            
        logger.info(f"Updated {CONFIG_PATH} with version {version}")
        
    def get_version_info(self) -> Optional[Dict]:
        """
        Gets information about the currently processed CPC version.
        
        Returns:
            Dictionary with version information if available
        """
        if not os.path.exists(CONFIG_PATH):
            return None
            
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading version config: {e}")
            return None
            
    def clean_old_versions(self, keep_versions: int = 2):
        """
        Removes old CPC versions to free up space, keeping the specified number of recent versions.
        
        Args:
            keep_versions: Number of most recent versions to keep
        """
        if not os.path.exists(self.data_dir):
            return
            
        versions = []
        for item in os.listdir(self.data_dir):
            version_dir = os.path.join(self.data_dir, item)
            if os.path.isdir(version_dir) and len(item) == 7 and "_" in item:
                versions.append(item)
                
        # Sort versions (YYYY_MM format ensures correct sorting)
        versions.sort(reverse=True)
        
        # Remove old versions
        for version in versions[keep_versions:]:
            version_dir = os.path.join(self.data_dir, version)
            logger.info(f"Removing old version: {version}")
            try:
                import shutil
                shutil.rmtree(version_dir)
            except Exception as e:
                logger.error(f"Error removing {version}: {e}")
                
def ensure_directory_exists(filepath: str):
    """Creates directory if it doesn't exist."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)