"""Discord message handling logic (for monitoring purposes)."""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from core.database import Database


class DiscordMessageHandler:
    """Handles Discord messages (primarily for monitoring and logging)."""
    
    def __init__(self, database: Database):
        self.database = database
    
    async def handle_discord_message(self, event_type: str, message_data: Dict[str, Any]):
        """Handle Discord messages for monitoring purposes."""
        try:
            if event_type == 'new':
                await self._handle_new_discord_message(message_data)
            elif event_type == 'edit':
                await self._handle_discord_message_edit(message_data)
            elif event_type == 'delete':
                await self._handle_discord_message_delete(message_data)
            else:
                logger.debug(f"Unknown Discord event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling Discord message: {e}")
    
    async def _handle_new_discord_message(self, message_data: Dict[str, Any]):
        """Handle new Discord messages (monitoring only)."""
        # This could be used for monitoring Discord activity
        # or implementing reverse forwarding if needed in the future
        channel_id = message_data.get('channel_id')
        content = message_data.get('content', '')[:100]  # First 100 chars for logging
        
        logger.debug(f"Discord message in channel {channel_id}: {content}...")
    
    async def _handle_discord_message_edit(self, message_data: Dict[str, Any]):
        """Handle Discord message edits (monitoring only)."""
        channel_id = message_data.get('channel_id')
        message_id = message_data.get('message_id')
        
        logger.debug(f"Discord message edited in channel {channel_id}, message ID: {message_id}")
    
    async def _handle_discord_message_delete(self, message_data: Dict[str, Any]):
        """Handle Discord message deletions (monitoring only)."""
        channel_id = message_data.get('channel_id')
        message_id = message_data.get('message_id')
        
        logger.debug(f"Discord message deleted in channel {channel_id}, message ID: {message_id}")
