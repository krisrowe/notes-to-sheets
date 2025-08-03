"""
CSV file implementation of the data source abstraction for testing.
"""
import csv
import os
from typing import List, Dict, Any, Optional
from .base import DataSource, Table
from ..yaml_config import YAMLConfig


class CSVDataSource(DataSource):
    """CSV file implementation of the data source abstraction."""
    
    def __init__(self, yaml_config: YAMLConfig = None):
        """
        Initialize the CSV data source.
        
        Args:
            yaml_config: YAML configuration instance (optional, will create if not provided)
        """
        if yaml_config is None:
            yaml_config = YAMLConfig()
        
        self.yaml_config = yaml_config
        self.data_dir = yaml_config.get_csv_data_dir()
        self.tables_cache = {}  # Cache for in-memory table storage
        self.connected = False
    
    def connect(self):
        """Connect to the CSV data source (ensure directory exists)."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            print(f"✅ Created test data directory: {self.data_dir}")
        else:
            print(f"✅ Connected to CSV data source: {self.data_dir}")
        
        self.connected = True
    
    def get_table(self, table_name: str) -> Table:
        """
        Get a table by name from CSV file or cache.
        
        Args:
            table_name: Name of the table (CSV filename without extension)
            
        Returns:
            Table object with data from CSV or cache
        """
        if not self.connected:
            self.connect()
        
        # Handle Label table lookup (for rules) with case-insensitive file search
        if table_name.lower() == 'label':
            # Look for rules.csv (case-insensitive)
            for filename in os.listdir(self.data_dir):
                if filename.lower() == 'label.csv':
                    table_name = filename[:-4]  # Remove .csv extension
                    break
            else:
                # No rules file found, return None to let caller handle
                return None
        
        # Check if table is cached (from previous saves)
        if table_name in self.tables_cache:
            cached_table = self.tables_cache[table_name]
            print(f"📖 Loaded {len(cached_table)} rows from cached '{table_name}' table")
            return Table(table_name, cached_table.data.copy())
        
        # Try to load from CSV file
        csv_path = os.path.join(self.data_dir, f"{table_name}.csv")
        
        if not os.path.exists(csv_path):
            raise Exception(f"CSV file '{csv_path}' not found for table '{table_name}'")
        
        table = Table(table_name)
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Clean up the row - handle empty values
                    clean_row = {}
                    for key, value in row.items():
                        clean_row[key] = value.strip() if value else ''
                    table.add_row(clean_row)
            
            print(f"📖 Loaded {len(table)} rows from '{table_name}' CSV file")
            return table
            
        except Exception as e:
            raise Exception(f"Failed to read CSV file '{csv_path}': {e}")
    
    def create_table(self, table_name: str, headers: List[str]) -> Table:
        """
        Create a new table with specified headers.
        
        Args:
            table_name: Name for the new table
            headers: Column headers
            
        Returns:
            Created table object
        """
        if not self.connected:
            self.connect()
        
        table = Table(table_name)
        
        # Cache the empty table
        self.tables_cache[table_name] = table
        
        print(f"✅ Created new table: '{table_name}' with headers: {headers}")
        return table
    
    def save_table(self, table: Table):
        """
        Save table data to cache (simulates saving to persistent storage).
        
        Args:
            table: Table to save
        """
        if not self.connected:
            self.connect()
        
        # Cache the table data for subsequent reads
        self.tables_cache[table.name] = Table(table.name, table.data.copy())
        
        print(f"✅ Cached {len(table.data)} rows for '{table.name}' table (test mode)")
    
    def list_tables(self) -> List[str]:
        """
        List available tables (CSV files + cached tables).
        
        Returns:
            List of table names
        """
        if not self.connected:
            self.connect()
        
        tables = set()
        
        # Add CSV files
        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.csv'):
                    tables.add(filename[:-4])  # Remove .csv extension
        
        # Add cached tables
        tables.update(self.tables_cache.keys())
        
        return list(tables)
    
    def write_csv_file(self, table_name: str, data: List[Dict[str, Any]]):
        """
        Write data to a CSV file (utility method for test setup).
        
        Args:
            table_name: Name of the table
            data: List of row dictionaries
        """
        if not self.connected:
            self.connect()
        
        if not data:
            return
        
        csv_path = os.path.join(self.data_dir, f"{table_name}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            headers = list(data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✅ Wrote {len(data)} rows to '{csv_path}'")
    
    def clear_cache(self):
        """Clear the in-memory cache (utility method for testing)."""
        self.tables_cache.clear()
        print("🧹 Cleared table cache")
