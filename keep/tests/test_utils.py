#!/usr/bin/env python3
"""
Tests for utility functions.
"""

import unittest
import sys
import os

# Import the functions we want to test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from note_processor import generate_appsheet_id, format_checklist_items


class TestIDGeneration(unittest.TestCase):
    """Test ID generation functionality."""
    
    def test_id_consistency(self):
        """Test that the same input always generates the same ID."""
        title = "Test Note"
        timestamp = 1234567890000000
        
        id1 = generate_appsheet_id(title, timestamp)
        id2 = generate_appsheet_id(title, timestamp)
        
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 8)  # Should be 8 characters
        
    def test_id_uniqueness(self):
        """Test that different inputs generate different IDs."""
        title1 = "Test Note 1"
        title2 = "Test Note 2"
        timestamp = 1234567890000000
        
        id1 = generate_appsheet_id(title1, timestamp)
        id2 = generate_appsheet_id(title2, timestamp)
        
        self.assertNotEqual(id1, id2)
        
    def test_id_format(self):
        """Test that IDs are hexadecimal strings."""
        title = "Test Note"
        timestamp = 1234567890000000
        
        note_id = generate_appsheet_id(title, timestamp)
        
        # Should be 8 characters long
        self.assertEqual(len(note_id), 8)
        
        # Should be hexadecimal
        try:
            int(note_id, 16)
        except ValueError:
            self.fail("Generated ID is not a valid hexadecimal string")


class TestChecklistFormatting(unittest.TestCase):
    """Test checklist formatting functionality."""
    
    def test_empty_checklist(self):
        """Test formatting of empty checklist."""
        list_content = []
        result = format_checklist_items(list_content)
        self.assertEqual(result, "")
        
    def test_single_unchecked_item(self):
        """Test formatting of single unchecked item."""
        list_content = [
            {'text': 'Buy groceries', 'isChecked': False}
        ]
        result = format_checklist_items(list_content)
        self.assertEqual(result, "☐ Buy groceries")
        
    def test_single_checked_item(self):
        """Test formatting of single checked item."""
        list_content = [
            {'text': 'Buy groceries', 'isChecked': True}
        ]
        result = format_checklist_items(list_content)
        self.assertEqual(result, "☑ Buy groceries")
        
    def test_multiple_items(self):
        """Test formatting of multiple items."""
        list_content = [
            {'text': 'Buy groceries', 'isChecked': False},
            {'text': 'Do laundry', 'isChecked': True},
            {'text': 'Call mom', 'isChecked': False}
        ]
        result = format_checklist_items(list_content)
        expected = "☐ Buy groceries\n☑ Do laundry\n☐ Call mom"
        self.assertEqual(result, expected)
        
    def test_items_with_html(self):
        """Test that HTML content is ignored (we only use text)."""
        list_content = [
            {
                'text': 'Buy groceries',
                'textHtml': '<p>Buy groceries</p>',
                'isChecked': False
            }
        ]
        result = format_checklist_items(list_content)
        self.assertEqual(result, "☐ Buy groceries")


if __name__ == '__main__':
    unittest.main() 