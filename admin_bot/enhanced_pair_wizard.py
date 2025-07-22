"""Enhanced pair creation wizard with bot selection and auto-webhook creation."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database, ForwardingPair
from core.session_manager import SessionManager
from admin_bot.bot_management import BotTokenManager
from admin_bot.discord_integration import DiscordChannelCommands
from utils.encryption import EncryptionManager


class EnhancedPairWizard:
    """Enhanced pair creation wizard with modern features."""
    
    def __init__(self, database: Database, session_manager: SessionManager, 
                 encryption_manager: EncryptionManager, discord_bot_token: str):
        self.database = database
        self.session_manager = session_manager
        self.encryption_manager = encryption_manager
        self.bot_manager = BotTokenManager(database, encryption_manager)
        self.discord_commands = DiscordChannelCommands(discord_bot_token)
        
        # Store wizard state for each user
        self.wizard_state = {}
    
    async def start_pair_wizard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the enhanced pair creation wizard."""
        try:
            user_id = update.effective_user.id
            
            # Initialize wizard state
            self.wizard_state[user_id] = {
                'step': 'name',
                'data': {},
                'started_at': datetime.now()
            }
            
            message = (
                "🚀 **Enhanced Pair Creation Wizard**\n\n"
                "I'll guide you through creating a new forwarding pair with these modern features:\n"
                "• Bot token selection from saved bots\n"
                "• Auto-webhook creation with source names\n"
                "• Discord Channel ID input (not webhook URL)\n"
                "• Session selection from active sessions\n\n"
                "**Step 1/6: Pair Name**\n"
                "Enter a unique name for this forwarding pair:"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error starting pair wizard: {e}")
            await update.message.reply_text(f"❌ Error starting wizard: {e}")
    
    async def handle_wizard_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user input during wizard steps."""
        try:
            user_id = update.effective_user.id
            
            if user_id not in self.wizard_state:
                return  # Not in wizard mode
            
            state = self.wizard_state[user_id]
            step = state['step']
            user_input = update.message.text.strip()
            
            if step == 'name':
                await self._handle_name_step(update, user_input, user_id)
            elif step == 'source_chat':
                await self._handle_source_chat_step(update, user_input, user_id)
            elif step == 'discord_channel':
                await self._handle_discord_channel_step(update, user_input, user_id)
            elif step == 'dest_chat':
                await self._handle_dest_chat_step(update, user_input, user_id)
            elif step == 'session':
                await self._handle_session_step(update, user_input, user_id)
            elif step == 'bot_selection':
                await self._handle_bot_selection_step(update, user_input, user_id)
                
        except Exception as e:
            logger.error(f"Error handling wizard input: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _handle_name_step(self, update: Update, user_input: str, user_id: int):
        """Handle pair name input."""
        # Validate name uniqueness
        existing_pairs = await self.database.get_all_pairs()
        if any(pair.name == user_input for pair in existing_pairs):
            await update.message.reply_text(
                f"❌ Pair name '{user_input}' already exists. Please choose a different name:"
            )
            return
        
        self.wizard_state[user_id]['data']['name'] = user_input
        self.wizard_state[user_id]['step'] = 'source_chat'
        
        await update.message.reply_text(
            "✅ Pair name set!\n\n"
            "**Step 2/6: Source Telegram Chat**\n"
            "Enter the Telegram chat ID to monitor for messages:\n"
            "Example: `-1001234567890`"
        )
    
    async def _handle_source_chat_step(self, update: Update, user_input: str, user_id: int):
        """Handle source chat ID input."""
        try:
            source_chat_id = int(user_input)
            self.wizard_state[user_id]['data']['source_chat_id'] = source_chat_id
            self.wizard_state[user_id]['step'] = 'discord_channel'
            
            await update.message.reply_text(
                "✅ Source chat ID set!\n\n"
                "**Step 3/6: Discord Channel**\n"
                "Enter the Discord Channel ID where messages will be relayed:\n"
                "Example: `1234567890123456789`\n\n"
                "💡 To find channel ID: Right-click channel → Copy ID"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid chat ID format. Please enter a valid number:\n"
                "Example: `-1001234567890`"
            )
    
    async def _handle_discord_channel_step(self, update: Update, user_input: str, user_id: int):
        """Handle Discord channel ID input and create webhook."""
        try:
            discord_channel_id = int(user_input)
            
            # Validate Discord channel
            validation = await self.discord_commands.validate_discord_channel(discord_channel_id)
            if not validation['success']:
                await update.message.reply_text(
                    f"❌ Discord channel validation failed: {validation['error']}\n\n"
                    "Please check:\n"
                    "• Channel ID is correct\n"
                    "• Bot has access to the channel\n"
                    "• Bot has 'Manage Webhooks' permission"
                )
                return
            
            # Create webhook with source channel name
            source_name = self.wizard_state[user_id]['data']['name']
            webhook_result = await self.discord_commands.create_webhook_for_pair(
                discord_channel_id, source_name
            )
            
            if not webhook_result['success']:
                await update.message.reply_text(
                    f"❌ Failed to create Discord webhook: {webhook_result['error']}\n\n"
                    "Please ensure the bot has 'Manage Webhooks' permission in the channel."
                )
                return
            
            self.wizard_state[user_id]['data']['discord_channel_id'] = discord_channel_id
            self.wizard_state[user_id]['data']['webhook_url'] = webhook_result['webhook_url']
            self.wizard_state[user_id]['step'] = 'dest_chat'
            
            await update.message.reply_text(
                f"✅ Discord channel validated and webhook created!\n"
                f"🌐 Channel: {validation.get('channel_name', 'Unknown')}\n"
                f"🔗 Webhook: {webhook_result['webhook_name']}\n\n"
                "**Step 4/6: Destination Telegram Chat**\n"
                "Enter the Telegram chat ID where final messages will be posted:\n"
                "Example: `-1009876543210`"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid channel ID format. Please enter a valid Discord channel ID:\n"
                "Example: `1234567890123456789`"
            )
    
    async def _handle_dest_chat_step(self, update: Update, user_input: str, user_id: int):
        """Handle destination chat ID input."""
        try:
            dest_chat_id = int(user_input)
            self.wizard_state[user_id]['data']['dest_chat_id'] = dest_chat_id
            self.wizard_state[user_id]['step'] = 'session'
            
            # Show available sessions
            sessions = await self.database.get_all_sessions()
            if not sessions:
                await update.message.reply_text(
                    "❌ No active sessions found!\n\n"
                    "Please add a session first using `/addsession` and then restart the wizard."
                )
                del self.wizard_state[user_id]
                return
            
            session_list = "**Step 5/6: Session Selection**\n\n"
            session_list += "Available Telegram user sessions:\n\n"
            
            for i, session in enumerate(sessions, 1):
                status_emoji = '🟢' if session.health_status == 'healthy' else '🔴'
                session_list += f"{i}. **{session.name}** {status_emoji}\n"
                session_list += f"   📱 {session.phone_number or 'No phone'}\n"
                session_list += f"   👥 {session.pair_count}/{session.max_pairs} pairs\n\n"
            
            session_list += "Enter the session name you want to use:"
            
            await update.message.reply_text(session_list, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid chat ID format. Please enter a valid number:\n"
                "Example: `-1009876543210`"
            )
    
    async def _handle_session_step(self, update: Update, user_input: str, user_id: int):
        """Handle session selection."""
        sessions = await self.database.get_all_sessions()
        selected_session = None
        
        for session in sessions:
            if session.name == user_input:
                selected_session = session
                break
        
        if not selected_session:
            available_sessions = [s.name for s in sessions]
            await update.message.reply_text(
                f"❌ Session '{user_input}' not found.\n\n"
                f"Available sessions: {', '.join(available_sessions)}"
            )
            return
        
        self.wizard_state[user_id]['data']['session_name'] = user_input
        self.wizard_state[user_id]['step'] = 'bot_selection'
        
        # Show available bot tokens
        bots = await self.bot_manager.get_available_bots()
        if not bots:
            await update.message.reply_text(
                "❌ No bot tokens available!\n\n"
                "Please add a bot token first using `/addbot <name> <token>` and then restart the wizard."
            )
            del self.wizard_state[user_id]
            return
        
        bot_list = "**Step 6/6: Bot Token Selection**\n\n"
        bot_list += "Available bot tokens for destination posting:\n\n"
        
        for i, bot in enumerate(bots, 1):
            bot_list += f"{i}. **{bot['name']}**\n"
            bot_list += f"   🤖 @{bot['username']} ({bot['first_name']})\n"
            bot_list += f"   📅 Added: {bot['added_at'].strftime('%Y-%m-%d')}\n\n"
        
        bot_list += "Enter the bot name you want to use for posting to the destination chat:"
        
        await update.message.reply_text(bot_list, parse_mode='Markdown')
    
    async def _handle_bot_selection_step(self, update: Update, user_input: str, user_id: int):
        """Handle bot token selection and complete pair creation."""
        # Get bot token
        bot_token = await self.bot_manager.get_bot_token_by_name(user_input)
        if not bot_token:
            bots = await self.bot_manager.get_available_bots()
            bot_names = [bot['name'] for bot in bots]
            await update.message.reply_text(
                f"❌ Bot '{user_input}' not found.\n\n"
                f"Available bots: {', '.join(bot_names)}"
            )
            return
        
        # Validate bot permissions for destination chat
        from core.bot_token_manager import BotTokenValidator
        dest_chat_id = self.wizard_state[user_id]['data']['dest_chat_id']
        
        chat_validation = await BotTokenValidator.validate_chat_permissions(bot_token, dest_chat_id)
        if not chat_validation['valid']:
            await update.message.reply_text(
                f"❌ Bot '{user_input}' cannot post to destination chat: {chat_validation['error']}\n\n"
                "Please add the bot to the destination chat and grant posting permissions."
            )
            return
        
        # Create the pair
        await self._create_pair(update, user_id, user_input, bot_token)
    
    async def _create_pair(self, update: Update, user_id: int, bot_name: str, bot_token: str):
        """Create the forwarding pair with all collected data."""
        try:
            data = self.wizard_state[user_id]['data']
            
            # Encrypt bot token
            encrypted_token = self.encryption_manager.encrypt(bot_token)
            
            # Create pair object
            pair = ForwardingPair(
                name=data['name'],
                telegram_source_chat_id=data['source_chat_id'],
                discord_channel_id=data['discord_channel_id'],
                telegram_dest_chat_id=data['dest_chat_id'],
                telegram_bot_token_encrypted=encrypted_token,
                telegram_bot_name=bot_name,
                discord_webhook_url=data['webhook_url'],
                session_name=data['session_name']
            )
            
            # Save to database
            pair_id = await self.database.add_pair(pair)
            
            if pair_id:
                # Send test message
                from core.bot_token_manager import BotTokenValidator
                test_result = await BotTokenValidator.send_test_message(bot_token, data['dest_chat_id'])
                
                success_message = (
                    "🎉 **Forwarding Pair Created Successfully!**\n\n"
                    f"**Pair ID:** {pair_id}\n"
                    f"**Name:** {data['name']}\n"
                    f"**Source:** {data['source_chat_id']}\n"
                    f"**Discord Channel:** {data['discord_channel_id']}\n"
                    f"**Destination:** {data['dest_chat_id']}\n"
                    f"**Session:** {data['session_name']}\n"
                    f"**Bot:** {bot_name}\n\n"
                )
                
                if test_result['valid']:
                    success_message += "✅ Test message sent successfully to destination chat!\n\n"
                else:
                    success_message += f"⚠️ Pair created but test message failed: {test_result['error']}\n\n"
                
                success_message += "The forwarding pair is now active and will start processing messages."
                
                await update.message.reply_text(success_message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to create forwarding pair in database.")
            
            # Clean up wizard state
            del self.wizard_state[user_id]
            
        except Exception as e:
            logger.error(f"Error creating pair: {e}")
            await update.message.reply_text(f"❌ Error creating pair: {e}")
            del self.wizard_state[user_id]