"""Shared fixtures for CPC processing tests."""

import pytest
import json
from pathlib import Path

@pytest.fixture
def test_dirs(tmp_path):
    """Create complete test directory structure."""
    dirs = {
        'root': tmp_path / "cpc_project",
        'data': tmp_path / "cpc_project" / "data",
        'config': tmp_path / "cpc_project" / "config",
        'version': tmp_path / "cpc_project" / "data" / "2025_01",
        'raw_xml': tmp_path / "cpc_project" / "data" / "2025_01" / "raw_xml",
        'processed_json': tmp_path / "cpc_project" / "data" / "2025_01" / "processed_json",
        'expanded_json': tmp_path / "cpc_project" / "data" / "2025_01" / "expanded_json",
        'changes': tmp_path / "cpc_project" / "data" / "2025_01" / "changes",
        'logs': tmp_path / "cpc_project" / "data" / "2025_01" / "logs",
        'cache': tmp_path / "cpc_project" / "cache"
    }
    
    # Create all directories
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

@pytest.fixture
def sample_xml_content():
    """Sample CPC XML content for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <classification-scheme>
        <classification-item>
            <classification-symbol>G06F40/00</classification-symbol>
            <class-title>
                <title-part>
                    <text>Natural language processing</text>
                    <CPC-specific-text>
                        <text>for machine translation</text>
                    </CPC-specific-text>
                </title-part>
            </class-title>
            <notes-and-warnings>
                <note>Important technical note</note>
                <warning>Implementation warning</warning>
            </notes-and-warnings>
            <limiting-references>
                <reference classification-symbol="G06N3/00">
                    Neural network implementations
                </reference>
            </limiting-references>
            <classification-item>
                <classification-symbol>G06F40/20</classification-symbol>
                <class-title>
                    <title-part>
                        <text>Syntax analysis</text>
                        <additional-text type="synonym">Parsing</additional-text>
                    </title-part>
                </class-title>
            </classification-item>
        </classification-item>
    </classification-scheme>
    '''

@pytest.fixture
def sample_json_content():
    """Sample CPC JSON content for testing."""
    return [
        {
            "symbol": "G06F40/00",
            "title": {
                "main": "Natural language processing",
                "cpc_specific": "for machine translation",
                "additional": None,
                "synonyms": None
            },
            "level": "main-group",
            "metadata": {
                "notes": ["Important technical note"],
                "warnings": ["Implementation warning"],
                "references": [
                    {
                        "text": "Neural network implementations",
                        "symbol": "G06N3/00",
                        "type": "limiting"
                    }
                ]
            },
            "children": [
                {
                    "symbol": "G06F40/20",
                    "title": {
                        "main": "Syntax analysis",
                        "cpc_specific": None,
                        "additional": None,
                        "synonyms": ["Parsing"]
                    },
                    "level": "subgroup",
                    "metadata": {
                        "notes": None,
                        "warnings": None,
                        "references": None
                    },
                    "children": []
                }
            ]
        }
    ]

@pytest.fixture
def sample_expanded_content():
    """Sample expanded CPC content with definitions."""
    return [
        {
            "symbol": "G06F40/00",
            "title": {
                "main": "Natural language processing",
                "cpc_specific": "for machine translation"
            },
            "level": "main-group",
            "expanded_definition": "Systems and methods for processing human language texts using computational linguistics. Includes techniques for analyzing, understanding, and generating natural language content.",
            "children": [
                {
                    "symbol": "G06F40/20",
                    "title": {
                        "main": "Syntax analysis",
                        "synonyms": ["Parsing"]
                    },
                    "level": "subgroup",
                    "expanded_definition": "Methods and systems for analyzing the grammatical structure of text, including parsing techniques and syntactic tree generation."
                }
            ]
        }
    ]

@pytest.fixture
def mock_ollama_response():
    """Mock response from Ollama API."""
    return {
        'message': {
            'content': "Technical system for computational processing and analysis of natural language text."
        }
    }

@pytest.fixture
def create_xml_file(test_dirs):
    """Helper to create XML test files."""
    def _create_file(filename: str, content: str):
        file_path = test_dirs['raw_xml'] / filename
        file_path.write_text(content)
        return file_path
    return _create_file

@pytest.fixture
def create_json_file(test_dirs):
    """Helper to create JSON test files."""
    def _create_file(filename: str, content: dict):
        file_path = test_dirs['processed_json'] / filename
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=2)
        return file_path
    return _create_file

@pytest.fixture
def version_config(test_dirs):
    """Create version configuration."""
    config = {
        "latest_version": "2025_01",
        "last_updated": "2025-01-31T12:00:00Z",
        "processing_stats": {
            "total_symbols": 100,
            "processed": 100,
            "failed": 0
        }
    }
    config_file = test_dirs['config'] / "cpc_version.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    return config

@pytest.fixture
def cleanup_test_dirs(test_dirs):
    """Cleanup fixture to remove test directories after tests."""
    yield
    import shutil
    shutil.rmtree(test_dirs['root'])