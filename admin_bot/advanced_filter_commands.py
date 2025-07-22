"""Advanced filter management commands for the admin bot."""

import asyncio
import json
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from loguru import logger

from utils.advanced_filters import AdvancedFilterSystem, FilterRule
from core.database import Database


class AdvancedFilterCommands:
    """Enhanced filter management commands with regex support."""
    
    def __init__(self, database: Database, filter_system: AdvancedFilterSystem):
        self.database = database
        self.filter_system = filter_system
    
    def register_handlers(self, application):
        """Register all filter command handlers."""
        handlers = [
            CommandHandler("addfilter", self.add_filter_command),
            CommandHandler("listfilters", self.list_filters_command),
            CommandHandler("removefilter", self.remove_filter_command),
            CommandHandler("testfilter", self.test_filter_command),
            CommandHandler("filterstats", self.filter_stats_command),
            CommandHandler("exportfilters", self.export_filters_command),
            CommandHandler("importfilters", self.import_filters_command),
            CommandHandler("securityfilters", self.security_filters_command),
            CallbackQueryHandler(self.handle_filter_callback, pattern="filter_")
        ]
        
        for handler in handlers:
            application.add_handler(handler)
        
        logger.info("Advanced filter commands registered")
    
    async def add_filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a new advanced filter rule."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "📝 **Add Advanced Filter**\n\n"
                    "Usage: `/addfilter <pair_id|global> <name> <pattern> <target> <action> [replacement] [priority]`\n\n"
                    "**Parameters:**\n"
                    "• `pair_id`: Specific pair ID or 'global'\n"
                    "• `name`: Descriptive name for the rule\n"
                    "• `pattern`: Regex pattern or plain text\n"
                    "• `target`: content|username|channel|media_caption\n"
                    "• `action`: block|allow|replace_content|add_warning\n"
                    "• `replacement`: Text to replace with (optional)\n"
                    "• `priority`: Rule priority 0-100 (optional, default: 50)\n\n"
                    "**Examples:**\n"
                    "`/addfilter global spam_links '(?i)bit\\.ly' content block`\n"
                    "`/addfilter 5 profanity_filter 'bad_word' content replace_content '[censored]' 60`",
                    parse_mode='Markdown'
                )
                return
            
            # Parse arguments
            args = context.args
            if len(args) < 5:
                await update.message.reply_text("❌ Insufficient arguments. Use `/addfilter` for help.")
                return
            
            pair_input = args[0]
            pair_id = None if pair_input == "global" else int(pair_input)
            name = args[1]
            pattern = args[2]
            target = args[3]
            action = args[4]
            replacement = args[5] if len(args) > 5 else None
            priority = int(args[6]) if len(args) > 6 else 50
            
            # Validate inputs
            valid_targets = ['content', 'username', 'channel', 'media_caption']
            valid_actions = ['block', 'allow', 'replace_content', 'add_warning']
            
            if target not in valid_targets:
                await update.message.reply_text(f"❌ Invalid target. Use: {', '.join(valid_targets)}")
                return
            
            if action not in valid_actions:
                await update.message.reply_text(f"❌ Invalid action. Use: {', '.join(valid_actions)}")
                return
            
            # Create filter rule
            rule_id = f"custom_{pair_id or 'global'}_{int(asyncio.get_event_loop().time())}"
            rule = FilterRule(
                rule_id=rule_id,
                name=name,
                pattern=pattern,
                rule_type='custom',
                target=target,
                action=action,
                replacement=replacement,
                priority=priority,
                is_regex=True,
                case_sensitive=False
            )
            
            # Add the rule
            success = await self.filter_system.add_filter_rule(rule, pair_id)
            
            if success:
                scope = "globally" if pair_id is None else f"for pair {pair_id}"
                await update.message.reply_text(
                    f"✅ **Filter Added Successfully**\n\n"
                    f"**Rule ID:** `{rule_id}`\n"
                    f"**Name:** {name}\n"
                    f"**Pattern:** `{pattern}`\n"
                    f"**Target:** {target}\n"
                    f"**Action:** {action}\n"
                    f"**Scope:** {scope}\n"
                    f"**Priority:** {priority}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to add filter rule. Check the pattern syntax.")
            
        except Exception as e:
            logger.error(f"Error in add_filter_command: {e}")
            await update.message.reply_text(f"❌ Error adding filter: {str(e)}")
    
    async def list_filters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all filter rules."""
        try:
            pair_id = None
            if context.args and context.args[0] != "global":
                pair_id = int(context.args[0])
            
            # Get rules
            if pair_id is None:
                rules = self.filter_system.global_rules
                scope = "Global"
            else:
                rules = self.filter_system.pair_rules.get(pair_id, [])
                scope = f"Pair {pair_id}"
            
            if not rules:
                await update.message.reply_text(f"📋 No filter rules found for {scope.lower()}.")
                return
            
            # Create paginated list
            page_size = 10
            total_pages = (len(rules) + page_size - 1) // page_size
            page = 0
            
            if context.args and len(context.args) > 1:
                try:
                    page = max(0, min(int(context.args[1]) - 1, total_pages - 1))
                except ValueError:
                    page = 0
            
            start_idx = page * page_size
            end_idx = min(start_idx + page_size, len(rules))
            page_rules = rules[start_idx:end_idx]
            
            message = f"📋 **{scope} Filter Rules** (Page {page + 1}/{total_pages})\n\n"
            
            for i, rule in enumerate(page_rules, start_idx + 1):
                status = "🟢" if rule.enabled else "🔴"
                message += f"{status} **{i}. {rule.name}**\n"
                message += f"   ID: `{rule.rule_id}`\n"
                message += f"   Pattern: `{rule.pattern[:50]}{'...' if len(rule.pattern) > 50 else ''}`\n"
                message += f"   Target: {rule.target} | Action: {rule.action}\n"
                message += f"   Priority: {rule.priority} | Used: {rule.usage_count} times\n\n"
            
            # Add navigation buttons
            keyboard = []
            nav_buttons = []
            
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"filter_list_{pair_id or 'global'}_{page - 1}"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"filter_list_{pair_id or 'global'}_{page + 1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([
                InlineKeyboardButton("🔄 Refresh", callback_data=f"filter_list_{pair_id or 'global'}_{page}"),
                InlineKeyboardButton("📊 Stats", callback_data=f"filter_stats_{pair_id or 'global'}")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in list_filters_command: {e}")
            await update.message.reply_text(f"❌ Error listing filters: {str(e)}")
    
    async def remove_filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a filter rule."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "🗑️ **Remove Filter**\n\n"
                    "Usage: `/removefilter <rule_id> [pair_id]`\n\n"
                    "**Examples:**\n"
                    "`/removefilter custom_5_1640000000` - Remove from pair 5\n"
                    "`/removefilter security_spam_content_1` - Remove global rule\n\n"
                    "Use `/listfilters` to see rule IDs.",
                    parse_mode='Markdown'
                )
                return
            
            rule_id = context.args[0]
            pair_id = int(context.args[1]) if len(context.args) > 1 else None
            
            success = await self.filter_system.remove_filter_rule(rule_id, pair_id)
            
            if success:
                scope = "globally" if pair_id is None else f"from pair {pair_id}"
                await update.message.reply_text(f"✅ Filter rule `{rule_id}` removed {scope}.")
            else:
                await update.message.reply_text(f"❌ Filter rule `{rule_id}` not found.")
            
        except Exception as e:
            logger.error(f"Error in remove_filter_command: {e}")
            await update.message.reply_text(f"❌ Error removing filter: {str(e)}")
    
    async def test_filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test filter rules against sample text."""
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "🧪 **Test Filter**\n\n"
                    "Usage: `/testfilter <pair_id|global> <test_text>`\n\n"
                    "This will show how your filters would handle the given text.\n\n"
                    "**Example:**\n"
                    "`/testfilter global 'Check out this amazing deal!'`",
                    parse_mode='Markdown'
                )
                return
            
            pair_input = context.args[0]
            test_text = " ".join(context.args[1:])
            
            # Create a mock message object for testing
            class MockMessage:
                def __init__(self, text):
                    self.message = text
                    self.media = None
                    self.sender = None
            
            # Create a mock pair
            class MockPair:
                def __init__(self, pair_id):
                    self.id = int(pair_id) if pair_id != "global" else 1
                    self.media_enabled = True
                    self.blocked_keywords = ""
            
            mock_message = MockMessage(test_text)
            mock_pair = MockPair(pair_input if pair_input != "global" else 1)
            
            # Test the filter
            result = await self.filter_system.filter_message(mock_message, mock_pair)
            
            # Format result
            status = "✅ WOULD FORWARD" if result.should_forward else "❌ WOULD BLOCK"
            message = f"🧪 **Filter Test Results**\n\n"
            message += f"**Test Text:** `{test_text}`\n"
            message += f"**Result:** {status}\n"
            message += f"**Action:** {result.action_taken}\n"
            message += f"**Reason:** {result.reason}\n"
            
            if result.modified_content:
                message += f"**Modified Content:** `{result.modified_content}`\n"
            
            if result.applied_rules:
                message += f"**Applied Rules:** {', '.join(result.applied_rules)}\n"
            
            if result.warnings:
                message += f"**Warnings:** {', '.join(result.warnings)}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in test_filter_command: {e}")
            await update.message.reply_text(f"❌ Error testing filter: {str(e)}")
    
    async def filter_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show filter statistics."""
        try:
            pair_id = None
            if context.args and context.args[0] != "global":
                pair_id = int(context.args[0])
            
            days = 7
            if len(context.args) > 1:
                try:
                    days = int(context.args[1])
                except ValueError:
                    pass
            
            stats = await self.filter_system.get_filter_statistics(pair_id, days)
            
            scope = "Global" if pair_id is None else f"Pair {pair_id}"
            message = f"📊 **Filter Statistics - {scope}** (Last {days} days)\n\n"
            
            message += f"**Messages Processed:** {stats.get('total_messages_processed', 0):,}\n"
            message += f"**Messages Blocked:** {stats.get('messages_blocked', 0):,}\n"
            message += f"**Messages Modified:** {stats.get('messages_modified', 0):,}\n"
            message += f"**Active Rules:** {stats.get('active_rules_count', 0)}\n"
            message += f"**Total Rule Applications:** {stats.get('total_rule_applications', 0):,}\n"
            
            effectiveness = stats.get('filter_effectiveness', 0)
            message += f"**Filter Effectiveness:** {effectiveness:.1%}\n\n"
            
            # Top blocking rules
            top_rules = stats.get('top_blocking_rules', [])
            if top_rules:
                message += "**Top Blocking Rules:**\n"
                for rule_name, count in top_rules[:5]:
                    message += f"• {rule_name}: {count} blocks\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in filter_stats_command: {e}")
            await update.message.reply_text(f"❌ Error getting filter stats: {str(e)}")
    
    async def export_filters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export filter rules to JSON."""
        try:
            pair_id = None
            if context.args and context.args[0] != "global":
                pair_id = int(context.args[0])
            
            config_json = self.filter_system.export_rules_config(pair_id)
            
            # Send as a file
            scope = "global" if pair_id is None else f"pair_{pair_id}"
            filename = f"filter_rules_{scope}.json"
            
            await update.message.reply_document(
                document=config_json.encode('utf-8'),
                filename=filename,
                caption=f"📤 **Filter Rules Export**\n\nScope: {scope}\nExported at: {asyncio.get_event_loop().time()}"
            )
            
        except Exception as e:
            logger.error(f"Error in export_filters_command: {e}")
            await update.message.reply_text(f"❌ Error exporting filters: {str(e)}")
    
    async def import_filters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Import filter rules from JSON."""
        try:
            if not update.message.document:
                await update.message.reply_text(
                    "📥 **Import Filter Rules**\n\n"
                    "Reply to this message with a JSON file containing filter rules.\n\n"
                    "Usage: `/importfilters [pair_id]`\n"
                    "If pair_id is not specified, rules will be imported as global rules.",
                    parse_mode='Markdown'
                )
                return
            
            pair_id = None
            if context.args and context.args[0] != "global":
                pair_id = int(context.args[0])
            
            # Download the file
            file = await context.bot.get_file(update.message.document.file_id)
            file_content = await file.download_as_bytearray()
            config_json = file_content.decode('utf-8')
            
            success = await self.filter_system.import_rules_config(config_json, pair_id)
            
            if success:
                scope = "globally" if pair_id is None else f"for pair {pair_id}"
                await update.message.reply_text(f"✅ Filter rules imported successfully {scope}.")
            else:
                await update.message.reply_text("❌ Failed to import filter rules. Check the file format.")
            
        except Exception as e:
            logger.error(f"Error in import_filters_command: {e}")
            await update.message.reply_text(f"❌ Error importing filters: {str(e)}")
    
    async def security_filters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manage built-in security filters."""
        try:
            keyboard = [
                [
                    InlineKeyboardButton("🔒 View Security Rules", callback_data="filter_security_view"),
                    InlineKeyboardButton("⚙️ Configure", callback_data="filter_security_config")
                ],
                [
                    InlineKeyboardButton("📊 Security Stats", callback_data="filter_security_stats"),
                    InlineKeyboardButton("🔄 Reload Rules", callback_data="filter_security_reload")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = "🛡️ **Security Filter Management**\n\n"
            message += "Built-in security filters protect against:\n"
            message += "• Malicious links and phishing\n"
            message += "• Spam and unwanted content\n"
            message += "• Cryptocurrency scams\n"
            message += "• Social engineering attacks\n\n"
            message += "Use the buttons below to manage security filters."
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in security_filters_command: {e}")
            await update.message.reply_text(f"❌ Error accessing security filters: {str(e)}")
    
    async def handle_filter_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle filter-related callback queries."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data.replace("filter_", "")
            
            if data.startswith("list_"):
                # Handle pagination
                parts = data.replace("list_", "").split("_")
                pair_id = None if parts[0] == "global" else int(parts[0])
                page = int(parts[1])
                
                # Regenerate list with new page
                context.args = [str(pair_id) if pair_id else "global", str(page + 1)]
                await self.list_filters_command(update, context)
            
            elif data.startswith("stats_"):
                pair_id = data.replace("stats_", "")
                context.args = [pair_id]
                await self.filter_stats_command(update, context)
            
            elif data == "security_view":
                # Show security rules
                security_rules = [r for r in self.filter_system.global_rules if r.rule_id.startswith("security_")]
                
                message = "🛡️ **Security Filter Rules**\n\n"
                for category in self.filter_system.security_patterns.keys():
                    count = len([r for r in security_rules if category in r.rule_id])
                    message += f"• **{category.replace('_', ' ').title()}:** {count} rules\n"
                
                message += f"\n**Total Security Rules:** {len(security_rules)}"
                await query.edit_message_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in handle_filter_callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")