#!/usr/bin/env python3
"""
Main entry point for the Telegram → Discord → Telegram forwarding bot.
"""

import asyncio
import os
import signal
import sys
from typing import Dict, List, Optional

from loguru import logger
# Environment variables will be loaded by the Settings class

from config.settings import Settings
from core.database import Database
from core.session_manager import SessionManager
from core.advanced_session_manager import AdvancedSessionManager
from core.telegram_source import TelegramSource
from core.telegram_destination import TelegramDestination
from core.discord_relay import DiscordRelay
from admin_bot.admin_handler import AdminHandler


class ForwardingBot:
    """Main bot orchestrator."""
    
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.database: Optional[Database] = None
        self.session_manager: Optional[SessionManager] = None
        self.advanced_session_manager: Optional[AdvancedSessionManager] = None
        self.telegram_source: Optional[TelegramSource] = None
        self.telegram_destination: Optional[TelegramDestination] = None
        self.discord_relay: Optional[DiscordRelay] = None
        self.admin_handler: Optional[AdminHandler] = None
        self.running = False
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing forwarding bot...")
        
        # Load settings
        self.settings = Settings.load_from_file("config.yaml")
        
        # Validate settings
        validation_errors = self.settings.validate()
        if validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in validation_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize database
        self.database = Database(self.settings.database_url)
        await self.database.initialize()
        
        # Initialize session manager
        self.session_manager = SessionManager(self.database, self.settings.encryption_key)
        
        # Initialize advanced session manager
        self.advanced_session_manager = AdvancedSessionManager(self.database, self.session_manager)
        
        # Initialize Telegram source client
        self.telegram_source = TelegramSource(self.session_manager, self.database)
        
        # Initialize Telegram destination service (uses per-pair bot tokens)
        from utils.encryption import EncryptionManager
        from core.message_filter import MessageFilter
        encryption_manager = EncryptionManager(self.settings.encryption_key)
        self.telegram_destination = TelegramDestination(
            self.database, encryption_manager
        )
        
        # Initialize message filter
        self.message_filter = MessageFilter(self.database)
        await self.message_filter.initialize()
        
        # Initialize Discord relay
        self.discord_relay = DiscordRelay(
            self.settings.discord_bot_token, self.database
        )
        
        # Initialize admin handler
        self.admin_handler = AdminHandler(
            self.settings.telegram_bot_token,
            self.database,
            self.session_manager,
            self.settings.admin_user_ids,
            self.advanced_session_manager,
            self.settings.encryption_key
        )
        
        # Initialize image hash manager
        from utils.image_hash import image_hash_manager
        image_hash_manager.database = self.database
        await image_hash_manager.initialize()
        
        logger.info("All components initialized successfully")
    
    async def start(self):
        """Start all bot components."""
        if self.running:
            logger.warning("Bot is already running")
            return
            
        logger.info("Starting forwarding bot...")
        self.running = True
        
        try:
            # Start non-blocking components first
            await self.advanced_session_manager.start()
            await self.telegram_source.start()
            await self.telegram_destination.start()
            await self.discord_relay.start()
            
            # Start admin handler and health monitor as background tasks
            admin_task = asyncio.create_task(self.admin_handler.start())
            health_task = asyncio.create_task(self._monitor_health())
            
            # Wait for tasks to complete or fail
            await asyncio.gather(admin_task, health_task)
        except Exception as e:
            logger.error(f"Error during bot startup: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all bot components."""
        if not self.running:
            return
            
        logger.info("Stopping forwarding bot...")
        self.running = False
        
        # Stop all components
        stop_tasks = []
        if self.admin_handler:
            stop_tasks.append(self.admin_handler.stop())
        if self.discord_relay:
            stop_tasks.append(self.discord_relay.stop())
        if self.telegram_destination:
            stop_tasks.append(self.telegram_destination.stop())
        if self.telegram_source:
            stop_tasks.append(self.telegram_source.stop())
        if self.advanced_session_manager:
            stop_tasks.append(self.advanced_session_manager.stop())
        if self.database:
            stop_tasks.append(self.database.close())
            
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        logger.info("Bot stopped successfully")
    
    async def _monitor_health(self):
        """Monitor system health and log status."""
        while self.running:
            try:
                # Basic health check every 5 minutes
                await asyncio.sleep(300)
                if not self.running:
                    break
                    
                logger.debug("Health check: Bot is running normally")
                
                # Check active forwarding pairs
                pairs = await self.database.get_all_pairs()
                logger.debug(f"Active forwarding pairs: {len(pairs)}")
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(60)  # Wait before retrying


async def main():
    """Main application entry point."""
    bot = ForwardingBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Ensure event loop policy is set correctly
    if sys.platform.startswith('win'):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except AttributeError:
            # Fallback for older Python versions or different platforms
            pass
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        sys.exit(1)
