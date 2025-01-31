import json
import time
import re
import csv
from concurrent.futures import ThreadPoolExecutor
import ollama
from typing import Dict, Optional, List
import logging
from dataclasses import dataclass
from datetime import datetime
import os

@dataclass
class ProcessingStats:
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    cache_hits: int = 0
    avg_response_time: float = 0.0

class CPCDefinitionExpander:
    def __init__(self, model_name: str = "phi4:14b", max_workers: int = 4):
        self.model = model_name
        self.max_workers = max_workers
        self.stats = ProcessingStats()
        self.cache = {}
        
        # Set up logging
        self._setup_logging()
        
        # Validation patterns
        self.validation_patterns = {
            'min_words': 15,
            'max_words': 100,
            'unwanted_starts': [
                r'^this (category|classification|group|section)',
                r'^these (categories|classifications|groups)',
                r'^refers to',
                r'^pertaining to'
            ],
            'required_patterns': [
                r'[A-Z0-9]',  # Must contain at least one uppercase letter or number
                r'\b(device|system|method|process|apparatus|technique|mechanism)\b'  # Technical terms
            ]
        }

    def _setup_logging(self):
        """Configure logging with both file and console handlers."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        self.logger = logging.getLogger("CPCExpander")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(
            os.path.join(log_dir, f"cpc_expansion_{datetime.now():%Y%m%d_%H%M%S}.log")
        )
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def get_definition(self, 
                      symbol: str, 
                      title: str, 
                      metadata: Dict,
                      parent_info: Optional[Dict] = None,
                      retries: int = 3) -> str:
        """
        Gets an expanded definition for a CPC category, with retries and validation.
        """
        # Check cache first
        cache_key = f"{symbol}_{hash(str(metadata))}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        prompt = self._construct_prompt(symbol, title, metadata, parent_info)
        
        for attempt in range(retries):
            try:
                response = ollama.chat(model=self.model, messages=[
                    {
                        "role": "system",
                        "content": "You are a patent classification expert. Provide technical, precise definitions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ])
                
                definition = response['message']['content'].strip()
                
                # Validate and format
                definition = self._format_definition(definition)
                is_valid, validation_msg = self._validate_definition(definition)
                
                if is_valid:
                    self.cache[cache_key] = definition
                    self.stats.successful += 1
                    return definition
                    
                self.logger.warning(f"⚠️ Invalid definition for {symbol}: {validation_msg}")
                
            except Exception as e:
                self.logger.error(f"❌ Error generating definition for {symbol}: {e}")
        
        self.stats.failed += 1
        return f"Error: Unable to generate valid definition for {symbol}"

    def _construct_prompt(self, symbol: str, title: str, metadata: Dict, 
                         parent_info: Optional[Dict] = None) -> str:
        """Construct a detailed prompt for the LLM."""
        context_parts = [
            "Provide a technical definition for this CPC classification:",
            f"Symbol: {symbol}",
            f"Title: {title}"
        ]

        if parent_info:
            context_parts.extend([
                "Parent Context:",
                f"- Symbol: {parent_info['symbol']}",
                f"- Title: {parent_info['title']}"
            ])

        instructions = [
            "Requirements:",
            "1. Start with key technical terms",
            "2. Focus on specific technical characteristics",
            "3. Use precise industry terminology",
            "4. Keep definition concise but complete",
            "5. Include specific technical components or methods"
        ]

        return "\n".join(context_parts + instructions)

    def _validate_definition(self, definition: str) -> tuple[bool, str]:
        """Validate the generated definition against quality criteria."""
        word_count = len(definition.split())
        
        if word_count < self.validation_patterns['min_words']:
            return False, "Definition too short"
            
        if word_count > self.validation_patterns['max_words']:
            return False, "Definition too long"
            
        # Check for unwanted starting phrases
        for pattern in self.validation_patterns['unwanted_starts']:
            if re.match(pattern, definition.lower()):
                return False, "Starts with unwanted phrase"
                
        # Check for required patterns
        for pattern in self.validation_patterns['required_patterns']:
            if not re.search(pattern, definition):
                return False, f"Missing required pattern: {pattern}"
                
        return True, "Valid"

    def _format_definition(self, definition: str) -> str:
        """Format and clean up the definition."""
        # Remove common unwanted prefixes
        prefixes_to_remove = [
            "definition:", 
            "expanded definition:",
            "technical definition:"
        ]
        
        cleaned = definition.lower()
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                definition = definition[len(prefix):].strip()
                
        # Ensure first letter is capitalized
        definition = definition[0].upper() + definition[1:]
        
        # Remove multiple spaces
        definition = ' '.join(definition.split())
        
        # Ensure ends with period
        if not definition.endswith('.'):
            definition += '.'
            
        return definition

    def expand_definitions(self, input_file: str, output_file: str) -> None:
        """Main method to expand definitions for an entire CPC hierarchy."""
        self.logger.info(f"Starting definition expansion: {input_file} → {output_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            processed_data = self.process_hierarchy(data)
            
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info("\n=== Processing Statistics ===")
            self.logger.info(f"Total Processed: {self.stats.total_processed}")
            self.logger.info(f"Successful: {self.stats.successful}")
            self.logger.info(f"Failed: {self.stats.failed}")
            self.logger.info(f"Cache Hits: {self.stats.cache_hits}")
            
        except Exception as e:
            self.logger.error(f"Fatal error during processing: {e}")
            raise