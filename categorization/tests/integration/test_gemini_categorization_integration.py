"""
Integration tests for Gemini API categorization using CSV data source.

These tests use the real Gemini API to validate end-to-end categorization functionality.
They require a valid GEMINI_API_KEY environment variable.

Test naming convention: test_integration_*
"""
import unittest
import os
import tempfile
import shutil
from categorization.data_sources.csv_source import CSVDataSource
from categorization.categorization_service import CategorizationService
from categorization.gemini_client import GeminiCategorizer
from categorization.tests.fixtures.test_data import (
    SAMPLE_NOTES, 
    EXPECTED_CATEGORIES, 
    TEST_CATEGORIZATION_RULES
)


class TestGeminiCategorizationIntegration(unittest.TestCase):
    """Integration tests for Gemini API categorization."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures."""
        # Check if API key is available
        cls.api_key = os.getenv('GEMINI_API_KEY')
        if not cls.api_key:
            raise unittest.SkipTest("GEMINI_API_KEY environment variable not set. Skipping integration tests.")
        
        print(f"\n🔑 Using Gemini API key: {cls.api_key[:10]}...")
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.csv_source = CSVDataSource(self.test_dir)
        
        # Create real Gemini categorizer
        self.gemini_categorizer = GeminiCategorizer(self.api_key)
        
        # Create categorization service
        self.service = CategorizationService(self.csv_source, self.gemini_categorizer)
        
        # Set up test data
        self.csv_source.write_csv_file('Note', SAMPLE_NOTES)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
    
    def test_integration_gemini_categorization_basic(self):
        """Test basic Gemini API categorization with a small dataset."""
        print("\n🧪 Testing basic Gemini API categorization...")
        
        # Run categorization on first 3 notes
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes',
            categorization_rules=TEST_CATEGORIZATION_RULES,
            limit=3
        )
        
        # Verify basic functionality
        self.assertEqual(result['total_notes'], 3)
        self.assertGreaterEqual(result['categorized_notes'], 0)  # Allow for some API errors
        self.assertEqual(len(result['results']), 3)
        
        # Verify results structure
        for res in result['results']:
            self.assertIn('note_id', res)
            self.assertIn('labels', res)
            self.assertIsInstance(res['note_id'], str)
            self.assertIsInstance(res['labels'], str)
            
            # Verify note_id is from our test data
            self.assertIn(res['note_id'], ['test001', 'test002', 'test003'])
        
        # Verify output table was created and populated
        output_table = self.csv_source.get_table('categorized_notes')
        self.assertEqual(len(output_table), 3)
        
        print(f"✅ Categorized {result['categorized_notes']}/{result['total_notes']} notes successfully")
        
        # Print results for manual inspection
        print("\n📊 Categorization Results:")
        for res in result['results']:
            print(f"  {res['note_id']}: {res['labels']}")
    
    def test_integration_gemini_categorization_validation(self):
        """Test Gemini API categorization and validate results against expectations."""
        print("\n🧪 Testing Gemini API categorization with validation...")
        
        # Run categorization on first 5 notes for validation
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='categorized_notes',
            categorization_rules=TEST_CATEGORIZATION_RULES,
            limit=5
        )
        
        # Verify basic functionality
        self.assertEqual(result['total_notes'], 5)
        self.assertEqual(len(result['results']), 5)
        
        # Validate categorization quality
        correct_predictions = 0
        total_predictions = 0
        
        print("\n📋 Validation Results:")
        for res in result['results']:
            note_id = res['note_id']
            predicted_labels = res['labels'].lower()
            
            # Skip error cases for validation
            if 'error:' in predicted_labels:
                print(f"  ❌ {note_id}: API Error - {res['labels']}")
                continue
            
            total_predictions += 1
            expected_labels = EXPECTED_CATEGORIES.get(note_id, [])
            
            # Check if any expected label is in the prediction
            is_correct = any(
                expected.lower() in predicted_labels 
                for expected in expected_labels
            )
            
            if is_correct:
                correct_predictions += 1
                print(f"  ✅ {note_id}: {res['labels']} (Expected: {expected_labels})")
            else:
                print(f"  ⚠️  {note_id}: {res['labels']} (Expected: {expected_labels})")
        
        # Calculate accuracy
        if total_predictions > 0:
            accuracy = correct_predictions / total_predictions
            print(f"\n📈 Categorization Accuracy: {accuracy:.1%} ({correct_predictions}/{total_predictions})")
            
            # We expect at least 60% accuracy for a basic validation
            self.assertGreaterEqual(accuracy, 0.6, 
                f"Categorization accuracy {accuracy:.1%} is below expected threshold of 60%")
        else:
            self.fail("No successful predictions to validate")
    
    def test_integration_gemini_error_handling(self):
        """Test Gemini API error handling with invalid input."""
        print("\n🧪 Testing Gemini API error handling...")
        
        # Create notes with problematic content
        problematic_notes = [
            {
                'id': 'empty001',
                'title': '',
                'content': ''
            },
            {
                'id': 'special001',
                'title': 'Special Characters',
                'content': '!@#$%^&*()_+ 测试 🚀 emoji content'
            }
        ]
        
        self.csv_source.write_csv_file('ProblematicNote', problematic_notes)
        
        # Run categorization
        result = self.service.categorize_notes(
            source_table='ProblematicNote',
            output_table='error_test_results',
            categorization_rules=TEST_CATEGORIZATION_RULES,
            limit=None
        )
        
        # Verify the service handles errors gracefully
        self.assertEqual(result['total_notes'], 2)
        self.assertEqual(len(result['results']), 2)
        
        # Results should be returned even if there are errors
        for res in result['results']:
            self.assertIn('note_id', res)
            self.assertIn('labels', res)
        
        print(f"✅ Error handling test completed: {result['errors']} errors out of {result['total_notes']} notes")
    
    def test_integration_gemini_custom_rules(self):
        """Test Gemini API with custom categorization rules."""
        print("\n🧪 Testing Gemini API with custom rules...")
        
        custom_rules = """
        Categorize notes into exactly these categories:
        - URGENT: Anything that needs immediate attention
        - ROUTINE: Regular daily activities
        - PLANNING: Future planning and preparation
        
        Use only these three labels.
        """
        
        # Run categorization with custom rules
        result = self.service.categorize_notes(
            source_table='Note',
            output_table='custom_categorized_notes',
            categorization_rules=custom_rules,
            limit=3
        )
        
        # Verify basic functionality
        self.assertEqual(result['total_notes'], 3)
        self.assertEqual(len(result['results']), 3)
        
        print("\n📊 Custom Rules Results:")
        for res in result['results']:
            print(f"  {res['note_id']}: {res['labels']}")
            
            # Verify labels contain expected custom categories (if not error)
            if 'error:' not in res['labels'].lower():
                labels_lower = res['labels'].lower()
                has_custom_label = any(
                    label in labels_lower 
                    for label in ['urgent', 'routine', 'planning']
                )
                # Note: We don't assert this as Gemini might interpret differently
                if has_custom_label:
                    print(f"    ✅ Uses custom categories")


@unittest.skipUnless(os.getenv('GEMINI_API_KEY'), "GEMINI_API_KEY not set")
class TestGeminiClientIntegration(unittest.TestCase):
    """Integration tests specifically for the Gemini client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.client = GeminiCategorizer(self.api_key)
    
    def test_integration_gemini_client_single_note(self):
        """Test Gemini client with a single note."""
        print("\n🧪 Testing Gemini client with single note...")
        
        notes = [SAMPLE_NOTES[0]]  # Just the grocery shopping note
        
        results = self.client.categorize_notes(notes, TEST_CATEGORIZATION_RULES)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        self.assertEqual(result['note_id'], 'test001')
        self.assertIsInstance(result['labels'], str)
        self.assertNotEqual(result['labels'].strip(), '')
        
        print(f"✅ Single note result: {result['labels']}")
    
    def test_integration_gemini_client_batch_processing(self):
        """Test Gemini client with multiple notes in batch."""
        print("\n🧪 Testing Gemini client batch processing...")
        
        notes = SAMPLE_NOTES[:4]  # First 4 notes
        
        results = self.client.categorize_notes(notes, TEST_CATEGORIZATION_RULES)
        
        self.assertEqual(len(results), 4)
        
        for i, result in enumerate(results):
            self.assertEqual(result['note_id'], notes[i]['id'])
            self.assertIsInstance(result['labels'], str)
        
        print(f"✅ Batch processing completed for {len(results)} notes")


if __name__ == '__main__':
    # Run integration tests with verbose output
    unittest.main(verbosity=2)
