"""Main admin bot handler for managing the forwarding system."""

import asyncio
from typing import List, Optional

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from core.database import Database
from core.session_manager import SessionManager
from core.advanced_session_manager import AdvancedSessionManager
from admin_bot.commands import AdminCommands
from admin_bot.unified_session_commands import UnifiedSessionCommands


class AdminHandler:
    """Main admin bot handler."""
    
    def __init__(self, bot_token: str, database: Database, session_manager: SessionManager, admin_user_ids: List[int], advanced_session_manager: Optional[AdvancedSessionManager] = None):
        self.bot_token = bot_token
        self.database = database
        self.session_manager = session_manager
        self.advanced_session_manager = advanced_session_manager
        self.admin_user_ids = set(admin_user_ids)
        self.application: Optional[Application] = None
        self.commands: Optional[AdminCommands] = None
        self.unified_commands: Optional[UnifiedSessionCommands] = None
        self.running = False
    
    async def start(self):
        """Start the admin bot."""
        if self.running:
            logger.warning("Admin bot is already running")
            return
        
        try:
            logger.info("Starting admin bot...")
            
            # Initialize commands handlers
            self.commands = AdminCommands(self.database, self.session_manager)
            if self.advanced_session_manager:
                self.unified_commands = UnifiedSessionCommands(self.database, self.advanced_session_manager)
            
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self._setup_handlers()
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.running = True
            logger.info("Admin bot started successfully")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start admin bot: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the admin bot."""
        if not self.running:
            return
        
        logger.info("Stopping admin bot...")
        self.running = False
        
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Admin bot stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping admin bot: {e}")
        
        self.application = None
        self.commands = None
    
    def _setup_handlers(self):
        """Setup command and callback handlers."""
        if not self.application or not self.commands:
            return
        
        # Add basic command handlers with admin check
        command_handlers = [
            ("start", self.commands.start_command),
            ("help", self.commands.help_command),
            ("addpair", self.commands.addpair_command),
            ("listpairs", self.commands.listpairs_command),
            ("removepair", self.commands.removepair_command),
            ("status", self.commands.status_command),
            ("sessions", self.commands.sessions_command),
            ("changesession", self.commands.changesession_command),
            ("blockword", self.commands.blockword_command),
        ]
        
        # Add unified session management command
        if self.unified_commands:
            unified_handlers = [
                ("addsession", self.unified_commands.addsession_command),
            ]
            command_handlers.extend(unified_handlers)
        
        for command_name, handler_func in command_handlers:
            wrapped_handler = self._wrap_admin_handler(handler_func)
            self.application.add_handler(CommandHandler(command_name, wrapped_handler))
        
        # Add unified session callback handlers FIRST (more specific patterns)
        if self.unified_commands:
            otp_callback_handler = self._wrap_admin_handler(self.unified_commands.handle_otp_callback)
            self.application.add_handler(CallbackQueryHandler(otp_callback_handler, pattern="^(enter_otp|resend_otp|cancel_otp):"))
        
        # Add general callback query handlers LAST (catch-all)
        wrapped_callback_handler = self._wrap_admin_handler(self.commands.handle_callback_query)
        self.application.add_handler(CallbackQueryHandler(wrapped_callback_handler))
        
        # Add message handler for OTP codes and unknown messages
        if self.unified_commands:
            # Handler for OTP messages (higher priority)
            otp_message_handler = self._wrap_admin_handler(self._handle_otp_or_unknown_message)
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, otp_message_handler)
            )
        else:
            # Handler for unknown messages only
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._wrap_admin_handler(self._handle_unknown_message))
            )
        
        logger.info("Admin bot handlers setup complete")
    
    def _wrap_admin_handler(self, handler_func):
        """Wrap handler function with admin permission check."""
        async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                user_id = update.effective_user.id
                
                # Debug logging for callbacks
                if update.callback_query:
                    logger.info(f"Callback received: {update.callback_query.data} from user {user_id}")
                
                # Check if user is admin
                if user_id not in self.admin_user_ids:
                    if update.effective_message:
                        await update.effective_message.reply_text(
                            "❌ Access denied. You are not authorized to use this bot."
                        )
                    logger.warning(f"Unauthorized access attempt from user {user_id}")
                    return
                
                # Call the actual handler
                await handler_func(update, context)
                
            except Exception as e:
                logger.error(f"Error in admin handler: {e}")
                try:
                    if update.effective_message:
                        await update.effective_message.reply_text(f"❌ An error occurred: {e}")
                except:
                    pass  # Ignore errors when sending error messages
        
        return wrapped_handler
    
    async def _handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages."""
        await update.message.reply_text(
            "❓ I don't understand that message. Use /help to see available commands."
        )
    
    async def _handle_otp_or_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle OTP codes or unknown messages."""
        if self.unified_commands:
            # Try to handle as OTP first
            handled = await self.unified_commands.handle_otp_message(update, context)
            if not handled:
                # Not an OTP message, treat as unknown
                await self._handle_unknown_message(update, context)
        else:
            await self._handle_unknown_message(update, context)
    
    def add_admin_user(self, user_id: int):
        """Add a new admin user."""
        self.admin_user_ids.add(user_id)
        logger.info(f"Added admin user: {user_id}")
    
    def remove_admin_user(self, user_id: int):
        """Remove an admin user."""
        self.admin_user_ids.discard(user_id)
        logger.info(f"Removed admin user: {user_id}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_user_ids
    
    async def broadcast_message(self, message: str):
        """Broadcast a message to all admin users."""
        if not self.application or not self.running:
            logger.error("Admin bot is not running")
            return
        
        for admin_id in self.admin_user_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send broadcast message to admin {admin_id}: {e}")
    
    async def send_alert(self, alert_message: str):
        """Send an alert to all admin users."""
        alert_text = f"🚨 **ALERT** 🚨\n\n{alert_message}"
        await self.broadcast_message(alert_text)
        logger.warning(f"Alert sent to admins: {alert_message}")
    
    async def send_notification(self, notification: str):
        """Send a notification to all admin users."""
        notification_text = f"📢 **Notification**\n\n{notification}"
        await self.broadcast_message(notification_text)
        logger.info(f"Notification sent to admins: {notification}")
