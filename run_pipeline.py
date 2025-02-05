"""Main entry point for CPC processing pipeline."""

from src.pipeline.xml_processor import CPCExtractor
from src.pipeline.json_processor import CPCJsonConverter
from src.pipeline.batch_processor import BatchProcessor
import logging
import urllib3
import os
import signal


urllib3.disable_warnings()
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_interrupt_handling():
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal. Cleaning up...")
        raise KeyboardInterrupt()

    if os.name == 'nt':  # Windows
        signal.signal(signal.SIGINT, signal_handler)
    else:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def run_pipeline():
    try:
        # 1. Extract XML
        logger.info("Starting XML extraction...")
        extractor = CPCExtractor()
        version, stats = extractor.process_latest_version()
        logger.info(f"XML extraction complete for version {version}")
        
        # 2. Convert to JSON
        logger.info("Starting JSON conversion...")
        converter = CPCJsonConverter()
        json_dir, conv_stats = converter.convert_directory(
            f"data/cpc_versions/{version}/raw_xml",
            version
        )
        logger.info("JSON conversion complete")
        
        # 3. Generate definitions
        logger.info("Starting definition expansion...")
        processor = BatchProcessor(version, "data/cpc_versions")
        processor.process_directory(json_dir)
        logger.info("Definition expansion complete")
        
        logger.info("🎉 Pipeline complete!")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    setup_interrupt_handling()
    run_pipeline()