"""Bot token management and validation for per-pair Telegram bots."""

import asyncio
from typing import Dict, Optional, Any
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden
from loguru import logger

from utils.encryption import EncryptionManager
from core.database import Database, ForwardingPair


class BotTokenValidator:
    """Validates and tests bot tokens for forwarding pairs."""
    
    @staticmethod
    async def validate_bot_token(token: str) -> Dict[str, Any]:
        """
        Validate a bot token using Telegram Bot API.
        
        Returns:
            Dict with validation results including bot info and permissions
        """
        try:
            bot = Bot(token=token)
            
            # Test basic bot connectivity
            me = await bot.get_me()
            
            return {
                'valid': True,
                'bot_id': me.id,
                'username': me.username,
                'first_name': me.first_name,
                'can_join_groups': me.can_join_groups,
                'can_read_all_group_messages': me.can_read_all_group_messages,
                'supports_inline_queries': me.supports_inline_queries,
                'error': None
            }
            
        except Forbidden:
            return {
                'valid': False,
                'error': 'Invalid bot token - unauthorized access'
            }
        except BadRequest as e:
            return {
                'valid': False,
                'error': f'Bad request: {str(e)}'
            }
        except TelegramError as e:
            return {
                'valid': False,
                'error': f'Telegram API error: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @staticmethod
    async def validate_chat_permissions(token: str, chat_id: int) -> Dict[str, Any]:
        """
        Validate bot permissions in a specific chat.
        
        Returns:
            Dict with permission validation results
        """
        try:
            bot = Bot(token=token)
            
            # Try to get chat member (bot) info
            chat_member = await bot.get_chat_member(chat_id, bot.id)
            
            # Check bot permissions
            can_send_messages = True
            can_send_media = True
            can_edit_messages = True
            can_delete_messages = True
            
            if hasattr(chat_member, 'can_send_messages'):
                can_send_messages = chat_member.can_send_messages
            if hasattr(chat_member, 'can_send_media_messages'):
                can_send_media = chat_member.can_send_media_messages
            if hasattr(chat_member, 'can_edit_messages'):
                can_edit_messages = chat_member.can_edit_messages
            if hasattr(chat_member, 'can_delete_messages'):
                can_delete_messages = chat_member.can_delete_messages
            
            return {
                'valid': True,
                'status': chat_member.status,
                'can_send_messages': can_send_messages,
                'can_send_media': can_send_media,
                'can_edit_messages': can_edit_messages,
                'can_delete_messages': can_delete_messages,
                'error': None
            }
            
        except BadRequest as e:
            if 'chat not found' in str(e).lower():
                return {
                    'valid': False,
                    'error': 'Chat not found - check chat ID'
                }
            elif 'bot is not a member' in str(e).lower():
                return {
                    'valid': False,
                    'error': 'Bot is not a member of this chat - please add the bot first'
                }
            else:
                return {
                    'valid': False,
                    'error': f'Permission error: {str(e)}'
                }
        except TelegramError as e:
            return {
                'valid': False,
                'error': f'Telegram API error: {str(e)}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @staticmethod
    async def send_test_message(token: str, chat_id: int) -> Dict[str, Any]:
        """
        Send a test message to verify posting capabilities.
        
        Returns:
            Dict with test results
        """
        try:
            bot = Bot(token=token)
            
            # Send test message
            test_message = "🤖 Bot token validation successful! This message will be deleted shortly."
            message = await bot.send_message(chat_id, test_message)
            
            # Try to delete the test message after a short delay
            await asyncio.sleep(2)
            try:
                await bot.delete_message(chat_id, message.message_id)
            except Exception:
                # Deletion failed, but sending worked
                pass
            
            return {
                'valid': True,
                'message_id': message.message_id,
                'error': None
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Test message failed: {str(e)}'
            }


class PerPairBotManager:
    """Manages individual bot instances for each forwarding pair."""
    
    def __init__(self, database: Database, encryption_manager: EncryptionManager):
        self.database = database
        self.encryption_manager = encryption_manager
        self.active_bots: Dict[int, Bot] = {}  # pair_id -> Bot instance
        
    async def get_bot_for_pair(self, pair_id: int) -> Optional[Bot]:
        """Get or create a bot instance for a specific pair."""
        if pair_id in self.active_bots:
            return self.active_bots[pair_id]
        
        # Load pair from database
        pair = await self.database.get_pair(pair_id)
        if not pair or not pair.telegram_bot_token_encrypted:
            logger.error(f"No bot token found for pair {pair_id}")
            return None
        
        try:
            # Decrypt bot token
            decrypted_token = self.encryption_manager.decrypt(pair.telegram_bot_token_encrypted)
            
            # Create bot instance
            bot = Bot(token=decrypted_token)
            
            # Test bot connectivity
            await bot.get_me()
            
            # Cache bot instance
            self.active_bots[pair_id] = bot
            logger.info(f"Created bot instance for pair {pair_id}")
            
            return bot
            
        except Exception as e:
            logger.error(f"Failed to create bot for pair {pair_id}: {e}")
            return None
    
    async def validate_pair_bot_token(self, pair_id: int) -> Dict[str, Any]:
        """Validate the bot token for a specific pair."""
        pair = await self.database.get_pair(pair_id)
        if not pair or not pair.telegram_bot_token_encrypted:
            return {
                'valid': False,
                'error': 'No bot token configured for this pair'
            }
        
        try:
            # Decrypt token
            decrypted_token = self.encryption_manager.decrypt(pair.telegram_bot_token_encrypted)
            
            # Validate token
            validation_result = await BotTokenValidator.validate_bot_token(decrypted_token)
            
            if validation_result['valid']:
                # Also validate chat permissions
                chat_validation = await BotTokenValidator.validate_chat_permissions(
                    decrypted_token, pair.telegram_dest_chat_id
                )
                validation_result['chat_permissions'] = chat_validation
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Token validation failed: {str(e)}'
            }
    
    async def remove_bot_for_pair(self, pair_id: int):
        """Remove bot instance for a pair."""
        if pair_id in self.active_bots:
            try:
                bot = self.active_bots[pair_id]
                # Close bot session if possible
                async with bot:
                    pass
            except Exception as e:
                logger.warning(f"Error closing bot for pair {pair_id}: {e}")
            finally:
                del self.active_bots[pair_id]
                logger.info(f"Removed bot instance for pair {pair_id}")
    
    async def cleanup_all_bots(self):
        """Clean up all bot instances."""
        for pair_id in list(self.active_bots.keys()):
            await self.remove_bot_for_pair(pair_id)
        
        logger.info("All bot instances cleaned up")
    
    async def refresh_bot_for_pair(self, pair_id: int) -> Optional[Bot]:
        """Refresh bot instance for a pair (remove and recreate)."""
        await self.remove_bot_for_pair(pair_id)
        return await self.get_bot_for_pair(pair_id)