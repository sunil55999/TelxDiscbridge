"""Telegram destination handler using per-pair bot tokens."""

import asyncio
from typing import Dict, List, Optional, Any
from io import BytesIO

from telegram import Bot, Message as TgMessage, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ParseMode, MessageLimit
from loguru import logger

from core.database import Database, MessageMapping
from core.bot_token_manager import PerPairBotManager
from utils.encryption import EncryptionManager


class TelegramDestination:
    """Handles sending messages to destination Telegram chats using per-pair bot tokens."""
    
    def __init__(self, database: Database, encryption_manager: EncryptionManager):
        self.database = database
        self.encryption_manager = encryption_manager
        self.bot_manager = PerPairBotManager(database, encryption_manager)
        self.running = False
    
    async def start(self):
        """Start the Telegram destination service."""
        if self.running:
            logger.warning("Telegram destination service is already running")
            return
        
        try:
            logger.info("Telegram destination service started (using per-pair bot tokens)")
            self.running = True
            
        except Exception as e:
            logger.error(f"Failed to start Telegram destination service: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram destination service."""
        if not self.running:
            return
        
        logger.info("Stopping Telegram destination service...")
        self.running = False
        
        # Clean up all bot instances
        await self.bot_manager.cleanup_all_bots()
        
        logger.info("Telegram destination service stopped")
    
    async def send_message(self, chat_id: int, message_data: Dict[str, Any], pair_id: int, original_message_id: int, discord_message_id: int) -> Optional[int]:
        """Send a message to a destination chat using the pair's bot token."""
        if not self.running:
            logger.error("Telegram destination service is not running")
            return None
        
        # Get bot instance for this pair
        bot = await self.bot_manager.get_bot_for_pair(pair_id)
        if not bot:
            logger.error(f"Failed to get bot instance for pair {pair_id}")
            return None
        
        try:
            sent_message = None
            
            # Handle different message types
            message_type = message_data.get('type', 'text')
            
            if message_type == 'text':
                sent_message = await self._send_text_message(bot, chat_id, message_data)
            elif message_type == 'photo':
                sent_message = await self._send_photo_message(bot, chat_id, message_data)
            elif message_type == 'document':
                sent_message = await self._send_document_message(bot, chat_id, message_data)
            elif message_type == 'video':
                sent_message = await self._send_video_message(bot, chat_id, message_data)
            elif message_type == 'audio':
                sent_message = await self._send_audio_message(bot, chat_id, message_data)
            elif message_type == 'sticker':
                sent_message = await self._send_sticker_message(bot, chat_id, message_data)
            elif message_type == 'poll':
                sent_message = await self._send_poll_message(bot, chat_id, message_data)
            else:
                logger.warning(f"Unsupported message type: {message_type}")
                return None
            
            if sent_message:
                # Store message mapping
                mapping = MessageMapping(
                    pair_id=pair_id,
                    telegram_source_id=original_message_id,
                    discord_message_id=discord_message_id,
                    telegram_dest_id=sent_message.message_id
                )
                await self.database.add_message_mapping(mapping)
                
                logger.debug(f"Sent message to chat {chat_id}, message ID: {sent_message.message_id}")
                return sent_message.message_id
            
        except Forbidden as e:
            logger.error(f"Bot forbidden from sending to chat {chat_id}: {e}")
        except BadRequest as e:
            logger.error(f"Bad request when sending to chat {chat_id}: {e}")
        except TelegramError as e:
            logger.error(f"Telegram error when sending to chat {chat_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending message to chat {chat_id}: {e}")
        
        return None
    
    async def _send_text_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a text message."""
        text = message_data.get('text', '')
        if not text:
            return None
        
        # Handle long messages
        if len(text) > MessageLimit.MAX_TEXT_LENGTH:
            text = text[:MessageLimit.MAX_TEXT_LENGTH - 3] + "..."
        
        parse_mode = None
        if message_data.get('has_formatting'):
            parse_mode = ParseMode.HTML if message_data.get('format_type') == 'html' else ParseMode.MARKDOWN_V2
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=message_data.get('disable_web_preview', False)
        )
    
    async def _send_photo_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a photo message."""
        photo_data = message_data.get('media_data')
        caption = message_data.get('caption', '')
        
        if not photo_data:
            return None
        
        # Truncate caption if too long
        if len(caption) > MessageLimit.CAPTION_LENGTH:
            caption = caption[:MessageLimit.CAPTION_LENGTH - 3] + "..."
        
        parse_mode = None
        if message_data.get('has_formatting'):
            parse_mode = ParseMode.HTML if message_data.get('format_type') == 'html' else ParseMode.MARKDOWN_V2
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        return await bot.send_photo(
            chat_id=chat_id,
            photo=BytesIO(photo_data),
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id
        )
    
    async def _send_document_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a document message."""
        document_data = message_data.get('media_data')
        filename = message_data.get('filename', 'document')
        caption = message_data.get('caption', '')
        
        if not document_data:
            return None
        
        # Truncate caption if too long
        if len(caption) > MessageLimit.CAPTION_LENGTH:
            caption = caption[:MessageLimit.CAPTION_LENGTH - 3] + "..."
        
        parse_mode = None
        if message_data.get('has_formatting'):
            parse_mode = ParseMode.HTML if message_data.get('format_type') == 'html' else ParseMode.MARKDOWN_V2
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        document_file = BytesIO(document_data)
        document_file.name = filename
        
        return await bot.send_document(
            chat_id=chat_id,
            document=document_file,
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id
        )
    
    async def _send_video_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a video message."""
        video_data = message_data.get('media_data')
        caption = message_data.get('caption', '')
        
        if not video_data:
            return None
        
        # Truncate caption if too long
        if len(caption) > MessageLimit.CAPTION_LENGTH:
            caption = caption[:MessageLimit.CAPTION_LENGTH - 3] + "..."
        
        parse_mode = None
        if message_data.get('has_formatting'):
            parse_mode = ParseMode.HTML if message_data.get('format_type') == 'html' else ParseMode.MARKDOWN_V2
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        return await bot.send_video(
            chat_id=chat_id,
            video=BytesIO(video_data),
            caption=caption,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id
        )
    
    async def _send_audio_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send an audio message."""
        audio_data = message_data.get('media_data')
        caption = message_data.get('caption', '')
        
        if not audio_data:
            return None
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        return await bot.send_audio(
            chat_id=chat_id,
            audio=BytesIO(audio_data),
            caption=caption,
            reply_to_message_id=reply_to_message_id
        )
    
    async def _send_sticker_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a sticker message."""
        sticker_data = message_data.get('media_data')
        
        if not sticker_data:
            return None
        
        reply_to_message_id = message_data.get('reply_to_message_id')
        
        return await bot.send_sticker(
            chat_id=chat_id,
            sticker=BytesIO(sticker_data),
            reply_to_message_id=reply_to_message_id
        )
    
    async def _send_poll_message(self, bot: Bot, chat_id: int, message_data: Dict[str, Any]) -> Optional[TgMessage]:
        """Send a poll message."""
        question = message_data.get('poll_question', '')
        options = message_data.get('poll_options', [])
        
        if not question or not options:
            return None
        
        # Limit options to Telegram's maximum
        if len(options) > 10:
            options = options[:10]
        
        is_anonymous = message_data.get('poll_anonymous', True)
        allows_multiple_answers = message_data.get('poll_multiple', False)
        
        return await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=is_anonymous,
            allows_multiple_answers=allows_multiple_answers
        )
    
    async def edit_message(self, chat_id: int, message_id: int, message_data: Dict[str, Any], pair_id: int) -> bool:
        """Edit an existing message using the pair's bot token."""
        if not self.running:
            logger.error("Telegram destination service is not running")
            return False
        
        # Get bot instance for this pair
        bot = await self.bot_manager.get_bot_for_pair(pair_id)
        if not bot:
            logger.error(f"Failed to get bot instance for pair {pair_id}")
            return False
        
        try:
            text = message_data.get('text', '')
            if not text:
                return False
            
            # Handle long messages
            if len(text) > MessageLimit.MAX_TEXT_LENGTH:
                text = text[:MessageLimit.MAX_TEXT_LENGTH - 3] + "..."
            
            parse_mode = None
            if message_data.get('has_formatting'):
                parse_mode = ParseMode.HTML if message_data.get('format_type') == 'html' else ParseMode.MARKDOWN_V2
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode
            )
            
            logger.debug(f"Edited message {message_id} in chat {chat_id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
            return False
    
    async def delete_message(self, chat_id: int, message_id: int, pair_id: int) -> bool:
        """Delete a message using the pair's bot token."""
        if not self.running:
            logger.error("Telegram destination service is not running")
            return False
        
        # Get bot instance for this pair
        bot = await self.bot_manager.get_bot_for_pair(pair_id)
        if not bot:
            logger.error(f"Failed to get bot instance for pair {pair_id}")
            return False
        
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.debug(f"Deleted message {message_id} from chat {chat_id}")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to delete message {message_id} from chat {chat_id}: {e}")
            return False
    
    async def get_chat_info(self, chat_id: int, pair_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get information about a chat using a pair's bot token."""
        if not self.running:
            return None
        
        # If pair_id provided, use that bot; otherwise use admin bot manager
        bot = None
        if pair_id:
            bot = await self.bot_manager.get_bot_for_pair(pair_id)
        
        if not bot:
            logger.error("No bot available for chat info request")
            return None
        
        try:
            chat = await bot.get_chat(chat_id)
            return {
                'id': chat.id,
                'type': chat.type,
                'title': chat.title or f"{chat.first_name or ''} {chat.last_name or ''}".strip(),
                'username': chat.username,
                'description': chat.description
            }
            
        except TelegramError as e:
            logger.error(f"Failed to get chat info for {chat_id}: {e}")
            return None
    
    async def test_bot_access(self, chat_ids: List[int]) -> Dict[int, bool]:
        """Test if the bot has access to specific chats."""
        results = {}
        
        if not self.bot or not self.running:
            return {chat_id: False for chat_id in chat_ids}
        
        for chat_id in chat_ids:
            try:
                await self.bot.get_chat(chat_id)
                results[chat_id] = True
            except Exception as e:
                logger.error(f"Bot cannot access chat {chat_id}: {e}")
                results[chat_id] = False
        
        return results
