"""Enhanced admin commands for per-pair bot token management."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database, ForwardingPair
from core.session_manager import SessionManager
from core.bot_token_manager import BotTokenValidator, PerPairBotManager
from utils.encryption import EncryptionManager


class EnhancedAdminCommands:
    """Enhanced admin command implementations with bot token management."""
    
    def __init__(self, database: Database, session_manager: SessionManager, encryption_manager: EncryptionManager):
        self.database = database
        self.session_manager = session_manager
        self.encryption_manager = encryption_manager
        self.bot_manager = PerPairBotManager(database, encryption_manager)
    
    async def addpair_enhanced_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /addpair command with bot token validation."""
        try:
            if len(context.args) >= 6:
                # Direct command with arguments: name, source_chat, discord_webhook, dest_chat, session, bot_token
                name, source_chat, discord_webhook, dest_chat, session, bot_token = context.args[:6]
                
                # Validate bot token
                validation_result = await BotTokenValidator.validate_bot_token(bot_token)
                if not validation_result['valid']:
                    await update.message.reply_text(
                        f"❌ Bot token validation failed: {validation_result['error']}\n\n"
                        "Please provide a valid bot token from @BotFather."
                    )
                    return
                
                # Validate chat permissions
                chat_validation = await BotTokenValidator.validate_chat_permissions(bot_token, int(dest_chat))
                if not chat_validation['valid']:
                    await update.message.reply_text(
                        f"❌ Bot permission validation failed: {chat_validation['error']}\n\n"
                        "Please add the bot to the destination chat and grant posting permissions."
                    )
                    return
                
                # Send test message
                test_result = await BotTokenValidator.send_test_message(bot_token, int(dest_chat))
                if not test_result['valid']:
                    await update.message.reply_text(
                        f"❌ Test message failed: {test_result['error']}\n\n"
                        "Bot token is valid but cannot post to the destination chat."
                    )
                    return
                
                # Encrypt bot token
                encrypted_token = self.encryption_manager.encrypt(bot_token)
                
                # Create pair
                pair = ForwardingPair(
                    name=name,
                    telegram_source_chat_id=int(source_chat),
                    discord_channel_id=0,  # Will use webhook URL instead
                    telegram_dest_chat_id=int(dest_chat),
                    telegram_bot_token_encrypted=encrypted_token,
                    discord_webhook_url=discord_webhook,
                    session_name=session
                )
                
                pair_id = await self.database.add_pair(pair)
                if pair_id:
                    bot_info = validation_result
                    await update.message.reply_text(
                        f"✅ Successfully created forwarding pair '{name}' (ID: {pair_id})\n\n"
                        f"🤖 Bot: @{bot_info['username']} ({bot_info['first_name']})\n"
                        f"📨 Source: `{source_chat}`\n"
                        f"🌐 Discord Webhook: {discord_webhook[:50]}...\n"
                        f"📤 Destination: `{dest_chat}`\n"
                        f"🔧 Session: {session}\n\n"
                        f"🔒 Bot token encrypted and stored securely.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Failed to create forwarding pair")
            else:
                # Interactive mode
                await self._start_enhanced_pair_creation(update, context)
                
        except ValueError as e:
            await update.message.reply_text(f"❌ Invalid chat/channel ID format: {e}")
        except Exception as e:
            logger.error(f"Error in enhanced addpair command: {e}")
            await update.message.reply_text(f"❌ Error creating pair: {e}")
    
    async def _start_enhanced_pair_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start interactive enhanced pair creation."""
        user_data = context.user_data
        user_data.clear()
        user_data['creating_pair'] = True
        user_data['step'] = 'name'
        
        instructions = (
            "🚀 **Enhanced Pair Creation Wizard**\n\n"
            "This wizard will help you create a forwarding pair with bot token validation.\n\n"
            "**Step 1/6:** Enter a unique name for this forwarding pair:"
        )
        
        await update.message.reply_text(instructions, parse_mode='Markdown')
    
    async def handle_enhanced_pair_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle enhanced pair creation steps."""
        user_data = context.user_data
        
        if not user_data.get('creating_pair'):
            return False
        
        step = user_data.get('step')
        text = update.message.text.strip()
        
        if step == 'name':
            user_data['name'] = text
            user_data['step'] = 'source_chat'
            await update.message.reply_text(
                "**Step 2/6:** Enter the source Telegram chat ID (where messages come from):\n\n"
                "💡 Forward a message from the chat and use /chatinfo to get the ID.",
                parse_mode='Markdown'
            )
            
        elif step == 'source_chat':
            try:
                user_data['source_chat'] = int(text)
                user_data['step'] = 'discord_webhook'
                await update.message.reply_text(
                    "**Step 3/6:** Enter the Discord webhook URL:\n\n"
                    "💡 Create a webhook in your Discord channel settings.",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format. Please enter a valid number.")
                return True
                
        elif step == 'discord_webhook':
            if not text.startswith('https://discord.com/api/webhooks/'):
                await update.message.reply_text(
                    "❌ Invalid webhook URL format. Please provide a valid Discord webhook URL."
                )
                return True
            user_data['discord_webhook'] = text
            user_data['step'] = 'dest_chat'
            await update.message.reply_text(
                "**Step 4/6:** Enter the destination Telegram chat ID (where messages go):\n\n"
                "💡 This is where the bot will post forwarded messages.",
                parse_mode='Markdown'
            )
            
        elif step == 'dest_chat':
            try:
                user_data['dest_chat'] = int(text)
                user_data['step'] = 'session'
                
                # List available sessions
                sessions = await self.session_manager.list_sessions()
                if sessions:
                    session_list = '\n'.join([f"• {s.name}" for s in sessions])
                    await update.message.reply_text(
                        f"**Step 5/6:** Choose a Telegram session:\n\n"
                        f"Available sessions:\n{session_list}\n\n"
                        f"Enter the session name:",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ No sessions available. Please add a session first using `/addsession`."
                    )
                    user_data.clear()
                    return True
                    
            except ValueError:
                await update.message.reply_text("❌ Invalid chat ID format. Please enter a valid number.")
                return True
                
        elif step == 'session':
            # Validate session exists
            sessions = await self.session_manager.list_sessions()
            session_names = [s.name for s in sessions]
            
            if text not in session_names:
                await update.message.reply_text(
                    f"❌ Session '{text}' not found. Available sessions: {', '.join(session_names)}"
                )
                return True
                
            user_data['session'] = text
            user_data['step'] = 'bot_token'
            await update.message.reply_text(
                "**Step 6/6:** Enter the Telegram bot token for destination posting:\n\n"
                "💡 Get this from @BotFather\n"
                "🔒 Token will be encrypted and stored securely\n"
                "⚠️ The bot will be validated before creating the pair",
                parse_mode='Markdown'
            )
            
        elif step == 'bot_token':
            # Validate and create pair
            await self._validate_and_create_enhanced_pair(update, context, text)
            return True
            
        return True
    
    async def _validate_and_create_enhanced_pair(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bot_token: str):
        """Validate bot token and create the pair."""
        user_data = context.user_data
        
        # Show validation progress
        validation_msg = await update.message.reply_text("🔍 Validating bot token...")
        
        try:
            # Step 1: Validate bot token
            await validation_msg.edit_text("🔍 Validating bot token... (1/3)")
            validation_result = await BotTokenValidator.validate_bot_token(bot_token)
            
            if not validation_result['valid']:
                await validation_msg.edit_text(
                    f"❌ Bot token validation failed: {validation_result['error']}\n\n"
                    "Please check your token and try again."
                )
                user_data.clear()
                return
            
            # Step 2: Validate chat permissions
            await validation_msg.edit_text("🔍 Validating chat permissions... (2/3)")
            chat_validation = await BotTokenValidator.validate_chat_permissions(
                bot_token, user_data['dest_chat']
            )
            
            if not chat_validation['valid']:
                await validation_msg.edit_text(
                    f"❌ Chat permission validation failed: {chat_validation['error']}\n\n"
                    "Please add the bot to the destination chat and grant posting permissions."
                )
                user_data.clear()
                return
            
            # Step 3: Send test message
            await validation_msg.edit_text("🔍 Sending test message... (3/3)")
            test_result = await BotTokenValidator.send_test_message(bot_token, user_data['dest_chat'])
            
            if not test_result['valid']:
                await validation_msg.edit_text(
                    f"❌ Test message failed: {test_result['error']}\n\n"
                    "Bot token is valid but cannot post to the destination chat."
                )
                user_data.clear()
                return
            
            # All validations passed - create pair
            await validation_msg.edit_text("✅ All validations passed! Creating forwarding pair...")
            
            # Encrypt bot token
            encrypted_token = self.encryption_manager.encrypt(bot_token)
            
            # Create pair
            pair = ForwardingPair(
                name=user_data['name'],
                telegram_source_chat_id=user_data['source_chat'],
                discord_channel_id=0,
                telegram_dest_chat_id=user_data['dest_chat'],
                telegram_bot_token_encrypted=encrypted_token,
                discord_webhook_url=user_data['discord_webhook'],
                session_name=user_data['session']
            )
            
            pair_id = await self.database.add_pair(pair)
            
            if pair_id:
                bot_info = validation_result
                await validation_msg.edit_text(
                    f"✅ **Forwarding Pair Created Successfully!**\n\n"
                    f"**ID:** {pair_id}\n"
                    f"**Name:** {user_data['name']}\n"
                    f"**Bot:** @{bot_info['username']} ({bot_info['first_name']})\n"
                    f"**Source:** `{user_data['source_chat']}`\n"
                    f"**Destination:** `{user_data['dest_chat']}`\n"
                    f"**Session:** {user_data['session']}\n\n"
                    f"🔒 Bot token encrypted and stored securely.\n"
                    f"🚀 Pair is now active and ready for forwarding!",
                    parse_mode='Markdown'
                )
            else:
                await validation_msg.edit_text("❌ Failed to create forwarding pair in database.")
                
        except Exception as e:
            logger.error(f"Error in enhanced pair creation: {e}")
            await validation_msg.edit_text(f"❌ Error during validation: {e}")
        
        finally:
            user_data.clear()
    
    async def validate_bot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Validate bot token for a specific pair."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: `/validatebot <pair_id>`\n\n"
                    "This command validates the bot token for a forwarding pair."
                )
                return
            
            pair_id = int(context.args[0])
            
            # Get pair
            pair = await self.database.get_pair(pair_id)
            if not pair:
                await update.message.reply_text(f"❌ Forwarding pair {pair_id} not found.")
                return
            
            # Validate bot token
            validation_msg = await update.message.reply_text(f"🔍 Validating bot for pair {pair_id}...")
            
            validation_result = await self.bot_manager.validate_pair_bot_token(pair_id)
            
            if validation_result['valid']:
                chat_perms = validation_result.get('chat_permissions', {})
                permissions_text = ""
                if chat_perms.get('valid'):
                    permissions_text = (
                        f"**Chat Permissions:**\n"
                        f"• Status: {chat_perms.get('status', 'unknown')}\n"
                        f"• Send Messages: {'✅' if chat_perms.get('can_send_messages') else '❌'}\n"
                        f"• Send Media: {'✅' if chat_perms.get('can_send_media') else '❌'}\n"
                        f"• Edit Messages: {'✅' if chat_perms.get('can_edit_messages') else '❌'}\n"
                        f"• Delete Messages: {'✅' if chat_perms.get('can_delete_messages') else '❌'}\n\n"
                    )
                
                await validation_msg.edit_text(
                    f"✅ **Bot Validation Successful**\n\n"
                    f"**Pair:** {pair.name} (ID: {pair_id})\n"
                    f"**Bot:** @{validation_result['username']} ({validation_result['first_name']})\n"
                    f"**Bot ID:** {validation_result['bot_id']}\n\n"
                    f"{permissions_text}"
                    f"Bot is ready for message forwarding!",
                    parse_mode='Markdown'
                )
            else:
                await validation_msg.edit_text(
                    f"❌ **Bot Validation Failed**\n\n"
                    f"**Pair:** {pair.name} (ID: {pair_id})\n"
                    f"**Error:** {validation_result['error']}\n\n"
                    f"Please check the bot token and permissions."
                )
                
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID format. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in validate bot command: {e}")
            await update.message.reply_text(f"❌ Error validating bot: {e}")
    
    async def update_bot_token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update bot token for a specific pair."""
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "Usage: `/updatebottoken <pair_id> <new_bot_token>`\n\n"
                    "This command updates the bot token for a forwarding pair."
                )
                return
            
            pair_id = int(context.args[0])
            new_token = context.args[1]
            
            # Get pair
            pair = await self.database.get_pair(pair_id)
            if not pair:
                await update.message.reply_text(f"❌ Forwarding pair {pair_id} not found.")
                return
            
            # Validate new token
            validation_msg = await update.message.reply_text(f"🔍 Validating new bot token...")
            
            validation_result = await BotTokenValidator.validate_bot_token(new_token)
            if not validation_result['valid']:
                await validation_msg.edit_text(
                    f"❌ Bot token validation failed: {validation_result['error']}"
                )
                return
            
            # Validate chat permissions
            chat_validation = await BotTokenValidator.validate_chat_permissions(
                new_token, pair.telegram_dest_chat_id
            )
            if not chat_validation['valid']:
                await validation_msg.edit_text(
                    f"❌ Chat permission validation failed: {chat_validation['error']}"
                )
                return
            
            # Update pair with new encrypted token
            encrypted_token = self.encryption_manager.encrypt(new_token)
            pair.telegram_bot_token_encrypted = encrypted_token
            
            success = await self.database.update_pair(pair)
            if success:
                # Remove old bot instance from cache
                await self.bot_manager.remove_bot_for_pair(pair_id)
                
                await validation_msg.edit_text(
                    f"✅ **Bot Token Updated Successfully**\n\n"
                    f"**Pair:** {pair.name} (ID: {pair_id})\n"
                    f"**New Bot:** @{validation_result['username']} ({validation_result['first_name']})\n\n"
                    f"🔒 Token encrypted and stored securely."
                )
            else:
                await validation_msg.edit_text("❌ Failed to update bot token in database.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid pair ID format. Please provide a valid number.")
        except Exception as e:
            logger.error(f"Error in update bot token command: {e}")
            await update.message.reply_text(f"❌ Error updating bot token: {e}")