"""Message formatting and conversion between platforms."""

import re
import html
from typing import Dict, Any, Optional, List
from io import BytesIO

from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument, MessageMediaPoll
from loguru import logger

from core.database import ForwardingPair


class MessageFormatter:
    """Handles message formatting and platform conversion."""
    
    def __init__(self):
        self.max_text_length = 4096
        self.max_caption_length = 1024
    
    async def format_message(self, message: Message, pair: ForwardingPair) -> Optional[Dict[str, Any]]:
        """Format a Telegram message for forwarding."""
        try:
            if not message:
                return None
            
            # Handle different message types
            if message.media:
                return await self._format_media_message(message, pair)
            elif message.message:
                return await self._format_text_message(message, pair)
            else:
                logger.debug("Message has no text or media content")
                return None
                
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return None
    
    async def _format_text_message(self, message: Message, pair: ForwardingPair) -> Dict[str, Any]:
        """Format a text message."""
        text = message.message or ""
        
        # Apply text formatting if enabled
        formatted_text = await self._format_text_content(text, message, pair)
        
        # Handle replies
        reply_to_message_id = None
        if message.reply_to and message.reply_to.reply_to_msg_id:
            reply_to_message_id = await self._get_mapped_message_id(
                message.reply_to.reply_to_msg_id, pair.id
            )
        
        return {
            'type': 'text',
            'text': formatted_text,
            'has_formatting': bool(message.entities),
            'format_type': 'html',  # Default to HTML formatting
            'reply_to_message_id': reply_to_message_id,
            'disable_web_preview': False,
            'author_name': await self._get_sender_name(message),
            'create_embed': False  # Whether to create Discord embed
        }
    
    async def _format_media_message(self, message: Message, pair: ForwardingPair) -> Optional[Dict[str, Any]]:
        """Format a media message."""
        media = message.media
        
        if not pair.media_enabled:
            # If media is disabled, convert to text description
            return await self._convert_media_to_text(message, pair)
        
        media_type = self._get_media_type(media)
        if not media_type:
            logger.warning("Unsupported media type")
            return None
        
        # Download media data (in a real implementation, you'd download from Telegram)
        media_data = await self._download_media(media, message)
        if not media_data:
            logger.warning("Failed to download media")
            return await self._convert_media_to_text(message, pair)
        
        # Format caption
        caption = message.message or ""
        formatted_caption = await self._format_text_content(caption, message, pair) if caption else ""
        
        # Handle replies
        reply_to_message_id = None
        if message.reply_to and message.reply_to.reply_to_msg_id:
            reply_to_message_id = await self._get_mapped_message_id(
                message.reply_to.reply_to_msg_id, pair.id
            )
        
        result = {
            'type': media_type,
            'media_data': media_data,
            'caption': formatted_caption,
            'has_formatting': bool(message.entities),
            'format_type': 'html',
            'reply_to_message_id': reply_to_message_id,
            'author_name': await self._get_sender_name(message)
        }
        
        # Add specific media attributes
        if media_type == 'document':
            result['filename'] = await self._get_document_filename(media)
        elif media_type == 'sticker':
            result['sticker_emoji'] = getattr(media.sticker, 'emoji', '🎭') if hasattr(media, 'sticker') else '🎭'
        elif media_type == 'poll':
            poll_data = await self._format_poll_data(media)
            result.update(poll_data)
        
        return result
    
    async def _format_text_content(self, text: str, message: Message, pair: ForwardingPair) -> str:
        """Format text content with entities."""
        if not text or not message.entities:
            return text
        
        try:
            # Convert Telegram entities to HTML
            formatted_text = text
            
            # Sort entities by offset in reverse order to maintain positions
            entities = sorted(message.entities, key=lambda e: e.offset, reverse=True)
            
            for entity in entities:
                start = entity.offset
                end = entity.offset + entity.length
                entity_text = text[start:end]
                
                # Apply formatting based on entity type
                if hasattr(entity, 'url'):  # Text link
                    formatted_text = (formatted_text[:start] + 
                                    f'<a href="{entity.url}">{entity_text}</a>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityBold':
                    formatted_text = (formatted_text[:start] + 
                                    f'<b>{entity_text}</b>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityItalic':
                    formatted_text = (formatted_text[:start] + 
                                    f'<i>{entity_text}</i>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityCode':
                    formatted_text = (formatted_text[:start] + 
                                    f'<code>{entity_text}</code>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityPre':
                    formatted_text = (formatted_text[:start] + 
                                    f'<pre>{entity_text}</pre>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityStrike':
                    formatted_text = (formatted_text[:start] + 
                                    f'<s>{entity_text}</s>' + 
                                    formatted_text[end:])
                elif entity.__class__.__name__ == 'MessageEntityUnderline':
                    formatted_text = (formatted_text[:start] + 
                                    f'<u>{entity_text}</u>' + 
                                    formatted_text[end:])
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting text entities: {e}")
            return text  # Return original text if formatting fails
    
    def _get_media_type(self, media) -> Optional[str]:
        """Determine media type from Telegram media object."""
        if isinstance(media, MessageMediaPhoto):
            return 'photo'
        elif isinstance(media, MessageMediaDocument):
            # Check if it's a video, audio, or document
            if hasattr(media.document, 'attributes'):
                for attr in media.document.attributes:
                    if attr.__class__.__name__ == 'DocumentAttributeVideo':
                        return 'video'
                    elif attr.__class__.__name__ == 'DocumentAttributeAudio':
                        return 'audio'
            return 'document'
        elif isinstance(media, MessageMediaVideo):
            return 'video'
        elif isinstance(media, MessageMediaAudio):
            return 'audio'
        elif isinstance(media, MessageMediaSticker):
            return 'sticker'
        elif isinstance(media, MessageMediaPoll):
            return 'poll'
        else:
            return None
    
    async def _download_media(self, media, message: Message) -> Optional[bytes]:
        """Download media content from Telegram."""
        # This is a placeholder - in a real implementation, you would
        # download the media using Telethon's download_media method
        try:
            # Placeholder: return empty bytes for now
            # In real implementation:
            # media_bytes = await message.download_media(bytes)
            # return media_bytes
            return b""  # Placeholder
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            return None
    
    async def _get_document_filename(self, media) -> str:
        """Extract filename from document media."""
        if hasattr(media, 'document') and hasattr(media.document, 'attributes'):
            for attr in media.document.attributes:
                if hasattr(attr, 'file_name') and attr.file_name:
                    return attr.file_name
        return 'document'
    
    async def _format_poll_data(self, media) -> Dict[str, Any]:
        """Format poll data from Telegram poll media."""
        poll_data = {}
        
        if hasattr(media, 'poll'):
            poll = media.poll
            poll_data['poll_question'] = poll.question
            poll_data['poll_options'] = [answer.text for answer in poll.answers]
            poll_data['poll_anonymous'] = not poll.public_voters
            poll_data['poll_multiple'] = poll.multiple_choice
        
        return poll_data
    
    async def _convert_media_to_text(self, message: Message, pair: ForwardingPair) -> Dict[str, Any]:
        """Convert media message to text description when media is disabled."""
        media_type = self._get_media_type(message.media)
        
        # Create text description
        description_parts = []
        
        if media_type == 'photo':
            description_parts.append("📷 Photo")
        elif media_type == 'video':
            description_parts.append("🎥 Video")
        elif media_type == 'audio':
            description_parts.append("🎵 Audio")
        elif media_type == 'document':
            filename = await self._get_document_filename(message.media)
            description_parts.append(f"📄 Document: {filename}")
        elif media_type == 'sticker':
            emoji = getattr(message.media.sticker, 'emoji', '🎭') if hasattr(message.media, 'sticker') else '🎭'
            description_parts.append(f"Sticker: {emoji}")
        elif media_type == 'poll':
            poll_data = await self._format_poll_data(message.media)
            question = poll_data.get('poll_question', 'Poll')
            description_parts.append(f"📊 Poll: {question}")
        else:
            description_parts.append("📎 Media")
        
        # Add caption if present
        if message.message:
            formatted_caption = await self._format_text_content(message.message, message, pair)
            description_parts.append(formatted_caption)
        
        text = "\n".join(description_parts)
        
        # Handle replies
        reply_to_message_id = None
        if message.reply_to and message.reply_to.reply_to_msg_id:
            reply_to_message_id = await self._get_mapped_message_id(
                message.reply_to.reply_to_msg_id, pair.id
            )
        
        return {
            'type': 'text',
            'text': text,
            'has_formatting': bool(message.entities),
            'format_type': 'html',
            'reply_to_message_id': reply_to_message_id,
            'disable_web_preview': True,
            'author_name': await self._get_sender_name(message),
            'create_embed': False
        }
    
    async def _get_sender_name(self, message: Message) -> str:
        """Get sender name from message."""
        try:
            # This would require access to the sender entity
            # Placeholder implementation
            if hasattr(message, 'from_id') and message.from_id:
                return f"User {message.from_id}"
            return "Unknown"
        except Exception as e:
            logger.error(f"Failed to get sender name: {e}")
            return "Unknown"
    
    async def _get_mapped_message_id(self, original_id: int, pair_id: int) -> Optional[int]:
        """Get mapped message ID for replies."""
        # This would require database access to find the mapped message ID
        # For now, return None (no reply mapping)
        return None
    
    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def escape_html(self, text: str) -> str:
        """Escape HTML entities in text."""
        return html.escape(text)
    
    def strip_formatting(self, text: str) -> str:
        """Strip HTML/Markdown formatting from text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove Markdown formatting
        text = re.sub(r'[*_`~]', '', text)
        return text
    
    def convert_html_to_markdown(self, html_text: str) -> str:
        """Convert HTML formatting to Markdown."""
        # Basic HTML to Markdown conversion
        conversions = {
            r'<b>(.*?)</b>': r'**\1**',
            r'<strong>(.*?)</strong>': r'**\1**',
            r'<i>(.*?)</i>': r'*\1*',
            r'<em>(.*?)</em>': r'*\1*',
            r'<code>(.*?)</code>': r'`\1`',
            r'<pre>(.*?)</pre>': r'```\1```',
            r'<s>(.*?)</s>': r'~~\1~~',
            r'<u>(.*?)</u>': r'__\1__',
            r'<a href="([^"]*)"[^>]*>(.*?)</a>': r'[\2](\1)'
        }
        
        result = html_text
        for pattern, replacement in conversions.items():
            result = re.sub(pattern, replacement, result, flags=re.DOTALL)
        
        return result
