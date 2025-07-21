"""Telegram message handling logic."""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from core.database import Database, ForwardingPair
from core.telegram_destination import TelegramDestination
from core.discord_relay import DiscordRelay


class TelegramMessageHandler:
    """Handles message forwarding from Telegram source to Discord."""
    
    def __init__(self, database: Database, discord_relay: DiscordRelay, telegram_destination: TelegramDestination):
        self.database = database
        self.discord_relay = discord_relay
        self.telegram_destination = telegram_destination
    
    async def handle_telegram_message(self, event_type: str, message_data: Dict[str, Any]):
        """Handle incoming Telegram messages from source."""
        try:
            if event_type == 'new':
                await self._handle_new_message(message_data)
            elif event_type == 'edit':
                await self._handle_message_edit(message_data)
            elif event_type == 'delete':
                await self._handle_message_delete(message_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")
    
    async def _handle_new_message(self, message_data: Dict[str, Any]):
        """Handle new message forwarding."""
        pair = message_data.get('pair')
        original_message = message_data.get('original_message')
        formatted_message = message_data.get('formatted_message')
        
        if not all([pair, original_message, formatted_message]):
            logger.error("Missing required message data")
            return
        
        try:
            # Forward to Discord first
            discord_message_id = await self.discord_relay.send_message_to_discord(
                channel_id=pair.discord_channel_id,
                message_data=formatted_message,
                pair_id=pair.id,
                original_message_id=original_message.id
            )
            
            if not discord_message_id:
                logger.error(f"Failed to send message to Discord for pair {pair.id}")
                return
            
            # Then forward to Telegram destination
            telegram_message_id = await self.telegram_destination.send_message(
                chat_id=pair.telegram_dest_chat_id,
                message_data=formatted_message,
                pair_id=pair.id,
                original_message_id=original_message.id,
                discord_message_id=discord_message_id
            )
            
            if telegram_message_id:
                logger.debug(f"Successfully forwarded message through pair {pair.id}")
            else:
                logger.error(f"Failed to send message to Telegram destination for pair {pair.id}")
                
        except Exception as e:
            logger.error(f"Error forwarding new message for pair {pair.id}: {e}")
    
    async def _handle_message_edit(self, message_data: Dict[str, Any]):
        """Handle message edit forwarding."""
        pair = message_data.get('pair')
        original_message = message_data.get('original_message')
        formatted_message = message_data.get('formatted_message')
        mapping = message_data.get('mapping')
        
        if not all([pair, original_message, formatted_message, mapping]):
            logger.error("Missing required edit message data")
            return
        
        try:
            # Edit Discord message
            discord_success = await self.discord_relay.edit_discord_message(
                channel_id=pair.discord_channel_id,
                message_id=mapping.discord_message_id,
                new_content=formatted_message.get('text', '')
            )
            
            # Edit Telegram destination message (if it's text)
            telegram_success = False
            if formatted_message.get('type') == 'text':
                telegram_success = await self.telegram_destination.edit_message(
                    chat_id=pair.telegram_dest_chat_id,
                    message_id=mapping.telegram_dest_id,
                    message_data=formatted_message
                )
            
            if discord_success or telegram_success:
                logger.debug(f"Successfully edited message for pair {pair.id}")
            else:
                logger.warning(f"Failed to edit message for pair {pair.id}")
                
        except Exception as e:
            logger.error(f"Error handling message edit for pair {pair.id}: {e}")
    
    async def _handle_message_delete(self, message_data: Dict[str, Any]):
        """Handle message deletion forwarding."""
        pair = message_data.get('pair')
        mapping = message_data.get('mapping')
        deleted_id = message_data.get('deleted_id')
        
        if not all([pair, mapping]):
            logger.error("Missing required delete message data")
            return
        
        try:
            # Delete Discord message
            discord_success = await self.discord_relay.delete_discord_message(
                channel_id=pair.discord_channel_id,
                message_id=mapping.discord_message_id
            )
            
            # Delete Telegram destination message
            telegram_success = await self.telegram_destination.delete_message(
                chat_id=pair.telegram_dest_chat_id,
                message_id=mapping.telegram_dest_id
            )
            
            if discord_success or telegram_success:
                logger.debug(f"Successfully deleted message for pair {pair.id}")
            else:
                logger.warning(f"Failed to delete message for pair {pair.id}")
                
        except Exception as e:
            logger.error(f"Error handling message deletion for pair {pair.id}: {e}")
