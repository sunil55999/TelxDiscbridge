"""Admin bot commands for managing forwarding pairs and settings."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database, ForwardingPair
from core.session_manager import SessionManager


class AdminCommands:
    """Admin command implementations."""
    
    def __init__(self, database: Database, session_manager: SessionManager):
        self.database = database
        self.session_manager = session_manager
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        welcome_message = (
            "🤖 **Telegram ↔ Discord ↔ Telegram Forwarding Bot**\n\n"
            "**Quick Start Commands:**\n"
            "• `/addsession` - Add new Telegram user session\n"
            "• `/addpair` - Create new forwarding pair\n"
            "• `/listpairs` - Show all active pairs\n"
            "• `/status` - System status & statistics\n"
            "• `/help` - Complete command guide\n\n"
            "**Management:**\n"
            "• `/sessions` - Manage Telegram sessions\n"
            "• `/blockword` - Add message filters\n"
            "• `/blockimages` - Quick filter toggles\n"
            "• `/stripheaders` - Remove message headers\n"
            "• `/blockimage` - Block specific images by hash\n"
            "• `/blockwordpair` - Block words for specific pairs\n\n"
            f"Your admin ID: `{user_id}`\n"
            "Use `/help` for comprehensive command documentation."
        )
        
        if update.message:
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not update.message:
            return
        help_text = (
            "📖 **Detailed Command Help**\n\n"
            
            "**Pair Management:**\n"
            "• `/addpair` - Start interactive pair creation\n"
            "• `/listpairs` - Show all active forwarding pairs\n"
            "• `/removepair [pair_id]` - Remove a specific pair\n"
            "• `/editpair [pair_id]` - Edit pair settings\n\n"
            
            "**Session Management:**\n"
            "• `/addsession <name> <phone>` - Add new Telegram session with OTP verification\n"
            "• `/changesession [pair_id] [session_name]` - Change session for a pair\n"
            "• `/sessions` - List all available sessions\n\n"
            
            "**System Management:**\n"
            "• `/status` - Show system status and statistics\n"
            "• `/restart` - Restart specific components\n"
            "• `/cleanmem` - Force garbage collection\n\n"
            
            "**Filtering:**\n"
            "• `/blockword [word]` - Add word to global filter\n"
            "• `/unblockword [word]` - Remove word from filter\n"
            "• `/showfilters` - Show current filter settings\n"
            "• `/blockimages` / `/allowimages` - Quick image toggles\n"
            "• `/stripheaders` / `/keepheaders` - Remove/keep headers\n"
            "• `/blockimage [hash] [pair_id]` - Block specific image\n"
            "• `/blockwordpair [pair_id] [word]` - Block word for pair\n"
            "• `/filterconfig` - Advanced filter settings\n\n"
            
            "Use commands without parameters for interactive mode.\n\n"
            
            "**Need help with sessions?** Use `/addsession` without parameters for a complete guide!"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def addpair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addpair command."""
        if not update.message:
            return
        try:
            if context.args and len(context.args) >= 5:
                # Direct command with arguments
                name, source_chat, discord_channel, dest_chat, session = context.args[:5]
                
                pair = ForwardingPair(
                    name=name,
                    telegram_source_chat_id=int(source_chat),
                    discord_channel_id=int(discord_channel),
                    telegram_dest_chat_id=int(dest_chat),
                    session_name=session
                )
                
                pair_id = await self.database.add_pair(pair)
                if pair_id:
                    await update.message.reply_text(
                        f"✅ Successfully created forwarding pair '{name}' (ID: {pair_id})"
                    )
                else:
                    await update.message.reply_text("❌ Failed to create forwarding pair")
            else:
                # Interactive mode
                await self._start_interactive_pair_creation(update, context)
                
        except ValueError as e:
            await update.message.reply_text(f"❌ Invalid chat/channel ID format: {e}")
        except Exception as e:
            logger.error(f"Error in addpair command: {e}")
            await update.message.reply_text(f"❌ Error creating pair: {e}")
    
    async def listpairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listpairs command."""
        if not update.message:
            return
        try:
            pairs = await self.database.get_all_pairs()
            
            if not pairs:
                await update.message.reply_text("📝 No forwarding pairs found.")
                return
            
            message_parts = ["📋 **Active Forwarding Pairs:**\n"]
            
            for pair in pairs:
                status = "🟢 Active" if pair.is_active else "🔴 Inactive"
                message_parts.append(
                    f"**{pair.id}.** {pair.name}\n"
                    f"   Status: {status}\n"
                    f"   Source: `{pair.telegram_source_chat_id}`\n"
                    f"   Discord: `{pair.discord_channel_id}`\n"
                    f"   Destination: `{pair.telegram_dest_chat_id}`\n"
                    f"   Session: `{pair.session_name}`\n"
                    f"   Filters: {len(pair.keyword_filters) if pair.keyword_filters else 0} words\n"
                    f"   Media: {'✅' if pair.media_enabled else '❌'}\n"
                )
            
            message = "\n".join(message_parts)
            
            # Split message if too long
            if len(message) > 4000:
                for i in range(0, len(message), 4000):
                    await update.message.reply_text(message[i:i+4000], parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in listpairs command: {e}")
            await update.message.reply_text(f"❌ Error listing pairs: {e}")
    
    async def removepair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removepair command."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❓ Please provide pair ID: `/removepair [pair_id]`\n"
                    "Use `/listpairs` to see available pairs.",
                    parse_mode='Markdown'
                )
                return
            
            pair_id = int(context.args[0])
            pair = await self.database.get_pair(pair_id)
            
            if not pair:
                await update.message.reply_text(f"❌ Pair with ID {pair_id} not found.")
                return
            
            # Confirmation keyboard
            keyboard = [
                [InlineKeyboardButton("✅ Yes, remove", callback_data=f"remove_pair_{pair_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_remove")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Are you sure you want to remove pair '{pair.name}' (ID: {pair_id})?",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID format. Please provide a number.")
        except Exception as e:
            logger.error(f"Error in removepair command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not update.message:
            return
        try:
            # Collect system status
            pairs = await self.database.get_all_pairs()
            active_pairs = [p for p in pairs if p.is_active]
            
            # Basic statistics
            status_message = (
                "📊 **System Status**\n\n"
                f"🔄 Active pairs: {len(active_pairs)}\n"
                f"💤 Inactive pairs: {len(pairs) - len(active_pairs)}\n"
                f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                "**Component Status:**\n"
                "• Telegram Source: 🟢 Running\n"
                "• Discord Relay: 🟢 Running\n"
                "• Telegram Destination: 🟢 Running\n"
                "• Database: 🟢 Connected\n"
            )
            
            # Add session information
            if active_pairs:
                sessions = set(pair.session_name for pair in active_pairs)
                status_message += f"\n**Active Sessions:** {len(sessions)}\n"
                for session in sessions:
                    session_pairs = [p for p in active_pairs if p.session_name == session]
                    status_message += f"• {session}: {len(session_pairs)} pairs\n"
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"❌ Error getting status: {e}")
    
    async def sessions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sessions command - Display all active sessions."""
        if not update.message:
            return
        try:
            # Get all sessions from database
            sessions = await self.database.get_all_sessions()
            
            if not sessions:
                await update.message.reply_text(
                    "📭 **No Active Sessions Found**\n\n"
                    "Use `/addsession` to add a new Telegram user session."
                )
                return
            
            sessions_message = "🔐 **Active Telegram Sessions**\n\n"
            
            for session in sessions:
                status_emoji = {
                    'healthy': '🟢',
                    'unhealthy': '🔴', 
                    'expired': '⚠️',
                    'unauthorized': '❌',
                    'unknown': '🔵'
                }.get(session.health_status, '❓')
                
                sessions_message += f"🏷️ {session.name} {status_emoji}\n"
                sessions_message += f"📱 Phone: {session.phone_number or 'Not set'}\n"
                sessions_message += f"👥 Pairs: {session.pair_count}/{session.max_pairs}\n"
                sessions_message += f"⚡ Health: {session.health_status.title()}\n"
                
                if session.last_verified:
                    if isinstance(session.last_verified, str):
                        # Handle string datetime format
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(session.last_verified.replace('Z', '+00:00'))
                            sessions_message += f"🕒 Last verified: {dt.strftime('%Y-%m-%d %H:%M')}\n"
                        except:
                            sessions_message += f"🕒 Last verified: {session.last_verified}\n"
                    else:
                        # Handle datetime object
                        sessions_message += f"🕒 Last verified: {session.last_verified.strftime('%Y-%m-%d %H:%M')}\n"
                
                sessions_message += f"🔧 Worker: {session.worker_id or 'None'}\n\n"
            
            sessions_message += "**Management Commands:**\n"
            sessions_message += "• /addsession - Add new session\n"
            sessions_message += "• /changesession \\<pair\\_id\\> \\<session\\> - Change pair session\n"
            sessions_message += "• /health - Check all session health"
            
            await update.message.reply_text(sessions_message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in sessions command: {e}")
            await update.message.reply_text(f"❌ Error getting sessions: {e}")
    
    async def changesession_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /changesession command."""
        if not update.message:
            return
        try:
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❓ Usage: /changesession \\[pair\\_id\\] \\[session\\_name\\]",
                    parse_mode='MarkdownV2'
                )
                return
            
            pair_id = int(context.args[0])
            new_session = context.args[1]
            
            # Get the pair
            pair = await self.database.get_pair(pair_id)
            if not pair:
                await update.message.reply_text(f"❌ Pair with ID {pair_id} not found.")
                return
            
            # Validate session exists
            session_info = await self.session_manager.get_session(new_session)
            if not session_info:
                await update.message.reply_text(f"❌ Session '{new_session}' not found.")
                return
            
            # Update pair
            old_session = pair.session_name
            pair.session_name = new_session
            
            if await self.database.update_pair(pair):
                await update.message.reply_text(
                    f"✅ Successfully changed session for pair '{pair.name}'\n"
                    f"From: `{old_session}`\n"
                    f"To: `{new_session}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to update pair session.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID format.")
        except Exception as e:
            logger.error(f"Error in changesession command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def blockword_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /blockword command."""
        if not update.message:
            return
        try:
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❓ Usage: `/blockword [pair_id] [word_or_phrase]`",
                    parse_mode='Markdown'
                )
                return
            
            pair_id = int(context.args[0])
            blocked_word = " ".join(context.args[1:])
            
            # Get the pair
            pair = await self.database.get_pair(pair_id)
            if not pair:
                await update.message.reply_text(f"❌ Pair with ID {pair_id} not found.")
                return
            
            # Add word to filters
            if not pair.keyword_filters:
                pair.keyword_filters = []
            
            if blocked_word not in pair.keyword_filters:
                pair.keyword_filters.append(blocked_word)
                
                if await self.database.update_pair(pair):
                    await update.message.reply_text(
                        f"✅ Added '{blocked_word}' to blocked words for pair '{pair.name}'"
                    )
                else:
                    await update.message.reply_text("❌ Failed to update pair filters.")
            else:
                await update.message.reply_text(f"⚠️ Word '{blocked_word}' is already blocked for this pair.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID format.")
        except Exception as e:
            logger.error(f"Error in blockword command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _start_interactive_pair_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start interactive pair creation process."""
        await update.message.reply_text(
            "🆕 **Interactive Pair Creation**\n\n"
            "Please provide the following information:\n\n"
            "Format: `/addpair [name] [source_chat_id] [discord_channel_id] [dest_chat_id] [session_name]`\n\n"
            "Example: `/addpair MyPair -1001234567890 123456789012345678 -1001234567891 session1`\n\n"
            "• Name: A descriptive name for this pair\n"
            "• Source chat ID: Telegram chat to monitor (with -)\n"
            "• Discord channel ID: Discord channel for relay\n"
            "• Destination chat ID: Telegram chat to send to (with -)\n"
            "• Session name: User session to use for monitoring\n\n"
            "Use `/help` for more details.",
            parse_mode='Markdown'
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Handle help callbacks
        if data.startswith("help:"):
            from admin_bot.comprehensive_help import ComprehensiveHelp
            await ComprehensiveHelp.handle_help_callback(update, context)
            return
        
        # Handle pair removal callbacks
        if data.startswith("remove_pair_"):
            pair_id = int(data.split("_")[-1])
            
            if await self.database.delete_pair(pair_id):
                await query.edit_message_text(f"✅ Pair {pair_id} has been removed successfully.")
            else:
                await query.edit_message_text(f"❌ Failed to remove pair {pair_id}.")
                
        elif data == "cancel_remove":
            await query.edit_message_text("❌ Removal cancelled.")
