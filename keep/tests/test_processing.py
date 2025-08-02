#!/usr/bin/env python3
"""
Tests for processing loop behavior.
Tests the execution processor with stubbed source and target objects.
"""

import unittest
from execution.processor import process_notes
from keep.note_source import KeepNoteSource


class StubbedSourceFileManager:
    """Stubbed source file manager for testing."""
    
    def __init__(self, sample_data):
        self.sample_data = sample_data
    
    def list_files(self):
        return [f"{note_id}.json" for note_id in self.sample_data.keys()]
    
    def get_all_note_ids(self):
        return list(self.sample_data.keys())
    
    def get_json_content(self, filename):
        # Extract note_id from filename (remove .json extension)
        note_id = filename.replace('.json', '')
        return self.sample_data.get(note_id)
    
    def list_files(self):
        """Return list of filenames with .json extension."""
        return [f"{note_id}.json" for note_id in self.sample_data.keys()]
    
    def get_session_images(self):
        return set()
    
    def get_image_bytes(self, filename):
        return b'fake_image_data'


class StubbedTarget:
    """Stubbed target for testing."""
    
    def __init__(self):
        self.notes_added = []
        self.attachments_added = []
        self.images_saved = []
    
    def write_notes_and_attachments(self, notes_data, attachments_data):
        self.notes_added.extend(notes_data)
        self.attachments_added.extend(attachments_data)
        return len(notes_data) + len(attachments_data)
    
    def save_image(self, filename, image_bytes):
        self.images_saved.append(filename)
        return True
    
    def get_existing_images(self):
        return set()


class TestProcessing(unittest.TestCase):
    """Test processing loop behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample data for testing
        self.sample_data = {
            'note1': {
                'title': 'Test Note 1',
                'textContent': 'Content 1',
                'createdTimestampUsec': '1660842497197000',
                'color': 'DEFAULT',
                'isTrashed': False,
                'isPinned': False,
                'isArchived': False
            },
            'note2': {
                'title': 'Test Note 2',
                'textContent': 'Content 2',
                'createdTimestampUsec': '1660842497198000',
                'color': 'RED',
                'isTrashed': False,
                'isPinned': True,
                'isArchived': False
            },
            'note3': {
                'title': 'Trashed Note',
                'textContent': 'This should be skipped',
                'createdTimestampUsec': '1660842497199000',
                'color': 'DEFAULT',
                'isTrashed': True,
                'isPinned': False,
                'isArchived': False
            }
        }
        
        # Create stubbed source and target
        self.source = StubbedSourceFileManager(self.sample_data)
        self.target = StubbedTarget()
        
        # Default config
        self.config = {
            'processing': {
                'color': 'label',
                'trashed': 'skip',
                'archived': 'skip',
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
        
        # Create note source with config
        self.note_source = KeepNoteSource(self.source, config=self.config)
    
    def test_processing_summary_counts(self):
        """Test that processing summary contains correct counts."""
        existing_notes = {}
        
        summary = process_notes(
            note_source=self.note_source,
            target=self.target,
            existing_notes=existing_notes,
            config=self.config,
            max_batches=1,
            batch_size=10,
            ignore_errors=False,
            sync_images=False
        )
        
        # Validate summary counts
        self.assertEqual(summary['processed'], 3)  # All 3 notes processed
        self.assertEqual(summary['imported'], 2)   # 2 notes imported (1 skipped due to trashed)
        self.assertEqual(summary['duplicates'], 0)  # No duplicates
        self.assertEqual(summary['errors'], 0)     # No errors
        self.assertEqual(summary['batches_completed'], 1)  # 1 batch completed
    
    def test_processing_with_existing_notes(self):
        """Test processing with existing notes (duplicate detection)."""
        # Mark one note as existing (using the calculated ID from ProcessedNote)
        # The first note "Test Note 1" with created_date "2023-01-01 12:00:00" generates ID "45eeddb2"
        existing_notes = {'45eeddb2': True}
        
        summary = process_notes(
            note_source=self.note_source,
            target=self.target,
            existing_notes=existing_notes,
            config=self.config,
            max_batches=1,
            batch_size=10,
            ignore_errors=False,
            sync_images=False
        )
        
        # Validate summary counts
        self.assertEqual(summary['processed'], 3)  # All 3 notes processed
        self.assertEqual(summary['imported'], 1)   # 1 new note imported
        self.assertEqual(summary['duplicates'], 1)  # 1 duplicate
        self.assertEqual(summary['errors'], 0)     # No errors
    
    def test_processing_with_batch_limits(self):
        """Test processing respects batch limits."""
        existing_notes = {}
        
        summary = process_notes(
            note_source=self.note_source,
            target=self.target,
            existing_notes=existing_notes,
            config=self.config,
            max_batches=1,
            batch_size=1,  # Only 1 note per batch
            ignore_errors=False,
            sync_images=False
        )
        
        # Should only process 1 batch with 1 note
        self.assertEqual(summary['batches_completed'], 1)
        self.assertLessEqual(summary['processed'], 1)
    
    def test_processing_skip_behavior(self):
        """Test that trashed notes are properly skipped."""
        existing_notes = {}
        
        summary = process_notes(
            note_source=self.note_source,
            target=self.target,
            existing_notes=existing_notes,
            config=self.config,
            max_batches=1,
            batch_size=10,
            ignore_errors=False,
            sync_images=False
        )
        
        # Should have 2 imported notes (note3 is trashed and should be skipped)
        self.assertEqual(summary['imported'], 2)
        
        # Verify the correct notes were added
        note_titles = [note['Title'] for note in self.target.notes_added]
        self.assertIn('Test Note 1', note_titles)
        self.assertIn('Test Note 2', note_titles)
        self.assertNotIn('Trashed Note', note_titles)


if __name__ == '__main__':
    unittest.main() 