"""Environment variable loader that works with both .env files and system variables."""

import os
import pathlib
from typing import Optional
from loguru import logger

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv not installed, .env files won't be loaded")


class EnvLoader:
    """Unified environment variable loader."""
    
    _loaded = False
    
    @classmethod
    def load(cls):
        """Load environment variables from .env file if available."""
        if cls._loaded:
            return
            
        if DOTENV_AVAILABLE:
            env_file = pathlib.Path('.env')
            if env_file.exists():
                load_dotenv()
                logger.info("Loaded environment variables from .env file")
                cls._loaded = True
                return
        
        logger.info("Using system environment variables")
        cls._loaded = True
    
    @staticmethod
    def get_str(key: str, default: str = "") -> str:
        """Get string environment variable."""
        EnvLoader.load()
        return os.getenv(key, default)
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """Get integer environment variable."""
        EnvLoader.load()
        try:
            value = os.getenv(key)
            return int(value) if value else default
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        EnvLoader.load()
        value = os.getenv(key, "").lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        else:
            return default
    
    @staticmethod
    def get_list(key: str, default: Optional[list] = None, separator: str = ",") -> list:
        """Get list environment variable (comma-separated by default)."""
        EnvLoader.load()
        if default is None:
            default = []
            
        value = os.getenv(key, "")
        if not value:
            return default
            
        try:
            return [item.strip() for item in value.split(separator) if item.strip()]
        except Exception as e:
            logger.warning(f"Failed to parse list for {key}: {e}")
            return default
    
    @staticmethod
    def get_int_list(key: str, default: Optional[list] = None, separator: str = ",") -> list:
        """Get list of integers from environment variable."""
        EnvLoader.load()
        if default is None:
            default = []
            
        str_list = EnvLoader.get_list(key, [], separator)
        try:
            return [int(item) for item in str_list if item]
        except ValueError as e:
            logger.warning(f"Failed to parse integer list for {key}: {e}")
            return default