"""
Google Sheets reader for note categorization.
"""
import gspread
from google.auth import default
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path to import storage module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.sheets_target import exponential_backoff_with_retry


class NotesSheetReader:
    """Reader for extracting notes from Google Sheets."""
    
    def __init__(self, sheet_id: str):
        """
        Initialize the sheets reader.
        
        Args:
            sheet_id: Google Sheet ID
        """
        self.sheet_id = sheet_id
        # Use default credentials like the existing project
        creds, _ = default(scopes=[
            'https://www.googleapis.com/auth/drive', 
            'https://www.googleapis.com/auth/spreadsheets'
        ])
        self.gc = gspread.authorize(creds)
        self.sheet = None
        
    def connect(self):
        """Connect to the Google Sheet."""
        try:
            self.sheet = self.gc.open_by_key(self.sheet_id)
            print(f"✅ Connected to Google Sheet: {self.sheet.title}")
        except Exception as e:
            raise Exception(f"Failed to connect to Google Sheet {self.sheet_id}: {e}")
    
    def read_notes_from_tab(self, tab_name: str = "note", limit: int = None) -> List[Dict[str, Any]]:
        """
        Read notes from the specified tab.
        
        Args:
            tab_name: Name of the tab containing notes (default: "note")
            limit: Maximum number of notes to read (default: None for all notes)
            
        Returns:
            List of note dictionaries with 'id', 'title', and 'content' keys
        """
        if not self.sheet:
            self.connect()
        
        try:
            worksheet = self.sheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            raise Exception(f"Tab '{tab_name}' not found in the sheet. Available tabs: {[ws.title for ws in self.sheet.worksheets()]}")
        
        # Get all records with exponential backoff
        def get_records():
            return worksheet.get_all_records()
        
        records = exponential_backoff_with_retry(get_records)
        
        notes = []
        for i, record in enumerate(records, start=2):  # Start at 2 since row 1 is headers
            # Look for common column names for ID, title, and content
            note_id = self._get_field_value(record, ['id', 'note_id', 'ID', 'Note ID'], default=str(i))
            title = self._get_field_value(record, ['title', 'Title', 'name', 'Name'], default='')
            content = self._get_field_value(record, ['content', 'Content', 'text', 'Text', 'body', 'Body'], default='')
            
            notes.append({
                'id': str(note_id),
                'title': str(title),
                'content': str(content)
            })
        
        # Apply limit if specified
        if limit is not None:
            notes = notes[:limit]
            print(f"📖 Read {len(notes)} notes from '{tab_name}' tab (limited to {limit})")
        else:
            print(f"📖 Read {len(notes)} notes from '{tab_name}' tab")
        
        return notes
    
    def create_categorization_tab(self, tab_name: str = "categorized_notes") -> str:
        """
        Create a new tab for categorization results.
        
        Args:
            tab_name: Name for the new tab
            
        Returns:
            Name of the created tab
        """
        if not self.sheet:
            self.connect()
        
        # Check if tab already exists
        try:
            existing_worksheet = self.sheet.worksheet(tab_name)
            print(f"⚠️  Tab '{tab_name}' already exists. Using existing tab.")
            return tab_name
        except gspread.WorksheetNotFound:
            pass
        
        # Create new worksheet
        def create_worksheet():
            return self.sheet.add_worksheet(title=tab_name, rows=1000, cols=10)
        
        worksheet = exponential_backoff_with_retry(create_worksheet)
        
        # Add headers
        def update_headers():
            worksheet.update('A1:B1', [['Note ID', 'Labels']])
        
        exponential_backoff_with_retry(update_headers)
        
        print(f"✅ Created new tab: '{tab_name}'")
        return tab_name
    
    def write_categorization_results(self, results: List[Dict[str, Any]], tab_name: str = "categorized_notes"):
        """
        Write categorization results to the specified tab.
        
        Args:
            results: List of dictionaries with 'note_id' and 'labels' keys
            tab_name: Name of the tab to write to
        """
        if not self.sheet:
            self.connect()
        
        worksheet = self.sheet.worksheet(tab_name)
        
        # Prepare data for batch update
        data_rows = []
        for result in results:
            data_rows.append([result['note_id'], result['labels']])
        
        if data_rows:
            # Clear existing data (except headers) and write new data
            def clear_and_update():
                # Clear existing data starting from row 2
                if len(data_rows) > 0:
                    end_row = len(data_rows) + 1
                    range_name = f'A2:B{end_row}'
                    worksheet.update(range_name, data_rows)
            
            exponential_backoff_with_retry(clear_and_update)
            print(f"✅ Wrote {len(results)} categorization results to '{tab_name}' tab")
    
    def _get_field_value(self, record: Dict[str, Any], field_names: List[str], default: str = '') -> str:
        """
        Get field value from record, trying multiple possible field names.
        
        Args:
            record: Dictionary record from Google Sheets
            field_names: List of possible field names to try
            default: Default value if no field is found
            
        Returns:
            Field value or default
        """
        for field_name in field_names:
            if field_name in record and record[field_name] is not None:
                return str(record[field_name]).strip()
        return default
