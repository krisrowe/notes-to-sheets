"""
Tests using actual sample JSON files to validate the processing pipeline.
"""

import unittest
import json
import os
import sys
import yaml

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from note_processor import process_note


class TestSampleFileProcessing(unittest.TestCase):
    """Test processing using actual sample JSON files."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_dir = os.path.join(os.path.dirname(__file__), '..', 'samples')
        
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
    
    def load_sample_file(self, filename):
        """Load a sample JSON file."""
        filepath = os.path.join(self.sample_dir, filename)
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def test_image_sample_processing(self):
        """Test processing the image sample."""
        note_data = self.load_sample_file('image.json')
        processed, ignore_actions = process_note(note_data, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.title, 'Sample AI Chatbot Conversation')
        self.assertEqual(processed.content, '')  # Empty text content
        self.assertTrue(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 1)
        # No color label since color is DEFAULT
    
    def test_links_sample_processing(self):
        """Test processing the links sample."""
        note_data = self.load_sample_file('links.json')
        processed, ignore_actions = process_note(note_data, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.title, 'Sample Links Collection')
        # Should contain the URLs from textContent (not HTML)
        self.assertIn('https://httpbin.org', processed.content)
        self.assertIn('https://en.wikipedia.org', processed.content)
        self.assertFalse(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 0)
        # No color label since color is DEFAULT
    
    def test_tasks_sample_processing(self):
        """Test processing the tasks sample."""
        note_data = self.load_sample_file('tasks.json')
        processed, ignore_actions = process_note(note_data, self.default_config)
        
        self.assertIsNotNone(processed)
        self.assertEqual(processed.title, 'Sample Tasks Checklist')
        # Should have formatted checklist content
        self.assertIn('☑', processed.content)
        self.assertIn('☐', processed.content)
        self.assertIn('Sample checklist item', processed.content)
        self.assertIn('Another sample item', processed.content)
        self.assertFalse(processed.has_attachments)
        self.assertEqual(processed.attachment_count, 0)
    
    def test_html_content_processing(self):
        """Test HTML content processing with samples."""
        note_data = self.load_sample_file('links.json')  # Use links.json which has HTML content
        
        # Test with ignore action (default)
        processed, ignore_actions = process_note(note_data, self.default_config)
        
        self.assertIsNotNone(processed)
        # Should contain plain text, not HTML tags
        self.assertIn('https://httpbin.org', processed.content)
        self.assertNotIn('<p', processed.content)
        self.assertNotIn('HTML', processed.labels)
        
        # Test with label action
        config = self.default_config.copy()
        config['processing']['html_content'] = 'label'
        
        processed, ignore_actions = process_note(note_data, config)
        
        self.assertIsNotNone(processed)
        # Should contain HTML tags
        self.assertIn('<p', processed.content)  # HTML paragraph tags
        self.assertIn('HTML', processed.labels)
    
    def test_custom_label_processing(self):
        """Test custom label processing with samples."""
        config = self.default_config.copy()
        config['labels']['pinned'] = 'Important'
        config['labels']['shared'] = 'Shared Out'
        
        # Use shared_owned.json which has sharing info
        note_data = self.load_sample_file('shared_owned.json')
        note_data['isPinned'] = True  # Add pinned flag
        
        processed, ignore_actions = process_note(note_data, config)
        
        self.assertIsNotNone(processed)
        self.assertIn('Important', processed.labels)
        self.assertIn('Shared Out', processed.labels)
    
    def test_color_labels_disabled(self):
        """Test color labels disabled with samples."""
        config = self.default_config.copy()
        config['color_label'] = False
        
        note_data = self.load_sample_file('image.json')
        processed, ignore_actions = process_note(note_data, config)
        
        self.assertIsNotNone(processed)
        self.assertNotIn('RED', processed.labels)  # Should not have color label
    
    def test_skip_trashed_with_samples(self):
        """Test skipping trashed notes with samples."""
        config = self.default_config.copy()
        config['processing']['trashed'] = 'skip'
        
        note_data = self.load_sample_file('trashed.json')
        
        processed, ignore_actions = process_note(note_data, config)
        
        self.assertIsNone(processed)  # Should be skipped
    
    def test_skip_archived_with_samples(self):
        """Test skipping archived notes with samples."""
        config = self.default_config.copy()
        config['processing']['archived'] = 'skip'
        
        note_data = self.load_sample_file('archived.json')
        
        processed, ignore_actions = process_note(note_data, config)
        
        self.assertIsNone(processed)  # Should be skipped


if __name__ == '__main__':
    unittest.main() 