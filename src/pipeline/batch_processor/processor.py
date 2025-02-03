"""Batch processor for CPC definitions with resume capability."""

import os
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

class BatchProcessor:
    def __init__(self, version: str, base_dir: str):
        self.version = version
        self.base_dir = Path(base_dir)
        self.state_db = self.base_dir / version / STATE_DB_NAME
        self.log_dir = self.base_dir / version / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_logging()
        self._init_state_db()
        
    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger(f"BatchProcessor-{self.version}")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(
            self.log_dir / f"batch_process_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
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
                r'[A-Z0-9]',
                r'\b(device|system|method|process|apparatus|technique|mechanism)\b'
            ]
        }
        
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

    def _validate_definition(self, definition: str) -> tuple[bool, str]:
        word_count = len(definition.split())
        
        if word_count < self.validation_patterns['min_words']:
            return False, "Definition too short"
            
        if word_count > self.validation_patterns['max_words']:
            return False, "Definition too long"
            
        for pattern in self.validation_patterns['unwanted_starts']:
            if re.match(pattern, definition.lower()):
                return False, "Starts with unwanted phrase"
                
        for pattern in self.validation_patterns['required_patterns']:
            if not re.search(pattern, definition):
                return False, f"Missing required pattern: {pattern}"
                
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
        """Process a single JSON file, skipping already processed symbols."""
        self.logger.info(f"Processing {json_path}")
        
        with open(json_path) as f:
            data = json.load(f)
        
        def process_item(item: Dict) -> Dict:
            """Process a single CPC item and its children."""
            symbol = item['symbol']
            
            if symbol not in processed_symbols:
                try:
                    item['expanded_definition'] = self.generate_definition(
                        symbol,
                        item['title']
                    )
                    self.save_state(symbol, STATUS_COMPLETED)
                except Exception as e:
                    self.logger.error(f"Failed to process {symbol}: {e}")
                    self.save_state(symbol, STATUS_FAILED, str(e))
            
            if 'children' in item and item['children']:
                item['children'] = [process_item(child) for child in item['children']]
            
            return item

        processed_data = [process_item(item) for item in data]
        
        # Save to batch output directory
        expanded_dir = Path(BATCH_OUTPUT_DIR) / self.version / "expanded_json"
        expanded_dir.mkdir(parents=True, exist_ok=True)
        output_path = expanded_dir / json_path.name
        
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=2)

    def process_directory(self, input_dir):
        """Process all JSON files in directory with resume capability."""
        input_dir = Path(input_dir)  # Convert string to Path
        processed_symbols = self.get_processed_symbols()
        failed_symbols = self.get_failed_symbols()
        
        self.logger.info(f"Resuming processing. Already processed: {len(processed_symbols)}")
        if failed_symbols:
            self.logger.warning(f"Previously failed symbols: {len(failed_symbols)}")
        
        json_files = list(input_dir.glob('*.json'))
        total_files = len(json_files)
        
        self.logger.info(f"Found {total_files} JSON files to process")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for json_path in json_files:
                futures.append(
                    executor.submit(self.process_json_file, json_path, processed_symbols)
                )
            
            for i, future in enumerate(futures, 1):
                try:
                    future.result()
                    self.logger.info(f"Completed file {i}/{total_files}")
                except Exception as e:
                    self.logger.error(f"Failed to process file {i}: {e}")

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

    def signal_handler(sig, frame):
        print("\nStopping processing gracefully...")
        sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)