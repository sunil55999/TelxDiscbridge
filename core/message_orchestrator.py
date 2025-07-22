"""Message orchestrator for coordinating forwarding between platforms."""

import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger

from core.database import Database, ForwardingPair
from core.telegram_source import TelegramSource
from core.telegram_destination import TelegramDestination
from core.discord_relay import DiscordRelay
from core.session_manager import SessionManager
from handlers.telegram_handler import TelegramMessageHandler
from handlers.discord_handler import DiscordMessageHandler


class MessageOrchestrator:
    """Orchestrates message flow between Telegram source, Discord relay, and Telegram destination."""
    
    def __init__(self, 
                 database: Database,
                 telegram_source: TelegramSource,
                 telegram_destination: TelegramDestination,
                 discord_relay: DiscordRelay,
                 session_manager: SessionManager):
        
        self.database = database
        self.telegram_source = telegram_source
        self.telegram_destination = telegram_destination
        self.discord_relay = discord_relay
        self.session_manager = session_manager
        
        # Message handlers
        self.telegram_handler = TelegramMessageHandler(
            database, discord_relay, telegram_destination
        )
        self.discord_handler = DiscordMessageHandler(database)
        
        self.running = False
    
    async def start(self):
        """Start the message orchestrator."""
        if self.running:
            logger.warning("Message orchestrator is already running")
            return
        
        logger.info("Starting message orchestrator...")
        
        try:
            # Set up message callbacks
            self._setup_message_callbacks()
            
            self.running = True
            logger.info("Message orchestrator started successfully")
            
            # Start monitoring and cleanup tasks as background tasks
            asyncio.create_task(self._monitor_message_flow())
            asyncio.create_task(self._cleanup_old_data())
            
        except Exception as e:
            logger.error(f"Failed to start message orchestrator: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the message orchestrator."""
        if not self.running:
            return
        
        logger.info("Stopping message orchestrator...")
        self.running = False
        
        # Remove callbacks
        self.telegram_source.set_message_callback(None)
        self.discord_relay.set_message_callback(None)
        
        logger.info("Message orchestrator stopped")
    
    def _setup_message_callbacks(self):
        """Setup message callbacks for all platforms."""
        # Set Telegram source callback
        self.telegram_source.set_message_callback(self._handle_telegram_source_message)
        
        # Set Discord relay callback (for future reverse forwarding)
        self.discord_relay.set_message_callback(self._handle_discord_message)
    
    async def _handle_telegram_source_message(self, event_type: str, message_data: Dict[str, Any]):
        """Handle messages from Telegram source."""
        try:
            logger.debug(f"Processing Telegram source message: {event_type}")
            await self.telegram_handler.handle_telegram_message(event_type, message_data)
            
        except Exception as e:
            logger.error(f"Error handling Telegram source message: {e}")
    
    async def _handle_discord_message(self, event_type: str, message_data: Dict[str, Any]):
        """Handle Discord messages (for monitoring)."""
        try:
            logger.debug(f"Processing Discord message: {event_type}")
            await self.discord_handler.handle_discord_message(event_type, message_data)
            
        except Exception as e:
            logger.error(f"Error handling Discord message: {e}")
    
    async def _monitor_message_flow(self):
        """Monitor message flow and health."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                if not self.running:
                    break
                
                # Basic health monitoring
                pairs = await self.database.get_all_pairs()
                active_pairs = [p for p in pairs if p.is_active]
                
                logger.debug(f"Health check: {len(active_pairs)} active pairs")
                
                # Check if components are still running
                if not self.telegram_source.running:
                    logger.warning("Telegram source is not running")
                
                if not self.telegram_destination.running:
                    logger.warning("Telegram destination is not running")
                
                if not self.discord_relay.running:
                    logger.warning("Discord relay is not running")
                
            except Exception as e:
                logger.error(f"Error in message flow monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_old_data(self):
        """Cleanup old message mappings and data."""
        while self.running:
            try:
                # Wait 24 hours between cleanups
                await asyncio.sleep(24 * 60 * 60)
                
                if not self.running:
                    break
                
                logger.info("Starting scheduled cleanup...")
                
                # Cleanup old message mappings (older than 30 days)
                await self.database.cleanup_old_mappings(days=30)
                
                logger.info("Scheduled cleanup completed")
                
            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour before retrying
    
    async def reload_pairs(self):
        """Reload forwarding pairs and update all components."""
        try:
            logger.info("Reloading forwarding pairs...")
            
            # Reload pairs in Telegram source
            await self.telegram_source.reload_pairs()
            
            # Get updated pairs for validation
            pairs = await self.database.get_all_pairs()
            logger.info(f"Reloaded {len(pairs)} forwarding pairs")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload pairs: {e}")
            return False
    
    async def test_pair_connectivity(self, pair_id: int) -> Dict[str, Any]:
        """Test connectivity for a specific forwarding pair."""
        try:
            pair = await self.database.get_pair(pair_id)
            if not pair:
                return {
                    'success': False,
                    'error': f'Pair {pair_id} not found'
                }
            
            results = {}
            
            # Test Telegram source access
            telegram_access = await self.telegram_source.test_session_access(
                pair.session_name, [pair.telegram_source_chat_id]
            )
            results['telegram_source'] = telegram_access.get(pair.telegram_source_chat_id, False)
            
            # Test Discord channel access
            discord_access = await self.discord_relay.test_channel_access([pair.discord_channel_id])
            results['discord_channel'] = discord_access.get(pair.discord_channel_id, False)
            
            # Test Telegram destination access
            telegram_dest_access = await self.telegram_destination.test_bot_access([pair.telegram_dest_chat_id])
            results['telegram_destination'] = telegram_dest_access.get(pair.telegram_dest_chat_id, False)
            
            # Overall success
            all_connected = all(results.values())
            
            return {
                'success': all_connected,
                'pair_id': pair_id,
                'pair_name': pair.name,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Error testing pair connectivity for {pair_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            pairs = await self.database.get_all_pairs()
            active_pairs = [p for p in pairs if p.is_active]
            
            # Group pairs by session
            session_stats = {}
            for pair in active_pairs:
                if pair.session_name not in session_stats:
                    session_stats[pair.session_name] = 0
                session_stats[pair.session_name] += 1
            
            # Component status
            component_status = {
                'telegram_source': self.telegram_source.running,
                'telegram_destination': self.telegram_destination.running,
                'discord_relay': self.discord_relay.running,
                'orchestrator': self.running
            }
            
            stats = {
                'total_pairs': len(pairs),
                'active_pairs': len(active_pairs),
                'inactive_pairs': len(pairs) - len(active_pairs),
                'unique_sessions': len(session_stats),
                'session_distribution': session_stats,
                'component_status': component_status,
                'all_systems_operational': all(component_status.values())
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                'error': str(e),
                'all_systems_operational': False
            }
    
    async def restart_session(self, session_name: str) -> bool:
        """Restart a specific session."""
        try:
            logger.info(f"Restarting session: {session_name}")
            
            # Restart the client for this session
            await self.telegram_source.restart_client(session_name)
            
            logger.info(f"Successfully restarted session: {session_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart session {session_name}: {e}")
            return False
    
    async def force_gc_cleanup(self):
        """Force garbage collection and memory cleanup."""
        try:
            import gc
            
            logger.info("Starting forced garbage collection...")
            
            # Force garbage collection
            collected = gc.collect()
            
            # Clean up message handler caches if any
            # This could be expanded to clean component-specific caches
            
            logger.info(f"Garbage collection completed, collected {collected} objects")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during forced cleanup: {e}")
            return False
    
    async def update_pair_settings(self, pair_id: int, settings: Dict[str, Any]) -> bool:
        """Update settings for a specific pair."""
        try:
            pair = await self.database.get_pair(pair_id)
            if not pair:
                logger.error(f"Pair {pair_id} not found")
                return False
            
            # Update allowed settings
            if 'name' in settings:
                pair.name = settings['name']
            if 'is_active' in settings:
                pair.is_active = settings['is_active']
            if 'keyword_filters' in settings:
                pair.keyword_filters = settings['keyword_filters']
            if 'media_enabled' in settings:
                pair.media_enabled = settings['media_enabled']
            if 'session_name' in settings:
                # Validate session exists
                session_info = await self.session_manager.get_session(settings['session_name'])
                if session_info:
                    pair.session_name = settings['session_name']
                else:
                    logger.error(f"Session {settings['session_name']} not found")
                    return False
            
            # Save changes
            success = await self.database.update_pair(pair)
            
            if success:
                # Reload pairs to apply changes
                await self.reload_pairs()
                logger.info(f"Updated settings for pair {pair_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating pair settings for {pair_id}: {e}")
            return False
