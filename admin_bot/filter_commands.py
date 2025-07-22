"""Admin commands for message filtering management."""

from typing import List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from core.message_filter import MessageFilter
from core.database import Database


class FilterCommands:
    """Admin commands for managing message filters."""
    
    def __init__(self, database: Database, message_filter: MessageFilter):
        self.database = database
        self.message_filter = message_filter
    
    async def blockword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add word to global blocked list."""
        if not update.message:
            return
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: `/blockword <word>`\n\n"
                    "Add a word to the global blocked words list."
                )
                return
            
            word = ' '.join(context.args)
            success = await self.message_filter.add_global_blocked_word(word)
            
            if success:
                await update.message.reply_text(
                    f"✅ Added '{word}' to global blocked words list.\n"
                    f"Messages containing this word will be filtered."
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to add '{word}' to blocked words list."
                )
                
        except Exception as e:
            logger.error(f"Error in blockword command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def unblockword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove word from global blocked list."""
        if not update.message:
            return
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: `/unblockword <word>`\n\n"
                    "Remove a word from the global blocked words list."
                )
                return
            
            word = ' '.join(context.args)
            success = await self.message_filter.remove_global_blocked_word(word)
            
            if success:
                await update.message.reply_text(
                    f"✅ Removed '{word}' from global blocked words list."
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to remove '{word}' from blocked words list."
                )
                
        except Exception as e:
            logger.error(f"Error in unblockword command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def showfilters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current filter settings and statistics."""
        if not update.message:
            return
        try:
            stats = await self.message_filter.get_filter_stats()
            
            message = "🛡️ **Message Filter Status**\n\n"
            
            # Global settings
            message += "**Global Settings:**\n"
            message += f"• Blocked words: {stats['global_blocked_words']}\n"
            message += f"• Blocked file types: {stats['blocked_file_types']}\n"
            message += f"• Filter images: {'✅' if stats['filter_images'] else '❌'}\n"
            message += f"• Filter videos: {'✅' if stats['filter_videos'] else '❌'}\n"
            message += f"• Filter documents: {'✅' if stats['filter_documents'] else '❌'}\n"
            message += f"• Strip headers: {'✅' if stats['strip_headers'] else '❌'}\n"
            message += f"• Strip mentions: {'✅' if stats['strip_mentions'] else '❌'}\n"
            message += f"• Max message length: {stats['max_message_length']}\n\n"
            
            # Per-pair filters
            message += f"**Per-Pair Filters:** {stats['pair_filters']} configured\n\n"
            
            # Blocked words list (if not too many)
            if stats['global_blocked_words'] <= 20:
                blocked_words = list(self.message_filter.global_blocked_words)
                if blocked_words:
                    message += "**Current Blocked Words:**\n"
                    for word in sorted(blocked_words):
                        message += f"• `{word}`\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in showfilters command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def filterconfig_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Configure filter settings."""
        if not update.message:
            return
        try:
            if not context.args:
                await update.message.reply_text(
                    "**Filter Configuration**\n\n"
                    "Usage: `/filterconfig <setting> <value>`\n\n"
                    "**Available settings:**\n"
                    "• `images on/off` - Filter image messages\n"
                    "• `videos on/off` - Filter video messages\n"
                    "• `documents on/off` - Filter document messages\n"
                    "• `headers on/off` - Strip message headers\n"
                    "• `mentions on/off` - Strip @mentions\n"
                    "• `maxlength <number>` - Set max message length\n\n"
                    "**Examples:**\n"
                    "`/filterconfig images on`\n"
                    "`/filterconfig maxlength 2000`",
                    parse_mode='Markdown'
                )
                return
            
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please provide both setting and value.")
                return
            
            setting = context.args[0].lower()
            value = context.args[1].lower()
            
            settings_update = {}
            
            if setting == "images":
                settings_update['filter_images'] = value == 'on'
                await update.message.reply_text(
                    f"✅ Image filtering {'enabled' if value == 'on' else 'disabled'}"
                )
            elif setting == "videos":
                settings_update['filter_videos'] = value == 'on'
                await update.message.reply_text(
                    f"✅ Video filtering {'enabled' if value == 'on' else 'disabled'}"
                )
            elif setting == "documents":
                settings_update['filter_documents'] = value == 'on'
                await update.message.reply_text(
                    f"✅ Document filtering {'enabled' if value == 'on' else 'disabled'}"
                )
            elif setting == "headers":
                settings_update['strip_headers'] = value == 'on'
                await update.message.reply_text(
                    f"✅ Header stripping {'enabled' if value == 'on' else 'disabled'}"
                )
            elif setting == "mentions":
                settings_update['strip_mentions'] = value == 'on'
                await update.message.reply_text(
                    f"✅ Mention stripping {'enabled' if value == 'on' else 'disabled'}"
                )
            elif setting == "maxlength":
                try:
                    max_length = int(context.args[1])
                    if max_length < 100 or max_length > 4096:
                        await update.message.reply_text(
                            "❌ Max length must be between 100 and 4096 characters."
                        )
                        return
                    settings_update['max_message_length'] = max_length
                    await update.message.reply_text(
                        f"✅ Max message length set to {max_length} characters"
                    )
                except ValueError:
                    await update.message.reply_text("❌ Please provide a valid number for max length.")
                    return
            else:
                await update.message.reply_text(
                    f"❌ Unknown setting: {setting}\n"
                    "Use `/filterconfig` without arguments to see available settings."
                )
                return
            
            # Apply settings
            if settings_update:
                success = await self.message_filter.update_filter_settings(settings_update)
                if not success:
                    await update.message.reply_text("⚠️ Settings updated but failed to save to database.")
                
        except Exception as e:
            logger.error(f"Error in filterconfig command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def testfilter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test message filtering with sample text."""
        if not update.message:
            return
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: `/testfilter <message text>`\n\n"
                    "Test how the message filter would process a message."
                )
                return
            
            test_message = ' '.join(context.args)
            test_data = {
                'text': test_message,
                'type': 'text',
                'caption': '',
                'filename': ''
            }
            
            # Run through filter
            result = await self.message_filter.filter_message(test_data)
            
            if result.get('blocked'):
                await update.message.reply_text(
                    f"❌ **Message would be BLOCKED**\n\n"
                    f"**Reason:** {result['reason']}\n\n"
                    f"**Original:** `{test_message}`",
                    parse_mode='Markdown'
                )
            else:
                filtered_text = result['filtered_data']['text']
                modifications = result.get('modifications_applied', False)
                
                message = f"✅ **Message would be ALLOWED**\n\n"
                message += f"**Original:** `{test_message}`\n\n"
                
                if modifications and filtered_text != test_message:
                    message += f"**Filtered:** `{filtered_text}`\n\n"
                    message += "**Modifications applied:**\n"
                    if result['filtered_data'].get('truncated'):
                        message += "• Text truncated due to length limit\n"
                    if test_message != filtered_text:
                        message += "• Headers/mentions stripped\n"
                else:
                    message += "**No modifications needed**"
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in testfilter command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    # Quick filter commands for common operations
    async def block_images_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick command to block image messages."""
        if not update.message:
            return
        try:
            success = await self.message_filter.update_global_settings({'filter_images': True})
            if success:
                await update.message.reply_text("✅ Image messages are now blocked globally.")
            else:
                await update.message.reply_text("❌ Failed to update image filtering setting.")
        except Exception as e:
            logger.error(f"Error in block_images command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def allow_images_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick command to allow image messages."""
        if not update.message:
            return
        try:
            success = await self.message_filter.update_global_settings({'filter_images': False})
            if success:
                await update.message.reply_text("✅ Image messages are now allowed globally.")
            else:
                await update.message.reply_text("❌ Failed to update image filtering setting.")
        except Exception as e:
            logger.error(f"Error in allow_images command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def strip_headers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick command to enable header/footer stripping."""
        if not update.message:
            return
        try:
            success = await self.message_filter.update_global_settings({'strip_headers': True})
            if success:
                await update.message.reply_text("✅ Message headers and footers will now be stripped.")
            else:
                await update.message.reply_text("❌ Failed to update header stripping setting.")
        except Exception as e:
            logger.error(f"Error in strip_headers command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def keep_headers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Quick command to disable header/footer stripping."""
        if not update.message:
            return
        try:
            success = await self.message_filter.update_global_settings({'strip_headers': False})
            if success:
                await update.message.reply_text("✅ Message headers and footers will now be kept.")
            else:
                await update.message.reply_text("❌ Failed to update header stripping setting.")
        except Exception as e:
            logger.error(f"Error in keep_headers command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")