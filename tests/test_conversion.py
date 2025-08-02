#!/usr/bin/env python3
"""
Tests for note conversion logic.
Validates that note sources correctly convert raw data into canonical ProcessedNote format.
"""

import unittest
import json
import os
import tempfile
from pathlib import Path
from execution.note import ProcessedNote
from keep.note_source import KeepNoteSource
from storage.local_source import LocalSourceFileManager


class TestNoteConversion(unittest.TestCase):
    """Test note conversion from raw source data to canonical ProcessedNote format."""
    
    def setUp(self):
        """Set up test directories and paths."""
        self.samples_dir = Path('keep/samples')
        self.canonical_dir = Path('tests/canonical-notes')
    
    def _create_test_config(self):
        """Create the standard test configuration used across all tests."""
        return {
            'processing': {
                'color': 'label',
                'trashed': 'skip',
                'archived': 'skip',
                'pinned': 'label',
                'html_content': 'ignore',
                'shared': 'label',
                'received': 'label'
            },
            'labels': {
                'trashed': 'Trashed',
                'pinned': 'Pinned',
                'archived': 'Archived',
                'shared': 'Shared',
                'received': 'Received'
            }
        }
    
    def test_keep_basic_note_conversion(self):
        """Test Keep source converts basic note correctly."""
        # Load sample data
        source_manager = LocalSourceFileManager(str(self.samples_dir))
        config = self._create_test_config()
        
        note_source = KeepNoteSource(source_manager, config=config)
        processed_note = note_source.load_by_filename("minimal_note")
        
        # Load expected data from JSON
        expected_dict = json.load(open(self.canonical_dir / "minimal-note-expected.json"))
        
        # Validate conversion
        self.assertIsNotNone(processed_note)
        
        # Get actual stored fields from ProcessedNote
        actual_dict = processed_note.__dict__.copy()
        
        # Compare stored fields (including note_id)
        self.assertDictEqual(expected_dict, actual_dict)
    
    def test_keep_labeled_note_conversion(self):
        """Test Keep source converts labeled note with HTML correctly."""
        # Load sample data
        source_manager = LocalSourceFileManager(str(self.samples_dir))
        config = self._create_test_config()
        
        note_source = KeepNoteSource(source_manager, config=config)
        processed_note = note_source.load_by_filename("pinned_note")
        
        # Load expected data from JSON
        expected_dict = json.load(open(self.canonical_dir / "pinned-note-expected.json"))
        
        self.assertIsNotNone(processed_note)
        
        # Get actual stored fields from ProcessedNote
        actual_dict = processed_note.__dict__.copy()
        
        # Compare stored fields (including note_id)
        self.assertDictEqual(expected_dict, actual_dict)
    
    def test_keep_attachment_note_conversion(self):
        """Test Keep source converts note with attachments correctly."""
        # Load sample data
        source_manager = LocalSourceFileManager(str(self.samples_dir))
        config = self._create_test_config()
        
        note_source = KeepNoteSource(source_manager, config=config)
        processed_note = note_source.load_by_filename("multiple_attachments")
        
        # Load expected data from JSON
        expected_dict = json.load(open(self.canonical_dir / "multiple-attachments-expected.json"))
        
        self.assertIsNotNone(processed_note)
        
        # Get actual stored fields from ProcessedNote
        actual_dict = processed_note.__dict__.copy()
        
        # Compare stored fields (including note_id)
        self.assertDictEqual(expected_dict, actual_dict)
        
        # Validate attachment structure
        for attachment in processed_note.attachments:
            self.assertIn('Type', attachment)
            self.assertIn('File', attachment)
            self.assertIn('Title', attachment)
            self.assertIn('note_id', attachment)
            self.assertEqual(attachment['note_id'], processed_note.note_id)
    
    def test_keep_skipped_note_conversion(self):
        """Test Keep source skips trashed notes correctly."""
        # Load sample data
        source_manager = LocalSourceFileManager(str(self.samples_dir))
        config = self._create_test_config()
        
        note_source = KeepNoteSource(source_manager, config=config)
        processed_note = note_source.load_by_filename("trashed")
        
        # Trashed notes should be skipped (return None)
        self.assertIsNone(processed_note)
    
    def test_note_id_consistency(self):
        """Test that note_id generation is consistent for the same input."""
        from execution.note import calculate_note_id
        
        # Test with same inputs multiple times
        title = "Test Note"
        created_date = "2022-08-18 12:08:17"
        
        id1 = calculate_note_id(title, created_date)
        id2 = calculate_note_id(title, created_date)
        id3 = calculate_note_id(title, created_date)
        
        # All should be the same
        self.assertEqual(id1, id2)
        self.assertEqual(id2, id3)
        self.assertEqual(id1, id3)
        
        # Test with different inputs
        different_title = "Different Note"
        different_date = "2022-08-19 12:08:17"
        
        id4 = calculate_note_id(different_title, created_date)
        id5 = calculate_note_id(title, different_date)
        
        # Should be different
        self.assertNotEqual(id1, id4)
        self.assertNotEqual(id1, id5)
        self.assertNotEqual(id4, id5)


if __name__ == '__main__':
    unittest.main() 