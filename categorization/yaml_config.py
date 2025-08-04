"""
YAML configuration management for the categorization module.
"""
import os
import yaml
from typing import Dict, Any, List, Optional


class YAMLConfig:
    """YAML configuration manager for storage and processing settings."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize YAML configuration.
        
        Args:
            config_file: Path to YAML config file (default: categorization/config.yaml)
        """
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
        
        self.config_file = config_file
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            print(f"⚠️  YAML config file {self.config_file} not found. Using defaults.")
            self.config = {}
    
    def get_storage_config(self, data_source: str) -> Dict[str, Any]:
        """
        Get storage configuration for a specific data source.
        
        Args:
            data_source: Data source type ('sheets' or 'csv')
            
        Returns:
            Configuration dictionary for the data source
        """
        return self.config.get('storage', {}).get(data_source, {})
    
    def get_default_data_source(self) -> str:
        """
        Get the default data source type from configuration.
        
        Returns:
            Default data source type ('sheets' or 'csv')
        """
        return self.config.get('storage', {}).get('default', 'sheets')
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.config.get('processing', {})
    
    # Sheets-specific methods
    def get_sheets_source_tab(self) -> str:
        """Get source tab name for Google Sheets."""
        return self.get_storage_config('sheets').get('source_tab', 'Note')
    
    def get_sheets_rules_tab(self) -> str:
        """Get rules tab name for Google Sheets."""
        return self.get_storage_config('sheets').get('rules_tab', 'Label')
    
    def get_sheets_output_tab(self) -> str:
        """Get output tab name for Google Sheets."""
        return self.get_storage_config('sheets').get('output_tab', 'labeled_notes')
    

    
    # CSV-specific methods
    def get_csv_data_dir(self) -> str:
        """Get data directory for CSV files."""
        data_dir = self.get_storage_config('csv').get('data_dir', 'test_data')
        # Make it relative to the categorization module directory
        return os.path.join(os.path.dirname(__file__), data_dir)
    
    def get_csv_source_file(self) -> str:
        """Get source file name for CSV (without extension)."""
        return self.get_storage_config('csv').get('source_file', 'notes')
    
    def get_csv_rules_file(self) -> str:
        """Get rules file name for CSV (without extension)."""
        return self.get_storage_config('csv').get('rules_file', 'label')
    
    def get_csv_output_file(self) -> str:
        """Get output file name for CSV (without extension)."""
        return self.get_storage_config('csv').get('output_file', 'labeled_notes')
    
    # Processing methods
    def get_default_limit(self) -> int:
        """Get default limit for number of notes to process."""
        return self.get_processing_config().get('default_limit', 10)
    
    def get_dry_run(self) -> bool:
        """Get default dry run setting."""
        return self.get_processing_config().get('dry_run', False)
    
    def get_api_delay(self) -> float:
        """Get API delay setting."""
        return self.get_processing_config().get('api_delay', 0.1)
    
    def get_max_retries(self) -> int:
        """Get maximum retries setting."""
        return self.get_processing_config().get('max_retries', 3)
    
    def get_label_delimiter(self) -> str:
        """Get label delimiter for multiple labels in a single field."""
        return self.get_processing_config().get('label_delimiter', ', ')
    
    # Filters methods
    def get_filters_config(self) -> Dict[str, Any]:
        """Get filters configuration."""
        return self.config.get('filters', {})
    
    def get_label_filter(self) -> Optional[str]:
        """Get label filter setting. Returns None if empty or not set."""
        label = self.get_filters_config().get('label', '')
        return label.strip() if label and label.strip() else None
