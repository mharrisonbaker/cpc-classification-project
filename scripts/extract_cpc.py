import os
import json
import time
import requests
import zipfile

# Constants
DATA_DIR = "C:\\Development\\cpc-classification-project\\data\\cpc_versions"
CONFIG_PATH = "C:\\Development\\cpc-classification-project\\config\\cpc_version.json"
BULK_DOWNLOAD_URL = "https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk"
SCHEME_ZIP_PATTERN = "CPCSchemeXML"
BASE_URL = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/"


# Download settings
MAX_RETRIES = 5
RETRY_WAIT_TIME = 90  # in seconds
CHUNK_SIZE = 256 * 1024  # 256 KB chunks
TIMEOUT = 600  # 10-minute timeout
MIN_EXPECTED_SIZE_MB = 2

def get_latest_cpc_version():
    """Fetch the latest CPC version by scraping the CPC Bulk Download page."""
    response = requests.get(BULK_DOWNLOAD_URL, timeout=TIMEOUT)
    if response.status_code != 200:
        raise Exception(f"Failed to access CPC bulk page. HTTP Status: {response.status_code}")

    # Find the version number in the page content
    version_str = None
    for line in response.text.splitlines():
        if "CPCSchemeXML" in line and "zip" in line:
            version_str = line.split("CPCSchemeXML")[1][:6]  # Extract YYYYMM
            break

    if not version_str:
        raise Exception("Could not determine the latest CPC version.")

    latest_version = f"{version_str[:4]}_{version_str[4:]}"
    download_url = f"https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCSchemeXML{version_str}.zip"
    
    print(f"🔹 Latest CPC Version: {latest_version}")
    print(f"🔹 Download URL: {download_url}")
    return latest_version, download_url

def download_cpc_zip(version, download_url):
    """Downloads the CPC Scheme ZIP file with retry and resume support."""
    target_dir = os.path.join(DATA_DIR, version)
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, f"CPCSchemeXML{version.replace('_', '')}.zip")

    # Check if already downloaded and valid
    if os.path.exists(zip_path) and os.path.getsize(zip_path) > MIN_EXPECTED_SIZE_MB * 1024 * 1024:
        print(f"✅ ZIP file already exists and looks complete ({os.path.getsize(zip_path) / (1024 * 1024):.2f} MB). Skipping download.")
        return zip_path

    print(f"📥 Attempting download: {download_url} → {zip_path}")

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            response = requests.get(download_url, stream=True, timeout=TIMEOUT)
            if response.status_code != 200:
                raise Exception(f"Failed to download CPC ZIP. HTTP Status: {response.status_code}")

            # Download in chunks with resume support
            with open(zip_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)

            # Check file size after download
            file_size = os.path.getsize(zip_path) / (1024 * 1024)  # Convert to MB
            if file_size < MIN_EXPECTED_SIZE_MB:
                print(f"⚠️ Downloaded file too small ({file_size:.2f} MB). Retrying...")
                os.remove(zip_path)
                attempt += 1
                time.sleep(RETRY_WAIT_TIME)
                continue

            print(f"✅ Download complete: {zip_path} ({file_size:.2f} MB)")
            return zip_path

        except Exception as e:
            print(f"❌ Download failed: {e}")
            attempt += 1
            time.sleep(RETRY_WAIT_TIME)

    raise Exception("❌ Failed to download CPC Scheme ZIP after multiple attempts.")

def extract_cpc_zip(version):
    """Extracts the CPC Scheme XML ZIP file into the correct directories."""
    target_dir = os.path.join(DATA_DIR, version)
    zip_path = os.path.join(target_dir, f"CPCSchemeXML{version.replace('_', '')}.zip")
    extract_dir = os.path.join(target_dir, "raw_xml")

    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"❌ ZIP file not found: {zip_path}")

    print(f"📂 Extracting {zip_path} to {extract_dir}...")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    print(f"✅ Extraction complete for version {version}.")

def update_config(version):
    """Updates config/cpc_version.json with the latest CPC version."""
    config_data = {
        "latest_version": version,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    with open(CONFIG_PATH, "w") as config_file:
        json.dump(config_data, config_file, indent=4)

    print(f"📝 Updated {CONFIG_PATH} with latest CPC version: {version}")

def ensure_cpc_changes_downloaded(version):
    """
    Ensures the CPC Compilation of Changes ZIP is downloaded and extracted.
    """
    changes_dir = os.path.join(DATA_DIR, version, "changes")
    changes_zip_filename = os.path.join(changes_dir, f"Compilation{version.replace('_', '')}.zip")

    # Ensure the changes directory exists
    os.makedirs(changes_dir, exist_ok=True)

    # ✅ Check if ZIP exists before skipping
    if not os.path.exists(changes_zip_filename):
        print(f"⚠️ Compilation of Changes ZIP not found. Downloading...")
        download_cpc_changes_zip(version)

    # ✅ Ensure the extraction runs if files are missing
    extracted_files = os.listdir(changes_dir)
    if not extracted_files or "cpc-compilation" not in str(extracted_files).lower():
        print(f"📂 Extracting Compilation of Changes...")
        extract_cpc_changes_zip(version)  # 🔹 Call the extraction function
    else:
        print(f"✅ Compilation of Changes files already extracted.")


def download_cpc_changes_zip(version):
    """
    Downloads the CPC Compilation of Changes ZIP file with retries and resumption support.
    """
    changes_dir = os.path.join(DATA_DIR, version, "changes")
    zip_filename = f"Compilation{version.replace('_', '')}.zip"
    zip_path = os.path.join(changes_dir, zip_filename)
    
    # Ensure the changes directory exists
    os.makedirs(changes_dir, exist_ok=True)

    # Construct the URL for the changes file
    download_url = f"{BASE_URL}{zip_filename}"
    print(f"📥 Attempting download: {download_url} → {zip_path}")

    # Check if file already exists
    if os.path.exists(zip_path):
        print(f"✅ Compilation of Changes ZIP already exists: {zip_path}")
        return zip_path

    # Download with retries
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(download_url, stream=True, timeout=TIMEOUT)
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)

            print(f"✅ Download complete: {zip_path}")
            return zip_path

        except requests.exceptions.RequestException as e:
            print(f"❌ Download failed: {e}")
            print(f"🔄 Retrying in {RETRY_WAIT_TIME} seconds... (Attempt {attempt}/{MAX_RETRIES})")
            time.sleep(RETRY_WAIT_TIME)

    raise Exception(f"❌ Failed to download Compilation of Changes ZIP after {MAX_RETRIES} attempts.")



def extract_cpc_changes_zip(version):
    """
    Extracts the Compilation of Changes ZIP file into the appropriate directory.
    """
    changes_dir = os.path.join(DATA_DIR, version, "changes")
    zip_filename = os.path.join(changes_dir, f"Compilation{version.replace('_', '')}.zip")

    # Ensure the file exists before attempting extraction
    if not os.path.exists(zip_filename):
        print(f"❌ Error: Compilation of Changes ZIP not found: {zip_filename}")
        return

    print(f"📂 Extracting {zip_filename} → {changes_dir}...")

    try:
        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
            zip_ref.extractall(changes_dir)
        print(f"✅ Compilation of Changes extracted successfully!")
    except Exception as e:
        print(f"❌ Error extracting Compilation of Changes: {e}")



if __name__ == "__main__":
    try:
        latest_version, latest_zip_url = get_latest_cpc_version()
        zip_file = download_cpc_zip(latest_version, latest_zip_url)
        extract_cpc_zip(latest_version)
        ensure_cpc_changes_downloaded(latest_version)  # ✅ Ensure changes file is handled
        update_config(latest_version)
        print("\n🎉 CPC Extraction Process Complete!")
    except Exception as e:
        print(f"❌ Error: {e}")

