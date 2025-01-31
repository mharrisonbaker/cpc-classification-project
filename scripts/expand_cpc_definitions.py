import os
import json
import time
import re
import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
import ollama


LLM_MODEL = "phi4:14b"
MAX_RETRIES = 3  # How many times to retry if a bad phrase is detected
LOG_DIR = "logs"  # Directory for logs
TIMING_LOG_FILE = os.path.join(LOG_DIR, "timing_log.csv")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error_log.csv")
EXPANDED_OUTPUT_DIR = "data/latest/expanded_json"
MAX_GLOBAL_API_ERRORS = 10  # Stop if we hit 10 API failures
global_api_failure_count = 0  # Track API errors across all calls


# Ensure required directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EXPANDED_OUTPUT_DIR, exist_ok=True)

# List of unwanted phrases
BAD_START_PHRASES = [
    "This category encompasses",
    "This category pertains to",
    "This classification includes",
    "This section describes",
    "This group covers",
    "This domain consists of"
]

def get_available_vram():
    """
    Checks available VRAM using `nvidia-smi` and returns an estimated MAX_WORKERS.
    """
    try:
        output = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], 
                                capture_output=True, text=True)
        free_vram = int(output.stdout.strip().split("\n")[0])  # Get free VRAM in MB
        print(f"🟢 Available VRAM: {free_vram}MB")

        # Estimate how many workers we can run safely
        if free_vram > 12000:  # If >12GB free, use 4 workers
            return 4
        elif free_vram > 8000:  # If >8GB free, use 3 workers
            return 3
        else:  # If low VRAM, use 2 workers
            return 2
    except Exception as e:
        print(f"⚠️ Could not determine VRAM: {e}")
        return 2  # Default to a safe number

MAX_WORKERS = get_available_vram()  # Dynamically set based on VRAM

def is_bad_generation(response):
    """
    Checks if the response starts with an unwanted phrase.
    """
    for phrase in BAD_START_PHRASES:
        if response.lower().startswith(phrase.lower()):
            return True
    return False

def log_inference(symbol, title, elapsed_time):
    """
    Logs execution time per symbol for performance analysis.
    """
    file_exists = os.path.exists(TIMING_LOG_FILE)

    with open(TIMING_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["Symbol", "Title", "Response Time (s)"])
        
        writer.writerow([symbol, title, elapsed_time])

def log_error(symbol, title, error_msg):
    """
    Logs errors separately to an error log CSV.
    """
    file_exists = os.path.exists(ERROR_LOG_FILE)

    with open(ERROR_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["Symbol", "Title", "Error Message"])
        
        writer.writerow([symbol, title, error_msg])

def get_expanded_definition(symbol, title, parent_title=""):
    """
    Uses Ollama to generate CPC definitions, filtering out bad responses.
    """
    global global_api_failure_count  # Track errors globally

    system_prompt = (
        "You are an expert in CPC classifications. "
        "Expand classification titles into concise, informative definitions. "
        "Do NOT begin with phrases like 'This category pertains to' or 'This classification encompasses'. "
        "Start directly with the definition."
    )

    user_prompt = f"""
    Expand the following CPC classification **without introductory statements**:

    - **Code**: {symbol}
    - **Title**: {title}
    """
    if parent_title:
        user_prompt += f"\n- **Parent Category**: {parent_title}"

    user_prompt += "\n\nRespond immediately with the definition."

    attempt = 0
    while attempt < MAX_RETRIES:
        if global_api_failure_count >= MAX_GLOBAL_API_ERRORS:
            print(f"🚨 Too many API failures ({global_api_failure_count}). Stopping execution!")
            exit(1)  # Exit the script

        try:
            start_time = time.time()
            response = ollama.chat(model=LLM_MODEL, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            definition = response['message']['content'].strip()
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 2)

            if is_bad_generation(definition):
                print(f"❌ Bad generation detected for {symbol}. Retrying... ({attempt + 1}/{MAX_RETRIES})")
                attempt += 1
                continue

            print(f"✅ Processed: {symbol} (Time: {elapsed_time}s)")
            log_inference(symbol, title, elapsed_time)
            return definition

        except Exception as e:
            global_api_failure_count += 1  # Increment the global failure count
            print(f"⚠️ API Error for {symbol}. Retrying in 5 seconds... ({attempt + 1}/{MAX_RETRIES})")
            time.sleep(5)
            attempt += 1

    print(f"❌ Max retries reached for {symbol}. Skipping.")
    log_error(symbol, title, "API failure after 3 retries")
    return "Definition could not be generated."


def process_hierarchy_parallel(data):
    """
    Processes CPC definitions in parallel using ThreadPoolExecutor.
    """
    if isinstance(data, dict):  # Handle single dictionary case
        data = [data]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_expanded_definition, item['symbol'], item['title'], item.get('parent_title', "")): item 
                   for item in data if 'symbol' in item and 'title' in item}

        for future in futures:
            item = futures[future]
            item['expanded_definition'] = future.result()

        for item in data:
            if 'children' in item and isinstance(item['children'], list):
                process_hierarchy_parallel(item['children'])

def expand_definitions(input_file, output_file):
    """
    Loads JSON, processes CPC definitions in parallel, and saves output.
    """
    print(f"📂 Processing input file: {input_file}")

    if not os.path.exists(input_file):
        print(f"❌ ERROR: Input file not found: {input_file}")
        return
    
    with open(input_file, 'r') as f:
        data = json.load(f)

    if not data:
        print(f"⚠️ WARNING: No data found in {input_file}.")
        return

    print(f"🔄 Processing {len(data)} classification items...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_expanded_definition, item['symbol'], item['title'], item.get('parent_title', "")): item 
                   for item in data if 'symbol' in item and 'title' in item}

        for future in futures:
            item = futures[future]
            try:
                item['expanded_definition'] = future.result()
            except Exception as e:
                print(f"❌ Error processing {item['symbol']}: {e}")

    print(f"📦 Saving expanded definitions to {output_file}")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n🎉 Processing complete! Expanded definitions saved to {output_file}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Expand CPC definitions using an LLM.")
    parser.add_argument("input_file", type=str, help="Path to the JSON input file.")
    parser.add_argument("output_file", type=str, help="Path to the expanded JSON output file.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    
    args = parser.parse_args()

    # Ensure required directories exist
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(EXPANDED_OUTPUT_DIR, exist_ok=True)

    print(f"📂 Processing: {args.input_file} → {args.output_file}")
    
    expand_definitions(args.input_file, args.output_file)

    print(f"✅ Expansion complete. Output saved to {args.output_file}")
