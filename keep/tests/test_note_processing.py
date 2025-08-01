"""
Tests for note processing functionality.
Validates the transformation of raw JSON note data into canonical ProcessedNote objects.
"""

import unittest
import json
import os
import sys
import yaml
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from note_processor import ProcessedNote, process_note, format_checklist_items, generate_appsheet_id


class TestProcessedNote(unittest.TestCase):
    """Test the ProcessedNote class."""
    
    def test_processed_note_creation(self):
        """Test creating a ProcessedNote object."""
        note = ProcessedNote(
            note_id="abc123",
            title="Test Note",
            content="Test content",
            labels="Test, Label",
            created_date="2024-01-01 12:00:00",
            modified_date="2024-01-02 12:00:00",
            has_attachments=True,
            attachment_count=2
        )
        
        self.assertEqual(note.note_id, "abc123")
        self.assertEqual(note.title, "Test Note")
        self.assertEqual(note.content, "Test content")
        self.assertEqual(note.labels, "Test, Label")
        self.assertEqual(note.has_attachments, True)
        self.assertEqual(note.attachment_count, 2)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        note = ProcessedNote(
            note_id="abc123",
            title="Test Note",
            content="Test content",
            labels="Test, Label",
            created_date="2024-01-01 12:00:00",
            modified_date="2024-01-02 12:00:00",
            has_attachments=True,
            attachment_count=2
        )
        
        expected = {
            'ID': 'abc123',
            'Title': 'Test Note',
            'Content': 'Test content',
            'Labels': 'Test, Label',
            'Created Date': '2024-01-01 12:00:00',
            'Modified Date': '2024-01-02 12:00:00',
            'Has Attachments': 'Yes',
            'Attachment Count': 2
        }
        
        self.assertEqual(note.to_dict(), expected)
    
    def test_equality(self):
        """Test equality comparison."""
        note1 = ProcessedNote(
            note_id="abc123",
            title="Test Note",
            content="Test content",
            labels="Test",
            created_date="2024-01-01 12:00:00",
            modified_date="2024-01-02 12:00:00"
        )
        
        note2 = ProcessedNote(
            note_id="abc123",
            title="Test Note",
            content="Test content",
            labels="Test",
            created_date="2024-01-01 12:00:00",
            modified_date="2024-01-02 12:00:00"
        )
        
        note3 = ProcessedNote(
            note_id="def456",
            title="Different Note",
            content="Different content",
            labels="Different",
            created_date="2024-01-01 12:00:00",
            modified_date="2024-01-02 12:00:00"
        )
        
        self.assertEqual(note1, note2)
        self.assertNotEqual(note1, note3)


class TestNoteProcessing(unittest.TestCase):
    """Test the note processing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Load only the labels from config.yaml, not the processing settings
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
        try:
            with open(config_path, 'r') as f:
                actual_config = yaml.safe_load(f)
                # Use only the labels section, create our own processing defaults
                self.default_config = {
                    'processing': {
                        'color': 'label',
                        'trashed': 'label',
                        'archived': 'label',
                        'pinned': 'label',
                        'html_content': 'ignore',
                        'shared': 'label'
                    },
                    'labels': actual_config.get('labels', {
                        'trashed': 'Trashed',
                        'pinned': 'Pinned',
                        'archived': 'Archived',
                        'shared': 'Shared',
                        'received': 'Received'
                    })
                }
        except FileNotFoundError:
            # Fallback to default config if file not found
            self.default_config = {
                'processing': {
                    'color': 'label',
                    'trashed': 'label',
                    'archived': 'label',
                    'pinned': 'label',
                    'html_content': 'ignore',
                    'shared': 'label'
                },
                'labels': {
                    'trashed': 'Trashed',
                    'pinned': 'Pinned',
                    'archived': 'Archived',
                    'shared': 'Shared',
                    'received': 'Received'
                }
            }
        
        self.sample_note = {
            'title': 'Test Note',
            'textContent': 'This is a test note',
            'textContentHtml': '<p>This is a test note</p>',
            'color': 'DEFAULT',
            'isTrashed': False,
            'isPinned': False,
            'isArchived': False,
            'createdTimestampUsec': '1704067200000000',  # 2024-01-01 12:00:00 UTC
            'userEditedTimestampUsec': '1704153600000000',  # 2024-01-02 12:00:00 UTC
            'labels': [{'name': 'Test'}],
            'attachments': []
        }
    
    def test_basic_note_processing(self):
        """Test basic note processing with default config."""
        processed, ignore_actions = process_note(self.sample_note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.title, 'Test Note')
        self.assertEqual(processed.content, 'This is a test note')
        self.assertEqual(processed.labels, 'Test')
        # Don't test exact timestamp format due to timezone differences
        self.assertIsInstance(processed.created_date, str)
        self.assertIsInstance(processed.modified_date, str)
        self.assertFalse(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 0)
    
    def test_html_content_processing(self):
        """Test HTML content processing."""
        # Test with ignore action (default)
        processed, ignore_actions = process_note(self.sample_note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.content, 'This is a test note')  # Should use textContent
        self.assertNotIn('HTML', processed.labels)
        
        # Test with label action
        config = self.default_config.copy()
        config['processing']['html_content'] = 'label'
        
        processed, ignore_actions = process_note(self.sample_note, config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.content, '<p>This is a test note</p>')
        self.assertIn('HTML', processed.labels)
    
    def test_status_labels(self):
        """Test status label processing."""
        note = self.sample_note.copy()
        note['isTrashed'] = True
        note['isPinned'] = True
        note['isArchived'] = True
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Trashed', processed.labels)
        self.assertIn('Pinned', processed.labels)
        self.assertIn('Archived', processed.labels)
        self.assertIn('Test', processed.labels)
    
    def test_custom_status_labels(self):
        """Test custom status label names."""
        config = self.default_config.copy()
        config['labels']['trashed'] = 'Deleted'
        config['labels']['pinned'] = 'Important'
        config['labels']['archived'] = 'Old'
        
        note = self.sample_note.copy()
        note['isTrashed'] = True
        note['isPinned'] = True
        note['isArchived'] = True
        
        processed, ignore_actions = process_note(note, config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Deleted', processed.labels)
        self.assertIn('Important', processed.labels)
        self.assertIn('Old', processed.labels)
    
    def test_color_labels(self):
        """Test color label processing."""
        note = self.sample_note.copy()
        note['color'] = 'RED'
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('RED', processed.labels)
    
    def test_color_labels_disabled(self):
        """Test color labels when disabled."""
        config = self.default_config.copy()
        config['processing']['color'] = 'ignore'
        
        note = self.sample_note.copy()
        note['color'] = 'RED'
        
        processed, ignore_actions = process_note(note, config)
        
        self.assertIsNotNone(processed)
        self.assertNotIn('RED', processed.labels)
    
    def test_sharing_labels_owned(self):
        """Test sharing labels for owned notes."""
        with open('samples/shared_owned.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Shared', processed.labels)
        self.assertNotIn('Received', processed.labels)
    
    def test_sharing_labels_received(self):
        """Test sharing labels for received notes."""
        with open('samples/shared_received.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Received', processed.labels)
        self.assertNotIn('Shared', processed.labels)
    
    def test_custom_sharing_labels(self):
        """Test custom sharing label names."""
        config = self.default_config.copy()
        config['labels']['received'] = 'Shared With Me'
        config['labels']['shared'] = 'Shared Out'
        
        with open('samples/shared_owned.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Shared Out', processed.labels)
    
    def test_skip_trashed(self):
        """Test skipping trashed notes."""
        config = self.default_config.copy()
        config['processing']['trashed'] = 'skip'
        
        with open('samples/trashed.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, config)
        
        self.assertIsNone(processed)
    
    def test_skip_archived(self):
        """Test skipping archived notes."""
        config = self.default_config.copy()
        config['processing']['archived'] = 'skip'
        
        with open('samples/archived.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, config)
        
        self.assertIsNone(processed)
        
        # Test that default config (archived: "label") adds the label
        with open('samples/archived.json', 'r') as f:
            note = json.load(f)
        
        # Create a fresh config with archived: "label"
        fresh_config = self.default_config.copy()
        fresh_config['processing']['archived'] = 'label'
        
        processed, ignore_actions = process_note(note, fresh_config)
        self.assertIsNotNone(processed)
        self.assertIn(self.default_config['labels']['archived'], processed.labels)
    
    def test_attachments_processing(self):
        """Test attachment processing."""
        with open('samples/multiple_attachments.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertTrue(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 3)
    
    def test_checklist_processing(self):
        """Test checklist processing."""
        with open('samples/tasks.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        # Should have formatted checklist content from tasks.json
        self.assertIn('☑', processed.content)
        self.assertIn('☐', processed.content)
        self.assertIn('Sample checklist item', processed.content)
    
    def test_empty_checklist(self):
        """Test empty checklist processing."""
        # Use a note without listContent field (like image.json)
        with open('samples/image.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        # Should have the original text content when no checklist
        self.assertEqual(processed.content, '')
    
    def test_missing_timestamps(self):
        """Test processing with missing userEditedTimestampUsec."""
        with open('samples/missing_timestamps.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        # Should have created_date since createdTimestampUsec is present
        self.assertIsInstance(processed.created_date, str)
        self.assertGreater(len(processed.created_date), 0)
        # Should have empty modified_date since userEditedTimestampUsec is missing
        self.assertEqual(processed.modified_date, '')
    
    def test_existing_labels_processing(self):
        """Test processing notes with existing labels."""
        with open('samples/with_labels.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Work', processed.labels)
        self.assertIn('Important', processed.labels)
        self.assertIn('Project', processed.labels)
    
    def test_color_labels_processing(self):
        """Test processing notes with non-DEFAULT colors."""
        with open('samples/colored.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertIn('RED', processed.labels)
    
    def test_missing_attachments_field(self):
        """Test processing notes without attachments field."""
        with open('samples/links.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertFalse(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 0)
    
    def test_processing_actions_error(self):
        """Test error processing actions."""
        # Test color error action
        config = self.default_config.copy()
        config['processing']['color'] = 'error'
        
        note = self.sample_note.copy()
        note['color'] = 'RED'
        
        with self.assertRaises(ValueError):
            process_note(note, config)
        
        # Test HTML content error action
        config = self.default_config.copy()
        config['processing']['html_content'] = 'error'
        
        with self.assertRaises(ValueError):
            process_note(self.sample_note, config)
        
        # Test trashed error action
        config = self.default_config.copy()
        config['processing']['trashed'] = 'error'
        
        note = self.sample_note.copy()
        note['isTrashed'] = True
        
        with self.assertRaises(ValueError):
            process_note(note, config)
        
        # Test archived error action
        config = self.default_config.copy()
        config['processing']['archived'] = 'error'
        
        note = self.sample_note.copy()
        note['isArchived'] = True
        
        with self.assertRaises(ValueError):
            process_note(note, config)
        
        # Test pinned error action
        config = self.default_config.copy()
        config['processing']['pinned'] = 'error'
        
        note = self.sample_note.copy()
        note['isPinned'] = True
        
        with self.assertRaises(ValueError):
            process_note(note, config)
        
        # Test shared error action
        config = self.default_config.copy()
        config['processing']['shared'] = 'error'
        
        # Use a sample with sharing info
        with open('samples/shared_owned.json', 'r') as f:
            note = json.load(f)
        
        with self.assertRaises(ValueError):
            process_note(note, config)
    
    def test_processing_actions_skip(self):
        """Test skip processing actions."""
        # Test color skip action
        config = self.default_config.copy()
        config['processing']['color'] = 'skip'
        
        note = self.sample_note.copy()
        note['color'] = 'RED'
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNone(processed)
        
        # Test HTML content skip action
        config = self.default_config.copy()
        config['processing']['html_content'] = 'skip'
        
        processed, ignore_actions = process_note(self.sample_note, config)
        self.assertIsNone(processed)
        
        # Test trashed skip action
        config = self.default_config.copy()
        config['processing']['trashed'] = 'skip'
        
        note = self.sample_note.copy()
        note['isTrashed'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNone(processed)
        
        # Test archived skip action
        config = self.default_config.copy()
        config['processing']['archived'] = 'skip'
        
        note = self.sample_note.copy()
        note['isArchived'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNone(processed)
        
        # Test pinned skip action
        config = self.default_config.copy()
        config['processing']['pinned'] = 'skip'
        
        note = self.sample_note.copy()
        note['isPinned'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNone(processed)
        
        # Test shared skip action
        config = self.default_config.copy()
        config['processing']['shared'] = 'skip'
        
        # Use a sample with sharing info
        with open('samples/shared_owned.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNone(processed)
    
    def test_processing_actions_ignore(self):
        """Test ignore processing actions."""
        # Test color ignore action
        config = self.default_config.copy()
        config['processing']['color'] = 'ignore'
        
        note = self.sample_note.copy()
        note['color'] = 'RED'
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNotNone(processed)
        self.assertNotIn('RED', processed.labels)
        
        # Test HTML content ignore action
        config = self.default_config.copy()
        config['processing']['html_content'] = 'ignore'
        
        processed, ignore_actions = process_note(self.sample_note, config)
        self.assertIsNotNone(processed)
        self.assertEqual(processed.content, 'This is a test note')  # Should use textContent
        self.assertNotIn('HTML', processed.labels)
        
        # Test trashed ignore action
        config = self.default_config.copy()
        config['processing']['trashed'] = 'ignore'
        
        note = self.sample_note.copy()
        note['isTrashed'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNotNone(processed)
        self.assertNotIn('Trashed', processed.labels)
        
        # Test archived ignore action
        config = self.default_config.copy()
        config['processing']['archived'] = 'ignore'
        
        note = self.sample_note.copy()
        note['isArchived'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNotNone(processed)
        self.assertNotIn('Archived', processed.labels)
        
        # Test pinned ignore action
        config = self.default_config.copy()
        config['processing']['pinned'] = 'ignore'
        
        note = self.sample_note.copy()
        note['isPinned'] = True
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNotNone(processed)
        self.assertNotIn('Pinned', processed.labels)
        
        # Test shared ignore action
        config = self.default_config.copy()
        config['processing']['shared'] = 'ignore'
        
        # Use a sample with sharing info
        with open('samples/shared_owned.json', 'r') as f:
            note = json.load(f)
        
        processed, ignore_actions = process_note(note, config)
        self.assertIsNotNone(processed)
        self.assertNotIn('Shared', processed.labels)
        self.assertNotIn('Received', processed.labels)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_format_checklist_items(self):
        """Test checklist formatting."""
        items = [
            {'text': 'Item 1', 'isChecked': True},
            {'text': 'Item 2', 'isChecked': False},
            {'text': 'Item 3', 'isChecked': True}
        ]
        
        result = format_checklist_items(items)
        expected = "☑ Item 1\n☐ Item 2\n☑ Item 3"
        
        self.assertEqual(result, expected)
    
    def test_format_empty_checklist(self):
        """Test empty checklist formatting."""
        result = format_checklist_items([])
        self.assertEqual(result, "")
    
    def test_generate_appsheet_id(self):
        """Test ID generation."""
        title = "Test Note"
        timestamp = "1704067200000000"
        
        id1 = generate_appsheet_id(title, timestamp)
        id2 = generate_appsheet_id(title, timestamp)
        
        # Should be consistent
        self.assertEqual(id1, id2)
        
        # Should be 8 characters
        self.assertEqual(len(id1), 8)
        
        # Should be different for different inputs
        id3 = generate_appsheet_id("Different Note", timestamp)
        self.assertNotEqual(id1, id3)


if __name__ == '__main__':
    unittest.main() 