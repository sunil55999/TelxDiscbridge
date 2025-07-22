"""
Unified admin command system - consolidates all admin functionality
Eliminates duplicates and provides consistent interface
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.message_filter import MessageFilter
from utils.encryption import EncryptionManager
from admin_bot.bot_management import BotTokenManager
from core.advanced_session_manager import AdvancedSessionManager


class UnifiedAdminCommands:
    """Unified admin command system with clean architecture."""
    
    def __init__(self, database: Database, encryption_manager: EncryptionManager, 
                 message_filter: MessageFilter, advanced_session_manager: AdvancedSessionManager):
        self.database = database
        self.encryption_manager = encryption_manager
        self.message_filter = message_filter
        self.advanced_session_manager = advanced_session_manager
        self.bot_manager = BotTokenManager(database, encryption_manager)
    
    # =============================================================================
    # CORE COMMANDS
    # =============================================================================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update.effective_user or not update.message:
            return
        
        user_id = update.effective_user.id
        
        welcome_message = (
            "🤖 **Telegram ↔ Discord ↔ Telegram Forwarding Bot**\n\n"
            "**Quick Start:**\n"
            "• `/addsession` - Add Telegram user session\n"
            "• `/addbot` - Add bot token for destinations\n"
            "• `/addpair` - Create forwarding pair\n"
            "• `/status` - System status\n"
            "• `/help` - Complete guide\n\n"
            
            "**Bot Management:**\n"
            "• `/listbots` - Show saved bot tokens\n"
            "• `/addbot <name> <token>` - Add named bot\n"
            "• `/removebot <name>` - Remove bot\n\n"
            
            "**Filtering:**\n"
            "• `/blockword <word>` - Block word globally\n"
            "• `/blockimage <hash>` - Block image by hash\n"
            "• `/showfilters` - View filter settings\n\n"
            
            f"Admin ID: `{user_id}`"
        )
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show comprehensive help."""
        help_text = (
            "📖 **Complete Command Reference**\n\n"
            
            "**🔧 PAIR MANAGEMENT**\n"
            "• `/addpair` - Create new forwarding pair\n"
            "• `/listpairs` - Show all pairs\n"
            "• `/removepair <id>` - Remove pair\n"
            "• `/status` - System status\n\n"
            
            "**👥 SESSION MANAGEMENT**\n"
            "• `/addsession <name> <phone>` - Add session\n"
            "• `/sessions` - List all sessions\n"
            "• `/changesession <pair_id> <session>` - Change pair session\n\n"
            
            "**🤖 BOT TOKEN MANAGEMENT**\n"
            "• `/addbot <name> <token>` - Add named bot token\n"
            "• `/listbots` - Show all saved bots\n"
            "• `/removebot <name>` - Remove bot token\n\n"
            
            "**🛡️ FILTERING SYSTEM**\n"
            "• `/blockword <word>` - Block word globally\n"
            "• `/unblockword <word>` - Unblock word\n"
            "• `/blockimage <hash>` - Block image by hash\n"
            "• `/showfilters` - View all filters\n"
            "• `/blockimages` / `/allowimages` - Toggle image filtering\n\n"
            
            "**📊 MONITORING**\n"
            "• `/health` - System health check\n"
            "• `/logs` - Recent error logs\n\n"
            
            "**💡 Quick Setup:**\n"
            "1. `/addsession mysession +1234567890`\n"
            "2. `/addbot mybot 123456:ABC...`\n"
            "3. `/addpair` (follow wizard)\n"
            "4. `/status` to verify"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    # =============================================================================
    # BOT TOKEN MANAGEMENT
    # =============================================================================
    
    async def addbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a named bot token."""
        if not update.message:
            return
            
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "**Add Bot Token**\n\n"
                    "Usage: `/addbot <name> <token>`\n\n"
                    "**Example:**\n"
                    "`/addbot MyBot 5555555555:AAA...`\n\n"
                    "The bot will be validated and saved for use in forwarding pairs.",
                    parse_mode='Markdown'
                )
                return
            
            bot_name = context.args[0]
            bot_token = context.args[1]
            
            # Add bot token with validation
            result = await self.bot_manager.add_named_bot_token(bot_name, bot_token)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ **Bot Added Successfully**\n\n"
                    f"**Name:** {bot_name}\n"
                    f"**Bot:** @{result['bot_info'].get('username', 'Unknown')}\n"
                    f"**Title:** {result['bot_info'].get('first_name', 'Unknown')}\n\n"
                    "You can now use this bot when creating forwarding pairs with `/addpair`.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ **Failed to add bot**\n\n"
                    f"Error: {result['error']}\n\n"
                    "Please check the token and try again."
                )
                
        except Exception as e:
            logger.error(f"Error in addbot command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def listbots_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all saved bot tokens."""
        if not update.message:
            return
            
        try:
            bots = await self.bot_manager.get_available_bots()
            
            if not bots:
                await update.message.reply_text(
                    "📭 **No Bot Tokens**\n\n"
                    "Use `/addbot <name> <token>` to add bot tokens.\n\n"
                    "**Example:**\n"
                    "`/addbot MyBot 123456:ABC...`"
                )
                return
            
            message = "🤖 **Saved Bot Tokens**\n\n"
            
            for i, bot in enumerate(bots, 1):
                message += f"**{i}. {bot['name']}**\n"
                message += f"🤖 @{bot['username']} ({bot['first_name']})\n"
                message += f"📅 Added: {bot['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            
            message += "**Commands:**\n"
            message += "• `/addbot <name> <token>` - Add new bot\n"
            message += "• `/removebot <name>` - Remove bot\n"
            message += "• `/addpair` - Use bots in forwarding pairs"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in listbots command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def removebot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a named bot token."""
        if not update.message:
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "**Remove Bot Token**\n\n"
                    "Usage: `/removebot <name>`\n\n"
                    "Use `/listbots` to see available bot names."
                )
                return
            
            bot_name = context.args[0]
            success = await self.bot_manager.remove_bot_token(bot_name)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Bot Removed**\n\n"
                    f"Bot token '{bot_name}' has been removed from the system."
                )
            else:
                await update.message.reply_text(
                    f"❌ **Bot Not Found**\n\n"
                    f"No bot token named '{bot_name}' exists.\n"
                    f"Use `/listbots` to see available bots."
                )
                
        except Exception as e:
            logger.error(f"Error in removebot command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    # =============================================================================
    # FILTERING SYSTEM
    # =============================================================================
    
    async def blockword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Block word globally."""
        if not update.message:
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "**Block Word Globally**\n\n"
                    "Usage: `/blockword <word or phrase>`\n\n"
                    "**Examples:**\n"
                    "• `/blockword spam`\n"
                    "• `/blockword unwanted phrase`\n\n"
                    "Blocked words will be filtered from all forwarded messages."
                )
                return
            
            word = ' '.join(context.args)
            success = await self.message_filter.add_global_blocked_word(word)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Word Blocked**\n\n"
                    f"Added '{word}' to global blocked words.\n"
                    f"Messages containing this word will be filtered."
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to block word '{word}'"
                )
                
        except Exception as e:
            logger.error(f"Error in blockword command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def unblockword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unblock word globally."""
        if not update.message:
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "**Unblock Word**\n\n"
                    "Usage: `/unblockword <word>`\n\n"
                    "Remove a word from the global blocked list."
                )
                return
            
            word = ' '.join(context.args)
            success = await self.message_filter.remove_global_blocked_word(word)
            
            if success:
                await update.message.reply_text(f"✅ Removed '{word}' from blocked words")
            else:
                await update.message.reply_text(f"❌ Failed to remove '{word}'")
                
        except Exception as e:
            logger.error(f"Error in unblockword command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def blockimage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Block image by perceptual hash."""
        if not update.message:
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "📸 **Block Image by Hash**\n\n"
                    "Usage: `/blockimage <hash>`\n\n"
                    "**To get image hash:**\n"
                    "Send any image to the bot and it will show the hash.\n\n"
                    "**Example:**\n"
                    "`/blockimage a1b2c3d4e5f6`"
                )
                return
            
            image_hash = context.args[0]
            
            # Import image hash manager
            from utils.image_hash import image_hash_manager
            success = await image_hash_manager.block_image_hash(image_hash)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Image Blocked**\n\n"
                    f"Hash: `{image_hash}`\n\n"
                    "Similar images will now be filtered from all forwarded messages.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to block image hash")
                
        except Exception as e:
            logger.error(f"Error in blockimage command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def showfilters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current filter settings."""
        if not update.message:
            return
            
        try:
            stats = await self.message_filter.get_filter_stats()
            
            message = "🛡️ **Filter Settings**\n\n"
            
            # Global blocked words
            message += f"**Blocked Words:** {stats['global_blocked_words']} words\n"
            
            # Image filtering
            from utils.image_hash import image_hash_manager
            image_stats = await image_hash_manager.get_blocked_hashes_stats()
            message += f"**Blocked Images:** {image_stats['total_blocked_hashes']} hashes\n\n"
            
            # Global settings
            message += "**Global Settings:**\n"
            global_settings = stats.get('global_settings', {})
            message += f"• Images: {'Blocked' if global_settings.get('filter_images', False) else 'Allowed'}\n"
            message += f"• Headers: {'Stripped' if global_settings.get('strip_headers', False) else 'Kept'}\n"
            message += f"• Mentions: {'Stripped' if global_settings.get('strip_mentions', False) else 'Kept'}\n\n"
            
            message += "**Commands:**\n"
            message += "• `/blockword <word>` - Block word\n"
            message += "• `/blockimage <hash>` - Block image\n"
            message += "• `/blockimages` / `/allowimages` - Toggle images"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in showfilters command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def blockimages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Block all image messages globally."""
        if not update.message:
            return
            
        try:
            success = await self.message_filter.update_global_settings({'filter_images': True})
            if success:
                await update.message.reply_text("✅ **All images are now blocked globally**")
            else:
                await update.message.reply_text("❌ Failed to update image filtering")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def allowimages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allow all image messages globally."""
        if not update.message:
            return
            
        try:
            success = await self.message_filter.update_global_settings({'filter_images': False})
            if success:
                await update.message.reply_text("✅ **All images are now allowed globally**")
            else:
                await update.message.reply_text("❌ Failed to update image filtering")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    # =============================================================================
    # SESSION MANAGEMENT
    # =============================================================================
    
    async def sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all sessions with health status."""
        if not update.message:
            return
            
        try:
            sessions = await self.database.get_all_sessions()
            
            if not sessions:
                await update.message.reply_text(
                    "📭 **No Sessions Available**\n\n"
                    "Use `/addsession <name> <phone>` to add a Telegram user session.\n\n"
                    "**Example:**\n"
                    "`/addsession mysession +1234567890`"
                )
                return
            
            message = "👥 **Telegram Sessions**\n\n"
            
            for session in sessions:
                status_emoji = {
                    'healthy': '✅',
                    'not_found': '❌',
                    'error': '⚠️',
                    'deleted': '🗑️'
                }.get(session.health_status, '❓')
                
                message += f"**{session.session_name}**\n"
                message += f"{status_emoji} Status: {session.health_status}\n"
                message += f"📱 Phone: {session.phone_number or 'Unknown'}\n"
                message += f"👤 User: {session.user_id or 'Not set'}\n"
                
                if session.last_verified:
                    try:
                        if isinstance(session.last_verified, str):
                            # Parse string datetime
                            from datetime import datetime
                            last_verified = datetime.fromisoformat(session.last_verified.replace('Z', '+00:00'))
                        else:
                            last_verified = session.last_verified
                        message += f"🕒 Last verified: {last_verified.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        message += f"🕒 Last verified: {session.last_verified}\n"
                
                message += "\n"
            
            message += "**Commands:**\n"
            message += "• `/addsession <name> <phone>` - Add new session\n"
            message += "• `/changesession <pair_id> <session>` - Change pair session"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in sessions command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    # =============================================================================
    # PAIR MANAGEMENT
    # =============================================================================
    
    async def addpair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interactive pair creation command."""
        if not update.message:
            return
            
        try:
            # Start interactive pair creation wizard
            user_data = context.user_data
            user_data.clear()
            user_data['creating_pair'] = True
            user_data['step'] = 'name'
            
            welcome_message = (
                "🚀 **Create New Forwarding Pair**\n\n"
                "I'll guide you through creating a forwarding pair step by step.\n\n"
                "**Step 1/6:** Enter a unique name for this forwarding pair:"
            )
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in addpair command: {e}")
            await update.message.reply_text(f"❌ Error starting pair creation: {e}")
    
    async def removepair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a forwarding pair."""
        if not update.message:
            return
            
        try:
            if not context.args:
                await update.message.reply_text(
                    "**Remove Forwarding Pair**\n\n"
                    "Usage: `/removepair <pair_id>`\n\n"
                    "Use `/listpairs` to see available pair IDs.\n\n"
                    "**Example:**\n"
                    "`/removepair 5`"
                )
                return
            
            pair_id = int(context.args[0])
            
            # Get pair details first
            pair = await self.database.get_pair_by_id(pair_id)
            if not pair:
                await update.message.reply_text(
                    f"❌ **Pair Not Found**\n\n"
                    f"No forwarding pair with ID {pair_id} exists.\n"
                    f"Use `/listpairs` to see available pairs."
                )
                return
            
            # Remove the pair
            success = await self.database.remove_pair(pair_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Pair Removed**\n\n"
                    f"Forwarding pair '{pair.name}' (ID: {pair_id}) has been deleted.\n"
                    f"All associated data has been cleaned up."
                )
            else:
                await update.message.reply_text(
                    f"❌ **Failed to Remove Pair**\n\n"
                    f"Could not delete pair {pair_id}. Please try again."
                )
                
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID. Please provide a number.")
        except Exception as e:
            logger.error(f"Error in removepair command: {e}")
            await update.message.reply_text(f"❌ Error removing pair: {e}")

    async def listpairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all forwarding pairs."""
        if not update.message:
            return
            
        try:
            pairs = await self.database.get_all_pairs()
            
            if not pairs:
                await update.message.reply_text(
                    "📭 **No Forwarding Pairs**\n\n"
                    "Use `/addpair` to create your first forwarding pair.\n\n"
                    "You'll need:\n"
                    "• A Telegram session (`/addsession`)\n"
                    "• A bot token (`/addbot`)\n"
                    "• Source and destination chat IDs"
                )
                return
            
            message = "🔗 **Forwarding Pairs**\n\n"
            
            for pair in pairs:
                status = "🟢 Active" if pair.is_active else "🔴 Disabled"
                message += f"**{pair.id}. {pair.name}**\n"
                message += f"{status}\n"
                message += f"📤 Source: `{pair.telegram_source_chat_id}`\n"
                message += f"📥 Destination: `{pair.telegram_dest_chat_id}`\n"
                message += f"👤 Session: {pair.session_name or 'None'}\n"
                
                if pair.discord_webhook_url:
                    message += f"🌐 Discord: {pair.discord_webhook_url[:30]}...\n"
                
                message += "\n"
            
            message += "**Commands:**\n"
            message += "• `/addpair` - Create new pair\n"
            message += "• `/removepair <id>` - Remove pair\n"
            message += "• `/status` - System overview"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in listpairs command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status."""
        if not update.message:
            return
            
        try:
            # Get basic stats
            pairs = await self.database.get_all_pairs() or []
            sessions = await self.database.get_all_sessions() or []
            
            active_pairs = len([p for p in pairs if p.is_active])
            healthy_sessions = len([s for s in sessions if s.health_status == 'healthy'])
            
            # Get filter stats
            filter_stats = await self.message_filter.get_filter_stats()
            
            message = "📊 **System Status**\n\n"
            
            message += "**Overview:**\n"
            message += f"• Forwarding Pairs: {active_pairs}/{len(pairs)} active\n"
            message += f"• Telegram Sessions: {healthy_sessions}/{len(sessions)} healthy\n"
            message += f"• Blocked Words: {filter_stats['global_blocked_words']}\n\n"
            
            # Bot tokens
            bots = await self.bot_manager.get_available_bots()
            message += f"• Saved Bot Tokens: {len(bots)}\n\n"
            
            message += "**System Health:**\n"
            message += "✅ Database: Connected\n"
            message += "✅ Message Filter: Active\n"
            message += "✅ Admin Bot: Running\n\n"
            
            message += f"**Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            message += "**Quick Actions:**\n"
            message += "• `/sessions` - View session details\n"
            message += "• `/listpairs` - View pair details\n"
            message += "• `/listbots` - View bot tokens"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    # =============================================================================
    # IMAGE HANDLING
    # =============================================================================
    
    async def handle_image_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image uploads for hash generation."""
        if not update.message or not update.message.photo:
            return
        
        try:
            # Get the largest photo
            photo = update.message.photo[-1]
            
            # Download the image
            file = await context.bot.get_file(photo.file_id)
            
            # Download image data
            import requests
            response = requests.get(file.file_path)
            if response.status_code != 200:
                await update.message.reply_text("❌ Failed to download image")
                return
            
            image_data = response.content
            
            # Calculate perceptual hash
            from utils.image_hash import image_hash_manager
            image_hash = image_hash_manager.calculate_image_hash(image_data)
            
            if image_hash:
                await update.message.reply_text(
                    f"📸 **Image Hash Generated**\n\n"
                    f"**Hash:** `{image_hash}`\n\n"
                    f"**To block this image:**\n"
                    f"`/blockimage {image_hash}`\n\n"
                    f"This hash identifies similar images using perceptual analysis.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to generate image hash. Make sure imagehash library is available."
                )
                
        except Exception as e:
            logger.error(f"Error handling image upload: {e}")
            await update.message.reply_text(f"❌ Error processing image: {e}")
    
    # =============================================================================
    # PAIR CREATION WIZARD
    # =============================================================================
    
    async def handle_pair_creation_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle input during pair creation process."""
        user_data = context.user_data
        
        if not user_data.get('creating_pair'):
            return False
        
        step = user_data.get('step')
        text = update.message.text.strip()
        
        try:
            if step == 'name':
                user_data['name'] = text
                user_data['step'] = 'source_chat'
                await update.message.reply_text(
                    "**Step 2/6:** Enter the source Telegram chat ID (where messages come from):\n\n"
                    "💡 Forward a message from the chat and use /chatinfo to get the ID.\n"
                    "💡 For channels, use the channel username or ID.",
                    parse_mode='Markdown'
                )
                return True
                
            elif step == 'source_chat':
                try:
                    user_data['source_chat'] = int(text)
                except ValueError:
                    await update.message.reply_text("❌ Please enter a valid chat ID (numbers only)")
                    return True
                
                user_data['step'] = 'discord_webhook'
                await update.message.reply_text(
                    "**Step 3/6:** Enter the Discord webhook URL:\n\n"
                    "💡 Create a webhook in your Discord channel settings.\n"
                    "💡 Right-click channel → Integrations → Webhooks → New Webhook",
                    parse_mode='Markdown'
                )
                return True
                
            elif step == 'discord_webhook':
                if not text.startswith('https://discord.com/api/webhooks/'):
                    await update.message.reply_text("❌ Please enter a valid Discord webhook URL")
                    return True
                
                user_data['discord_webhook'] = text
                user_data['step'] = 'dest_chat'
                await update.message.reply_text(
                    "**Step 4/6:** Enter the destination Telegram chat ID (where messages go):\n\n"
                    "💡 This is where forwarded messages will be posted.\n"
                    "💡 Make sure the bot has posting permissions.",
                    parse_mode='Markdown'
                )
                return True
                
            elif step == 'dest_chat':
                try:
                    user_data['dest_chat'] = int(text)
                except ValueError:
                    await update.message.reply_text("❌ Please enter a valid chat ID (numbers only)")
                    return True
                
                # Show available sessions
                sessions = await self.database.get_all_sessions()
                if not sessions:
                    await update.message.reply_text(
                        "❌ **No Sessions Available**\n\n"
                        "You need to add a Telegram session first.\n"
                        "Use `/addsession` to add a session, then try creating the pair again."
                    )
                    user_data.clear()
                    return True
                
                session_list = "\n".join([f"• {s.session_name}" for s in sessions])
                user_data['step'] = 'session'
                await update.message.reply_text(
                    f"**Step 5/6:** Choose a Telegram session:\n\n"
                    f"**Available sessions:**\n{session_list}\n\n"
                    f"Enter the session name:",
                    parse_mode='Markdown'
                )
                return True
                
            elif step == 'session':
                # Validate session exists
                sessions = await self.database.get_all_sessions()
                valid_sessions = [s.session_name for s in sessions]
                
                if text not in valid_sessions:
                    await update.message.reply_text(
                        f"❌ Invalid session name. Available sessions:\n"
                        f"{', '.join(valid_sessions)}"
                    )
                    return True
                
                user_data['session'] = text
                
                # Show available bots
                bots = await self.bot_manager.get_available_bots()
                if not bots:
                    await update.message.reply_text(
                        "❌ **No Bot Tokens Available**\n\n"
                        "You need to add a bot token first.\n"
                        "Use `/addbot` to add a bot token, then try creating the pair again."
                    )
                    user_data.clear()
                    return True
                
                bot_list = "\n".join([f"• {b['name']} (@{b['username']})" for b in bots])
                user_data['step'] = 'bot'
                await update.message.reply_text(
                    f"**Step 6/6:** Choose a bot token for posting:\n\n"
                    f"**Available bots:**\n{bot_list}\n\n"
                    f"Enter the bot name:",
                    parse_mode='Markdown'
                )
                return True
                
            elif step == 'bot':
                # Validate bot exists
                bots = await self.bot_manager.get_available_bots()
                selected_bot = None
                
                for bot in bots:
                    if bot['name'] == text:
                        selected_bot = bot
                        break
                
                if not selected_bot:
                    bot_names = [b['name'] for b in bots]
                    await update.message.reply_text(
                        f"❌ Invalid bot name. Available bots:\n"
                        f"{', '.join(bot_names)}"
                    )
                    return True
                
                # Create the pair
                await self._create_pair_from_wizard(update, context, selected_bot)
                return True
                
        except Exception as e:
            logger.error(f"Error in pair creation wizard: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
            user_data.clear()
            
        return False
    
    async def _create_pair_from_wizard(self, update: Update, context: ContextTypes.DEFAULT_TYPE, selected_bot: Dict[str, Any]):
        """Create the forwarding pair from wizard data."""
        user_data = context.user_data
        
        try:
            # Validate bot token and permissions
            bot_token = selected_bot['token']
            dest_chat = user_data['dest_chat']
            
            from core.bot_token_manager import BotTokenValidator
            
            # Validate chat permissions
            chat_validation = await BotTokenValidator.validate_chat_permissions(bot_token, dest_chat)
            if not chat_validation['valid']:
                await update.message.reply_text(
                    f"❌ **Bot Permission Error**\n\n"
                    f"The bot cannot post to chat {dest_chat}.\n\n"
                    f"**Error:** {chat_validation['error']}\n\n"
                    "Please add the bot to the destination chat and grant posting permissions."
                )
                user_data.clear()
                return
            
            # Send test message
            test_result = await BotTokenValidator.send_test_message(bot_token, dest_chat)
            if not test_result['valid']:
                await update.message.reply_text(
                    f"⚠️ **Warning: Test Message Failed**\n\n"
                    f"The bot has permissions but test message failed:\n"
                    f"{test_result['error']}\n\n"
                    "Creating pair anyway, but please verify the bot can post."
                )
            
            # Encrypt bot token
            encrypted_token = self.encryption_manager.encrypt(bot_token)
            
            # Create pair object
            from core.database import ForwardingPair
            pair = ForwardingPair(
                name=user_data['name'],
                telegram_source_chat_id=user_data['source_chat'],
                discord_channel_id=0,  # Using webhook instead
                telegram_dest_chat_id=user_data['dest_chat'],
                telegram_bot_token_encrypted=encrypted_token,
                telegram_bot_name=selected_bot['name'],
                discord_webhook_url=user_data['discord_webhook'],
                session_name=user_data['session']
            )
            
            # Save to database
            pair_id = await self.database.add_pair(pair)
            
            if pair_id:
                success_message = (
                    "🎉 **Forwarding Pair Created Successfully!**\n\n"
                    f"**Pair ID:** {pair_id}\n"
                    f"**Name:** {user_data['name']}\n"
                    f"**Source:** `{user_data['source_chat']}`\n"
                    f"**Destination:** `{user_data['dest_chat']}`\n"
                    f"**Session:** {user_data['session']}\n"
                    f"**Bot:** {selected_bot['name']} (@{selected_bot['username']})\n\n"
                )
                
                if test_result['valid']:
                    success_message += "✅ Test message sent successfully!\n"
                
                success_message += "The pair is now active and ready for forwarding."
                
                await update.message.reply_text(success_message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to create forwarding pair in database.")
            
        except Exception as e:
            logger.error(f"Error creating pair from wizard: {e}")
            await update.message.reply_text(f"❌ Error creating pair: {e}")
        finally:
            user_data.clear()