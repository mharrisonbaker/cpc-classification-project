"""Batch processor for CPC definitions with resume capability."""

import os
import re  
import json
import time
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from dataclasses import dataclass
import ollama
import signal
import sys
from .constants import (
    BATCH_OUTPUT_DIR, 
    LLM_MODEL,
    MAX_WORKERS,
    BATCH_SIZE,
    STATE_DB_NAME,
    STATUS_COMPLETED,
    STATUS_FAILED,
    RETRY_ATTEMPTS
)

@dataclass
class ProcessingState:
    version: str
    total_symbols: int
    processed_symbols: Set[str]
    failed_symbols: Dict[str, str]
    start_time: datetime
    last_update: datetime

from .definition_expander import CPCDefinitionExpander  


class BatchProcessor:
    def __init__(self, version: str, base_dir: str):
        self.version = version
        self.base_dir = Path(base_dir)
        self.state_db = self.base_dir / version / STATE_DB_NAME
        self.log_dir = self.base_dir / version / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_logging()
        self._init_state_db()
        
        self.cache = {}

        #  Fix: Use CPCDefinitionExpander
        self.expander = CPCDefinitionExpander(model_name=LLM_MODEL)

    def setup_interrupt_handling():
        def signal_handler(signum, frame):
            print("\nReceived interrupt signal. Cleaning up...")
            raise KeyboardInterrupt()

        if os.name == 'nt':  # Windows
            signal.signal(signal.CTRL_C_EVENT, signal_handler)
        else:  # Unix/Linux/Mac
            signal.signal(signal.SIGINT, signal_handler)
        
    def _init_logging(self):
        self.logger = logging.getLogger(f"BatchProcessor-{self.version}")
        self.logger.setLevel(logging.INFO)
        
        # File handler - keeps INFO level
        fh = logging.FileHandler(
            self.log_dir / f"batch_process_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        # Console handler - change to WARNING
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)  # Changed from INFO to WARNING
        ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        self.logger.addHandler(ch)

    def _init_state_db(self):
        """Initialize SQLite database for tracking processing state."""
        with sqlite3.connect(self.state_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processed_symbols (
                    symbol TEXT PRIMARY KEY,
                    status TEXT,
                    error TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS processing_stats (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

    def save_state(self, symbol: str, status: str, error: str = None):
        """Save processing state for a symbol."""
        with sqlite3.connect(self.state_db) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO processed_symbols (symbol, status, error) VALUES (?, ?, ?)',
                (symbol, status, error)
            )

    def process_directory(self, input_dir):
        input_dir = Path(input_dir)
        processed_symbols = self.get_processed_symbols()
        json_files = list(input_dir.glob('*.json'))
        total_files = len(json_files)

        self.logger.info(f"Found {total_files} JSON files to process")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self.process_json_file, json_path, processed_symbols): json_path
                for json_path in json_files
            }
            
            completed = 0
            for future in futures:
                json_path = futures[future]
                try:
                    future.result()  # Wait for completion
                    completed += 1
                    self.logger.info(f"Completed {json_path.name} ({completed}/{total_files})")
                except KeyboardInterrupt:
                    self.logger.warning("Process interrupted! Cleaning up...")
                    executor.shutdown(wait=False)
                    raise
                except Exception as e:
                    self.logger.error(f"Failed to process {json_path.name}: {e}")     

    def get_processed_symbols(self) -> Set[str]:
        """Get set of already processed symbols."""
        with sqlite3.connect(self.state_db) as conn:
            cursor = conn.execute('SELECT symbol FROM processed_symbols WHERE status = ?', 
                                (STATUS_COMPLETED,))
            return {row[0] for row in cursor.fetchall()}

    def get_failed_symbols(self) -> Dict[str, str]:
        """Get dictionary of failed symbols and their errors."""
        with sqlite3.connect(self.state_db) as conn:
            cursor = conn.execute('SELECT symbol, error FROM processed_symbols WHERE status = ?',
                                (STATUS_FAILED,))
            return dict(cursor.fetchall())

    def generate_definition(self, symbol: str, title: Dict[str, str]) -> str:
        """Generate expanded definition using Ollama."""
        print(f"\nGenerating definition for {symbol}")
        self.logger.info(f"Generating definition for {symbol}")
        
        # Cache check
        cache_key = f"{symbol}_{hash(str(title))}"
        if cache_key in self.cache:
            print(f"Cache hit for {symbol}")
            return self.cache[cache_key]

        title_text = title.get('main', '')
        if title.get('cpc_specific'):
            title_text += f" {title['cpc_specific']}"
        
        print(f"Title: {title_text}")

        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = ollama.chat(model=LLM_MODEL, messages=[
                    {
                        "role": "system",
                        "content": "You are a patent classification expert. Provide technical, precise definitions."
                    },
                    {
                        "role": "user",
                        "content": self._construct_prompt(symbol, title_text)
                    }
                ])
                
                definition = response['message']['content'].strip()
                print(f"Raw definition: {definition}")
                
                # Format and validate
                definition = self._format_definition(definition)
                is_valid, msg = self._validate_definition(definition)
                
                if is_valid:
                    self.cache[cache_key] = definition
                    print(f"Valid definition: {definition}")
                    return definition
                
                print(f"Invalid definition: {msg}")
                
            except Exception as e:
                print(f"Error: {e}")
                
        return f"Error: Unable to generate valid definition for {symbol}"
    
    def _construct_prompt(self, symbol: str, title_text: str) -> str:
        """Construct a detailed prompt for the LLM."""
        return f"""
        Provide a precise, technical definition for the CPC classification:
        
        - Symbol: {symbol}
        - Title: {title_text}

        Instructions:
        1. Use industry-specific terminology.
        2. Clearly explain the technical scope.
        3. Keep the response between 15-100 words.
        4. Format in full sentences.

        Example:
        "A01B 1/00 refers to soil-working tools designed for breaking, loosening, or conditioning soil before planting."
        """


    def _validate_definition(self, definition: str) -> tuple[bool, str]:
        """Validate definition length only."""
        word_count = len(definition.split())
        
        if word_count < 15:
            return False, f"Definition too short ({word_count} words)"
            
        if word_count > 150:
            return False, f"Definition too long ({word_count} words)"
                
        return True, "Valid"

    def _format_definition(self, definition: str) -> str:
        prefixes_to_remove = [
            "definition:", 
            "expanded definition:",
            "technical definition:"
        ]
        
        cleaned = definition.lower()
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                definition = definition[len(prefix):].strip()
                
        definition = definition[0].upper() + definition[1:]
        definition = ' '.join(definition.split())
        
        if not definition.endswith('.'):
            definition += '.'
            
        return definition

    def process_json_file(self, json_path: Path, processed_symbols: Set[str]):
        """Process a single JSON file, level by level, with resume capability."""
        self.logger.info(f"Processing {json_path}")

        expanded_dir = Path(BATCH_OUTPUT_DIR) / self.version / "expanded_json"
        output_path = expanded_dir / json_path.name
        
        # Check if file exists and contains valid expanded definitions
        if output_path.exists():
            try:
                with open(output_path, encoding="utf-8") as f:
                    existing_data = json.load(f)
                if any('expanded_definition' in item for item in existing_data):
                    self.logger.info(f"Skipping {json_path} - already processed")
                    return
            except json.JSONDecodeError:
                self.logger.warning(f"Found corrupt expanded JSON: {output_path}")

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        def process_level(items: List[Dict], level: int = 0):
            for item in items:
                try:
                    symbol = item['symbol']
                    if symbol not in processed_symbols and 'expanded_definition' not in item:
                        definition = self.generate_definition(symbol, item['title'])
                        if definition and "Error" not in definition:
                            item['expanded_definition'] = definition
                            self.save_state(symbol, STATUS_COMPLETED)
                            self.logger.info(f"Level {level}: Added definition for {symbol}")
                        else:
                            self.logger.warning(f"Level {level}: No valid definition for {symbol}")
                            self.save_state(symbol, STATUS_FAILED, "No valid definition")

                except KeyboardInterrupt:
                    self.logger.warning("Interrupted during processing!")
                    raise
                except Exception as e:
                    self.logger.error(f"Error processing symbol: {e}")
                    continue

            # Process children after current level
            for item in items:
                if 'children' in item and item['children']:
                    process_level(item['children'], level + 1)
        
        temp_path = None
        try:
            process_level(data)
            expanded_dir.mkdir(parents=True, exist_ok=True)
            
            # Atomic write using temporary file
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(output_path)
            
        except KeyboardInterrupt:
            self.logger.warning(f"Processing interrupted for {json_path}")
            if temp_path and temp_path.exists():
                temp_path.unlink()
            self._cleanup_interrupted_state()  # Add this method
            raise
        except Exception as e:
            self.logger.error(f"Error processing {json_path}: {str(e)}", exc_info=True)
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise

        self.logger.info(f"Completed processing: {output_path}")


    def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        with sqlite3.connect(self.state_db) as conn:
            total = conn.execute('SELECT COUNT(*) FROM processed_symbols').fetchone()[0]
            completed = conn.execute(
                'SELECT COUNT(*) FROM processed_symbols WHERE status = ?',
                (STATUS_COMPLETED,)
            ).fetchone()[0]
            failed = conn.execute(
                'SELECT COUNT(*) FROM processed_symbols WHERE status = ?',
                (STATUS_FAILED,)
            ).fetchone()[0]
            
        return {
            "total_symbols": total,
            "completed": completed,
            "failed": failed,
            "completion_rate": (completed / total * 100) if total > 0 else 0
        }

    def clean_failed_states(self):
        """Reset failed states to allow reprocessing."""
        with sqlite3.connect(self.state_db) as conn:
            conn.execute('DELETE FROM processed_symbols WHERE status = ?', 
                        (STATUS_FAILED,))
        self.logger.info("Cleaned failed states")

    def _cleanup_interrupted_state(self):
        """Clean up state after interruption"""
        with sqlite3.connect(self.state_db) as conn:
            conn.execute('''
                UPDATE processed_symbols 
                SET status = ? 
                WHERE status = ?''', 
                (STATUS_FAILED, STATUS_PROCESSING)
            )