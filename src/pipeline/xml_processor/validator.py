"""Validation utilities for CPC XML files and downloads."""

import os
import zipfile
import logging
from typing import Tuple, Optional
import xml.etree.ElementTree as ET

from .constants import MIN_EXPECTED_SIZE_MB

logger = logging.getLogger(__name__)

def validate_zip_file(zip_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a ZIP file's integrity and size.
    
    Args:
        zip_path: Path to the ZIP file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(zip_path):
        return False, f"ZIP file not found: {zip_path}"
        
    # Check file size
    file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    if file_size_mb < MIN_EXPECTED_SIZE_MB:
        return False, f"File too small: {file_size_mb:.2f}MB < {MIN_EXPECTED_SIZE_MB}MB"
    
    # Test ZIP integrity
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            result = zip_ref.testzip()
            if result is not None:
                return False, f"Corrupt file in ZIP: {result}"
    except zipfile.BadZipFile as e:
        return False, f"Invalid ZIP file: {e}"
    except Exception as e:
        return False, f"Error validating ZIP: {e}"
    
    return True, None

def validate_xml_file(xml_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validates an XML file for well-formedness and basic CPC schema requirements.
    
    Args:
        xml_path: Path to the XML file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(xml_path):
        return False, f"XML file not found: {xml_path}"
        
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Basic CPC schema validation
        required_elements = ['classification-item', 'classification-symbol', 'class-title']
        for element in required_elements:
            if root.find(f".//{element}") is None:
                return False, f"Missing required element: {element}"
                
    except ET.ParseError as e:
        return False, f"XML parsing error: {e}"
    except Exception as e:
        return False, f"Error validating XML: {e}"
    
    return True, None

def validate_extraction_directory(extract_dir: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the extraction directory contains expected files.
    
    Args:
        extract_dir: Path to the extraction directory
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not os.path.exists(extract_dir):
        return False, f"Directory not found: {extract_dir}"
        
    xml_files = [f for f in os.listdir(extract_dir) if f.endswith('.xml')]
    
    if not xml_files:
        return False, "No XML files found in extraction directory"
        
    # Validate each XML file
    for xml_file in xml_files:
        xml_path = os.path.join(extract_dir, xml_file)
        is_valid, error = validate_xml_file(xml_path)
        if not is_valid:
            return False, f"Invalid XML file ({xml_file}): {error}"
            
    return True, None

