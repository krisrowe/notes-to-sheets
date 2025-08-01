#!/usr/bin/env python3
"""
Tests for label processing functionality.
"""

import unittest
import json


class TestLabelProcessing(unittest.TestCase):
    """Test label processing functionality."""
    
    def test_basic_labels(self):
        """Test basic label extraction from note data."""
        with open('samples/with_labels.json', 'r') as f:
            note_data = json.load(f)
        
        # Simulate the label processing logic from the main script
        label_names = [label['name'] for label in note_data.get('labels', [])]
        labels = " , ".join(label_names)
        
        self.assertEqual(labels, "Work , Important , Project")
        
    def test_status_labels(self):
        """Test conversion of boolean flags to status labels."""
        with open('samples/pinned_note.json', 'r') as f:
            note_data = json.load(f)
        
        # Simulate the status label processing logic
        label_names = []
        
        if note_data.get('isTrashed', False):
            label_names.append('Trashed')
        if note_data.get('isPinned', False):
            label_names.append('Pinned')
        if note_data.get('isArchived', False):
            label_names.append('Archived')
            
        labels = " , ".join(label_names)
        
        self.assertEqual(labels, "Pinned")
        
    def test_color_label(self):
        """Test color conversion to label."""
        with open('samples/colored.json', 'r') as f:
            note_data = json.load(f)
        
        # Simulate the color label processing logic
        label_names = []
        color = note_data.get('color', 'DEFAULT')
        if color and color != 'DEFAULT':
            label_names.append(color)
            
        labels = " , ".join(label_names)
        
        self.assertEqual(labels, "RED")
        
    def test_default_color_no_label(self):
        """Test that DEFAULT color doesn't create a label."""
        with open('samples/image.json', 'r') as f:
            note_data = json.load(f)
        
        # Simulate the color label processing logic
        label_names = []
        color = note_data.get('color', 'DEFAULT')
        if color and color != 'DEFAULT':
            label_names.append(color)
            
        labels = " , ".join(label_names)
        
        self.assertEqual(labels, "")
        
    def test_combined_labels(self):
        """Test combination of all label types."""
        # Create a combined scenario by loading with_labels.json and modifying it
        with open('samples/with_labels.json', 'r') as f:
            note_data = json.load(f)
        
        # Add pinned status and red color
        note_data['isPinned'] = True
        note_data['color'] = 'RED'
        
        # Simulate the complete label processing logic
        label_names = [label['name'] for label in note_data.get('labels', [])]
        
        if note_data.get('isTrashed', False):
            label_names.append('Trashed')
        if note_data.get('isPinned', False):
            label_names.append('Pinned')
        if note_data.get('isArchived', False):
            label_names.append('Archived')
            
        color = note_data.get('color', 'DEFAULT')
        if color and color != 'DEFAULT':
            label_names.append(color)
            
        labels = " , ".join(label_names)
        
        self.assertEqual(labels, "Work , Important , Project , Pinned , RED")


if __name__ == '__main__':
    unittest.main() 