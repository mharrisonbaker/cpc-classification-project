# scripts/verify_cleaning.py

import json
import random
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.pipeline.definition_processor.cleaner import DefinitionCleaner

def print_comparison(original: str, cleaned: str, symbol: str = None) -> None:
    """Print a before/after comparison of definition cleaning."""
    print("\n" + "="*80)
    if symbol:
        print(f"Symbol: {symbol}")
    print("-"*80)
    print("ORIGINAL:")
    print(original)
    print("-"*80)
    print("CLEANED:")
    print(cleaned)
    print("="*80)

def verify_cleaning(input_dir: Path, num_samples: int = 5) -> None:
    """
    Sample definitions from JSON files and show cleaning results.
    
    Args:
        input_dir: Directory containing JSON files
        num_samples: Number of random definitions to sample
    """
    cleaner = DefinitionCleaner()
    
    # Get all JSON files
    json_files = list(input_dir.glob("**/*.json"))
    print(f"Found {len(json_files)} JSON files")
    
    # Sample random files
    sampled_files = random.sample(json_files, min(len(json_files), num_samples))
    
    for file_path in sampled_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Find items with expanded definitions
            def find_definitions(item, definitions=None):
                if definitions is None:
                    definitions = []
                if isinstance(item, dict):
                    if 'expanded_definition' in item and item['expanded_definition']:
                        definitions.append((
                            item.get('symbol', 'Unknown'),
                            item['expanded_definition']
                        ))
                    if 'children' in item and item['children']:
                        for child in item['children']:
                            find_definitions(child, definitions)
                elif isinstance(item, list):
                    for subitem in item:
                        find_definitions(subitem, definitions)
                return definitions
            
            definitions = find_definitions(data)
            
            if definitions:
                # Sample one definition from this file
                symbol, original = random.choice(definitions)
                cleaned = cleaner.clean_definition(original)
                print(f"\nFrom file: {file_path.name}")
                print_comparison(original, cleaned, symbol)
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

def main():
    # Setup paths
    project_root = Path(__file__).resolve().parents[1]
    input_dir = project_root / "data" / "batch_output" / "2025_01" / "expanded_json"
    
    print(f"Project root: {project_root}")
    print(f"Input directory: {input_dir}")
    print("\nVerifying cleaning patterns...")
    verify_cleaning(input_dir, num_samples=5)
    
if __name__ == '__main__':
    main()