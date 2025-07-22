"""Advanced regex-based filtering system with flexible pattern matching."""

import re
import asyncio
from typing import List, Dict, Any, Optional, Set, Pattern, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument, User, Channel
from loguru import logger

from core.database import ForwardingPair, Database


@dataclass
class FilterRule:
    """Advanced filter rule with regex support."""
    rule_id: str
    name: str
    pattern: str
    rule_type: str  # 'block', 'allow', 'replace', 'redirect'
    target: str  # 'content', 'username', 'channel', 'media_caption'
    action: str  # 'block', 'allow', 'replace_content', 'add_warning'
    replacement: Optional[str] = None
    priority: int = 0
    is_regex: bool = True
    case_sensitive: bool = False
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    
    def __post_init__(self):
        """Compile regex pattern if needed."""
        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                self.compiled_pattern: Optional[Pattern] = re.compile(self.pattern, flags)
            except re.error as e:
                logger.error(f"Invalid regex pattern in rule {self.rule_id}: {e}")
                self.compiled_pattern = None
                self.enabled = False
        else:
            self.compiled_pattern = None


@dataclass
class FilterResult:
    """Enhanced filter result with detailed information."""
    should_forward: bool
    action_taken: str
    reason: str
    modified_content: Optional[str] = None
    applied_rules: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedFilterSystem:
    """Comprehensive filtering system with regex support and advanced capabilities."""
    
    def __init__(self, database: Database):
        self.database = database
        self.global_rules: List[FilterRule] = []
        self.pair_rules: Dict[int, List[FilterRule]] = {}
        self.compiled_patterns: Dict[str, Pattern] = {}
        
        # Built-in security patterns
        self.security_patterns = {
            'malicious_links': [
                r'(?i)\b(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)\/[a-zA-Z0-9]+',
                r'(?i)\b[a-zA-Z0-9]+\.(tk|ml|ga|cf)\b',
                r'(?i)(free.*money|easy.*cash|work.*home|make.*\$\d+)',
            ],
            'spam_content': [
                r'(?i)\b(viagra|cialis|pharmacy|pills|medication)\b',
                r'(?i)\b(lottery|winner|congratulations|prize|award)\b',
                r'(?i)\b(urgent|immediate|limited.*time|act.*now)\b',
                r'(?i)\b(click.*here|visit.*now|download.*now)\b',
            ],
            'phishing': [
                r'(?i)\b(verify.*account|update.*payment|suspended.*account)\b',
                r'(?i)\b(login.*required|confirm.*identity|security.*alert)\b',
                r'(?i)\b(bank|paypal|amazon|microsoft).*\b(verify|update|confirm)',
            ],
            'cryptocurrency_scams': [
                r'(?i)\b(bitcoin|btc|ethereum|eth|crypto).*\b(giveaway|free|double)\b',
                r'(?i)\b(send.*\d+.*get.*\d+|investment.*guaranteed)\b',
                r'(?i)\b(mining.*profit|trading.*bot|crypto.*signals)\b',
            ]
        }
        
        # Initialize built-in patterns
        self._init_security_patterns()
    
    def _init_security_patterns(self):
        """Initialize built-in security filter patterns."""
        try:
            rule_id = 0
            for category, patterns in self.security_patterns.items():
                for pattern in patterns:
                    rule = FilterRule(
                        rule_id=f"security_{category}_{rule_id}",
                        name=f"Security: {category.replace('_', ' ').title()}",
                        pattern=pattern,
                        rule_type='block',
                        target='content',
                        action='block',
                        priority=100,
                        is_regex=True,
                        case_sensitive=False
                    )
                    self.global_rules.append(rule)
                    rule_id += 1
            
            logger.info(f"Initialized {len(self.global_rules)} built-in security patterns")
            
        except Exception as e:
            logger.error(f"Error initializing security patterns: {e}")
    
    async def add_filter_rule(self, rule: FilterRule, pair_id: Optional[int] = None) -> bool:
        """Add a new filter rule."""
        try:
            # Validate regex pattern
            if rule.is_regex and rule.compiled_pattern is None:
                logger.error(f"Invalid regex pattern in rule {rule.rule_id}")
                return False
            
            # Add to appropriate collection
            if pair_id is None:
                self.global_rules.append(rule)
                logger.info(f"Added global filter rule: {rule.name}")
            else:
                if pair_id not in self.pair_rules:
                    self.pair_rules[pair_id] = []
                self.pair_rules[pair_id].append(rule)
                logger.info(f"Added pair-specific filter rule for pair {pair_id}: {rule.name}")
            
            # Store in database
            await self._store_filter_rule(rule, pair_id)
            return True
            
        except Exception as e:
            logger.error(f"Error adding filter rule: {e}")
            return False
    
    async def remove_filter_rule(self, rule_id: str, pair_id: Optional[int] = None) -> bool:
        """Remove a filter rule."""
        try:
            if pair_id is None:
                # Remove from global rules
                self.global_rules = [r for r in self.global_rules if r.rule_id != rule_id]
            else:
                # Remove from pair-specific rules
                if pair_id in self.pair_rules:
                    self.pair_rules[pair_id] = [r for r in self.pair_rules[pair_id] if r.rule_id != rule_id]
            
            # Remove from database
            await self._remove_filter_rule(rule_id, pair_id)
            logger.info(f"Removed filter rule: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing filter rule: {e}")
            return False
    
    async def filter_message(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Apply comprehensive filtering to a message."""
        try:
            result = FilterResult(
                should_forward=True,
                action_taken="none",
                reason="No filters applied"
            )
            
            # Get applicable rules (global + pair-specific)
            rules = self.global_rules.copy()
            if pair.id in self.pair_rules:
                rules.extend(self.pair_rules[pair.id])
            
            # Sort rules by priority (higher priority first)
            rules.sort(key=lambda x: x.priority, reverse=True)
            
            # Extract message content and metadata
            content = message.message or ""
            username = ""
            channel_name = ""
            media_caption = ""
            
            if message.sender:
                if isinstance(message.sender, User):
                    username = message.sender.username or f"user_{message.sender.id}"
                elif isinstance(message.sender, Channel):
                    channel_name = message.sender.title or f"channel_{message.sender.id}"
            
            if message.media and hasattr(message.media, 'caption'):
                media_caption = getattr(message.media, 'caption', '') or ""
            
            # Apply rules in priority order
            for rule in rules:
                if not rule.enabled:
                    continue
                
                # Determine target text based on rule target
                target_text = ""
                if rule.target == "content":
                    target_text = content
                elif rule.target == "username":
                    target_text = username
                elif rule.target == "channel":
                    target_text = channel_name
                elif rule.target == "media_caption":
                    target_text = media_caption
                else:
                    continue
                
                # Check if rule matches
                match_found = False
                if rule.is_regex and rule.compiled_pattern:
                    match_found = bool(rule.compiled_pattern.search(target_text))
                else:
                    # Simple string matching
                    if rule.case_sensitive:
                        match_found = rule.pattern in target_text
                    else:
                        match_found = rule.pattern.lower() in target_text.lower()
                
                if match_found:
                    # Update usage count
                    rule.usage_count += 1
                    result.applied_rules.append(rule.rule_id)
                    
                    # Apply rule action
                    if rule.action == "block":
                        result.should_forward = False
                        result.action_taken = "blocked"
                        result.reason = f"Blocked by rule: {rule.name}"
                        return result  # Stop processing on block
                    
                    elif rule.action == "replace_content" and rule.replacement:
                        if rule.is_regex and rule.compiled_pattern:
                            content = rule.compiled_pattern.sub(rule.replacement, content)
                        else:
                            content = content.replace(rule.pattern, rule.replacement)
                        result.modified_content = content
                        result.action_taken = "content_modified"
                        result.reason = f"Content modified by rule: {rule.name}"
                    
                    elif rule.action == "add_warning":
                        warning_text = rule.replacement or f"⚠️ Content flagged by filter: {rule.name}"
                        result.warnings.append(warning_text)
                        result.action_taken = "warning_added"
            
            # Apply legacy filters if no advanced rules applied
            if result.action_taken == "none":
                legacy_result = await self._apply_legacy_filters(message, pair)
                if not legacy_result.should_forward:
                    return legacy_result
            
            # Store filtering statistics
            await self._record_filter_statistics(pair.id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in advanced filtering: {e}")
            # Return safe default on error
            return FilterResult(
                should_forward=True,
                action_taken="error",
                reason=f"Filter error: {str(e)}"
            )
    
    async def _apply_legacy_filters(self, message: Message, pair: ForwardingPair) -> FilterResult:
        """Apply legacy filtering for backward compatibility."""
        try:
            # Check media filters
            if message.media and not pair.media_enabled:
                return FilterResult(
                    should_forward=False,
                    action_taken="blocked",
                    reason="Media disabled for this pair"
                )
            
            # Check keyword blacklist
            content = message.message or ""
            if pair.blocked_keywords:
                keywords = pair.blocked_keywords.split(',')
                for keyword in keywords:
                    keyword = keyword.strip().lower()
                    if keyword in content.lower():
                        return FilterResult(
                            should_forward=False,
                            action_taken="blocked",
                            reason=f"Blocked keyword: {keyword}"
                        )
            
            return FilterResult(
                should_forward=True,
                action_taken="none",
                reason="Legacy filters passed"
            )
            
        except Exception as e:
            logger.error(f"Error in legacy filtering: {e}")
            return FilterResult(
                should_forward=True,
                action_taken="error",
                reason=f"Legacy filter error: {str(e)}"
            )
    
    async def get_filter_statistics(self, pair_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """Get filtering statistics."""
        try:
            # This would query the database for filtering stats
            # For now, return basic statistics
            stats = {
                "total_messages_processed": 0,
                "messages_blocked": 0,
                "messages_modified": 0,
                "top_blocking_rules": [],
                "filter_effectiveness": 0.0,
                "time_period_days": days
            }
            
            # Calculate stats from rule usage
            if pair_id is None:
                # Global stats
                all_rules = self.global_rules
            else:
                # Pair-specific stats
                all_rules = self.pair_rules.get(pair_id, [])
            
            total_usage = sum(rule.usage_count for rule in all_rules)
            blocking_rules = [(rule.name, rule.usage_count) for rule in all_rules 
                            if rule.action == "block" and rule.usage_count > 0]
            blocking_rules.sort(key=lambda x: x[1], reverse=True)
            
            stats.update({
                "total_rule_applications": total_usage,
                "top_blocking_rules": blocking_rules[:5],
                "active_rules_count": len([r for r in all_rules if r.enabled])
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting filter statistics: {e}")
            return {}
    
    async def _store_filter_rule(self, rule: FilterRule, pair_id: Optional[int]):
        """Store filter rule in database."""
        try:
            # Implementation would store rule in database
            # For now, just log
            logger.debug(f"Storing filter rule {rule.rule_id} for pair {pair_id}")
        except Exception as e:
            logger.error(f"Error storing filter rule: {e}")
    
    async def _remove_filter_rule(self, rule_id: str, pair_id: Optional[int]):
        """Remove filter rule from database."""
        try:
            # Implementation would remove rule from database
            logger.debug(f"Removing filter rule {rule_id} for pair {pair_id}")
        except Exception as e:
            logger.error(f"Error removing filter rule: {e}")
    
    async def _record_filter_statistics(self, pair_id: int, result: FilterResult):
        """Record filtering statistics in database."""
        try:
            # Implementation would record stats in database
            logger.debug(f"Recording filter stats for pair {pair_id}: {result.action_taken}")
        except Exception as e:
            logger.error(f"Error recording filter statistics: {e}")
    
    def export_rules_config(self, pair_id: Optional[int] = None) -> str:
        """Export filter rules to JSON configuration."""
        try:
            if pair_id is None:
                rules = self.global_rules
            else:
                rules = self.pair_rules.get(pair_id, [])
            
            config = {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "pair_id": pair_id,
                "rules": []
            }
            
            for rule in rules:
                rule_dict = {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "rule_type": rule.rule_type,
                    "target": rule.target,
                    "action": rule.action,
                    "replacement": rule.replacement,
                    "priority": rule.priority,
                    "is_regex": rule.is_regex,
                    "case_sensitive": rule.case_sensitive,
                    "enabled": rule.enabled
                }
                config["rules"].append(rule_dict)
            
            return json.dumps(config, indent=2)
            
        except Exception as e:
            logger.error(f"Error exporting rules config: {e}")
            return "{}"
    
    async def import_rules_config(self, config_json: str, pair_id: Optional[int] = None) -> bool:
        """Import filter rules from JSON configuration."""
        try:
            config = json.loads(config_json)
            
            if "rules" not in config:
                logger.error("Invalid config format: missing 'rules' key")
                return False
            
            imported_count = 0
            for rule_data in config["rules"]:
                rule = FilterRule(
                    rule_id=rule_data.get("rule_id", f"imported_{imported_count}"),
                    name=rule_data.get("name", "Imported Rule"),
                    pattern=rule_data.get("pattern", ""),
                    rule_type=rule_data.get("rule_type", "block"),
                    target=rule_data.get("target", "content"),
                    action=rule_data.get("action", "block"),
                    replacement=rule_data.get("replacement"),
                    priority=rule_data.get("priority", 0),
                    is_regex=rule_data.get("is_regex", True),
                    case_sensitive=rule_data.get("case_sensitive", False),
                    enabled=rule_data.get("enabled", True)
                )
                
                if await self.add_filter_rule(rule, pair_id):
                    imported_count += 1
            
            logger.info(f"Imported {imported_count} filter rules")
            return imported_count > 0
            
        except Exception as e:
            logger.error(f"Error importing rules config: {e}")
            return False