# src/pipeline/definition_processor/cleaner.py

import re
import logging
from pathlib import Path
from typing import Union, Dict, List, Optional

logger = logging.getLogger(__name__)

class DefinitionCleaner:
    """Cleans and standardizes CPC expanded definitions."""
    
    def __init__(self):
        # Generic CPC symbol patterns
        self._full_symbol = r'[A-HY]\d+[A-Z]?\d*(?:/\d+)?'
        self._partial_symbol = r'\d+[A-Z]?\d*(?:/\d+)?'  # For cases without section letter
        
        # Connecting words for symbol references
        self._connectors = r'(?:pertains to|relates to|covers|addresses|refers to)'
        self._domain_refs = r'(?:covers |addresses |pertains to |relates to )?the domain of'
        
        # Common preamble patterns to remove
        self.preamble_patterns = [
            # Direct symbol references with variations
            rf"^Symbol {self._full_symbol} {self._connectors}",
            rf"^Symbol: {self._full_symbol}(?:\s+Title:)?",
            rf"^Code {self._full_symbol} specifically {self._domain_refs}",
            rf"^{self._full_symbol} {self._domain_refs}",
            rf"^{self._full_symbol} {self._connectors}",
            
            # Partial symbol references (without section letter)
            rf"^{self._partial_symbol} {self._domain_refs}",
            rf"^{self._partial_symbol} {self._connectors}",
            
            # Basic CPC/Classification references
            rf"^(?:The )?(?:CPC )?classification (?:symbol )?(?:{self._full_symbol} )?(?:{self._connectors})",
            r"^This classification (?:pertains to|refers to|encompasses|relates to|covers)",
            rf"^Symbol: {self._full_symbol} Title:.*?(?:Expanded )?Definition:?",
            r"^(?:The )?(?:CPC )?classification (?:symbol )?[A-Z]",
            r"^The (?:CPC )?classification relates to",
            r"^The Cooperative Patent Classification \(CPC\)",
            r"^The CPC classification symbol",
            
            # Tools/devices references
            rf"(?:Tools|Devices|Mechanisms), as classified under (?:CPC symbol )?{self._full_symbol},? (?:refer to|relate to|pertain to)",
            rf"(?:Tools|Devices|Mechanisms), as classified under",
            
            # Under/within references
            rf".*?(?:methods|devices|technologies|compounds|compositions|additives|tools|mechanisms) under the (?:CPC |Cooperative Patent Classification \(CPC\) )?(?:symbol )?{self._full_symbol}",
            rf".*?, as classified under the (?:CPC |Cooperative Patent Classification \(CPC\) )?(?:symbol )?{self._full_symbol}",
            r".*? within the domain of",
            
            # Category/classification descriptions
            r"^(?:The )?(?:category|classification) (?:covers|encompasses|includes|involves)",
            r"^This classification (?:covers|encompasses|includes|involves|specifically|addresses)",
            r"^This category (?:covers|encompasses|includes|involves|specifically|addresses)",
            
            # Technical domain/scope intros
            r"^The (?:technical )?(?:scope|domain) (?:of this|involves|includes)",
            r"^This (?:technical )?domain",
            r"^Within this scope",
            r"^The scope of this",
            
            # Common subject intros
            r"^These (?:additives|compounds|materials|devices|tools)",
            r"^This (?:technology|process|formulation|device|tool)",
            r"^The (?:technology|process|formulation|device|tool)",
            
            # Short tool/device patterns
            r"^(?:Tools|Devices|Mechanisms) (?:designed|intended|used) for",
            r"^(?:Tools|Devices|Mechanisms) that",
            
            # Other common starts
            r"^In (?:technical )?terms,",
            r"^Technically,",
            r"^In essence,",
            r"^Specifically,"
        ]
        
        # Compile patterns for efficiency
        self.preamble_regex = re.compile(
            '|'.join(self.preamble_patterns), 
            re.IGNORECASE | re.MULTILINE
        )
        
        logger.info("Initialized DefinitionCleaner with %d preamble patterns", 
                   len(self.preamble_patterns))

    def clean_definition(self, text: str) -> str:
        """
        Clean a single definition by removing preambles and standardizing format.
        
        Args:
            text: Raw expanded definition text
            
        Returns:
            Cleaned definition text
        """
        if not text:
            return text
            
        # Remove preambles
        cleaned = self.preamble_regex.sub('', text).strip()
        
        # Handle special cases where multiple preambles might be present
        while any(re.match(pattern, cleaned, re.IGNORECASE) for pattern in self.preamble_patterns):
            cleaned = self.preamble_regex.sub('', cleaned).strip()
        
        # Capitalize first letter if needed
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
            
        # Ensure proper ending punctuation
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
            
        logger.debug("Cleaned definition from %d to %d characters", 
                    len(text), len(cleaned))
            
        return cleaned

    

    def process_json(self, data: Union[Dict, List]) -> Union[Dict, List]:
        """
        Recursively process all expanded definitions in a CPC JSON structure.
        
        Args:
            data: CPC JSON data structure (dict or list)
            
        Returns:
            Processed CPC JSON data with cleaned definitions
        """
        if isinstance(data, dict):
            if 'expanded_definition' in data and data['expanded_definition']:
                data['expanded_definition'] = self.clean_definition(
                    data['expanded_definition']
                )
                
                # Log symbol processing if available
                if 'symbol' in data:
                    logger.info("Processed definition for symbol: %s", data['symbol'])
            
            if 'children' in data and data['children']:
                data['children'] = self.process_json(data['children'])
                
        elif isinstance(data, list):
            return [self.process_json(item) for item in data]
            
        return data

    def validate_cleaning(self, original: str, cleaned: str) -> bool:
        """
        Validate that the cleaning process maintained content integrity.
        
        Args:
            original: Original definition text
            cleaned: Cleaned definition text
            
        Returns:
            True if cleaning is valid, False otherwise
        """
        if not cleaned:
            logger.warning("Cleaning resulted in empty definition")
            return False
            
        # Check significant content loss
        if len(cleaned) < len(original) * 0.5:
            logger.warning("Cleaning removed more than 50% of content")
            return False
            
        # Ensure key technical terms are preserved
        # This could be enhanced with domain-specific term checking
        return True

    @staticmethod
    def get_version_dirs(base_path: Union[str, Path]) -> List[Path]:
        """
        Get all version directories in the data path.
        
        Args:
            base_path: Base path containing version directories
            
        Returns:
            List of version directory paths
        """
        base_path = Path(base_path)
        version_dirs = []
        
        # Check standard version directories
        for version_dir in base_path.glob('[0-9][0-9][0-9][0-9]_[0-9][0-9]'):
            if version_dir.is_dir():
                version_dirs.append(version_dir)
                
        # Check 'latest' directory
        latest_dir = base_path / 'latest'
        if latest_dir.exists() and latest_dir.is_dir():
            version_dirs.append(latest_dir)
            
        return version_dirs