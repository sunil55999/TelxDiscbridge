"""Message filtering utilities for the forwarding bot."""

import re
import asyncio
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument
from loguru import logger

from core.database import ForwardingPair


@dataclass
class FilterResult:
    """Result of message filtering."""
    should_forward: bool
    reason: Optional[str] = None
    modified_content: Optional[str] = None


class MessageFilter:
    """Handles message filtering and content blocking."""
    
    def __init__(self):
        self.global_blocked_words: Set[str] = set()
        self.global_blocked_patterns: List[re.Pattern] = []
        self.global_media_blocked: bool = False
        
        # Compile common spam patterns
        self._compile_spam_patterns()
    
    def _compile_spam_patterns(self):
        """Compile common spam detection patterns."""
        spam_patterns = [
            r'(?i)\b(viagra|cialis|casino|lottery|winner|congratulations|prize)\b',
            r'(?i)\b(click\s+here|visit\s+now|limited\s+time)\b',
            r'(?i)\b(free\s+money|easy\s+money|work\s+from\s+home)\b',
            r'(?i)\b(urgent|immediate|act\s+now)\b',
        ]
        
        try:
            self.spam_patterns = [re.compile(pattern) for pattern in spam_patterns]
            logger.debug("Compiled spam detection patterns")
        except Exception as e:
            logger.error(f"Failed to compile spam patterns: {e}")
            self.spam_patterns = []
    
    async def should_forward_message(self, message: Message, pair: ForwardingPair) -> bool:
        """Determine if a message should be forwarded based on filters."""
        try:
            result = await self.filter_message(message, pair)
            return result.should_forward
        except Exception as e:
            logger.error(f"Error in message filtering: {e}")
            return True  # Default to forwarding on error
    
    async def filter_message(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Apply all filters to a message and return detailed result."""
        try:
            # Check media filters first
            if message.media and not pair.media_enabled:
                return FilterResult(
                    should_forward=False,
                    reason="Media disabled for this pair"
                )
            
            # Check global media blocking
            if message.media and self.global_media_blocked:
                return FilterResult(
                    should_forward=False,
                    reason="Media globally blocked"
                )
            
            # Check specific media type filters
            media_filter_result = await self._check_media_filters(message, pair)
            if not media_filter_result.should_forward:
                return media_filter_result
            
            # Check text content filters
            text_content = message.message or ""
            if text_content:
                text_filter_result = await self._check_text_filters(text_content, pair)
                if not text_filter_result.should_forward:
                    return text_filter_result
            
            # Check spam detection
            spam_result = await self._check_spam_filters(message, pair)
            if not spam_result.should_forward:
                return spam_result
            
            # Check sender filters (if applicable)
            sender_result = await self._check_sender_filters(message, pair)
            if not sender_result.should_forward:
                return sender_result
            
            # All filters passed
            return FilterResult(should_forward=True)
            
        except Exception as e:
            logger.error(f"Error in message filtering: {e}")
            return FilterResult(should_forward=True)  # Default to forwarding on error
    
    async def _check_media_filters(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Check media-specific filters."""
        if not message.media:
            return FilterResult(should_forward=True)
        
        media = message.media
        
        # Check photo blocking
        if isinstance(media, MessageMediaPhoto):
            # Could add specific photo filtering logic here
            pass
        
        # Check document blocking
        elif isinstance(media, MessageMediaDocument):
            # Check file size limits or file types
            if hasattr(media.document, 'size') and media.document.size > 50 * 1024 * 1024:  # 50MB limit
                return FilterResult(
                    should_forward=False,
                    reason="File size exceeds limit (50MB)"
                )
        
        # Check video blocking
        elif isinstance(media, MessageMediaVideo):
            # Could add video-specific filtering
            pass
        
        # Check audio blocking
        elif isinstance(media, MessageMediaAudio):
            # Could add audio-specific filtering
            pass
        
        # Check sticker blocking
        elif isinstance(media, MessageMediaSticker):
            # Could add sticker filtering based on emoji or pack
            pass
        
        return FilterResult(should_forward=True)
    
    async def _check_text_filters(self, text: str, pair: ForwardingPair) -> FilterResult:
        """Check text content filters."""
        text_lower = text.lower()
        
        # Check pair-specific keyword filters
        if pair.keyword_filters:
            for blocked_word in pair.keyword_filters:
                if blocked_word.lower() in text_lower:
                    return FilterResult(
                        should_forward=False,
                        reason=f"Contains blocked word: {blocked_word}"
                    )
        
        # Check global blocked words
        for blocked_word in self.global_blocked_words:
            if blocked_word.lower() in text_lower:
                return FilterResult(
                    should_forward=False,
                    reason=f"Contains globally blocked word: {blocked_word}"
                )
        
        # Check pattern-based filters
        for pattern in self.global_blocked_patterns:
            if pattern.search(text):
                return FilterResult(
                    should_forward=False,
                    reason=f"Matches blocked pattern: {pattern.pattern}"
                )
        
        # Check for excessive caps (possible spam)
        if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.8:
            return FilterResult(
                should_forward=False,
                reason="Excessive capital letters (possible spam)"
            )
        
        # Check for excessive repetition
        if self._has_excessive_repetition(text):
            return FilterResult(
                should_forward=False,
                reason="Excessive character/word repetition"
            )
        
        return FilterResult(should_forward=True)
    
    async def _check_spam_filters(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Check for spam indicators."""
        text = message.message or ""
        
        # Check spam patterns
        for pattern in self.spam_patterns:
            if pattern.search(text):
                return FilterResult(
                    should_forward=False,
                    reason=f"Matches spam pattern"
                )
        
        # Check for suspicious URLs
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(text)
        
        if len(urls) > 3:  # More than 3 URLs might be spam
            return FilterResult(
                should_forward=False,
                reason="Too many URLs (possible spam)"
            )
        
        # Check for suspicious domains (this would be expanded with a real spam domain list)
        suspicious_domains = [
            'bit.ly', 'tinyurl.com', 'short.link', 'suspicious-domain.com'
        ]
        
        for url in urls:
            for domain in suspicious_domains:
                if domain in url:
                    return FilterResult(
                        should_forward=False,
                        reason=f"Contains suspicious domain: {domain}"
                    )
        
        return FilterResult(should_forward=True)
    
    async def _check_sender_filters(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Check sender-based filters."""
        # This could be expanded to filter based on sender characteristics
        # For now, just return True (no sender filtering)
        return FilterResult(should_forward=True)
    
    def _has_excessive_repetition(self, text: str) -> bool:
        """Check if text has excessive character or word repetition."""
        # Check character repetition
        char_count = {}
        for char in text.lower():
            if char.isalnum():
                char_count[char] = char_count.get(char, 0) + 1
        
        if any(count > len(text) * 0.3 for count in char_count.values()):
            return True
        
        # Check word repetition
        words = text.lower().split()
        if len(words) > 3:
            word_count = {}
            for word in words:
                word_count[word] = word_count.get(word, 0) + 1
            
            if any(count > len(words) * 0.4 for count in word_count.values()):
                return True
        
        return False
    
    def add_global_blocked_word(self, word: str):
        """Add a word to global blocked words."""
        self.global_blocked_words.add(word.lower())
        logger.info(f"Added global blocked word: {word}")
    
    def remove_global_blocked_word(self, word: str):
        """Remove a word from global blocked words."""
        self.global_blocked_words.discard(word.lower())
        logger.info(f"Removed global blocked word: {word}")
    
    def add_global_blocked_pattern(self, pattern: str):
        """Add a regex pattern to global blocked patterns."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            self.global_blocked_patterns.append(compiled_pattern)
            logger.info(f"Added global blocked pattern: {pattern}")
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
    
    def set_global_media_blocking(self, blocked: bool):
        """Set global media blocking status."""
        self.global_media_blocked = blocked
        logger.info(f"Global media blocking set to: {blocked}")
    
    def clear_global_filters(self):
        """Clear all global filters."""
        self.global_blocked_words.clear()
        self.global_blocked_patterns.clear()
        self.global_media_blocked = False
        logger.info("Cleared all global filters")
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get statistics about current filters."""
        return {
            'global_blocked_words': len(self.global_blocked_words),
            'global_blocked_patterns': len(self.global_blocked_patterns),
            'global_media_blocked': self.global_media_blocked,
            'spam_patterns': len(self.spam_patterns)
        }


class ContentModerator:
    """Advanced content moderation with configurable rules."""
    
    def __init__(self):
        self.moderation_rules: List[Dict[str, Any]] = []
        self.whitelist_users: Set[int] = set()
        self.blacklist_users: Set[int] = set()
    
    def add_moderation_rule(self, rule: Dict[str, Any]):
        """Add a custom moderation rule."""
        self.moderation_rules.append(rule)
        logger.info(f"Added moderation rule: {rule.get('name', 'unnamed')}")
    
    def add_whitelisted_user(self, user_id: int):
        """Add user to whitelist (bypasses most filters)."""
        self.whitelist_users.add(user_id)
        logger.info(f"Added user {user_id} to whitelist")
    
    def add_blacklisted_user(self, user_id: int):
        """Add user to blacklist (blocks all messages)."""
        self.blacklist_users.add(user_id)
        logger.info(f"Added user {user_id} to blacklist")
    
    async def moderate_message(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Apply moderation rules to a message."""
        # Check blacklist first
        if hasattr(message, 'from_id') and message.from_id in self.blacklist_users:
            return FilterResult(
                should_forward=False,
                reason="Sender is blacklisted"
            )
        
        # Check whitelist (bypass other rules)
        if hasattr(message, 'from_id') and message.from_id in self.whitelist_users:
            return FilterResult(should_forward=True)
        
        # Apply custom moderation rules
        for rule in self.moderation_rules:
            result = await self._apply_moderation_rule(message, rule, pair)
            if not result.should_forward:
                return result
        
        return FilterResult(should_forward=True)
    
    async def _apply_moderation_rule(self, message: Message, rule: Dict[str, Any], pair: ForwardingPair) -> FilterResult:
        """Apply a single moderation rule."""
        # This is a placeholder for custom rule logic
        # Rules could be defined as dictionaries with conditions and actions
        return FilterResult(should_forward=True)
