"""Enhanced main application with integrated improvements."""

import asyncio
import signal
import sys
from typing import Optional
from loguru import logger

from config.settings import Settings
from core.database import Database
from core.advanced_session_manager import AdvancedSessionManager
from core.session_manager import SessionManager
from core.telegram_source import TelegramSource
from core.telegram_destination import TelegramDestination
from core.discord_relay import DiscordRelay
from core.message_filter import MessageFilter
from core.alert_system import AlertSystem
from admin_bot.admin_handler import AdminHandler

# Enhanced systems
from core.error_middleware import init_error_middleware, get_error_middleware, handle_errors_async
from core.metrics_system import init_metrics_collector, get_metrics_collector
from utils.advanced_filters import AdvancedFilterSystem
from admin_bot.advanced_filter_commands import AdvancedFilterCommands


class EnhancedForwardingBot:
    """Enhanced forwarding bot with comprehensive error handling, metrics, and advanced filtering."""
    
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.database: Optional[Database] = None
        self.session_manager: Optional[SessionManager] = None
        self.advanced_session_manager: Optional[AdvancedSessionManager] = None
        self.telegram_source: Optional[TelegramSource] = None
        self.telegram_destination: Optional[TelegramDestination] = None
        self.discord_relay: Optional[DiscordRelay] = None
        self.message_filter: Optional[MessageFilter] = None
        self.alert_system: Optional[AlertSystem] = None
        self.admin_handler: Optional[AdminHandler] = None
        
        # Enhanced systems
        self.advanced_filter_system: Optional[AdvancedFilterSystem] = None
        self.advanced_filter_commands: Optional[AdvancedFilterCommands] = None
        
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._health_task: Optional[asyncio.Task] = None
    
    @handle_errors_async()
    async def initialize(self):
        """Initialize all bot components with enhanced error handling."""
        logger.info("Initializing enhanced forwarding bot...")
        
        try:
            # Load configuration
            self.settings = Settings()
            await self.settings.load_from_file("config.yaml")
            
            # Initialize database
            self.database = Database()
            await self.database.initialize(self.settings.database.url)
            
            # Initialize error middleware
            init_error_middleware(self.database)
            
            # Initialize metrics collector
            init_metrics_collector(self.database)
            metrics_collector = get_metrics_collector()
            if metrics_collector:
                await metrics_collector.start_collection()
            
            # Initialize session management
            self.session_manager = SessionManager(self.database)
            self.advanced_session_manager = AdvancedSessionManager(self.database, self.session_manager)
            
            # Initialize message filtering
            self.message_filter = MessageFilter()
            await self.message_filter.initialize()
            
            # Initialize advanced filtering system
            self.advanced_filter_system = AdvancedFilterSystem(self.database)
            
            # Initialize alert system
            self.alert_system = AlertSystem(self.database)
            
            # Initialize communication systems
            self.telegram_source = TelegramSource(
                self.database, 
                self.advanced_session_manager,
                message_filter=self.advanced_filter_system  # Use enhanced filter
            )
            
            self.telegram_destination = TelegramDestination(self.database)
            
            self.discord_relay = DiscordRelay(
                self.database,
                self.settings.discord.token,
                self.settings.discord.application_id
            )
            
            # Initialize admin bot
            self.admin_handler = AdminHandler(
                self.database,
                self.settings.telegram.admin_bot_token,
                self.settings.telegram.admin_chat_ids,
                self.advanced_session_manager,
                self.alert_system
            )
            
            # Initialize advanced filter commands
            self.advanced_filter_commands = AdvancedFilterCommands(
                self.database,
                self.advanced_filter_system
            )
            
            logger.info("All enhanced components initialized successfully")
            
        except Exception as e:
            logger.critical(f"Failed to initialize enhanced bot: {e}")
            error_middleware = get_error_middleware()
            if error_middleware:
                await error_middleware._handle_error(e, None)
            raise
    
    @handle_errors_async()
    async def start(self):
        """Start the enhanced bot with comprehensive monitoring."""
        if self.running:
            logger.warning("Enhanced bot is already running")
            return
        
        logger.info("Starting enhanced forwarding bot...")
        self.running = True
        
        try:
            # Start core systems
            await self.advanced_session_manager.start()
            await self.telegram_source.start()
            await self.telegram_destination.start()
            await self.alert_system.start()
            
            # Start admin bot with enhanced filter commands
            await self.admin_handler.start()
            if self.advanced_filter_commands:
                self.advanced_filter_commands.register_handlers(self.admin_handler.application)
            
            # Start Discord relay
            asyncio.create_task(self.discord_relay.start())
            
            # Start health monitoring
            self._health_task = asyncio.create_task(self._enhanced_health_monitor())
            
            # Record startup metrics
            metrics_collector = get_metrics_collector()
            if metrics_collector:
                metrics_collector.increment_counter("bot_startups_total")
            
            logger.info("Enhanced forwarding bot started successfully")
            
        except Exception as e:
            logger.critical(f"Failed to start enhanced bot: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the enhanced bot gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping enhanced forwarding bot...")
        self.running = False
        self._shutdown_event.set()
        
        try:
            # Stop health monitoring
            if self._health_task and not self._health_task.done():
                self._health_task.cancel()
                try:
                    await self._health_task
                except asyncio.CancelledError:
                    pass
            
            # Stop core systems
            if self.advanced_session_manager:
                await self.advanced_session_manager.stop()
            
            if self.telegram_source:
                await self.telegram_source.stop()
            
            if self.telegram_destination:
                await self.telegram_destination.stop()
            
            if self.alert_system:
                await self.alert_system.stop()
            
            if self.admin_handler:
                await self.admin_handler.stop()
            
            if self.discord_relay:
                await self.discord_relay.stop()
            
            # Stop metrics collection
            metrics_collector = get_metrics_collector()
            if metrics_collector:
                await metrics_collector.stop_collection()
            
            logger.info("Enhanced forwarding bot stopped")
            
        except Exception as e:
            logger.error(f"Error during enhanced bot shutdown: {e}")
    
    async def _enhanced_health_monitor(self):
        """Enhanced health monitoring with metrics and alerting."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.running:
                    break
                
                # Record system health metrics
                metrics_collector = get_metrics_collector()
                if metrics_collector:
                    health_metrics = metrics_collector.get_health_metrics()
                    
                    # Check for critical conditions
                    memory_usage = health_metrics.get('system', {}).get('memory_usage_mb', 0)
                    cpu_usage = health_metrics.get('system', {}).get('cpu_usage_percent', 0)
                    error_rate = health_metrics.get('messages', {}).get('success_rate', 1.0)
                    
                    # Alert on critical conditions
                    if memory_usage > 500:  # 500MB
                        if self.alert_system:
                            await self.alert_system.send_alert(
                                level="warning",
                                title="High Memory Usage",
                                message=f"Memory usage: {memory_usage:.1f}MB",
                                source="health_monitor"
                            )
                    
                    if cpu_usage > 80:
                        if self.alert_system:
                            await self.alert_system.send_alert(
                                level="warning", 
                                title="High CPU Usage",
                                message=f"CPU usage: {cpu_usage:.1f}%",
                                source="health_monitor"
                            )
                    
                    if error_rate < 0.9:  # Less than 90% success rate
                        if self.alert_system:
                            await self.alert_system.send_alert(
                                level="error",
                                title="Low Success Rate",
                                message=f"Message success rate: {error_rate:.1%}",
                                source="health_monitor"
                            )
                
                # Log basic health status
                logger.debug("Enhanced health check: Bot is running normally")
                
                # Check component health
                active_pairs = 0
                if self.database:
                    try:
                        # Get active pairs count (would need to implement this method)
                        active_pairs = await self._get_active_pairs_count()
                    except Exception as e:
                        logger.warning(f"Could not get active pairs count: {e}")
                
                logger.debug(f"Active forwarding pairs: {active_pairs}")
                
            except Exception as e:
                logger.error(f"Error in enhanced health monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _get_active_pairs_count(self) -> int:
        """Get count of active forwarding pairs."""
        try:
            if self.database:
                # This would be implemented in the database class
                return 0  # Placeholder
        except Exception as e:
            logger.error(f"Error getting active pairs count: {e}")
        return 0
    
    async def get_status(self) -> dict:
        """Get comprehensive bot status."""
        try:
            status = {
                "running": self.running,
                "components": {},
                "metrics": {},
                "health": "healthy"
            }
            
            # Component status
            status["components"] = {
                "database": self.database is not None,
                "session_manager": self.advanced_session_manager is not None,
                "telegram_source": self.telegram_source is not None,
                "telegram_destination": self.telegram_destination is not None,
                "discord_relay": self.discord_relay is not None,
                "admin_handler": self.admin_handler is not None,
                "alert_system": self.alert_system is not None,
                "advanced_filters": self.advanced_filter_system is not None
            }
            
            # Get metrics
            metrics_collector = get_metrics_collector()
            if metrics_collector:
                status["metrics"] = metrics_collector.get_health_metrics()
            
            # Get error statistics
            error_middleware = get_error_middleware()
            if error_middleware:
                status["errors"] = error_middleware.get_error_statistics()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"running": False, "error": str(e)}


# Global bot instance
enhanced_bot: Optional[EnhancedForwardingBot] = None


async def main():
    """Enhanced main function with comprehensive error handling."""
    global enhanced_bot
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        if enhanced_bot:
            asyncio.create_task(enhanced_bot.stop())
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and initialize enhanced bot
        enhanced_bot = EnhancedForwardingBot()
        await enhanced_bot.initialize()
        
        # Start the bot
        await enhanced_bot.start()
        
        # Wait for shutdown signal
        await enhanced_bot._shutdown_event.wait()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
        sys.exit(1)
    finally:
        if enhanced_bot:
            await enhanced_bot.stop()


if __name__ == "__main__":
    asyncio.run(main())