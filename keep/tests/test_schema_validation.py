#!/usr/bin/env python3
"""
Tests for schema validation behavior.
Validates one known good JSON file and tests various validation scenarios.
"""

import unittest
import os
import json
import copy
from jsonschema import validate, ValidationError
from storage.local_source import LocalSourceFileManager
from keep.note_source import KeepNoteSource


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create source manager pointing to samples directory
        samples_dir = os.path.join(os.path.dirname(__file__), '..', 'samples')
        self.source_manager = LocalSourceFileManager(samples_dir)
        
        # Load schema for validation
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.json')
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        # Create note source with schema validation
        self.note_source = KeepNoteSource(self.source_manager, self.schema)
        
        # Load a known good note for testing
        self.good_note = self.source_manager.get_json_content('minimal_note.json')
    
    def test_known_good_note_validation(self):
        """Test validation of a known good note."""
        # This should pass validation
        validate(instance=self.good_note, schema=self.schema)
        self.assertTrue(True)  # If we get here, validation passed
    
    def test_missing_required_attribute(self):
        """Test validation fails when required attribute is missing."""
        # Remove required 'title' attribute
        bad_note = copy.deepcopy(self.good_note)
        del bad_note['title']
        
        with self.assertRaises(ValidationError) as context:
            validate(instance=bad_note, schema=self.schema)
        
        self.assertIn("'title' is a required property", str(context.exception))
    
    def test_unknown_enum_value(self):
        """Test validation fails when using unknown enum value."""
        # Add color with unknown enum value
        bad_note = copy.deepcopy(self.good_note)
        bad_note['color'] = 'INVALID_COLOR'
        
        with self.assertRaises(ValidationError) as context:
            validate(instance=bad_note, schema=self.schema)
        
        self.assertIn("'INVALID_COLOR' is not one of", str(context.exception))
    
    def test_unexpected_attribute(self):
        """Test validation fails when adding unexpected attribute."""
        # Add unexpected attribute
        bad_note = copy.deepcopy(self.good_note)
        bad_note['unexpectedField'] = 'should not be here'
        
        with self.assertRaises(ValidationError) as context:
            validate(instance=bad_note, schema=self.schema)
        
        self.assertIn("Additional properties are not allowed", str(context.exception))


if __name__ == '__main__':
    unittest.main() 