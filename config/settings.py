"""Configuration settings for the forwarding bot."""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import yaml
from loguru import logger
from .env_loader import EnvLoader


@dataclass
class Settings:
    """Bot configuration settings."""
    
    # Database
    database_url: str = ""
    
    # Telegram Bot API (for destination and admin)
    telegram_bot_token: str = ""
    
    # Discord Bot
    discord_bot_token: str = ""
    
    # Telegram API credentials (for source - Telethon)
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    
    # Admin settings
    admin_user_ids: List[int] = field(default_factory=list)
    
    # Worker settings
    max_pairs_per_worker: int = 25
    worker_timeout: int = 300
    
    # Session encryption
    encryption_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "forwarding_bot.log"
    
    # Rate limiting
    message_rate_limit: int = 30  # messages per minute
    
    # Features
    enable_media_forwarding: bool = True
    enable_sticker_forwarding: bool = True
    enable_poll_forwarding: bool = True
    
    # File size limits (MB)
    max_file_size_mb: int = 50
    
    def __post_init__(self):
        """Post-initialization validation and environment variable loading."""
        # Initialize environment loader
        EnvLoader.load()
        
        # Core API credentials - load from environment if not set
        if not self.database_url:
            self.database_url = EnvLoader.get_str('DATABASE_URL', 'sqlite:///forwarding_bot.db')
        
        if not self.telegram_bot_token:
            self.telegram_bot_token = EnvLoader.get_str('TELEGRAM_BOT_TOKEN')
            
        if not self.discord_bot_token:
            self.discord_bot_token = EnvLoader.get_str('DISCORD_BOT_TOKEN')
            
        if not self.telegram_api_id:
            self.telegram_api_id = EnvLoader.get_str('TELEGRAM_API_ID')
            
        if not self.telegram_api_hash:
            self.telegram_api_hash = EnvLoader.get_str('TELEGRAM_API_HASH')
            
        if not self.encryption_key:
            self.encryption_key = EnvLoader.get_str('ENCRYPTION_KEY')
            
        # Load admin user IDs from environment
        if not self.admin_user_ids:
            self.admin_user_ids = EnvLoader.get_int_list('ADMIN_USER_IDS')
        
        # Load configuration settings from environment
        self.log_level = EnvLoader.get_str('LOG_LEVEL', self.log_level)
        self.log_file = EnvLoader.get_str('LOG_FILE', self.log_file)
        
        # Load numeric settings
        self.max_pairs_per_worker = EnvLoader.get_int('MAX_PAIRS_PER_WORKER', self.max_pairs_per_worker)
        self.worker_timeout = EnvLoader.get_int('WORKER_TIMEOUT', self.worker_timeout)
        self.message_rate_limit = EnvLoader.get_int('MESSAGE_RATE_LIMIT', self.message_rate_limit)
        self.max_file_size_mb = EnvLoader.get_int('MAX_FILE_SIZE_MB', self.max_file_size_mb)
        
        # Load feature toggles
        self.enable_media_forwarding = EnvLoader.get_bool('ENABLE_MEDIA_FORWARDING', self.enable_media_forwarding)
        self.enable_sticker_forwarding = EnvLoader.get_bool('ENABLE_STICKER_FORWARDING', self.enable_sticker_forwarding)
        self.enable_poll_forwarding = EnvLoader.get_bool('ENABLE_POLL_FORWARDING', self.enable_poll_forwarding)
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Settings':
        """Load settings from YAML configuration file and environment variables."""
        try:
            # First load YAML config as base
            config_data = {}
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded YAML config from {config_path}")
            except FileNotFoundError:
                logger.info(f"Config file {config_path} not found, using environment variables and defaults")
            
            # Create settings instance with config data - post_init will load env vars
            settings = cls(**config_data)
            logger.info("Settings loaded successfully with environment variable overrides")
            return settings
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Fallback to environment only
            return cls()
    
    def validate(self) -> List[str]:
        """Validate settings and return list of errors."""
        errors = []
        
        if not self.database_url:
            errors.append("database_url is required")
            
        if not self.telegram_bot_token:
            errors.append("telegram_bot_token is required")
            
        if not self.discord_bot_token:
            errors.append("discord_bot_token is required")
            
        if not self.telegram_api_id:
            errors.append("telegram_api_id is required")
            
        if not self.telegram_api_hash:
            errors.append("telegram_api_hash is required")
            
        if not self.admin_user_ids:
            errors.append("At least one admin_user_id is required")
            
        if self.max_pairs_per_worker < 1:
            errors.append("max_pairs_per_worker must be positive")
            
        if self.message_rate_limit < 1:
            errors.append("message_rate_limit must be positive")
            
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            'database_url': self.database_url,
            'telegram_bot_token': '***' if self.telegram_bot_token else '',
            'discord_bot_token': '***' if self.discord_bot_token else '',
            'telegram_api_id': '***' if self.telegram_api_id else '',
            'telegram_api_hash': '***' if self.telegram_api_hash else '',
            'admin_user_ids': self.admin_user_ids,
            'max_pairs_per_worker': self.max_pairs_per_worker,
            'worker_timeout': self.worker_timeout,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'message_rate_limit': self.message_rate_limit,
            'enable_media_forwarding': self.enable_media_forwarding,
            'enable_sticker_forwarding': self.enable_sticker_forwarding,
            'enable_poll_forwarding': self.enable_poll_forwarding,
            'max_file_size_mb': self.max_file_size_mb
        }
    
    def save_to_file(self, config_path: str) -> bool:
        """Save current settings to YAML file."""
        try:
            config_data = self.to_dict()
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            logger.info(f"Settings saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {config_path}: {e}")
            return False