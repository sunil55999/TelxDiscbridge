#!/usr/bin/env python3
"""
Main entry point for the Telegram → Discord → Telegram forwarding bot.
"""

import asyncio
import os
import signal
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger

from config.settings import Settings

load_dotenv()
from core.database import Database
from core.session_manager import SessionManager
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
        self.session_manager = SessionManager(self.database, self.settings)
        
        # Initialize Telegram source client
        self.telegram_source = TelegramSource(self.session_manager, self.database)
        
        # Initialize Telegram destination bot
        self.telegram_destination = TelegramDestination(
            self.settings.telegram_bot_token, self.database
        )
        
        # Initialize Discord relay
        self.discord_relay = DiscordRelay(
            self.settings.discord_bot_token, self.database
        )
        
        # Initialize admin handler
        self.admin_handler = AdminHandler(
            self.settings.telegram_bot_token,
            self.database,
            self.session_manager,
            self.settings.admin_user_ids
        )
        
        logger.info("All components initialized successfully")
    
    async def start(self):
        """Start all bot components."""
        if self.running:
            logger.warning("Bot is already running")
            return
            
        logger.info("Starting forwarding bot...")
        self.running = True
        
        try:
            # Start all components concurrently
            await asyncio.gather(
                self.telegram_source.start(),
                self.telegram_destination.start(),
                self.discord_relay.start(),
                self.admin_handler.start(),
                self._monitor_health()
            )
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
