import os
import re
import glob
from pathlib import Path

def analyze_cpc_files(directory):
    # Pattern for CPC scheme files
    pattern = r'cpc-scheme-[A-Z][0-9][0-9][A-Z]\.xml$'
    
    # Get all matching files
    files = []
    for file in Path(directory).glob('*.xml'):
        if re.match(pattern, file.name):
            files.append(file)
    
    print(f"Found {len(files)} matching CPC scheme files")
    print("\nSample of file names:")
    for file in sorted(files)[:5]:
        print(f"- {file.name}")
    
    # If you want to look at file sizes
    sizes = [file.stat().st_size for file in files]
    if sizes:
        print(f"\nFile size stats:")
        print(f"Smallest: {min(sizes):,} bytes")
        print(f"Largest: {max(sizes):,} bytes")
        print(f"Average: {sum(sizes)/len(sizes):,.0f} bytes")

# Run the analysis
directory = r"C:\Data\CPCSchemeXML202408"
analyze_cpc_files(directory)