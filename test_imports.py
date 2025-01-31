# test_imports.py

def test_pipeline_imports():
    """Test that all pipeline imports work correctly."""
    try:
        # Test top-level imports
        from src.pipeline import (
            extract_cpc_zip,
            get_latest_cpc_version,
            download_cpc_zip,
            convert_xml_to_json,
            parse_cpc_scheme,
            CPCDefinitionExpander
        )
        print("✅ Top-level pipeline imports successful")
    except ImportError as e:
        print(f"❌ Top-level import failed: {e}")
        return False

    # Test specific module imports
    try:
        from src.pipeline.xml_processor import (
            extract_cpc_zip,
            get_latest_cpc_version,
            download_cpc_zip,
            ensure_cpc_changes_downloaded
        )
        print("✅ XML processor imports successful")
    except ImportError as e:
        print(f"❌ XML processor import failed: {e}")
        return False

    try:
        from src.pipeline.json_processor import (
            convert_xml_to_json,
            parse_cpc_scheme,
            get_title_text,
            parse_classification_item
        )
        print("✅ JSON processor imports successful")
    except ImportError as e:
        print(f"❌ JSON processor import failed: {e}")
        return False

    try:
        from src.pipeline.batch_processor import (
            CPCDefinitionExpander,
            ProcessingStats
        )
        print("✅ Batch processor imports successful")
    except ImportError as e:
        print(f"❌ Batch processor import failed: {e}")
        return False

    return True

def verify_cross_module_imports():
    """Test imports between modules work correctly."""
    try:
        # Try to create instances/use functions
        from src.pipeline import CPCDefinitionExpander
        expander = CPCDefinitionExpander(model_name="phi4:14b")
        print("✅ Can instantiate CPCDefinitionExpander")
        
        from src.pipeline import convert_xml_to_json, parse_cpc_scheme
        print("✅ Can import processing functions")
        
        return True
    except Exception as e:
        print(f"❌ Cross-module verification failed: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Testing Import Structure ===\n")
    
    if test_pipeline_imports() and verify_cross_module_imports():
        print("\n✅ All import tests passed!")
    else:
        print("\n❌ Some import tests failed. Check the errors above.")