"""JSON schema definitions for CPC data."""

CPC_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "pattern": "^[A-HY][0-9]{2}[A-Z]{1}\\d+/\\d+$|^[A-HY][0-9]{2}[A-Z]{1}\\d+$|^[A-HY][0-9]{2}[A-Z]{1}$|^[A-HY][0-9]{2}$|^[A-HY]$"
        },
        "title": {
            "type": "object",
            "properties": {
                "main": {"type": "string"},
                "cpc_specific": {"type": ["string", "null"]},
                "additional": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "synonyms": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                }
            },
            "required": ["main"]
        },
        "level": {
            "type": "string",
            "enum": ["section", "class", "subclass", "group", "subgroup", "main-group"]
        },
        "parent_symbol": {
            "type": ["string", "null"]
        },
        "metadata": {
            "type": "object",
            "properties": {
                "notes": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "warnings": {
                    "type": ["array", "null"],
                    "items": {"type": "string"}
                },
                "references": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "symbol": {"type": ["string", "null"]},
                            "type": {
                                "type": "string",
                                "enum": ["informative", "limiting", "application"]
                            }
                        },
                        "required": ["text", "type"]
                    }
                }
            }
        },
        "children": {
            "type": ["array", "null"],
            "items": {"$ref": "#"}
        },
        "expanded_definition": {
            "type": ["string", "null"]
        }
    },
    "required": ["symbol", "title", "level"]
}

# Schema for processing statistics
STATS_SCHEMA = {
    "type": "object",
    "properties": {
        "processed_items": {"type": "integer"},
        "with_notes": {"type": "integer"},
        "with_warnings": {"type": "integer"},
        "with_references": {"type": "integer"},
        "with_definitions": {"type": "integer"},
        "processing_time": {"type": "number"},
        "timestamp": {"type": "string", "format": "date-time"}
    },
    "required": ["processed_items", "timestamp"]
}

# Schema for version tracking
VERSION_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "pattern": "^\\d{4}_\\d{2}$"},
        "processed_date": {"type": "string", "format": "date-time"},
        "stats": {"$ref": "#/definitions/stats"},
        "source_files": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["version", "processed_date"],
    "definitions": {
        "stats": STATS_SCHEMA
    }
}