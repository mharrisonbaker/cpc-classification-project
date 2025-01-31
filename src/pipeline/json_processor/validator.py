"""Validation utilities for CPC JSON data."""

import json
import jsonschema
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

from .schema import CPC_SCHEMA, STATS_SCHEMA, VERSION_SCHEMA
from .constants import MAX_TITLE_LENGTH, MAX_DEFINITION_LENGTH

logger = logging.getLogger(__name__)

class CPCJsonValidator:
    """Validates CPC JSON data against defined schemas."""
    
    def __init__(self):
        self.validation_stats = {
            "total_validated": 0,
            "valid": 0,
            "invalid": 0,
            "errors": []
        }
    
    def validate_cpc_item(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a single CPC classification item against the schema.
        
        Args:
            data: Dictionary containing CPC classification data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        self.validation_stats["total_validated"] += 1
        
        try:
            jsonschema.validate(data, CPC_SCHEMA)
            
            # Additional validation checks
            if len(data["title"]["main"]) > MAX_TITLE_LENGTH:
                raise ValueError(f"Title exceeds maximum length of {MAX_TITLE_LENGTH}")
                
            if "expanded_definition" in data and data["expanded_definition"]:
                if len(data["expanded_definition"]) > MAX_DEFINITION_LENGTH:
                    raise ValueError(f"Definition exceeds maximum length of {MAX_DEFINITION_LENGTH}")
            
            self.validation_stats["valid"] += 1
            return True, None
            
        except jsonschema.exceptions.ValidationError as e:
            error_msg = f"Schema validation error: {str(e)}"
            self.validation_stats["invalid"] += 1
            self.validation_stats["errors"].append(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.validation_stats["invalid"] += 1
            self.validation_stats["errors"].append(error_msg)
            return False, error_msg
    
    def validate_json_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validates an entire JSON file containing CPC data.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    is_valid, error = self.validate_cpc_item(item)
                    if not is_valid:
                        return False, f"Invalid item in file: {error}"
            else:
                return self.validate_cpc_item(data)
            
            return True, None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            self.validation_stats["errors"].append(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"File validation error: {str(e)}"
            self.validation_stats["errors"].append(error_msg)
            return False, error_msg
    
    def validate_stats(self, stats: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates processing statistics against the stats schema."""
        try:
            jsonschema.validate(stats, STATS_SCHEMA)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            return False, f"Invalid stats format: {str(e)}"
    
    def validate_version_info(self, version_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates version information against the version schema."""
        try:
            jsonschema.validate(version_info, VERSION_SCHEMA)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            return False, f"Invalid version info format: {str(e)}"
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Returns validation statistics."""
        return self.validation_stats
    
    def reset_stats(self):
        """Resets validation statistics."""
        self.validation_stats = {
            "total_validated": 0,
            "valid": 0,
            "invalid": 0,
            "errors": []
        }