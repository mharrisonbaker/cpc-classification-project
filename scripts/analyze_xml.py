import os
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict

def analyze_cpc_files(directory_path):
    print(f"Analyzing CPC XML files in: {directory_path}")
    
    # Statistics
    stats = {
        'total_files': 0,
        'file_sizes': [],
        'root_elements': defaultdict(int),
        'depth_stats': defaultdict(int),
        'file_extensions': defaultdict(int)
    }
    
    # Walk through directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.xml'):
                file_path = Path(root) / file
                stats['total_files'] += 1
                
                # File size
                size = os.path.getsize(file_path)
                stats['file_sizes'].append(size)
                
                try:
                    # Parse XML structure
                    tree = ET.parse(file_path)
                    root_el = tree.getroot()
                    
                    # Count root element types
                    stats['root_elements'][root_el.tag] += 1
                    
                    # Get a sample of the structure from the first file
                    if stats['total_files'] == 1:
                        print("\nSample structure from first file:")
                        print_element_structure(root_el)
                        
                except Exception as e:
                    print(f"Error parsing {file}: {str(e)}")
                
                # Track file extensions
                ext = Path(file).suffix
                stats['file_extensions'][ext] += 1
                
    # Print summary
    print("\nSummary:")
    print(f"Total XML files found: {stats['total_files']}")
    if stats['file_sizes']:
        print(f"Average file size: {sum(stats['file_sizes']) / len(stats['file_sizes']) / 1024:.2f} KB")
        print(f"Largest file: {max(stats['file_sizes']) / 1024:.2f} KB")
        print(f"Smallest file: {min(stats['file_sizes']) / 1024:.2f} KB")
    
    print("\nRoot elements found:")
    for elem, count in stats['root_elements'].items():
        print(f"  {elem}: {count} files")

def print_element_structure(element, level=0):
    """Print the structure of an XML element"""
    print("  " * level + f"<{element.tag}>")
    for child in element:
        print_element_structure(child, level + 1)

if __name__ == "__main__":
    directory_path = r"C:\Data\CPCSchemeXML202408"
    analyze_cpc_files(directory_path)