"""Converter for CPC XML to JSON transformation."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..xml_processor.parser import CPCSchemeParser, CPCClassification
from .validator import CPCJsonValidator
from .constants import (
    JSON_OUTPUT_DIR,
    DEFAULT_INDENT,
    DEFAULT_ENCODING,
    PROCESSED_DIR_NAME,
    BATCH_SIZE
)

logger = logging.getLogger(__name__)

class CPCJsonConverter:
    """Converts CPC XML data to structured JSON format."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or JSON_OUTPUT_DIR
        self.xml_parser = CPCSchemeParser()
        self.validator = CPCJsonValidator()
        
        self.conversion_stats = {
            "files_processed": 0,
            "items_converted": 0,
            "validation_errors": 0,
            "start_time": None,
            "end_time": None,
            "processing_time": 0
        }

    def convert_directory(self, xml_dir: str, version: str) -> Tuple[str, Dict[str, Any]]:
        """
        Converts all XML files in a directory to JSON.
        
        Args:
            xml_dir: Directory containing XML files
            version: CPC version string (YYYY_MM)
            
        Returns:
            Tuple of (output_directory, conversion_statistics)
        """
        self.conversion_stats["start_time"] = datetime.now()
        
        # Create output directory
        output_dir = os.path.join(self.output_dir, version, PROCESSED_DIR_NAME)
        os.makedirs(output_dir, exist_ok=True)

        # Check if JSON files already exist
        existing_jsons = len(list(Path(output_dir).glob("*.json")))
        if existing_jsons > 0:
            logger.info(f"Found {existing_jsons} existing JSON files, skipping conversion.")
            return output_dir, self.conversion_stats
        
        # Process all XML files
        xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
        logger.info(f"Found {len(xml_files)} XML files to process")
        
        for xml_file in xml_files:
            xml_path = os.path.join(xml_dir, xml_file)
            json_path = os.path.join(output_dir, xml_file.replace('.xml', '.json'))
            
            try:
                self.convert_file(xml_path, json_path)
                self.conversion_stats["files_processed"] += 1
            except Exception as e:
                logger.error(f"Error processing {xml_file}: {e}")
                continue
        
        self.conversion_stats["end_time"] = datetime.now()
        self.conversion_stats["processing_time"] = (
            self.conversion_stats["end_time"] - self.conversion_stats["start_time"]
        ).total_seconds()
        
        return output_dir, self.get_conversion_stats()

    def convert_file(self, xml_path: str, json_path: str):
        """
        Converts a single XML file to JSON.
        
        Args:
            xml_path: Path to input XML file
            json_path: Path to output JSON file
        """
        logger.info(f"Converting {xml_path} → {json_path}")
        
        # Parse XML
        classifications = self.xml_parser.parse_file(xml_path)
        
        # Convert to JSON structure
        json_data = []
        for classification in classifications:
            converted_item = self._convert_classification(classification)
            is_valid, error = self.validator.validate_cpc_item(converted_item)
            
            if is_valid:
                json_data.append(converted_item)
                self.conversion_stats["items_converted"] += 1
            else:
                logger.warning(f"Validation error for {classification.symbol}: {error}")
                self.conversion_stats["validation_errors"] += 1
        
        # Write JSON file
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding=DEFAULT_ENCODING) as f:
            json.dump(json_data, f, indent=DEFAULT_INDENT, ensure_ascii=False)

    def _convert_classification(self, classification: CPCClassification) -> Dict[str, Any]:
        """
        Converts a CPCClassification object to a JSON-compatible dictionary.
        
        Args:
            classification: CPCClassification object
            
        Returns:
            Dictionary representation of the classification
        """
        return {
            "symbol": classification.symbol,
            "level": classification.level,
            "parent_symbol": classification.parent_symbol,
            "title": {
                "main": classification.title.main_text,
                "cpc_specific": classification.title.cpc_specific_text,
                "additional": classification.title.additional_text,
                "synonyms": classification.title.synonyms
            },
            "metadata": {
                "notes": classification.notes,
                "warnings": classification.warnings,
                "references": [
                    {
                        "text": ref.text,
                        "symbol": ref.symbol,
                        "type": ref.type
                    }
                    for ref in (classification.references or [])
                ] if classification.references else None
            },
            "children": [
                self._convert_classification(child)
                for child in (classification.children or [])
            ] if classification.children else None
        }

    def get_conversion_stats(self) -> Dict[str, Any]:
        """Returns current conversion statistics."""
        stats = self.conversion_stats.copy()
        stats.update({
            "xml_parser_stats": self.xml_parser.get_statistics(),
            "validation_stats": self.validator.get_validation_stats()
        })
        return stats

    def reset_stats(self):
        """Resets conversion statistics."""
        self.conversion_stats = {
            "files_processed": 0,
            "items_converted": 0,
            "validation_errors": 0,
            "start_time": None,
            "end_time": None,
            "processing_time": 0
        }
        self.validator.reset_stats()