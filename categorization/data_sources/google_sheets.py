"""
Google Sheets implementation of the data source abstraction.
"""
import gspread
from google.auth import default
from typing import List, Dict, Any, Optional
import sys
import os
from ..yaml_config import YAMLConfig

# Add parent directory to path to import storage module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from storage.sheets_target import exponential_backoff_with_retry
from categorization.data_sources.base import DataSource, Table


class GoogleSheetsDataSource(DataSource):
    """Google Sheets implementation of the data source abstraction."""
    
    def __init__(self, sheet_id: str, yaml_config: YAMLConfig = None):
        """
        Initialize the Google Sheets data source.
        
        Args:
            sheet_id: Google Sheet ID
            yaml_config: YAML configuration instance (optional, will create if not provided)
        """
        if yaml_config is None:
            yaml_config = YAMLConfig()
        
        self.sheet_id = sheet_id
        self.yaml_config = yaml_config
        self.gc = None
        self.sheet = None
        
    def connect(self):
        """Connect to the Google Sheet."""
        if self.gc is None:
            # Use default credentials like the existing project
            creds, _ = default(scopes=[
                'https://www.googleapis.com/auth/drive', 
                'https://www.googleapis.com/auth/spreadsheets'
            ])
            self.gc = gspread.authorize(creds)
        
        if self.sheet is None:
            try:
                self.sheet = self.gc.open_by_key(self.sheet_id)
                print(f"✅ Connected to Google Sheet: {self.sheet.title}")
            except Exception as e:
                raise Exception(f"Failed to connect to Google Sheet {self.sheet_id}: {e}")
    
    def get_table(self, table_name: str) -> Table:
        """
        Get a table by name from the Google Sheet.
        
        Args:
            table_name: Name of the tab/worksheet
            
        Returns:
            Table object with data from the worksheet
        """
        if not self.sheet:
            self.connect()
        
        try:
            worksheet = self.sheet.worksheet(table_name)
        except gspread.WorksheetNotFound:
            available_tabs = [ws.title for ws in self.sheet.worksheets()]
            raise Exception(f"Tab '{table_name}' not found in the sheet. Available tabs: {available_tabs}")
        
        # Get all records with exponential backoff
        def get_records():
            return worksheet.get_all_records()
        
        records = exponential_backoff_with_retry(get_records)
        
        # Convert records to our table format
        table = Table(table_name)
        for record in records:
            # Clean up the record - convert all values to strings and handle None values
            clean_record = {}
            for key, value in record.items():
                if value is None:
                    clean_record[key] = ''
                else:
                    clean_record[key] = str(value).strip()
            table.add_row(clean_record)
        
        print(f"📖 Loaded {len(table)} rows from '{table_name}' table")
        return table
    
    def create_table(self, table_name: str, headers: List[str]) -> Table:
        """
        Create a new table (worksheet) with specified headers.
        
        Args:
            table_name: Name for the new worksheet
            headers: Column headers
            
        Returns:
            Created table object
        """
        if not self.sheet:
            self.connect()
        
        # Check if worksheet already exists
        try:
            existing_worksheet = self.sheet.worksheet(table_name)
            print(f"⚠️  Table '{table_name}' already exists. Using existing table.")
            return Table(table_name)
        except gspread.WorksheetNotFound:
            pass
        
        # Create new worksheet
        def create_worksheet():
            return self.sheet.add_worksheet(title=table_name, rows=1000, cols=len(headers))
        
        worksheet = exponential_backoff_with_retry(create_worksheet)
        
        # Add headers
        def update_headers():
            worksheet.update('1:1', [headers])
        
        exponential_backoff_with_retry(update_headers)
        
        print(f"✅ Created new table: '{table_name}'")
        return Table(table_name)
    
    def save_table(self, table: Table):
        """
        Save table data to the Google Sheet.
        
        Args:
            table: Table to save
        """
        if not self.sheet:
            self.connect()
        
        worksheet = self.sheet.worksheet(table.name)
        
        if not table.data:
            print(f"⚠️  No data to save to table '{table.name}'")
            return
        
        # Get headers from the first row of data
        headers = list(table.data[0].keys()) if table.data else []
        
        # Prepare data for batch update
        data_rows = []
        for row in table.data:
            data_row = [row.get(header, '') for header in headers]
            data_rows.append(data_row)
        
        # Clear existing data (except headers) and write new data
        def clear_and_update():
            if data_rows:
                end_row = len(data_rows) + 1
                range_name = f'A2:{chr(65 + len(headers) - 1)}{end_row}'
                worksheet.update(range_name, data_rows)
        
        exponential_backoff_with_retry(clear_and_update)
        print(f"✅ Saved {len(table.data)} rows to '{table.name}' table")
    
    def list_tables(self) -> List[str]:
        """
        List available tables (worksheets).
        
        Returns:
            List of worksheet names
        """
        if not self.sheet:
            self.connect()
        
        return [ws.title for ws in self.sheet.worksheets()]
