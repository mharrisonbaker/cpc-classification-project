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
        self.state_db = self.base_dir / version / "batch_state.db"
        self.log_dir = self.base_dir / version / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_logging()
        self._init_state_db()
        
    def _init_logging(self):
        self.logger = logging.getLogger(f"BatchProcessor-{self.version}")
        self.logger.setLevel(logging.INFO)
        
        fh = logging.FileHandler(
            self.log_dir / f"batch_process_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)

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
            cursor = conn.execute('SELECT symbol FROM processed_symbols WHERE status = "completed"')
            return {row[0] for row in cursor.fetchall()}

    def get_failed_symbols(self) -> Dict[str, str]:
        """Get dictionary of failed symbols and their errors."""
        with sqlite3.connect(self.state_db) as conn:
            cursor = conn.execute('SELECT symbol, error FROM processed_symbols WHERE status = "failed"')
            return dict(cursor.fetchall())

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
                    # Your definition generation logic here
                    # item['expanded_definition'] = generated_definition
                    self.save_state(symbol, "completed")
                except Exception as e:
                    self.logger.error(f"Failed to process {symbol}: {e}")
                    self.save_state(symbol, "failed", str(e))
            
            if 'children' in item and item['children']:
                item['children'] = [process_item(child) for child in item['children']]
            
            return item

        processed_data = [process_item(item) for item in data]
        
        # Save processed file
        output_path = json_path.parent / 'expanded' / json_path.name
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=2)

    def process_directory(self, input_dir: Path):
        """Process all JSON files in directory with resume capability."""
        processed_symbols = self.get_processed_symbols()
        failed_symbols = self.get_failed_symbols()
        
        self.logger.info(f"Resuming processing. Already processed: {len(processed_symbols)}")
        if failed_symbols:
            self.logger.warning(f"Previously failed symbols: {len(failed_symbols)}")
        
        json_files = list(input_dir.glob('*.json'))
        total_files = len(json_files)
        
        self.logger.info(f"Found {total_files} JSON files to process")
        
        for i, json_path in enumerate(json_files, 1):
            try:
                self.process_json_file(json_path, processed_symbols)
                self.logger.info(f"Completed file {i}/{total_files}: {json_path.name}")
            except Exception as e:
                self.logger.error(f"Failed to process file {json_path}: {e}")
                continue

    def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        with sqlite3.connect(self.state_db) as conn:
            total = conn.execute('SELECT COUNT(*) FROM processed_symbols').fetchone()[0]
            completed = conn.execute(
                'SELECT COUNT(*) FROM processed_symbols WHERE status = "completed"'
            ).fetchone()[0]
            failed = conn.execute(
                'SELECT COUNT(*) FROM processed_symbols WHERE status = "failed"'
            ).fetchone()[0]
            
        return {
            "total_symbols": total,
            "completed": completed,
            "failed": failed,
            "completion_rate": (completed / total * 100) if total > 0 else 0
        }