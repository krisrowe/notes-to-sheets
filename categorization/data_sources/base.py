"""
Base abstractions for data sources and datasets.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class Table:
    """Represents a table/tab with rows and columns."""
    
    def __init__(self, name: str, data: List[Dict[str, Any]] = None):
        """
        Initialize a table.
        
        Args:
            name: Table/tab name
            data: List of row dictionaries
        """
        self.name = name
        self.data = data or []
    
    def add_row(self, row: Dict[str, Any]):
        """Add a row to the table."""
        self.data.append(row)
    
    def get_rows(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get rows from the table.
        
        Args:
            limit: Maximum number of rows to return
            
        Returns:
            List of row dictionaries
        """
        if limit is not None:
            return self.data[:limit]
        return self.data.copy()
    
    def clear(self):
        """Clear all data from the table."""
        self.data.clear()
    
    def __len__(self):
        """Return number of rows in the table."""
        return len(self.data)


class DataSource(ABC):
    """Abstract base class for data sources (Google Sheets, CSV, etc.)."""
    
    @abstractmethod
    def connect(self):
        """Connect to the data source."""
        pass
    
    @abstractmethod
    def get_table(self, table_name: str) -> Table:
        """
        Get a table by name.
        
        Args:
            table_name: Name of the table/tab
            
        Returns:
            Table object with data
        """
        pass
    
    @abstractmethod
    def create_table(self, table_name: str, headers: List[str]) -> Table:
        """
        Create a new table with specified headers.
        
        Args:
            table_name: Name of the new table
            headers: Column headers
            
        Returns:
            Created table object
        """
        pass
    
    @abstractmethod
    def save_table(self, table: Table):
        """
        Save table data to the data source.
        
        Args:
            table: Table to save
        """
        pass
    
    @abstractmethod
    def list_tables(self) -> List[str]:
        """
        List available tables/tabs.
        
        Returns:
            List of table names
        """
        pass
