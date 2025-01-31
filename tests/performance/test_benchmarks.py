"""Performance benchmark tests for CPC processing pipeline."""

import pytest
import time
import psutil
import json
import os
from pathlib import Path
from unittest.mock import patch
import logging
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from src.pipeline.xml_processor import CPCExtractor
from src.pipeline.json_processor import CPCJsonConverter
from src.pipeline.batch_processor import BatchProcessor

# Set up logging for benchmarks
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BenchmarkStats:
    """Track performance statistics."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_samples = []
        self.cpu_samples = []
        self.file_counts = {}
        self.processing_times = {}
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.memory_samples = []
        self.cpu_samples = []
    
    def sample_metrics(self):
        """Sample current memory and CPU usage."""
        process = psutil.Process()
        self.memory_samples.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_samples.append(process.cpu_percent())
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.end_time = time.time()
    
    def get_stats(self):
        """Get performance statistics."""
        return {
            "execution_time": self.end_time - self.start_time,
            "avg_memory_mb": np.mean(self.memory_samples),
            "max_memory_mb": max(self.memory_samples),
            "avg_cpu_percent": np.mean(self.cpu_samples),
            "file_counts": self.file_counts,
            "processing_times": self.processing_times
        }

@pytest.fixture
def benchmark_stats():
    """Create benchmark stats tracker."""
    return BenchmarkStats()

@pytest.fixture
def large_xml_dataset(test_dirs, sample_xml_content):
    """Create a large dataset for benchmarking."""
    xml_dir = test_dirs['raw_xml']
    file_counts = [10, 50, 100]  # Different dataset sizes
    
    datasets = {}
    for count in file_counts:
        # Create directory for this dataset
        dataset_dir = xml_dir / f"dataset_{count}"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Create XML files
        for i in range(count):
            xml_file = dataset_dir / f"section_{i}.xml"
            xml_file.write_text(sample_xml_content)
        
        datasets[count] = dataset_dir
    
    return datasets

def monitor_task(func, stats):
    """Decorator to monitor task performance."""
    def wrapper(*args, **kwargs):
        stats.start_monitoring()
        
        # Start monitoring thread
        def monitor():
            while time.time() < stats.start_time + 3600:  # Monitor for up to 1 hour
                stats.sample_metrics()
                time.sleep(1)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            monitor_future = executor.submit(monitor)
            try:
                result = func(*args, **kwargs)
                stats.stop_monitoring()
                return result
            finally:
                monitor_future.cancel()
    
    return wrapper

def test_xml_processing_scaling(large_xml_dataset, benchmark_stats):
    """Test XML processing performance with different dataset sizes."""
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    
    for count, dataset_dir in large_xml_dataset.items():
        logger.info(f"Testing XML processing with {count} files...")
        
        @monitor_task(stats=benchmark_stats)
        def process_dataset():
            return converter.convert_directory(str(dataset_dir), "2025_01")
        
        json_dir, stats = process_dataset()
        
        benchmark_stats.file_counts[count] = len(list(Path(json_dir).glob("*.json")))
        benchmark_stats.processing_times[count] = benchmark_stats.end_time - benchmark_stats.start_time
        
        logger.info(f"Processed {count} files in {benchmark_stats.processing_times[count]:.2f} seconds")
        logger.info(f"Average memory usage: {np.mean(benchmark_stats.memory_samples):.2f} MB")

def test_definition_expansion_performance(test_dirs, benchmark_stats, mock_ollama_response):
    """Test definition expansion performance."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = mock_ollama_response
        
        processor = BatchProcessor("2025_01", str(test_dirs['data']))
        
        @monitor_task(stats=benchmark_stats)
        def expand_definitions():
            return processor.process_directory(test_dirs['processed_json'])
        
        expand_definitions()
        
        stats = processor.get_processing_stats()
        benchmark_stats.file_counts["expanded"] = stats["total_symbols"]
        
        logger.info(f"Definition Expansion Performance:")
        logger.info(f"Total symbols processed: {stats['total_symbols']}")
        logger.info(f"Execution time: {benchmark_stats.end_time - benchmark_stats.start_time:.2f} seconds")
        logger.info(f"Average memory usage: {np.mean(benchmark_stats.memory_samples):.2f} MB")

def test_concurrent_processing_scaling(test_dirs, benchmark_stats, mock_ollama_response):
    """Test performance with different numbers of worker threads."""
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = mock_ollama_response
        
        worker_counts = [2, 4, 8]  # Test different thread counts
        
        for workers in worker_counts:
            processor = BatchProcessor("2025_01", str(test_dirs['data']))
            processor.max_workers = workers
            
            @monitor_task(stats=benchmark_stats)
            def process_with_workers():
                return processor.process_directory(test_dirs['processed_json'])
            
            process_with_workers()
            
            benchmark_stats.processing_times[f"workers_{workers}"] = (
                benchmark_stats.end_time - benchmark_stats.start_time
            )
            
            logger.info(f"Performance with {workers} workers:")
            logger.info(f"Execution time: {benchmark_stats.processing_times[f'workers_{workers}']:.2f} seconds")
            logger.info(f"Average memory: {np.mean(benchmark_stats.memory_samples):.2f} MB")

def test_memory_usage_large_files(test_dirs, benchmark_stats, sample_xml_content):
    """Test memory usage with large files."""
    # Create a large XML file
    large_xml = test_dirs['raw_xml'] / "large.xml"
    with open(large_xml, 'w') as f:
        # Write header
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<classification-scheme>\n')
        
        # Write many classification items
        for i in range(1000):  # Create 1000 classifications
            f.write(sample_xml_content)
        
        # Write footer
        f.write('</classification-scheme>')
    
    converter = CPCJsonConverter(output_dir=str(test_dirs['processed_json']))
    
    @monitor_task(stats=benchmark_stats)
    def process_large_file():
        return converter.convert_file(str(large_xml), str(test_dirs['processed_json'] / "large.json"))
    
    process_large_file()
    
    logger.info("Large File Processing Performance:")
    logger.info(f"Peak memory usage: {max(benchmark_stats.memory_samples):.2f} MB")
    logger.info(f"Average memory usage: {np.mean(benchmark_stats.memory_samples):.2f} MB")

def save_benchmark_results(benchmark_stats, test_dirs):
    """Save benchmark results to file."""
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_info": {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total / (1024 * 1024 * 1024)  # GB
        },
        "performance_metrics": benchmark_stats.get_stats()
    }
    
    results_file = test_dirs['logs'] / f"benchmark_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    pytest.main([__file__])