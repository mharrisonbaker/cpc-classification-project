# scripts/process_definitions.py

import json
import logging
from pathlib import Path
import sys
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import os

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.pipeline.definition_processor.cleaner import DefinitionCleaner

def setup_logging(log_dir: Path) -> None:
    """Configure logging for the script."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"definition_cleaning_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_completed_files(cleaned_dir: Path) -> set:
    """Get set of already processed files."""
    completed = set()
    if cleaned_dir.exists():
        for json_file in cleaned_dir.glob("**/*.json"):
            # Store relative path for comparison
            completed.add(json_file.name)
    return completed

def process_file(args):
    """
    Process a single JSON file.
    
    Args:
        args: Tuple of (json_file, expanded_dir, cleaned_dir)
        
    Returns:
        Tuple of (filename, success boolean, error message if any)
    """
    json_file, expanded_dir, cleaned_dir = args
    
    try:
        # Create DefinitionCleaner instance for this process
        cleaner = DefinitionCleaner()
        
        relative_path = Path(json_file).relative_to(expanded_dir)
        output_file = cleaned_dir / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and process JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        processed_data = cleaner.process_json(data)
        
        # Save processed data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
            
        return str(relative_path), True, None
        
    except Exception as e:
        return str(json_file), False, str(e)

def process_batch_directory(
    batch_dir: Path,
    logger: logging.Logger,
    max_workers: int = None
) -> None:
    """
    Process all JSON files in a batch directory using multiple processes.
    
    Args:
        batch_dir: Path to batch directory
        logger: Logger instance
        max_workers: Maximum number of worker processes (None = CPU count)
    """
    expanded_dir = batch_dir / "expanded_json"
    cleaned_dir = batch_dir / "cleaned_json"
    
    if not expanded_dir.exists():
        logger.warning(f"Expanded directory not found: {expanded_dir}")
        return
        
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    # Get set of completed files
    completed_files = get_completed_files(cleaned_dir)
    logger.info(f"Found {len(completed_files)} already processed files")
    
    # Get list of files to process
    json_files = [
        f for f in expanded_dir.glob("**/*.json")
        if f.name not in completed_files
    ]
    total_files = len(json_files)
    
    logger.info(f"Found {total_files} files remaining to process")
    
    if total_files == 0:
        logger.info("No new files to process")
        return
    
    # If max_workers not specified, use CPU count
    if max_workers is None:
        max_workers = os.cpu_count() or 4
    
    # Prepare arguments for each file
    file_args = [(str(f), str(expanded_dir), str(cleaned_dir)) for f in json_files]
    
    # Process files in parallel with progress bar
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, args) for args in file_args]
        
        success_count = 0
        error_count = 0
        
        with tqdm(total=total_files, desc="Processing files") as pbar:
            for future in as_completed(futures):
                filename, success, error = future.result()
                if success:
                    success_count += 1
                    logger.info(f"Successfully processed: {filename}")
                else:
                    error_count += 1
                    logger.error(f"Error processing {filename}: {error}")
                pbar.update(1)
    
    # Log summary
    logger.info(f"\nProcessing complete:")
    logger.info(f"Previously completed: {len(completed_files)}")
    logger.info(f"New files processed: {total_files}")
    logger.info(f"Successfully processed: {success_count}")
    logger.info(f"Errors: {error_count}")

def main():
    # Setup paths
    project_root = Path(__file__).resolve().parents[1]
    batch_dir = project_root / "data" / "batch_output" / "2025_01"
    log_dir = project_root / "logs" / "definition_cleaning"
    
    # Setup logging
    setup_logging(log_dir)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting definition cleaning process")
    
    try:
        # Process batch directory with multiprocessing
        # You can adjust max_workers if needed
        max_workers = os.cpu_count() or 4
        logger.info(f"Using {max_workers} worker processes")
        
        process_batch_directory(batch_dir, logger, max_workers=max_workers)
            
        logger.info("Definition cleaning process completed successfully")
        
    except Exception as e:
        logger.error(f"Fatal error in definition cleaning process: {str(e)}")
        raise

if __name__ == '__main__':
    main()