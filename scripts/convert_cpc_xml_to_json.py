import os
import json
import xml.etree.ElementTree as ET
import sys

def ensure_directory_exists(filepath):
    """Creates the parent directory for the given file if it doesn't exist."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def get_latest_version():
    """Reads the latest CPC version from config.json."""
    config_path = r"C:\Development\cpc-classification-project\config\config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)
        return config_data.get("latest_version", "")

def get_title_text(item):
    """Extracts and combines all title parts from the given classification item."""
    title_parts = []
    class_title = item.find("class-title")
    if class_title is not None:
        for title_part in class_title.findall(".//title-part"):
            texts = title_part.findall("text")
            cpc_texts = title_part.findall("CPC-specific-text/text")
            title_parts.extend([t.text for t in texts + cpc_texts if t.text])
    return " ".join(title_parts).strip()

def parse_classification_item(item):
    """Recursively parses classification items to maintain hierarchy."""
    result = {
        "symbol": item.find("classification-symbol").text,
        "title": get_title_text(item),
        "children": []
    }
    
    for child in item.findall("./classification-item"):
        result["children"].append(parse_classification_item(child))
    
    return result

def parse_cpc_scheme(xml_file):
    """Parses the CPC scheme XML file and extracts structured classification data dynamically."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    classifications = []
    for item in root.findall(".//classification-item"):
        classifications.append(parse_classification_item(item))
    
    return classifications

def convert_xml_to_json(input_xml):
    """
    Converts the given CPC scheme XML file into a structured JSON file.
    The output JSON is saved in the directory corresponding to the latest version.
    """
    latest_version = get_latest_version()
    if not latest_version:
        raise ValueError("Latest CPC version not found in config.json")
    
    output_json = fr"C:\Development\cpc-classification-project\data\cpc_versions\{latest_version}\json_output\{os.path.basename(input_xml).replace('.xml', '.json')}"
    
    structured_data = parse_cpc_scheme(input_xml)
    
    if not structured_data:
        print(f"⚠️ Warning: No classification data extracted from {input_xml}. Check XML structure.")
    
    # Ensure the output directory exists before writing the file
    ensure_directory_exists(output_json)
    
    with open(output_json, "w", encoding="utf-8") as json_file:
        json.dump(structured_data, json_file, indent=2, ensure_ascii=False)
    
    print(f"✅ Conversion complete. JSON saved to {output_json}")

def process_all_raw_xml():
    """Processes all XML files in the latest raw_xml directory."""
    latest_version = get_latest_version()
    raw_xml_dir = fr"C:\Development\cpc-classification-project\data\cpc_versions\{latest_version}\raw_xml"
    
    if not os.path.exists(raw_xml_dir):
        raise FileNotFoundError(f"Raw XML directory not found: {raw_xml_dir}")
    
    xml_files = [f for f in os.listdir(raw_xml_dir) if f.endswith(".xml")]
    
    if not xml_files:
        print("⚠️ No XML files found to process.")
        return
    
    print(f"🔄 Processing {len(xml_files)} XML files...")
    for xml_file in xml_files:
        xml_path = os.path.join(raw_xml_dir, xml_file)
        convert_xml_to_json(xml_path)
    
    print("🎉 Batch processing complete!")

if __name__ == "__main__":
    if len(sys.argv) == 2:
        input_xml_file = sys.argv[1]
        convert_xml_to_json(input_xml_file)
    else:
        process_all_raw_xml()
