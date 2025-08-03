"""
Unit tests for the categorization service using CSV data source.
"""
import unittest
import os
import tempfile
import shutil
import csv
from unittest.mock import Mock, patch
from categorization.categorization_service import CategorizationService
from categorization.data_sources.csv_source import CSVDataSource
from categorization.gemini_client import GeminiCategorizer
from categorization.yaml_config import YAMLConfig


class TestCategorizationService(unittest.TestCase):
    """Test cases for the categorization service."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock YAML config that returns our test directory
        self.mock_yaml_config = Mock(spec=YAMLConfig)
        self.mock_yaml_config.get_csv_data_dir.return_value = self.test_dir
        self.mock_yaml_config.get_csv_source_file.return_value = "notes"
        self.mock_yaml_config.get_csv_output_file.return_value = "labeled_notes"
        self.mock_yaml_config.get_csv_rules_file.return_value = "label"
        self.mock_yaml_config.get_label_filter.return_value = None
        
        # Create CSV data source with mock config
        self.csv_source = CSVDataSource(self.mock_yaml_config)
        
        # Create mock Gemini categorizer
        self.mock_categorizer = Mock(spec=GeminiCategorizer)
        
        # Create mock rules manager
        self.mock_rules_manager = Mock()
        
        # Create categorization service
        self.service = CategorizationService(self.csv_source, self.mock_categorizer, self.mock_rules_manager, self.mock_yaml_config)
        
        # Sample test data
        self.test_notes = [
            {
                'id': 'test001',
                'title': 'Grocery Shopping',
                'content': 'Need to buy milk eggs bread and apples for the week'
            },
            {
                'id': 'test002',
                'title': 'Team Meeting Notes',
                'content': 'Discussed Q4 goals and project timeline with Sarah and Mike'
            },
            {
                'id': 'test003',
                'title': 'Workout Plan',
                'content': 'Monday - chest and triceps Tuesday - back and biceps Wednesday - legs'
            }
        ]
        
        # Expected categorization results
        self.expected_results = [
            {'note_id': 'test001', 'labels': 'Shopping'},
            {'note_id': 'test002', 'labels': 'Work'},
            {'note_id': 'test003', 'labels': 'Health'}
        ]
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
    
    def test_categorize_notes_success(self):
        """Test successful note categorization."""
        # Set up CSV data
        self.csv_source.write_csv_file('Note', self.test_notes)
        
        # Mock Gemini categorizer response
        self.mock_categorizer.categorize_notes.return_value = self.expected_results
        
        # Mock rules manager response
        self.mock_rules_manager.get_rules.return_value = 'Test rules'
        
        # Run categorization
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes',
            limit=None
        )
        
        # Verify results
        self.assertEqual(result['total_notes'], 3)
        self.assertEqual(result['categorized_notes'], 3)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(len(result['results']), 3)
        
        # Verify Gemini categorizer was called correctly
        self.mock_categorizer.categorize_notes.assert_called_once()
        call_args = self.mock_categorizer.categorize_notes.call_args[0]
        notes_arg, rules_arg = call_args
        
        self.assertEqual(len(notes_arg), 3)
        self.assertEqual(notes_arg[0]['id'], 'test001')
        self.assertEqual(notes_arg[0]['title'], 'Grocery Shopping')
        self.assertEqual(rules_arg, 'Test rules')
        
        # Verify output table was saved
        output_table = self.csv_source.get_table('categorized_notes')
        self.assertEqual(len(output_table), 3)
        self.assertEqual(output_table.data[0]['Note ID'], 'test001')
        self.assertEqual(output_table.data[0]['Labels'], 'Shopping')
    
    def test_categorize_notes_with_limit(self):
        """Test note categorization with limit."""
        # Set up CSV data
        self.csv_source.write_csv_file('Note', self.test_notes)
        
        # Mock Gemini categorizer response (only first 2 notes)
        limited_results = self.expected_results[:2]
        self.mock_categorizer.categorize_notes.return_value = limited_results
        
        # Mock rules manager response
        self.mock_rules_manager.get_rules.return_value = 'Test rules'
        
        # Run categorization with limit
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes',
            limit=2
        )
        
        # Verify results
        self.assertEqual(result['total_notes'], 2)
        self.assertEqual(result['categorized_notes'], 2)
        self.assertEqual(result['errors'], 0)
        
        # Verify only 2 notes were processed
        call_args = self.mock_categorizer.categorize_notes.call_args[0]
        notes_arg = call_args[0]
        self.assertEqual(len(notes_arg), 2)
    
    def test_categorize_notes_with_errors(self):
        """Test note categorization with some errors."""
        # Set up CSV data
        self.csv_source.write_csv_file('Note', self.test_notes)
        
        # Mock Gemini categorizer response with errors
        error_results = [
            {'note_id': 'test001', 'labels': 'Shopping'},
            {'note_id': 'test002', 'labels': 'ERROR: Failed to categorize'},
            {'note_id': 'test003', 'labels': 'Health'}
        ]
        self.mock_categorizer.categorize_notes.return_value = error_results
        
        # Mock rules manager response
        self.mock_rules_manager.get_rules.return_value = 'Test rules'
        
        # Run categorization
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes'
        )
        
        # Verify results
        self.assertEqual(result['total_notes'], 3)
        self.assertEqual(result['categorized_notes'], 2)  # 2 successful
        self.assertEqual(result['errors'], 1)  # 1 error
    
    def test_categorize_empty_table(self):
        """Test categorization with empty source table."""
        # Set up empty CSV data - need at least headers for CSV to be valid
        empty_data = []  # Empty list means no data rows
        self.csv_source.write_csv_file('Note', empty_data)
        
        # Create the actual empty CSV file with headers
        csv_path = os.path.join(self.test_dir, 'Note.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'title', 'content'])  # Headers only, no data
        
        # Mock rules manager response
        self.mock_rules_manager.get_rules.return_value = 'Test rules'
        
        # Run categorization
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes'
        )
        
        # Verify results
        self.assertEqual(result['total_notes'], 0)
        self.assertEqual(result['categorized_notes'], 0)
        self.assertEqual(result['errors'], 0)
        
        # Verify Gemini categorizer was not called
        self.mock_categorizer.categorize_notes.assert_not_called()
    
    def test_list_available_tables(self):
        """Test listing available tables."""
        # Set up CSV data
        self.csv_source.write_csv_file('Note', self.test_notes)
        self.csv_source.write_csv_file('Other', [{'id': '1', 'data': 'test'}])
        
        # List tables
        tables = self.service.list_available_tables()
        
        # Verify results
        self.assertIn('Note', tables)
        self.assertIn('Other', tables)
    
    def test_field_value_extraction(self):
        """Test field value extraction with different column names."""
        # Test data with different column names
        test_data = [
            {
                'ID': 'test001',  # Different case
                'Title': 'Test Note',  # Different case
                'Body': 'Test content'  # Different field name
            }
        ]
        
        self.csv_source.write_csv_file('Note', test_data)
        self.mock_categorizer.categorize_notes.return_value = [
            {'note_id': 'test001', 'labels': 'Test'}
        ]
        
        # Mock rules manager response
        self.mock_rules_manager.get_rules.return_value = 'Test rules'
        
        # Run categorization
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes'
        )
        
        # Verify the service correctly extracted fields despite different names
        call_args = self.mock_categorizer.categorize_notes.call_args[0]
        notes_arg = call_args[0]
        
        self.assertEqual(notes_arg[0]['id'], 'test001')
        self.assertEqual(notes_arg[0]['title'], 'Test Note')
        self.assertEqual(notes_arg[0]['content'], 'Test content')


class TestCSVDataSource(unittest.TestCase):
    """Test cases for the CSV data source."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock YAML config that returns our test directory
        self.mock_yaml_config = Mock(spec=YAMLConfig)
        self.mock_yaml_config.get_csv_data_dir.return_value = self.test_dir
        self.mock_yaml_config.get_csv_source_file.return_value = "notes"
        self.mock_yaml_config.get_csv_output_file.return_value = "labeled_notes"
        self.mock_yaml_config.get_csv_rules_file.return_value = "label"
        
        # Create CSV data source with mock config
        self.csv_source = CSVDataSource(self.mock_yaml_config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
    
    def test_csv_read_write(self):
        """Test reading and writing CSV data."""
        test_data = [
            {'id': '1', 'name': 'Test 1', 'value': 'Value 1'},
            {'id': '2', 'name': 'Test 2', 'value': 'Value 2'}
        ]
        
        # Write CSV data
        self.csv_source.write_csv_file('test_table', test_data)
        
        # Read CSV data
        table = self.csv_source.get_table('test_table')
        
        # Verify data
        self.assertEqual(len(table), 2)
        self.assertEqual(table.data[0]['id'], '1')
        self.assertEqual(table.data[0]['name'], 'Test 1')
        self.assertEqual(table.data[1]['id'], '2')
    
    def test_table_caching(self):
        """Test that saved tables are cached for subsequent reads."""
        # Create and save a table
        table = self.csv_source.create_table('cached_table', ['id', 'data'])
        table.add_row({'id': '1', 'data': 'cached'})
        self.csv_source.save_table(table)
        
        # Read the table back
        retrieved_table = self.csv_source.get_table('cached_table')
        
        # Verify cached data
        self.assertEqual(len(retrieved_table), 1)
        self.assertEqual(retrieved_table.data[0]['id'], '1')
        self.assertEqual(retrieved_table.data[0]['data'], 'cached')


if __name__ == '__main__':
    unittest.main()
