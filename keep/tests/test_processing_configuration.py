import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from keep.note_source import KeepNoteSource
from storage.local_source import LocalSourceFileManager
from execution.note import ProcessedNote


class TestProcessingConfiguration(unittest.TestCase):
    """Test all processing configuration options for each source field."""
    
    def setUp(self):
        """Set up test environment with sample files."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.sample_dir = os.path.join(self.test_dir, 'samples')
        os.makedirs(self.sample_dir)
        
        # Create sample files for each field type
        self.create_sample_files()
        
        # Create source manager
        self.source_manager = LocalSourceFileManager(self.sample_dir)
        
        # Don't use schema validation for these tests since we're testing processing logic
        self.schema = None
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def create_sample_files(self):
        """Create sample JSON files for testing each field type."""
        
        # Sample for trashed field
        trashed_note = {
            "title": "Trashed Note",
            "textContent": "This note is in the trash",
            "isTrashed": True,
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for pinned field
        pinned_note = {
            "title": "Pinned Note",
            "textContent": "This note is pinned",
            "isPinned": True,
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for archived field
        archived_note = {
            "title": "Archived Note",
            "textContent": "This note is archived",
            "isArchived": True,
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for shared field - note you own and shared with others
        shared_note = {
            "title": "Shared Note",
            "textContent": "This note is shared",
            "sharees": [{"isOwner": True, "email": "owner@example.com"}],
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for received field - note shared with you by others
        received_note = {
            "title": "Received Note",
            "textContent": "This note was received",
            "sharees": [{"isOwner": False, "email": "other@example.com"}],
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for html_content field
        html_note = {
            "title": "HTML Note",
            "textContent": "This note has <b>HTML</b> content",
            "textContentHtml": "<b>Bold text</b>",
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Sample for color field
        colored_note = {
            "title": "Colored Note",
            "textContent": "This note has a color",
            "color": "RED",
            "userEditedTimestampUsec": 1660824519000000,
            "createdTimestampUsec": 1660824519000000
        }
        
        # Write sample files
        samples = {
            'trashed': trashed_note,
            'pinned': pinned_note,
            'archived': archived_note,
            'shared': shared_note,
            'received': received_note,
            'html': html_note,
            'colored': colored_note
        }
        
        for filename, data in samples.items():
            filepath = os.path.join(self.sample_dir, f'{filename}.json')
            with open(filepath, 'w') as f:
                json.dump(data, f)
    
    def create_config(self, field, setting):
        """Create a configuration with specific field setting."""
        config = {
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
        config['processing'][field] = setting
        return config
    
    def test_trashed_skip_configuration(self):
        """Test trashed field with skip configuration."""
        config = self.create_config('trashed', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('trashed')
        self.assertIsNone(note)
    
    def test_trashed_label_configuration(self):
        """Test trashed field with label configuration."""
        config = self.create_config('trashed', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('trashed')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Trashed Note')
        self.assertIn('Trashed', note.labels)
    
    def test_trashed_error_configuration(self):
        """Test trashed field with error configuration."""
        config = self.create_config('trashed', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('trashed')
    
    def test_trashed_ignore_configuration(self):
        """Test trashed field with ignore configuration."""
        config = self.create_config('trashed', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('trashed')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Trashed Note')
        self.assertEqual(note.labels, '')  # No label added
    
    def test_pinned_skip_configuration(self):
        """Test pinned field with skip configuration."""
        config = self.create_config('pinned', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('pinned')
        self.assertIsNone(note)
    
    def test_pinned_label_configuration(self):
        """Test pinned field with label configuration."""
        config = self.create_config('pinned', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('pinned')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Pinned Note')
        self.assertIn('Pinned', note.labels)
    
    def test_pinned_error_configuration(self):
        """Test pinned field with error configuration."""
        config = self.create_config('pinned', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('pinned')
    
    def test_pinned_ignore_configuration(self):
        """Test pinned field with ignore configuration."""
        config = self.create_config('pinned', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('pinned')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Pinned Note')
        self.assertEqual(note.labels, '')  # No label added
    
    def test_archived_skip_configuration(self):
        """Test archived field with skip configuration."""
        config = self.create_config('archived', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('archived')
        self.assertIsNone(note)
    
    def test_archived_label_configuration(self):
        """Test archived field with label configuration."""
        config = self.create_config('archived', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('archived')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Archived Note')
        self.assertIn('Archived', note.labels)
    
    def test_archived_error_configuration(self):
        """Test archived field with error configuration."""
        config = self.create_config('archived', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('archived')
    
    def test_archived_ignore_configuration(self):
        """Test archived field with ignore configuration."""
        config = self.create_config('archived', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('archived')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Archived Note')
        self.assertEqual(note.labels, '')  # No label added
    
    def test_shared_skip_configuration(self):
        """Test shared field with skip configuration."""
        config = self.create_config('shared', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('shared')
        self.assertIsNone(note)
    
    def test_shared_label_configuration(self):
        """Test shared field with label configuration."""
        config = self.create_config('shared', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('shared')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Shared Note')
        self.assertIn('Shared', note.labels)
    
    def test_shared_error_configuration(self):
        """Test shared field with error configuration."""
        config = self.create_config('shared', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('shared')
    
    def test_shared_ignore_configuration(self):
        """Test shared field with ignore configuration."""
        config = self.create_config('shared', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('shared')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Shared Note')
        self.assertEqual(note.labels, '')  # No label added
    
    def test_received_skip_configuration(self):
        """Test received field with skip configuration."""
        config = self.create_config('received', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('received')
        self.assertIsNone(note)
    
    def test_received_label_configuration(self):
        """Test received field with label configuration."""
        config = self.create_config('received', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('received')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Received Note')
        self.assertIn('Received', note.labels)
    
    def test_received_error_configuration(self):
        """Test received field with error configuration."""
        config = self.create_config('received', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('received')
    
    def test_received_ignore_configuration(self):
        """Test received field with ignore configuration."""
        config = self.create_config('received', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('received')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Received Note')
        self.assertEqual(note.labels, '')  # No label added
    
    def test_html_content_skip_configuration(self):
        """Test html_content field with skip configuration."""
        config = self.create_config('html_content', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('html')
        self.assertIsNone(note)
    
    def test_html_content_label_configuration(self):
        """Test html_content field with label configuration."""
        config = self.create_config('html_content', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('html')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'HTML Note')
        # HTML content should be processed as label or handled according to config
    
    def test_html_content_error_configuration(self):
        """Test html_content field with error configuration."""
        config = self.create_config('html_content', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('html')
    
    def test_html_content_ignore_configuration(self):
        """Test html_content field with ignore configuration."""
        config = self.create_config('html_content', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('html')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'HTML Note')
        # HTML content should be ignored
    
    def test_color_skip_configuration(self):
        """Test color field with skip configuration."""
        config = self.create_config('color', 'skip')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should return None (skipped)
        note = note_source.load_by_filename('colored')
        self.assertIsNone(note)
    
    def test_color_label_configuration(self):
        """Test color field with label configuration."""
        config = self.create_config('color', 'label')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('colored')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Colored Note')
        self.assertIn('Red', note.labels)
    
    def test_color_error_configuration(self):
        """Test color field with error configuration."""
        config = self.create_config('color', 'error')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        # Should raise an exception
        with self.assertRaises(ValueError):
            note_source.load_by_filename('colored')
    
    def test_color_ignore_configuration(self):
        """Test color field with ignore configuration."""
        config = self.create_config('color', 'ignore')
        note_source = KeepNoteSource(self.source_manager, self.schema, config=config)
        
        note = note_source.load_by_filename('colored')
        self.assertIsNotNone(note)
        self.assertIsInstance(note, ProcessedNote)
        self.assertEqual(note.title, 'Colored Note')
        self.assertEqual(note.labels, '')  # No label added


if __name__ == '__main__':
    unittest.main() 