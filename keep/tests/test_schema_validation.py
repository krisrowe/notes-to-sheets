#!/usr/bin/env python3
"""
Tests for JSON schema validation functionality.
"""

import json
import os
import unittest
from jsonschema import validate, ValidationError

# Import the functions we want to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from importer import load_keep_schema, validate_keep_note


class TestSchemaValidation(unittest.TestCase):
    """Test JSON schema validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.schema = load_keep_schema()
        self.sample_dir = os.path.join(os.path.dirname(__file__), '..', 'samples')
        
    def test_schema_loading(self):
        """Test that the JSON schema loads correctly."""
        self.assertIsNotNone(self.schema)
        self.assertIn('properties', self.schema)
        self.assertIn('required', self.schema)
        self.assertIn('title', self.schema['properties'])
        self.assertIn('createdTimestampUsec', self.schema['properties'])
        
    def test_image_sample_validation(self):
        """Test validation of the image sample file."""
        sample_file = os.path.join(self.sample_dir, 'image.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Image sample validation failed: {e.message}")
            
    def test_links_sample_validation(self):
        """Test validation of the links sample file."""
        sample_file = os.path.join(self.sample_dir, 'links.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Links sample validation failed: {e.message}")
            
    def test_tasks_sample_validation(self):
        """Test validation of the tasks sample file."""
        sample_file = os.path.join(self.sample_dir, 'tasks.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Tasks sample validation failed: {e.message}")
            
    def test_standalone_validation_function(self):
        """Test the standalone validation function."""
        # Test with valid note data
        valid_note = {
            'title': 'Test Note',
            'createdTimestampUsec': 1234567890000000,
            'color': 'DEFAULT',
            'isTrashed': False,
            'isPinned': False,
            'isArchived': False
        }
        
        is_valid, error_msg, error_path, schema_path = validate_keep_note(valid_note)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        self.assertEqual(error_path, [])
        self.assertEqual(schema_path, [])
        
        # Test with invalid note data (missing required field)
        invalid_note = {
            'title': 'Test Note',
            # Missing createdTimestampUsec
            'color': 'DEFAULT'
        }
        
        is_valid, error_msg, error_path, schema_path = validate_keep_note(invalid_note)
        self.assertFalse(is_valid)
        self.assertIn("createdTimestampUsec", error_msg)
        
        # Test with invalid note data (unexpected field)
        invalid_note2 = {
            'title': 'Test Note',
            'createdTimestampUsec': 1234567890000000,
            'unexpectedField': 'should not be here'
        }
        
        is_valid, error_msg, error_path, schema_path = validate_keep_note(invalid_note2)
        self.assertFalse(is_valid)
        self.assertIn("unexpectedField", error_msg)
    
    def test_shared_owned_sample_validation(self):
        """Test validation of the shared owned sample file."""
        sample_file = os.path.join(self.sample_dir, 'shared_owned.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Shared owned sample validation failed: {e.message}")
    
    def test_shared_received_sample_validation(self):
        """Test validation of the shared received sample file."""
        sample_file = os.path.join(self.sample_dir, 'shared_received.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Shared received sample validation failed: {e.message}")
    
    def test_trashed_sample_validation(self):
        """Test validation of the trashed sample file."""
        sample_file = os.path.join(self.sample_dir, 'trashed.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Trashed sample validation failed: {e.message}")
    
    def test_archived_sample_validation(self):
        """Test validation of the archived sample file."""
        sample_file = os.path.join(self.sample_dir, 'archived.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Archived sample validation failed: {e.message}")
    
    def test_with_labels_sample_validation(self):
        """Test validation of the with labels sample file."""
        sample_file = os.path.join(self.sample_dir, 'with_labels.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"With labels sample validation failed: {e.message}")
    
    def test_colored_sample_validation(self):
        """Test validation of the colored sample file."""
        sample_file = os.path.join(self.sample_dir, 'colored.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Colored sample validation failed: {e.message}")
    
    def test_multiple_attachments_sample_validation(self):
        """Test validation of the multiple attachments sample file."""
        sample_file = os.path.join(self.sample_dir, 'multiple_attachments.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Multiple attachments sample validation failed: {e.message}")
    
    def test_minimal_note_sample_validation(self):
        """Test validation of the minimal note sample file."""
        sample_file = os.path.join(self.sample_dir, 'minimal_note.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Minimal note sample validation failed: {e.message}")
    
    def test_pinned_note_sample_validation(self):
        """Test validation of the pinned note sample file."""
        sample_file = os.path.join(self.sample_dir, 'pinned_note.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Pinned note sample validation failed: {e.message}")
    
    def test_missing_timestamps_sample_validation(self):
        """Test validation of the missing timestamps sample file."""
        sample_file = os.path.join(self.sample_dir, 'missing_timestamps.json')
        self.assertTrue(os.path.exists(sample_file), f"Sample file not found: {sample_file}")
        
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        # This should not raise an exception
        try:
            validate(instance=note_data, schema=self.schema)
            self.assertTrue(True)  # Validation passed
        except ValidationError as e:
            self.fail(f"Missing timestamps sample validation failed: {e.message}")


if __name__ == '__main__':
    unittest.main() 