"""
Centralized configuration management for the notes-to-sheets application.
Handles defaults, config.ini, and command line arguments with proper precedence.
"""

import argparse
import configparser
import os
import sys
from typing import Optional, Dict, Any


# Global default constants - single source of truth
DEFAULT_BATCH_SIZE = 20
DEFAULT_MAX_BATCHES = -1
DEFAULT_IGNORE_ERRORS = False
DEFAULT_NO_IMAGE_IMPORT = False
DEFAULT_WIPE_MODE = None


class Config:
    """Centralized configuration manager."""
    
    def __init__(self):
        self._user_config = self._load_user_config()
        self._cmd_line_args = None
    
    def _load_user_config(self) -> Optional[configparser.ConfigParser]:
        """Load user-specific configuration from config.ini."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        config = configparser.ConfigParser()
        
        try:
            config.read(config_path)
            return config
        except Exception as e:
            print(f"Warning: Could not load config.ini: {e}")
            return None
    
    def _get_cmd_line_args(self) -> Optional[argparse.Namespace]:
        """Get command line arguments if running as main script."""
        if self._cmd_line_args is None and len(sys.argv) > 1:
            # Only parse args if we're running as main script (not imported)
            try:
                parser = argparse.ArgumentParser(add_help=False)
                parser.add_argument('--batch-size', type=int)
                parser.add_argument('--max-batches', type=int)
                parser.add_argument('--ignore-errors', action='store_true')
                parser.add_argument('--no-image-import', action='store_true')
                parser.add_argument('--wipe', action='store_true')
                parser.add_argument('--wipe-hard', action='store_true')
                # Add positional args as optional to avoid conflicts
                parser.add_argument('source_path', nargs='?')
                parser.add_argument('target_config', nargs='?')
                
                self._cmd_line_args, _ = parser.parse_known_args()
            except:
                self._cmd_line_args = None
        
        return self._cmd_line_args
    
    def _get_config_value(self, key: str, default_value: Any, value_type: str = 'str') -> Any:
        """Helper function to get config value with proper precedence."""
        # Check command line first
        cmd_args = self._get_cmd_line_args()
        if cmd_args:
            cmd_value = getattr(cmd_args, key.replace('-', '_'), None)
            if cmd_value is not None:
                return cmd_value
        
        # Check config.ini
        if self._user_config and self._user_config.has_section('defaults'):
            try:
                if value_type == 'int':
                    return int(self._user_config['defaults'].get(key, default_value))
                elif value_type == 'bool':
                    return self._user_config['defaults'].getboolean(key, default_value)
                else:
                    return self._user_config['defaults'].get(key, default_value)
            except (ValueError, KeyError):
                pass
        
        # Return default
        return default_value
    
    def get_batch_size(self) -> int:
        """Get batch size with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('batch_size', DEFAULT_BATCH_SIZE, 'int')
    
    def get_max_batches(self) -> int:
        """Get max batches with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('max_batches', DEFAULT_MAX_BATCHES, 'int')
    
    def get_ignore_errors(self) -> bool:
        """Get ignore_errors with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('ignore_errors', DEFAULT_IGNORE_ERRORS, 'bool')
    
    def get_no_image_import(self) -> bool:
        """Get no_image_import with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('no_image_import', DEFAULT_NO_IMAGE_IMPORT, 'bool')
    
    def get_source_path(self) -> str:
        """Get source path with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('source_path', '')
    
    def get_target_config(self) -> str:
        """Get target config with proper precedence: cmd_line > config.ini > default."""
        return self._get_config_value('target_config', '')
    
    def get_wipe_mode(self) -> Optional[str]:
        """Get wipe mode with proper precedence: cmd_line > config.ini > default."""
        # Check command line first
        cmd_args = self._get_cmd_line_args()
        if cmd_args:
            if cmd_args.wipe_hard:
                return 'hard'
            elif cmd_args.wipe:
                return 'soft'
        
        # Check config.ini
        if self._user_config and self._user_config.has_section('defaults'):
            wipe_mode = self._user_config['defaults'].get('wipe_mode', 'null')
            if wipe_mode in ['soft', 'hard']:
                return wipe_mode
        
        return DEFAULT_WIPE_MODE


# Global config instance
config = Config() 