"""Unit tests for CPC XML parser."""

import pytest
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict

from src.pipeline.xml_processor.parser import (
    CPCSchemeParser,
    CPCTitle,
    CPCReference,
    CPCClassification
)

@pytest.fixture
def sample_xml_str():
    """Sample XML string for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <classification-scheme>
        <classification-item>
            <classification-symbol>A01B1/00</classification-symbol>
            <class-title>
                <title-part>
                    <text>Hand tools</text>
                    <CPC-specific-text>
                        <text>for agricultural purposes</text>
                    </CPC-specific-text>
                </title-part>
            </class-title>
            <notes-and-warnings>
                <note>This group covers general-purpose hand tools</note>
                <warning>Special attention required</warning>
            </notes-and-warnings>
            <limiting-references>
                <reference classification-symbol="A01B3/00">Tools for mechanical processing</reference>
            </limiting-references>
            <classification-item>
                <classification-symbol>A01B1/02</classification-symbol>
                <class-title>
                    <title-part>
                        <text>Spades</text>
                        <additional-text type="synonym">Shovels</additional-text>
                    </title-part>
                </class-title>
            </classification-item>
        </classification-item>
    </classification-scheme>
    '''

@pytest.fixture
def parser():
    """Create a parser instance."""
    return CPCSchemeParser()

@pytest.fixture
def xml_file(tmp_path, sample_xml_str):
    """Create a temporary XML file."""
    xml_path = tmp_path / "test.xml"
    xml_path.write_text(sample_xml_str)
    return xml_path

def test_parser_initialization(parser):
    """Test parser initialization and stats."""
    assert isinstance(parser, CPCSchemeParser)
    assert parser.stats["processed_items"] == 0
    assert parser.stats["with_notes"] == 0
    assert parser.stats["with_warnings"] == 0
    assert parser.stats["with_references"] == 0

def test_parse_title(parser):
    """Test parsing of class title."""
    xml_str = '''
    <class-title>
        <title-part>
            <text>Main title text</text>
            <CPC-specific-text>
                <text>CPC specific detail</text>
            </CPC-specific-text>
            <additional-text type="synonym">Synonym text</additional-text>
        </title-part>
    </class-title>
    '''
    element = ET.fromstring(xml_str)
    title = parser._parse_title(element)
    
    assert isinstance(title, CPCTitle)
    assert title.main_text == "Main title text"
    assert title.cpc_specific_text == "CPC specific detail"
    assert title.synonyms == ["Synonym text"]

def test_determine_level(parser):
    """Test classification level determination."""
    test_cases = [
        ("A", "section"),
        ("A01", "class"),
        ("A01B", "subclass"),
        ("A01B1/00", "main-group"),
        ("A01B1/02", "subgroup")
    ]
    
    for symbol, expected_level in test_cases:
        assert parser._determine_level(symbol) == expected_level

def test_parse_references(parser):
    """Test parsing of references."""
    xml_str = '''
    <classification-item>
        <limiting-references>
            <reference classification-symbol="A01B3/00">Test reference</reference>
        </limiting-references>
        <informative-references>
            <reference>Another reference</reference>
        </informative-references>
    </classification-item>
    '''
    element = ET.fromstring(xml_str)
    refs = parser._parse_references(element)
    
    assert len(refs) == 2
    assert isinstance(refs[0], CPCReference)
    assert refs[0].text == "Test reference"
    assert refs[0].symbol == "A01B3/00"
    assert refs[0].type == "limiting"

def test_parse_notes_and_warnings(parser):
    """Test parsing of notes and warnings."""
    xml_str = '''
    <classification-item>
        <notes-and-warnings>
            <note>Test note</note>
            <warning>Test warning</warning>
        </notes-and-warnings>
    </classification-item>
    '''
    element = ET.fromstring(xml_str)
    notes, warnings = parser._parse_notes_and_warnings(element)
    
    assert len(notes) == 1
    assert len(warnings) == 1
    assert notes[0] == "Test note"
    assert warnings[0] == "Test warning"

def test_parse_complete_file(parser, xml_file):
    """Test parsing of a complete XML file."""
    result = parser.parse_file(xml_file)
    
    assert len(result) == 1  # One top-level classification
    top_level = result[0]
    
    assert isinstance(top_level, CPCClassification)
    assert top_level.symbol == "A01B1/00"
    assert top_level.level == "main-group"
    assert len(top_level.children) == 1
    assert top_level.children[0].symbol == "A01B1/02"
    
    # Check stats
    assert parser.stats["processed_items"] >= 2  # Parent + child
    assert parser.stats["with_notes"] >= 1
    assert parser.stats["with_warnings"] >= 1
    assert parser.stats["with_references"] >= 1

def test_to_dict(parser, xml_file):
    """Test conversion of CPCClassification to dictionary."""
    classifications = parser.parse_file(xml_file)
    dict_result = parser.to_dict(classifications[0])
    
    assert isinstance(dict_result, dict)
    assert "symbol" in dict_result
    assert "title" in dict_result
    assert "metadata" in dict_result
    assert "children" in dict_result
    
    # Verify structure
    assert dict_result["symbol"] == "A01B1/00"
    assert "main" in dict_result["title"]
    assert "notes" in dict_result["metadata"]
    assert isinstance(dict_result["children"], list)

def test_error_handling(parser, tmp_path):
    """Test parser error handling with malformed XML."""
    # Create malformed XML file
    bad_xml = tmp_path / "bad.xml"
    bad_xml.write_text('''
    <classification-scheme>
        <classification-item>
            <broken-tag>
    ''')
    
    with pytest.raises(ET.ParseError):
        parser.parse_file(bad_xml)

if __name__ == '__main__':
    pytest.main([__file__])