"""
Categorization service that uses the data source abstraction.
"""
from typing import List, Dict, Any, Optional
from .data_sources.base import DataSource, Table
from .gemini_client import GeminiCategorizer
from .rules_manager import RulesManager
from .yaml_config import YAMLConfig


class CategorizationService:
    """Service for categorizing notes using pluggable data sources."""
    
    def __init__(self, data_source: DataSource, gemini_categorizer: GeminiCategorizer, rules_manager: RulesManager, yaml_config: YAMLConfig = None):
        """
        Initialize the categorization service.
        
        Args:
            data_source: Data source implementation (Google Sheets, CSV, etc.)
            gemini_categorizer: Gemini AI categorizer
            rules_manager: Rules manager for loading categorization rules
            yaml_config: YAML configuration instance (optional, will create if not provided)
        """
        self.data_source = data_source
        self.gemini_categorizer = gemini_categorizer
        self.rules_manager = rules_manager
        self.yaml_config = yaml_config if yaml_config else YAMLConfig()
    
    def categorize_notes(
        self, 
        source_table: str, 
        output_table: str, 
        rules_file: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Categorize notes from source table and save results to output table.
        
        Args:
            source_table: Name of the table containing notes
            output_table: Name of the table to save categorization results
            rules_file: Path to local rules file (optional, will use Label tab if not provided)
            limit: Maximum number of notes to process
            
        Returns:
            Dictionary with categorization results and statistics
        """
        # Connect to data source
        self.data_source.connect()
        
        # Load categorization rules
        try:
            categorization_rules = self.rules_manager.get_rules(
                rules_file=rules_file
            )
            print(f"📋 Categorization rules:")
            # Print first few lines of rules for confirmation
            rules_preview = '\n'.join(categorization_rules.split('\n')[:5])
            print(f"   {rules_preview}...")
        except ValueError as e:
            print(f"❌ Error loading rules: {e}")
            return {
                'total_notes': 0,
                'categorized_notes': 0,
                'errors': 1,
                'results': [],
                'error_message': str(e)
            }
        
        # Read notes from source table
        print(f"📖 Reading notes from '{source_table}' table...")
        notes_table = self.data_source.get_table(source_table)
        
        # Load existing categorization results to check for duplicates and apply filters
        try:
            existing_results_table = self.data_source.get_table(output_table)
            existing_results = {row.get('Note ID', ''): row.get('Labels', '') for row in existing_results_table.get_rows()}
            print(f"📋 Found {len(existing_results)} existing categorization results")
        except Exception:
            print(f"ℹ️  No existing results found in '{output_table}' table. All notes are new.")
            existing_results = {}
        
        # Check for label filter
        label_filter = self.yaml_config.get_label_filter()
        
        # Process notes and apply filters/deduplication with limit
        notes_to_process = []
        skipped_duplicates = 0
        skipped_filter = 0
        total_examined = 0
        
        for row in notes_table.get_rows():
            total_examined += 1
            note_id = self._get_field_value(row, ['id', 'note_id', 'ID', 'Note ID'], default='unknown')
            
            # Skip notes that already exist in the target table
            if note_id in existing_results:
                skipped_duplicates += 1
                continue
            
            # Apply label filter if specified
            if label_filter:
                # Check the Labels column in the source note (not existing results)
                source_labels = self._get_field_value(row, ['Labels', 'labels', 'Label', 'label'], default='')
                # Only process notes that have the required label
                if label_filter not in source_labels:
                    skipped_filter += 1
                    continue
            
            # Add to processing list
            notes_to_process.append(row)
            
            # Stop when we reach the limit of new notes to process
            if limit and len(notes_to_process) >= limit:
                break
        
        # Report filtering results
        print(f"📊 Examined {total_examined} notes from source table")
        if skipped_duplicates > 0:
            print(f"⏭️  Skipped {skipped_duplicates} notes already processed (duplicates)")
        if label_filter:
            if skipped_filter > 0:
                print(f"🔍 Skipped {skipped_filter} notes not matching label filter '{label_filter}'")
            print(f"🆕 Found {len(notes_to_process)} new notes to process with label '{label_filter}'")
        else:
            print(f"🆕 Found {len(notes_to_process)} new notes to process")
        
        if limit and len(notes_to_process) == limit:
            print(f"📏 Reached limit of {limit} new notes for processing")
        
        notes_data = notes_to_process
        
        if not notes_data:
            print("⚠️  No notes found in the source table.")
            return {
                'total_notes': 0,
                'categorized_notes': 0,
                'errors': 0,
                'results': []
            }
        
        if limit:
            print(f"📏 Processing {len(notes_data)} notes (limited from {len(notes_table)} total)")
        else:
            print(f"📏 Processing {len(notes_data)} notes")
        
        # Convert table data to the format expected by GeminiCategorizer
        notes_for_categorization = []
        for row in notes_data:
            note = {
                'id': self._get_field_value(row, ['id', 'note_id', 'ID', 'Note ID'], default='unknown'),
                'title': self._get_field_value(row, ['title', 'Title', 'name', 'Name'], default=''),
                'content': self._get_field_value(row, ['content', 'Content', 'text', 'Text', 'body', 'Body'], default='')
            }
            notes_for_categorization.append(note)
        
        # Categorize notes using Gemini AI
        print(f"🤖 Categorizing {len(notes_for_categorization)} notes using Gemini AI...")
        print("📋 Categorization rules:")
        print(f"   {categorization_rules}")
        print()
        
        categorization_results = self.gemini_categorizer.categorize_notes(
            notes_for_categorization, 
            categorization_rules
        )
        
        # Create or get output table
        output_table_obj = self._get_or_create_output_table(output_table)
        
        # Add new results (append to existing data, don't clear)
        for result in categorization_results:
            output_table_obj.add_row({
                'Note ID': result['note_id'],
                'Labels': result['labels']
            })
        
        # Save results to data source
        print(f"💾 Saving categorization results to '{output_table}' table...")
        self.data_source.save_table(output_table_obj)
        
        # Calculate statistics
        error_count = sum(1 for result in categorization_results if 'ERROR:' in result['labels'])
        success_count = len(categorization_results) - error_count
        
        return {
            'total_notes': len(notes_data),
            'categorized_notes': success_count,
            'errors': error_count,
            'results': categorization_results
        }
    
    def _get_or_create_output_table(self, table_name: str) -> Table:
        """Get existing output table or create a new one."""
        try:
            # Try to get existing table
            return self.data_source.get_table(table_name)
        except Exception:
            # Create new table if it doesn't exist
            return self.data_source.create_table(table_name, ['Note ID', 'Labels'])
    
    def _get_field_value(self, record: Dict[str, Any], field_names: List[str], default: str = '') -> str:
        """
        Get field value from record, trying multiple possible field names.
        
        Args:
            record: Dictionary record from data source
            field_names: List of possible field names to try
            default: Default value if no field is found
            
        Returns:
            Field value or default
        """
        for field_name in field_names:
            if field_name in record and record[field_name] is not None:
                return str(record[field_name]).strip()
        return default
    
    def list_available_tables(self) -> List[str]:
        """List all available tables in the data source."""
        self.data_source.connect()
        return self.data_source.list_tables()
