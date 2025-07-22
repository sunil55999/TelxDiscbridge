"""Bot token management commands for admin interface."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database, ForwardingPair
from core.bot_token_manager import BotTokenValidator
from utils.encryption import EncryptionManager


class BotTokenManager:
    """Bot token management and naming system."""
    
    def __init__(self, database: Database, encryption_manager: EncryptionManager):
        self.database = database
        self.encryption_manager = encryption_manager
        self.bot_cache = {}  # Cache for validated bot information
    
    async def add_named_bot_token(self, bot_name: str, bot_token: str) -> Dict[str, Any]:
        """Add a named bot token to the system."""
        try:
            # Validate bot token
            validation_result = await BotTokenValidator.validate_bot_token(bot_token)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f"Bot token validation failed: {validation_result['error']}"
                }
            
            # Store in cache with name
            bot_info = validation_result['bot_info']
            self.bot_cache[bot_name] = {
                'token': bot_token,
                'bot_info': bot_info,
                'added_at': datetime.now(),
                'username': bot_info.get('username', 'Unknown'),
                'first_name': bot_info.get('first_name', 'Unknown Bot')
            }
            
            return {
                'success': True,
                'bot_info': bot_info,
                'message': f"Bot '{bot_name}' (@{bot_info.get('username', 'unknown')}) added successfully"
            }
            
        except Exception as e:
            logger.error(f"Error adding named bot token: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_available_bots(self) -> List[Dict[str, Any]]:
        """Get list of available named bot tokens."""
        bots = []
        for name, info in self.bot_cache.items():
            bots.append({
                'name': name,
                'username': info['username'],
                'first_name': info['first_name'],
                'added_at': info['added_at']
            })
        return bots
    
    async def get_bot_token_by_name(self, bot_name: str) -> Optional[str]:
        """Get bot token by name."""
        return self.bot_cache.get(bot_name, {}).get('token')
    
    async def remove_bot_token(self, bot_name: str) -> bool:
        """Remove a named bot token."""
        if bot_name in self.bot_cache:
            del self.bot_cache[bot_name]
            return True
        return False


class BotManagementCommands:
    """Admin commands for bot token management."""
    
    def __init__(self, database: Database, encryption_manager: EncryptionManager):
        self.database = database
        self.encryption_manager = encryption_manager
        self.bot_manager = BotTokenManager(database, encryption_manager)
    
    async def addbot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add a named bot token to the system."""
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "**Add Named Bot Token**\n\n"
                    "Usage: `/addbot <name> <bot_token>`\n\n"
                    "**Example:**\n"
                    "`/addbot MyBot 5555555555:AAA...`\n\n"
                    "This will save the bot token with a friendly name for easy selection.",
                    parse_mode='Markdown'
                )
                return
            
            bot_name = context.args[0]
            bot_token = context.args[1]
            
            # Add bot token
            result = await self.bot_manager.add_named_bot_token(bot_name, bot_token)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ {result['message']}\n\n"
                    "You can now use this bot when creating forwarding pairs.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to add bot: {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in addbot command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def listbots_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all available named bot tokens."""
        try:
            bots = await self.bot_manager.get_available_bots()
            
            if not bots:
                await update.message.reply_text(
                    "📭 **No Bot Tokens Available**\n\n"
                    "Use `/addbot <name> <token>` to add bot tokens for use in forwarding pairs."
                )
                return
            
            message = "🤖 **Available Bot Tokens**\n\n"
            
            for bot in bots:
                message += f"**{bot['name']}**\n"
                message += f"🤖 Bot: @{bot['username']} ({bot['first_name']})\n"
                message += f"📅 Added: {bot['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            
            message += "**Management:**\n"
            message += "• `/addbot <name> <token>` - Add new bot\n"
            message += "• `/removebot <name>` - Remove bot token"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in listbots command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def removebot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a named bot token."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: `/removebot <name>`\n\n"
                    "Remove a named bot token from the system."
                )
                return
            
            bot_name = context.args[0]
            success = await self.bot_manager.remove_bot_token(bot_name)
            
            if success:
                await update.message.reply_text(f"✅ Bot token '{bot_name}' removed successfully.")
            else:
                await update.message.reply_text(f"❌ Bot token '{bot_name}' not found.")
                
        except Exception as e:
            logger.error(f"Error in removebot command: {e}")
            await update.message.reply_text(f"❌ Error: {e}")