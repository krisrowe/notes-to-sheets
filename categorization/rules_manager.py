"""
Rules management for the categorization module.
Supports reading rules from local files or from a Label tab in Google Sheets.
"""
import os
from typing import Optional, Dict, Any, List
from .data_sources.base import DataSource


class RulesManager:
    """Manages categorization rules from files or Google Sheets."""
    
    def __init__(self, data_source: Optional[DataSource] = None):
        """
        Initialize rules manager.
        
        Args:
            data_source: Optional data source for reading rules from sheets
        """
        self.data_source = data_source
    
    def get_rules(self, rules_file: Optional[str] = None) -> str:
        """
        Get categorization rules from file or data source.
        
        If rules_file is provided, reads from the file.
        If no rules_file is provided, attempts to read from Label tab in data source.
        
        Args:
            rules_file: Path to local rules file (optional)
            
        Returns:
            Formatted categorization rules string
            
        Raises:
            ValueError: If no rules source is available or rules are empty
            NotImplementedError: If data source doesn't support reading rules
        """
        if rules_file:
            return self._get_rules_from_file(rules_file)
        elif self.data_source:
            return self._get_rules_from_sheet()
        else:
            raise ValueError("No rules source available. Provide rules_file or ensure data source supports reading rules from Label tab.")
    
    def _get_rules_from_file(self, rules_file: str) -> str:
        """
        Read rules from a local file.
        
        Args:
            rules_file: Path to rules file
            
        Returns:
            Rules content as string
            
        Raises:
            ValueError: If file doesn't exist or is empty
        """
        if not os.path.exists(rules_file):
            raise ValueError(f"Rules file not found: {rules_file}")
        
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = f.read().strip()
        
        if not rules:
            raise ValueError(f"Rules file is empty: {rules_file}")
        
        return rules
    
    def _get_rules_from_sheet(self) -> str:
        """
        Read rules from Label tab in Google Sheet.
        
        Returns:
            Formatted rules string based on Label tab data
            
        Raises:
            ValueError: If Label tab doesn't exist or has no active rules
        """
        if not self.data_source:
            raise ValueError("No data source available for reading sheet rules")
        
        try:
            # Get the Label table/tab
            label_table = self.data_source.get_table("Label")
            
            # Handle case where data source doesn't have Label table
            if label_table is None:
                raise ValueError("Label table not found in data source")
            
            # Read all rows from the Label table
            rows = label_table.get_rows()
            
            if not rows:
                raise ValueError("Label tab is empty")
            
            # Filter for rows where Auto is TRUE and format rules
            active_rules = []
            for row in rows:
                auto_value = str(row.get('Auto', '')).strip().upper()
                if auto_value in ['TRUE', 'YES', '1', 'Y']:
                    name = row.get('Name', '').strip()
                    description = row.get('Description', '').strip()
                    
                    if name and description:
                        active_rules.append(f"{name}: {description}")
            
            if not active_rules:
                raise ValueError("No active rules found in Label tab (no rows with Auto=TRUE)")
            
            # Format the rules into a coherent instruction
            rules_header = "Categorize notes based on the following rules, using the specific labels provided:\n\n"
            rules_body = "\n\n".join(active_rules)
            rules_footer = "\n\nIf a note fits multiple categories, include all relevant labels separated by commas.\nIf a note doesn't clearly fit any category, leave it unlabeled or assign a general \"Uncategorized\" label."
            
            return rules_header + rules_body + rules_footer
            
        except Exception as e:
            raise ValueError(f"Error reading rules from Label tab: {str(e)}")
    
    def has_sheet_rules(self) -> bool:
        """
        Check if Label tab exists and has active rules.
        
        Returns:
            True if Label tab exists with active rules, False otherwise
        """
        if not self.data_source:
            return False
        
        try:
            # Check if Label table exists
            tables = self.data_source.list_tables()
            if "Label" not in tables:
                return False
            
            # Check if there are any active rules
            label_table = self.data_source.get_table("Label")
            rows = label_table.get_all_rows()
            
            for row in rows:
                auto_value = str(row.get('Auto', '')).strip().upper()
                if auto_value in ['TRUE', 'YES', '1', 'Y']:
                    name = row.get('Name', '').strip()
                    description = row.get('Description', '').strip()
                    if name and description:
                        return True
            
            return False
            
        except Exception:
            return False
