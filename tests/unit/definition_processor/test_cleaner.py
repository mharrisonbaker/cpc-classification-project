# tests/unit/definition_processor/test_cleaner.py

import pytest
from src.pipeline.definition_processor.cleaner import DefinitionCleaner

@pytest.fixture
def cleaner():
    return DefinitionCleaner()

def test_clean_definition_removes_cpc_preamble(cleaner):
    text = "The CPC classification symbol G01H1/14 relates to electrical systems."
    cleaned = cleaner.clean_definition(text)
    assert cleaned == "Electrical systems."
    
def test_clean_definition_removes_symbol_title_preamble(cleaner):
    text = "Symbol: G01H1/12 Title: Frequency Expanded Definition: This classification encompasses..."
    cleaned = cleaner.clean_definition(text)
    assert not cleaned.startswith("Symbol:")
    
def test_clean_definition_preserves_content(cleaner):
    original = "The classification encompasses methods for testing materials under stress."
    cleaned = cleaner.clean_definition(original)
    assert "testing materials under stress" in cleaned
    
def test_clean_definition_handles_empty_input(cleaner):
    assert cleaner.clean_definition("") == ""
    assert cleaner.clean_definition(None) is None
    
def test_clean_definition_ensures_proper_capitalization(cleaner):
    text = "the classification involves testing."
    cleaned = cleaner.clean_definition(text)
    assert cleaned[0].isupper()
    
def test_clean_definition_ensures_proper_punctuation(cleaner):
    text = "The classification describes testing"
    cleaned = cleaner.clean_definition(text)
    assert cleaned.endswith(".")
    
def test_process_json_handles_nested_structure(cleaner):
    data = {
        "symbol": "G01H",
        "expanded_definition": "The CPC classification covers testing.",
        "children": [
            {
                "symbol": "G01H1/00",
                "expanded_definition": "This classification involves methods."
            }
        ]
    }
    processed = cleaner.process_json(data)
    assert "The CPC classification" not in processed["expanded_definition"]
    assert "This classification" not in processed["children"][0]["expanded_definition"]
    
def test_validate_cleaning_checks_content_preservation(cleaner):
    original = "The classification encompasses important testing methods for materials."
    cleaned = cleaner.clean_definition(original)
    assert cleaner.validate_cleaning(original, cleaned)
    
def test_validate_cleaning_detects_excessive_removal(cleaner):
    original = "A very long technical description " * 20
    cleaned = "Short text"
    assert not cleaner.validate_cleaning(original, cleaned)
    
def test_get_version_dirs_finds_valid_directories(cleaner, tmp_path):
    # Create test directory structure
    (tmp_path / "2025_01").mkdir()
    (tmp_path / "latest").mkdir()
    (tmp_path / "invalid").mkdir()
    
    version_dirs = cleaner.get_version_dirs(tmp_path)
    assert len(version_dirs) == 2
    assert any(d.name == "2025_01" for d in version_dirs)
    assert any(d.name == "latest" for d in version_dirs)