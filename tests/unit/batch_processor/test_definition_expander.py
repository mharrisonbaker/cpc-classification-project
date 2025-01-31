"""Unit tests for CPC definition expander."""

import pytest
from unittest.mock import Mock, patch
import json
from pathlib import Path

from src.pipeline.batch_processor.definition_expander import (
    CPCDefinitionExpander,
    ProcessingStats
)

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    dirs = {
        'cache': tmp_path / "cache",
        'logs': tmp_path / "logs"
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True)
    return dirs

@pytest.fixture
def expander(temp_dirs):
    """Create a definition expander instance."""
    return CPCDefinitionExpander(
        model_name="phi4:14b",
        max_workers=2
    )

@pytest.fixture
def sample_classification():
    """Create a sample classification for testing."""
    return {
        "symbol": "G06F40/00",
        "title": "Natural language processing",
        "metadata": {
            "notes": ["Important technical note"],
            "references": [{"text": "See ML", "symbol": "G06N20/00"}]
        }
    }

def test_expander_initialization(expander):
    """Test expander initialization."""
    assert isinstance(expander, CPCDefinitionExpander)
    assert expander.model == "phi4:14b"
    assert expander.max_workers == 2
    assert expander.stats.total_processed == 0

@patch('ollama.chat')
def test_get_definition(mock_chat, expander, sample_classification):
    """Test definition generation."""
    # Mock Ollama response
    mock_chat.return_value = {
        'message': {
            'content': "Technical definition of NLP systems."
        }
    }

    definition = expander.get_definition(
        sample_classification["symbol"],
        sample_classification["title"],
        sample_classification["metadata"]
    )

    assert isinstance(definition, str)
    assert len(definition) > 0
    assert expander.stats.successful > 0

def test_validation_patterns(expander):
    """Test definition validation patterns."""
    # Test various definition formats
    test_cases = [
        ("This category includes text processing", False),  # Unwanted start
        ("A technical system for processing", True),        # Valid start
        ("Short", False),                                  # Too short
        ("A" * 1000, False),                              # Too long
        ("Advanced computational system for analyzing text structures.", True)  # Valid
    ]

    for definition, expected_valid in test_cases:
        is_valid, _ = expander._validate_definition(definition)
        assert is_valid == expected_valid

def test_format_definition(expander):
    """Test definition formatting."""
    test_cases = [
        (
            "definition: technical content",
            "Technical content."
        ),
        (
            "TECHNICAL CONTENT",
            "Technical content."
        ),
        (
            "technical content without period",
            "Technical content without period."
        )
    ]

    for input_text, expected in test_cases:
        formatted = expander._format_definition(input_text)
        assert formatted == expected

@patch('ollama.chat')
def test_definition_caching(mock_chat, expander, sample_classification):
    """Test caching of generated definitions."""
    mock_chat.return_value = {
        'message': {
            'content': "Technical definition."
        }
    }

    # First call - should use Ollama
    definition1 = expander.get_definition(
        sample_classification["symbol"],
        sample_classification["title"],
        sample_classification["metadata"]
    )

    # Second call - should use cache
    definition2 = expander.get_definition(
        sample_classification["symbol"],
        sample_classification["title"],
        sample_classification["metadata"]
    )

    assert definition1 == definition2
    assert mock_chat.call_count == 1  # Called only once
    assert expander.stats.cache_hits == 1

@patch('ollama.chat')
def test_error_handling(mock_chat, expander, sample_classification):
    """Test handling of generation errors."""
    # Mock error response
    mock_chat.side_effect = Exception("API Error")

    definition = expander.get_definition(
        sample_classification["symbol"],
        sample_classification["title"],
        sample_classification["metadata"]
    )

    assert "Error" in definition
    assert expander.stats.failed > 0

def test_prompt_construction(expander, sample_classification):
    """Test construction of prompts."""
    prompt = expander._construct_prompt(
        sample_classification["symbol"],
        sample_classification["title"],
        sample_classification["metadata"]
    )

    assert sample_classification["symbol"] in prompt
    assert sample_classification["title"] in prompt
    assert "Requirements:" in prompt
    assert "technical" in prompt.lower()

def test_processing_stats(expander):
    """Test processing statistics tracking."""
    # Create some activity
    with patch('ollama.chat') as mock_chat:
        mock_chat.return_value = {'message': {'content': "Definition"}}
        
        # Successful generation
        expander.get_definition("G06F40/00", "Title", {})
        
        # Failed generation
        mock_chat.side_effect = Exception("Error")
        expander.get_definition("G06F40/10", "Title", {})

    stats = expander.stats
    assert stats.total_processed == 2
    assert stats.successful == 1
    assert stats.failed == 1
    assert isinstance(stats.avg_response_time, float)

@pytest.mark.parametrize("input_text", [
    "This category includes...",
    "This classification covers...",
    "Referring to systems that...",
    "These technologies involve..."
])
def test_unwanted_phrases(expander, input_text):
    """Test detection of unwanted phrases."""
    is_valid, message = expander._validate_definition(input_text)
    assert not is_valid
    assert "unwanted phrase" in message.lower()

def test_technical_term_requirement(expander):
    """Test requirement for technical terms."""
    non_technical = "A simple process for doing things."
    technical = "A computational system for processing data structures."
    
    is_valid, _ = expander._validate_definition(non_technical)
    assert not is_valid
    
    is_valid, _ = expander._validate_definition(technical)
    assert is_valid

if __name__ == '__main__':
    pytest.main([__file__])