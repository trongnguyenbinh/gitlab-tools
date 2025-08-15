"""
Configuration module for GitLab Cloner.

This module provides configuration management and validation for the GitLab cloner tool.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import json


class Config:
    """Configuration manager for GitLab cloner."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        return os.path.join(os.path.expanduser("~"), ".gitlab_cloner_config.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except IOError:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    def validate_gitlab_url(self, url: str) -> bool:
        """
        Validate GitLab URL format.
        
        Args:
            url: GitLab URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        url = url.lower()
        return url.startswith(('http://', 'https://'))
    
    def validate_access_token(self, token: str) -> bool:
        """
        Validate GitLab access token format.
        
        Args:
            token: Access token to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not token:
            return False
        
        # GitLab personal access tokens typically start with 'glpat-'
        # But we'll accept any non-empty string for flexibility
        return len(token.strip()) > 0
    
    def validate_destination_path(self, path: str) -> bool:
        """
        Validate destination path.
        
        Args:
            path: Destination path to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not path:
            return False
        
        try:
            path_obj = Path(path)
            # Check if parent directory exists or can be created
            parent = path_obj.parent
            return parent.exists() or parent == path_obj
        except (OSError, ValueError):
            return False


# Default configuration values
DEFAULT_CONFIG = {
    "clone_timeout": 300,  # 5 minutes
    "api_timeout": 30,     # 30 seconds
    "max_retries": 3,
    "retry_delay": 1,      # 1 second
    "concurrent_clones": 1, # Number of concurrent clone operations
    "skip_existing": True,
    "use_ssh": False,      # Use SSH URLs instead of HTTPS
}
