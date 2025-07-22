"""Advanced message filtering system for content control."""

import re
import asyncio
from typing import List, Dict, Set, Optional, Any
from datetime import datetime
from loguru import logger

from core.database import Database


class MessageFilter:
    """Advanced message filtering with multiple filter types."""
    
    def __init__(self, database: Database):
        self.database = database
        self.global_blocked_words: Set[str] = set()
        self.global_blocked_phrases: Set[str] = set()
        self.blocked_file_types: Set[str] = set()
        self.filter_images: bool = False
        self.filter_videos: bool = False
        self.filter_documents: bool = False
        self.strip_headers: bool = True
        self.strip_mentions: bool = True
        self.strip_forwarded_from: bool = True
        self.max_message_length: int = 4000
        self.last_update = datetime.now()
        
        # Per-pair filters (loaded from database)
        self.pair_filters: Dict[int, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize filters from database."""
        try:
            # Load global filters
            await self._load_global_filters()
            
            # Load per-pair filters
            await self._load_pair_filters()
            
            logger.info("Message filters initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize message filters: {e}")
    
    async def _load_global_filters(self):
        """Load global filters from database."""
        try:
            # Note: This would require a filters table in the database
            # For now, use default settings
            self.global_blocked_words = {
                "spam", "scam", "phishing", "malware", "virus"
            }
            self.blocked_file_types = {
                ".exe", ".bat", ".cmd", ".scr", ".pif", ".com"
            }
            
        except Exception as e:
            logger.error(f"Failed to load global filters: {e}")
    
    async def _load_pair_filters(self):
        """Load per-pair specific filters."""
        try:
            pairs = await self.database.get_all_pairs()
            for pair in pairs:
                self.pair_filters[pair.id] = {
                    'blocked_words': set(),
                    'blocked_phrases': set(),
                    'filter_images': False,
                    'filter_videos': False,
                    'filter_documents': False,
                    'custom_rules': []
                }
                
        except Exception as e:
            logger.error(f"Failed to load pair filters: {e}")
    
    async def filter_message(self, message_data: Dict[str, Any], pair_id: Optional[int] = None) -> Dict[str, Any]:
        """Filter and process message based on rules."""
        try:
            # Make a copy to avoid modifying original
            filtered_data = message_data.copy()
            
            # Apply global content filtering
            if not await self._check_global_content_filters(filtered_data):
                return {'blocked': True, 'reason': 'Global content filter'}
            
            # Apply per-pair filtering if pair_id provided
            if pair_id and not await self._check_pair_filters(filtered_data, pair_id):
                return {'blocked': True, 'reason': 'Pair-specific filter'}
            
            # Apply content modifications
            filtered_data = await self._apply_content_modifications(filtered_data)
            
            # Apply length limits
            filtered_data = await self._apply_length_limits(filtered_data)
            
            return {
                'blocked': False,
                'filtered_data': filtered_data,
                'modifications_applied': True
            }
            
        except Exception as e:
            logger.error(f"Error filtering message: {e}")
            return {'blocked': False, 'filtered_data': message_data}
    
    async def _check_global_content_filters(self, message_data: Dict[str, Any]) -> bool:
        """Check message against global content filters."""
        try:
            # Check text content
            text = message_data.get('text', '').lower()
            caption = message_data.get('caption', '').lower()
            
            # Check blocked words
            for word in self.global_blocked_words:
                if word.lower() in text or word.lower() in caption:
                    logger.info(f"Message blocked by global word filter: {word}")
                    return False
            
            # Check file type restrictions
            filename = message_data.get('filename', '').lower()
            for blocked_ext in self.blocked_file_types:
                if filename.endswith(blocked_ext):
                    logger.info(f"Message blocked by file type filter: {blocked_ext}")
                    return False
            
            # Check media type restrictions
            message_type = message_data.get('type', '')
            if self.filter_images and message_type == 'photo':
                logger.info("Message blocked by image filter")
                return False
            
            if self.filter_videos and message_type == 'video':
                logger.info("Message blocked by video filter")
                return False
            
            if self.filter_documents and message_type == 'document':
                logger.info("Message blocked by document filter")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in global content filtering: {e}")
            return True  # Allow message on error
    
    async def _check_pair_filters(self, message_data: Dict[str, Any], pair_id: int) -> bool:
        """Check message against pair-specific filters."""
        try:
            if pair_id not in self.pair_filters:
                return True
            
            pair_filter = self.pair_filters[pair_id]
            text = message_data.get('text', '').lower()
            caption = message_data.get('caption', '').lower()
            
            # Check pair-specific blocked words
            for word in pair_filter.get('blocked_words', set()):
                if word.lower() in text or word.lower() in caption:
                    logger.info(f"Message blocked by pair {pair_id} word filter: {word}")
                    return False
            
            # Check pair-specific media filters
            message_type = message_data.get('type', '')
            if pair_filter.get('filter_images') and message_type == 'photo':
                return False
            if pair_filter.get('filter_videos') and message_type == 'video':
                return False
            if pair_filter.get('filter_documents') and message_type == 'document':
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in pair filtering: {e}")
            return True
    
    async def _apply_content_modifications(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply content modifications like header/mention stripping."""
        try:
            text = message_data.get('text', '')
            if not text:
                return message_data
            
            modified_text = text
            
            # Strip forwarded headers
            if self.strip_forwarded_from:
                # Remove "Forwarded from:" patterns
                modified_text = re.sub(r'^Forwarded from:?\s*[^\n]*\n?', '', modified_text, flags=re.MULTILINE | re.IGNORECASE)
                modified_text = re.sub(r'^From:?\s*[^\n]*\n?', '', modified_text, flags=re.MULTILINE | re.IGNORECASE)
            
            # Strip headers (lines starting with specific patterns)
            if self.strip_headers:
                # Remove common header patterns
                header_patterns = [
                    r'^#+\s+[^\n]*\n?',  # Markdown headers
                    r'^\*\*[^\n]*\*\*\n?',  # Bold headers
                    r'^===[^\n]*===\n?',  # Separator headers
                    r'^---[^\n]*---\n?'   # Dash separators
                ]
                for pattern in header_patterns:
                    modified_text = re.sub(pattern, '', modified_text, flags=re.MULTILINE)
            
            # Strip mentions
            if self.strip_mentions:
                # Remove @username mentions
                modified_text = re.sub(r'@\w+', '', modified_text)
                # Remove Telegram-style mentions
                modified_text = re.sub(r'\[.*?\]\(tg://user\?id=\d+\)', '', modified_text)
            
            # Clean up extra whitespace
            modified_text = re.sub(r'\n\s*\n\s*\n', '\n\n', modified_text)  # Multiple newlines to double
            modified_text = modified_text.strip()
            
            message_data['text'] = modified_text
            return message_data
            
        except Exception as e:
            logger.error(f"Error in content modifications: {e}")
            return message_data
    
    async def _apply_length_limits(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply message length limits."""
        try:
            text = message_data.get('text', '')
            if len(text) > self.max_message_length:
                truncated_text = text[:self.max_message_length - 3] + "..."
                message_data['text'] = truncated_text
                message_data['truncated'] = True
                logger.info(f"Message truncated from {len(text)} to {len(truncated_text)} characters")
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error applying length limits: {e}")
            return message_data
    
    # Admin management methods
    async def add_global_blocked_word(self, word: str) -> bool:
        """Add word to global blocked list."""
        try:
            self.global_blocked_words.add(word.lower())
            # TODO: Save to database
            logger.info(f"Added global blocked word: {word}")
            return True
        except Exception as e:
            logger.error(f"Failed to add blocked word: {e}")
            return False
    
    async def remove_global_blocked_word(self, word: str) -> bool:
        """Remove word from global blocked list."""
        try:
            self.global_blocked_words.discard(word.lower())
            # TODO: Remove from database
            logger.info(f"Removed global blocked word: {word}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove blocked word: {e}")
            return False
    
    async def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return {
            'global_blocked_words': len(self.global_blocked_words),
            'blocked_file_types': len(self.blocked_file_types),
            'pair_filters': len(self.pair_filters),
            'filter_images': self.filter_images,
            'filter_videos': self.filter_videos,
            'filter_documents': self.filter_documents,
            'strip_headers': self.strip_headers,
            'strip_mentions': self.strip_mentions,
            'max_message_length': self.max_message_length
        }
    
    async def update_filter_settings(self, settings: Dict[str, Any]) -> bool:
        """Update filter settings."""
        try:
            if 'filter_images' in settings:
                self.filter_images = settings['filter_images']
            if 'filter_videos' in settings:
                self.filter_videos = settings['filter_videos']
            if 'filter_documents' in settings:
                self.filter_documents = settings['filter_documents']
            if 'strip_headers' in settings:
                self.strip_headers = settings['strip_headers']
            if 'strip_mentions' in settings:
                self.strip_mentions = settings['strip_mentions']
            if 'max_message_length' in settings:
                self.max_message_length = settings['max_message_length']
            
            logger.info("Filter settings updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update filter settings: {e}")
            return False