#!/usr/bin/env python3
"""
Tests for sample file structure validation.
"""

import json
import os
import unittest


class TestSampleFileContents(unittest.TestCase):
    """Test that sample files contain expected content."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_dir = os.path.join(os.path.dirname(__file__), '..', 'samples')
        
    def test_image_sample_structure(self):
        """Test that image sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'image.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('attachments', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertEqual(len(note_data['attachments']), 1)
        self.assertTrue(note_data['attachments'][0]['mimetype'].startswith('image/'))
        
    def test_links_sample_structure(self):
        """Test that links sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'links.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('annotations', note_data)
        self.assertIn('textContent', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['annotations']), 0)
        
        # All annotations should be WEBLINK, SHEETS, DOCS, or GMAIL type
        for annotation in note_data['annotations']:
            self.assertIn(annotation['source'], ['WEBLINK', 'SHEETS', 'DOCS', 'GMAIL'])
            
    def test_tasks_sample_structure(self):
        """Test that tasks sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'tasks.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('listContent', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['listContent']), 0)
        
        # All list items should have required fields
        for item in note_data['listContent']:
            self.assertIn('text', item)
            self.assertIn('isChecked', item)
    
    def test_shared_owned_sample_structure(self):
        """Test that shared owned sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'shared_owned.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('sharees', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['sharees']), 0)
        
        # Should have both owner and non-owner sharees
        has_owner = False
        has_non_owner = False
        for sharee in note_data['sharees']:
            if sharee['isOwner']:
                has_owner = True
            else:
                has_non_owner = True
        
        self.assertTrue(has_owner, "Should have at least one owner")
        self.assertTrue(has_non_owner, "Should have at least one non-owner")
    
    def test_shared_received_sample_structure(self):
        """Test that shared received sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'shared_received.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('sharees', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['sharees']), 0)
        
        # Should only have non-owner sharees (received notes)
        for sharee in note_data['sharees']:
            self.assertFalse(sharee['isOwner'], "Received notes should not have owner sharees")
    
    def test_trashed_sample_structure(self):
        """Test that trashed sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'trashed.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('isTrashed', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertTrue(note_data['isTrashed'], "Should be marked as trashed")
    
    def test_archived_sample_structure(self):
        """Test that archived sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'archived.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('isArchived', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertTrue(note_data['isArchived'], "Should be marked as archived")
    
    def test_with_labels_sample_structure(self):
        """Test that with labels sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'with_labels.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('labels', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['labels']), 0)
        
        # All labels should have name field
        for label in note_data['labels']:
            self.assertIn('name', label)
    
    def test_colored_sample_structure(self):
        """Test that colored sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'colored.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('color', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertEqual(note_data['color'], 'RED', "Should be red colored")
    
    def test_multiple_attachments_sample_structure(self):
        """Test that multiple attachments sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'multiple_attachments.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('attachments', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertGreater(len(note_data['attachments']), 1, "Should have multiple attachments")
        
        # All attachments should have required fields
        for attachment in note_data['attachments']:
            self.assertIn('filePath', attachment)
            self.assertIn('mimetype', attachment)
            self.assertTrue(attachment['mimetype'].startswith('image/'), "Should be image mimetype")
    
    def test_minimal_note_sample_structure(self):
        """Test that minimal note sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'minimal_note.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        # Should only have required fields
        self.assertEqual(len(note_data), 2, "Should only have title and createdTimestampUsec")
    
    def test_pinned_note_sample_structure(self):
        """Test that pinned note sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'pinned_note.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('isPinned', note_data)
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        self.assertTrue(note_data['isPinned'], "Should be marked as pinned")
    
    def test_missing_timestamps_sample_structure(self):
        """Test that missing timestamps sample has expected structure."""
        sample_file = os.path.join(self.sample_dir, 'missing_timestamps.json')
        with open(sample_file, 'r') as f:
            note_data = json.load(f)
            
        self.assertIn('title', note_data)
        self.assertIn('createdTimestampUsec', note_data)
        # Should not have userEditedTimestampUsec
        self.assertNotIn('userEditedTimestampUsec', note_data)
        # Should only have required fields
        self.assertEqual(len(note_data), 2, "Should only have title and createdTimestampUsec")


if __name__ == '__main__':
    unittest.main() 