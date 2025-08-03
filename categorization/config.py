"""
Configuration management for the categorization module.
Handles sensitive data from INI file, while YAML config handles storage settings.
"""
import configparser
import os
from typing import Optional
from .yaml_config import YAMLConfig


class CategorizationConfig:
    """Configuration manager for categorization module - handles sensitive data only."""
    
    def __init__(self, config_file: str = None, yaml_config_file: str = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to INI config file (default: categorization/config.ini)
            yaml_config_file: Path to YAML config file (default: categorization/config.yaml)
        """
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.yaml_config = YAMLConfig(yaml_config_file)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            print(f"⚠️  Config file {self.config_file} not found. Using defaults and environment variables.")
    
    def get_sheet_id(self) -> Optional[str]:
        """Get Google Sheet ID from config or environment."""
        return (
            self.config.get('categorization', 'sheet_id', fallback=None) or
            os.getenv('CATEGORIZATION_SHEET_ID')
        )
    
    def get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from config or environment."""
        return (
            self.config.get('categorization', 'gemini_api_key', fallback=None) or
            os.getenv('GEMINI_API_KEY')
        )
    
    def get_yaml_config(self) -> YAMLConfig:
        """Get the YAML configuration instance."""
        return self.yaml_config
