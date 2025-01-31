"""CPC XML scheme parsing functionality."""

import os
import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CPCTitle:
    """Represents a CPC classification title with all its components."""
    main_text: str
    cpc_specific_text: Optional[str] = None
    additional_text: List[str] = None
    synonyms: List[str] = None

@dataclass
class CPCReference:
    """Represents a CPC classification reference."""
    text: str
    symbol: Optional[str] = None
    type: str = "informative"  # informative, limiting, or application

@dataclass
class CPCClassification:
    """Represents a complete CPC classification item."""
    symbol: str
    title: CPCTitle
    level: str  # section, class, subclass, group, subgroup
    parent_symbol: Optional[str] = None
    notes: List[str] = None
    warnings: List[str] = None
    references: List[CPCReference] = None
    children: List['CPCClassification'] = None

class CPCSchemeParser:
    """Parser for CPC classification scheme XML files."""
    
    def __init__(self):
        self.stats = {
            "processed_items": 0,
            "with_notes": 0,
            "with_warnings": 0,
            "with_references": 0
        }

    def parse_file(self, xml_path: str) -> List[CPCClassification]:
        """
        Parses a CPC scheme XML file.
        
        Args:
            xml_path: Path to the XML file
            
        Returns:
            List of parsed CPCClassification objects
        """
        logger.info(f"Parsing XML file: {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        classifications = []
        for item in root.findall(".//classification-item"):
            classifications.append(self._parse_classification_item(item))
            
        logger.info(f"Parsed {len(classifications)} top-level classifications")
        return classifications

    def _parse_classification_item(self, item: ET.Element, 
                                 parent_symbol: Optional[str] = None) -> CPCClassification:
        """Parses a single classification item and its children."""
        self.stats["processed_items"] += 1
        
        symbol = item.find("classification-symbol").text
        level = self._determine_level(symbol)
        
        # Parse title
        title = self._parse_title(item.find("class-title"))
        
        # Parse metadata
        notes, warnings = self._parse_notes_and_warnings(item)
        references = self._parse_references(item)
        
        # Create classification object
        classification = CPCClassification(
            symbol=symbol,
            title=title,
            level=level,
            parent_symbol=parent_symbol,
            notes=notes,
            warnings=warnings,
            references=references,
            children=[]
        )
        
        # Parse children recursively
        for child in item.findall("./classification-item"):
            classification.children.append(
                self._parse_classification_item(child, parent_symbol=symbol)
            )
            
        return classification

    def _parse_title(self, title_element: ET.Element) -> CPCTitle:
        """Parses the title element with all its components."""
        if title_element is None:
            return CPCTitle(main_text="")
            
        main_parts = []
        cpc_specific_parts = []
        additional_parts = []
        synonyms = []
        
        for title_part in title_element.findall(".//title-part"):
            # Main text
            texts = title_part.findall("text")
            main_parts.extend(t.text for t in texts if t.text)
            
            # CPC-specific text
            cpc_texts = title_part.findall(".//CPC-specific-text/text")
            cpc_specific_parts.extend(t.text for t in cpc_texts if t.text)
            
            # Additional text and synonyms
            for additional in title_part.findall(".//additional-text"):
                if additional.get("type") == "synonym":
                    synonyms.append(additional.text)
                else:
                    additional_parts.append(additional.text)
                    
        return CPCTitle(
            main_text=" ".join(main_parts).strip(),
            cpc_specific_text=" ".join(cpc_specific_parts).strip() if cpc_specific_parts else None,
            additional_text=additional_parts if additional_parts else None,
            synonyms=synonyms if synonyms else None
        )

    def _parse_notes_and_warnings(self, item: ET.Element) -> tuple[List[str], List[str]]:
        """Extracts notes and warnings from a classification item."""
        notes = []
        warnings = []
        
        notes_warnings = item.find("notes-and-warnings")
        if notes_warnings is not None:
            notes = [note.text for note in notes_warnings.findall("note") if note.text]
            warnings = [warning.text for warning in notes_warnings.findall("warning") if warning.text]
            
            if notes:
                self.stats["with_notes"] += 1
            if warnings:
                self.stats["with_warnings"] += 1
                
        return notes, warnings

    def _parse_references(self, item: ET.Element) -> List[CPCReference]:
        """Extracts all types of references from a classification item."""
        references = []
        
        for ref_type in ["limiting-references", "informative-references", "application-references"]:
            refs = item.find(ref_type)
            if refs is not None:
                ref_category = ref_type.replace("-references", "")
                for ref in refs.findall(".//reference"):
                    references.append(CPCReference(
                        text=ref.text if ref.text else "",
                        symbol=ref.get("classification-symbol"),
                        type=ref_category
                    ))
                
        if references:
            self.stats["with_references"] += 1
            
        return references if references else None

    def _determine_level(self, symbol: str) -> str:
        """Determines the hierarchical level of a classification symbol."""
        if len(symbol) == 1:
            return "section"
        elif len(symbol) <= 3:
            return "class"
        elif len(symbol) == 4:
            return "subclass"
        else:
            parts = symbol.split('/')
            if len(parts) == 1:
                return "group"
            return "subgroup" if parts[1] != "00" else "main-group"

    def get_statistics(self) -> Dict[str, int]:
        """Returns parsing statistics."""
        return self.stats

    def to_dict(self, classification: CPCClassification) -> Dict:
        """Converts a CPCClassification object to a dictionary for JSON serialization."""
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
                    } for ref in (classification.references or [])
                ] if classification.references else None
            },
            "children": [
                self.to_dict(child) for child in (classification.children or [])
            ] if classification.children else None
        }